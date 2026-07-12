"""Opaque, signed continuation-token support."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Any

from mcp_sgu.config import get_settings

_TOKEN_VERSION = 2
_TOKEN_MAX_AGE = 3600
_states: dict[str, tuple[int, dict[str, Any]]] = {}


class ContinuationTokenError(Exception):
    """Invalid, expired, or unavailable continuation token."""


def _secret() -> bytes:
    settings = get_settings()
    value = settings.mcp_continuation_secret or settings.mcp_bearer_token
    if not value:
        raise ContinuationTokenError("Continuation tokens are unavailable without a configured secret")
    return value.encode()


def _signature(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def encode_continuation_token(state: dict[str, Any]) -> str:
    """Store state locally and return a versioned opaque signed token."""
    now = int(time.time())
    _purge(now)
    token_id = secrets.token_urlsafe(24)
    payload = f"{_TOKEN_VERSION}:{now}:{token_id}"
    _states[token_id] = (now, state)
    return base64.urlsafe_b64encode(f"{payload}:{_signature(payload)}".encode()).decode().rstrip("=")


def decode_continuation_token(token: str) -> dict[str, Any]:
    """Validate an opaque token and retrieve its bounded server-side state."""
    try:
        decoded = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode()
        version, issued_at, token_id, signature = decoded.split(":", 3)
        payload = f"{version}:{issued_at}:{token_id}"
        if version != str(_TOKEN_VERSION) or not hmac.compare_digest(signature, _signature(payload)):
            raise ContinuationTokenError("Invalid continuation token signature")
        issued = int(issued_at)
        if issued > int(time.time()) or int(time.time()) - issued > _TOKEN_MAX_AGE:
            raise ContinuationTokenError("Continuation token has expired")
        stored = _states.pop(token_id, None)
        if stored is None or stored[0] != issued:
            raise ContinuationTokenError("Continuation token state is unavailable or already used")
        return stored[1]
    except (ValueError, TypeError) as exc:
        raise ContinuationTokenError("Malformed continuation token") from exc


def _purge(now: int) -> None:
    """Remove expired state opportunistically."""
    for token_id, (issued, _) in list(_states.items()):
        if now - issued > _TOKEN_MAX_AGE:
            del _states[token_id]
