#!/usr/bin/env python3
"""Push the branches and open one PR per changed repo, only if every build passed."""
import argparse

from common import (UpgradeError, load_config, load_intake, load_json, main_wrapper, repo_dir,
                    resolve_workspace, run, save_json, vuln_dir)


def pr_body(ticket, repo, flow, changes, siblings, footer=None):
    lines = [f'Fixes the vulnerable dependency versions listed in Agility {ticket} ({flow} flow).', '',
             '| Dependency | From | To | File |', '| --- | --- | --- | --- |']
    lines += [f"| {c['dependency']} | {c['old']} | {c['new']} | `{c['file']}` |" for c in changes]
    # A finding that did not come from the ticket says where it came from, so the PR does not overclaim.
    for dependency, source in sorted({(c['dependency'], c['source']) for c in changes if c.get('source')}):
        lines += ['', f'Note: `{dependency}` is not listed in {ticket}; it comes from {source}.']
    lines += ['', 'All repositories in the chain built successfully before this PR was opened.']
    others = {name: url for name, url in siblings.items() if name != repo}
    if others:
        lines += ['', 'Related PRs:'] + [f'- {name}: {url}' for name, url in others.items()]
    if footer:
        lines += ['', footer]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--feature-dir', required=True)
    parser.add_argument('--workspace')
    parser.add_argument('--base', help='target branch for PRs when the working branch already existed')
    parser.add_argument('--yes', action='store_true', help='push and open PRs; without it only the plan is shown')
    parser.add_argument('--trailer', help='extra line appended to each commit message, for example Co-Authored-By')
    parser.add_argument('--footer', help='extra line appended to each PR description')
    parser.add_argument('--config')
    args = parser.parse_args()
    config = load_config(args.config)
    out = vuln_dir(args.feature_dir)
    builds = load_json(out / 'build-results.json')
    if not builds.get('all_passed'):
        raise UpgradeError('Builds have not all passed, so no PRs will be raised. '
                           f"Failed repo: {builds.get('failed_repo') or 'none recorded'}.", 6)
    applied, plan = load_json(out / 'apply-results.json'), load_json(out / 'changes.json')
    branches = load_json(out / 'branches.json') if (out / 'branches.json').is_file() else {}
    created_from = branches.get('bases', {})
    intake = load_intake(out)
    ticket, workspace = plan['ticket'], resolve_workspace(config, args.workspace)
    per_repo = {}
    for change in plan['changes']:
        per_repo.setdefault(change['repo'], []).append(change)

    def target(repo):
        # The parent branch the working branch was created from: recorded at creation, else the intake answer.
        return (created_from.get(repo) or args.base or intake.get('base_for', {}).get(repo) or intake.get('base')
                or config.get('base_branch', {}).get(repo))

    print('PR plan:')
    for repo, info in applied['repos'].items():
        print(f"  {repo}: branch {info['branch']} -> {target(repo) or 'repo default branch'}, "
              f"files {', '.join(info['files'])}")
    if not args.yes:
        print('Nothing pushed. Re-run with --yes after the user confirms.')
        return 0
    title = f'fix(deps): upgrade vulnerable dependencies [{ticket}]'
    urls = {}
    for repo, info in applied['repos'].items():
        root = repo_dir(workspace, repo)
        code, text = run(['git', 'add', '--'] + info['files'], root)
        if code:
            raise UpgradeError(f'{repo}: {text.strip()}', 7)
        if run(['git', 'diff', '--cached', '--quiet'], root)[0] != 0:
            message = ['-m', title] + (['-m', args.trailer] if args.trailer else [])
            code, text = run(['git', 'commit'] + message, root)
            if code:
                raise UpgradeError(f'{repo}: commit failed: {text.strip()}', 7)
        code, text = run(['git', 'push', '-u', 'origin', info['branch']], root)
        if code:
            raise UpgradeError(f'{repo}: push failed: {text.strip()}', 7)
        code, existing = run(['gh', 'pr', 'list', '--head', info['branch'], '--state', 'open',
                              '--json', 'url', '--jq', '.[0].url'], root)
        if code == 0 and existing.strip():
            urls[repo] = existing.strip()
            continue
        command = ['gh', 'pr', 'create', '--head', info['branch'], '--title', title,
                   '--body', pr_body(ticket, repo, plan['flow'], per_repo[repo], {}, args.footer)]
        # The PR targets the parent branch the working branch was created from, when we created it.
        base = target(repo)
        if base:
            command += ['--base', base]
        code, text = run(command, root)
        if code:
            raise UpgradeError(f'{repo}: PR creation failed: {text.strip()}', 7)
        urls[repo] = text.strip().splitlines()[-1]
    for repo, url in urls.items():
        run(['gh', 'pr', 'edit', url, '--body', pr_body(ticket, repo, plan['flow'], per_repo[repo], urls,
                                                        args.footer)],
            repo_dir(workspace, repo))
    save_json(out / 'pr-results.json', {'ticket': ticket, 'prs': urls})
    for repo, url in urls.items():
        print(f'{repo}: {url}')


if __name__ == '__main__':
    raise SystemExit(main_wrapper(main))
