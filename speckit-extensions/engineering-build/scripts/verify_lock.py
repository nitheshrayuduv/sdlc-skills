#!/usr/bin/env python3
"""Verify (or regenerate) skills.lock.yml for the vendored skills. Standard library only.

  verify_lock.py --ext <extension dir>                      exit 0 ok, 3 on drift
  verify_lock.py --ext <extension dir> --update             rewrite sha256 values in the lock
  verify_lock.py --ext <extension dir> --skills <skills dir> check a source checkout

Skills live in <extension dir>/skills/ once installed. In the source repository they
live in the top-level skills/ folder; the installer copies the locked ones in.
The hash covers every file in skills/<id>/ (sorted paths, CRLF normalised to LF),
so a checkout with autocrlf produces the same digest.
"""
import argparse
import hashlib
import sys
from pathlib import Path


def skill_digest(skill_dir):
    outer = hashlib.sha256()
    for path in sorted(p for p in skill_dir.rglob('*') if p.is_file()):
        rel = path.relative_to(skill_dir).as_posix()
        data = path.read_bytes().replace(b'\r\n', b'\n')
        outer.update(rel.encode() + b'\0' + hashlib.sha256(data).hexdigest().encode() + b'\n')
    return outer.hexdigest()


def read_lock(text):
    """Parse the fixed, flat shape of skills.lock.yml without PyYAML."""
    skills, cur = [], None
    for raw in text.splitlines():
        line = raw.split('#', 1)[0].rstrip() if not raw.lstrip().startswith('- ') else raw.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith('- '):
            cur = {}
            skills.append(cur)
            stripped = stripped[2:]
        if cur is None or ':' not in stripped:
            continue
        key, _, value = stripped.partition(':')
        cur[key.strip()] = value.strip().strip('"')
    return [s for s in skills if 'id' in s]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ext', required=True, help='extension directory (contains skills.lock.yml)')
    ap.add_argument('--skills', help='directory holding the skill folders (default: <ext>/skills)')
    ap.add_argument('--update', action='store_true', help='recompute and write sha256 values')
    args = ap.parse_args(argv)
    ext = Path(args.ext)
    skills_root = Path(args.skills) if args.skills else ext / 'skills'
    lock_path = ext / 'skills.lock.yml'
    text = lock_path.read_text(encoding='utf-8')
    entries = read_lock(text)
    if not entries:
        print('skills.lock.yml lists no skills', file=sys.stderr)
        return 3
    bad = []
    for entry in entries:
        skill_dir = skills_root / entry['id']
        if not skill_dir.is_dir():
            bad.append(f"{entry['id']}: missing directory")
            continue
        if entry.get('license') != 'internal' and not (skill_dir / 'LICENSE').is_file():
            bad.append(f"{entry['id']}: license notice missing")
        digest = skill_digest(skill_dir)
        if args.update:
            old = entry.get('sha256', '')
            text = text.replace(f'sha256: {old}', f'sha256: {digest}', 1) if old else text
            continue
        if digest != entry.get('sha256'):
            bad.append(f"{entry['id']}: hash drift (lock {entry.get('sha256','')[:12]}, actual {digest[:12]})")
    if args.update:
        lock_path.write_text(text, encoding='utf-8')
        print('lock updated')
        return 0
    for line in bad:
        print('FAIL ' + line, file=sys.stderr)
    if bad:
        return 3
    print(f'ok: {len(entries)} vendored skills match skills.lock.yml')
    return 0


if __name__ == '__main__':
    sys.exit(main())
