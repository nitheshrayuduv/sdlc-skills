#!/usr/bin/env python3
"""Read a vulnerability scanner report and write the vulnerable and fixed versions it lists.

Accepted inputs, detected automatically:
- Trivy JSON (`trivy image --format json`): Results[].Vulnerabilities[] with PkgName,
  InstalledVersion, FixedVersion, VulnerabilityID, Severity and PkgPath.
- A text or HTML table: optional "IMAGE - name : VERSION/TAG - tag" headings, then rows of
  advisory, severity, package, version, fix version and file path (tab, pipe or wide-space separated).
- Free text lines such as "group:artifact 1.2.3 -> 1.2.4" as a fallback.

The report is read from a local file only; nothing is fetched over the network.
"""
import argparse
import html
import json
import re
from pathlib import Path

from common import VERSION, UpgradeError, compare_versions, main_wrapper, save_json

GROUP_ARTIFACT = re.compile(r'\b([A-Za-z][\w.\-]*:[A-Za-z][\w.\-]*)\b')
ADVISORY = re.compile(r'\b(CVE-\d{4}-\d{4,}|GHSA(?:-[a-z0-9]{4}){3})\b', re.IGNORECASE)
FIXED = re.compile(r'(?:fixed(?:\s+(?:in|version))?|fix|patched(?:\s+in)?|upgrade\s+to|update\s+to|->|=>|→|\bto\b)\W*(' + VERSION + ')', re.IGNORECASE)
VULNERABLE = re.compile(r'(?:vulnerable|affected|current|installed|from)\W*(' + VERSION + ')', re.IGNORECASE)
TABLE_ROW = re.compile(r'^\s*(?:CVE-\d{4}-\d+|GHSA-[\w-]+)\b', re.IGNORECASE)
IMAGE = re.compile(r'IMAGE\s*-\s*(\S+)\s*:\s*VERSION/TAG\s*-\s*(\S+)', re.IGNORECASE)
SEVERITY_ORDER = ['UNKNOWN', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
LIBRARY_TYPES = ('jar', 'pom', 'gradle', 'gradle-lockfile', 'sbt')
OS_REASON = 'Operating-system package in the container image. Fix it by updating the base image, not the build.'


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


def add(merged, package, ecosystem, version, fix, advisory, severity, image, path):
    """Merge rows for one package and version across images and advisories."""
    item = merged.setdefault((package, version), {
        'dependency': package, 'ecosystem': ecosystem, 'vulnerable_version': version,
        'fix_candidates': set(), 'advisories': set(), 'severity': 'UNKNOWN', 'images': set(), 'paths': set()})
    for candidate in re.split(r'\s*,\s*', fix or ''):
        if candidate:
            item['fix_candidates'].add(candidate)
    if advisory:
        item['advisories'].add(advisory.upper())
    if image:
        item['images'].add(image)
    if path:
        item['paths'].add(path)
    severity = (severity or '').upper()
    if severity in SEVERITY_ORDER and SEVERITY_ORDER.index(severity) > SEVERITY_ORDER.index(item['severity']):
        item['severity'] = severity


def finish(merged):
    findings = []
    for item in merged.values():
        candidates = sorted(item['fix_candidates'], key=compare_versions)
        advisories = sorted(item['advisories'])
        if item['ecosystem'] == 'os':
            status = 'out-of-scope'
        elif item['ecosystem'] != 'unknown' and candidates:
            status = 'ok'
        else:
            status = 'needs-confirmation'
        findings.append({
            'dependency': item['dependency'], 'ecosystem': item['ecosystem'],
            'vulnerable_version': item['vulnerable_version'],
            'fixed_version': candidates[-1] if candidates else None,  # the highest fix covers every advisory
            'fix_candidates': candidates, 'advisory': advisories[0] if advisories else None,
            'advisories': advisories, 'severity': item['severity'], 'images': sorted(item['images']),
            'paths': sorted(item['paths']), 'status': status,
            'reason': OS_REASON if item['ecosystem'] == 'os' else None,
        })
    return findings


def parse_trivy(data):
    merged = {}
    for result in data.get('Results') or []:
        target = (result.get('Target') or '').split('/')[-1] or None
        os_packages = result.get('Class') == 'os-pkgs'
        for vuln in result.get('Vulnerabilities') or []:
            package = vuln.get('PkgName') or ''
            if os_packages:
                ecosystem = 'os'
            elif result.get('Type') in LIBRARY_TYPES or ':' in package:
                ecosystem = 'maven'  # group:artifact coordinates, used by Maven and Gradle alike
            else:
                ecosystem = result.get('Type') or 'unknown'  # npm, pip, gomod, ...
            add(merged, package, ecosystem, vuln.get('InstalledVersion'), vuln.get('FixedVersion'),
                vuln.get('VulnerabilityID'), vuln.get('Severity'), target, vuln.get('PkgPath'))
    return finish(merged)


def parse_table(text):
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
        advisory, severity, package, version, fix = parts[:5]
        path = parts[5] if len(parts) > 5 else ''
        add(merged, package, classify(package, path), version, fix, advisory, severity, image, path)
    return finish(merged)


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
    """Parse report text: Trivy JSON, else a table, else free-text lines."""
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if isinstance(data, dict) and 'Results' in data:
        return parse_trivy(data)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--report', required=True, action='append',
                        help='scanner report file (Trivy JSON, table or text); repeat for several')
    parser.add_argument('--ticket', required=True, help='ticket or reference id this fix is tracked under')
    parser.add_argument('--out', required=True, help='findings.json to write')
    args = parser.parse_args()
    findings, titles = [], []
    for name in args.report:
        path = Path(name)
        if not path.is_file():
            raise UpgradeError(f'Report file not found: {path}', 2)
        findings += parse_findings(path.read_text(encoding='utf-8', errors='replace'))
        titles.append(path.name)
    save_json(args.out, {'ticket': args.ticket, 'title': ', '.join(titles), 'findings': findings})
    counts = {}
    for finding in findings:
        counts[finding['status']] = counts.get(finding['status'], 0) + 1
    print(f'{len(findings)} finding(s) {counts} -> {args.out}')
    if not findings:
        raise UpgradeError('No vulnerable and fixed versions were found in the report.', 4)


if __name__ == '__main__':
    raise SystemExit(main_wrapper(main))
