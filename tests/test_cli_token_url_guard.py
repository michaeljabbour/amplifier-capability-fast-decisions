"""Bearer tokens must only be sent over https or to loopback http endpoints."""

from __future__ import annotations

import urllib.request

import pytest

from amplifier_fast_decisions import cli
from amplifier_fast_decisions.cli import _token_url_allowed


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/v1",
        "HTTPS://example.com",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://[::1]:8080",
    ],
)
def test_allowed(url):
    assert _token_url_allowed(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/v1",
        "http://10.0.0.5:8000",
        "http://localhost.evil.com",
        "http://127.0.0.1.evil.com",
        "ftp://example.com",
        "file:///etc/passwd",
        "example.com",
        "",
    ],
)
def test_refused(url):
    assert not _token_url_allowed(url)


class _Boom:
    def __init__(self):
        self.called = False


def _no_network(monkeypatch):
    seen = _Boom()

    def fake(*a, **k):
        seen.called = True
        raise OSError("blocked")

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return seen


def test_hosted_refuses_token_over_plain_http(monkeypatch):
    seen = _no_network(monkeypatch)
    monkeypatch.setenv("FAST_DECISIONS_HOSTED_URL", "http://example.com/v1")
    monkeypatch.setenv("FAST_DECISIONS_HOSTED_TOKEN_ENV", "FD_TEST_TOKEN")
    monkeypatch.setenv("FD_TEST_TOKEN", "sekret")
    result = cli._hosted_server_check()
    assert result["state"] == "refused_insecure_url"
    assert result["ok"] is False
    assert "sekret" not in repr(result)
    assert not seen.called


def test_laya_refuses_token_over_plain_http(monkeypatch):
    seen = _no_network(monkeypatch)
    monkeypatch.setenv("FAST_DECISIONS_LAYA_URL", "http://example.com")
    monkeypatch.setenv("FAST_DECISIONS_LAYA_TOKEN_ENV", "FD_TEST_TOKEN")
    monkeypatch.setenv("FD_TEST_TOKEN", "sekret")
    result = cli._laya_server_check()
    assert result["state"] == "refused_insecure_url"
    assert "sekret" not in repr(result)
    assert not seen.called


def test_hosted_loopback_attaches_token(monkeypatch):
    headers = {}

    class R:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake(req, timeout=None):
        headers.update(dict(req.header_items()))
        return R()

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    monkeypatch.setenv("FAST_DECISIONS_HOSTED_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("FAST_DECISIONS_HOSTED_TOKEN_ENV", "FD_TEST_TOKEN")
    monkeypatch.setenv("FD_TEST_TOKEN", "sekret")
    assert cli._hosted_server_check()["state"] == "reachable"
    assert headers.get("Authorization") == "Bearer sekret"


def test_no_token_plain_http_still_probes(monkeypatch):
    seen = _no_network(monkeypatch)
    monkeypatch.setenv("FAST_DECISIONS_LAYA_URL", "http://example.com")
    monkeypatch.setenv("FAST_DECISIONS_LAYA_TOKEN_ENV", "FD_TEST_UNSET")
    monkeypatch.delenv("FD_TEST_UNSET", raising=False)
    result = cli._laya_server_check()
    assert result["state"] == "unreachable"
    assert seen.called
