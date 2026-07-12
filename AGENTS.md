PROJECT PURPOSE

This repository contains a proof-of-concept Model Context Protocol (MCP) server for open geological data from the Swedish Geological Survey, SGU.

The first dataset is SGU's Brunnar dataset. It contains registered well records and geological layer observations associated with wells.

The intended result is a read-only MCP server that can be used by OpenAI-compatible clients and other MCP-compatible clients.

This is currently a proof of concept intended to demonstrate the value of MCP and SGU open data. It should be useful enough to support a future investment case, but it is not yet intended to be a production-grade national geological data platform.

Keep the implementation focused, understandable and easy to deploy. Do not introduce unnecessary infrastructure or attempt to support every SGU dataset immediately.

CORE OBJECTIVES

The server should allow a calling model to:

- Resolve ordinary addresses to geographic points.
- Find wells near an address.
- Search wells near coordinates.
- Search wells using a radius.
- Search wells using a bounding box.
- Search by municipality name or municipality code.
- Filter by well-use code.
- Filter by depth.
- Filter by capacity.
- Filter by position quality.
- Filter by drilling date.
- Retrieve an individual well.
- Retrieve geological layer records associated with a well.
- Summarize well information for a bounded area.
- Explain SGU Swedish field names and code values.
- Return source metadata and data-quality warnings.
- Create temporary CSV and GeoJSON exports.

The server must preserve original SGU data while providing enough contextual information for a calling model to translate or explain that data correctly.

The server must not pretend that it can answer questions requiring data that is not present in SGU Brunnar, including:

- Current drinking-water safety.
- Complete laboratory water-quality analysis.
- Exact cadastral property boundaries.
- Guaranteed sustainable groundwater yield.
- Complete hydrogeological assessments.
- Legal or regulatory conclusions.

PRIMARY CLIENT AND PROTOCOL

The initial development client is the OpenAI Platform remote MCP environment.

The MCP implementation must remain standards-oriented and must not contain OpenAI-specific business logic.

The server should remain usable by other MCP-compatible clients that support remote MCP over Streamable HTTP.

The current development authentication model is a simple bearer token:

Authorization: Bearer YOUR_MCP_BEARER_TOKEN

Do not implement OAuth unless explicitly requested later.

REPOSITORY AND DEVELOPMENT ENVIRONMENT

The project should work in a development container or Docker container.

Do not require developers to create or activate a Python virtual environment.

Documentation must prefer Docker or a development container over local Python installation.

The project should support:

- Python 3.12 or later.
- Docker.
- Development containers where useful.
- Google Cloud Shell for deployment.
- Windows developers using PowerShell.

Do not assume that the developer can run gcloud locally.

Do not assume Docker is available inside every agent environment. If Docker is unavailable, run Python compilation and available tests and clearly report what could not be run.

AUTHORITATIVE SGU API

The primary SGU OGC API endpoint is:

https://api.sgu.se/oppnadata/brunnar/ogc/features/v1

Important endpoints include:

https://api.sgu.se/oppnadata/brunnar/ogc/features/v1/collections

https://api.sgu.se/oppnadata/brunnar/ogc/features/v1/collections/brunnar

https://api.sgu.se/oppnadata/brunnar/ogc/features/v1/collections/brunnar/queryables

https://api.sgu.se/oppnadata/brunnar/ogc/features/v1/collections/brunnar/items

https://api.sgu.se/oppnadata/brunnar/ogc/features/v1/collections/brunnar-lager

https://api.sgu.se/oppnadata/brunnar/ogc/features/v1/collections/brunnar-lager/queryables

https://api.sgu.se/oppnadata/brunnar/ogc/features/v1/collections/brunnar-lager/items

Current SGU product documentation:

https://resource.sgu.se/dokument/produkter/brunnar-beskrivning.pdf

SGU is a public source and does not require an SGU API key.

Always verify live API behavior when possible.

If live access is unavailable:

- Do not invent fields.
- Do not claim that live verification succeeded.
- Use the known schema in this file.
- Maintain or improve scripts/verify_sgu.py.
- Clearly report that live verification could not be performed.

SGU COLLECTIONS

The current implementation focuses on two collections.

brunnar

Main well records.

brunnar-lager

Geological layer records associated with wells.

The two collections are related through identifiers such as:

- obsplatsid
- brunnsid

The layer relationship should be treated as one-to-many unless live metadata proves otherwise.

AUTHORITATIVE CURRENT FIELD NAMES

MAIN COLLECTION: BRUNNAR

The main collection contains fields including:

obsplatsid
brunnsid
n
e
posvardering_kod
posvardering
kommunkod
kommunnamn
fastighet
ort
lage_specifikt
borrdatum
tecken_vattenmangd
kapacitet
tecken_niva
grundvattenniva
nivadatum
bottendiam
totaldjup
tecken_jorddjup
jorddjup
rorborrning_till
stalror_till
plastror_till
tatning_kod
tatning
anvandning_kod
anvandning
gradborrning
allman_anmarkning
grundvattenanmarkning
geom

The GeoServer feature identifier may also appear as fid or as the top-level GeoJSON id.

LAYER COLLECTION: BRUNNAR-LAGER

The layer collection contains fields including:

lagerid
obsplatsid
brunnsid
n
e
lagernr
djup_fran
djup_till
jordart_bergart
lageranmarkning
geom

Do not use invented alternative field names such as:

anvandningskod
positionskvalitetskod
positionskvalitet
vattenniva
startdjup
slutdjup
jordart
bergart
lagernotering

The existing field definitions should be checked against the live API and updated only when justified by current SGU metadata.

SGU CODE LISTS

WELL-USE CODES

Known well-use codes include:

ÖVR
BEV
ENE
HUS
IND
OBS
SAM
LAN
VAF

The original code must always be preserved.

Translations and explanations must be added separately.

POSITION-QUALITY CODES

Known position-quality codes include:

9
3
0
1
2

The current meanings are approximately:

9 = Well cannot be located.
3 = Location not checked.
0 = Maximum error less than 100 metres.
1 = Maximum error less than 250 metres.
2 = Uncertain position.

Never replace a source code with only an English interpretation.

SEALING CODES

Known sealing codes include:

T
C
B
P
L
M
N
Ö

Use current SGU documentation for precise Swedish and English descriptions.

SOURCE DATA PRESERVATION

Source data must be preserved exactly.

Do not:

- Rename source fields in the raw feature.
- Translate raw source values in place.
- Round numeric source values.
- Replace source codes with translated descriptions.
- Replace source geometries.
- Silently convert partial dates into full dates.
- Discard source identifiers.

Where transformed or interpreted data is needed, return it in a separate structure.

A suitable result structure is:

{
  "raw_feature": {
    "type": "Feature",
    "id": "original-id",
    "geometry": {},
    "properties": {}
  },
  "feature": {
    "type": "Feature",
    "id": "original-id",
    "geometry": {},
    "properties": {}
  },
  "interpretation": {},
  "source_crs": "EPSG:3006",
  "output_crs": "EPSG:4326"
}

The raw_feature must remain unchanged.

The transformed feature may contain output geometry converted to WGS84.

The interpretation structure may include:

- Swedish field label.
- English label.
- Source value.
- Unit.
- Description.
- Code translation.
- Caveats.

COORDINATE REFERENCE SYSTEMS

SGU source coordinates are stored in:

EPSG:3006 — SWEREF 99 TM

The fields n and e represent source coordinates in the native SGU coordinate system:

e = easting
n = northing

The application may accept user input in WGS84 latitude and longitude.

When transforming coordinates:

- Use pyproj.
- Use always_xy=True where appropriate.
- Clearly distinguish longitude/latitude from latitude/longitude.
- Never label coordinates as WGS84 unless they were actually transformed or explicitly requested in a WGS84-compatible CRS.

For GeoJSON output, use WGS84-compatible coordinates where practical.

For SGU queries:

- If a WGS84 bbox is accepted from the user, transform it to the CRS used by the SGU query.
- Explicitly declare the bbox CRS using the OGC API parameter supported by SGU.
- Verify the exact behavior against the live service.

Apply the same CRS handling consistently to:

- search_wells;
- summarize_well_area;
- create_export;
- radius filtering;
- CSV coordinate columns;
- GeoJSON output.

Use the source n and e fields as a reliable fallback for point transformation.

ADDRESS HANDLING

Address input is supported through Google Geocoding.

The tool receives the raw address from the caller and is responsible for geocoding it.

A normal address lookup returns a geographic point, not a cadastral property boundary.

The system must clearly distinguish:

well search near an address point

from:

analysis inside a cadastral fastighet polygon

The first proof of concept only supports address-point analysis.

Future work may add:

- Lantmäteriet integration.
- Fastighet polygons.
- User-supplied property polygons.
- A separate polygon service.

ADDRESS VALIDATION RULES

For tools that support addresses:

- Address plus radius is valid.
- Address without radius is invalid for bounded spatial searches.
- Address combined with latitude or longitude is invalid.
- Latitude and longitude must be supplied together.
- Latitude and longitude plus radius is valid.
- Bbox is valid.
- Address-only nationwide searches must not be allowed implicitly.

CRITICAL ADDRESS BUG TO AVOID

Do not check for a spatial constraint before considering the address.

This is wrong:

has_spatial = any(
    [
        latitude is not None and longitude is not None and radius_m,
        bbox,
    ]
)

The reason is that the address has not yet been geocoded.

The validation must recognize:

address and radius_m is not None

before geocoding.

The summarize_well_area function must accept:

{
  "address": "Drottninggatan 1, Stockholm",
  "radius_m": 1000
}

It must then geocode the address and use the returned coordinates for the SGU query.

MCP TOOLS

The expected tools are:

resolve_address
search_wells
get_well
get_well_layers
summarize_well_area
explain_field
get_dataset_metadata
create_export

resolve_address

Use Google Geocoding.

Return:

- Original address.
- Normalized address.
- Latitude.
- Longitude.
- Address components where useful.
- Location precision.
- Provider.
- Warning that the result is not a cadastral boundary.

search_wells

Support:

- Address plus radius.
- Latitude/longitude plus radius.
- Bbox.
- Municipality name.
- Municipality code.
- Well-use code.
- Depth limits.
- Capacity limits.
- Position-quality code.
- Drilling-date filters.
- Sorting.
- Continuation tokens.
- Optional contextual interpretation.

Do not allow unbounded searches without an explicit safe mechanism.

get_well

Accept:

- brunnsid;
- obsplatsid;
- feature ID.

Return both raw and transformed data.

get_well_layers

Accept:

- brunnsid;
- obsplatsid.

Return layers ordered by:

1. lagernr;
2. djup_fran.

Preserve raw layer records.

summarize_well_area

Support bounded areas based on:

- Address plus radius.
- Coordinates plus radius.
- Bbox.

Return:

- Total count.
- Records scanned.
- Completeness.
- Well-use distribution.
- Position-quality distribution.
- Depth statistics.
- Capacity statistics.
- Groundwater-level availability.
- Missing-value counts.
- Caveats.

Do not claim layer availability unless it was actually checked.

explain_field

Explain:

- Source field name.
- Swedish label.
- English label.
- Unit.
- Source definition.
- Code values.
- Caveats.
- Source reference.

get_dataset_metadata

Return current SGU metadata, including:

- Collections.
- Queryables.
- CRS.
- Extent.
- Formats.
- Links.
- License.
- Field definitions.
- Known limitations.

Do not hardcode historical metadata when current SGU metadata is available.

create_export

Support:

- CSV.
- GeoJSON.

Exports may be temporary and in-memory during the proof of concept.

The export must:

- Respect a separate export limit.
- Not be limited by the inline MCP result limit.
- Use correct WGS84 geometry when exporting GeoJSON.
- Include source identifiers.
- Include a retrieval timestamp.
- Expire after the configured TTL.

PAGINATION

The SGU service is potentially large.

Never attempt to return the entire dataset to a model.

The SGU client must:

- Follow OGC API next links.
- Preserve all query parameters in those links.
- Avoid manually reconstructing next URLs unless verified necessary.
- Detect repeated next links.
- Deduplicate records.
- Enforce maximum fetch limits.
- Return explicit truncation warnings.

Distinguish between:

MAX_INLINE_RESULTS
MAX_EXPORT_RECORDS
Summary scan limit
Upstream page size

Do not apply the inline result limit to exports or summaries.

Continuation tokens must preserve all query state needed for the next request.

Continuation tokens must:

- Be signed.
- Use a configured secret.
- Expire.
- Avoid exposing sensitive query data.
- Not contain hardcoded secrets.
- Not silently lose filters.
- Be invalidated or safely handled after use.

CACHING

The proof of concept may use bounded in-memory caching.

Cache:

- SGU metadata.
- Queryables.
- Code lists.
- Recent result pages.
- Recent address geocoding results.
- Temporary exports.

Cache behavior is allowed to be best effort.

Cache loss after a Cloud Run restart is acceptable during development.

Do not introduce a large database for the proof of concept.

AUTHENTICATION AND SECURITY

Use application-level bearer authentication:

Authorization: Bearer YOUR_MCP_BEARER_TOKEN

The token must come from:

MCP_BEARER_TOKEN

Do not hardcode tokens.

Use constant-time comparison.

Do not log:

- Bearer tokens.
- Google API keys.
- Complete addresses unless explicitly required.
- Unnecessary coordinates that could expose sensitive locations.

Production configuration must require:

MCP_BEARER_TOKEN
MCP_CONTINUATION_SECRET

The Google API key must come from:

GOOGLE_MAPS_API_KEY

Only make outbound requests to:

- The configured SGU base URL.
- The configured Google Geocoding API endpoint.

Do not permit arbitrary caller-provided outbound URLs.

CLOUD RUN DEPLOYMENT

Preferred Google Cloud Run region:

europe-north2

This corresponds to Stockholm.

The current proof of concept should use:

- Cloud Build.
- Artifact Registry.
- Cloud Run.
- Secret Manager.

Required secrets:

MCP_BEARER_TOKEN
MCP_CONTINUATION_SECRET
GOOGLE_MAPS_API_KEY

Cloud Run should allow the request to reach the application, while application-level bearer authentication protects the MCP endpoint.

Do not rely on Cloud Run IAM alone if the OpenAI remote MCP client only sends the application bearer token.

Do not automatically create or deploy Google Cloud resources during development unless explicitly instructed.

HEALTH AND DIAGNOSTICS

The application should expose:

GET /healthz
GET /readyz
GET /api/status
GET /api/metadata
GET /

Expected behavior:

- /healthz checks process liveness.
- /readyz performs a lightweight SGU connectivity check.
- /api/status shows configuration status without secrets.
- /api/metadata returns dataset metadata.
- / returns a simple HTML diagnostic page.

Health and status output must never expose secrets.

LOGGING

Use structured logs where practical.

Include:

- Request ID.
- Tool name.
- Duration.
- Upstream service.
- Upstream status.
- Result count.
- Cache hit or miss.
- Error category.

Do not include:

- Bearer tokens.
- Google API keys.
- Full addresses by default.
- Unnecessary personal data.

The application should update SGU connectivity status when SGU requests succeed or fail.

TESTING

Tests must use real SGU-shaped field names and values.

Do not allow tests to pass using invented fields.

Required tests include:

- Bearer authentication.
- Missing and invalid tokens.
- Production secret validation.
- Address plus radius.
- Address without radius.
- Conflicting address and coordinates.
- Coordinate transformation.
- Native CRS bbox generation.
- Exact radius filtering.
- Partial drilling dates.
- SGU field definitions.
- Code-list interpretation.
- Pagination.
- Continuation state preservation.
- Repeated next-link detection.
- Export limits.
- Raw feature preservation.
- GeoJSON coordinate output.
- Health endpoints.
- Readiness failure behavior.
- Verification-script failure behavior.

Tests should use mocked external HTTP by default.

The live SGU API should only be used by an explicit integration or verification command.

Preferred Docker-based test command:

docker run --rm -v "$($PWD):/workspace" -w /workspace python:3.12-slim bash -lc "pip install --no-cache-dir '.[dev]' && pytest -q"

Preferred compilation check:

python -m compileall src tests scripts

Do not claim tests passed if dependencies were missing or tests were not actually executed.

README REQUIREMENTS

The README must be written for a novice.

It must explain:

1. What the project does.
2. What MCP is used for in this project.
3. That SGU is the source.
4. That no Python virtual environment is required.
5. How to copy .env.example to .env.
6. How to build with Docker.
7. How to run with Docker.
8. How to open the diagnostic HTML page.
9. How to test health endpoints.
10. How to run tests in Docker.
11. How to run live SGU verification.
12. How to configure the OpenAI remote MCP server.
13. How to create Google Maps credentials.
14. How to use Google Cloud Shell.
15. How to create all required secrets.
16. How to build and deploy to Cloud Run.
17. What an address point does and does not represent.
18. What the main SGU data-quality limitations are.
19. That exports and caches are temporary during the proof of concept.
20. How to troubleshoot common failures.

Use clear Windows PowerShell examples.

Never use fake redacted examples such as:

Authorization: ******

Use:

Authorization: Bearer YOUR_MCP_BEARER_TOKEN

CURRENT KNOWN PROBLEM AREAS

The following areas require particular attention:

1. Address validation in summarize_well_area.
2. Consistent native CRS bbox handling.
3. Explicit bbox-crs behavior.
4. Correct WGS84 transformation.
5. Raw feature preservation.
6. Partial drilling-date precision.
7. Production secret validation.
8. Uvicorn Docker startup.
9. Verification script quality.
10. README clarity.
11. Continuation token completeness.
12. Export limits separate from inline MCP limits.
13. Tests based on actual SGU-shaped fixtures.
14. Live API verification.

CHANGE-MANAGEMENT RULES

Before changing code:

1. Inspect the existing implementation.
2. Run or inspect the relevant tests.
3. Check the current SGU metadata.
4. Make the smallest coherent change.
5. Add or update tests.
6. Update README documentation when behavior changes.
7. Run formatting and compilation checks.
8. Review the final diff.

Do not:

- Commit secrets.
- Deploy cloud resources automatically.
- Replace working architecture without justification.
- Invent SGU fields.
- Silently change source values.
- Claim live verification without network access.
- Claim tests passed when they were not run.

When finishing a task, report:

- Files changed.
- Behavior changed.
- Tests run.
- Tests not run and why.
- Live SGU verification status.
- Assumptions.
- Remaining limitations.