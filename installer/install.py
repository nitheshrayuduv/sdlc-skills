#!/usr/bin/env python3
"""Install the engineering-build extension, its preset and its skills into Spec Kit repositories.

  python installer/install.py install   --repo PATH [--source local|catalog|url|bundle] [--agent-skills DIR] ...
  python installer/install.py update    --repo PATH
  python installer/install.py verify    --repo PATH [--json]
  python installer/install.py status    --repo PATH
  python installer/install.py uninstall --repo PATH
  python installer/install.py package   [--output dist]

Spec Kit itself is installed separately (`specify init`). This script stages the extension
from speckit-extensions/engineering-build/ together with the skills its skills.lock.yml
names (copied from the top-level skills/ folder), then drives the `specify` CLI to add the
extension and the preset. It never copies into Spec Kit's registries itself.
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

EXT_ID, PRESET_ID = 'engineering-build', 'engineering-build-preset'
OLD_IDS = (('extension', 'engineering-plan'), ('extension', 'sdlc-skills'), ('preset', 'org-sdlc'))
MIN_SPECIFY = (1, 2, 0)
MIN_PYTHON = (3, 8)
CORE_COMMANDS = ('speckit.clarify', 'speckit.plan', 'speckit.tasks', 'speckit.implement')
REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_EXT = REPO_ROOT / 'speckit-extensions' / EXT_ID
LOCAL_PRESET = LOCAL_EXT / 'preset'
LOCAL_SKILLS = REPO_ROOT / 'skills'
CONFIG_NAME = EXT_ID + '-config.yml'
STAGE_IGNORE = ('preset', 'tests', 'docs', '__pycache__', '*.pyc', '.extensionignore')
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
            with open(self.repo / '.specify' / (EXT_ID + '-install.log'), 'a', encoding='utf-8') as fh:
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
    for kind, ident in OLD_IDS:
        if installed(ctx, specify, kind, ident):
            ctx.log(f'warning: older {kind} {ident!r} is installed; remove it so it does not run next to {EXT_ID} '
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


def verify_lock(ext_dir, skills_dir=None):
    script = Path(ext_dir) / 'scripts' / 'verify_lock.py'
    cmd = [sys.executable, '-B', str(script), '--ext', str(ext_dir)] + (['--skills', str(skills_dir)] if skills_dir else [])
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode:
        raise InstallError('vendored skill integrity check failed:\n' + res.stderr, INTEGRITY)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def locked_skill_ids(ext_dir):
    text = (Path(ext_dir) / 'skills.lock.yml').read_text(encoding='utf-8')
    return re.findall(r'^\s*-\s+id:\s*(\S+)', text, re.M)


def stage_extension(ext_src, skills_src, dest):
    """Copy the extension source plus every skill its lock names into dest, then verify the lock."""
    ext_src, skills_src, dest = Path(ext_src), Path(skills_src), Path(dest)
    if not (ext_src / 'extension.yml').is_file():
        raise InstallError(f'no extension.yml in {ext_src}', PREFLIGHT)
    verify_lock(ext_src, skills_src)
    shutil.copytree(ext_src, dest, ignore=shutil.ignore_patterns(*STAGE_IGNORE))
    for ident in locked_skill_ids(ext_src):
        shutil.copytree(skills_src / ident, dest / 'skills' / ident, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    verify_lock(dest)
    return dest


def source_paths(local_path=None):
    """(extension, preset, skills) source folders in an sdlc-skills checkout."""
    base = Path(local_path).resolve() if local_path else REPO_ROOT
    ext = base / 'speckit-extensions' / EXT_ID
    return ext, ext / 'preset', base / 'skills'


def locate_sources(ctx, workdir):
    """Return (extension dir, preset dir) for the chosen --source, or (None, None) for catalog ids.

    A local source is staged into workdir first, so the installed extension carries its skills.
    """
    a = ctx.args
    if a.source == 'local':
        ext, preset, skills = source_paths(a.local_path)
        staged = stage_extension(ext, skills, Path(workdir) / EXT_ID)
        ctx.log(f'staged {EXT_ID} with skills: {", ".join(locked_skill_ids(ext))}')
        return staged, preset
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
        found = list(dest.rglob('extension.yml')) if dest.exists() else []
        pfound = list(dest.rglob('preset.yml')) if dest.exists() else []
        if not ctx.dry and (not found or not pfound):
            raise InstallError('archive must contain extension.yml and preset.yml', INTEGRITY)
        ext_dir = found[0].parent if found else dest / EXT_ID
        if not ctx.dry and not (ext_dir / 'skills').is_dir():
            raise InstallError('archive extension has no skills/ folder; build it with `install.py package`', INTEGRITY)
        return ext_dir, (pfound[0].parent if pfound else dest / PRESET_ID)
    return None, None  # catalog: install by id


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


# The shipped vuln-flows.json is a neutral example. Real repo chains and hand-overs belong to
# the project, so update keeps them; --flows-config installs them from a private file.
PRESERVED_FLOW_KEYS = ('workspace_root', 'branch_prefix', 'build', 'repo_overrides', 'base_branch',
                       'platform_repo', 'reference_paths', 'handoff', 'flows')


def flow_config_path(ctx):
    return ctx.repo / '.specify' / 'extensions' / EXT_ID / 'config' / 'vuln-flows.json'


def merge_flow_settings(fresh, saved):
    """Keep the project's own flow settings (including repo chains and hand-overs); take new default keys from the release."""
    merged = dict(fresh)
    for key in PRESERVED_FLOW_KEYS:
        if key not in saved:
            continue
        if isinstance(saved[key], dict) and isinstance(fresh.get(key), dict):
            merged[key] = {**fresh[key], **saved[key]}
        else:
            merged[key] = saved[key]
    return merged


def read_flow_settings(ctx):
    path = flow_config_path(ctx)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except ValueError:
        return None


def read_private_flows(ctx):
    """Load --flows-config, the team's own vuln-flows.json kept outside version control."""
    if not ctx.args.flows_config:
        return None
    path = Path(ctx.args.flows_config).expanduser()
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise InstallError(f'--flows-config {path}: {exc}', PREFLIGHT)


def restore_flow_settings(ctx, saved, private=None):
    path = flow_config_path(ctx)
    if (saved is None and private is None) or ctx.dry or not path.is_file():
        if private is not None and ctx.dry:
            ctx.log(f'would apply flow settings from {ctx.args.flows_config}')
        return
    merged = json.loads(path.read_text(encoding='utf-8'))
    if saved is not None:
        merged = merge_flow_settings(merged, saved)
        ctx.log('kept this project\'s flow settings in ' + str(path) + ' (' + ', '.join(PRESERVED_FLOW_KEYS) + ')')
    if private is not None:
        merged = {**merged, **private}
        ctx.log(f'applied flow settings from {ctx.args.flows_config}')
    path.write_text(json.dumps(merged, indent=2) + '\n', encoding='utf-8')


def bootstrap_config(ctx, ext_dir):
    """Copy the template to the project config only if absent; apply --profile and --set."""
    cfg_dir = ctx.repo / '.specify' / 'extensions' / EXT_ID
    cfg = cfg_dir / CONFIG_NAME
    template = (Path(ext_dir) / 'config' / (EXT_ID + '-config.template.yml')) if ext_dir else None
    if cfg.exists():
        ctx.log('config exists, left untouched: ' + str(cfg))
        return
    if ctx.dry:
        ctx.log(f'would create {cfg}')
        return
    if template is None or not template.is_file():
        template = cfg_dir / 'config' / (EXT_ID + '-config.template.yml')
    text = template.read_text(encoding='utf-8')
    if ctx.args.profile == 'strict':
        text = re.sub(r'required:\s*false', 'required: true', text, count=1)
    for item in ctx.args.set or []:
        key, _, value = item.partition('=')
        if not key or not _:
            raise InstallError(f'--set expects key=value, got {item!r}', PREFLIGHT)
        pattern = re.compile(rf'^(\s*{re.escape(key.split(".")[-1])}\s*:\s*).*$', re.M)
        if not pattern.search(text):
            raise InstallError(f'--set {key}: key not found in config template', PREFLIGHT)
        text = pattern.sub(lambda m: m.group(1) + value, text, count=1)
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg.write_text(text, encoding='utf-8')
    ctx.log(f'config written ({ctx.args.profile} profile): {cfg}')


def install_agent_skills(ctx):
    """Copy the skills into an agent skills folder (for example .claude/skills) for direct use."""
    if not ctx.args.agent_skills:
        return
    if ctx.args.source != 'local':
        ctx.log('warning: --agent-skills needs --source local; skipped')
        return
    _, _, skills = source_paths(ctx.args.local_path)
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


def post_checks(ctx, specify):
    if ctx.dry:
        return
    if not installed(ctx, specify, 'extension', EXT_ID):
        raise InstallError('post-install check failed: extension not listed')
    if not installed(ctx, specify, 'preset', PRESET_ID):
        raise InstallError('post-install check failed: preset not listed')
    for name in CORE_COMMANDS:
        out = ctx.run([specify, 'preset', 'resolve', name], mutate=False)
        if PRESET_ID not in out.replace('\\', '/').replace('\n', ''):
            raise InstallError(f'post-install check failed: {name} does not resolve to the {PRESET_ID} preset')
    ctx.log('post-install checks passed')


def cmd_install(ctx, specify, update=False):
    preflight(ctx, specify)
    ext_ok = installed(ctx, specify, 'extension', EXT_ID)
    preset_ok = installed(ctx, specify, 'preset', PRESET_ID)
    if ext_ok and preset_ok and not update:
        ctx.log('already installed')
        return {'status': 'already installed'}
    with tempfile.TemporaryDirectory(prefix=EXT_ID + '-install-') as work:
        ext_src, preset_src = locate_sources(ctx, work)
        if ext_src is not None and (ext_src / 'skills.lock.yml').is_file():
            verify_lock(ext_src)
            ctx.log('skill lock verified (before)')
        backup = backup_registries(ctx)
        saved_flow = read_flow_settings(ctx) if update else None
        private_flow = read_private_flows(ctx)
        try:
            ext_cmd = [specify, 'extension', 'add'] + ([str(ext_src), '--dev'] if ext_src else [EXT_ID])
            preset_cmd = [specify, 'preset', 'add'] + (['--dev', str(preset_src)] if preset_src else [PRESET_ID])
            if ctx.args.source == 'catalog' and ctx.args.version:
                ext_cmd += ['--version', ctx.args.version]
                preset_cmd += ['--version', ctx.args.version]
            if update:
                ext_cmd.append('--force')
                if preset_ok:
                    ctx.run([specify, 'preset', 'remove', PRESET_ID])
            if not ext_ok or update:
                ctx.run(ext_cmd)
            ctx.run(preset_cmd + ['--priority', str(ctx.args.priority)])
            if ctx.args.inject_failure == 'after-extension':
                raise InstallError('injected failure after extension add')
            restore_flow_settings(ctx, saved_flow, private_flow)
            bootstrap_config(ctx, ext_src)
            installed_ext = ctx.repo / '.specify' / 'extensions' / EXT_ID
            if not ctx.dry and installed_ext.is_dir():
                verify_lock(installed_ext)
                ctx.log('skill lock verified (after)')
            post_checks(ctx, specify)
            install_agent_skills(ctx)
        except InstallError as exc:
            if not ctx.dry:
                # Remove what this run added while it is still registered, then restore the registries.
                if not preset_ok or update:
                    subprocess.run([specify, 'preset', 'remove', PRESET_ID], cwd=ctx.repo, capture_output=True, text=True, stdin=subprocess.DEVNULL)
                if not ext_ok:
                    subprocess.run([specify, 'extension', 'remove', EXT_ID, '--force'], cwd=ctx.repo, capture_output=True, text=True, stdin=subprocess.DEVNULL)
                restore_registries(ctx, backup)
            raise exc
    ctx.log('done. Restart your AI agent if the new commands do not appear.')
    return {'status': 'updated' if update else 'installed'}


def cmd_verify(ctx, specify):
    preflight(ctx, specify)
    problems = []
    if not installed(ctx, specify, 'extension', EXT_ID):
        problems.append('extension not installed')
    if not installed(ctx, specify, 'preset', PRESET_ID):
        problems.append('preset not installed')
    ext_dir = ctx.repo / '.specify' / 'extensions' / EXT_ID
    if ext_dir.is_dir():
        try:
            verify_lock(ext_dir)
        except InstallError as exc:
            raise InstallError(str(exc), INTEGRITY)
        cfg = ext_dir / CONFIG_NAME
        template = ext_dir / 'config' / (EXT_ID + '-config.template.yml')
        locked = locked_ids(template)
        if cfg.is_file():
            for ident in locked:
                if binding_disabled(cfg.read_text(encoding='utf-8'), ident):
                    problems.append(f'locked binding {ident} is disabled')
    if problems:
        raise InstallError('; '.join(problems))
    ctx.log('verify ok')
    return {'status': 'ok'}


def _binding_blocks(text):
    blocks = re.split(r'(?m)^\s*-\s+id:\s*', text)[1:]
    return {b.split()[0].strip('"'): b for b in blocks if b.strip()}


def locked_ids(template):
    if not Path(template).is_file():
        return []
    return [i for i, b in _binding_blocks(Path(template).read_text(encoding='utf-8')).items()
            if re.search(r'locked:\s*true', b)]


def binding_disabled(text, ident):
    block = _binding_blocks(text).get(ident)
    return bool(block and re.search(r'enabled:\s*false', block))


def cmd_status(ctx, specify):
    preflight(ctx, specify)
    info = {'extension': installed(ctx, specify, 'extension', EXT_ID), 'preset': installed(ctx, specify, 'preset', PRESET_ID)}
    ctx.log(f'extension {EXT_ID}: {"installed" if info["extension"] else "absent"}; '
            f'preset {PRESET_ID}: {"installed" if info["preset"] else "absent"}')
    return info


def cmd_uninstall(ctx, specify):
    preflight(ctx, specify)
    backup = backup_registries(ctx)
    try:
        if installed(ctx, specify, 'preset', PRESET_ID):
            ctx.run([specify, 'preset', 'remove', PRESET_ID])
        if installed(ctx, specify, 'extension', EXT_ID):
            ctx.run([specify, 'extension', 'remove', EXT_ID, '--force', '--keep-config'])
    except InstallError:
        if not ctx.dry:
            restore_registries(ctx, backup)
        raise
    return {'status': 'uninstalled'}


def cmd_package(args):
    """Build one zip holding the staged extension (with its skills) and the preset, plus its SHA-256."""
    ext, preset, skills = source_paths(args.local_path)
    version = re.search(r'^\s+version:\s*"?([\d.]+)', (ext / 'extension.yml').read_text(encoding='utf-8'), re.M).group(1)
    out_dir = Path(args.output).resolve()
    archive = out_dir / f'{EXT_ID}-{version}.zip'
    if archive.exists():
        raise InstallError(f'{archive} already exists; use a new --output or version')
    with tempfile.TemporaryDirectory(prefix=EXT_ID + '-package-') as work:
        root = Path(work)
        stage_extension(ext, skills, root / EXT_ID)
        shutil.copytree(preset, root / PRESET_ID, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
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
    ap.add_argument('--repo', help='Spec Kit project to change')
    ap.add_argument('--repos-file', help='file with one repo path per line (bulk mode)')
    ap.add_argument('--source', choices=['local', 'catalog', 'url', 'bundle'], default='local')
    ap.add_argument('--local-path', help='sdlc-skills checkout to install from (default: this checkout)')
    ap.add_argument('--url'), ap.add_argument('--sha256'), ap.add_argument('--bundle')
    ap.add_argument('--version', help='exact catalog release to install')
    ap.add_argument('--priority', type=int, default=5, help='preset priority (lower wins), default 5')
    ap.add_argument('--profile', choices=['default', 'strict'], default='default')
    ap.add_argument('--set', action='append', metavar='key=value', help='override a config value')
    ap.add_argument('--agent-skills', metavar='DIR', help='also copy the skills into this agent skills folder, relative to the repo (for example .claude/skills)')
    ap.add_argument('--flows-config', metavar='FILE', help="your team's vuln-flows.json (real repo chains), kept outside git; overlays the shipped example")
    ap.add_argument('--output', default='dist', help='package: output folder (default dist)')
    ap.add_argument('--specify', help='path to the specify executable')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--inject-failure', choices=['after-extension'], help=argparse.SUPPRESS)
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
    elif args.repo:
        repos = [args.repo]
    else:
        build_parser().error('--repo or --repos-file is required')
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
