"""Registry + credential storage for the Social module's platform connections.

Distinct from ``PLATFORM_REGISTRY`` in ``web_server.py`` on purpose: that
registry is for *messaging* gateways -- adapters that run as a persistent,
listening service (a bot account). Social platforms (Facebook, YouTube, ...)
are publish-on-demand integrations with no running adapter/listener, so they
don't share the enabled/multiplex/gateway-liveness concerns messaging
channels have.

Every credential entered here is the USER'S OWN -- their own Meta/Google
developer app, never a Douglas-owned one shared across every install -- and
is stored exactly like every other platform credential already in this
codebase: locally, in ``$HERMES_HOME/.env``, via the same
``save_env_value()``/``get_env_value()`` writer WhatsApp Cloud, Slack, and
Telegram already use. Nothing collected here is ever sent to any Douglas
server. See ``douglas/PROGRESS.md`` (2026-08-07 entry) and
``douglas/IMPLEMENTATION_PLAN.md`` ("Modulo Social") for the product
decision this implements and the phases still pending (real OAuth exchange,
the actual publish adapter, a real premium-entitlement check).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from hermes_cli.config import get_env_value, redact_key, remove_env_value, save_env_value

# platform id -> display name + the ordered env var names the frontend
# collects for it. Adding a platform is just a new entry here -- the API
# routes and the credential read/write logic below are already generic.
SOCIAL_PLATFORM_REGISTRY: Dict[str, Dict[str, Any]] = {
    "facebook": {
        "name": "Facebook",
        # App ID/Secret: the user's own Meta developer app (Fase B1).
        # Page ID: which Page to publish to (Fase B1). A Page Access Token
        # lands here too once the real OAuth exchange (Fase B2) exists --
        # not added yet so this registry doesn't advertise a field nothing
        # can fill in for real today.
        "env_vars": ("FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET", "FACEBOOK_PAGE_ID"),
    },
}


def get_social_platform_status(platform_id: str) -> Optional[Dict[str, Any]]:
    """Non-secret status payload for one platform: which fields are set, masked.

    Never returns a raw credential value -- only whether it's set and a
    redacted display form (``redact_key``), matching the messaging
    platforms endpoint's own contract.
    """
    entry = SOCIAL_PLATFORM_REGISTRY.get(platform_id)
    if entry is None:
        return None

    fields = []
    for key in entry["env_vars"]:
        value = get_env_value(key) or ""
        fields.append(
            {
                "key": key,
                "is_set": bool(value),
                "redacted_value": redact_key(value) if value else None,
            }
        )

    return {
        "id": platform_id,
        "name": entry["name"],
        "env_vars": fields,
        "configured": all(field["is_set"] for field in fields),
    }


def update_social_platform_credentials(
    platform_id: str, env: Dict[str, str], clear_env: Sequence[str] = ()
) -> Dict[str, Any]:
    """Save/clear this platform's credentials, then return the fresh status.

    Raises ``ValueError`` for an unknown platform or a key that platform
    doesn't declare in its registry entry -- the API route translates that
    into an HTTP 404/400, matching how ``update_messaging_platform`` handles
    the equivalent cases.
    """
    entry = SOCIAL_PLATFORM_REGISTRY.get(platform_id)
    if entry is None:
        raise ValueError(f"Unknown social platform: {platform_id}")

    allowed = set(entry["env_vars"])

    for key in clear_env:
        if key not in allowed:
            raise ValueError(f"{key} is not configurable for {entry['name']}")
        remove_env_value(key)

    for key, value in env.items():
        if key not in allowed:
            raise ValueError(f"{key} is not configurable for {entry['name']}")
        trimmed = value.strip()
        if trimmed:
            save_env_value(key, trimmed)

    status = get_social_platform_status(platform_id)
    assert status is not None  # entry existed above, so this can't be None
    return status
