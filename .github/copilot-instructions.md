# Copilot Instructions for mcp-sgu-open-data

## Project Overview

This is a read-only MCP (Model Context Protocol) server that exposes the Swedish Geological Survey
(SGU) Brunnar (wells) open dataset via Streamable HTTP transport.

- **MCP endpoint**: `POST /mcp` (protected by bearer token)
- **Primary dataset**: `brunnar` collection from `https://api.sgu.se/oppnadata/brunnar/ogc/features/v1`
- **Transport**: Streamable HTTP (FastMCP `stateless_http=True`)
- **Auth**: `Authorization: ****** header enforced by `BearerTokenMiddleware`

## Architecture

```
src/mcp_sgu/
├── app.py            # Starlette app, health endpoints, MCP mount
├── config.py         # Pydantic Settings (all env vars)
├── auth.py           # BearerTokenMiddleware (protects /mcp and /api/exports)
├── cache.py          # Bounded TTL in-memory cache
├── sgu_client.py     # SGU OGC API client (retry, pagination, dedup)
├── geocoding.py      # Google Geocoding API client
├── pagination.py     # HMAC-signed continuation tokens
├── field_defs.py     # SGU field definitions, code lists, enrich_feature()
├── coordinates.py    # haversine, radius_to_bbox, SWEREF99TM ↔ WGS84
├── exports.py        # In-memory export store (CSV, GeoJSON)
└── tools/
    ├── resolve_address.py
    ├── search_wells.py
    ├── get_well.py
    ├── get_well_layers.py
    ├── summarize_well_area.py
    ├── explain_field.py
    ├── get_dataset_metadata.py
    └── create_export.py
```

## Coding Conventions

### Language and types
- Python 3.12+
- All public functions have type hints and docstrings
- Use `from __future__ import annotations` in all modules
- Use `dict[str, Any]` not `Dict[str, Any]`

### Imports
- Standard library → third-party → local; each group separated by blank line
- Avoid circular imports; keep tool modules thin, defer heavy logic to core modules

### Async
- All I/O functions are `async`
- Use `asyncio.Lock` for shared mutable state
- Never block the event loop with synchronous I/O

### Error handling
- Never silently swallow exceptions
- Use custom exception types from `sgu_client.py` for SGU errors
- Return structured error dicts from MCP tools instead of raising exceptions
- Log full diagnostic details server-side; sanitise external-facing error messages

### Configuration
- All secrets and settings via environment variables (Pydantic Settings in `config.py`)
- Never hard-code tokens, API keys, or base URLs
- Use `get_settings()` singleton to access config; reset `_settings = None` in tests

### Data integrity
- Preserve all source SGU field names and values exactly
- Never rename, translate, round, or normalise source values in place
- Add interpretations in a separate `context` sub-object
- Document Swedish source labels alongside English explanatory labels

### Security
- Token comparison uses `hmac.compare_digest` (constant-time)
- Never log tokens, API keys, or full addresses
- Reject all requests to `/mcp` without a valid Authorization token header
- Only allow outbound requests to configured SGU and Google endpoints

### Pagination
- Always follow OGC `next` links from the response, never construct page URLs manually
- Pass `params=None` (not `params={}`) when following next links to preserve query strings
- Enforce `MAX_INLINE_RESULTS` and `MAX_EXPORT_RECORDS` globally
- Use HMAC-signed continuation tokens; never expose raw offset/page state

### Testing
- Run tests with `python -m pytest tests/`
- Mock all external HTTP with `pytest_httpx` (`HTTPXMock`)
- Reset module-level singletons with `autouse=True` fixtures in `conftest.py`:
  `reset_settings_singleton`, `reset_sgu_client`, `reset_caches`
- Use `re.compile(rf"^{re.escape(url)}(\?.*)?$")` to match URLs with optional query params
- Use `is_reusable=True` on exception mocks that are retried multiple times
- Tests must pass without real secrets or network access

### Linting and formatting
- Ruff for lint + format: `ruff check . && ruff format --check .`
- Target Python 3.12: `ruff check --target-version py312`

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MCP_BEARER_TOKEN` | — | Required. Auth token for `/mcp` |
| `GOOGLE_MAPS_API_KEY` | — | Google Geocoding API key |
| `SGU_BASE_URL` | `https://api.sgu.se/...` | SGU OGC API base URL |
| `APP_ENV` | `development` | `development` / `staging` / `production` |
| `LOG_LEVEL` | `INFO` | Python log level |
| `MAX_INLINE_RESULTS` | `100` | Max records per MCP tool response |
| `MAX_EXPORT_RECORDS` | `50000` | Max records per export |
| `MAX_UPSTREAM_CONCURRENCY` | `4` | Max concurrent SGU requests |
| `CACHE_TTL_SECONDS` | `300` | Cache TTL in seconds |
| `EXPORT_TTL_SECONDS` | `3600` | Export file TTL in seconds |

## SGU Collections

| Collection | Purpose |
|---|---|
| `brunnar` | Well records (main collection) |
| `brunnar-lager` | Geological layer records; linked by `brunnsid` / `obsplatsid` |

## MCP Tools

| Tool | Purpose |
|---|---|
| `resolve_address` | Geocode a free-text address via Google Maps |
| `search_wells` | Full-text / spatial / attribute well search with pagination |
| `get_well` | Retrieve a single well by `brunnsid`, `obsplatsid`, or feature ID |
| `get_well_layers` | Get geological layers for a well |
| `summarize_well_area` | Aggregate statistics for a constrained area |
| `explain_field` | SGU field definitions, units, code values |
| `get_dataset_metadata` | API-level metadata with caching |
| `create_export` | Create filtered CSV or GeoJSON export |

## Deployment

- **Docker**: `docker build -t sgu-brunnar-mcp .`
- **Cloud Run region**: `europe-north1` (Stockholm)
- **Build**: `gcloud builds submit --config cloudbuild.yaml`
- **Health**: `GET /healthz` (liveness), `GET /readyz` (readiness)

## Known Limitations

- SGU API live access is not available in the sandbox; field names are based on OGC API
  Features standard and the problem specification
- In-memory cache and export store are lost on Cloud Run instance restart
- SWEREF99TM coordinate transformations depend on the `pyproj` / PROJ library
- `CACHE_TTL_SECONDS` default is 300 s; adjust for production workloads
