"""Tests for health and status endpoints."""

from __future__ import annotations

from starlette.testclient import TestClient


def test_healthz_returns_ok(app) -> None:
    """GET /healthz returns 200 with status ok."""
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_api_status_structure(app) -> None:
    """GET /api/status returns expected structure."""
    client = TestClient(app)
    resp = client.get("/api/status")
    assert resp.status_code == 200
    body = resp.json()

    required_keys = [
        "name", "version", "environment", "uptime_seconds",
        "mcp_endpoint", "auth_configured", "limits", "enabled_tools",
    ]
    for key in required_keys:
        assert key in body, f"Missing key: {key}"

    assert body["mcp_endpoint"] == "/mcp"
    assert isinstance(body["enabled_tools"], list)
    assert len(body["enabled_tools"]) == 8

    # Secrets must not appear in status
    assert "test-token" not in str(body)
    assert "test-google-key" not in str(body)


def test_root_returns_html(app) -> None:
    """GET / returns an HTML page."""
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "SGU" in resp.text
    assert "/mcp" in resp.text


def test_api_metadata_returns_json(app) -> None:
    """GET /api/metadata returns JSON (may fail if SGU is unreachable)."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/metadata")
    assert resp.status_code == 200
    body = resp.json()
    # Should have field_definitions even if SGU is unreachable
    assert "field_definitions" in body

def test_export_download_not_found(app, auth_headers) -> None:
    """Download of non-existent export returns 404."""
    client = TestClient(app)
    resp = client.get(
        "/api/exports/nonexistent-id",
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_export_download_requires_auth(app) -> None:
    """Download endpoint requires valid bearer token."""
    client = TestClient(app)
    resp = client.get("/api/exports/nonexistent-id")
    assert resp.status_code == 401


def test_request_id_header_returned(app) -> None:
    """Server returns X-Request-Id header."""
    client = TestClient(app)
    resp = client.get("/healthz")
    assert "x-request-id" in resp.headers
