"""Standard-library tests for the vulnerability upgrade scripts. Run: python -m unittest discover tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts' / 'vuln'
sys.path.insert(0, str(SCRIPTS))

import agility_fetch  # noqa: E402

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
        found = {f['dependency']: f for f in agility_fetch.parse_findings(TICKET_TEXT) if f['dependency']}
        jackson = found['com.fasterxml.jackson.core:jackson-databind']
        self.assertEqual((jackson['vulnerable_version'], jackson['fixed_version']), ('2.13.0', '2.13.4.2'))
        self.assertEqual(jackson['advisory'], 'CVE-2022-42003')
        snake = found['org.yaml:snakeyaml']
        self.assertEqual((snake['vulnerable_version'], snake['fixed_version']), ('1.30', '1.33'))

    def test_incomplete_line_needs_confirmation(self):
        item = [f for f in agility_fetch.parse_findings(TICKET_TEXT) if f['dependency'] is None][0]
        self.assertEqual(item['status'], 'needs-confirmation')

    def test_missing_token_fails_without_leaking(self):
        result = script('agility_fetch.py', '--ticket', 'D-12345', '--out', 'x.json')
        self.assertEqual(result.returncode, 2)
        self.assertIn('AGILITY_TOKEN', result.stderr)


REPORT = (
    'Vulnerability report of DEPLOY : 26.3.2\n\n'
    'IMAGE - xebialabsunsupported/xl-deploy : VERSION/TAG - 26.3.2-1018.800\n\n'
    'CVE\tSeverity\tImpacted Package\tversion\tfix version\tfile path\n'
    'CVE-2026-111497\tMEDIUM\tlibbrotli1\t1.2.0-3build1\t1.2.0-3ubuntu0.1\tpkg:deb/ubuntu/libbrotli1@1.2.0-3build1?arch=amd64\n'
    'CVE-2026-106121\tMEDIUM\tcom.rabbitmq:amqp-client\t5.35.0\t5.36.1\topt/xebialabs/mq-libs/amqp-client-5.35.0.jar\n'
    'CVE-2026-106122\tMEDIUM\tcom.rabbitmq:amqp-client\t5.35.0\t5.36.0\topt/xebialabs/mq-libs/amqp-client-5.35.0.jar\n\n'
    'IMAGE - xebialabsunsupported/deploy-task-engine : VERSION/TAG - 26.3.2-1018.800\n\n'
    'CVE\tSeverity\tImpacted Package\tversion\tfix version\tfile path\n'
    'CVE-2026-106121\tMEDIUM\tcom.rabbitmq:amqp-client\t5.35.0\t5.36.1\topt/xebialabs/mq-libs/amqp-client-5.35.0.jar\n')


class ReportTests(unittest.TestCase):
    def test_scanner_report(self):
        found = agility_fetch.parse_findings(REPORT)
        by_name = {f['dependency']: f for f in found}
        amqp = by_name['com.rabbitmq:amqp-client']
        self.assertEqual((amqp['status'], amqp['fixed_version']), ('ok', '5.36.1'))  # highest fix covers both CVEs
        self.assertEqual(amqp['advisories'], ['CVE-2026-106121', 'CVE-2026-106122'])
        self.assertEqual(amqp['images'], ['deploy-task-engine', 'xl-deploy'])
        self.assertEqual(by_name['libbrotli1']['status'], 'out-of-scope')
        self.assertEqual(agility_fetch.flow_hint(REPORT), 'deploy')


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.ws, self.feature = base / 'ws', base / 'feature'
        self.config = base / 'flows.json'
        config = json.loads((ROOT / 'config' / 'vuln-flows.json').read_text())
        config['flows'] = {'deploy': {'publish': False, 'repos': ['xl-platform', 'service-a', 'service-b']},
                           'release': {'publish': True, 'repos': ['xl-platform', 'service-a']}}
        config['build']['command'] = [PY, '-c', 'print("built")']
        config['build']['publish_command'] = [PY, '-c', 'print("published")']
        self.config.write_text(json.dumps(config))
        self.make_repo('xl-platform', {
            'xl-reference/versions.conf': 'jackson-databind = "2.13.0"\nsnakeyaml = "1.30"\n',
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
        self.findings.write_text(json.dumps({'ticket': 'D-12345', 'findings': findings}))

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
        self.assertEqual(self.run_script('find_versions.py', '--flow', 'deploy', '--workspace', self.ws,
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
        self.assertEqual(jackson['owners'], ['service-a', 'service-b', 'xl-platform'])
        # service-b changes the property definition, not the reference line or the other property
        service_b = [c for c in jackson['changes'] if c['repo'] == 'service-b']
        self.assertEqual([(c['file'], c['key']) for c in service_b], [('gradle.properties', 'jacksonVersion')])
        # service-a's unrelated property with the same number is left alone
        self.assertFalse(any(c['file'] == 'gradle.properties' for c in jackson['changes'] if c['repo'] == 'service-a'))
        # snakeyaml is vulnerable only in the platform reference; service-b pins a different version
        self.assertEqual(snake['scope'], 'platform-only')
        self.assertEqual(snake['owners'], ['xl-platform'])

    def current_branch(self, repo):
        return subprocess.run(['git', 'branch', '--show-current'], cwd=self.ws / repo,
                              capture_output=True, text=True).stdout.strip()

    def prepare(self, *extra):
        return self.run_script('prepare_branches.py', '--feature-dir', self.feature, '--workspace', self.ws,
                               '--flow', 'deploy', '--branch', 'vuln/D-12345', *extra)

    def test_missing_branch_asks_for_parent_then_creates_from_it(self):
        git(self.ws / 'service-a', 'branch', 'release/26.3')
        check = self.prepare('--check-only')
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn('MISSING: xl-platform, service-a, service-b', check.stdout)
        refused = self.prepare()
        self.assertEqual(refused.returncode, 8)
        self.assertIn('parent branch', refused.stderr)
        for repo in ('xl-platform', 'service-b'):
            git(self.ws / repo, 'branch', 'release/26.3')
        done = self.prepare('--base', 'release/26.3')
        self.assertEqual(done.returncode, 0, done.stderr)
        for repo in ('xl-platform', 'service-a', 'service-b'):
            self.assertEqual(self.current_branch(repo), 'vuln/D-12345')
        bases = json.loads((self.feature / 'vuln' / 'branches.json').read_text())['bases']
        self.assertEqual(bases['service-a'], 'release/26.3')

    def test_existing_branch_is_reused(self):
        for repo in ('xl-platform', 'service-a', 'service-b'):
            git(self.ws / repo, 'branch', 'vuln/D-12345')
        self.assertIn('exists in every repo', self.prepare('--check-only').stdout)
        self.assertEqual(self.prepare().returncode, 0)
        self.assertEqual(self.current_branch('service-b'), 'vuln/D-12345')

    def test_handoff_is_used_by_next_build_then_restored(self):
        (self.ws / 'xl-platform' / 'gradle.properties').write_text('version=9.9.9\n')
        (self.ws / 'service-a' / 'gradle.properties').write_text('platformVersion=1.0.0\n')
        check = [PY, '-c', 'import sys; sys.exit(0 if "platformVersion=9.9.9" in open("gradle.properties").read() else 1)']
        config = json.loads(self.config.read_text())
        config['repo_overrides'] = {'service-a': {'command': check}}
        config['flows']['deploy']['publish'] = True
        config['handoff'] = [{'from': 'xl-platform', 'version_file': 'gradle.properties', 'version_key': 'version',
                              'to': [{'repo': 'service-a', 'file': 'gradle.properties', 'key': 'platformVersion'},
                                     {'repo': 'service-b', 'file': 'gradle.properties', 'key': 'missingKey'}]}]
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'deploy', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('platformVersion 1.0.0 -> 9.9.9', result.stdout)
        self.assertIn('missingKey not found', result.stdout)
        self.assertEqual((self.ws / 'service-a' / 'gradle.properties').read_text(), 'platformVersion=1.0.0\n')

    def test_transitive_check_marks_only_not_found(self):
        findings = json.loads(self.findings.read_text())
        findings['findings'].append({'dependency': 'com.rabbitmq:amqp-client', 'vulnerable_version': '5.35.0',
                                     'fixed_version': '5.36.1', 'status': 'ok'})
        self.findings.write_text(json.dumps(findings))
        plan = self.locate()
        rabbit = [r for r in plan['dependencies'] if r['dependency'] == 'com.rabbitmq:amqp-client'][0]
        self.assertEqual(rabbit['decision'], 'not-found')
        config = json.loads(self.config.read_text())
        config['transitive']['command'] = [PY, '-c', 'print("+--- com.example:parent:1.0\\n     \\\\--- {dependency}:5.35.0")']
        self.config.write_text(json.dumps(config))
        result = self.run_script('transitive_check.py', '--changes', self.feature / 'vuln' / 'changes.json',
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stderr)
        after = json.loads((self.feature / 'vuln' / 'changes.json').read_text())
        rows = {r['dependency']: r for r in after['dependencies']}
        self.assertEqual(rows['com.rabbitmq:amqp-client']['decision'], 'transitive')
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
        self.assertEqual(self.current_branch('service-a'), 'vuln/D-12345')

    def default_branch(self, repo):
        return self.current_branch(repo)

    def test_apply_refuses_wrong_branch_and_dirty_repo(self):
        self.locate()
        changes, applied = self.feature / 'vuln' / 'changes.json', self.feature / 'vuln' / 'apply.json'
        wrong = self.run_script('apply_upgrade.py', '--changes', changes, '--workspace', self.ws, '--out', applied,
                                '--branch', 'vuln/D-12345')
        self.assertEqual(wrong.returncode, 2)
        (self.ws / 'service-a' / 'scratch.txt').write_text('x')
        dirty = self.prepare('--base', self.default_branch('service-a'))
        self.assertEqual(dirty.returncode, 2)

    def test_deploy_chain_order_and_publish_off(self):
        result = self.run_script('build_chain.py', '--flow', 'deploy', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads((self.feature / 'vuln' / 'build-results.json').read_text())
        self.assertTrue(data['all_passed'])
        self.assertEqual([r['repo'] for r in data['results']], ['xl-platform', 'service-a', 'service-b'])
        self.assertEqual({r['step'] for r in data['results']}, {'build'})

    def test_release_chain_publishes_each_repo_after_build(self):
        self.run_script('build_chain.py', '--flow', 'release', '--feature-dir', self.feature, '--workspace', self.ws)
        data = json.loads((self.feature / 'vuln' / 'build-results.json').read_text())
        self.assertEqual([(r['repo'], r['step']) for r in data['results']],
                         [('xl-platform', 'build'), ('xl-platform', 'publish'),
                          ('service-a', 'build'), ('service-a', 'publish')])

    def test_failed_build_stops_chain_and_blocks_prs(self):
        config = json.loads(self.config.read_text())
        config['repo_overrides'] = {'service-a': {'command': [PY, '-c', 'import sys; sys.exit(3)']}}
        self.config.write_text(json.dumps(config))
        result = self.run_script('build_chain.py', '--flow', 'deploy', '--feature-dir', self.feature,
                                 '--workspace', self.ws)
        self.assertEqual(result.returncode, 1)
        data = json.loads((self.feature / 'vuln' / 'build-results.json').read_text())
        self.assertEqual(data['failed_repo'], 'service-a')
        self.assertNotIn('service-b', [r['repo'] for r in data['results']])
        pr = self.run_script('raise_prs.py', '--feature-dir', self.feature, '--workspace', self.ws, '--yes')
        self.assertEqual(pr.returncode, 6)
        self.assertIn('no PRs', pr.stderr)

    def test_intake_validation(self):
        bad = self.run_script('intake.py', '--flow', 'deploy', '--ticket', 'nope', '--feature-dir', self.feature)
        self.assertEqual(bad.returncode, 2)
        bad = self.run_script('intake.py', '--flow', 'other', '--ticket', 'D-12345', '--feature-dir', self.feature)
        self.assertEqual(bad.returncode, 2)
        good = self.run_script('intake.py', '--flow', 'deploy', '--ticket', 'd-12345', '--feature-dir', self.feature)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads((self.feature / 'vuln' / 'intake.json').read_text())['ticket'], 'D-12345')


if __name__ == '__main__':
    unittest.main()
