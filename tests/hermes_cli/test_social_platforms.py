"""GET/PUT /api/social/platforms/{id} — credential storage for the Social
module's platform connections (Facebook first — see hermes_cli/social_platforms.py
and douglas/PROGRESS.md, 2026-08-07 entry).

Distinct from the messaging platform endpoints: no gateway/enabled/multiplex
concerns, and every credential is the user's own (never a Douglas-owned app
shared across installs) — these tests assert the storage/redaction contract,
not any platform-specific business logic (there isn't any yet; OAuth and the
publish adapter are later phases, see douglas/IMPLEMENTATION_PLAN.md).
"""

from fastapi.testclient import TestClient

import hermes_cli.social_platforms as social_platforms
from hermes_cli.web_server import _SESSION_TOKEN, app

client = TestClient(app)
HEADERS = {"X-Hermes-Session-Token": _SESSION_TOKEN}


def _fake_env_store(monkeypatch):
    """In-memory .env stand-in so these tests never touch the real filesystem."""
    store: dict[str, str] = {}

    def fake_get(key: str):
        return store.get(key)

    def fake_save(key: str, value: str):
        store[key] = value

    def fake_remove(key: str) -> bool:
        return store.pop(key, None) is not None

    monkeypatch.setattr(social_platforms, "get_env_value", fake_get)
    monkeypatch.setattr(social_platforms, "save_env_value", fake_save)
    monkeypatch.setattr(social_platforms, "remove_env_value", fake_remove)
    return store


def test_get_unknown_platform_404(monkeypatch):
    _fake_env_store(monkeypatch)
    resp = client.get("/api/social/platforms/nope", headers=HEADERS)
    assert resp.status_code == 404


def test_get_before_any_credential_saved(monkeypatch):
    _fake_env_store(monkeypatch)
    resp = client.get("/api/social/platforms/facebook", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is False
    assert all(field["is_set"] is False for field in body["env_vars"])


def test_put_saves_credential_and_get_reflects_it(monkeypatch):
    store = _fake_env_store(monkeypatch)
    resp = client.put(
        "/api/social/platforms/facebook",
        headers=HEADERS,
        json={"env": {"FACEBOOK_APP_ID": "123456"}, "clear_env": []},
    )
    assert resp.status_code == 200
    assert store["FACEBOOK_APP_ID"] == "123456"

    resp = client.get("/api/social/platforms/facebook", headers=HEADERS)
    field = next(f for f in resp.json()["env_vars"] if f["key"] == "FACEBOOK_APP_ID")
    assert field["is_set"] is True


def test_put_never_returns_the_raw_secret(monkeypatch):
    _fake_env_store(monkeypatch)
    resp = client.put(
        "/api/social/platforms/facebook",
        headers=HEADERS,
        json={"env": {"FACEBOOK_APP_SECRET": "s3cret-value"}, "clear_env": []},
    )
    assert resp.status_code == 200
    assert "s3cret-value" not in resp.text


def test_put_rejects_key_not_in_registry(monkeypatch):
    _fake_env_store(monkeypatch)
    resp = client.put(
        "/api/social/platforms/facebook",
        headers=HEADERS,
        json={"env": {"BOGUS_KEY": "x"}, "clear_env": []},
    )
    assert resp.status_code == 400


def test_put_rejects_unknown_platform(monkeypatch):
    _fake_env_store(monkeypatch)
    resp = client.put(
        "/api/social/platforms/nope",
        headers=HEADERS,
        json={"env": {}, "clear_env": []},
    )
    assert resp.status_code == 404


def test_put_clear_env_removes_a_saved_credential(monkeypatch):
    store = _fake_env_store(monkeypatch)
    store["FACEBOOK_APP_ID"] = "123456"

    resp = client.put(
        "/api/social/platforms/facebook",
        headers=HEADERS,
        json={"env": {}, "clear_env": ["FACEBOOK_APP_ID"]},
    )
    assert resp.status_code == 200
    assert "FACEBOOK_APP_ID" not in store


def test_put_ignores_blank_values(monkeypatch):
    """A blank/whitespace-only value must not overwrite a saved credential —
    matches the messaging platform endpoint's own trim-then-skip behavior."""
    store = _fake_env_store(monkeypatch)
    store["FACEBOOK_APP_ID"] = "123456"

    resp = client.put(
        "/api/social/platforms/facebook",
        headers=HEADERS,
        json={"env": {"FACEBOOK_APP_ID": "   "}, "clear_env": []},
    )
    assert resp.status_code == 200
    assert store["FACEBOOK_APP_ID"] == "123456"
