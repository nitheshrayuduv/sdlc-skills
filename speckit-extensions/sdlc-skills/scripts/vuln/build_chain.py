#!/usr/bin/env python3
"""Build the repos of a flow in order, publishing each to Maven Local. The first failure stops the chain.

After a repo is published, its version is written into the properties files of the later repos listed
under "handoff" in the config, so the next build uses it. Those edits are build wiring only and are
put back when the chain ends, so they never reach a PR.
"""
import argparse
import os
import re
import subprocess
import threading
import time

from pathlib import Path

from common import (UpgradeError, flow_repos, load_config, load_json, main_wrapper, redact, repo_dir, run,
                    save_json, vuln_dir)


def resolve(command, root):
    """Use the repo's own Gradle wrapper; on Windows that is gradlew.bat."""
    command = list(command)
    if command[0] in ('./gradlew', 'gradlew'):
        command[0] = str(root / ('gradlew.bat' if os.name == 'nt' else 'gradlew'))
    return command


def run_live(command, cwd, timeout, log_path, label, heartbeat=60):
    """Run a build, writing its output to log_path as it happens and printing a heartbeat line.

    Without this a long Gradle build is silent until it ends. Tail the log to watch it:
    Get-Content <log> -Wait -Tail 20. Returns (exit code, redacted output).
    """
    started, lines, last = time.time(), [], ['starting']
    try:
        proc = subprocess.Popen(command, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors='replace', bufsize=1)
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


def gradle_version(root, config):
    """Ask the repo's own Gradle for the version it just published (release plugins compute it)."""
    command = resolve(config['build'].get('version_command', ['./gradlew', '-q', 'properties']), root)
    code, output = run(command, root, config['build'].get('version_timeout_seconds', 900))
    for line in output.splitlines():
        match = re.match(r'^version:\s*(\S+)\s*$', line)
        if match and match.group(1) != 'unspecified':
            return match.group(1)
    return None


def hand_off(repo, root, later, config, workspace, snapshots, notes):
    for rule in config.get('handoff', []):
        if rule['from'] != repo:
            continue
        if rule.get('version_source') == 'gradle':
            version, origin = gradle_version(root, config), 'Gradle'
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
    parser.add_argument('--from-repo', help='resume the chain at this repo')
    parser.add_argument('--changed-only', action='store_true',
                        help='build only repos with a change in changes.json and the repos that pin them')
    parser.add_argument('--changes', help='changes.json for --changed-only (default: <feature-dir>/vuln/changes.json)')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--config')
    args = parser.parse_args()
    config = load_config(args.config)
    workspace = args.workspace or config['workspace_root']
    repos = flow_repos(config, args.flow)
    if args.from_repo:
        if args.from_repo not in repos:
            raise UpgradeError(f'{args.from_repo} is not in the {args.flow} flow.', 2)
        repos = repos[repos.index(args.from_repo):]
    out = vuln_dir(args.feature_dir)
    skipped, scope_notes = [], []
    if args.changed_only:
        every = list(repos)
        repos, changed, scope_notes = affected_repos(repos, config, args.changes or out / 'changes.json')
        skipped = [r for r in every if r not in repos]
        print(f"changed: {', '.join(changed)}")
        print(f"building: {', '.join(repos)}")
        print(f"skipped (unchanged and not downstream of a change): {', '.join(skipped) or 'none'}")
        for note in scope_notes:
            print(f'warning: {note}')
    publish = bool(config['flows'][args.flow].get('publish'))
    timeout = config['build'].get('timeout_seconds')
    results, notes, snapshots, failed = [], [], [], None
    try:
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
                code, output = run_live(command, root, timeout, log, f'{repo} {step}')
                results.append({'repo': repo, 'step': step, 'status': 'passed' if code == 0 else 'failed',
                                'exit_code': code, 'seconds': round(time.time() - started), 'log': str(log)})
                if code:
                    failed = repo
                    print(f'[{repo}] {step} FAILED (exit {code}). Last lines:\n' + '\n'.join(output.splitlines()[-20:]))
                    break
            if failed:
                break
            if publish and not args.dry_run:
                hand_off(repo, root, repos[position + 1:], config, workspace, snapshots, notes)
    finally:
        for path, original in reversed(snapshots):
            path.write_bytes(original)
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
