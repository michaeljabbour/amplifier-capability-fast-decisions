"""Offline launcher regressions: fake validators, no model or real scenario execution."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
REL = Path('evals/paired/scenarios/holdout-v3')


@pytest.fixture
def launchers(tmp_path):
    repo = tmp_path / 'fixture-repo'
    here = repo / REL
    here.mkdir(parents=True)
    for name in ('run_all_b.sh', 'run_all_c.sh'):
        shutil.copyfile(ROOT / REL / name, here / name)
    for directory in ('mixed', 'polyglot', 'knowledge', 'repos'):
        (here / directory).mkdir()
    (here / 'mixed/first.yaml').write_text('id: first\n')
    (here / 'polyglot/second.yaml').write_text('id: second\n')
    (here / 'knowledge/first.yaml').write_text('id: first\n')
    (here / 'repos/second.yaml').write_text('id: second\n')
    tools = tmp_path / 'tools'
    tools.mkdir()
    memory = tools / 'memory_pressure'
    memory.write_text('#!/bin/sh\nprintf "System-wide memory free percentage: %s%%\\n" "${FAKE_FREE:-90}"\n')
    memory.chmod(0o755)
    validator = tools / 'python3'
    validator.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_CALLS"
if [ "${FAKE_QUIET:-0}" = 0 ]; then printf 'fixture validator output\\n'; fi
case "${FAKE_FAIL_ID:-}" in
  '') exit 0 ;;
  *) case " $* " in *" --ids $FAKE_FAIL_ID "*) exit 7 ;; esac ;;
esac
exit 0
''')
    validator.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k in {'PATH', 'HOME', 'LANG', 'LC_ALL'}}
    env.update(PATH=str(tools) + os.pathsep + env.get('PATH', ''), FAKE_CALLS=str(tmp_path / 'calls'), B_OUT=str(tmp_path / 'batch-b'))

    def run(batch, *args, **extra):
        active = dict(env, **extra)
        result = subprocess.run(['bash', str(here / f'run_all_{batch}.sh'), *map(str, args)], cwd=tmp_path,
                                env=active, text=True, capture_output=True, timeout=10)
        calls = Path(env['FAKE_CALLS']).read_text() if Path(env['FAKE_CALLS']).exists() else ''
        return result, calls

    return tmp_path, here, env, run


@pytest.mark.parametrize('batch', ['b', 'c'])
def test_failure_survives_later_success(launchers, batch):
    tmp, _, _, run = launchers
    args = ('first', 'second') if batch == 'b' else (tmp / 'new.jsonl',)
    result, calls = run(batch, *args, FAKE_FAIL_ID='first')
    assert result.returncode == 1, result.stderr
    assert '--ids first' in calls and '--ids second' in calls
    assert 'FAILED first' in result.stderr


@pytest.mark.parametrize('batch', ['b', 'c'])
def test_quiet_success_is_success(launchers, batch):
    tmp, _, _, run = launchers
    args = ('first',) if batch == 'b' else (tmp / 'new.jsonl',)
    result, calls = run(batch, *args, FAKE_QUIET='1')
    assert result.returncode == 0, result.stderr
    assert calls


@pytest.mark.parametrize('batch', ['b', 'c'])
def test_memory_skip_is_incomplete(launchers, batch):
    tmp, _, _, run = launchers
    args = ('first',) if batch == 'b' else (tmp / 'new.jsonl',)
    result, calls = run(batch, *args, FAKE_FREE='20')
    assert result.returncode == 2, result.stderr
    assert 'SKIP' in result.stderr
    assert not calls


def test_batch_b_rejects_output_path_escape(launchers):
    tmp, _, _, run = launchers
    result, calls = run('b', '../../outside')
    assert result.returncode == 2
    assert not calls
    assert not (tmp / 'outside.json').exists()


def test_batch_b_does_not_overwrite_existing_result(launchers):
    _, _, env, run = launchers
    output = Path(env['B_OUT'])
    output.mkdir()
    saved = output / 'first.json'
    saved.write_text('historical receipt\n')
    result, calls = run('b', 'first')
    assert result.returncode == 1
    assert saved.read_text() == 'historical receipt\n'
    assert not calls


def test_batch_c_requires_new_output_and_preserves_existing(launchers):
    tmp, here, _, run = launchers
    saved = tmp / 'historical.jsonl'
    saved.write_text('historical receipt\n')
    result, calls = run('c', saved)
    assert result.returncode == 2
    assert saved.read_text() == 'historical receipt\n'
    assert not calls
    result, _ = run('c')
    assert result.returncode == 2
    assert not (here / 'validation-c.jsonl').exists()


@pytest.mark.parametrize('batch', ['b', 'c'])
def test_no_scenarios_is_incomplete(launchers, batch):
    tmp, here, _, run = launchers
    for path in here.glob('*/*.yaml'):
        path.unlink()
    args = () if batch == 'b' else (tmp / 'new.jsonl',)
    result, calls = run(batch, *args)
    assert result.returncode == 2
    assert not calls


def test_documented_cleanup_preview_keeps_ignored_research(tmp_path):
    agent_text = (ROOT / 'AGENTS.md').read_text()
    preview = 'git clean -ndX -- build/ dist/ .ruff_cache/'
    assert f'`{preview}`' in agent_text
    repo = tmp_path / 'cleanup-fixture'
    repo.mkdir()
    subprocess.run(['git', '-c', 'core.fsmonitor=false', 'init', '-q', str(repo)], check=True)
    (repo / '.gitignore').write_text('build/\ndist/\n.ruff_cache/\n.research/\n.venv/\n')
    for rel in ['build/disposable.o', 'dist/disposable.whl', '.ruff_cache/disposable', '.research/market/keep.md', '.venv/keep']:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rel)
    before = {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts}
    result = subprocess.run(preview.split(), cwd=repo, text=True, capture_output=True, check=True)
    assert 'build/' in result.stdout and 'dist/' in result.stdout and '.ruff_cache/' in result.stdout
    assert '.research' not in result.stdout and '.venv' not in result.stdout
    after = {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts}
    assert after == before  # git clean was preview-only; no data deleted.
