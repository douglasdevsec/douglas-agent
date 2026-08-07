"""Facebook OAuth (Login for Business) via a fixed local loopback server.

Desktop-app OAuth pattern, mirroring hermes_cli/auth.py's Spotify PKCE flow
(``_spotify_wait_for_callback`` and friends) but adapted for a GUI trigger
instead of a blocking CLI command: ``start_facebook_oauth()`` starts the
flow and returns immediately; a background thread does the actual
wait-for-callback + token exchange; the frontend polls
``get_facebook_oauth_status()`` (via ``GET /api/social/platforms/facebook/
oauth/status``) until it's done. See douglas/PROGRESS.md (2026-08-07,
"Fase B2" entry) and douglas/IMPLEMENTATION_PLAN.md ("Modulo Social") for
the product decision this implements.

Why a FIXED loopback port instead of an OS-assigned ephemeral one (unlike
Spotify's flow above, which lets the user pick any port): Facebook's OAuth
``redirect_uri`` allowlist requires an EXACT string match, port included —
there is no wildcard-port support. A random port every attempt would need
re-registering in the user's Meta app on every single connection. Instead
the user adds this ONE fixed URL to their app's "Valid OAuth Redirect
URIs" once (surfaced in the wizard copy, apps/desktop/src/app/social/
fixtures.ts) — the same one-time-setup shape as the WhatsApp Cloud wizard
already asks for a webhook URL.

Opens the system browser, never an embedded webview — the user's real
Facebook session/2FA/passkeys live there, and this app must never see the
raw Facebook password.
"""

from __future__ import annotations

import secrets
import threading
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional, Tuple, Type
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from hermes_cli.auth import _can_open_graphical_browser, _is_remote_session
from hermes_cli.config import get_env_value, save_env_value

FACEBOOK_GRAPH_VERSION = "v21.0"
# Standard triad for posting to a Page the user administers. Anything
# beyond the app's own admins/testers requires Meta App Review before it
# works for other people's accounts — see the wizard copy for the heads-up.
FACEBOOK_OAUTH_SCOPES = "pages_manage_posts,pages_read_engagement,pages_show_list"
FACEBOOK_LOOPBACK_PORT = 53682
FACEBOOK_LOOPBACK_PATH = "/facebook/callback"
FACEBOOK_REDIRECT_URI = f"http://localhost:{FACEBOOK_LOOPBACK_PORT}{FACEBOOK_LOOPBACK_PATH}"
_CALLBACK_TIMEOUT_SECONDS = 300.0  # 5 minutes to complete the browser flow


@dataclass(frozen=True)
class _OAuthAttempt:
    state: str
    status: str  # "pending" | "success" | "error"
    error: Optional[str] = None


# In-memory only — this is a single-user desktop app process, not a
# multi-tenant server, so there's nothing to persist across restarts and
# nothing here is ever written to disk. Replaced wholesale (never mutated
# in place) on every status change so a reader under the lock never sees a
# half-updated attempt.
_ATTEMPTS: Dict[str, _OAuthAttempt] = {}
_ATTEMPTS_LOCK = threading.Lock()


class _FacebookOAuthError(Exception):
    pass


def _set_attempt(state: str, *, status: str, error: Optional[str] = None) -> None:
    with _ATTEMPTS_LOCK:
        _ATTEMPTS[state] = _OAuthAttempt(state=state, status=status, error=error)


def _make_callback_handler(expected_path: str) -> Tuple[Type[BaseHTTPRequestHandler], Dict[str, Any]]:
    result: Dict[str, Any] = {"code": None, "state": None, "error": None, "error_description": None}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != expected_path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found.")
                return

            params = parse_qs(parsed.query)
            result["code"] = params.get("code", [None])[0]
            result["state"] = params.get("state", [None])[0]
            result["error"] = params.get("error", [None])[0]
            result["error_description"] = params.get("error_description", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if result["error"]:
                body = (
                    "<html><body><h1>Facebook authorization failed.</h1>"
                    "You can close this tab and return to Douglas Agent.</body></html>"
                )
            else:
                body = (
                    "<html><body><h1>Facebook authorization received.</h1>"
                    "You can close this tab and return to Douglas Agent.</body></html>"
                )
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return  # silence BaseHTTPRequestHandler's default stderr access log

    return _Handler, result


def _facebook_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
        message = payload.get("error", {}).get("message")
        if message:
            return f"Facebook rejected the request: {message}"
    except Exception:
        pass
    return f"Facebook rejected the request (HTTP {response.status_code})."


def _exchange_code_for_page_token(*, app_id: str, app_secret: str, page_id: str, code: str) -> str:
    """code -> short-lived user token -> long-lived user token -> Page token.

    A Page Access Token minted from a *long*-lived user token does not
    expire on its own (only if the user revokes access or changes their
    password — see Meta's docs on "Long-Lived Access Tokens"). One minted
    from a short-lived user token would expire in ~1-2 hours, unusable for
    a background posting feature — hence the extra exchange step.
    """
    base = f"https://graph.facebook.com/{FACEBOOK_GRAPH_VERSION}"

    try:
        short_lived = httpx.get(
            f"{base}/oauth/access_token",
            params={
                "client_id": app_id,
                "redirect_uri": FACEBOOK_REDIRECT_URI,
                "client_secret": app_secret,
                "code": code,
            },
            timeout=20.0,
        )
    except Exception as exc:
        raise _FacebookOAuthError(f"Could not reach Facebook to exchange the code: {exc}") from exc
    if short_lived.status_code >= 400:
        raise _FacebookOAuthError(_facebook_error_message(short_lived))
    short_lived_token = short_lived.json().get("access_token")
    if not short_lived_token:
        raise _FacebookOAuthError("Facebook did not return an access token.")

    try:
        long_lived = httpx.get(
            f"{base}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_lived_token,
            },
            timeout=20.0,
        )
    except Exception as exc:
        raise _FacebookOAuthError(f"Could not reach Facebook to extend the token: {exc}") from exc
    if long_lived.status_code >= 400:
        raise _FacebookOAuthError(_facebook_error_message(long_lived))
    long_lived_token = long_lived.json().get("access_token")
    if not long_lived_token:
        raise _FacebookOAuthError("Facebook did not return a long-lived access token.")

    try:
        page = httpx.get(
            f"{base}/{page_id}",
            params={"fields": "access_token", "access_token": long_lived_token},
            timeout=20.0,
        )
    except Exception as exc:
        raise _FacebookOAuthError(f"Could not reach Facebook to fetch the Page token: {exc}") from exc
    if page.status_code >= 400:
        raise _FacebookOAuthError(_facebook_error_message(page))
    page_token = page.json().get("access_token")
    if not page_token:
        raise _FacebookOAuthError(
            "Facebook did not return a Page access token. Confirm the Page ID is "
            "correct and that your Facebook user is an admin of that Page."
        )
    return page_token


def _run_oauth_attempt(state: str, *, app_id: str, app_secret: str, page_id: str) -> None:
    handler_cls, result = _make_callback_handler(FACEBOOK_LOOPBACK_PATH)

    class _ReuseHTTPServer(HTTPServer):
        allow_reuse_address = True

    try:
        server = _ReuseHTTPServer(("127.0.0.1", FACEBOOK_LOOPBACK_PORT), handler_cls)
    except OSError as exc:
        _set_attempt(
            state,
            status="error",
            error=(
                f"Could not start the local callback server on port "
                f"{FACEBOOK_LOOPBACK_PORT}: {exc}. Close whatever else is using "
                "that port on this machine and try again."
            ),
        )
        return

    server_thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    server_thread.start()

    try:
        deadline = time.monotonic() + _CALLBACK_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if result["code"] or result["error"]:
                break
            time.sleep(0.2)
        else:
            _set_attempt(state, status="error", error="Timed out waiting for Facebook authorization.")
            return

        if result["error"]:
            detail = result["error_description"] or result["error"]
            _set_attempt(state, status="error", error=f"Facebook authorization failed: {detail}")
            return

        if result["state"] != state:
            _set_attempt(state, status="error", error="Facebook authorization failed: state mismatch.")
            return

        try:
            page_token = _exchange_code_for_page_token(
                app_id=app_id, app_secret=app_secret, page_id=page_id, code=result["code"]
            )
        except _FacebookOAuthError as exc:
            _set_attempt(state, status="error", error=str(exc))
            return

        save_env_value("FACEBOOK_PAGE_ACCESS_TOKEN", page_token)
        _set_attempt(state, status="success")
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1.0)


def start_facebook_oauth() -> Dict[str, Any]:
    """Start a Facebook authorization attempt. Returns immediately.

    Raises ``ValueError`` (translated to an HTTP 400 by the API route) when
    credentials from Fase B1 are missing, or the environment can't reach a
    local browser at all.
    """
    app_id = (get_env_value("FACEBOOK_APP_ID") or "").strip()
    app_secret = (get_env_value("FACEBOOK_APP_SECRET") or "").strip()
    page_id = (get_env_value("FACEBOOK_PAGE_ID") or "").strip()
    missing = [
        name
        for name, value in (("App ID", app_id), ("App Secret", app_secret), ("Page ID", page_id))
        if not value
    ]
    if missing:
        raise ValueError(f"Missing {', '.join(missing)} — save your credentials before authorizing.")

    if _is_remote_session():
        raise ValueError(
            "Douglas Agent appears to be running in a remote session — the local "
            "browser can't reach this machine's loopback server for Facebook "
            "authorization."
        )

    state = secrets.token_urlsafe(24)
    _set_attempt(state, status="pending")

    authorize_url = f"https://www.facebook.com/{FACEBOOK_GRAPH_VERSION}/dialog/oauth?" + urlencode(
        {
            "client_id": app_id,
            "redirect_uri": FACEBOOK_REDIRECT_URI,
            "state": state,
            "scope": FACEBOOK_OAUTH_SCOPES,
            "response_type": "code",
        }
    )

    waiter = threading.Thread(
        target=_run_oauth_attempt,
        kwargs={"state": state, "app_id": app_id, "app_secret": app_secret, "page_id": page_id},
        daemon=True,
    )
    waiter.start()

    opened = False
    if _can_open_graphical_browser():
        try:
            opened = bool(webbrowser.open(authorize_url))
        except Exception:
            opened = False

    return {"authorize_url": authorize_url, "state": state, "browser_opened": opened}


def get_facebook_oauth_status(state: str) -> Dict[str, Any]:
    with _ATTEMPTS_LOCK:
        attempt = _ATTEMPTS.get(state)
    if attempt is None:
        return {"status": "error", "error": "Unknown authorization attempt."}
    return {"status": attempt.status, "error": attempt.error}
