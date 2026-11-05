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

import raise_prs  # noqa: E402
import read_report  # noqa: E402

PY = sys.executable
TICKET_TEXT = ('<p>jackson: com.fasterxml.jackson.core:jackson-databind 2.13.0 -> 2.13.4.2 (CVE-2022-42003)</p>'
               '<p>org.yaml:snakeyaml vulnerable 1.30 fixed in 1.33</p>'
               '<p>mystery-lib 3.1.0</p>')


def script(name, *args, cwd=None, stdin=None):
    return subprocess.run([PY, '-B', str(SCRIPTS / name), *map(str, args)], capture_output=True, text=True, cwd=cwd,
                          input=stdin)


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

    def test_report_is_read_from_a_file_or_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / 'ticket.json'
            report.write_text(json.dumps({'title': 'Upgrade jackson', 'description': TICKET_TEXT}))
            out = Path(tmp) / 'findings.json'
            done = script('read_report.py', '--report', report, '--ticket', 'PROJ-123', '--out', out)
            self.assertEqual(done.returncode, 0, done.stderr)
            data = json.loads(out.read_text())
            self.assertEqual((data['ticket'], data['title']), ('PROJ-123', 'Upgrade jackson'))
            self.assertEqual(len(data['findings']), 3)
            done = script('read_report.py', '--report', '-', '--out', out, stdin=TICKET_TEXT)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIsNone(json.loads(out.read_text())['ticket'])

    def test_missing_report_fails_clearly(self):
        result = script('read_report.py', '--report', 'no-such-report.txt', '--out', 'x.json')
        self.assertEqual(result.returncode, 2)
        self.assertIn('Cannot read the report', result.stderr)


REPORT = (
    'Vulnerability report of MAIN : 1.4.2\n\n'
    'IMAGE - example-org/app-image : VERSION/TAG - 1.4.2-100\n\n'
    'CVE\tSeverity\tImpacted Package\tversion\tfix version\tfile path\n'
    'CVE-2026-111497\tMEDIUM\tlibbrotli1\t1.2.0-3build1\t1.2.0-3ubuntu0.1\tpkg:deb/ubuntu/libbrotli1@1.2.0-3build1?arch=amd64\n'
    'CVE-2026-106121\tMEDIUM\torg.example:messaging-client\t5.35.0\t5.36.1\topt/app/lib/messaging-client-5.35.0.jar\n'
    'CVE-2026-106122\tMEDIUM\torg.example:messaging-client\t5.35.0\t5.36.0\topt/app/lib/messaging-client-5.35.0.jar\n\n'
    'IMAGE - example-org/worker-image : VERSION/TAG - 1.4.2-100\n\n'
    'CVE\tSeverity\tImpacted Package\tversion\tfix version\tfile path\n'
    'CVE-2026-106121\tMEDIUM\torg.example:messaging-client\t5.35.0\t5.36.1\topt/app/lib/messaging-client-5.35.0.jar\n')


class ReportTests(unittest.TestCase):
    def test_scanner_report(self):
        found = read_report.parse_findings(REPORT)
        by_name = {f['dependency']: f for f in found}
        client = by_name['org.example:messaging-client']
        self.assertEqual((client['status'], client['fixed_version']), ('ok', '5.36.1'))  # highest fix covers both CVEs
        self.assertEqual(client['advisories'], ['CVE-2026-106121', 'CVE-2026-106122'])
        self.assertEqual(client['images'], ['app-image', 'worker-image'])
        self.assertEqual(by_name['libbrotli1']['status'], 'out-of-scope')
        self.assertEqual(read_report.flow_hint(REPORT), 'main')


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.ws, self.feature = base / 'ws', base / 'feature'
        self.config = base / 'flows.json'
        config = json.loads((ROOT / 'config' / 'vuln-flows.json').read_text())
        config['flows'] = {'main': {'publish': False, 'repos': ['shared-lib', 'service-a', 'service-b']},
                           'hotfix': {'publish': True, 'repos': ['shared-lib', 'service-a']}}
        config['build']['command'] = [PY, '-c', 'print("built")']
        config['build']['publish_command'] = [PY, '-c', 'print("published")']
        self.config.write_text(json.dumps(config))
        self.make_repo('shared-lib', {
            'bom/versions.conf': 'jackson-databind = "2.13.0"\nsnakeyaml = "1.30"\n',
            'gradle.properties': 'unrelated=1.0.0\n'})
        self.make_repo('service-a', {
            'dependencies.conf': 'jackson-databind: 2.13.0\n',
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
        self.assertEqual(jackson['owners'], ['service-a', 'service-b', 'shared-lib'])
        # service-b changes the property definition, not the reference line or the other property
        service_b = [c for c in jackson['changes'] if c['repo'] == 'service-b']
        self.assertEqual([(c['file'], c['key']) for c in service_b], [('gradle.properties', 'jacksonVersion')])
        # service-a's unrelated property with the same number is left alone
        self.assertFalse(any(c['file'] == 'gradle.properties' for c in jackson['changes'] if c['repo'] == 'service-a'))
        # snakeyaml is vulnerable only in the platform reference; service-b pins a different version
        self.assertEqual(snake['scope'], 'platform-only')
        self.assertEqual(snake['owners'], ['shared-lib'])

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
        self.assertIn('MISSING: shared-lib, service-a, service-b', check.stdout)
        refused = self.prepare()
        self.assertEqual(refused.returncode, 8)
        self.assertIn('parent branch', refused.stderr)
        for repo in ('shared-lib', 'service-b'):
            git(self.ws / repo, 'branch', 'release/1.4')
        done = self.prepare('--base', 'release/1.4')
        self.assertEqual(done.returncode, 0, done.stderr)
        for repo in ('shared-lib', 'service-a', 'service-b'):
            self.assertEqual(self.current_branch(repo), 'vuln/PROJ-123')
        bases = json.loads((self.feature / 'vuln' / 'branches.json').read_text())['bases']
        self.assertEqual(bases['service-a'], 'release/1.4')

    def test_existing_branch_is_reused(self):
        for repo in ('shared-lib', 'service-a', 'service-b'):
            git(self.ws / repo, 'branch', 'vuln/PROJ-123')
        self.assertIn('exists in every repo', self.prepare('--check-only').stdout)
        self.assertEqual(self.prepare().returncode, 0)
        self.assertEqual(self.current_branch('service-b'), 'vuln/PROJ-123')

    def test_handoff_is_used_by_next_build_then_restored(self):
        (self.ws / 'shared-lib' / 'gradle.properties').write_text('version=9.9.9\n')
        (self.ws / 'service-a' / 'gradle.properties').write_text('platformVersion=1.0.0\n')
        check = [PY, '-c', 'import sys; sys.exit(0 if "platformVersion=9.9.9" in open("gradle.properties").read() else 1)']
        config = json.loads(self.config.read_text())
        config['repo_overrides'] = {'service-a': {'command': check}}
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'shared-lib', 'version_file': 'gradle.properties', 'version_key': 'version',
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
        sharedLibVersion="1.4.2"
        serviceAVersion="1.4.2"
}
'''
        for repo in ('service-a', 'service-b'):
            (self.ws / repo / 'gradle').mkdir(exist_ok=True)
            (self.ws / repo / 'gradle' / 'dependencies.conf').write_text(conf)
        stub = 'print("version: 7.7.7")'
        code = ('import sys; t = open("gradle/dependencies.conf").read()\n'
                'ok = "sharedLibVersion=\\"7.7.7\\"" in t and "serviceAVersion=\\"7.7.7\\"" in t\n'
                'sys.exit(0 if ok else 1)')
        check = [PY, '-c', code]
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', stub]
        config['repo_overrides'] = {'service-b': {'command': check}}
        config['flows']['main']['publish'] = True
        dep = 'gradle/dependencies.conf'
        config['handoff'] = [
            {'from': 'shared-lib', 'version_source': 'gradle',
             'to': [{'repo': 'service-a', 'file': dep, 'key': 'sharedLibVersion'},
                    {'repo': 'service-b', 'file': dep, 'key': 'sharedLibVersion'}]},
            {'from': 'service-a', 'version_source': 'gradle',
             'to': [{'repo': 'service-b', 'file': dep, 'key': 'serviceAVersion'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('sharedLibVersion 1.4.2 -> 7.7.7', result.stdout)
        # both keys in the same file are put back exactly, quotes included
        for repo in ('service-a', 'service-b'):
            self.assertEqual((self.ws / repo / 'gradle' / 'dependencies.conf').read_text(), conf)

    def test_handoff_without_a_gradle_version_is_reported_not_guessed(self):
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', 'print("version: unspecified")']
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'shared-lib', 'version_source': 'gradle',
                              'to': [{'repo': 'service-a', 'file': 'gradle.properties', 'key': 'unrelated'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('could not read its version from Gradle', result.stdout)
        self.assertEqual((self.ws / 'service-a' / 'gradle.properties').read_text(), 'unrelated=2.13.0\n')

    def changed_only(self, changed, order=None, rules=None, *extra):
        """Dry-run the chain in --changed-only mode and return (result, build-results.json)."""
        config = json.loads(self.config.read_text())
        if order:
            config['flows']['main']['repos'] = order
        dep = 'gradle/dependencies.conf'
        config['handoff'] = [{'from': frm, 'version_source': 'gradle',
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
        rules = [('shared-lib', 'sharedLibVersion', ['service-a', 'service-b']),
                 ('service-a', 'serviceAVersion', ['service-b'])]
        result, data = self.changed_only(['service-a'], rules=rules)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([r['repo'] for r in data['results']], ['service-a', 'service-b'])
        self.assertEqual(data['skipped'], ['shared-lib'])
        self.assertTrue(data['changed_only'])

    def test_changed_only_with_no_dependents_builds_just_the_changed_repo(self):
        rules = [('shared-lib', 'sharedLibVersion', ['service-a', 'service-b'])]
        result, data = self.changed_only(['service-b'], rules=rules)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([r['repo'] for r in data['results']], ['service-b'])
        self.assertEqual(data['skipped'], ['shared-lib', 'service-a'])

    def test_changed_only_follows_dependents_transitively(self):
        rules = [('shared-lib', 'sharedLibVersion', ['service-a']),
                 ('service-a', 'serviceAVersion', ['service-b'])]
        result, data = self.changed_only(['shared-lib'], rules=rules)
        self.assertEqual([r['repo'] for r in data['results']], ['shared-lib', 'service-a', 'service-b'])
        self.assertEqual(data['skipped'], [])

    def test_changed_only_needs_changes(self):
        result, _ = self.changed_only([], rules=[])
        self.assertEqual(result.returncode, 2)
        self.assertIn('nothing to build', result.stderr)

    def test_changed_only_warns_when_a_dependent_is_built_before_its_upstream(self):
        rules = [('service-a', 'serviceAVersion', ['service-b'])]
        result, data = self.changed_only(['service-a'], order=['service-b', 'service-a', 'shared-lib'], rules=rules)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([r['repo'] for r in data['results']], ['service-b', 'service-a'])
        self.assertTrue(any('service-b pins serviceAVersion' in w for w in data['warnings']))
        self.assertIn('warning:', result.stdout)

    def test_apply_and_handoff_keep_crlf_line_endings_byte_for_byte(self):
        crlf_props = b'a=1\r\nlz4JavaVersion=1.11.1\r\nb=2\r\n'
        crlf_conf = b'versions {\r\n        sharedLibVersion="1.4.2"\r\n}\r\n'
        (self.ws / 'service-a' / 'gradle').mkdir(exist_ok=True)
        (self.ws / 'service-a' / 'gradle.properties').write_bytes(crlf_props)
        (self.ws / 'service-b' / 'gradle').mkdir(exist_ok=True)
        (self.ws / 'service-b' / 'gradle' / 'dependencies.conf').write_bytes(crlf_conf)
        for repo in ('service-a', 'service-b'):
            git(self.ws / repo, 'checkout', '-q', '-b', 'vuln/PROJ-123')
        changes = self.feature / 'vuln' / 'changes.json'
        changes.write_text(json.dumps({'ticket': 'PROJ-123', 'flow': 'main', 'changes': [
            {'repo': 'service-a', 'file': 'gradle.properties', 'line': 2, 'key': 'lz4JavaVersion',
             'old': '1.11.1', 'new': '1.11.4'}]}))
        applied = self.run_script('apply_upgrade.py', '--changes', changes, '--workspace', self.ws,
                                  '--branch', 'vuln/PROJ-123', '--allow-dirty',
                                  '--out', self.feature / 'vuln' / 'applied.json')
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertEqual((self.ws / 'service-a' / 'gradle.properties').read_bytes(),
                         b'a=1\r\nlz4JavaVersion=1.11.4\r\nb=2\r\n')
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', 'print("version: 7.7.7")']
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'shared-lib', 'version_source': 'gradle',
                              'to': [{'repo': 'service-b', 'file': 'gradle/dependencies.conf',
                                      'key': 'sharedLibVersion'}]}]
        self.config.write_text(json.dumps(config))
        built = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                '--workspace', self.ws)
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self.assertIn('sharedLibVersion 1.4.2 -> 7.7.7', built.stdout)
        self.assertEqual((self.ws / 'service-b' / 'gradle' / 'dependencies.conf').read_bytes(), crlf_conf)

    def test_build_output_is_written_to_the_log_while_it_runs(self):
        config = json.loads(self.config.read_text())
        config['build']['command'] = [PY, '-c', 'print("> Task :compileScala"); print("done")']
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'hotfix', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('build log:', result.stdout)
        log = (self.feature / 'vuln' / 'build-shared-lib.log').read_text()
        self.assertIn('> Task :compileScala', log)

    def test_resume_reapplies_the_handoff_from_repos_already_published(self):
        conf = 'versions {\n        sharedLibVersion="1.4.2"\n}\n'
        (self.ws / 'service-a' / 'gradle').mkdir(exist_ok=True)
        (self.ws / 'service-a' / 'gradle' / 'dependencies.conf').write_text(conf)
        code = ('import sys\nt = open("gradle/dependencies.conf").read()\n'
                'sys.exit(0 if "sharedLibVersion=\\"7.7.7\\"" in t else 1)')
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', 'print("version: 7.7.7")']
        config['repo_overrides'] = {'service-a': {'command': [PY, '-c', code]}}
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'shared-lib', 'version_source': 'gradle',
                              'to': [{'repo': 'service-a', 'file': 'gradle/dependencies.conf',
                                      'key': 'sharedLibVersion'}]}]
        self.config.write_text(json.dumps(config))
        (self.feature / 'vuln' / 'changes.json').write_text(json.dumps(
            {'ticket': 'PROJ-123', 'flow': 'main', 'changes': [{'repo': 'shared-lib'}]}))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws, '--changed-only', '--from-repo', 'service-a')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('resuming at service-a', result.stdout)
        data = json.loads((self.feature / 'vuln' / 'build-results.json').read_text())
        self.assertNotIn('shared-lib', [r['repo'] for r in data['results']])
        self.assertTrue(data['all_passed'])
        self.assertEqual((self.ws / 'service-a' / 'gradle' / 'dependencies.conf').read_text(), conf)

    def test_resume_at_an_unselected_repo_is_refused(self):
        result, _ = self.changed_only(['service-b'], None, [], '--from-repo', 'shared-lib')
        self.assertEqual(result.returncode, 2)
        self.assertIn('not one of the repos to build', result.stderr)

    def test_next_run_restores_files_left_edited_by_a_stopped_run(self):
        conf = b'versions {\r\n        sharedLibVersion="1.4.2"\r\n}\r\n'
        target = self.ws / 'service-a' / 'gradle' / 'dependencies.conf'
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(conf.replace(b'1.4.2', b'9.9.9-STRAY'))
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
        (self.ws / 'service-a' / 'gradle' / 'dependencies.conf').write_text('        k="1.0.0"\n')
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', 'print("version: 7.7.7")']
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'shared-lib', 'version_source': 'gradle',
                              'to': [{'repo': 'service-a', 'file': 'gradle/dependencies.conf', 'key': 'k'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.feature / 'vuln' / 'handoff-backup.json').exists())

    def test_repo_env_override_applies_only_to_that_repo(self):
        config = json.loads(self.config.read_text())
        config['build']['command'] = [PY, '-c', 'import os; print("JDK=" + os.environ.get("JDK_TAG", "none"))']
        config['repo_overrides'] = {'shared-lib': {'env': {'JDK_TAG': 'seventeen'}}}
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        vuln = self.feature / 'vuln'
        self.assertIn('JDK=seventeen', (vuln / 'build-shared-lib.log').read_text())
        self.assertIn('JDK=none', (vuln / 'build-service-a.log').read_text())

    def test_version_command_uses_the_repos_env(self):
        (self.ws / 'service-a' / 'gradle').mkdir(exist_ok=True)
        (self.ws / 'service-a' / 'gradle' / 'dependencies.conf').write_text('        k="1.0.0"\n')
        config = json.loads(self.config.read_text())
        config['build']['version_command'] = [PY, '-c', 'import os; print("version: " + os.environ.get("JDK_TAG", "none"))']
        config['repo_overrides'] = {'shared-lib': {'env': {'JDK_TAG': 'seventeen'}}}
        config['flows']['main']['publish'] = True
        config['handoff'] = [{'from': 'shared-lib', 'version_source': 'gradle',
                              'to': [{'repo': 'service-a', 'file': 'gradle/dependencies.conf', 'key': 'k'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('k 1.0.0 -> seventeen', result.stdout)

    def test_chain_refuses_to_start_when_a_handoff_pin_was_edited_by_hand(self):
        conf = self.ws / 'service-a' / 'gradle' / 'dependencies.conf'
        conf.parent.mkdir(exist_ok=True)
        conf.write_text('        sharedLibVersion="1.4.2"\n')
        git(self.ws / 'service-a', 'add', '-A')
        git(self.ws / 'service-a', 'commit', '-qm', 'pins')
        conf.write_text('        sharedLibVersion="1.4.3-SNAPSHOT"\n')
        config = json.loads(self.config.read_text())
        config['handoff'] = [{'from': 'shared-lib', 'version_source': 'gradle',
                              'to': [{'repo': 'service-a', 'file': 'gradle/dependencies.conf', 'key': 'sharedLibVersion'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 2)
        self.assertIn('changed by hand', result.stderr)
        self.assertIn('sharedLibVersion is 1.4.3-SNAPSHOT, committed 1.4.2', result.stderr)

    def test_workspace_is_found_from_the_platform_repo_when_not_configured(self):
        import common
        config = {'workspace_root': str(self.ws / 'nowhere'),
                  'flows': {'main': {'repos': ['shared-lib', 'service-a']}}}
        previous = os.getcwd()
        try:
            os.chdir(self.ws / 'shared-lib')
            self.assertEqual(Path(common.resolve_workspace(config)).resolve(), self.ws.resolve())
        finally:
            os.chdir(previous)
        self.assertEqual(common.resolve_workspace(config, 'explicit'), 'explicit')
        config['workspace_root'] = str(self.ws)
        self.assertEqual(common.resolve_workspace(config), str(self.ws))

    def test_transitive_check_marks_only_not_found(self):
        findings = json.loads(self.findings.read_text())
        findings['findings'].append({'dependency': 'org.example:messaging-client', 'vulnerable_version': '5.35.0',
                                     'fixed_version': '5.36.1', 'status': 'ok'})
        self.findings.write_text(json.dumps(findings))
        plan = self.locate()
        rabbit = [r for r in plan['dependencies'] if r['dependency'] == 'org.example:messaging-client'][0]
        self.assertEqual(rabbit['decision'], 'not-found')
        config = json.loads(self.config.read_text())
        config['transitive']['command'] = [PY, '-c', 'print("+--- com.example:parent:1.0\\n     \\\\--- {dependency}:5.35.0")']
        self.config.write_text(json.dumps(config))
        result = self.run_script('transitive_check.py', '--changes', self.feature / 'vuln' / 'changes.json',
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stderr)
        after = json.loads((self.feature / 'vuln' / 'changes.json').read_text())
        rows = {r['dependency']: r for r in after['dependencies']}
        self.assertEqual(rows['org.example:messaging-client']['decision'], 'transitive')
        self.assertEqual(rows['org.yaml:snakeyaml']['decision'], 'change')

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
        self.assertEqual((self.ws / 'service-a' / 'dependencies.conf').read_text(), 'jackson-databind: 2.13.4.2\n')
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

    def test_deploy_chain_order_and_publish_off(self):
        result = self.run_script('build_chain.py', '--flow', 'main', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads((self.feature / 'vuln' / 'build-results.json').read_text())
        self.assertTrue(data['all_passed'])
        self.assertEqual([r['repo'] for r in data['results']], ['shared-lib', 'service-a', 'service-b'])
        self.assertEqual({r['step'] for r in data['results']}, {'build'})

    def test_release_chain_publishes_each_repo_after_build(self):
        self.run_script('build_chain.py', '--flow', 'hotfix', '--feature-dir', self.feature, '--workspace', self.ws)
        data = json.loads((self.feature / 'vuln' / 'build-results.json').read_text())
        self.assertEqual([(r['repo'], r['step']) for r in data['results']],
                         [('shared-lib', 'build'), ('shared-lib', 'publish'),
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
        for repo in ('shared-lib', 'service-a', 'service-b'):
            git(self.ws / repo, 'branch', 'release/1.4')
        self.assertEqual(self.prepare('--base', 'release/1.4').returncode, 0)
        self.assertEqual(self.prepare('--check-only').returncode, 0)
        bases = json.loads((self.feature / 'vuln' / 'branches.json').read_text())['bases']
        self.assertEqual(bases.get('service-a'), 'release/1.4')

    def test_intake_validation(self):
        for ticket in ('not a ticket', '../x', ''):
            bad = self.run_script('intake.py', '--flow', 'main', '--ticket', ticket, '--feature-dir', self.feature)
            self.assertEqual(bad.returncode, 2, ticket)
        bad = self.run_script('intake.py', '--flow', 'other', '--ticket', 'PROJ-123', '--feature-dir', self.feature)
        self.assertEqual(bad.returncode, 2)
        for ticket, kept in (('#PROJ-123', 'PROJ-123'), ('456', '456')):
            good = self.run_script('intake.py', '--flow', 'main', '--ticket', ticket, '--feature-dir', self.feature)
            self.assertEqual(good.returncode, 0, good.stderr)
            intake = json.loads((self.feature / 'vuln' / 'intake.json').read_text())
            self.assertEqual((intake['ticket'], intake['branch']), (kept, 'vuln/' + kept))


if __name__ == '__main__':
    unittest.main()
