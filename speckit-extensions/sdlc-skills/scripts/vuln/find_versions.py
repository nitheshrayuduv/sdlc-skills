#!/usr/bin/env python3
"""Find where each vulnerable version is declared in the repos of a flow."""
import argparse
import fnmatch
import os
import re
from pathlib import Path

from common import (SKIP_DIRS, UpgradeError, VERSION, flow_repos, load_config, load_json, main_wrapper,
                    repo_dir, resolve_workspace, save_json, version_pattern)

MAX_BYTES = 2_000_000
PROPERTY = re.compile(r'^\s*([\w.\-]+)\s*[=:]\s*["\']?(' + VERSION + r')["\']?\s*(?:#.*)?$')


def candidate_files(root, patterns):
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            path = Path(folder) / name
            if any(fnmatch.fnmatch(name, p) for p in patterns) and path.stat().st_size <= MAX_BYTES:
                yield path


def read_lines(path):
    return path.read_text(encoding='utf-8', errors='ignore').splitlines()


def artifact_of(dependency):
    return dependency.split(':')[-1]


def make_hit(repo, rel, number, text, finding, kind, config):
    return {
        'dependency': finding['dependency'],
        'vulnerable_version': finding['vulnerable_version'],
        'repo': repo, 'file': rel, 'line': number, 'text': text.strip()[:300],
        'match_type': kind,
        'is_reference': any(ref in rel for ref in config.get('reference_paths', [])),
    }


def scan_repo(repo, root, findings, config):
    files = {p: read_lines(p) for p in candidate_files(root, config['version_files'])}
    hits = []
    for finding in findings:
        art = artifact_of(finding['dependency'])
        vuln = version_pattern(finding['vulnerable_version'])
        token = re.sub(r'[^a-z0-9]', '', art.lower())
        referenced_keys = set()
        for path, lines in files.items():
            rel = path.relative_to(root).as_posix()
            for number, text in enumerate(lines, 1):
                if art.lower() not in text.lower():
                    continue
                if vuln.search(text):
                    hits.append(make_hit(repo, rel, number, text, finding, 'literal', config))
                elif re.search(VERSION, text):
                    hits.append(make_hit(repo, rel, number, text, finding, 'other_version', config))
                referenced_keys.update(re.findall(r'\$\{?([\w.\-]+)\}?', text))
        for path, lines in files.items():
            rel = path.relative_to(root).as_posix()
            for number, text in enumerate(lines, 1):
                match = PROPERTY.match(text)
                if not match or not vuln.search(match.group(2)):
                    continue
                key = match.group(1)
                if key in referenced_keys:
                    kind = 'property_definition'
                elif token and token in re.sub(r'[^a-z0-9]', '', key.lower()):
                    kind = 'property_candidate'
                else:
                    continue
                entry = make_hit(repo, rel, number, text, finding, kind, config)
                entry['key'] = key
                hits.append(entry)
    return hits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flow', required=True)
    parser.add_argument('--workspace')
    parser.add_argument('--findings', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--config')
    args = parser.parse_args()
    config = load_config(args.config)
    workspace = resolve_workspace(config, args.workspace)
    findings = [f for f in load_json(args.findings)['findings'] if f['status'] == 'ok']
    if not findings:
        raise UpgradeError('No confirmed findings to search for. Confirm the findings first.', 2)
    hits = []
    for repo in flow_repos(config, args.flow):
        hits.extend(scan_repo(repo, repo_dir(workspace, repo), findings, config))
    save_json(args.out, {'flow': args.flow, 'hits': hits})
    print(f'{len(hits)} match(es) -> {args.out}')


if __name__ == '__main__':
    raise SystemExit(main_wrapper(main))
