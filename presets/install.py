#!/usr/bin/env python3
"""Install the engineering-build preset and its skills into Spec Kit repositories.

Run from the root of the repository to change (or pass --repo PATH), with sdlc-skills cloned next to it:

  python ../sdlc-skills/presets/install.py install   [--repo PATH] [--source local|catalog|url|bundle] [--agent-skills DIR] ...
  python ../sdlc-skills/presets/install.py update    [--repo PATH]
  python ../sdlc-skills/presets/install.py verify    [--repo PATH] [--json]
  python ../sdlc-skills/presets/install.py status    [--repo PATH]
  python ../sdlc-skills/presets/install.py uninstall [--repo PATH]
  python presets/install.py package   [--output dist]     (inside sdlc-skills)

Spec Kit itself is installed separately (`specify init`). The preset's skills live in the
top-level skills/ folder, not inside the preset, so this script stages
presets/engineering-build/ together with the skills its skills.lock.yml names,
checks every hash, then runs `specify preset add --dev <staged>`. It never writes Spec Kit's
registries itself. An older install that used the engineering-build extension is removed first.
Standard library only. Exit codes: 0 success, 1 failure, 2 preflight failure, 3 integrity failure.
"""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

PRESET_ID = 'engineering-build'
# Earlier releases shipped an extension plus a second preset; install and update remove them.
OUR_OLD = (('preset', 'engineering-build-preset'), ('extension', 'engineering-build'))
OLD_CONFIG = Path('extensions') / 'engineering-build' / 'engineering-build-config.yml'
LEGACY = (('extension', 'engineering-plan'), ('extension', 'sdlc-skills'), ('preset', 'org-sdlc'))
MIN_SPECIFY = (1, 2, 0)
MIN_PYTHON = (3, 8)
CORE_COMMANDS = ('speckit.constitution', 'speckit.specify', 'speckit.clarify',
                 'speckit.plan', 'speckit.tasks', 'speckit.implement')
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_NAME = PRESET_ID + '.yml'  # project overrides, in .specify/ so updates never replace them
STAGE_IGNORE = ('tests', 'docs', '__pycache__', '*.pyc', '.presetignore')
OK, FAIL, PREFLIGHT, INTEGRITY = 0, 1, 2, 3


class InstallError(Exception):
    def __init__(self, message, code=FAIL):
        super().__init__(message)
        self.code = code


class Ctx:
    """Per-repo run context: dry-run, logging and the machine-readable event list."""

    def __init__(self, args, repo):
        self.args, self.repo = args, Path(repo).resolve()
        self.dry = args.dry_run
        self.events = []

    def log(self, msg):
        self.events.append(msg)
        if not self.args.json:
            print(msg)
        if not self.dry and (self.repo / '.specify').is_dir():
            with open(self.repo / '.specify' / (PRESET_ID + '-install.log'), 'a', encoding='utf-8') as fh:
                fh.write(f'{datetime.datetime.now().isoformat(timespec="seconds")} {msg}\n')

    def run(self, cmd, mutate=True):
        """Run a command without a shell. Mutating commands are only printed in dry-run mode."""
        self.log('$ ' + ' '.join(str(c) for c in cmd) + ('   [dry-run, not executed]' if self.dry and mutate else ''))
        if self.dry and mutate:
            return ''
        res = subprocess.run([str(c) for c in cmd], cwd=self.repo, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if res.returncode:
            raise InstallError(f'command failed ({res.returncode}): {" ".join(map(str, cmd))}\n{res.stdout}{res.stderr}')
        return res.stdout


def parse_version(text):
    m = re.search(r'(\d+)\.(\d+)\.(\d+)', text)
    return tuple(int(x) for x in m.groups()) if m else None


def find_specify(args):
    exe = args.specify or shutil.which('specify')
    if not exe:
        raise InstallError('specify CLI not found on PATH (use --specify PATH)', PREFLIGHT)
    return exe


def git_state(repo):
    if not shutil.which('git') or not (repo / '.git').exists():
        return 'not a git repository'
    out = subprocess.run(['git', 'status', '--porcelain'], cwd=repo, capture_output=True, text=True).stdout
    return 'dirty' if out.strip() else 'clean'


def preflight(ctx, specify):
    if sys.version_info < MIN_PYTHON:
        raise InstallError(f'Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required', PREFLIGHT)
    if not (ctx.repo / '.specify').is_dir():
        raise InstallError(f'{ctx.repo} has no .specify/ folder; run `specify init` first', PREFLIGHT)
    out = subprocess.run([specify, '--version'], capture_output=True, text=True)
    ver = parse_version(out.stdout + out.stderr)
    if ver is None or ver < MIN_SPECIFY:
        raise InstallError(f'specify {".".join(map(str, MIN_SPECIFY))}+ required, found {ver}', PREFLIGHT)
    for kind, ident in LEGACY:
        if installed(ctx, specify, kind, ident):
            ctx.log(f'warning: older {kind} {ident!r} is installed; remove it so it does not run next to {PRESET_ID} '
                    f'(specify {kind} remove {ident})')
    state = git_state(ctx.repo)
    ctx.log(f'preflight ok: specify {".".join(map(str, ver))}, git tree {state}')
    if state == 'dirty':
        ctx.log('warning: git tree has uncommitted changes')


def list_json(ctx, specify, kind):
    out = ctx.run([specify, kind, 'list', '--json'], mutate=False)
    try:
        data = json.loads(out)
    except ValueError:
        return []
    return data if isinstance(data, list) else data.get(kind + 's', data.get('items', []))


def installed(ctx, specify, kind, ident):
    return any(isinstance(e, dict) and e.get('id') == ident for e in list_json(ctx, specify, kind))


def verify_lock(preset_dir, skills_dir=None):
    script = Path(preset_dir) / 'scripts' / 'verify_lock.py'
    cmd = [sys.executable, '-B', str(script), '--preset', str(preset_dir)] + (['--skills', str(skills_dir)] if skills_dir else [])
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode:
        raise InstallError('vendored skill integrity check failed:\n' + res.stderr, INTEGRITY)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def locked_skill_ids(preset_dir):
    text = (Path(preset_dir) / 'skills.lock.yml').read_text(encoding='utf-8')
    return re.findall(r'^\s*-\s+id:\s*(\S+)', text, re.M)


def stage_preset(preset_src, skills_src, dest):
    """Copy the preset source plus every skill its lock names into dest, then verify the lock."""
    preset_src, skills_src, dest = Path(preset_src), Path(skills_src), Path(dest)
    if not (preset_src / 'preset.yml').is_file():
        raise InstallError(f'no preset.yml in {preset_src}', PREFLIGHT)
    verify_lock(preset_src, skills_src)
    shutil.copytree(preset_src, dest, ignore=shutil.ignore_patterns(*STAGE_IGNORE))
    for ident in locked_skill_ids(preset_src):
        shutil.copytree(skills_src / ident, dest / 'skills' / ident, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    verify_lock(dest)
    return dest


def source_paths(local_path=None):
    """(preset, skills) source folders in an sdlc-skills checkout."""
    base = Path(local_path).resolve() if local_path else REPO_ROOT
    return base / 'presets' / PRESET_ID, base / 'skills'


def locate_source(ctx, workdir):
    """Return the staged preset folder for the chosen --source, or None to install a catalog id."""
    a = ctx.args
    if a.source == 'local':
        preset, skills = source_paths(a.local_path)
        staged = stage_preset(preset, skills, Path(workdir) / PRESET_ID)
        ctx.log(f'staged {PRESET_ID} with skills: {", ".join(locked_skill_ids(preset))}')
        return staged
    if a.source in ('url', 'bundle'):
        if a.source == 'url':
            if not a.url or not a.sha256:
                raise InstallError('--source url needs --url and --sha256', PREFLIGHT)
            archive = Path(workdir) / 'bundle.zip'
            ctx.log(f'downloading {a.url}')
            if not ctx.dry:
                urllib.request.urlretrieve(a.url, archive)
        else:
            if not a.bundle:
                raise InstallError('--source bundle needs --bundle FILE.zip', PREFLIGHT)
            archive = Path(a.bundle)
        if a.sha256 and not ctx.dry:
            if sha256_file(archive) != a.sha256.lower():
                raise InstallError('archive SHA-256 does not match --sha256', INTEGRITY)
            ctx.log('archive SHA-256 verified')
        dest = Path(workdir) / 'unpacked'
        if not ctx.dry:
            with zipfile.ZipFile(archive) as z:
                for name in z.namelist():
                    target = (dest / name).resolve()
                    if dest.resolve() not in target.parents and target != dest.resolve():
                        raise InstallError(f'unsafe path in archive: {name}', INTEGRITY)
                z.extractall(dest)
        found = list(dest.rglob('preset.yml')) if dest.exists() else []
        if not ctx.dry and not found:
            raise InstallError('archive must contain preset.yml', INTEGRITY)
        preset_dir = found[0].parent if found else dest / PRESET_ID
        if not ctx.dry and not (preset_dir / 'skills').is_dir():
            raise InstallError('archive preset has no skills/ folder; build it with `install.py package`', INTEGRITY)
        return preset_dir
    return None  # catalog: install by id


def backup_registries(ctx):
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    dest = ctx.repo / '.specify' / '.backup' / stamp
    sources = [ctx.repo / '.specify' / 'extensions' / '.registry', ctx.repo / '.specify' / 'extensions.yml',
               ctx.repo / '.specify' / 'presets' / '.registry']
    ctx.log(f'backup registries to {dest}')
    if ctx.dry:
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    for src in sources:
        if src.is_file():
            target = dest / src.relative_to(ctx.repo / '.specify')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
    return dest


def restore_registries(ctx, backup):
    ctx.log(f'restoring registries from {backup}')
    for src in backup.rglob('*'):
        if src.is_file():
            target = ctx.repo / '.specify' / src.relative_to(backup)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)


def remove_old_install(ctx, specify):
    """Remove the extension-based install of earlier releases, keeping its config as the project config."""
    found = [(kind, ident) for kind, ident in OUR_OLD if installed(ctx, specify, kind, ident)]
    if not found:
        return []
    old_cfg = ctx.repo / '.specify' / OLD_CONFIG
    new_cfg = ctx.repo / '.specify' / CONFIG_NAME
    if old_cfg.is_file() and not new_cfg.exists():
        ctx.log(f'moving the old binding config to {new_cfg}')
        if not ctx.dry:
            shutil.copy2(old_cfg, new_cfg)
    for kind, ident in found:
        ctx.log(f'removing the older {kind} {ident!r}; this release is a single preset')
        ctx.run([specify, kind, 'remove', ident] + (['--force', '--keep-config'] if kind == 'extension' else []))
    return found


def bootstrap_config(ctx, preset_dir):
    """Copy bindings.yml to the project config only if absent; apply --profile and --set."""
    cfg = ctx.repo / '.specify' / CONFIG_NAME
    if cfg.exists():
        ctx.log('config exists, left untouched: ' + str(cfg))
        return
    if ctx.dry:
        ctx.log(f'would create {cfg}')
        return
    template = Path(preset_dir) / 'bindings.yml' if preset_dir else None
    if template is None or not template.is_file():
        template = ctx.repo / '.specify' / 'presets' / PRESET_ID / 'bindings.yml'
    text = template.read_text(encoding='utf-8')
    text = text.replace('# Binding registry (shipped defaults).', '# Project binding settings, copied from the preset at install.', 1)
    if ctx.args.profile == 'strict':
        text = re.sub(r'required:\s*false', 'required: true', text, count=1)
    for item in ctx.args.set or []:
        key, _, value = item.partition('=')
        if not key or not _:
            raise InstallError(f'--set expects key=value, got {item!r}', PREFLIGHT)
        pattern = re.compile(rf'^(\s*{re.escape(key.split(".")[-1])}\s*:\s*).*$', re.M)
        if not pattern.search(text):
            raise InstallError(f'--set {key}: key not found in bindings.yml', PREFLIGHT)
        text = pattern.sub(lambda m: m.group(1) + value, text, count=1)
    cfg.write_text(text, encoding='utf-8')
    ctx.log(f'config written ({ctx.args.profile} profile): {cfg}')


def install_agent_skills(ctx):
    """Copy the skills into an agent skills folder (for example .claude/skills) for direct use."""
    if not ctx.args.agent_skills:
        return
    if ctx.args.source != 'local':
        ctx.log('warning: --agent-skills needs --source local; skipped')
        return
    _, skills = source_paths(ctx.args.local_path)
    target_root = Path(ctx.args.agent_skills)
    target_root = target_root if target_root.is_absolute() else ctx.repo / target_root
    for src in sorted(p for p in skills.iterdir() if p.is_dir()):
        target = target_root / src.name
        if target.exists() and ctx.args.command != 'update':
            ctx.log(f'agent skill exists, left untouched: {target}')
            continue
        ctx.log(f'agent skill {src.name} -> {target}' + ('   [dry-run, not copied]' if ctx.dry else ''))
        if not ctx.dry:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(src, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def unresolved_commands(ctx, specify):
    bad = []
    for name in CORE_COMMANDS:
        out = ctx.run([specify, 'preset', 'resolve', name], mutate=False)
        if ('presets/' + PRESET_ID + '/') not in out.replace('\\', '/').replace('\n', ''):
            bad.append(name)
    return bad


def post_checks(ctx, specify):
    if ctx.dry:
        return
    if not installed(ctx, specify, 'preset', PRESET_ID):
        raise InstallError('post-install check failed: preset not listed')
    bad = unresolved_commands(ctx, specify)
    if bad:
        raise InstallError(f'post-install check failed: {", ".join(bad)} do not resolve to the {PRESET_ID} preset')
    ctx.log('post-install checks passed')


def cmd_install(ctx, specify, update=False):
    preflight(ctx, specify)
    present = installed(ctx, specify, 'preset', PRESET_ID)
    old = [x for x in OUR_OLD if installed(ctx, specify, *x)]
    if present and not old and not update:
        ctx.log('already installed')
        return {'status': 'already installed'}
    with tempfile.TemporaryDirectory(prefix=PRESET_ID + '-install-') as work:
        preset_src = locate_source(ctx, work)
        backup = backup_registries(ctx)
        try:
            removed = remove_old_install(ctx, specify)
            if present:
                ctx.run([specify, 'preset', 'remove', PRESET_ID])
            cmd = [specify, 'preset', 'add'] + (['--dev', str(preset_src)] if preset_src else [PRESET_ID])
            if ctx.args.source == 'catalog' and ctx.args.version:
                cmd += ['--version', ctx.args.version]
            ctx.run(cmd + ['--priority', str(ctx.args.priority)])
            if ctx.args.inject_failure == 'after-preset':
                raise InstallError('injected failure after preset add')
            bootstrap_config(ctx, preset_src)
            installed_dir = ctx.repo / '.specify' / 'presets' / PRESET_ID
            if not ctx.dry and installed_dir.is_dir():
                verify_lock(installed_dir)
                ctx.log('skill lock verified (installed copy)')
            post_checks(ctx, specify)
            install_agent_skills(ctx)
        except InstallError as exc:
            if not ctx.dry:
                subprocess.run([specify, 'preset', 'remove', PRESET_ID], cwd=ctx.repo, capture_output=True, text=True, stdin=subprocess.DEVNULL)
                restore_registries(ctx, backup)
                if present or old:
                    ctx.log('the earlier install was removed before the failure; reinstall it from its own release')
            raise exc
    ctx.log('done. Restart your AI agent if the updated commands do not appear.')
    return {'status': 'updated' if (update or present or old) else 'installed'}


def cmd_verify(ctx, specify):
    preflight(ctx, specify)
    problems = []
    if not installed(ctx, specify, 'preset', PRESET_ID):
        problems.append('preset not installed')
    for kind, ident in OUR_OLD:
        if installed(ctx, specify, kind, ident):
            problems.append(f'older {kind} {ident} still installed; run update')
    preset_dir = ctx.repo / '.specify' / 'presets' / PRESET_ID
    if preset_dir.is_dir():
        try:
            verify_lock(preset_dir)
        except InstallError as exc:
            raise InstallError(str(exc), INTEGRITY)
        problems += [f'{name} does not resolve to the preset' for name in unresolved_commands(ctx, specify)]
        cfg = ctx.repo / '.specify' / CONFIG_NAME
        if cfg.is_file():
            for ident in locked_ids(preset_dir / 'bindings.yml'):
                if binding_disabled(cfg.read_text(encoding='utf-8'), ident):
                    problems.append(f'locked binding {ident} is disabled')
    if problems:
        raise InstallError('; '.join(problems))
    ctx.log('verify ok')
    return {'status': 'ok'}


def _binding_blocks(text):
    blocks = re.split(r'(?m)^\s*-\s+id:\s*', text)[1:]
    return {b.split()[0].strip('"'): b for b in blocks if b.strip()}


def locked_ids(registry):
    if not Path(registry).is_file():
        return []
    return [i for i, b in _binding_blocks(Path(registry).read_text(encoding='utf-8')).items()
            if re.search(r'locked:\s*true', b)]


def binding_disabled(text, ident):
    block = _binding_blocks(text).get(ident)
    return bool(block and re.search(r'enabled:\s*false', block))


def cmd_status(ctx, specify):
    preflight(ctx, specify)
    info = {'preset': installed(ctx, specify, 'preset', PRESET_ID),
            'older_install': [f'{k} {i}' for k, i in OUR_OLD if installed(ctx, specify, k, i)]}
    ctx.log(f'preset {PRESET_ID}: {"installed" if info["preset"] else "absent"}'
            + (f'; older install present: {", ".join(info["older_install"])}' if info['older_install'] else ''))
    return info


def cmd_uninstall(ctx, specify):
    preflight(ctx, specify)
    backup = backup_registries(ctx)
    try:
        if installed(ctx, specify, 'preset', PRESET_ID):
            ctx.run([specify, 'preset', 'remove', PRESET_ID])
    except InstallError:
        if not ctx.dry:
            restore_registries(ctx, backup)
        raise
    ctx.log(f'project settings in .specify/{CONFIG_NAME} were kept')
    return {'status': 'uninstalled'}


def cmd_package(args):
    """Build one zip holding the staged preset (with its skills), plus its SHA-256."""
    preset, skills = source_paths(args.local_path)
    version = re.search(r'^\s+version:\s*"?([\d.]+)', (preset / 'preset.yml').read_text(encoding='utf-8'), re.M).group(1)
    out_dir = Path(args.output).resolve()
    archive = out_dir / f'{PRESET_ID}-{version}.zip'
    if archive.exists():
        raise InstallError(f'{archive} already exists; use a new --output or version')
    with tempfile.TemporaryDirectory(prefix=PRESET_ID + '-package-') as work:
        root = Path(work)
        stage_preset(preset, skills, root / PRESET_ID)
        out_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for path in sorted(p for p in root.rglob('*') if p.is_file()):
                z.write(path, path.relative_to(root).as_posix())
    digest = sha256_file(archive)
    (out_dir / (archive.name + '.sha256')).write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    return {'archive': str(archive), 'sha256': digest, 'version': version}


def run_one(args, repo):
    ctx = Ctx(args, repo)
    try:
        specify = find_specify(args)
        fn = {'install': cmd_install, 'verify': cmd_verify, 'status': cmd_status, 'uninstall': cmd_uninstall}.get(args.command)
        result = cmd_install(ctx, specify, update=True) if args.command == 'update' else fn(ctx, specify)
        return {'repo': str(ctx.repo), 'code': OK, 'result': result, 'events': ctx.events}
    except InstallError as exc:
        ctx.log('error: ' + str(exc))
        return {'repo': str(ctx.repo), 'code': exc.code, 'error': str(exc), 'events': ctx.events}


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['install', 'update', 'verify', 'status', 'uninstall', 'package'])
    ap.add_argument('--repo', help='Spec Kit project to change (default: the current folder)')
    ap.add_argument('--repos-file', help='file with one repo path per line (bulk mode)')
    ap.add_argument('--source', choices=['local', 'catalog', 'url', 'bundle'], default='local')
    ap.add_argument('--local-path', help='sdlc-skills checkout to install from (default: this checkout)')
    ap.add_argument('--url'), ap.add_argument('--sha256'), ap.add_argument('--bundle')
    ap.add_argument('--version', help='exact catalog release to install')
    ap.add_argument('--priority', type=int, default=5, help='preset priority (lower wins), default 5')
    ap.add_argument('--profile', choices=['default', 'strict'], default='default')
    ap.add_argument('--set', action='append', metavar='key=value', help='override a setting in the new project config')
    ap.add_argument('--agent-skills', metavar='DIR', help='also copy the skills into this agent skills folder, relative to the repo (for example .claude/skills)')
    ap.add_argument('--output', default='dist', help='package: output folder (default dist)')
    ap.add_argument('--specify', help='path to the specify executable')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--inject-failure', choices=['after-preset'], help=argparse.SUPPRESS)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == 'package':
        try:
            result = cmd_package(args)
        except InstallError as exc:
            print('error: ' + str(exc), file=sys.stderr)
            return exc.code
        print(json.dumps(result, indent=2) if args.json else f"{result['archive']}\nsha256 {result['sha256']}")
        return OK
    if args.repos_file:
        repos = [l.strip() for l in Path(args.repos_file).read_text(encoding='utf-8').splitlines()
                 if l.strip() and not l.startswith('#')]
    else:
        repos = [args.repo or '.']  # default: the folder you run it from
    results = [run_one(args, r) for r in repos]
    if args.json:
        print(json.dumps(results, indent=2))
    elif len(results) > 1:
        print('\nrepo | result')
        for r in results:
            print(f"{r['repo']} | {'ok' if r['code'] == OK else 'exit ' + str(r['code'])}")
    return max(r['code'] for r in results)


if __name__ == '__main__':
    sys.exit(main())
