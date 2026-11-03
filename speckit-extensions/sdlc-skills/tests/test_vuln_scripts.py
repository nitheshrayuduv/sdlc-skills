"""Standard-library tests for the vulnerability upgrade scripts. Run: python -m unittest discover tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts' / 'vuln'
sys.path.insert(0, str(SCRIPTS))

import read_report  # noqa: E402
import raise_prs  # noqa: E402

PY = sys.executable
TICKET_TEXT = ('<p>jackson: com.fasterxml.jackson.core:jackson-databind 2.13.0 -> 2.13.4.2 (CVE-2022-42003)</p>'
               '<p>org.yaml:snakeyaml vulnerable 1.30 fixed in 1.33</p>'
               '<p>mystery-lib 3.1.0</p>')


def script(name, *args, cwd=None):
    return subprocess.run([PY, '-B', str(SCRIPTS / name), *map(str, args)], capture_output=True, text=True, cwd=cwd)


def git(repo, *args):
    subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True)


class ParsingTests(unittest.TestCase):
    def test_arrow_and_keyword_forms(self):
        found = {f['dependency']: f for f in read_report.parse_findings(TICKET_TEXT) if f['dependency']}
        jackson = found['com.fasterxml.jackson.core:jackson-databind']
        self.assertEqual((jackson['vulnerable_version'], jackson['fixed_version']), ('2.13.0', '2.13.4.2'))
        self.assertEqual(jackson['advisory'], 'CVE-2022-42003')
        snake = found['org.yaml:snakeyaml']
        self.assertEqual((snake['vulnerable_version'], snake['fixed_version']), ('1.30', '1.33'))

    def test_incomplete_line_needs_confirmation(self):
        item = [f for f in read_report.parse_findings(TICKET_TEXT) if f['dependency'] is None][0]
        self.assertEqual(item['status'], 'needs-confirmation')

    def test_missing_report_file_is_refused(self):
        result = script('read_report.py', '--report', 'no-such-report.json', '--ticket', 'PROJ-123', '--out', 'x.json')
        self.assertEqual(result.returncode, 2)
        self.assertIn('Report file not found', result.stderr)


REPORT = (
    'IMAGE - registry.example.com/app : VERSION/TAG - 1.4.2\n\n'
    'CVE\tSeverity\tPackage\tVersion\tFix version\tPath\n'
    'CVE-2026-000001\tMEDIUM\tzlib1g\t1.2.13\t1.2.13.1\tpkg:deb/debian/zlib1g@1.2.13?arch=amd64\n'
    'CVE-2026-000002\tMEDIUM\torg.example:messaging-client\t5.35.0\t5.36.1\tapp/lib/messaging-client-5.35.0.jar\n'
    'CVE-2026-000003\tHIGH\torg.example:messaging-client\t5.35.0\t5.36.0\tapp/lib/messaging-client-5.35.0.jar\n\n'
    'IMAGE - registry.example.com/worker : VERSION/TAG - 1.4.2\n\n'
    'CVE\tSeverity\tPackage\tVersion\tFix version\tPath\n'
    'CVE-2026-000002\tMEDIUM\torg.example:messaging-client\t5.35.0\t5.36.1\tworker/lib/messaging-client-5.35.0.jar\n')

TRIVY = {
    'Results': [
        {'Target': 'registry.example.com/app:1.4.2 (debian 12)', 'Class': 'os-pkgs', 'Type': 'debian',
         'Vulnerabilities': [{'VulnerabilityID': 'CVE-2026-000001', 'PkgName': 'zlib1g', 'InstalledVersion': '1.2.13',
                              'FixedVersion': '1.2.13.1', 'Severity': 'MEDIUM'}]},
        {'Target': 'Java', 'Class': 'lang-pkgs', 'Type': 'jar',
         'Vulnerabilities': [{'VulnerabilityID': 'CVE-2026-000004', 'PkgName': 'org.example:lib-core',
                              'InstalledVersion': '2.1.0', 'FixedVersion': '2.1.3, 2.1.4', 'Severity': 'HIGH',
                              'PkgPath': 'app/lib/lib-core-2.1.0.jar'}]},
        {'Target': 'package-lock.json', 'Class': 'lang-pkgs', 'Type': 'npm',
         'Vulnerabilities': [{'VulnerabilityID': 'GHSA-aaaa-bbbb-cccc', 'PkgName': 'left-pad',
                              'InstalledVersion': '1.0.0', 'FixedVersion': '1.0.1', 'Severity': 'LOW'}]},
    ]}


class ReportTests(unittest.TestCase):
    def test_table_report(self):
        by_name = {f['dependency']: f for f in read_report.parse_findings(REPORT)}
        client = by_name['org.example:messaging-client']
        self.assertEqual((client['status'], client['fixed_version']), ('ok', '5.36.1'))  # highest fix covers both
        self.assertEqual(client['advisories'], ['CVE-2026-000002', 'CVE-2026-000003'])
        self.assertEqual(client['severity'], 'HIGH')
        self.assertEqual(client['images'], ['app', 'worker'])
        self.assertEqual(by_name['zlib1g']['status'], 'out-of-scope')

    def test_trivy_json_report(self):
        by_name = {f['dependency']: f for f in read_report.parse_findings(json.dumps(TRIVY))}
        self.assertEqual(by_name['zlib1g']['status'], 'out-of-scope')
        lib = by_name['org.example:lib-core']
        self.assertEqual((lib['ecosystem'], lib['status'], lib['fixed_version']), ('maven', 'ok', '2.1.4'))
        self.assertEqual((by_name['left-pad']['ecosystem'], by_name['left-pad']['status']), ('npm', 'ok'))

    def test_report_file_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            report, out = Path(tmp) / 'trivy.json', Path(tmp) / 'findings.json'
            report.write_text(json.dumps(TRIVY))
            result = script('read_report.py', '--report', report, '--ticket', 'PROJ-123', '--out', out)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(out.read_text())
            self.assertEqual((data['ticket'], data['title'], len(data['findings'])), ('PROJ-123', 'trivy.json', 3))


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.ws, self.feature = base / 'ws', base / 'feature'
        self.config = base / 'flows.json'
        config = json.loads((ROOT / 'config' / 'vuln-flows.json').read_text())
        config['flows'] = {'main': {'publish': False, 'repos': ['platform', 'service-a', 'service-b']},
                           'nightly': {'publish': True, 'repos': ['platform', 'service-a']}}
        config['build']['command'] = [PY, '-c', 'print("built")']
        config['build']['publish_command'] = [PY, '-c', 'print("published")']
        self.config.write_text(json.dumps(config))
        self.make_repo('platform', {
            'reference/versions.conf': 'jackson-databind = "2.13.0"\nsnakeyaml = "1.30"\n',
            'gradle.properties': 'unrelated=1.0.0\n'})
        self.make_repo('service-a', {
            'versions.conf': 'jackson-databind: 2.13.0\n',
            'gradle.properties': 'unrelated=2.13.0\n'})
        self.make_repo('service-b', {
            'build.gradle': "implementation 'org.yaml:snakeyaml:1.35'\n",
            'gradle.properties': 'jacksonVersion=2.13.0\n',
            'dependencies.gradle': "implementation \"com.fasterxml.jackson.core:jackson-databind:${jacksonVersion}\"\n"})
        findings = [
            {'dependency': 'com.fasterxml.jackson.core:jackson-databind', 'vulnerable_version': '2.13.0',
             'fixed_version': '2.13.4.2', 'advisory': None, 'status': 'ok'},
            {'dependency': 'org.yaml:snakeyaml', 'vulnerable_version': '1.30', 'fixed_version': '1.33',
             'advisory': None, 'status': 'ok'}]
        self.findings = self.feature / 'vuln' / 'findings.json'
        self.findings.parent.mkdir(parents=True)
        self.findings.write_text(json.dumps({'ticket': 'PROJ-123', 'findings': findings}))

    def make_repo(self, name, files):
        repo = self.ws / name
        for rel, text in files.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text(text)
        git(repo, 'init', '-q')
        git(repo, 'config', 'user.email', 't@example.com')
        git(repo, 'config', 'user.name', 'test')
        git(repo, 'add', '-A')
        git(repo, 'commit', '-qm', 'init')

    def run_script(self, name, *args):
        return script(name, '--config', self.config, *args)

    def locate(self):
        hits, changes = self.feature / 'vuln' / 'hits.json', self.feature / 'vuln' / 'changes.json'
        self.assertEqual(self.run_script('find_versions.py', '--flow', 'main', '--workspace', self.ws,
                                         '--findings', self.findings, '--out', hits).returncode, 0)
        result = self.run_script('resolve_owner.py', '--hits', hits, '--findings', self.findings,
                                 '--out', changes, '--plan-md', self.feature / 'vuln' / 'plan.md')
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(changes.read_text())

    def test_owner_rules(self):
        plan = self.locate()
        rows = {r['dependency'].split(':')[-1]: r for r in plan['dependencies']}
        jackson, snake = rows['jackson-databind'], rows['snakeyaml']
        self.assertEqual(jackson['decision'], 'change')
        self.assertEqual(jackson['scope'], 'platform+downstream')
        self.assertEqual(jackson['owners'], ['platform', 'service-a', 'service-b'])
        # service-b changes the property definition, not the reference line or the other property
        service_b = [c for c in jackson['changes'] if c['repo'] == 'service-b']
        self.assertEqual([(c['file'], c['key']) for c in service_b], [('gradle.properties', 'jacksonVersion')])
        # service-a's unrelated property with the same number is left alone
        self.assertFalse(any(c['file'] == 'gradle.properties' for c in jackson['changes'] if c['repo'] == 'service-a'))
        # snakeyaml is vulnerable only in the platform reference; service-b pins a different version
        self.assertEqual(snake['scope'], 'platform-only')
        self.assertEqual(snake['owners'], ['platform'])

    def current_branch(self, repo):
        return subprocess.run(['git', 'branch', '--show-current'], cwd=self.ws / repo,
                              capture_output=True, text=True).stdout.strip()

    def prepare(self, *extra):
        return self.run_script('prepare_branches.py', '--feature-dir', self.feature, '--workspace', self.ws,
                               '--flow', 'main', '--branch', 'vuln/PROJ-123', *extra)

    def test_missing_branch_asks_for_parent_then_creates_from_it(self):
        git(self.ws / 'service-a', 'branch', 'release/1.4')
        check = self.prepare('--check-only')
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn('MISSING: platform, service-a, service-b', check.stdout)
        refused = self.prepare()
        self.assertEqual(refused.returncode, 8)
        self.assertIn('parent branch', refused.stderr)
        for repo in ('platform', 'service-b'):
            git(self.ws / repo, 'branch', 'release/1.4')
        done = self.prepare('--base', 'release/1.4')
        self.assertEqual(done.returncode, 0, done.stderr)
        for repo in ('platform', 'service-a', 'service-b'):
            self.assertEqual(self.current_branch(repo), 'vuln/PROJ-123')
        bases = json.loads((self.feature / 'vuln' / 'branches.json').read_text())['bases']
        self.assertEqual(bases['service-a'], 'release/1.4')

    def test_existing_branch_is_reused(self):
        for repo in ('platform', 'service-a', 'service-b'):
            git(self.ws / repo, 'branch', 'vuln/PROJ-123')
        self.assertIn('exists in every repo', self.prepare('--check-only').stdout)
        self.assertEqual(self.prepare().returncode, 0)
        self.assertEqual(self.current_branch('service-b'), 'vuln/PROJ-123')

    def test_handoff_is_used_by_next_build_then_restored(self):
        (self.ws / 'platform' / 'gradle.properties').write_text('version=9.9.9\n')
        (self.ws / 'service-a' / 'gradle.properties').write_text('platformVersion=1.0.0\n')
        check = [PY, '-c', 'import sys; sys.exit(0 if "platformVersion=9.9.9" in open("gradle.properties").read() else 1)']
        config = json.loads(self.config.read_text())
        config['repo_overrides'] = {'service-a': {'command': check}}
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'platform', 'version_file': 'gradle.properties', 'version_key': 'version',
                              'to': [{'repo': 'service-a', 'file': 'gradle.properties', 'key': 'platformVersion'},
                                     {'repo': 'service-b', 'file': 'gradle.properties', 'key': 'missingKey'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('platformVersion 1.0.0 -> 9.9.9', result.stdout)
        self.assertIn('missingKey not found', result.stdout)
        self.assertEqual((self.ws / 'service-a' / 'gradle.properties').read_text(), 'platformVersion=1.0.0\n')

    def test_handoff_reads_version_from_gradle_and_rewrites_dependencies_conf(self):
        conf = '''versions {
        platformVersion="1.4.0"
        upstreamVersion="1.4.0"
}
'''
        for repo in ('service-a', 'service-b'):
            (self.ws / repo / 'gradle').mkdir(exist_ok=True)
            (self.ws / repo / 'gradle' / 'versions.conf').write_text(conf)
        stub = 'print("version: 7.7.7")'
        code = ('import sys; t = open("gradle/versions.conf").read()\n'
                'ok = "platformVersion=\\"7.7.7\\"" in t and "upstreamVersion=\\"7.7.7\\"" in t\n'
                'sys.exit(0 if ok else 1)')
        check = [PY, '-c', code]
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', stub]
        config['repo_overrides'] = {'service-b': {'command': check}}
        config['flows']['main']['publish'] = True
        dep = 'gradle/versions.conf'
        config['handoff'] = [
            {'from': 'platform', 'version_source': 'build',
             'to': [{'repo': 'service-a', 'file': dep, 'key': 'platformVersion'},
                    {'repo': 'service-b', 'file': dep, 'key': 'platformVersion'}]},
            {'from': 'service-a', 'version_source': 'build',
             'to': [{'repo': 'service-b', 'file': dep, 'key': 'upstreamVersion'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('platformVersion 1.4.0 -> 7.7.7', result.stdout)
        # both keys in the same file are put back exactly, quotes included
        for repo in ('service-a', 'service-b'):
            self.assertEqual((self.ws / repo / 'gradle' / 'versions.conf').read_text(), conf)

    def test_handoff_without_a_build_tool_version_is_reported_not_guessed(self):
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', 'print("version: unspecified")']
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'platform', 'version_source': 'build',
                              'to': [{'repo': 'service-a', 'file': 'gradle.properties', 'key': 'unrelated'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('could not read its version from the build tool', result.stdout)
        self.assertEqual((self.ws / 'service-a' / 'gradle.properties').read_text(), 'unrelated=2.13.0\n')

    def changed_only(self, changed, order=None, rules=None, *extra):
        """Dry-run the chain in --changed-only mode and return (result, build-results.json)."""
        config = json.loads(self.config.read_text())
        if order:
            config['flows']['main']['repos'] = order
        dep = 'gradle/versions.conf'
        config['handoff'] = [{'from': frm, 'version_source': 'build',
                              'to': [{'repo': r, 'file': dep, 'key': key} for r in to]}
                             for frm, key, to in (rules or [])]
        self.config.write_text(json.dumps(config))
        changes = self.feature / 'vuln' / 'changes.json'
        changes.write_text(json.dumps({'ticket': 'PROJ-123', 'flow': 'main',
                                       'changes': [{'repo': r} for r in changed]}))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws, '--changed-only', '--dry-run', *extra)
        out = self.feature / 'vuln' / 'build-results.json'
        return result, (json.loads(out.read_text()) if out.is_file() else None)

    def test_changed_only_skips_unchanged_upstream_repos(self):
        rules = [('platform', 'platformVersion', ['service-a', 'service-b']),
                 ('service-a', 'serviceAVersion', ['service-b'])]
        result, data = self.changed_only(['service-a'], rules=rules)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([r['repo'] for r in data['results']], ['service-a', 'service-b'])
        self.assertEqual(data['skipped'], ['platform'])
        self.assertTrue(data['changed_only'])

    def test_changed_only_with_no_dependents_builds_just_the_changed_repo(self):
        rules = [('platform', 'platformVersion', ['service-a', 'service-b'])]
        result, data = self.changed_only(['service-b'], rules=rules)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([r['repo'] for r in data['results']], ['service-b'])
        self.assertEqual(data['skipped'], ['platform', 'service-a'])

    def test_changed_only_follows_dependents_transitively(self):
        rules = [('platform', 'platformVersion', ['service-a']),
                 ('service-a', 'serviceAVersion', ['service-b'])]
        result, data = self.changed_only(['platform'], rules=rules)
        self.assertEqual([r['repo'] for r in data['results']], ['platform', 'service-a', 'service-b'])
        self.assertEqual(data['skipped'], [])

    def test_changed_only_needs_changes(self):
        result, _ = self.changed_only([], rules=[])
        self.assertEqual(result.returncode, 2)
        self.assertIn('nothing to build', result.stderr)

    def test_changed_only_warns_when_a_dependent_is_built_before_its_upstream(self):
        rules = [('service-a', 'serviceAVersion', ['service-b'])]
        result, data = self.changed_only(['service-a'], order=['service-b', 'service-a', 'platform'], rules=rules)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([r['repo'] for r in data['results']], ['service-b', 'service-a'])
        self.assertTrue(any('service-b pins serviceAVersion' in w for w in data['warnings']))
        self.assertIn('warning:', result.stdout)

    def test_apply_and_handoff_keep_crlf_line_endings_byte_for_byte(self):
        crlf_props = b'a=1\r\nlibCoreVersion=2.1.0\r\nb=2\r\n'
        crlf_conf = b'versions {\r\n        platformVersion="1.4.0"\r\n}\r\n'
        (self.ws / 'service-a' / 'gradle').mkdir(exist_ok=True)
        (self.ws / 'service-a' / 'gradle.properties').write_bytes(crlf_props)
        (self.ws / 'service-b' / 'gradle').mkdir(exist_ok=True)
        (self.ws / 'service-b' / 'gradle' / 'versions.conf').write_bytes(crlf_conf)
        for repo in ('service-a', 'service-b'):
            git(self.ws / repo, 'checkout', '-q', '-b', 'vuln/PROJ-123')
        changes = self.feature / 'vuln' / 'changes.json'
        changes.write_text(json.dumps({'ticket': 'PROJ-123', 'flow': 'main', 'changes': [
            {'repo': 'service-a', 'file': 'gradle.properties', 'line': 2, 'key': 'libCoreVersion',
             'old': '2.1.0', 'new': '2.1.4'}]}))
        applied = self.run_script('apply_upgrade.py', '--changes', changes, '--workspace', self.ws,
                                  '--branch', 'vuln/PROJ-123', '--allow-dirty',
                                  '--out', self.feature / 'vuln' / 'applied.json')
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertEqual((self.ws / 'service-a' / 'gradle.properties').read_bytes(),
                         b'a=1\r\nlibCoreVersion=2.1.4\r\nb=2\r\n')
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', 'print("version: 7.7.7")']
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'platform', 'version_source': 'build',
                              'to': [{'repo': 'service-b', 'file': 'gradle/versions.conf',
                                      'key': 'platformVersion'}]}]
        self.config.write_text(json.dumps(config))
        built = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                '--workspace', self.ws)
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self.assertIn('platformVersion 1.4.0 -> 7.7.7', built.stdout)
        self.assertEqual((self.ws / 'service-b' / 'gradle' / 'versions.conf').read_bytes(), crlf_conf)

    def test_build_output_is_written_to_the_log_while_it_runs(self):
        config = json.loads(self.config.read_text())
        config['build']['command'] = [PY, '-c', 'print("> Task :compileScala"); print("done")']
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'nightly', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('build log:', result.stdout)
        log = (self.feature / 'vuln' / 'build-platform.log').read_text()
        self.assertIn('> Task :compileScala', log)

    def test_resume_reapplies_the_handoff_from_repos_already_published(self):
        conf = 'versions {\n        platformVersion="1.4.0"\n}\n'
        (self.ws / 'service-a' / 'gradle').mkdir(exist_ok=True)
        (self.ws / 'service-a' / 'gradle' / 'versions.conf').write_text(conf)
        code = ('import sys\nt = open("gradle/versions.conf").read()\n'
                'sys.exit(0 if "platformVersion=\\"7.7.7\\"" in t else 1)')
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', 'print("version: 7.7.7")']
        config['repo_overrides'] = {'service-a': {'command': [PY, '-c', code]}}
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'platform', 'version_source': 'build',
                              'to': [{'repo': 'service-a', 'file': 'gradle/versions.conf',
                                      'key': 'platformVersion'}]}]
        self.config.write_text(json.dumps(config))
        (self.feature / 'vuln' / 'changes.json').write_text(json.dumps(
            {'ticket': 'PROJ-123', 'flow': 'main', 'changes': [{'repo': 'platform'}]}))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws, '--changed-only', '--from-repo', 'service-a')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('resuming at service-a', result.stdout)
        data = json.loads((self.feature / 'vuln' / 'build-results.json').read_text())
        self.assertNotIn('platform', [r['repo'] for r in data['results']])
        self.assertTrue(data['all_passed'])
        self.assertEqual((self.ws / 'service-a' / 'gradle' / 'versions.conf').read_text(), conf)

    def test_resume_at_an_unselected_repo_is_refused(self):
        result, _ = self.changed_only(['service-b'], None, [], '--from-repo', 'platform')
        self.assertEqual(result.returncode, 2)
        self.assertIn('not one of the repos to build', result.stderr)

    def test_next_run_restores_files_left_edited_by_a_stopped_run(self):
        conf = b'versions {\r\n        platformVersion="1.4.0"\r\n}\r\n'
        target = self.ws / 'service-a' / 'gradle' / 'versions.conf'
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(conf.replace(b'1.4.0', b'9.9.9-STRAY'))
        import base64
        (self.feature / 'vuln' / 'handoff-backup.json').write_text(json.dumps(
            [{'path': str(target), 'data': base64.b64encode(conf).decode('ascii')}]))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('recovered an earlier interrupted run', result.stdout)
        self.assertEqual(target.read_bytes(), conf)
        self.assertFalse((self.feature / 'vuln' / 'handoff-backup.json').exists())

    def test_backup_is_removed_after_a_normal_run(self):
        (self.ws / 'service-a' / 'gradle').mkdir(exist_ok=True)
        (self.ws / 'service-a' / 'gradle' / 'versions.conf').write_text('        k="1.0.0"\n')
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', 'print("version: 7.7.7")']
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'platform', 'version_source': 'build',
                              'to': [{'repo': 'service-a', 'file': 'gradle/versions.conf', 'key': 'k'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.feature / 'vuln' / 'handoff-backup.json').exists())

    def test_repo_env_override_applies_only_to_that_repo(self):
        config = json.loads(self.config.read_text())
        config['build']['command'] = [PY, '-c', 'import os; print("JDK=" + os.environ.get("JDK_TAG", "none"))']
        config['repo_overrides'] = {'platform': {'env': {'JDK_TAG': 'seventeen'}}}
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        vuln = self.feature / 'vuln'
        self.assertIn('JDK=seventeen', (vuln / 'build-platform.log').read_text())
        self.assertIn('JDK=none', (vuln / 'build-service-a.log').read_text())

    def test_version_command_uses_the_repos_env(self):
        (self.ws / 'service-a' / 'gradle').mkdir(exist_ok=True)
        (self.ws / 'service-a' / 'gradle' / 'versions.conf').write_text('        k="1.0.0"\n')
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', 'import os; print("version: " + os.environ.get("JDK_TAG", "none"))']
        config['repo_overrides'] = {'platform': {'env': {'JDK_TAG': 'seventeen'}}}
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'platform', 'version_source': 'build',
                              'to': [{'repo': 'service-a', 'file': 'gradle/versions.conf', 'key': 'k'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('k 1.0.0 -> seventeen', result.stdout)

    def test_chain_refuses_to_start_when_a_handoff_pin_was_edited_by_hand(self):
        conf = self.ws / 'service-a' / 'gradle' / 'versions.conf'
        conf.parent.mkdir(exist_ok=True)
        conf.write_text('        platformVersion="1.4.0"\n')
        git(self.ws / 'service-a', 'add', '-A')
        git(self.ws / 'service-a', 'commit', '-qm', 'pins')
        conf.write_text('        platformVersion="1.4.1-SNAPSHOT"\n')
        config = json.loads(self.config.read_text())
        config['handoff'] = [{'from': 'platform', 'version_source': 'build',
                              'to': [{'repo': 'service-a', 'file': 'gradle/versions.conf', 'key': 'platformVersion'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 2)
        self.assertIn('changed by hand', result.stderr)
        self.assertIn('platformVersion is 1.4.1-SNAPSHOT, committed 1.4.0', result.stderr)

    def test_workspace_is_found_from_the_platform_repo_when_not_configured(self):
        import common
        config = {'workspace_root': str(self.ws / 'nowhere'),
                  'flows': {'main': {'repos': ['platform', 'service-a']}}}
        previous = os.getcwd()
        try:
            os.chdir(self.ws / 'platform')
            self.assertEqual(Path(common.resolve_workspace(config)).resolve(), self.ws.resolve())
        finally:
            os.chdir(previous)
        self.assertEqual(common.resolve_workspace(config, 'explicit'), 'explicit')
        config['workspace_root'] = str(self.ws)
        self.assertEqual(common.resolve_workspace(config), str(self.ws))

    def test_maven_dependency_blocks_and_properties_are_found(self):
        pom = """<project>
  <properties>
    <snakeyaml.version>1.30</snakeyaml.version>
    <unrelated.version>1.30</unrelated.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-databind</artifactId>
      <version>2.13.0</version>
    </dependency>
    <dependency>
      <groupId>org.yaml</groupId>
      <artifactId>snakeyaml</artifactId>
      <version>${snakeyaml.version}</version>
    </dependency>
  </dependencies>
</project>
"""
        self.make_repo('service-c', {'pom.xml': pom})
        config = json.loads(self.config.read_text())
        config['flows']['main']['repos'].append('service-c')
        self.config.write_text(json.dumps(config))
        hits = self.feature / 'vuln' / 'hits.json'
        result = self.run_script('find_versions.py', '--flow', 'main', '--workspace', self.ws,
                                 '--findings', self.findings, '--out', hits)
        self.assertEqual(result.returncode, 0, result.stderr)
        found = [(h['dependency'].split(':')[-1], h['line'], h['match_type'], h.get('key'))
                 for h in json.loads(hits.read_text())['hits'] if h['repo'] == 'service-c']
        self.assertIn(('jackson-databind', 10, 'literal', None), found)
        self.assertIn(('snakeyaml', 3, 'property_definition', 'snakeyaml.version'), found)
        self.assertNotIn('unrelated.version', [f[3] for f in found])

    def test_version_catalog_reference_is_followed(self):
        catalog = '[versions]\nyaml = "1.30"\n\n[libraries]\nsnake = { module = "org.yaml:snakeyaml", version.ref = "yaml" }\n'
        self.make_repo('service-c', {'gradle/libs.versions.toml': catalog})
        config = json.loads(self.config.read_text())
        config['flows']['main']['repos'].append('service-c')
        self.config.write_text(json.dumps(config))
        hits = self.feature / 'vuln' / 'hits.json'
        self.run_script('find_versions.py', '--flow', 'main', '--workspace', self.ws, '--findings', self.findings,
                        '--out', hits)
        found = [(h['line'], h['match_type'], h.get('key')) for h in json.loads(hits.read_text())['hits']
                 if h['repo'] == 'service-c']
        self.assertIn((2, 'property_definition', 'yaml'), found)

    def test_handoff_rewrites_a_maven_property_and_restores_it(self):
        pom = '<project>\r\n  <properties>\r\n    <platform.version>1.4.0</platform.version>\r\n  </properties>\r\n</project>\r\n'
        (self.ws / 'service-a' / 'pom.xml').write_bytes(pom.encode())
        code = ('import sys\nt = open("pom.xml").read()\n'
                'sys.exit(0 if "<platform.version>7.7.7</platform.version>" in t else 1)')
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', 'print("version: 7.7.7")']
        config['repo_overrides'] = {'service-a': {'command': [PY, '-c', code]}}
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'platform', 'version_source': 'build',
                              'to': [{'repo': 'service-a', 'file': 'pom.xml', 'key': 'platform.version'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature, '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('platform.version 1.4.0 -> 7.7.7', result.stdout)
        self.assertEqual((self.ws / 'service-a' / 'pom.xml').read_bytes(), pom.encode())

    def test_maven_preset_applies_per_repo_and_falls_back_to_mvn(self):
        config = json.loads(self.config.read_text())
        config['build'] = {'tool': 'gradle'}
        config['repo_overrides'] = {'service-b': {'tool': 'maven'}}
        config['flows']['main']['publish'] = True
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature, '--workspace', self.ws,
                                 '--dry-run')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertIn('[service-b] build: mvn clean install -DskipTests', lines)       # no mvnw in the repo
        self.assertFalse(any(line.startswith('[service-b] publish') for line in lines))  # install already publishes
        self.assertIn('[platform] build: gradle clean build -x test', lines)            # no gradlew in the repo
        self.assertIn('[platform] publish: gradle publishToMavenLocal', lines)

    def test_unknown_build_tool_without_commands_is_refused(self):
        config = json.loads(self.config.read_text())
        config['build'] = {'tool': 'bazel'}
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature, '--workspace', self.ws,
                                 '--dry-run')
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown build tool 'bazel'", result.stderr)

    def test_os_packages_are_listed_but_never_edited(self):
        findings = json.loads(self.findings.read_text())
        findings['findings'].append({'dependency': 'zlib1g', 'ecosystem': 'os', 'vulnerable_version': '1.3.1',
                                     'fixed_version': '1.3.2', 'status': 'out-of-scope', 'reason': 'os'})
        self.findings.write_text(json.dumps(findings))
        plan = self.locate()
        row = [r for r in plan['dependencies'] if r['dependency'] == 'zlib1g'][0]
        self.assertEqual((row['decision'], row['changes']), ('out-of-scope', []))

    def test_apply_edits_only_listed_lines(self):
        self.locate()
        self.assertEqual(self.prepare('--base', self.default_branch('service-a')).returncode, 0)
        changes, applied = self.feature / 'vuln' / 'changes.json', self.feature / 'vuln' / 'apply.json'
        result = self.run_script('apply_upgrade.py', '--changes', changes, '--workspace', self.ws, '--out', applied)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.ws / 'service-a' / 'versions.conf').read_text(), 'jackson-databind: 2.13.4.2\n')
        self.assertEqual((self.ws / 'service-a' / 'gradle.properties').read_text(), 'unrelated=2.13.0\n')
        self.assertEqual((self.ws / 'service-b' / 'build.gradle').read_text(),
                         "implementation 'org.yaml:snakeyaml:1.35'\n")
        self.assertEqual(self.current_branch('service-a'), 'vuln/PROJ-123')

    def default_branch(self, repo):
        return self.current_branch(repo)

    def test_apply_refuses_wrong_branch_and_dirty_repo(self):
        self.locate()
        changes, applied = self.feature / 'vuln' / 'changes.json', self.feature / 'vuln' / 'apply.json'
        wrong = self.run_script('apply_upgrade.py', '--changes', changes, '--workspace', self.ws, '--out', applied,
                                '--branch', 'vuln/PROJ-123')
        self.assertEqual(wrong.returncode, 2)
        (self.ws / 'service-a' / 'scratch.txt').write_text('x')
        dirty = self.prepare('--base', self.default_branch('service-a'))
        self.assertEqual(dirty.returncode, 2)

    def test_main_chain_order_and_publish_off(self):
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads((self.feature / 'vuln' / 'build-results.json').read_text())
        self.assertTrue(data['all_passed'])
        self.assertEqual([r['repo'] for r in data['results']], ['platform', 'service-a', 'service-b'])
        self.assertEqual({r['step'] for r in data['results']}, {'build'})

    def test_publishing_chain_publishes_each_repo_after_build(self):
        self.run_script('build_chain.py', '--flow', 'nightly', '--feature-dir', self.feature, '--workspace', self.ws)
        data = json.loads((self.feature / 'vuln' / 'build-results.json').read_text())
        self.assertEqual([(r['repo'], r['step']) for r in data['results']],
                         [('platform', 'build'), ('platform', 'publish'),
                          ('service-a', 'build'), ('service-a', 'publish')])

    def test_failed_build_stops_chain_and_blocks_prs(self):
        config = json.loads(self.config.read_text())
        config['repo_overrides'] = {'service-a': {'command': [PY, '-c', 'import sys; sys.exit(3)']}}
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 1)
        data = json.loads((self.feature / 'vuln' / 'build-results.json').read_text())
        self.assertEqual(data['failed_repo'], 'service-a')
        self.assertNotIn('service-b', [r['repo'] for r in data['results']])
        pr = self.run_script('raise_prs.py', '--feature-dir', self.feature, '--workspace', self.ws, '--yes')
        self.assertEqual(pr.returncode, 6)
        self.assertIn('no PRs', pr.stderr)

    def test_pr_plan_targets_the_intake_parent_branch_and_names_non_ticket_sources(self):
        vuln = self.feature / 'vuln'
        (vuln / 'build-results.json').write_text(json.dumps({'all_passed': True}))
        (vuln / 'intake.json').write_text(json.dumps({'flow': 'main', 'ticket': 'PROJ-123', 'branch': 'vuln/PROJ-123',
                                                      'base': 'release/1.4', 'base_for': {'service-b': 'master'}}))
        (vuln / 'branches.json').write_text(json.dumps({'branch': 'vuln/PROJ-123', 'states': {}, 'missing': []}))
        (vuln / 'apply-results.json').write_text(json.dumps({'repos': {
            'service-a': {'branch': 'vuln/PROJ-123', 'files': ['a.conf']},
            'service-b': {'branch': 'vuln/PROJ-123', 'files': ['b.conf']}}}))
        (vuln / 'changes.json').write_text(json.dumps({'ticket': 'PROJ-123', 'flow': 'main', 'changes': [
            {'repo': 'service-a', 'dependency': 'g:a', 'old': '1', 'new': '2', 'file': 'a.conf'},
            {'repo': 'service-b', 'dependency': 'g:b', 'old': '1', 'new': '2', 'file': 'b.conf', 'source': 'a Trivy scan'}]}))
        plan = self.run_script('raise_prs.py', '--feature-dir', self.feature, '--workspace', self.ws)
        self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
        self.assertIn('service-a: branch vuln/PROJ-123 -> release/1.4', plan.stdout)
        self.assertIn('service-b: branch vuln/PROJ-123 -> master', plan.stdout)
        self.assertIn('Nothing pushed', plan.stdout)
        body = raise_prs.pr_body('PROJ-123', 'service-b', 'main',
                                 [{'dependency': 'g:b', 'old': '1', 'new': '2', 'file': 'b.conf', 'source': 'a Trivy scan'}],
                                 {}, 'footer line')
        self.assertIn('`g:b` is not listed in PROJ-123; it comes from a Trivy scan', body)
        self.assertTrue(body.endswith('footer line'))

    def test_check_only_keeps_the_recorded_parent_branches(self):
        for repo in ('platform', 'service-a', 'service-b'):
            git(self.ws / repo, 'branch', 'release/1.4')
        self.assertEqual(self.prepare('--base', 'release/1.4').returncode, 0)
        self.assertEqual(self.prepare('--check-only').returncode, 0)
        bases = json.loads((self.feature / 'vuln' / 'branches.json').read_text())['bases']
        self.assertEqual(bases.get('service-a'), 'release/1.4')

    def test_intake_validation(self):
        bad = self.run_script('intake.py', '--flow', 'main', '--ticket', 'nope', '--feature-dir', self.feature)
        self.assertEqual(bad.returncode, 2)
        bad = self.run_script('intake.py', '--flow', 'other', '--ticket', 'PROJ-123', '--feature-dir', self.feature)
        self.assertEqual(bad.returncode, 2)
        good = self.run_script('intake.py', '--flow', 'main', '--ticket', 'proj-123', '--feature-dir', self.feature)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads((self.feature / 'vuln' / 'intake.json').read_text())['ticket'], 'PROJ-123')


if __name__ == '__main__':
    unittest.main()
