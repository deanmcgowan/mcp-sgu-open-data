"""Tests for pagination and continuation tokens."""

from __future__ import annotations

import pytest


def test_encode_decode_roundtrip() -> None:
    """Continuation token encodes and decodes without loss."""
    from mcp_sgu.pagination import decode_continuation_token, encode_continuation_token

    state = {"params": {"limit": 50, "offset": 50}, "offset": 50, "lat": 59.3, "lon": 18.0}
    token = encode_continuation_token(state)
    decoded = decode_continuation_token(token)
    assert decoded == state


def test_continuation_token_is_url_safe() -> None:
    """Continuation token should contain only URL-safe characters."""
    from mcp_sgu.pagination import encode_continuation_token

    state = {"params": {"filter": "kommunkod='0180'", "limit": 100}, "offset": 0}
    token = encode_continuation_token(state)
    # Token should be base64url-safe
    safe_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
    assert all(c in safe_chars for c in token), f"Unsafe chars in token: {token}"


def test_invalid_token_raises() -> None:
    """Decoding a garbage token raises ContinuationTokenError."""
    from mcp_sgu.pagination import ContinuationTokenError, decode_continuation_token

    with pytest.raises(ContinuationTokenError):
        decode_continuation_token("not-a-valid-token")


def test_tampered_token_raises() -> None:
    """Decoding a tampered token raises ContinuationTokenError."""
    from mcp_sgu.pagination import (
        ContinuationTokenError,
        decode_continuation_token,
        encode_continuation_token,
    )

    state = {"offset": 50}
    token = encode_continuation_token(state)
    # Tamper with last character
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(ContinuationTokenError):
        decode_continuation_token(tampered)


def test_expired_token_raises(monkeypatch) -> None:
    """Decoding an expired token raises ContinuationTokenError."""
    from mcp_sgu import pagination as pag_module
    from mcp_sgu.pagination import ContinuationTokenError, encode_continuation_token

    # Create a token, then advance time past max age
    state = {"offset": 0}
    token = encode_continuation_token(state)

    # Patch time.time to return a value far in the future
    monkeypatch.setattr(pag_module, "_TOKEN_MAX_AGE", -1)  # Already expired
    with pytest.raises(ContinuationTokenError, match="expired"):
        from mcp_sgu.pagination import decode_continuation_token
        decode_continuation_token(token)
