"""hermes_cli/social_oauth.py — Facebook OAuth via a fixed local loopback
server (Fase B2, see douglas/PROGRESS.md, 2026-08-07 entry).

Never binds the real loopback port or calls real Facebook APIs: the
background-thread callback waiter is monkeypatched out for the
start/status contract tests, and the token-exchange logic is tested in
isolation against a stubbed ``httpx.get``. What IS exercised for real:
credential validation, state generation, the in-memory attempt registry,
and the exact 3-step token exchange (short-lived -> long-lived -> Page
token) with its error paths.
"""

from __future__ import annotations

import types

import pytest
from fastapi.testclient import TestClient

import hermes_cli.social_oauth as social_oauth
from hermes_cli.web_server import _SESSION_TOKEN, app

client = TestClient(app)
HEADERS = {"X-Hermes-Session-Token": _SESSION_TOKEN}


@pytest.fixture(autouse=True)
def _isolated_attempts(monkeypatch):
    """Never let one test's in-memory attempts leak into another."""
    monkeypatch.setattr(social_oauth, "_ATTEMPTS", {})


@pytest.fixture
def fake_credentials(monkeypatch):
    values = {
        "FACEBOOK_APP_ID": "app-123",
        "FACEBOOK_APP_SECRET": "secret-abc",
        "FACEBOOK_PAGE_ID": "page-456",
    }
    monkeypatch.setattr(social_oauth, "get_env_value", lambda key: values.get(key))
    return values


@pytest.fixture
def no_real_waiter_thread(monkeypatch):
    """Replace the background callback-waiter with a no-op.

    start_facebook_oauth() must return immediately regardless of what the
    real waiter would eventually do -- these tests assert exactly that
    contract, not the waiter's own behavior (covered separately below via
    _exchange_code_for_page_token).
    """
    started_with = {}

    class _FakeThread:
        def __init__(self, target, kwargs, daemon):
            started_with["target"] = target
            started_with["kwargs"] = kwargs

        def start(self):
            pass  # deliberately never actually runs _run_oauth_attempt

    monkeypatch.setattr(social_oauth.threading, "Thread", _FakeThread)
    monkeypatch.setattr(social_oauth, "_can_open_graphical_browser", lambda: False)
    return started_with


def test_start_requires_all_three_credentials(monkeypatch, no_real_waiter_thread):
    monkeypatch.setattr(social_oauth, "get_env_value", lambda key: None)
    with pytest.raises(ValueError, match="Missing App ID, App Secret, Page ID"):
        social_oauth.start_facebook_oauth()


def test_start_reports_each_missing_field_by_name(monkeypatch, no_real_waiter_thread):
    monkeypatch.setattr(
        social_oauth,
        "get_env_value",
        lambda key: "app-123" if key == "FACEBOOK_APP_ID" else None,
    )
    with pytest.raises(ValueError) as exc_info:
        social_oauth.start_facebook_oauth()
    assert "App Secret" in str(exc_info.value)
    assert "Page ID" in str(exc_info.value)
    assert "App ID" not in str(exc_info.value)


def test_start_refuses_remote_session(monkeypatch, fake_credentials, no_real_waiter_thread):
    monkeypatch.setattr(social_oauth, "_is_remote_session", lambda: True)
    with pytest.raises(ValueError, match="remote session"):
        social_oauth.start_facebook_oauth()


def test_start_returns_state_and_authorize_url(fake_credentials, no_real_waiter_thread):
    result = social_oauth.start_facebook_oauth()
    assert result["state"]
    assert result["authorize_url"].startswith("https://www.facebook.com/")
    assert f"client_id={fake_credentials['FACEBOOK_APP_ID']}" in result["authorize_url"]
    assert "redirect_uri=" in result["authorize_url"]
    assert "localhost" in result["authorize_url"]


def test_start_never_leaks_app_secret_into_the_authorize_url(fake_credentials, no_real_waiter_thread):
    result = social_oauth.start_facebook_oauth()
    assert fake_credentials["FACEBOOK_APP_SECRET"] not in result["authorize_url"]


def test_start_registers_a_pending_attempt(fake_credentials, no_real_waiter_thread):
    result = social_oauth.start_facebook_oauth()
    status = social_oauth.get_facebook_oauth_status(result["state"])
    assert status["status"] == "pending"


def test_status_for_unknown_state(fake_credentials):
    status = social_oauth.get_facebook_oauth_status("never-started")
    assert status["status"] == "error"
    assert status["error"]


def test_status_reflects_a_completed_attempt(fake_credentials):
    social_oauth._set_attempt("some-state", status="success")
    assert social_oauth.get_facebook_oauth_status("some-state") == {"status": "success", "error": None}

    social_oauth._set_attempt("other-state", status="error", error="boom")
    assert social_oauth.get_facebook_oauth_status("other-state") == {"status": "error", "error": "boom"}


# ── Token exchange (short-lived -> long-lived -> Page token) ────────────────


def _fake_response(status_code: int, json_body: dict):
    resp = types.SimpleNamespace()
    resp.status_code = status_code
    resp.json = lambda: json_body
    return resp


def test_exchange_happy_path(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params))
        if "fb_exchange_token" in params:
            return _fake_response(200, {"access_token": "long-lived-token"})
        if url.endswith("/page-456"):
            return _fake_response(200, {"access_token": "page-token-xyz"})
        return _fake_response(200, {"access_token": "short-lived-token"})

    monkeypatch.setattr(social_oauth.httpx, "get", fake_get)

    token = social_oauth._exchange_code_for_page_token(
        app_id="app-123", app_secret="secret-abc", page_id="page-456", code="auth-code"
    )
    assert token == "page-token-xyz"
    assert len(calls) == 3
    # The code exchange must carry the exact redirect_uri Facebook expects
    # back -- a mismatch here is a common real-world OAuth failure mode.
    assert calls[0][1]["redirect_uri"] == social_oauth.FACEBOOK_REDIRECT_URI
    assert calls[0][1]["code"] == "auth-code"
    assert calls[1][1]["fb_exchange_token"] == "short-lived-token"
    assert calls[2][1]["access_token"] == "long-lived-token"


def test_exchange_fails_when_short_lived_step_errors(monkeypatch):
    monkeypatch.setattr(
        social_oauth.httpx,
        "get",
        lambda url, params, timeout: _fake_response(400, {"error": {"message": "Invalid code"}}),
    )
    with pytest.raises(social_oauth._FacebookOAuthError, match="Invalid code"):
        social_oauth._exchange_code_for_page_token(
            app_id="app-123", app_secret="secret-abc", page_id="page-456", code="bad-code"
        )


def test_exchange_fails_when_page_token_missing(monkeypatch):
    def fake_get(url, params, timeout):
        if "fb_exchange_token" in params:
            return _fake_response(200, {"access_token": "long-lived-token"})
        if params.get("fields") == "access_token":
            return _fake_response(200, {})  # Page exists but no token -- not an admin
        return _fake_response(200, {"access_token": "short-lived-token"})

    monkeypatch.setattr(social_oauth.httpx, "get", fake_get)

    with pytest.raises(social_oauth._FacebookOAuthError, match="admin of that Page"):
        social_oauth._exchange_code_for_page_token(
            app_id="app-123", app_secret="secret-abc", page_id="page-456", code="auth-code"
        )


def test_exchange_wraps_network_errors(monkeypatch):
    def raise_connect_error(*args, **kwargs):
        raise ConnectionError("no network")

    monkeypatch.setattr(social_oauth.httpx, "get", raise_connect_error)

    with pytest.raises(social_oauth._FacebookOAuthError, match="Could not reach Facebook"):
        social_oauth._exchange_code_for_page_token(
            app_id="app-123", app_secret="secret-abc", page_id="page-456", code="auth-code"
        )


# ── API routes (POST .../oauth/start, GET .../oauth/status) ─────────────────


def test_post_start_without_credentials_is_400(monkeypatch):
    monkeypatch.setattr(social_oauth, "get_env_value", lambda key: None)
    resp = client.post("/api/social/platforms/facebook/oauth/start", headers=HEADERS)
    assert resp.status_code == 400
    assert "Missing" in resp.json()["detail"]


def test_get_status_for_unregistered_state(monkeypatch):
    resp = client.get(
        "/api/social/platforms/facebook/oauth/status",
        headers=HEADERS,
        params={"state": "never-seen"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


def test_post_start_with_credentials_returns_authorize_url(monkeypatch, no_real_waiter_thread):
    values = {
        "FACEBOOK_APP_ID": "app-123",
        "FACEBOOK_APP_SECRET": "secret-abc",
        "FACEBOOK_PAGE_ID": "page-456",
    }
    monkeypatch.setattr(social_oauth, "get_env_value", lambda key: values.get(key))
    resp = client.post("/api/social/platforms/facebook/oauth/start", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["authorize_url"].startswith("https://www.facebook.com/")
    assert body["state"]
