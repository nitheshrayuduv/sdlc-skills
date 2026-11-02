#!/usr/bin/env python3
"""Check Playwright test files against the playwright-expert must-do / must-not-do rules.

  check_playwright_rules.py <test files...> [--config playwright.config.ts]

Exit 1 when a failing rule is found; warnings alone exit 0. Standard library only.
"""
import argparse
import re
import sys
from pathlib import Path

CSS_CLASS = re.compile(r"""(?:locator|\$\$?|querySelector(?:All)?)\(\s*(['"`])\s*[^'"`]*\.[A-Za-z_][\w-]*""")
ROLE = re.compile(r'\bgetBy(?:Role|Label|Text|TestId|Placeholder|AltText|Title)\(')
ANY_LOCATOR = re.compile(r'\blocator\(|\bgetBy\w+\(')
FIRST_NTH = re.compile(r'\.(?:first|nth)\(')
COMMENT = re.compile(r'//|/\*')


def check_file(path):
    fails, warns = [], []
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    role = other = 0
    for i, line in enumerate(lines, 1):
        code = line.split('//', 1)[0]
        if 'waitForTimeout(' in code:
            fails.append(f'{path}:{i}: waitForTimeout() is forbidden; use auto-waiting or web-first assertions')
        if CSS_CLASS.search(code):
            fails.append(f'{path}:{i}: CSS-class selector; use role, label, text or test-id locators')
        if FIRST_NTH.search(code):
            prev = lines[i - 2] if i > 1 else ''
            if not (COMMENT.search(line) or COMMENT.search(prev)):
                fails.append(f'{path}:{i}: first()/nth() needs an adjacent comment giving the reason')
        role += len(ROLE.findall(code))
        other += len(ANY_LOCATOR.findall(code)) - len(ROLE.findall(code))
    total = role + other
    if total:
        ratio = role / total
        if ratio < 0.6:
            warns.append(f'{path}: only {ratio:.0%} of locators are role/label/text based (prefer role-based)')
    return fails, warns


def check_config(path):
    warns = []
    text = path.read_text(encoding='utf-8', errors='replace')
    if not re.search(r'trace\s*:\s*[\'"](?:on|retain-on-failure|on-first-retry)', text):
        warns.append(f'{path}: traces are not enabled on failure (use trace: "retain-on-failure")')
    if not re.search(r'screenshot\s*:\s*[\'"](?:on|only-on-failure)', text):
        warns.append(f'{path}: screenshots on failure are not enabled')
    if not re.search(r'fullyParallel\s*:\s*true', text):
        warns.append(f'{path}: fullyParallel is not true (parallel execution)')
    return warns


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--config', help='path to playwright.config.ts')
    args = ap.parse_args(argv)
    fails, warns = [], []
    for name in args.files:
        f, w = check_file(Path(name))
        fails += f
        warns += w
    if args.config:
        cfg = Path(args.config)
        if cfg.is_file():
            warns += check_config(cfg)
        else:
            warns.append(f'{cfg}: config not found')
    for line in fails:
        print('FAIL ' + line)
    for line in warns:
        print('WARN ' + line)
    if not fails:
        print(f'ok: {len(args.files)} file(s) pass the failing rules ({len(warns)} warning(s))')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
