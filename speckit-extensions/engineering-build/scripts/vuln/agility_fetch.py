#!/usr/bin/env python3
"""Read an Agility ticket and write the vulnerable and fixed versions it lists.

The ticket description holds a scanner report: one "IMAGE - name : VERSION/TAG - tag" heading per
image, then rows of CVE, severity, impacted package, version, fix version and file path. Free-text
lines such as "group:artifact 1.2.3 -> 1.2.4" are understood as a fallback.

The token is read from AGILITY_TOKEN and the server from AGILITY_URL (for example
https://<your-agility-host>/<instance>). Neither is ever written to a file or log.
"""
import argparse
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from common import VERSION, UpgradeError, compare_versions, main_wrapper, redact, save_json

GROUP_ARTIFACT = re.compile(r'\b([A-Za-z][\w.\-]*:[A-Za-z][\w.\-]*)\b')
ADVISORY = re.compile(r'\b(CVE-\d{4}-\d{4,}|GHSA(?:-[a-z0-9]{4}){3})\b', re.IGNORECASE)
FIXED = re.compile(r'(?:fixed(?:\s+(?:in|version))?|fix|patched(?:\s+in)?|upgrade\s+to|update\s+to|->|=>|→|\bto\b)\W*(' + VERSION + ')', re.IGNORECASE)
VULNERABLE = re.compile(r'(?:vulnerable|affected|current|installed|from)\W*(' + VERSION + ')', re.IGNORECASE)
TABLE_ROW = re.compile(r'^\s*(?:CVE-\d{4}-\d+|GHSA-[\w-]+)\b', re.IGNORECASE)
IMAGE = re.compile(r'IMAGE\s*-\s*(\S+)\s*:\s*VERSION/TAG\s*-\s*(\S+)', re.IGNORECASE)
REPORT_FLOW = re.compile(r'vulnerability\s+report\s+of\s+(\w+)', re.IGNORECASE)
SEVERITY_ORDER = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
ASSET_TYPES = ('Story', 'Defect', 'Issue')
OS_REASON = 'Operating-system package in the container image. Fix it by updating the base image, not Gradle.'


def to_text(raw):
    raw = re.sub(r'(?i)<br\s*/?>|</p>|</tr>|</li>|</div>', '\n', raw or '')
    raw = re.sub(r'(?i)</t[dh]>', '\t', raw)
    return html.unescape(re.sub(r'<[^>]+>', '', raw))


def classify(package, path):
    if (path or '').startswith('pkg:') or '@' in package:
        return 'os'
    if ':' in package:
        return 'maven'
    return 'unknown'


def parse_table(text):
    """Parse the scanner report. Rows for one package and version are merged across images and CVEs."""
    image, merged = None, {}
    for line in text.splitlines():
        heading = IMAGE.search(line)
        if heading:
            image = heading.group(1).split('/')[-1]
            continue
        if not TABLE_ROW.match(line):
            continue
        parts = [p.strip() for p in re.split(r'\t+|\s*\|\s*|\s{2,}', line.strip()) if p.strip()]
        if len(parts) < 5:
            continue
        cve, severity, package, version, fix = parts[:5]
        path = parts[5] if len(parts) > 5 else ''
        item = merged.setdefault((package, version), {
            'dependency': package, 'ecosystem': classify(package, path), 'vulnerable_version': version,
            'fix_candidates': set(), 'advisories': set(), 'severity': 'LOW', 'images': set(), 'paths': set()})
        item['fix_candidates'].add(fix)
        item['advisories'].add(cve.upper())
        if image:
            item['images'].add(image)
        if path:
            item['paths'].add(path)
        if severity.upper() in SEVERITY_ORDER and (
                SEVERITY_ORDER.index(severity.upper()) > SEVERITY_ORDER.index(item['severity'])):
            item['severity'] = severity.upper()
    findings = []
    for item in merged.values():
        candidates = sorted(item['fix_candidates'], key=compare_versions)
        advisories = sorted(item['advisories'])
        findings.append({
            'dependency': item['dependency'], 'ecosystem': item['ecosystem'],
            'vulnerable_version': item['vulnerable_version'],
            'fixed_version': candidates[-1],  # the highest fix covers every CVE for this package
            'fix_candidates': candidates, 'advisory': advisories[0], 'advisories': advisories,
            'severity': item['severity'], 'images': sorted(item['images']), 'paths': sorted(item['paths']),
            'status': {'maven': 'ok', 'os': 'out-of-scope'}.get(item['ecosystem'], 'needs-confirmation'),
            'reason': OS_REASON if item['ecosystem'] == 'os' else None,
        })
    return findings


def parse_line(line):
    versions = [m.group(0) for m in re.finditer(VERSION, line)]
    if not versions:
        return None
    found_fixed, found_vuln = FIXED.search(line), VULNERABLE.search(line)
    fixed = found_fixed.group(1) if found_fixed else None
    vulnerable = found_vuln.group(1) if found_vuln else None
    if vulnerable is None and fixed is None and len(versions) >= 2:
        vulnerable, fixed = versions[0], versions[1]
    elif vulnerable is None and fixed is not None:
        vulnerable = next((v for v in versions if v != fixed), None)
    elif vulnerable is None:
        vulnerable = versions[0]
    ga = GROUP_ARTIFACT.search(line)
    advisory = ADVISORY.search(line)
    status = 'ok' if ga and vulnerable and fixed and vulnerable != fixed else 'needs-confirmation'
    return {
        'dependency': ga.group(1) if ga else None, 'ecosystem': 'maven' if ga else 'unknown',
        'vulnerable_version': vulnerable, 'fixed_version': fixed,
        'advisory': advisory.group(1).upper() if advisory else None, 'status': status,
        'source_line': line.strip()[:300],
    }


def parse_findings(raw):
    text = to_text(raw)
    table = parse_table(text)
    if table:
        return table
    found, seen = [], set()
    for line in text.splitlines():
        item = parse_line(line)
        key = item and (item['dependency'], item['vulnerable_version'], item['fixed_version'])
        if item and key not in seen:
            seen.add(key)
            found.append(item)
    return found


def flow_hint(raw):
    match = REPORT_FLOW.search(to_text(raw))
    """The flow named in the report header, lower-cased; a hint only, checked against the config by intake."""
    return match.group(1).lower() if match else None


def fetch_ticket(ticket):
    token, base = os.environ.get('AGILITY_TOKEN'), os.environ.get('AGILITY_URL')
    if not token or not base:
        raise UpgradeError('Set AGILITY_TOKEN and AGILITY_URL before reading a ticket.', 2)
    for asset in ASSET_TYPES:
        query = urllib.parse.urlencode({'where': f"Number='{ticket}'", 'sel': 'Name,Description'})
        request = urllib.request.Request(
            f"{base.rstrip('/')}/rest-1.v1/Data/{asset}?{query}",
            headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.load(response)
        except urllib.error.HTTPError as err:
            raise UpgradeError(f'Agility returned HTTP {err.code} for {ticket}.', 3)
        except (urllib.error.URLError, TimeoutError) as err:
            raise UpgradeError(redact(f'Could not reach Agility: {err}'), 3)
        assets = body.get('Assets') or []
        if assets:
            attrs = assets[0].get('Attributes', {})
            return {'type': asset, 'name': (attrs.get('Name') or {}).get('value') or '',
                    'description': (attrs.get('Description') or {}).get('value') or ''}
    raise UpgradeError(f'Ticket {ticket} was not found in Agility.', 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticket', required=True)
    parser.add_argument('--out', required=True, help='findings.json to write')
    parser.add_argument('--fixture', help='JSON file with name and description, used instead of calling Agility')
    args = parser.parse_args()
    if args.fixture:
        with open(args.fixture, encoding='utf-8') as handle:
            ticket = json.load(handle)
    else:
        ticket = fetch_ticket(args.ticket)
    body = ticket.get('name', '') + '\n' + ticket.get('description', '')
    findings = parse_findings(body)
    save_json(args.out, {'ticket': args.ticket, 'title': ticket.get('name', ''),
                         'flow_hint': flow_hint(body), 'findings': findings})
    counts = {}
    for finding in findings:
        counts[finding['status']] = counts.get(finding['status'], 0) + 1
    print(f'{len(findings)} finding(s) {counts} -> {args.out}')
    if not findings:
        raise UpgradeError('No vulnerable and fixed versions were found in the ticket.', 4)


if __name__ == '__main__':
    raise SystemExit(main_wrapper(main))
