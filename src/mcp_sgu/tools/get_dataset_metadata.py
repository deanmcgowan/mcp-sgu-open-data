"""Tool: get_dataset_metadata — return SGU dataset and API metadata."""

from __future__ import annotations

import datetime
from typing import Any

from mcp_sgu.field_defs import FIELD_DEFINITIONS, POSITION_QUALITY_CODES, SEALING_CODES, WELL_USE_CODES
from mcp_sgu.logging_config import get_logger, set_tool_name
from mcp_sgu.sgu_client import SGUError, get_sgu_client

logger = get_logger(__name__)

_COLLECTIONS = ["brunnar", "brunnar-lager"]


async def get_dataset_metadata() -> dict[str, Any]:
    """Return metadata about the SGU Brunnar dataset and API capabilities.

    Includes:
    - API title and description
    - Collections and their extents
    - Supported formats and CRS
    - Queryable fields
    - Code lists
    - License and data quality notes
    - SGU documentation references
    """
    set_tool_name("get_dataset_metadata")

    client = get_sgu_client()

    # Fetch landing page and collections
    landing: dict[str, Any] = {}
    collections_data: list[dict[str, Any]] = []
    queryables: dict[str, Any] = {}
    errors: list[str] = []

    try:
        landing = await client.get_landing_page()
    except SGUError as exc:
        errors.append(f"Could not fetch landing page: {exc}")

    try:
        coll_resp = await client.get_collections()
        collections_data = coll_resp.get("collections", [])
    except SGUError as exc:
        errors.append(f"Could not fetch collections: {exc}")

    for coll_id in _COLLECTIONS:
        try:
            q = await client.get_queryables(coll_id)
            queryables[coll_id] = q
        except SGUError as exc:
            errors.append(f"Could not fetch queryables for {coll_id}: {exc}")

    return {
        "api_title": landing.get("title", "SGU Brunnar OGC API Features"),
        "api_description": landing.get("description"),
        "api_version": "OGC API Features 1.0",
        "base_url": client._base_url,
        "collections": _summarize_collections(collections_data, _COLLECTIONS),
        "queryables": queryables,
        "supported_formats": _formats(landing, collections_data),
        "crs": {
            "storage": "EPSG:3006 (SWEREF 99 TM)",
            "output": "EPSG:4326 (WGS84), transformed by this server",
            "description": "SGU Brunnar is stored in SWEREF 99 TM (EPSG:3006).",
        },
        "field_definitions": FIELD_DEFINITIONS,
        "code_lists": {
            "anvandning_kod": WELL_USE_CODES,
            "posvardering_kod": POSITION_QUALITY_CODES,
            "tatning_kod": SEALING_CODES,
        },
        "license": {
            "name": "CC0 1.0 Universal",
            "url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "source": "Current SGU Brunnar product documentation",
        },
        "data_quality_notes": [
            "Data completeness varies; many wells lack capacity or depth measurements.",
            "Position accuracy depends on posvardering_kod; some wells have uncertain coordinates.",
            "Drilling dates may be partial (year only).",
            "Capacity values reflect reported measurements, not guaranteed sustainable yield.",
        ],
        "sgu_documentation": [
            "https://resource.sgu.se/dokument/produkter/brunnar-beskrivning.pdf",
            "https://api.sgu.se/oppnadata/brunnar/ogc/features/v1",
            "https://www.sgu.se/produkter-och-tjanster/databaser-och-apier/api-brunnsarkivet/",
        ],
        "retrieval_timestamp": _now_iso(),
        "warnings": errors if errors else None,
    }


def _summarize_collections(
    collections: list[dict[str, Any]],
    known_ids: list[str],
) -> list[dict[str, Any]]:
    """Return a summary of available collections."""
    summary = []
    collection_map = {c.get("id"): c for c in collections}

    for coll_id in known_ids:
        coll = collection_map.get(coll_id, {})
        entry: dict[str, Any] = {
            "id": coll_id,
            "title": coll.get("title", coll_id),
            "description": coll.get("description"),
        }
        extent = coll.get("extent")
        if extent:
            entry["extent"] = extent
        links = coll.get("links", [])
        entry["links"] = links
        summary.append(entry)

    # Include any unexpected collections from the API
    for coll in collections:
        if coll.get("id") not in known_ids:
            summary.append(
                {
                    "id": coll.get("id"),
                    "title": coll.get("title"),
                    "description": coll.get("description"),
                    "note": "Unexpected collection not currently served by this MCP server",
                }
            )

    return summary


def _formats(landing: dict[str, Any], collections: list[dict[str, Any]]) -> list[str]:
    """Collect advertised response formats when available."""
    formats = {"application/geo+json", "application/json"}
    for resource in [landing, *collections]:
        for link in resource.get("links", []):
            if link.get("type"):
                formats.add(link["type"])
    return sorted(formats)


def _now_iso() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()
