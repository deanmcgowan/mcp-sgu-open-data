"""Main Starlette application with MCP server and health endpoints."""

from __future__ import annotations

import datetime
import time
from typing import Any

from mcp_sgu import __version__

_startup_time = time.time()
_last_sgu_success: float | None = None
_last_sgu_error: str | None = None


def _now_iso() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()


def update_sgu_status(success: bool, error: str | None = None) -> None:
    """Update the last SGU request status (called by SGU client hooks)."""
    global _last_sgu_success, _last_sgu_error
    if success:
        _last_sgu_success = time.time()
        _last_sgu_error = None
    else:
        _last_sgu_error = error


async def _check_sgu_readiness(base_url: str) -> tuple[bool, str]:
    """Perform a lightweight SGU metadata request to check readiness."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(base_url, headers={"Accept": "application/json"})
        if resp.status_code < 400:
            return True, "ok"
        return False, f"HTTP {resp.status_code}"
    except httpx.TimeoutException:
        return False, "timeout"
    except Exception as exc:
        return False, str(exc)


def create_app() -> Any:
    """Create and return the Starlette ASGI application."""

    from mcp.server.fastmcp import FastMCP
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.requests import Request
    from starlette.responses import HTMLResponse, JSONResponse, Response
    from starlette.routing import Mount, Route

    from mcp_sgu.auth import BearerTokenMiddleware
    from mcp_sgu.cache import (
        get_address_cache,
        get_metadata_cache,
        get_results_cache,
    )
    from mcp_sgu.config import get_settings
    from mcp_sgu.logging_config import configure_logging, get_logger, set_request_id
    from mcp_sgu.tools.create_export import create_export as tool_create_export
    from mcp_sgu.tools.explain_field import explain_field as tool_explain_field
    from mcp_sgu.tools.get_dataset_metadata import get_dataset_metadata as tool_get_dataset_metadata
    from mcp_sgu.tools.get_well import get_well as tool_get_well
    from mcp_sgu.tools.get_well_layers import get_well_layers as tool_get_well_layers
    from mcp_sgu.tools.resolve_address import resolve_address as tool_resolve_address
    from mcp_sgu.tools.search_wells import search_wells as tool_search_wells
    from mcp_sgu.tools.summarize_well_area import summarize_well_area as tool_summarize_well_area

    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    if not settings.mcp_bearer_token:
        logger.warning("MCP_BEARER_TOKEN is not set; /mcp will reject all requests")

    # ── Build MCP server ────────────────────────────────────────────────

    mcp = FastMCP(
        name="SGU Brunnar MCP Server",
        instructions=(
            "This server provides access to the Swedish Geological Survey (SGU) "
            "Brunnar (wells) open dataset. "
            "You can search for wells, retrieve individual well records, "
            "get geological layer information, and export data. "
            "All source data is in Swedish; use explain_field for translations."
        ),
        stateless_http=True,
        streamable_http_path="/",
    )

    # Register tools
    mcp.tool()(tool_resolve_address)
    mcp.tool()(tool_search_wells)
    mcp.tool()(tool_get_well)
    mcp.tool()(tool_get_well_layers)
    mcp.tool()(tool_summarize_well_area)
    mcp.tool()(tool_explain_field)
    mcp.tool()(tool_get_dataset_metadata)
    mcp.tool()(tool_create_export)

    mcp_starlette = mcp.streamable_http_app()

    # ── Health / status handlers ─────────────────────────────────────────

    async def healthz(_: Request) -> Response:
        """Liveness probe — returns 200 if the process is running."""
        return JSONResponse({"status": "ok", "version": __version__})

    async def readyz(request: Request) -> Response:
        """Readiness probe — checks SGU connectivity with a short timeout."""
        cfg = get_settings()
        ok, detail = await _check_sgu_readiness(cfg.sgu_base_url)
        body = {
            "status": "ready" if ok else "not_ready",
            "sgu_connectivity": detail,
            "version": __version__,
        }
        return JSONResponse(body, status_code=200 if ok else 503)

    async def api_status(_: Request) -> Response:
        """Return application status without exposing secrets."""
        cfg = get_settings()
        metadata_cache = get_metadata_cache()
        results_cache = get_results_cache()
        address_cache = get_address_cache()
        uptime = round(time.time() - _startup_time, 1)

        return JSONResponse({
            "name": "mcp-sgu-open-data",
            "version": __version__,
            "environment": cfg.app_env,
            "uptime_seconds": uptime,
            "mcp_endpoint": "/mcp",
            "auth_configured": bool(cfg.mcp_bearer_token),
            "google_geocoding_configured": bool(cfg.google_maps_api_key),
            "sgu_base_url": cfg.sgu_base_url,
            "last_sgu_success": (
                _now_iso_from(_last_sgu_success) if _last_sgu_success else None
            ),
            "last_sgu_error": _last_sgu_error,
            "cache": {
                "metadata_maxsize": metadata_cache.maxsize,
                "results_maxsize": results_cache.maxsize,
                "address_maxsize": address_cache.maxsize,
            },
            "limits": {
                "max_inline_results": cfg.max_inline_results,
                "max_export_records": cfg.max_export_records,
                "max_upstream_concurrency": cfg.max_upstream_concurrency,
                "cache_ttl_seconds": cfg.cache_ttl_seconds,
                "export_ttl_seconds": cfg.export_ttl_seconds,
            },
            "enabled_tools": [
                "resolve_address",
                "search_wells",
                "get_well",
                "get_well_layers",
                "summarize_well_area",
                "explain_field",
                "get_dataset_metadata",
                "create_export",
            ],
        })

    async def api_metadata(_: Request) -> Response:
        """Return dataset metadata (same as the MCP tool)."""
        from mcp_sgu.tools.get_dataset_metadata import get_dataset_metadata
        result = await get_dataset_metadata()
        return JSONResponse(result)

    async def export_download(request: Request) -> Response:
        """Download an export file. Protected by bearer auth (handled by middleware)."""
        from mcp_sgu.exports import get_export

        export_id = request.path_params.get("export_id", "")
        record = await get_export(export_id)
        if record is None:
            return JSONResponse(
                {"error": "not_found", "detail": "Export not found or has expired."},
                status_code=404,
            )

        content_type = "text/csv; charset=utf-8" if record.format == "csv" else "application/geo+json"
        filename = f"sgu_brunnar_{export_id[:8]}.{record.format}"
        return Response(
            content=record.content,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    async def root(_: Request) -> Response:
        """Diagnostic HTML page."""
        cfg = get_settings()
        uptime = round(time.time() - _startup_time, 1)
        html = _build_root_html(
            version=__version__,
            environment=cfg.app_env,
            sgu_base_url=cfg.sgu_base_url,
            uptime=uptime,
            auth_configured=bool(cfg.mcp_bearer_token),
        )
        return HTMLResponse(html)

    # ── Request ID middleware ─────────────────────────────────────────────

    from starlette.middleware.base import BaseHTTPMiddleware

    class RequestIdMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Any) -> Any:
            import uuid
            req_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())[:8]
            set_request_id(req_id)
            response = await call_next(request)
            response.headers["X-Request-Id"] = req_id
            return response

    # ── Routes ────────────────────────────────────────────────────────────

    routes = [
        Route("/healthz", healthz),
        Route("/readyz", readyz),
        Route("/api/status", api_status),
        Route("/api/metadata", api_metadata),
        Route("/api/exports/{export_id}", export_download),
        Route("/", root),
        Mount("/mcp", app=mcp_starlette),
    ]

    app = Starlette(
        routes=routes,
        middleware=[
            Middleware(RequestIdMiddleware),
            Middleware(BearerTokenMiddleware),
        ],
    )

    logger.info(
        "SGU MCP server initialized",
        extra={"version": __version__, "environment": settings.app_env},
    )

    return app


def _now_iso_from(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, tz=datetime.UTC).isoformat()


def _build_root_html(
    version: str,
    environment: str,
    sgu_base_url: str,
    uptime: float,
    auth_configured: bool,
) -> str:
    auth_status = "Configured ✓" if auth_configured else "NOT CONFIGURED ⚠"
    auth_class = "ok" if auth_configured else "warn"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SGU Brunnar MCP Server</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
    h1 {{ color: #2c6e49; }}
    table {{ border-collapse: collapse; width: 100%; }}
    td, th {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f4f4f4; }}
    .ok {{ color: #2c6e49; font-weight: bold; }}
    .warn {{ color: #b45309; font-weight: bold; }}
    code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
  </style>
</head>
<body>
  <h1>&#x1F30D; SGU Brunnar MCP Server</h1>
  <p>Read-only MCP server exposing the Swedish Geological Survey (SGU) Brunnar (wells) dataset.</p>

  <h2>Status</h2>
  <table>
    <tr><th>Item</th><th>Value</th></tr>
    <tr><td>Version</td><td>{version}</td></tr>
    <tr><td>Environment</td><td>{environment}</td></tr>
    <tr><td>Uptime</td><td>{uptime}s</td></tr>
    <tr><td>MCP endpoint</td><td><code>/mcp</code></td></tr>
    <tr><td>Auth</td><td class="{auth_class}">{auth_status}</td></tr>
    <tr><td>SGU API</td><td><a href="{sgu_base_url}">{sgu_base_url}</a></td></tr>
  </table>

  <h2>Available Tools</h2>
  <ul>
    <li><strong>resolve_address</strong> &mdash; Geocode a free-text address</li>
    <li><strong>search_wells</strong> &mdash; Search wells by location, municipality, or attributes</li>
    <li><strong>get_well</strong> &mdash; Retrieve a single well by ID</li>
    <li><strong>get_well_layers</strong> &mdash; Get geological layers for a well</li>
    <li><strong>summarize_well_area</strong> &mdash; Aggregate statistics for an area</li>
    <li><strong>explain_field</strong> &mdash; Explain SGU field names and codes</li>
    <li><strong>get_dataset_metadata</strong> &mdash; Dataset and API metadata</li>
    <li><strong>create_export</strong> &mdash; Create CSV or GeoJSON export</li>
  </ul>

  <h2>Diagnostic Endpoints</h2>
  <ul>
    <li><a href="/healthz"><code>/healthz</code></a> &mdash; Liveness check</li>
    <li><a href="/readyz"><code>/readyz</code></a> &mdash; Readiness check</li>
    <li><a href="/api/status"><code>/api/status</code></a> &mdash; Application status</li>
    <li><a href="/api/metadata"><code>/api/metadata</code></a> &mdash; Dataset metadata</li>
  </ul>
</body>
</html>"""


def main() -> None:
    """Entrypoint for running the server directly."""
    import uvicorn

    from mcp_sgu.config import get_settings

    settings = get_settings()
    app = create_app()

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_config=None,  # We handle logging ourselves
        access_log=False,
    )


if __name__ == "__main__":
    main()
