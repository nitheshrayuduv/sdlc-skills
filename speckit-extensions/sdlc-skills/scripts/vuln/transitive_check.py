#!/usr/bin/env python3
"""For dependencies declared nowhere, check whether a repo pulls the vulnerable version in transitively.

Runs Gradle dependencyInsight in each repo of the flow. It only reports; it never edits files. A
transitive hit means the fix is to upgrade the parent dependency or add a constraint, which the user
chooses.
"""
import argparse

from common import (flow_repos, load_config, load_json, main_wrapper, repo_dir, resolve_workspace, run,
                    save_json, version_pattern)
from build_chain import resolve
from resolve_owner import markdown


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--changes', required=True, help='changes.json to read and update')
    parser.add_argument('--workspace')
    parser.add_argument('--plan-md', help='rewrite the plan section with the new decisions')
    parser.add_argument('--config')
    args = parser.parse_args()
    config = load_config(args.config)
    data = load_json(args.changes)
    workspace = resolve_workspace(config, args.workspace)
    template = config['transitive']['command']
    timeout = config['build'].get('timeout_seconds')
    for row in data['dependencies']:
        if row['decision'] != 'not-found':
            continue
        row['transitive'], row['transitive_errors'] = [], []
        pattern = version_pattern(row['vulnerable_version'])
        for repo in flow_repos(config, data['flow']):
            root = repo_dir(workspace, repo)
            command = resolve([part.format(dependency=row['dependency']) for part in template], root)
            code, output = run(command, root, timeout)
            lines = output.splitlines()
            hit = next((i for i, text in enumerate(lines)
                        if row['dependency'] in text and pattern.search(text)), None)
            if hit is not None:
                row['transitive'].append({'repo': repo, 'evidence': lines[max(0, hit - 3):hit + 12]})
            elif code:
                row['transitive_errors'].append({'repo': repo, 'exit_code': code, 'tail': lines[-3:]})
        if row['transitive']:
            row['decision'] = 'transitive'
            row['action'] = 'Upgrade the parent dependency shown in the evidence, or add a constraint. Needs a decision.'
        print(f"{row['dependency']}: {row['decision']} "
              f"({len(row['transitive'])} repo(s), {len(row['transitive_errors'])} check error(s))")
    save_json(args.changes, data)
    if args.plan_md:
        with open(args.plan_md, 'w', encoding='utf-8') as handle:
            handle.write(markdown(data['ticket'], data['flow'], data['dependencies']))


if __name__ == '__main__':
    raise SystemExit(main_wrapper(main))
