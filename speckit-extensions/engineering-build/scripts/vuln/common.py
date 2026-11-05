"""Shared helpers for the vulnerability upgrade scripts. Standard library only."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent.parent / 'config' / 'vuln-flows.json'
SKIP_DIRS = {'.git', '.gradle', 'build', 'out', 'node_modules', '.idea'}
VERSION = r'\d+(?:\.\d+)+(?:[.\-][A-Za-z0-9]+)*'


class UpgradeError(Exception):
    """A problem the user can act on. Printed without a traceback."""

    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def load_config(path=None):
    return load_json(path or DEFAULT_CONFIG)


def vuln_dir(feature_dir):
    path = Path(feature_dir).expanduser().resolve() / 'vuln'
    path.mkdir(parents=True, exist_ok=True)
    return path


def flow_repos(config, flow):
    if flow not in config.get('flows', {}):
        raise UpgradeError(f"Unknown flow '{flow}'. Choose one of: {', '.join(config.get('flows', {}))}.", 2)
    return list(config['flows'][flow]['repos'])


def resolve_workspace(config, explicit=None):
    """Where the flow's repos are checked out, side by side.

    --workspace wins. Otherwise workspace_root, when it holds the repos. Otherwise the folder above
    the project these scripts run in (the current folder, or the project the extension is installed
    in) when that project is itself a repo of a flow. So a fresh install
    finds its sibling repos without editing the config.
    """
    if explicit:
        return explicit
    configured = Path(config['workspace_root']).expanduser()
    names = {repo for flow in config.get('flows', {}).values() for repo in flow.get('repos', [])}
    if any((configured / name).is_dir() for name in names):
        return str(configured)
    installed_in = Path(__file__).resolve().parents[5] if len(Path(__file__).resolve().parents) > 5 else None
    for project in (Path.cwd(), installed_in):
        if project is not None and project.name in names and project.parent.is_dir():
            return str(project.parent)
    return str(configured)


def repo_dir(workspace, name):
    path = Path(workspace).expanduser().resolve() / name
    if not path.is_dir():
        raise UpgradeError(f'Repository folder not found: {path}', 2)
    return path


SECRET_VARS = ('GH_TOKEN', 'GITHUB_TOKEN')


def redact(text):
    """Mask token values from the environment in command output."""
    for name in SECRET_VARS:
        token = os.environ.get(name)
        if token and text:
            text = text.replace(token, '***')
    return text


def run(cmd, cwd, timeout=None):
    """Run a command without a shell. Returns (code, combined output)."""
    try:
        done = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                              errors='replace', timeout=timeout)
    except FileNotFoundError:
        return 127, f'Command not found: {cmd[0]}'
    except subprocess.TimeoutExpired:
        return 124, f'Timed out after {timeout}s: {" ".join(cmd)}'
    return done.returncode, redact((done.stdout or '') + (done.stderr or ''))


def version_pattern(version):
    """Match a version as a whole token, so 1.2.3 does not match 11.2.3 or 1.2.30."""
    return re.compile(r'(?<![\w.])' + re.escape(version) + r'(?![\w]|\.\d)')


def compare_versions(version):
    """Sort key: numeric parts first, so 5.36.1 sorts above 5.36.0 and 5.9."""
    return [int(n) for n in re.findall(r'\d+', version)]


def load_intake(directory):
    """intake.json holds the flow, ticket, branch and parent branch chosen at the start."""
    path = Path(directory) / 'intake.json'
    return load_json(path) if path.is_file() else {}


def main_wrapper(fn):
    """Run a script's main(); print user errors cleanly and return their exit code."""
    try:
        return fn() or 0
    except UpgradeError as err:
        print(f'error: {redact(str(err))}', file=sys.stderr)
        return err.code
