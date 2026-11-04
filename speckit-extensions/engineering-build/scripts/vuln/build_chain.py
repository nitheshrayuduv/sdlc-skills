#!/usr/bin/env python3
"""Build the repos of a flow in order, publishing each to Maven Local. The first failure stops the chain.

After a repo is published, its version is written into the properties files of the later repos listed
under "handoff" in the config, so the next build uses it. Those edits are build wiring only and are
put back when the chain ends, so they never reach a PR.
"""
import argparse
import base64
import json
import os
import re
import subprocess
import threading
import time

from pathlib import Path

from common import (UpgradeError, flow_repos, load_config, load_json, main_wrapper, redact, repo_dir,
                    resolve_workspace, run, save_json, vuln_dir)


def resolve(command, root):
    """Use the repo's own Gradle wrapper; on Windows that is gradlew.bat."""
    command = list(command)
    if command[0] in ('./gradlew', 'gradlew'):
        command[0] = str(root / ('gradlew.bat' if os.name == 'nt' else 'gradlew'))
    return command


def repo_env(config, repo):
    """The process environment for a repo, plus any `env` set for it under repo_overrides (for example JAVA_HOME)."""
    env = dict(os.environ)
    env.update(config.get('repo_overrides', {}).get(repo, {}).get('env', {}))
    return env


def run_live(command, cwd, timeout, log_path, label, heartbeat=60, env=None):
    """Run a build, writing its output to log_path as it happens and printing a heartbeat line.

    Without this a long Gradle build is silent until it ends. Tail the log to watch it:
    Get-Content <log> -Wait -Tail 20. Returns (exit code, redacted output).
    """
    started, lines, last = time.time(), [], ['starting']
    try:
        proc = subprocess.Popen(command, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors='replace', bufsize=1, env=env)
    except FileNotFoundError:
        return 127, f'Command not found: {command[0]}'
    with open(log_path, 'w', encoding='utf-8') as log:
        def pump():
            for line in proc.stdout:
                line = redact(line)
                log.write(line)
                log.flush()
                lines.append(line)
                if line.startswith('> Task'):
                    last[0] = line.strip()
        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        code = None
        while code is None:
            try:
                code = proc.wait(timeout=heartbeat)
            except subprocess.TimeoutExpired:
                elapsed = time.time() - started
                if timeout and elapsed > timeout:
                    proc.kill()
                    code = 124
                    lines.append(f'Timed out after {timeout}s\n')
                    break
                print(f"[{label}] still running, {int(elapsed // 60)} min, last: {last[0]}", flush=True)
        reader.join(10)
    return code, ''.join(lines)


def write_backup(snapshots, backup_path):
    """Keep every temporary edit's original bytes on disk, so a hard stop cannot leave them behind."""
    items = [{'path': str(p), 'data': base64.b64encode(data).decode('ascii')} for p, data in snapshots]
    Path(backup_path).write_text(json.dumps(items), encoding='utf-8')


def recover_interrupted_handoff(backup_path):
    """Put back files left edited by an earlier run that was stopped before it could clean up."""
    path = Path(backup_path)
    if not path.is_file():
        return []
    restored = []
    for item in reversed(json.loads(path.read_text(encoding='utf-8'))):
        Path(item['path']).write_bytes(base64.b64decode(item['data']))
        restored.append(item['path'])
    path.unlink()
    return restored


def property_value(text, key):
    pattern = re.compile(r'^\s*' + re.escape(key) + r'\s*[=:]\s*["\']?([^\s"\']+)')
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1)
    return None


def hand_edited_pins(repos, config, workspace):
    """Hand-over keys whose value on disk differs from the committed one.

    The chain sets these keys itself and restores what it found. A key already changed by hand would
    be "restored" to the hand edit, not to the committed release pin, so the chain refuses to start.
    """
    problems = []
    for rule in config.get('handoff', []):
        for target in rule['to']:
            if target['repo'] not in repos:
                continue
            root = repo_dir(workspace, target['repo'])
            path = root / target['file']
            if not path.is_file():
                continue
            code, committed_text = run(['git', 'show', f"HEAD:{target['file']}"], root)
            if code:
                continue
            committed = property_value(committed_text, target['key'])
            current = property_value(path.read_bytes().decode('utf-8', 'replace'), target['key'])
            if committed and current and committed != current:
                problems.append(f"{target['repo']}/{target['file']}: {target['key']} is {current}, committed {committed}")
    return sorted(set(problems))


def read_property(path, key):
    if not path.is_file():
        return None
    pattern = re.compile(r'^\s*' + re.escape(key) + r'\s*[=:]\s*["\']?([^\s"\']+)')
    for line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1)
    return None


def set_property(path, key, value):
    """Change an existing property only; never adds one. Returns the old value or None."""
    pattern = re.compile(r'^(\s*' + re.escape(key) + r'\s*[=:]\s*["\']?)([^\s"\']+)(.*)$')
    lines = path.read_bytes().decode('utf-8').splitlines(keepends=True)  # bytes: keep CRLF as it is
    for index, line in enumerate(lines):
        stripped = line.rstrip('\r\n')
        match = pattern.match(stripped)
        if match:
            lines[index] = match.group(1) + value + match.group(3) + line[len(stripped):]
            path.write_bytes(''.join(lines).encode('utf-8'))
            return match.group(2)
    return None


def gradle_version(root, config, repo=None):
    """Ask the repo's own Gradle for the version it just published (release plugins compute it)."""
    command = resolve(config['build'].get('version_command', ['./gradlew', '-q', 'properties']), root)
    try:
        done = subprocess.run(command, cwd=str(root), capture_output=True, text=True, errors='replace',
                              timeout=config['build'].get('version_timeout_seconds', 900),
                              env=repo_env(config, repo) if repo else None)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    output = redact((done.stdout or '') + (done.stderr or ''))
    for line in output.splitlines():
        match = re.match(r'^version:\s*(\S+)\s*$', line)
        if match and match.group(1) != 'unspecified':
            return match.group(1)
    return None


def hand_off(repo, root, later, config, workspace, snapshots, notes, backup_path=None):
    for rule in config.get('handoff', []):
        if rule['from'] != repo:
            continue
        if rule.get('version_source') == 'gradle':
            version, origin = gradle_version(root, config, repo), 'Gradle'
        else:
            origin = rule.get('version_file', 'gradle.properties')
            version = read_property(root / origin, rule.get('version_key', 'version'))
        if not version:
            notes.append(f"{repo}: could not read its version from {origin}")
            continue
        for target in rule['to']:
            if target['repo'] not in later:
                continue
            path = repo_dir(workspace, target['repo']) / target['file']
            if not path.is_file():
                notes.append(f"{target['repo']}: {target['file']} not found, version {version} not handed over")
                continue
            original = path.read_bytes()
            old = set_property(path, target['key'], version)
            if old is None:
                notes.append(f"{target['repo']}: key {target['key']} not found in {target['file']}, skipped")
            else:
                snapshots.append((path, original))
                if backup_path:
                    write_backup(snapshots, backup_path)
                notes.append(f"{target['repo']}: {target['key']} {old} -> {version} (from {repo}, temporary)")


def affected_repos(repos, config, changes_path):
    """Repos worth building: the ones with a change, plus every repo that pins one of them.

    Dependents come from the handoff rules (upstream -> repos that pin its version), followed
    transitively. Repos outside that set only consume released versions of their upstreams, so
    building them proves nothing about the change. Returns (repos in flow order, changed, notes).
    """
    if not Path(changes_path).is_file():
        raise UpgradeError(f'{changes_path} not found. Run the locate step first.', 2)
    changed = {c['repo'] for c in load_json(changes_path).get('changes', [])}
    unknown = sorted(changed - set(repos))
    if unknown:
        raise UpgradeError(f"changes.json names repos outside this flow: {', '.join(unknown)}", 2)
    if not changed:
        raise UpgradeError('changes.json has no changes, so there is nothing to build.', 2)
    rules = config.get('handoff', [])
    affected, queue = set(changed), list(changed)
    while queue:
        current = queue.pop()
        for rule in rules:
            if rule['from'] != current:
                continue
            for target in rule['to']:
                if target['repo'] in repos and target['repo'] not in affected:
                    affected.add(target['repo'])
                    queue.append(target['repo'])
    selected = [r for r in repos if r in affected]
    notes = []
    for rule in rules:
        if rule['from'] not in selected:
            continue
        for target in rule['to']:
            name = target['repo']
            if name in selected and selected.index(name) < selected.index(rule['from']):
                notes.append(f"{name} pins {target['key']} of {rule['from']} but is built before it in the flow "
                             'order, so it builds against the pinned release, not this run')
    return selected, sorted(changed), sorted(set(notes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flow', required=True)
    parser.add_argument('--feature-dir', required=True)
    parser.add_argument('--workspace')
    parser.add_argument('--from-repo', help='resume at this repo; earlier repos are assumed already published '
                                            'and their versions are handed over again')
    parser.add_argument('--changed-only', action='store_true',
                        help='build only repos with a change in changes.json and the repos that pin them')
    parser.add_argument('--changes', help='changes.json for --changed-only (default: <feature-dir>/vuln/changes.json)')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--config')
    args = parser.parse_args()
    config = load_config(args.config)
    workspace = resolve_workspace(config, args.workspace)
    repos = flow_repos(config, args.flow)
    out = vuln_dir(args.feature_dir)
    skipped, scope_notes, done_before = [], [], []
    backup_path = out / 'handoff-backup.json'
    if not args.dry_run:
        for restored in recover_interrupted_handoff(backup_path):
            print(f'recovered an earlier interrupted run: restored {restored}')
    if args.changed_only:
        every = list(repos)
        repos, changed, scope_notes = affected_repos(repos, config, args.changes or out / 'changes.json')
        skipped = [r for r in every if r not in repos]
        print(f"changed: {', '.join(changed)}")
        print(f"building: {', '.join(repos)}")
        print(f"skipped (unchanged and not downstream of a change): {', '.join(skipped) or 'none'}")
        for note in scope_notes:
            print(f'warning: {note}')
    if args.from_repo:
        if args.from_repo not in repos:
            raise UpgradeError(f'{args.from_repo} is not one of the repos to build: {", ".join(repos)}.', 2)
        cut = repos.index(args.from_repo)
        done_before, repos = repos[:cut], repos[cut:]
        print(f"resuming at {args.from_repo}; assuming already built and published: {', '.join(done_before) or 'none'}")
    if not args.dry_run:
        edited = hand_edited_pins(repos, config, workspace)
        if edited:
            raise UpgradeError('These version pins were changed by hand; the chain sets them itself and must start '
                               'from the committed values. Revert them (git checkout -- <file>) and run again:\n  '
                               + '\n  '.join(edited), 2)
    publish = bool(config['flows'][args.flow].get('publish'))
    timeout = config['build'].get('timeout_seconds')
    results, notes, snapshots, failed = [], [], [], None
    try:
        if done_before and publish and not args.dry_run:
            # The earlier repos are already in Maven Local; hand their versions to the repos still to build.
            for earlier in done_before:
                hand_off(earlier, repo_dir(workspace, earlier), repos, config, workspace, snapshots, notes,
                         backup_path)
        for position, repo in enumerate(repos):
            root = repo_dir(workspace, repo)
            override = config.get('repo_overrides', {}).get(repo, {})
            steps = [('build', override.get('command', config['build']['command']))]
            if publish:
                steps.append(('publish', override.get('publish_command', config['build']['publish_command'])))
            for step, command in steps:
                command = resolve(command, root)
                print(f"[{repo}] {step}: {' '.join(command)}", flush=True)
                if args.dry_run:
                    results.append({'repo': repo, 'step': step, 'status': 'planned'})
                    continue
                started = time.time()
                log = out / f'{step}-{repo}.log'
                print(f'[{repo}] {step} log: {log}', flush=True)
                code, output = run_live(command, root, timeout, log, f'{repo} {step}', env=repo_env(config, repo))
                results.append({'repo': repo, 'step': step, 'status': 'passed' if code == 0 else 'failed',
                                'exit_code': code, 'seconds': round(time.time() - started), 'log': str(log)})
                if code:
                    failed = repo
                    print(f'[{repo}] {step} FAILED (exit {code}). Last lines:\n' + '\n'.join(output.splitlines()[-20:]))
                    break
            if failed:
                break
            if publish and not args.dry_run:
                hand_off(repo, root, repos[position + 1:], config, workspace, snapshots, notes, backup_path)
    finally:
        for path, original in reversed(snapshots):
            path.write_bytes(original)
        if snapshots and backup_path.is_file():
            backup_path.unlink()
    for note in notes:
        print(f'handoff: {note}')
    all_passed = failed is None and not args.dry_run and bool(results)
    save_json(out / 'build-results.json', {'flow': args.flow, 'all_passed': all_passed, 'failed_repo': failed,
                                            'dry_run': args.dry_run, 'changed_only': args.changed_only,
                                            'skipped': skipped, 'warnings': scope_notes,
                                            'handoff': notes, 'results': results})
    print('All builds passed.' if all_passed else f'Stopped at {failed}.' if failed else 'Dry run only.')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main_wrapper(main))
