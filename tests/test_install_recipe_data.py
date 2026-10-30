"""Run static Bash with fictional data/fake commands; no installs, network or models."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import yaml


RECIPE = Path(__file__).resolve().parents[1] / "recipes/make-amplifier-faster.yaml"


class InstallRecipeDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.marker = self.root / "SHOULD_NOT_EXIST"
        self.log = self.root / "calls.jsonl"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.recipe = yaml.safe_load(RECIPE.read_text())
        self.steps = {
            step["id"]: step
            for stage in self.recipe["stages"]
            for step in stage["steps"]
        }
        self.context = dict(self.recipe["context"])
        self.context["events_dir"] = str(self.root / "no-events")
        self.fake_tags = {"models": []}
        self.context["machine"] = {
            "prefer_error": "",
            "prefer_host": "auto",
            "chosen_host": "ollama",
        }
        fake = (
            "#!"
            + sys.executable
            + "\n"
            + """import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['FICTIONAL_RECIPE_LOG'], 'a') as handle:
    handle.write(json.dumps([name] + args) + '\\n')
if name == 'uname':
    print('Darwin' if args == ['-s'] else 'arm64')
elif name == 'sysctl':
    print('Apple fictional CPU' if args[-1] == 'machdep.cpu.brand_string' else '17179869184')
elif name == 'curl':
    print('0.001' if '-w' in args else os.environ.get('FICTIONAL_MODEL_LIST', '{"models":[]}'))
elif name == 'amplifier' and args == ['--version']:
    print('fictional-amplifier')
"""
        )
        for name in (
            "uname",
            "sysctl",
            "curl",
            "ollama",
            "amplifier",
            "brew",
            "uv",
            "nohup",
            "mlx_lm.server",
        ):
            path = self.bin / name
            path.write_text(fake)
            path.chmod(0o700)
        # Prevent import of any optional ML package; other snippets use real stdlib.
        python = self.bin / "python3"
        python.write_text(
            "#!"
            + sys.executable
            + "\n"
            + "import os, sys\n"
            + "if sys.argv[1:] == ['-c', 'import mlx_lm']: raise SystemExit(1)\n"
            + "os.execv("
            + repr(sys.executable)
            + ", ["
            + repr(sys.executable)
            + "] + sys.argv[1:])\n"
        )
        python.chmod(0o700)

    def render(self, value):
        def replace(match):
            result = self.context
            for part in match.group(1).split("."):
                result = result[part]
            return str(result)

        return re.sub(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}", replace, value)

    def run_step(self, name):
        step = self.steps[name]
        env = {
            "PATH": str(self.bin) + os.pathsep + "/usr/bin:/bin",
            "HOME": str(self.root),
            "TMPDIR": str(self.root),
            "FICTIONAL_RECIPE_LOG": str(self.log),
            "FICTIONAL_MODEL_LIST": json.dumps(self.fake_tags),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
        env.update(
            {key: self.render(value) for key, value in step.get("env", {}).items()}
        )
        result = subprocess.run(
            ["/bin/bash", "-c", self.render(step["command"])],
            env=env,
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertFalse(self.marker.exists(), "context was executed as shell source")
        return result

    def calls(self):
        return (
            [json.loads(line) for line in self.log.read_text().splitlines()]
            if self.log.exists()
            else []
        )

    def payload(self):
        return "$(touch " + str(self.marker) + ")'\"\\\nfictional"

    def test_every_bash_command_is_static_and_syntax_valid(self):
        for name, step in self.steps.items():
            if step.get("type") != "bash":
                continue
            with self.subTest(step=name):
                self.assertNotIn("{{", step["command"])
                result = subprocess.run(
                    ["/bin/bash", "-n"],
                    input=step["command"],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_preapproval_preference_is_literal_json_data(self):
        self.context["prefer_host"] = self.payload()
        result = self.run_step("detect")
        self.assertEqual(result.returncode, 0, result.stderr)
        machine = json.loads(result.stdout)
        self.assertEqual(machine["prefer_host"], self.context["prefer_host"])
        self.assertTrue(machine["prefer_error"])
        self.assertTrue(
            all(call[0] in {"uname", "sysctl", "curl"} for call in self.calls())
        )
        self.context["machine"] = machine
        self.assertNotEqual(self.run_step("guard-prefer-host").returncode, 0)

    def test_preapproval_endpoint_values_never_execute(self):
        for key in ("ollama_url", "mlx_url"):
            with self.subTest(key=key):
                self.context[key] = "http://127.0.0.1/" + self.payload()
                self.run_step("detect")
                self.context[key] = self.recipe["context"][key]

    def test_nonlocal_or_credential_endpoints_fail_before_probe(self):
        for url in (
            "https://example.invalid",
            "http://user:pass@localhost",
            "http://localhost?private=1",
            "http://localhost#fragment",
            "file:///tmp/model",
            "http://localhost:bad",
        ):
            with self.subTest(url=url):
                self.log.unlink(missing_ok=True)
                self.context["ollama_url"] = url
                self.assertNotEqual(self.run_step("detect").returncode, 0)
                self.assertEqual(self.calls(), [])

    def test_benign_preapproval_is_read_only(self):
        result = self.run_step("detect")
        self.assertEqual(result.returncode, 0, result.stderr)
        machine = json.loads(result.stdout)
        self.assertEqual(machine["chosen_host"], "ollama")
        self.context["machine"] = machine
        self.assertEqual(self.run_step("guard-prefer-host").returncode, 0)
        self.assertEqual(self.run_step("probe").returncode, 0)
        self.assertFalse(
            any(
                call[0] in {"ollama", "brew", "uv", "nohup", "mlx_lm.server"}
                for call in self.calls()
            )
        )
        self.assertFalse(
            any(
                call[0] == "amplifier"
                and call[1:] not in [["--version"], ["bundle", "list"]]
                for call in self.calls()
            )
        )

    def test_model_json_and_cli_preserve_literal_values(self):
        for name, key in (
            ("warm-model", "ollama_model"),
            ("warm-mlx-model", "mlx_model"),
        ):
            with self.subTest(step=name):
                self.log.unlink(missing_ok=True)
                self.context[key] = self.payload()
                result = self.run_step(name)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = [call for call in self.calls() if call[0] == "curl"]
                self.assertEqual(len(calls), 2)
                for call in calls:
                    self.assertEqual(
                        json.loads(call[call.index("-d") + 1])["model"],
                        self.context[key],
                    )

    def test_pull_model_is_one_literal_argument(self):
        self.context["ollama_model"] = self.payload()
        result = self.run_step("pull-model")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(["ollama", "pull", self.context["ollama_model"]], self.calls())

    def test_pull_model_requires_exact_json_name(self):
        for existing, pulls in (
            ("qwen3:0x6b", True),
            ("qwen3:0.6b-other", True),
            ("qwen3:0.6b", False),
        ):
            with self.subTest(existing=existing):
                self.log.unlink(missing_ok=True)
                self.fake_tags = {"models": [{"name": existing}]}
                self.assertEqual(self.run_step("pull-model").returncode, 0)
                actual = [call for call in self.calls() if call[0] == "ollama"]
                self.assertEqual(bool(actual), pulls)

    def test_bundle_sources_are_literal_arguments(self):
        for host, profile, key in (
            ("mlx", "routing", "mlx_bundle_source"),
            ("ollama", "routing", "routing_bundle_source"),
            ("ollama", "incumbent", "bundle_source"),
        ):
            with self.subTest(host=host, profile=profile):
                self.log.unlink(missing_ok=True)
                self.context["machine"]["chosen_host"] = host
                self.context["profile"] = profile
                self.context[key] = self.payload()
                self.assertEqual(self.run_step("add-rung").returncode, 0)
                self.assertIn(
                    ["amplifier", "bundle", "add", self.context[key]], self.calls()
                )

    def test_receipt_path_remains_data_and_json_escapes_it(self):
        self.context["events_dir"] = str(self.root / self.payload())
        self.context["machine"]["chosen_host"] = self.payload()
        result = self.run_step("check-receipts")
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(
            evidence["expected_backend"], self.context["machine"]["chosen_host"]
        )
        self.assertIn(self.context["events_dir"], evidence["note"])

    def test_approval_gate_remains_required_and_denies_by_default(self):
        preflight = next(
            stage for stage in self.recipe["stages"] if stage["name"] == "preflight"
        )
        self.assertIs(preflight["approval"]["required"], True)
        self.assertEqual(preflight["approval"]["default"], "deny")


if __name__ == "__main__":
    unittest.main()
