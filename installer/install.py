#!/usr/bin/env python3
"""Install the sdlc-skills extension and org-sdlc preset into Spec Kit repositories.

  python installer/install.py install   --repo PATH [--source local|catalog|url|bundle] ...
  python installer/install.py update    --repo PATH
  python installer/install.py verify    --repo PATH [--json]
  python installer/install.py status    --repo PATH
  python installer/install.py uninstall --repo PATH

It drives the `specify` CLI and never copies into Spec Kit's registries itself.
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

EXT_ID, PRESET_ID = 'sdlc-skills', 'org-sdlc'
MIN_SPECIFY = (1, 2, 0)
MIN_PYTHON = (3, 8)
CORE_COMMANDS = ('speckit.clarify', 'speckit.plan', 'speckit.tasks', 'speckit.implement')
REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_EXT = REPO_ROOT / 'speckit-extensions' / EXT_ID
LOCAL_PRESET = REPO_ROOT / 'speckit-extensions' / PRESET_ID
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
            with open(self.repo / '.specify' / 'sdlc-skills-install.log', 'a', encoding='utf-8') as fh:
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


def verify_lock(ext_dir):
    script = Path(ext_dir) / 'scripts' / 'verify_lock.py'
    res = subprocess.run([sys.executable, '-B', str(script), '--ext', str(ext_dir)], capture_output=True, text=True)
    if res.returncode:
        raise InstallError('vendored skill integrity check failed:\n' + res.stderr, INTEGRITY)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def locate_sources(ctx, workdir):
    """Return (extension source, preset source) for the chosen --source, as local dirs or catalog ids."""
    a = ctx.args
    if a.source == 'local':
        base = Path(a.local_path).resolve() if a.local_path else None
        ext = (base / EXT_ID) if base else LOCAL_EXT
        preset = (base / PRESET_ID) if base else LOCAL_PRESET
        return ext, preset
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
        return (found[0].parent if found else dest / EXT_ID), (pfound[0].parent if pfound else dest / PRESET_ID)
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


# A project's own chains, hand-over rules and build settings survive an update. Mappings are merged
# (new default keys appear, the project's values win); everything else is taken from the project as is.
PRESERVED_FLOW_KEYS = ('workspace_root', 'branch_prefix', 'platform_repo', 'reference_paths', 'version_files',
                       'build', 'repo_overrides', 'base_branch', 'handoff', 'flows')
MERGED_FLOW_KEYS = ('build',)  # new build defaults appear; the project's own values win


def flow_config_path(ctx):
    return ctx.repo / '.specify' / 'extensions' / EXT_ID / 'config' / 'vuln-flows.json'


def merge_flow_settings(fresh, saved):
    """Keep the project's own flow settings; take only new keys and scripts' defaults from the release."""
    merged = dict(fresh)
    for key in PRESERVED_FLOW_KEYS:
        if key not in saved:
            continue
        if key in MERGED_FLOW_KEYS and isinstance(saved[key], dict) and isinstance(fresh.get(key), dict):
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


def restore_flow_settings(ctx, saved):
    path = flow_config_path(ctx)
    if saved is None or ctx.dry or not path.is_file():
        return
    merged = merge_flow_settings(json.loads(path.read_text(encoding='utf-8')), saved)
    path.write_text(json.dumps(merged, indent=2) + '\n', encoding='utf-8')
    ctx.log('kept this project\'s flow settings in ' + str(path) + ' (' + ', '.join(PRESERVED_FLOW_KEYS) + ')')


def bootstrap_config(ctx, ext_dir):
    """Copy the template to the project config only if absent; apply --profile and --set."""
    cfg_dir = ctx.repo / '.specify' / 'extensions' / EXT_ID
    cfg = cfg_dir / 'sdlc-skills-config.yml'
    template = (Path(ext_dir) / 'config' / 'sdlc-skills-config.template.yml') if ext_dir else None
    if cfg.exists():
        ctx.log('config exists, left untouched: ' + str(cfg))
        return
    if ctx.dry:
        ctx.log(f'would create {cfg}')
        return
    if template is None or not template.is_file():
        template = cfg_dir / 'config' / 'sdlc-skills-config.template.yml'
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
    with tempfile.TemporaryDirectory(prefix='sdlc-skills-install-') as work:
        ext_src, preset_src = locate_sources(ctx, work)
        if ext_src is not None:
            verify_lock(ext_src)
            ctx.log('vendored skill lock verified (before)')
        backup = backup_registries(ctx)
        saved_flow = read_flow_settings(ctx) if update else None
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
            restore_flow_settings(ctx, saved_flow)
            bootstrap_config(ctx, ext_src)
            installed_ext = ctx.repo / '.specify' / 'extensions' / EXT_ID
            if not ctx.dry and installed_ext.is_dir():
                verify_lock(installed_ext)
                ctx.log('vendored skill lock verified (after)')
            post_checks(ctx, specify)
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
        cfg = ext_dir / 'sdlc-skills-config.yml'
        template = ext_dir / 'config' / 'sdlc-skills-config.template.yml'
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
    ap.add_argument('command', choices=['install', 'update', 'verify', 'status', 'uninstall'])
    ap.add_argument('--repo', help='Spec Kit project to change')
    ap.add_argument('--repos-file', help='file with one repo path per line (bulk mode)')
    ap.add_argument('--source', choices=['local', 'catalog', 'url', 'bundle'], default='local')
    ap.add_argument('--local-path', help='directory holding sdlc-skills/ and org-sdlc/ (default: this checkout)')
    ap.add_argument('--url'), ap.add_argument('--sha256'), ap.add_argument('--bundle')
    ap.add_argument('--version', help='exact catalog release to install')
    ap.add_argument('--priority', type=int, default=5, help='preset priority (lower wins), default 5')
    ap.add_argument('--profile', choices=['default', 'strict'], default='default')
    ap.add_argument('--set', action='append', metavar='key=value', help='override a config value')
    ap.add_argument('--specify', help='path to the specify executable')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--inject-failure', choices=['after-extension'], help=argparse.SUPPRESS)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
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
