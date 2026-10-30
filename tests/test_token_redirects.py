"""Credentialed probes must not forward tokens to redirected endpoints."""

import urllib.request

import pytest

from amplifier_fast_decisions import cli


@pytest.mark.parametrize("backend", ["hosted", "laya"])
@pytest.mark.parametrize("redirect", ["http://other.example/health", "https://other.example/health"])
def test_probe_token_is_not_forwarded_to_redirect(monkeypatch, backend, redirect):
    requests = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        requests.append(request)
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("FD_REDIRECT_FIXTURE", "dummy-redirect-credential")
    monkeypatch.setenv(f"FAST_DECISIONS_{backend.upper()}_TOKEN_ENV", "FD_REDIRECT_FIXTURE")
    monkeypatch.setenv(f"FAST_DECISIONS_{backend.upper()}_URL", "https://configured.example")
    assert getattr(cli, f"_{backend}_server_check")()["state"] == "reachable"
    assert requests[0].get_header("Authorization") == "Bearer dummy-redirect-credential"

    redirected = urllib.request.HTTPRedirectHandler().redirect_request(
        requests[0], None, 302, "Found", {}, redirect,
    )
    assert redirected.get_header("Authorization") is None
