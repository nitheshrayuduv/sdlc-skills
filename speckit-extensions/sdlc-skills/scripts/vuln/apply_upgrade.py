#!/usr/bin/env python3
"""Edit the lines listed in changes.json in each affected repo. Run prepare_branches.py first."""
import argparse
import difflib
from pathlib import Path

from common import (UpgradeError, load_config, load_intake, load_json, main_wrapper, repo_dir,
                    resolve_workspace, run, save_json, version_pattern)


def edit(path, changes, dry_run):
    raw = path.read_bytes().decode('utf-8').splitlines(keepends=True)  # bytes: keep CRLF as it is
    before = list(raw)
    for change in changes:
        index = change['line'] - 1
        pattern = version_pattern(change['old'])
        if index >= len(raw) or not pattern.search(raw[index]):
            raise UpgradeError(f"{path.name}:{change['line']} no longer contains {change['old']}. "
                               'Re-run the search before applying.', 5)
        raw[index] = pattern.sub(change['new'], raw[index], count=1)
    diff = ''.join(difflib.unified_diff(before, raw, f'a/{path.name}', f'b/{path.name}'))
    if not dry_run:
        path.write_bytes(''.join(raw).encode('utf-8'))
    return diff


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--changes', required=True)
    parser.add_argument('--workspace')
    parser.add_argument('--branch', help='default: the branch in intake.json')
    parser.add_argument('--out', required=True, help='apply-results.json to write')
    parser.add_argument('--allow-dirty', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--config')
    args = parser.parse_args()
    config = load_config(args.config)
    changes_path = Path(args.changes)
    data = load_json(changes_path)
    workspace = resolve_workspace(config, args.workspace)
    branch = args.branch or load_intake(changes_path.parent).get('branch') or config['branch_prefix'] + data['ticket']
    by_repo = {}
    for change in data['changes']:
        by_repo.setdefault(change['repo'], []).append(change)
    if not by_repo:
        raise UpgradeError('changes.json has no changes to apply.', 2)
    results = {}
    for repo, changes in by_repo.items():
        root = repo_dir(workspace, repo)
        current = run(['git', 'branch', '--show-current'], root)[1].strip()
        if current != branch and not args.dry_run:
            raise UpgradeError(f'{repo} is on {current or "a detached HEAD"}, not {branch}. '
                               'Run prepare_branches.py first.', 2)
        code, status = run(['git', 'status', '--porcelain'], root)
        if code or (status.strip() and not args.allow_dirty):
            raise UpgradeError(f'{repo} has uncommitted changes. Commit or stash them, or use --allow-dirty.', 2)
        files = {}
        for change in changes:
            files.setdefault(change['file'], []).append(change)
        diffs = [edit(root / rel, items, args.dry_run) for rel, items in files.items()]
        results[repo] = {'branch': branch, 'files': sorted(files), 'diff': '\n'.join(diffs)}
        print(f"{repo}: {len(changes)} line(s) in {len(files)} file(s)" + (' (dry run)' if args.dry_run else ''))
        print(results[repo]['diff'])
    save_json(args.out, {'ticket': data['ticket'], 'branch': branch, 'dry_run': args.dry_run, 'repos': results})


if __name__ == '__main__':
    raise SystemExit(main_wrapper(main))
