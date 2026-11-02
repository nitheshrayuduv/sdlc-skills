#!/usr/bin/env python3
"""Decide which repo and file each dependency change belongs in."""
import argparse

from common import load_config, load_json, main_wrapper, save_json

CHANGE_TYPES = ('literal', 'property_definition')


def decide(finding, hits, platform):
    mine = [h for h in hits if h['dependency'] == finding['dependency']]
    changes = [h for h in mine if h['match_type'] in CHANGE_TYPES]
    review = [h for h in mine if h['match_type'] == 'property_candidate']
    others = [h for h in mine if h['match_type'] == 'other_version']
    owners = sorted({h['repo'] for h in changes})
    if changes:
        decision = 'change'
        scope = ('platform-only' if owners == [platform]
                 else 'platform+downstream' if platform in owners else 'downstream')
    elif review:
        decision, scope = 'review', None
    elif others:
        decision, scope = 'not-affected', None
    else:
        decision, scope = 'not-found', None  # transitive_check.py looks at these next
    return {
        'dependency': finding['dependency'],
        'vulnerable_version': finding['vulnerable_version'],
        'fixed_version': finding['fixed_version'],
        'advisories': finding.get('advisories') or [a for a in [finding.get('advisory')] if a],
        'images': finding.get('images', []),
        'decision': decision, 'scope': scope, 'owners': owners,
        'changes': [{'repo': h['repo'], 'file': h['file'], 'line': h['line'], 'key': h.get('key'),
                     'match_type': h['match_type'], 'old': finding['vulnerable_version'],
                     'new': finding['fixed_version'], 'dependency': finding['dependency'],
                     'is_reference': h['is_reference']} for h in changes],
        'review': [{'repo': h['repo'], 'file': h['file'], 'line': h['line'], 'key': h.get('key')} for h in review],
    }


def skipped(finding):
    return {
        'dependency': finding['dependency'] or finding.get('source_line', '?'),
        'vulnerable_version': finding['vulnerable_version'], 'fixed_version': finding['fixed_version'],
        'advisories': finding.get('advisories', []), 'images': finding.get('images', []),
        'decision': 'out-of-scope', 'scope': None, 'owners': [], 'changes': [], 'review': [],
        'reason': finding.get('reason'),
    }


def markdown(ticket, flow, rows):
    out = [f'## Vulnerability Upgrade ({ticket}, {flow} flow)', '',
           '| Dependency | Vulnerable | Fixed | Decision | Repo and file |', '| --- | --- | --- | --- | --- |']
    for row in rows:
        places = [f"{c['repo']}: `{c['file']}:{c['line']}`" for c in row['changes'] + row['review']]
        places += [f"{t['repo']} (via dependency graph)" for t in row.get('transitive', [])]
        decision = row['decision'] + (f" ({row['scope']})" if row['scope'] else '')
        out.append(f"| {row['dependency']} | {row['vulnerable_version']} | {row['fixed_version']} | "
                   f"{decision} | {'<br>'.join(places) or '-'} |")
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hits', required=True)
    parser.add_argument('--findings', required=True)
    parser.add_argument('--out', required=True, help='changes.json to write')
    parser.add_argument('--plan-md', help='Markdown section to merge into plan.md')
    parser.add_argument('--config')
    args = parser.parse_args()
    config = load_config(args.config)
    data, found = load_json(args.hits), load_json(args.findings)
    rows = []
    for finding in found['findings']:
        if finding['status'] == 'ok':
            rows.append(decide(finding, data['hits'], config['platform_repo']))
        elif finding['status'] == 'out-of-scope':
            rows.append(skipped(finding))
    changes = [c for row in rows for c in row['changes']]
    save_json(args.out, {'ticket': found['ticket'], 'flow': data['flow'], 'dependencies': rows, 'changes': changes})
    if args.plan_md:
        with open(args.plan_md, 'w', encoding='utf-8') as handle:
            handle.write(markdown(found['ticket'], data['flow'], rows))
    counts = {}
    for row in rows:
        counts[row['decision']] = counts.get(row['decision'], 0) + 1
    print(f"{len(changes)} change(s); decisions: {counts} -> {args.out}")


if __name__ == '__main__':
    raise SystemExit(main_wrapper(main))
