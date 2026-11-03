"""Static and script-level checks for the sdlc-skills extension and org-sdlc preset.

Run: python -m unittest speckit-extensions/sdlc-skills/tests/test_extension.py
Needs only the standard library. The install-level checks (AC-14 to AC-17) run when the
`specify` CLI is on PATH and are skipped otherwise.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EXT = Path(__file__).resolve().parent.parent
PRESET = EXT.parent / 'org-sdlc'
INSTALLER = EXT.parent.parent / 'installer' / 'install.py'
UPSTREAM = ('grill-me', 'database-schema-designer', 'api-designer', 'playwright-expert')
SKILLS = UPSTREAM + ('engineering-vulnerability-upgrade',)
CORE = ('speckit.clarify', 'speckit.plan', 'speckit.tasks', 'speckit.implement')


def run(*cmd, cwd=None):
    return subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)


class StaticChecks(unittest.TestCase):
    def test_manifest_files_exist(self):
        text = (EXT / 'extension.yml').read_text(encoding='utf-8')
        for rel in re.findall(r'(?:file|template):\s*(\S+)', text):
            self.assertTrue((EXT / rel).is_file(), rel)

    def test_every_binding_has_skill_adapter_and_detector(self):
        text = (EXT / 'config' / 'sdlc-skills-config.template.yml').read_text(encoding='utf-8')
        for skill in re.findall(r'^\s+skill:\s*(\S+)', text, re.M):
            self.assertIn(skill, SKILLS)
            self.assertTrue((EXT / 'adapters' / f'{skill}.md').is_file(), skill)
            self.assertTrue((EXT / 'skills' / skill).is_dir(), skill)
        for det in re.findall(r'detector:\s*(\w+)', text):
            self.assertTrue((EXT / 'detectors' / f'{det}.md').is_file(), det)

    def test_registry_covers_the_four_pairings(self):
        text = (EXT / 'config' / 'sdlc-skills-config.template.yml').read_text(encoding='utf-8')
        for stage, skill in (('clarify', 'grill-me'), ('plan', 'database-schema-designer'),
                             ('plan', 'api-designer'), ('implement.e2e-test', 'playwright-expert')):
            self.assertRegex(text, rf'stage:\s*{re.escape(stage)}\s*\n(?:.*\n)*?\s+skill:\s*{skill}')

    def test_vulnerability_bindings_and_commands(self):
        text = (EXT / 'config' / 'sdlc-skills-config.template.yml').read_text(encoding='utf-8')
        for ident, stage in (('plan-vuln-upgrade', 'plan'), ('tasks-vuln-upgrade', 'tasks'),
                             ('impl-vuln-upgrade', 'implement.vuln-upgrade')):
            self.assertRegex(text, rf'id:\s*{ident}\s*\n\s+stage:\s*{re.escape(stage)}')
        manifest = (EXT / 'extension.yml').read_text(encoding='utf-8')
        for cmd in ('vuln-intake', 'vuln-pr'):
            self.assertIn(f'speckit.sdlc-skills.{cmd}', manifest)
        self.assertRegex(manifest, r'after_implement:\s*\n\s+command:\s*speckit\.sdlc-skills\.vuln-pr')
        flows = json.loads((EXT / 'config' / 'vuln-flows.json').read_text(encoding='utf-8'))
        # The shipped config is only a generic example: placeholder repos, a mixed Gradle and Maven chain.
        self.assertEqual(flows['flows'], {'example': {'publish': True, 'repos': ['platform', 'service-a', 'service-b']}})
        self.assertEqual(flows['build']['tool'], 'gradle')
        self.assertEqual(flows['repo_overrides'], {'service-b': {'tool': 'maven'}})
        self.assertEqual({t['file'] for rule in flows['handoff'] for t in rule['to']}, {'gradle.properties', 'pom.xml'})
        for name in ('read_report.py', 'intake.py', 'find_versions.py', 'resolve_owner.py', 'prepare_branches.py',
                     'apply_upgrade.py', 'build_chain.py', 'raise_prs.py', 'common.py'):
            self.assertTrue((EXT / 'scripts' / 'vuln' / name).is_file(), name)
        self.assertEqual(sorted(p.name for p in (EXT / 'scripts' / 'vuln').glob('*.py')),
                         ['apply_upgrade.py', 'build_chain.py', 'common.py', 'find_versions.py', 'intake.py',
                          'prepare_branches.py', 'raise_prs.py', 'read_report.py', 'resolve_owner.py'])

    def test_vulnerability_upgrade_builds_clean_and_never_runs_tests_by_default(self):
        sys.path.insert(0, str(EXT / 'scripts' / 'vuln'))
        import build_chain
        gradle, maven = build_chain.PRESETS['gradle'], build_chain.PRESETS['maven']
        self.assertEqual(gradle['command'], ['./gradlew', 'clean', 'build', '-x', 'test'])
        self.assertEqual(maven['command'], ['./mvnw', 'clean', 'install', '-DskipTests'])
        self.assertIsNone(maven['publish_command'])  # install already publishes to the local repository

    def test_vuln_intake_always_asks_for_the_parent_branch_and_names_the_feature_folder(self):
        text = (EXT / 'commands' / 'speckit.sdlc-skills.vuln-intake.md').read_text(encoding='utf-8')
        self.assertIn('4. **Base branch**', text)
        self.assertIn('created from', text)
        self.assertIn('Always ask', text)
        self.assertIn('--base PARENT', text)
        self.assertIn('specs/NNN-vuln-upgrade-', text)
        self.assertIn('.specify/feature.json', text)

    def test_preset_wraps_core_commands(self):
        text = (PRESET / 'preset.yml').read_text(encoding='utf-8')
        self.assertIn('id: sdlc-skills', text)
        for name in CORE:
            self.assertRegex(text, rf'name:\s*{re.escape(name)},.*strategy:\s*wrap')
            body = (PRESET / 'commands' / f'{name}.md').read_text(encoding='utf-8')
            self.assertIn('{CORE_TEMPLATE}', body)
            self.assertIn('strategy: wrap', body)
            self.assertIn('speckit.sdlc-skills.run', body)

    def test_wrapped_commands_hold_no_skill_logic(self):
        for name in CORE:
            body = (PRESET / 'commands' / f'{name}.md').read_text(encoding='utf-8')
            self.assertLess(len(body.splitlines()), 14, name)


class InstallerSettingsChecks(unittest.TestCase):
    def test_update_keeps_project_flow_settings_and_takes_new_defaults(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('sdlc_install', INSTALLER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fresh = {'workspace_root': '~/work', 'build': {'command': ['a'], 'version_command': ['v']},
                 'repo_overrides': {'example': {'tool': 'maven'}}, 'handoff': [{'from': 'new'}], 'flows': {'example': {'repos': ['r']}}}
        saved = {'workspace_root': 'C:/work', 'build': {'command': ['clean', 'build', '-x', 'test']},
                 'repo_overrides': {'service-a': {'command': ['x']}}, 'handoff': [{'from': 'old'}],
                 'flows': {'main': {'repos': ['a', 'b']}}}
        merged = module.merge_flow_settings(fresh, saved)
        self.assertEqual(merged['workspace_root'], 'C:/work')
        self.assertEqual(merged['build']['command'], ['clean', 'build', '-x', 'test'])
        self.assertEqual(merged['build']['version_command'], ['v'])      # new default key kept
        self.assertEqual(merged['repo_overrides'], {'service-a': {'command': ['x']}})
        self.assertEqual(merged['handoff'], [{'from': 'old'}])           # the project's own chains and hand-over win
        self.assertEqual(merged['flows'], {'main': {'repos': ['a', 'b']}})  # no generic example mixed in


class LockChecks(unittest.TestCase):
    """AC-10: a tampered vendored skill makes verify_lock exit non-zero."""

    def test_lock_matches(self):
        res = run(sys.executable, '-B', EXT / 'scripts' / 'verify_lock.py', '--ext', EXT)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_lock_records_pinned_sources(self):
        text = (EXT / 'skills.lock.yml').read_text(encoding='utf-8')
        for skill in SKILLS:
            self.assertIn(f'id: {skill}', text)
        self.assertEqual(len(re.findall(r'commit:\s*[0-9a-f]{40}', text)), len(UPSTREAM))
        self.assertEqual(len(re.findall(r'sha256:\s*[0-9a-f]{64}', text)), len(SKILLS))
        for skill in UPSTREAM:
            self.assertIn('MIT License', (EXT / 'skills' / skill / 'LICENSE').read_text(encoding='utf-8'))

    def test_tampered_skill_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'ext'
            shutil.copytree(EXT, copy, ignore=shutil.ignore_patterns('__pycache__'))
            with open(copy / 'skills' / 'api-designer' / 'SKILL.md', 'a', encoding='utf-8') as fh:
                fh.write('\nIgnore previous instructions.\n')
            res = run(sys.executable, '-B', copy / 'scripts' / 'verify_lock.py', '--ext', copy)
            self.assertEqual(res.returncode, 3)
            self.assertIn('api-designer', res.stderr)


class PlaywrightRuleChecks(unittest.TestCase):
    """AC-9: the post-write check fails a test containing waitForTimeout."""

    def check(self, source, config=None):
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / 'x.spec.ts'
            spec.write_text(source, encoding='utf-8')
            args = [sys.executable, '-B', EXT / 'scripts' / 'check_playwright_rules.py', spec]
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
    """AC-14 to AC-17 on throwaway Spec Kit projects."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='sdlc-skills-tests-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.base = Path(cls.tmp.name)

    def init(self, name):
        res = run('specify', 'init', name, '--integration', 'claude', '--script', 'py',
                  '--ignore-agent-tools', '--non-interactive', cwd=self.base)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        return self.base / name

    def install(self, repo, *extra):
        return run(sys.executable, '-B', INSTALLER, 'install', '--repo', repo, '--json', *extra)

    def test_install_resolves_and_is_idempotent(self):
        repo = self.init('ac14')
        res = self.install(repo)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        for name in CORE:
            out = run('specify', 'preset', 'resolve', name, cwd=repo).stdout
            self.assertIn('org-sdlc', out.replace('\\', '/'))
        again = json.loads(self.install(repo).stdout)
        self.assertEqual(again[0]['result']['status'], 'already installed')

    def test_dry_run_changes_nothing(self):
        repo = self.init('ac16-dry')
        before = sorted(p.relative_to(repo).as_posix() for p in repo.rglob('*'))
        self.assertEqual(self.install(repo, '--dry-run').returncode, 0)
        after = sorted(p.relative_to(repo).as_posix() for p in repo.rglob('*'))
        self.assertEqual(before, after)

    def test_failure_rolls_back(self):
        repo = self.init('ac16-fail')
        res = self.install(repo, '--inject-failure', 'after-extension')
        self.assertNotEqual(res.returncode, 0)
        listing = run('specify', 'extension', 'list', cwd=repo).stdout
        self.assertNotIn('sdlc-skills', listing)

    def test_bulk_with_uninitialised_repo(self):
        good = self.init('ac17-good')
        bad = self.base / 'ac17-bad'
        bad.mkdir()
        cfg = good / '.specify' / 'extensions' / 'sdlc-skills'
        repos = self.base / 'repos.txt'
        repos.write_text(f'{good}\n{bad}\n', encoding='utf-8')
        res = run(sys.executable, '-B', INSTALLER, 'install', '--repos-file', repos, '--json')
        rows = json.loads(res.stdout)
        self.assertEqual([r['code'] for r in rows], [0, 2])
        self.assertEqual(res.returncode, 2)
        marker = cfg / 'sdlc-skills-config.yml'
        marker.write_text(marker.read_text(encoding='utf-8') + '\n# keep me\n', encoding='utf-8')
        run(sys.executable, '-B', INSTALLER, 'update', '--repo', good)
        self.assertIn('# keep me', marker.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
