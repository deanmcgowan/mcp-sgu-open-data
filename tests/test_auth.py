"""Tests for bearer token authentication."""

from __future__ import annotations

from starlette.testclient import TestClient


def test_mcp_requires_auth(app) -> None:
    """MCP endpoint rejects requests without Authorization header."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/mcp", json={"jsonrpc": "2.0", "method": "tools/list", "id": 1})
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"] == "unauthorized"


def test_mcp_rejects_wrong_token(app) -> None:
    """MCP endpoint rejects requests with wrong token."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        headers={"Authorization": "******"},
    )
    assert resp.status_code == 401


def test_mcp_rejects_malformed_auth_header(app) -> None:
    """MCP endpoint rejects malformed Authorization header."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        headers={"Authorization": "Token abc123"},
    )
    assert resp.status_code == 401


def test_healthz_no_auth_required(app) -> None:
    """Health endpoint must not require authentication."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/healthz")
    assert resp.status_code == 200


def test_readyz_no_auth_required(app) -> None:
    """Readiness endpoint must not require authentication."""
    client = TestClient(app, raise_server_exceptions=False)
    # readyz makes an upstream call; we don't care about the result, just status is not 401
    resp = client.get("/readyz")
    assert resp.status_code in (200, 503)  # May be 503 if SGU unreachable


def test_mcp_accepts_valid_token(app, auth_headers) -> None:
    """MCP endpoint accepts a valid bearer token."""
    client = TestClient(app, raise_server_exceptions=False)
    # Even with a valid token the endpoint may return 4xx for an invalid MCP payload
    # but it should NOT return 401
    resp = client.post("/mcp", headers=auth_headers, content=b"invalid json")
    assert resp.status_code != 401


def test_api_status_no_auth(app) -> None:
    """API status endpoint must not require authentication."""
    client = TestClient(app)
    resp = client.get("/api/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "version" in body
    assert "enabled_tools" in body
    # Secrets must not be exposed
    assert "mcp_bearer_token" not in str(body)
    assert "google_maps_api_key" not in str(body)
