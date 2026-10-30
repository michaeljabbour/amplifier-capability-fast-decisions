"""Synthetic credential sentinels checked inside real candidate child processes."""
import importlib.util
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import battery_tasks as bt
import forge_e2e
import paired_scenarios as ps
import polyglot_tasks as pt
from grader_env import grader_env

SECRETS = ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'XAI_API_KEY', 'GOOGLE_API_KEY',
           'AWS_SECRET_ACCESS_KEY', 'BEARER_TOKEN', 'UNRELATED_PROVIDER_KEY', 'HTTP_PROXY')
GUARD = ('import os\nassert not set(' + repr(SECRETS) + ').intersection(os.environ), "credential inherited"\n'
         'assert os.environ["SERVICE_PORT"] == "4711"\n')


def load_tasks(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GraderEnvironmentBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name)
        env = {key: 'fictional-test-marker' for key in SECRETS}
        env['SERVICE_PORT'] = '4711'
        self.patch = mock.patch.dict(os.environ, env)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_allowlist_filters_unknowns_and_overrides_without_mutating_parent(self):
        result = grader_env({'OPENAI_API_KEY': 'fictional-test-marker', 'PYTHONPATH': '/fixture/src'})
        self.assertFalse(set(SECRETS).intersection(result))
        self.assertEqual(result['PYTHONPATH'], '/fixture/src')
        self.assertEqual(result['PATH'], os.environ['PATH'])
        self.assertEqual(result['SERVICE_PORT'], '4711')
        self.assertIn('OPENAI_API_KEY', os.environ)  # selected model harness still owns its auth

    def test_battery_snippet_import_child_gets_no_provider_credentials(self):
        (self.ws / 'candidate.py').write_text(GUARD + 'value = 42\n')
        result, error = bt._run_snippet(self.ws, 'import candidate\nprint(json.dumps(candidate.value))\n')
        self.assertIsNone(error)
        self.assertEqual(result, 42)

    def test_battery_cli_child_still_grades_normally_without_credentials(self):
        (self.ws / 'cli_tool.py').write_text(GUARD + bt._FIX_CLI_DRY_RUN)
        result = bt._evaluate_cli_dry_run(self.ws)
        self.assertEqual(result['failed'], 0, result)
        self.assertGreater(result['passed'], 0)

    def _check_tasks(self, name, relative):
        tasks = load_tasks(name, relative)
        (self.ws / 'src').mkdir()
        (self.ws / 'src' / 'candidate.py').write_text(GUARD + 'value = 42\n')
        result = tasks._py(self.ws, 'import candidate; print(candidate.value)')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '42')
        (self.ws / 'tests').mkdir()
        (self.ws / 'tests' / 'test_boundary.py').write_text(
            GUARD + 'import unittest\nimport candidate\nclass Check(unittest.TestCase):\n'
            ' def test_value(self): self.assertEqual(candidate.value, 42)\n')
        passed, detail = tasks._unittest(self.ws, 'test_boundary.py')
        self.assertTrue(passed, detail)

    def test_large_repo_candidate_import_and_unittest_child(self):
        self._check_tasks('grader_large_repo_tasks', 'evals/suites/large-repo-v0/tasks.py')

    def test_continuous_candidate_import_and_unittest_child(self):
        self._check_tasks('grader_continuous_tasks', 'evals/continuous/tasks.py')

    def test_polyglot_python_candidate_child(self):
        (self.ws / 'test_boundary.py').write_text(GUARD + 'def test_value(): assert 2 + 2 == 4\n')
        result = pt._python_run(self.ws, ['test_boundary.py'])
        self.assertEqual(result['failed'], 0, result)
        self.assertEqual(result['passed'], 1)

    def test_polyglot_other_language_common_boundary_scrubs_explicit_env_too(self):
        result = pt._run([sys.executable, '-c', GUARD + 'print("ordinary-output")'],
                         env=dict(os.environ), cwd=self.ws, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('ordinary-output', result.stdout)

    def test_paired_shell_grader_candidate_child(self):
        (self.ws / 'candidate.py').write_text(GUARD + 'print("ordinary-output")\n')
        result = ps._check_tests({'runner': 'cmd', 'cmd': shlex.join([sys.executable, 'candidate.py']),
                                  'expect_regex': 'ordinary-output'}, self.ws, self.ws)
        self.assertEqual(result['failed'], 0, result)

    def _check_forge(self, use_pytest):
        (self.ws / 'test_boundary.py').write_text(GUARD + 'import unittest\nclass Check(unittest.TestCase):\n'
                                                 ' def test_value(self): self.assertEqual(2 + 2, 4)\n')
        if use_pytest:
            passed, runner, detail = forge_e2e.run_workspace_tests(self.ws)
            self.assertEqual(runner, 'pytest')
        else:
            with mock.patch.object(forge_e2e, '_interpreter_with_pytest', return_value=None):
                passed, runner, detail = forge_e2e.run_workspace_tests(self.ws)
            self.assertEqual(runner, 'unittest')
        self.assertTrue(passed, detail)

    def test_forge_pytest_candidate_child(self):
        self._check_forge(True)

    def test_forge_unittest_candidate_child(self):
        self._check_forge(False)
