"""Continuation token support for pagination."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from mcp_sgu.logging_config import get_logger

logger = get_logger(__name__)

_TOKEN_SECRET = b"mcp-sgu-continuation-token"
_TOKEN_VERSION = 1
_TOKEN_MAX_AGE = 3600  # 1 hour


class ContinuationTokenError(Exception):
    """Invalid or expired continuation token."""


def encode_continuation_token(state: dict[str, Any]) -> str:
    """Encode query state as a safe continuation token.

    The token is base64-encoded JSON with an HMAC signature.
    It does not expose secrets from the query state.
    """
    payload = {
        "v": _TOKEN_VERSION,
        "t": int(time.time()),
        "s": state,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(_TOKEN_SECRET, raw, hashlib.sha256).hexdigest()[:16]
    data = {"d": base64.urlsafe_b64encode(raw).decode(), "sig": sig}
    return base64.urlsafe_b64encode(
        json.dumps(data, separators=(",", ":")).encode()
    ).decode()


def decode_continuation_token(token: str) -> dict[str, Any]:
    """Decode and validate a continuation token.

    Raises ContinuationTokenError on invalid/expired tokens.
    """
    try:
        outer = json.loads(base64.urlsafe_b64decode(token + "=="))
        raw = base64.urlsafe_b64decode(outer["d"] + "==")
        expected_sig = hmac.new(_TOKEN_SECRET, raw, hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(outer["sig"], expected_sig):
            raise ContinuationTokenError("Invalid continuation token signature")
        payload = json.loads(raw)
        age = int(time.time()) - payload.get("t", 0)
        if age > _TOKEN_MAX_AGE:
            raise ContinuationTokenError("Continuation token has expired")
        return payload["s"]
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise ContinuationTokenError(f"Malformed continuation token: {exc}") from exc
