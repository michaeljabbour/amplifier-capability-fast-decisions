"""Regrade's preserved workspace boundary: crafted tar data, fake grader, no model calls."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def regrade_fixture(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('paired_archive_safety_fixture', ROOT / 'evals/paired.py')
    paired = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, paired)
    spec.loader.exec_module(paired)
    out = tmp_path / 'campaign'
    out.mkdir()
    run_root = tmp_path / 'runs'
    snapshot_dir = run_root / 'session/turn-snapshots'
    snapshot_dir.mkdir(parents=True)
    archive = snapshot_dir / 't1.tar.gz'
    (out / 'state.json').write_text(json.dumps({'waves': {'w': {'accepted_attempt': 1, 'attempts': [
        {'attempt': 1, 'root': str(run_root), 'sessions': [{'key': 'session', 'scenario': 'fictional'}]}
    ]}}}))
    extracted = tmp_path / 'extracted'
    extracted.mkdir()
    destinations = []

    class TemporaryDirectory:
        def __enter__(self):
            path = extracted / f'scope{len(destinations)}'
            path.mkdir()
            destinations.append(path)
            return str(path)

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(paired, 'tempfile', SimpleNamespace(TemporaryDirectory=TemporaryDirectory))
    grades = []

    def grade(*args):
        grades.append(args)
        return {'checks': 1, 'failed': 0}

    monkeypatch.setattr(paired.ps, 'grade_turn', grade)
    backend = SimpleNamespace(result=lambda root, key: {'turns': [{'index': 1, 'final_message': 'fixture'}]},
                              run_dir=lambda root, key: root / key)

    def pack(entries):
        with tarfile.open(archive, 'w:gz') as tf:
            for name, kind, body in entries:
                member = tarfile.TarInfo(name)
                member.mode = 0o755 if kind == 'dir' else 0o644
                if kind == 'dir':
                    member.type = tarfile.DIRTYPE
                    tf.addfile(member)
                elif kind in ('symlink', 'hardlink'):
                    member.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE
                    member.linkname = str(body)
                    tf.addfile(member)
                else:
                    data = body.encode()
                    member.size = len(data)
                    tf.addfile(member, io.BytesIO(data))

    def run(passes=1):
        return paired.regrade(out, backend, {'fictional': object()}, {'fictional': tmp_path / 'snapshot'}, passes=passes)

    return tmp_path, paired, pack, run, grades, destinations


@pytest.mark.parametrize('attack', ['traversal', 'absolute', 'symlink', 'hardlink'])
def test_rejects_escape_members_before_writes_or_grading(regrade_fixture, attack):
    tmp, paired, pack, run, grades, destinations = regrade_fixture
    outside = tmp / 'outside.txt'
    outside.write_text('preserve outside sentinel')
    outside_dir = tmp / 'outside-dir'
    outside_dir.mkdir()
    payload = outside_dir / 'payload.txt'
    payload.write_text('preserve outside payload')
    entries = [('ws', 'dir', ''), ('ws/first.txt', 'file', 'benign first member')]
    if attack == 'traversal':
        entries.append(('../../outside.txt', 'file', 'attack'))
    elif attack == 'absolute':
        entries.append((str(outside), 'file', 'attack'))
    elif attack == 'symlink':
        entries += [('ws/link', 'symlink', outside_dir), ('ws/link/payload.txt', 'file', 'attack')]
    else:
        entries += [('ws/link', 'hardlink', outside), ('ws/link', 'file', 'attack')]
    pack(entries)
    with pytest.raises((paired.PairedError, tarfile.FilterError)):
        run()
    assert outside.read_text() == 'preserve outside sentinel'
    assert payload.read_text() == 'preserve outside payload'
    assert not grades
    assert not list(destinations[0].iterdir())  # full preflight, even before benign member writes.


def test_regular_workspace_roundtrip_and_repeat(regrade_fixture):
    _, _, pack, run, grades, destinations = regrade_fixture
    pack([('ws', 'dir', ''), ('ws/note.txt', 'file', 'benign workspace')])
    result = run(passes=2)
    assert result == {'graded_turns': 1, 'passes': 2, 'deterministic': True, 'differs_from_recorded': []}
    assert len(grades) == 2
    assert all((path / 'ws/note.txt').read_text() == 'benign workspace' for path in destinations)


def test_no_unsafe_fallback_without_data_filter(regrade_fixture, monkeypatch):
    _, paired, pack, run, grades, destinations = regrade_fixture
    pack([('ws', 'dir', ''), ('ws/note.txt', 'file', 'benign workspace')])
    monkeypatch.setattr(tarfile, 'data_filter', None)
    with pytest.raises(paired.PairedError, match='data-filter support'):
        run()
    assert not grades
    assert not list(destinations[0].iterdir())
