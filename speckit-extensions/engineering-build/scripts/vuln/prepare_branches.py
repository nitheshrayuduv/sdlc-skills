#!/usr/bin/env python3
"""Check out the working branch in every repo of the flow, creating it from a parent branch if missing.

Run with --check-only first. If it reports missing repos, ask the user for the parent branch and run
again with --base (or --base-for REPO=BRANCH for a repo with a different parent).
"""
import argparse

from common import (UpgradeError, flow_repos, load_config, load_intake, load_json, main_wrapper, repo_dir,
                    resolve_workspace, run, save_json, vuln_dir)


def ref_exists(root, ref):
    return run(['git', 'rev-parse', '--verify', '--quiet', ref], root)[0] == 0


def inspect(root, branch):
    code, remotes = run(['git', 'remote'], root)
    fetched = False
    if code == 0 and 'origin' in remotes.split():
        fetched = run(['git', 'fetch', '--prune', 'origin'], root)[0] == 0
    if ref_exists(root, f'refs/heads/{branch}'):
        return 'exists-local', fetched
    if ref_exists(root, f'refs/remotes/origin/{branch}'):
        return 'exists-remote', fetched
    return 'missing', fetched


def base_ref(root, base):
    for ref in (f'refs/remotes/origin/{base}', f'refs/heads/{base}'):
        if ref_exists(root, ref):
            return ref.replace('refs/remotes/', '').replace('refs/heads/', '')
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--feature-dir', required=True)
    parser.add_argument('--workspace')
    parser.add_argument('--flow')
    parser.add_argument('--branch')
    parser.add_argument('--base', help='parent branch for repos where the branch does not exist')
    parser.add_argument('--base-for', action='append', default=[], metavar='REPO=BRANCH')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--config')
    args = parser.parse_args()
    config = load_config(args.config)
    out = vuln_dir(args.feature_dir)
    intake = load_intake(out)
    flow = args.flow or intake.get('flow')
    branch = args.branch or intake.get('branch')
    base = args.base or intake.get('base')
    if not flow or not branch:
        raise UpgradeError('Flow and branch are required. Run intake.py first or pass --flow and --branch.', 2)
    overrides = {**config.get('base_branch', {}), **intake.get('base_for', {}),
                 **dict(item.split('=', 1) for item in args.base_for)}
    workspace = resolve_workspace(config, args.workspace)
    states = {}
    for repo in flow_repos(config, flow):
        root = repo_dir(workspace, repo)
        code, dirty = run(['git', 'status', '--porcelain'], root)
        if code or dirty.strip():
            raise UpgradeError(f'{repo} has uncommitted changes. Commit or stash them first.', 2)
        states[repo] = inspect(root, branch)[0]
    missing = [r for r, s in states.items() if s == 'missing']
    for repo, state in states.items():
        print(f'{repo}: {branch} {state}')
    if args.check_only:
        earlier = load_json(out / 'branches.json') if (out / 'branches.json').is_file() else {}
        save_json(out / 'branches.json', {'branch': branch, 'states': states, 'missing': missing,
                                          'bases': earlier.get('bases', {})})
        print('MISSING: ' + ', '.join(missing) if missing else 'The branch exists in every repo.')
        return 0
    actions = {}
    for repo, state in states.items():
        root = repo_dir(workspace, repo)
        if state == 'missing':
            parent = overrides.get(repo) or base
            if not parent:
                raise UpgradeError(f'{branch} does not exist in {repo}. Ask the user for the parent branch '
                                   'and re-run with --base.', 8)
            ref = base_ref(root, parent)
            if not ref:
                raise UpgradeError(f'Parent branch {parent} was not found in {repo}.', 8)
            run(['git', 'fetch', 'origin', parent], root)
            code, text = run(['git', 'checkout', '-b', branch, '--no-track', ref], root)
            actions[repo] = f'created from {ref}'
        else:
            code, text = run(['git', 'checkout', branch], root)
            actions[repo] = 'checked out existing branch'
        if code:
            raise UpgradeError(f'{repo}: {text.strip()}', 2)
        print(f'{repo}: {actions[repo]}')
    save_json(out / 'branches.json', {'branch': branch, 'base': base, 'states': states, 'actions': actions,
                                      'bases': {r: overrides.get(r) or base for r in missing}})
    return 0


if __name__ == '__main__':
    raise SystemExit(main_wrapper(main))
