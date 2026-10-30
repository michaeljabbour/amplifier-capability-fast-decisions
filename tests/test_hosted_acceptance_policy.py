"""Manual acceptance script policy checks with a fake curl/clock/bench; no model or network."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def acceptance(tmp_path):
    tools = tmp_path / 'bin'
    tools.mkdir()
    curl = tools / 'curl'
    curl.write_text(f'#!{sys.executable}\n' + '''import json, os, pathlib, sys
pathlib.Path(os.environ['FAKE_CURL_CALLS']).write_text(json.dumps(sys.argv[1:]))
print(json.dumps({'model': os.environ.get('FAKE_RETURNED_MODEL', 'fast-decisions-judge'),
                  'choices': [{'logprobs': {'content': [{'top_logprobs': [{}] * 10}]}}]}))
''')
    curl.chmod(0o755)
    python = tools / 'python3'
    python.write_text('''#!/bin/sh
if [ "$1" = -c ] && [ "$2" = 'import time; print(time.time())' ]; then
  printf '0\\n'
else
  exec "$TEST_PYTHON" "$@"
fi
''')
    python.chmod(0o755)
    bench = tools / 'afast'
    bench.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_BENCH_CALLS"
printf '{"fixture": true}\\n'
''')
    bench.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k in {'PATH', 'HOME', 'LANG', 'LC_ALL'}}
    env.update(PATH=str(tools) + os.pathsep + env.get('PATH', ''), TEST_PYTHON=sys.executable,
               JUDGE_API_KEY='fictional-scoped-test-key', ACCEPT_PROBES='1',
               FAKE_CURL_CALLS=str(tmp_path / 'curl-calls.json'), FAKE_BENCH_CALLS=str(tmp_path / 'bench-calls'))

    def run(url, model='fast-decisions-judge'):
        result = subprocess.run(['bash', str(ROOT / 'deploy/hosted-judge/accept.sh')],
                                cwd=tmp_path, env=dict(env, JUDGE_API_BASE=url, FAKE_RETURNED_MODEL=model),
                                text=True, capture_output=True, timeout=15)
        return result, Path(env['FAKE_CURL_CALLS']), Path(env['FAKE_BENCH_CALLS'])

    return run


@pytest.mark.parametrize('url', [
    'http://example.com/v1', 'http://10.0.0.5/v1', 'http://localhost.evil.test/v1',
    'http://127.0.0.1.evil.test/v1', 'ftp://localhost/v1', 'file:///tmp/judge',
    'https://user:password@example.com/v1', 'https://example.com/v1?key=private',
    'https://example.com/v1#fragment', 'http://localhost:99999/v1',
])
def test_refuses_unsafe_base_before_any_request(acceptance, url):
    result, curl_calls, bench_calls = acceptance(url)
    assert result.returncode != 0
    assert not curl_calls.exists()
    assert not bench_calls.exists()
    assert 'fictional-scoped-test-key' not in result.stdout + result.stderr


@pytest.mark.parametrize('url', ['https://example.com/v1', 'http://localhost:1234/v1',
                                 'http://127.0.0.1:1234/v1', 'http://[::1]:1234/v1'])
def test_allows_https_and_loopback_only(acceptance, url):
    result, curl_calls, bench_calls = acceptance(url)
    assert result.returncode == 0, result.stdout + result.stderr
    assert url + '/chat/completions' in json.loads(curl_calls.read_text())
    assert len(bench_calls.read_text().splitlines()) == 2
    # All requests and clocks here are fakes; this is not provider/latency acceptance.


def test_rejects_model_id_substring_match(acceptance):
    result, curl_calls, bench_calls = acceptance('https://example.com/v1', 'other-fast-decisions-judge-extra')
    assert result.returncode != 0
    assert curl_calls.exists()
    assert not bench_calls.exists()
    assert 'model id mismatch on 1/1' in result.stdout
