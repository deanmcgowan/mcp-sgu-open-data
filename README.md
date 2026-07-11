# SGU Brunnar MCP Server

A read-only [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes
the [Swedish Geological Survey (SGU)](https://www.sgu.se/) **Brunnar** (wells) open dataset over
Streamable HTTP transport.

The server is designed for deployment on **Google Cloud Run** and can be configured as a
**remote MCP server** in the OpenAI Platform.

---

## Table of Contents

- [Architecture](#architecture)
- [Available Tools](#available-tools)
- [Local Setup](#local-setup)
- [Running Locally](#running-locally)
- [Running Tests](#running-tests)
- [Environment Variables](#environment-variables)
- [MCP Endpoint](#mcp-endpoint)
- [OpenAI Platform Configuration](#openai-platform-configuration)
- [Google Geocoding Setup](#google-geocoding-setup)
- [Docker Build](#docker-build)
- [Google Cloud Run Deployment](#google-cloud-run-deployment)
- [Paging Behaviour](#paging-behaviour)
- [Export Behaviour](#export-behaviour)
- [Security Considerations](#security-considerations)
- [Data-Quality Limitations](#data-quality-limitations)
- [Future Extension to Other SGU Datasets](#future-extension-to-other-sgu-datasets)
- [Known Limitations](#known-limitations)

---

## Architecture

```
Client (OpenAI / any MCP client)
        │ POST /mcp
        ▼
BearerTokenMiddleware  ── 401 if token missing/invalid
        │
        ▼
FastMCP (Streamable HTTP, stateless)
        │
        ▼
MCP Tools  ──→  SGUClient  ──→  api.sgu.se (OGC API Features)
           ──→  GeocodingClient  ──→  maps.googleapis.com
           ──→  ExportStore (in-memory, TTL)
           ──→  InMemoryCache (TTL, bounded LRU)
```

**Key modules:**

| Module | Responsibility |
|---|---|
| `app.py` | Starlette ASGI app, routes, health endpoints |
| `auth.py` | Constant-time bearer token middleware |
| `config.py` | Pydantic Settings from environment |
| `sgu_client.py` | SGU OGC API client (retry, pagination, dedup) |
| `geocoding.py` | Google Geocoding API client |
| `pagination.py` | HMAC-signed continuation tokens |
| `field_defs.py` | SGU field definitions, code lists |
| `coordinates.py` | Haversine distance, bbox, SWEREF99TM ↔ WGS84 |
| `exports.py` | In-memory CSV / GeoJSON export store |

---

## Available Tools

| Tool | Description |
|---|---|
| `resolve_address` | Geocode a free-text address (Swedish or international) via Google Maps |
| `search_wells` | Search wells by location, radius, bbox, municipality, attributes, and depth |
| `get_well` | Retrieve a single well by `brunnsid`, `obsplatsid`, or feature ID |
| `get_well_layers` | Get geological layer records for a well |
| `summarize_well_area` | Aggregate statistics (depth, capacity, quality) for a bounded area |
| `explain_field` | Explain SGU field names, units, and code values in Swedish and English |
| `get_dataset_metadata` | Dataset and API metadata (collections, CRS, extent, license) |
| `create_export` | Create a filtered CSV or GeoJSON export (download URL returned) |

### Sample Tool Calls

**Search wells near an address (English)**
```json
{
  "tool": "search_wells",
  "arguments": {
    "address": "Drottninggatan 1, Stockholm",
    "radius_m": 2000,
    "page_size": 10
  }
}
```

**Sök brunnar nära en adress (Svenska)**
```json
{
  "tool": "search_wells",
  "arguments": {
    "address": "Drottninggatan 1, Stockholm",
    "radius_m": 2000,
    "page_size": 10
  }
}
```

**Retrieve a well by ID**
```json
{
  "tool": "get_well",
  "arguments": {
    "brunnsid": 12345,
    "include_layers": true
  }
}
```

**Export to GeoJSON**
```json
{
  "tool": "create_export",
  "arguments": {
    "municipality_code": "0180",
    "format": "geojson",
    "max_records": 500
  }
}
```

---

## Local Setup

**Prerequisites:** Python 3.12+, pip

```bash
# Clone the repository
git clone https://github.com/deanmcgowan/mcp-sgu-open-data.git
cd mcp-sgu-open-data

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy the example config
cp .env.example .env
# Edit .env and fill in MCP_BEARER_TOKEN and GOOGLE_MAPS_API_KEY
```

---

## Running Locally

```bash
# Set environment variables (or use .env with a tool like python-dotenv)
export MCP_BEARER_TOKEN=my-dev-token
export GOOGLE_MAPS_API_KEY=my-google-key
export APP_ENV=development

# Start the server
python -m mcp_sgu.app

# Or with uvicorn directly
uvicorn mcp_sgu.app:create_app --factory --host 0.0.0.0 --port 8080 --reload
```

Verify the server is running:

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/api/status
```

---

## Running Tests

```bash
# Run all tests (no external secrets required)
python -m pytest tests/

# With coverage
python -m pytest tests/ --cov=mcp_sgu --cov-report=term-missing

# Linting
ruff check .
ruff format --check .
```

Tests use mocked HTTP responses and do **not** require real SGU or Google credentials.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MCP_BEARER_TOKEN` | Yes | — | Auth token that MCP clients must present |
| `MCP_CONTINUATION_SECRET` | Yes | — | Secret for opaque continuation tokens |
| `GOOGLE_MAPS_API_KEY` | For geocoding | — | Google Maps / Geocoding API key |
| `SGU_BASE_URL` | No | `https://api.sgu.se/oppnadata/brunnar/ogc/features/v1` | SGU OGC API base URL |
| `APP_ENV` | No | `development` | `development` / `staging` / `production` |
| `LOG_LEVEL` | No | `INFO` | Python log level |
| `MAX_INLINE_RESULTS` | No | `100` | Max records per MCP tool response |
| `MAX_EXPORT_RECORDS` | No | `50000` | Max records per export |
| `MAX_UPSTREAM_CONCURRENCY` | No | `4` | Max concurrent SGU requests |
| `CACHE_TTL_SECONDS` | No | `300` | Cache TTL in seconds |
| `EXPORT_TTL_SECONDS` | No | `3600` | Export file TTL before deletion |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8080` | Server port (Cloud Run sets this automatically) |

---

## MCP Endpoint

```
POST https://<SERVICE_URL>/mcp
Authorization: ******
Content-Type: application/json
```

The endpoint uses the [Streamable HTTP MCP transport](https://modelcontextprotocol.io/docs/concepts/transports).
All requests without a valid `Authorization: ****** header are rejected with HTTP 401.

---

## OpenAI Platform Configuration

Add the server as a remote MCP server in your OpenAI assistant configuration:

```json
{
  "type": "mcp",
  "server_label": "sgu-brunnar",
  "server_url": "https://<SERVICE_URL>/mcp",
  "headers": {
    "Authorization": "******"
  }
}
```

> **Security note:** Never commit real tokens to source control. Use environment variables or
> secrets management.

---

## Google Geocoding Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the **Geocoding API** for your project
3. Create an API key under **APIs & Services → Credentials**
4. Restrict the key to the Geocoding API and your server's IP/referrer if possible
5. Set `GOOGLE_MAPS_API_KEY=<your-key>` in your environment or `.env` file

The `resolve_address` tool and address-based `search_wells` searches require this key.
Without it, address-based searches will return an error.

---

## Docker Build

```bash
# Build the image locally
docker build -t sgu-brunnar-mcp:local .

# Run locally with environment variables
docker run --rm \
  -e MCP_BEARER_TOKEN=dev-token \
  -e GOOGLE_MAPS_API_KEY=your-key \
  -e APP_ENV=development \
  -p 8080:8080 \
  sgu-brunnar-mcp:local

# Verify
curl http://localhost:8080/healthz
```

---

## Google Cloud Run Deployment

### Prerequisites

- Google Cloud SDK (`gcloud`) installed and authenticated
- Project with billing enabled
- Required APIs enabled (see below)

### 1. Enable Required APIs

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

### 2. Create Artifact Registry Repository

```bash
gcloud artifacts repositories create sgu-mcp \
  --repository-format=docker \
  --location=europe-north2 \
  --description="SGU MCP server images"
```

### 3. Build with Cloud Build

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions _REGION=europe-north2,_REPO=sgu-mcp,_SERVICE=sgu-brunnar-mcp .
```

### 4. Create Secrets

```bash
# Store the bearer token in Secret Manager
echo -n "$(python -c "import secrets; print(secrets.token_urlsafe(32))")" | \
  gcloud secrets create MCP_BEARER_TOKEN --data-file=-

# Store the Google Maps key
echo -n "YOUR_GOOGLE_MAPS_API_KEY" | \
  gcloud secrets create GOOGLE_MAPS_API_KEY --data-file=-
```

### 5. Deploy to Cloud Run

```bash
PROJECT=$(gcloud config get-value project)
REGION=europe-north2
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/sgu-mcp/sgu-brunnar-mcp:latest"

gcloud run deploy sgu-brunnar-mcp \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --min-instances=0 \
  --max-instances=3 \
  --memory=512Mi \
  --cpu=1 \
  --set-env-vars="APP_ENV=production,LOG_LEVEL=INFO" \
  --set-secrets="MCP_BEARER_TOKEN=MCP_BEARER_TOKEN:latest,GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY:latest"
```

### 6. Get the Service URL

```bash
gcloud run services describe sgu-brunnar-mcp \
  --region=europe-north2 \
  --format="value(status.url)"
```

### 7. Test Health Endpoints

```bash
SERVICE_URL=$(gcloud run services describe sgu-brunnar-mcp \
  --region=europe-north2 --format="value(status.url)")

curl "${SERVICE_URL}/healthz"
curl "${SERVICE_URL}/readyz"
curl "${SERVICE_URL}/api/status"
```

### 8. Allow Invocations (if using Cloud Run IAM)

If you use `--no-allow-unauthenticated` and want to call from outside GCP:

```bash
# Add allUsers invoker (use with caution; the bearer token provides app-level auth)
gcloud run services add-iam-policy-binding sgu-brunnar-mcp \
  --region=europe-north1 \
  --member=allUsers \
  --role=roles/run.invoker
```

---

## Paging Behaviour

The server follows OGC API Features `next` link pagination:

- Each tool call returns up to `MAX_INLINE_RESULTS` records (default 100)
- If more records exist, a `continuation_token` is returned
- Pass the `continuation_token` in the next call to get the next page
- Continuation tokens are HMAC-signed and expire after `EXPORT_TTL_SECONDS`
- The server enforces `MAX_INLINE_RESULTS` globally; it will not return more than this even if
  the upstream page is larger
- Partial-result warnings are included when a limit is reached

---

## Export Behaviour

The `create_export` tool:

1. Streams matching records from SGU (up to `MAX_EXPORT_RECORDS`)
2. Serialises to CSV (UTF-8 with BOM for Excel compatibility) or GeoJSON
3. Stores the result in memory with a TTL of `EXPORT_TTL_SECONDS`
4. Returns a download URL: `GET /api/exports/{export_id}` (requires same bearer token)
5. Exports are automatically deleted after the TTL expires

> **Cloud Run restart note:** In-memory exports are lost when the Cloud Run instance restarts.
> For production, replace `ExportStore` with a Google Cloud Storage backend.

---

## Security Considerations

- The `/mcp` endpoint and `/api/exports` require `Authorization: ******`
- Token comparison uses `hmac.compare_digest` to prevent timing attacks
- Tokens are never logged
- The server only makes outbound requests to the configured SGU URL and Google Maps API
- No arbitrary upstream URLs can be injected by callers
- Stack traces are not exposed in production error responses
- No secrets are stored in the source code; all secrets come from environment variables

---

## Data-Quality Limitations

- **Position quality**: Well coordinates vary in accuracy (GPS, map digitising, address-level).
  Always check `posvardering_kod` and `posvardering`.
- **Capacity**: `kapacitet` is the *reported* capacity at the time of drilling, not necessarily
  the current sustainable yield.
- **Depth**: `totaldjup` may be missing or approximate.
- **Groundwater level**: `grundvattenniva` may reflect conditions at the time of drilling only.
- **Address geocoding**: The returned point is a geocoded address centroid, not a cadastral
  parcel boundary.
- **Date precision**: Drilling dates may be partial (year only) or absent.
- **Source language**: All source field names and values are in Swedish. Use `explain_field` for
  translations and definitions.

---

## Future Extension to Other SGU Datasets

The architecture is designed to support additional SGU datasets:

1. **Add a new collection identifier** in `field_defs.py` or a new field definitions module
2. **Create collection-specific tools** in `src/mcp_sgu/tools/` following the same pattern
3. **Register the new tools** in `app.py`
4. **Update `SGU_BASE_URL`** or add a new `SGU_*_BASE_URL` configuration variable

Candidate future datasets from SGU OGC APIs:
- `jordarter` — Quaternary deposits / soil types
- `berggrundsgeologi` — Bedrock geology
- `grundvatten` — Groundwater monitoring stations
- `geofysik` — Geophysical survey data

---

## Known Limitations

- **Live verification required**: This sandbox cannot reach the SGU API. Run
  `python scripts/verify_sgu.py` before production deployment to verify queryables, storage CRS,
  and pagination against the live service.
- **In-memory state**: Cache and exports are stored in process memory; lost on restart.
- **No persistent storage**: Export files are not stored in Cloud Storage in this version.
- **Single region**: Configured for `europe-north2` (Stockholm); other regions require config
  changes.
- **Stateless MCP**: Uses `stateless_http=True` which means no server-side session state is
  maintained between MCP requests.
