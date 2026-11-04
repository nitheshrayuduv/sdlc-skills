#!/usr/bin/env python3
"""Validate the flow, Agility ticket and branch, and write intake.json.

Run it again with --base once the user has named the parent branch for a missing branch.
"""
import argparse
import re

from common import UpgradeError, flow_repos, load_config, main_wrapper, save_json, vuln_dir

TICKET = re.compile(r'^[A-Z]{1,3}-\d{3,}$')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flow', required=True)
    parser.add_argument('--ticket', required=True)
    parser.add_argument('--feature-dir', required=True)
    parser.add_argument('--branch', help='branch to work on (default: <branch_prefix><ticket>)')
    parser.add_argument('--base', help='parent branch to create the branch from when it does not exist')
    parser.add_argument('--base-for', action='append', default=[], metavar='REPO=BRANCH',
                        help='a different parent branch for one repo; remembered in intake.json')
    parser.add_argument('--config')
    args = parser.parse_args()
    config = load_config(args.config)
    repos = flow_repos(config, args.flow)
    ticket = args.ticket.strip().upper()
    if not TICKET.match(ticket):
        raise UpgradeError(f"'{args.ticket}' does not look like an Agility number such as D-12345 or S-12345.", 2)
    base_for = dict(item.split('=', 1) for item in args.base_for)
    unknown = [r for r in base_for if r not in repos]
    if unknown:
        raise UpgradeError(f"--base-for names repos outside the {args.flow} flow: {', '.join(unknown)}", 2)
    out = vuln_dir(args.feature_dir) / 'intake.json'
    save_json(out, {'flow': args.flow, 'ticket': ticket, 'repos': repos,
                    'branch': args.branch or config['branch_prefix'] + ticket, 'base': args.base,
                    'base_for': base_for,
                    'publish': bool(config['flows'][args.flow].get('publish'))})
    print(out)


if __name__ == '__main__':
    raise SystemExit(main_wrapper(main))
