#!/usr/bin/env python3
"""Build the repos of a flow in order, publishing each to Maven Local. The first failure stops the chain.

After a repo is published, its version is written into the properties files of the later repos listed
under "handoff" in the config, so the next build uses it. Those edits are build wiring only and are
put back when the chain ends, so they never reach a PR.
"""
import argparse
import os
import re
import time

from common import (UpgradeError, flow_repos, load_config, main_wrapper, repo_dir, run, save_json,
                    vuln_dir)


def resolve(command, root):
    """Use the repo's own Gradle wrapper; on Windows that is gradlew.bat."""
    command = list(command)
    if command[0] in ('./gradlew', 'gradlew'):
        command[0] = str(root / ('gradlew.bat' if os.name == 'nt' else 'gradlew'))
    return command


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
    lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
    for index, line in enumerate(lines):
        stripped = line.rstrip('\r\n')
        match = pattern.match(stripped)
        if match:
            lines[index] = match.group(1) + value + match.group(3) + line[len(stripped):]
            path.write_text(''.join(lines), encoding='utf-8', newline='')
            return match.group(2)
    return None


def hand_off(repo, root, later, config, workspace, snapshots, notes):
    for rule in config.get('handoff', []):
        if rule['from'] != repo:
            continue
        version = read_property(root / rule.get('version_file', 'gradle.properties'), rule.get('version_key', 'version'))
        if not version:
            notes.append(f"{repo}: could not read its version from {rule.get('version_file', 'gradle.properties')}")
            continue
        for target in rule['to']:
            if target['repo'] not in later:
                continue
            path = repo_dir(workspace, target['repo']) / target['file']
            if not path.is_file():
                notes.append(f"{target['repo']}: {target['file']} not found, version {version} not handed over")
                continue
            original = path.read_text(encoding='utf-8')
            old = set_property(path, target['key'], version)
            if old is None:
                notes.append(f"{target['repo']}: key {target['key']} not found in {target['file']}, skipped")
            else:
                snapshots.append((path, original))
                notes.append(f"{target['repo']}: {target['key']} {old} -> {version} (from {repo}, temporary)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flow', required=True)
    parser.add_argument('--feature-dir', required=True)
    parser.add_argument('--workspace')
    parser.add_argument('--from-repo', help='resume the chain at this repo')
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
    publish = bool(config['flows'][args.flow].get('publish'))
    out = vuln_dir(args.feature_dir)
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
                code, output = run(command, root, timeout)
                log = out / f'{step}-{repo}.log'
                log.write_text(output, encoding='utf-8')
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
            path.write_text(original, encoding='utf-8', newline='')
    for note in notes:
        print(f'handoff: {note}')
    all_passed = failed is None and not args.dry_run and bool(results)
    save_json(out / 'build-results.json', {'flow': args.flow, 'all_passed': all_passed, 'failed_repo': failed,
                                            'dry_run': args.dry_run, 'handoff': notes, 'results': results})
    print('All builds passed.' if all_passed else f'Stopped at {failed}.' if failed else 'Dry run only.')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main_wrapper(main))
