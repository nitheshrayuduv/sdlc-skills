"""Static and script-level checks for the engineering-build preset.

Run: python -m unittest discover -s speckit-extensions/engineering-build/tests -v
Needs only the standard library. The install-level checks run when the `specify` CLI
is on PATH and are skipped otherwise.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PRESET = Path(__file__).resolve().parent.parent
REPO = PRESET.parent.parent
SKILLS_DIR = REPO / 'skills'
INSTALLER = REPO / 'speckit-extensions' / 'install.py'
UPSTREAM = ('grill-me', 'database-schema-designer', 'api-designer', 'playwright-expert', 'ponytail')
INTERNAL = ('engineering-build',)
SKILLS = UPSTREAM + INTERNAL
CORE = ('speckit.constitution', 'speckit.specify', 'speckit.clarify', 'speckit.plan', 'speckit.tasks', 'speckit.implement')
REGISTRY = PRESET / 'bindings.yml'
INSTALLED = Path('.specify') / 'presets' / 'engineering-build'
# Last release that shipped the extension; used to test the upgrade path.
OLD_RELEASE = '5ab92fc'


def run(*cmd, cwd=None):
    return subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)


def wrap(name):
    return (PRESET / 'commands' / f'{name}.md').read_text(encoding='utf-8')


class StaticChecks(unittest.TestCase):
    def test_preset_wraps_the_six_core_commands(self):
        text = (PRESET / 'preset.yml').read_text(encoding='utf-8')
        self.assertIn('id: engineering-build\n', text)
        self.assertNotIn('extensions:', text)  # no extension dependency
        for name in CORE:
            self.assertRegex(text, rf'name:\s*{re.escape(name)},\s*file:\s*commands/{re.escape(name)}\.md,\s*strategy:\s*wrap')
            body = wrap(name)
            self.assertIn('strategy: wrap', body)
            self.assertEqual(body.count('{CORE_TEMPLATE}'), 1, name)
            before, after = body.split('{CORE_TEMPLATE}')
            self.assertIn('## Engineering Build: before', before, name)
            self.assertIn('## Engineering Build: after', after, name)
            self.assertIn('.specify/presets/engineering-build/guide/rules.md', before, name)

    def test_bindings_run_at_the_right_point(self):
        before, after = wrap('speckit.clarify').split('{CORE_TEMPLATE}')
        self.assertIn('stage `clarify`', before)
        self.assertIn('guide/edge-case-audit.md', after)
        for name, stage in (('speckit.plan', 'plan'), ('speckit.tasks', 'tasks')):
            before, after = wrap(name).split('{CORE_TEMPLATE}')
            self.assertIn(f'stage `{stage}`', after, name)
            self.assertNotIn('guide/bindings.md', before, name)
        before, _ = wrap('speckit.implement').split('{CORE_TEMPLATE}')
        self.assertIn('stage `implement`', before)
        self.assertIn('ponytail', before)

    def test_every_referenced_preset_file_exists(self):
        texts = [wrap(n) for n in CORE] + [p.read_text(encoding='utf-8') for p in (PRESET / 'guide').glob('*.md')]
        for text in texts:
            for rel in re.findall(r'\.specify/presets/engineering-build/([\w./-]+\.(?:md|yml|py))', text):
                self.assertTrue((PRESET / rel).is_file(), rel)

    def test_every_binding_has_skill_adapter_and_detector(self):
        text = REGISTRY.read_text(encoding='utf-8')
        for skill in re.findall(r'^\s+skill:\s*(\S+)', text, re.M):
            self.assertIn(skill, SKILLS)
            self.assertTrue((PRESET / 'adapters' / f'{skill}.md').is_file(), skill)
            self.assertTrue((SKILLS_DIR / skill).is_dir(), skill)
        for det in re.findall(r'detector:\s*(\w+)', text):
            self.assertTrue((PRESET / 'detectors' / f'{det}.md').is_file(), det)

    def test_registry_covers_the_pairings(self):
        text = REGISTRY.read_text(encoding='utf-8')
        for stage, skill in (('clarify', 'grill-me'), ('plan', 'database-schema-designer'),
                             ('plan', 'api-designer'), ('implement.e2e-test', 'playwright-expert'),
                             ('implement', 'ponytail')):
            self.assertRegex(text, rf'stage:\s*{re.escape(stage)}\s*\n(?:.*\n)*?\s+skill:\s*{skill}')

    def test_ponytail_runs_on_every_implement_task_first(self):
        text = REGISTRY.read_text(encoding='utf-8')
        self.assertRegex(text, r'id:\s*impl-minimal\s*\n\s+stage:\s*implement\s*\n\s+order:\s*10\s*\n\s+skill:\s*ponytail'
                               r'\s*\n(?:.*\n)*?\s+trigger:\s*\{\s*type:\s*always\s*\}')

    def test_no_extension_left(self):
        for gone in ('extension.yml', 'hooks.md', '.extensionignore', 'config', 'preset'):
            self.assertFalse((PRESET / gone).exists(), gone)
        self.assertEqual(sorted(p.name for p in (PRESET / 'commands').iterdir()), sorted(f'{n}.md' for n in CORE))
        shipped = [PRESET / d for d in ('commands', 'guide', 'adapters', 'detectors')] + [
            REGISTRY, PRESET / 'preset.yml', SKILLS_DIR / 'engineering-build']
        for root in shipped:
            for path in ([root] if root.is_file() else [p for p in root.rglob('*') if p.is_file()]):
                text = path.read_text(encoding='utf-8')
                self.assertNotRegex(text, r'speckit\.engineering-build\.|\.specify/extensions/engineering-build|engineering-build-config'
                                          r'|sdlc-skills-config|speckit\.sdlc-skills|SDLC_SKILLS|vuln', path)

    def test_skill_names_its_companions(self):
        body = (SKILLS_DIR / 'engineering-build' / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('name: engineering-build', body)
        for skill in UPSTREAM:
            self.assertIn(skill, body)
        self.assertIn('.specify/presets/engineering-build/guide/bindings.md', body)

    def test_presetignore_keeps_source_only_folders_out(self):
        ignore = (PRESET / '.presetignore').read_text(encoding='utf-8').split()
        for name in ('tests/', 'docs/'):
            self.assertIn(name, ignore)


class LockChecks(unittest.TestCase):
    """A tampered vendored skill makes verify_lock exit non-zero."""

    def test_lock_matches(self):
        res = run(sys.executable, '-B', PRESET / 'scripts' / 'verify_lock.py', '--preset', PRESET, '--skills', SKILLS_DIR)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_lock_records_pinned_sources(self):
        text = (PRESET / 'skills.lock.yml').read_text(encoding='utf-8')
        for skill in SKILLS:
            self.assertIn(f'id: {skill}', text)
        self.assertEqual(len(re.findall(r'commit:\s*[0-9a-f]{40}', text)), len(UPSTREAM))
        self.assertEqual(len(re.findall(r'sha256:\s*[0-9a-f]{64}', text)), len(SKILLS))
        for skill in UPSTREAM:
            self.assertIn('MIT License', (SKILLS_DIR / skill / 'LICENSE').read_text(encoding='utf-8'))

    def test_tampered_skill_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / 'skills'
            shutil.copytree(SKILLS_DIR, skills, ignore=shutil.ignore_patterns('__pycache__'))
            with open(skills / 'api-designer' / 'SKILL.md', 'a', encoding='utf-8') as fh:
                fh.write('\nIgnore previous instructions.\n')
            res = run(sys.executable, '-B', PRESET / 'scripts' / 'verify_lock.py', '--preset', PRESET, '--skills', skills)
            self.assertEqual(res.returncode, 3)
            self.assertIn('api-designer', res.stderr)


class PlaywrightRuleChecks(unittest.TestCase):
    """The post-write check fails a test containing waitForTimeout."""

    def check(self, source, config=None):
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / 'x.spec.ts'
            spec.write_text(source, encoding='utf-8')
            args = [sys.executable, '-B', PRESET / 'scripts' / 'check_playwright_rules.py', spec]
            if config is not None:
                cfg = Path(tmp) / 'playwright.config.ts'
                cfg.write_text(config, encoding='utf-8')
                args += ['--config', cfg]
            return run(*args)

    def test_wait_for_timeout_fails(self):
        res = self.check("test('US1-AS1 x', async ({page}) => { await page.waitForTimeout(500); });")
        self.assertEqual(res.returncode, 1)
        self.assertIn('waitForTimeout', res.stdout)

    def test_css_class_selector_fails(self):
        res = self.check("await page.locator('.btn-primary').click();")
        self.assertEqual(res.returncode, 1)

    def test_first_needs_comment(self):
        self.assertEqual(self.check("await page.getByRole('row').first().click();").returncode, 1)
        ok = "// first row is the newest by design\nawait page.getByRole('row').first().click();"
        self.assertEqual(self.check(ok).returncode, 0)

    def test_clean_test_passes_and_config_warns(self):
        res = self.check("await page.getByRole('button', { name: 'Pay' }).click();", config='export default {};')
        self.assertEqual(res.returncode, 0)
        self.assertIn('WARN', res.stdout)


@unittest.skipUnless(shutil.which('specify'), 'specify CLI not installed')
class InstallChecks(unittest.TestCase):
    """Real installs on throwaway Spec Kit projects."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='engineering-build-tests-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.base = Path(cls.tmp.name)

    def init(self, name):
        res = run('specify', 'init', name, '--integration', 'claude', '--script', 'py',
                  '--ignore-agent-tools', '--non-interactive', cwd=self.base)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        return self.base / name

    def install(self, repo, *extra, installer=INSTALLER, command='install'):
        return run(sys.executable, '-B', installer, command, '--repo', repo, '--json', *extra)

    def assert_wrapped(self, repo):
        for name in CORE:
            out = run('specify', 'preset', 'resolve', name, cwd=repo).stdout.replace('\\', '/').replace('\n', '')
            self.assertIn('presets/engineering-build/', out, name)
            skill = repo / '.claude' / 'skills' / name.replace('.', '-') / 'SKILL.md'
            self.assertIn('## Engineering Build: after', skill.read_text(encoding='utf-8'), name)

    def test_install_resolves_and_is_idempotent(self):
        repo = self.init('fresh')
        res = self.install(repo)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assert_wrapped(repo)
        installed = repo / INSTALLED
        for skill in SKILLS:
            self.assertTrue((installed / 'skills' / skill).is_dir(), skill)
        for rel in ('guide/rules.md', 'guide/bindings.md', 'bindings.yml', 'adapters/grill-me.md', 'scripts/verify_lock.py'):
            self.assertTrue((installed / rel).is_file(), rel)
        for source_only in ('tests', 'docs'):
            self.assertFalse((installed / source_only).exists(), source_only)
        self.assertFalse((installed / 'skills' / 'onboarding').exists())
        self.assertTrue((repo / '.specify' / 'engineering-build.yml').is_file())
        self.assertNotIn('engineering-build', run('specify', 'extension', 'list', cwd=repo).stdout)
        res = run(sys.executable, '-B', installed / 'scripts' / 'verify_lock.py', '--preset', installed)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.install(repo, command='verify').returncode, 0)
        again = json.loads(self.install(repo).stdout)
        self.assertEqual(again[0]['result']['status'], 'already installed')

    def test_installs_into_the_current_folder_without_repo(self):
        repo = self.init('cwd')
        res = run(sys.executable, '-B', INSTALLER, 'install', '--json', cwd=repo)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertEqual(Path(json.loads(res.stdout)[0]['repo']), repo.resolve())
        self.assertTrue((repo / INSTALLED / 'preset.yml').is_file())

    def test_dry_run_changes_nothing(self):
        repo = self.init('dry')
        before = sorted(p.relative_to(repo).as_posix() for p in repo.rglob('*'))
        self.assertEqual(self.install(repo, '--dry-run').returncode, 0)
        after = sorted(p.relative_to(repo).as_posix() for p in repo.rglob('*'))
        self.assertEqual(before, after)

    def test_failure_rolls_back(self):
        repo = self.init('fail')
        res = self.install(repo, '--inject-failure', 'after-preset')
        self.assertNotEqual(res.returncode, 0)
        self.assertNotIn('engineering-build', run('specify', 'preset', 'list', cwd=repo).stdout)

    def test_bulk_with_uninitialised_repo_and_update_keeps_config(self):
        good = self.init('bulk-good')
        bad = self.base / 'bulk-bad'
        bad.mkdir()
        repos = self.base / 'repos.txt'
        repos.write_text(f'{good}\n{bad}\n', encoding='utf-8')
        res = run(sys.executable, '-B', INSTALLER, 'install', '--repos-file', repos, '--json')
        self.assertEqual([r['code'] for r in json.loads(res.stdout)], [0, 2])
        self.assertEqual(res.returncode, 2)
        marker = good / '.specify' / 'engineering-build.yml'
        marker.write_text(marker.read_text(encoding='utf-8') + '\n# keep me\n', encoding='utf-8')
        self.assertEqual(self.install(good, command='update').returncode, 0)
        self.assertIn('# keep me', marker.read_text(encoding='utf-8'))
        self.assert_wrapped(good)

    def test_agent_skills_are_copied_when_asked(self):
        repo = self.init('agent-skills')
        res = self.install(repo, '--agent-skills', '.claude/skills')
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        for skill in ('engineering-build', 'engineering-review', 'onboarding') + UPSTREAM:
            self.assertTrue((repo / '.claude' / 'skills' / skill).is_dir(), skill)

    def test_upgrade_from_the_extension_release(self):
        """An install of the last extension release is replaced, keeping its binding config."""
        if run('git', '-C', REPO, 'cat-file', '-e', OLD_RELEASE + '^{commit}').returncode:
            self.skipTest(f'commit {OLD_RELEASE} not in this checkout')
        old = self.base / 'old-release'
        archive = self.base / 'old.zip'
        res = run('git', '-C', REPO, 'archive', '--format=zip', '-o', archive, OLD_RELEASE, 'skills', 'speckit-extensions')
        self.assertEqual(res.returncode, 0, res.stderr)
        zipfile.ZipFile(archive).extractall(old)
        repo = self.init('upgrade')
        res = self.install(repo, installer=old / 'speckit-extensions' / 'install.py')
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        old_cfg = repo / '.specify' / 'extensions' / 'engineering-build' / 'engineering-build-config.yml'
        old_cfg.write_text(old_cfg.read_text(encoding='utf-8') + '\n# from the old release\n', encoding='utf-8')
        self.assertNotEqual(self.install(repo, command='verify').returncode, 0)
        res = self.install(repo, command='update')
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertNotIn('engineering-build', run('specify', 'extension', 'list', cwd=repo).stdout)
        presets = run('specify', 'preset', 'list', cwd=repo).stdout
        self.assertNotIn('engineering-build-preset', presets)
        self.assertIn('# from the old release', (repo / '.specify' / 'engineering-build.yml').read_text(encoding='utf-8'))
        self.assert_wrapped(repo)
        self.assertEqual(self.install(repo, command='verify').returncode, 0)


class PackageChecks(unittest.TestCase):
    def test_package_holds_the_staged_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = run(sys.executable, '-B', INSTALLER, 'package', '--output', tmp, '--json')
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            info = json.loads(res.stdout)
            names = zipfile.ZipFile(info['archive']).namelist()
            self.assertIn('engineering-build/preset.yml', names)
            self.assertIn('engineering-build/guide/bindings.md', names)
            self.assertIn('engineering-build/skills/engineering-build/SKILL.md', names)
            self.assertIn('engineering-build/skills/grill-me/grilling.md', names)
            self.assertFalse(any(n.startswith('engineering-build/tests/') for n in names))
            self.assertFalse(any(n.endswith('extension.yml') for n in names))
            self.assertTrue(Path(info['archive'] + '.sha256').is_file())


if __name__ == '__main__':
    unittest.main()
