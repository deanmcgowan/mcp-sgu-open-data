"""Tool: search_wells — search the SGU brunnar collection."""

from __future__ import annotations

import datetime
from typing import Any

from mcp_sgu.coordinates import (
    feature_coordinates,
    haversine_distance_m,
    radius_to_bbox,
)
from mcp_sgu.field_defs import enrich_feature
from mcp_sgu.geocoding import GeocodingError, geocode_address
from mcp_sgu.logging_config import get_logger, set_tool_name
from mcp_sgu.pagination import (
    ContinuationTokenError,
    decode_continuation_token,
    encode_continuation_token,
)
from mcp_sgu.sgu_client import SGUError, get_sgu_client

logger = get_logger(__name__)

_COLLECTION = "brunnar"
_ALLOWED_SORT_FIELDS = {
    "brunnsid", "kommunkod", "kommunnamn", "kapacitet",
    "totaldjup", "borrningsstart", "borrningsslut",
}


async def search_wells(  # noqa: PLR0912, PLR0913, PLR0914, PLR0915
    address: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_m: float | None = None,
    bbox: list[float] | None = None,
    municipality_name: str | None = None,
    municipality_code: str | None = None,
    well_use_code: str | None = None,
    min_total_depth: float | None = None,
    max_total_depth: float | None = None,
    min_capacity: float | None = None,
    max_capacity: float | None = None,
    position_quality_code: str | None = None,
    drilling_date_from: str | None = None,
    drilling_date_to: str | None = None,
    has_layers: bool | None = None,
    sort_field: str | None = None,
    sort_direction: str = "asc",
    page_size: int = 50,
    continuation_token: str | None = None,
) -> dict[str, Any]:
    """Search the SGU brunnar (wells) collection.

    Parameters
    ----------
    address:
        Free-text address; will be geocoded to lat/lon.
    latitude, longitude:
        Explicit coordinates (WGS84).
    radius_m:
        Radius in metres around the point (requires lat/lon or address).
    bbox:
        Bounding box as [min_lon, min_lat, max_lon, max_lat].
    municipality_name:
        Filter by municipality name (partial match).
    municipality_code:
        Filter by SCB municipality code (4 digits).
    well_use_code:
        Filter by well use code (e.g. ``"V"`` for water supply).
    min_total_depth, max_total_depth:
        Filter by total well depth (metres).
    min_capacity, max_capacity:
        Filter by reported capacity (l/h).
    position_quality_code:
        Filter by position quality code.
    drilling_date_from, drilling_date_to:
        Filter by drilling date range (ISO date strings).
    has_layers:
        If True, only return wells with layer data; if False, only without.
    sort_field:
        Field to sort by.
    sort_direction:
        ``"asc"`` or ``"desc"``.
    page_size:
        Number of records to return per page (max 100).
    continuation_token:
        Token from a previous response to fetch the next page.
    """
    set_tool_name("search_wells")

    from mcp_sgu.config import get_settings
    settings = get_settings()

    page_size = min(max(1, page_size), settings.max_inline_results)

    # --- Continuation token ---
    if continuation_token:
        try:
            state = decode_continuation_token(continuation_token)
        except ContinuationTokenError as exc:
            return {"error": "invalid_continuation_token", "detail": str(exc)}
        # Restore query state
        params = state.get("params", {})
        offset = state.get("offset", 0)
        resolved_lat = state.get("lat")
        resolved_lon = state.get("lon")
        radius = state.get("radius_m")
    else:
        offset = 0
        resolved_lat = latitude
        resolved_lon = longitude
        radius = radius_m
        params: dict[str, Any] = {}

        # --- Input validation ---
        if address and (latitude is not None or longitude is not None):
            return {
                "error": "conflicting_inputs",
                "detail": "Provide either 'address' or 'latitude'/'longitude', not both.",
            }

        if radius_m is not None and radius_m <= 0:
            return {"error": "invalid_radius", "detail": "radius_m must be positive."}

        if bbox and len(bbox) != 4:
            return {
                "error": "invalid_bbox",
                "detail": "bbox must have exactly 4 values: [min_lon, min_lat, max_lon, max_lat].",
            }

        if sort_direction not in ("asc", "desc"):
            return {
                "error": "invalid_sort_direction",
                "detail": "sort_direction must be 'asc' or 'desc'.",
            }

        if sort_field and sort_field not in _ALLOWED_SORT_FIELDS:
            return {
                "error": "invalid_sort_field",
                "detail": f"sort_field must be one of: {sorted(_ALLOWED_SORT_FIELDS)}",
            }

        # --- Geocode address if needed ---
        if address:
            try:
                geo = await geocode_address(address)
                resolved_lat = geo["latitude"]
                resolved_lon = geo["longitude"]
            except GeocodingError as exc:
                return {"error": "geocoding_failed", "detail": str(exc), "address": address}

        # --- Build bbox for radius search ---
        if radius_m and resolved_lat is not None and resolved_lon is not None:
            min_lon, min_lat, max_lon, max_lat = radius_to_bbox(resolved_lat, resolved_lon, radius_m)
            params["bbox"] = f"{min_lon},{min_lat},{max_lon},{max_lat}"
        elif bbox:
            params["bbox"] = ",".join(str(v) for v in bbox)

        # --- CQL filters ---
        cql_parts: list[str] = []

        if municipality_code:
            cql_parts.append(f"kommunkod='{municipality_code}'")
        if municipality_name:
            cql_parts.append(f"kommunnamn ILIKE '%{municipality_name}%'")
        if well_use_code:
            cql_parts.append(f"anvandningskod='{well_use_code.upper()}'")
        if min_total_depth is not None:
            cql_parts.append(f"totaldjup>={min_total_depth}")
        if max_total_depth is not None:
            cql_parts.append(f"totaldjup<={max_total_depth}")
        if min_capacity is not None:
            cql_parts.append(f"kapacitet>={min_capacity}")
        if max_capacity is not None:
            cql_parts.append(f"kapacitet<={max_capacity}")
        if position_quality_code:
            cql_parts.append(f"positionskvalitetskod='{position_quality_code}'")
        if drilling_date_from:
            cql_parts.append(f"borrningsstart>='{drilling_date_from}'")
        if drilling_date_to:
            cql_parts.append(f"borrningsslut<='{drilling_date_to}'")

        if cql_parts:
            params["filter"] = " AND ".join(cql_parts)
            params["filter-lang"] = "cql2-text"

        if sort_field:
            params["sortby"] = f"{'+' if sort_direction == 'asc' else '-'}{sort_field}"

        params["limit"] = page_size
        params["offset"] = offset

    # --- Query SGU ---
    client = get_sgu_client()
    try:
        features, meta = await client.get_items(
            _COLLECTION,
            params,
            max_records=page_size,
        )
    except SGUError as exc:
        return {"error": "sgu_unavailable", "detail": str(exc)}

    # --- Exact radius filtering (post-query) ---
    warnings: list[str] = []
    if radius and resolved_lat is not None and resolved_lon is not None:
        filtered = []
        for f in features:
            coord = feature_coordinates(f)
            if coord is None:
                continue
            dist = haversine_distance_m(resolved_lat, resolved_lon, coord[0], coord[1])
            if dist <= radius:
                f = dict(f)
                f["_distance_m"] = round(dist, 1)
                filtered.append(f)
        features = sorted(filtered, key=lambda f: f.get("_distance_m", 0))
        if len(features) < len(features):
            warnings.append("Some features were outside the requested radius and were excluded.")

    # --- Enrich features ---
    enriched_records = []
    for f in features:
        enriched_records.append({
            "feature": f,
            "interpretation": enrich_feature(f),
            "source_collection": _COLLECTION,
            "crs": "EPSG:4326 (WGS84)",
        })

    # --- Continuation token for next page ---
    next_token = None
    number_matched = meta.get("numberMatched")
    has_more = meta.get("_truncated") or _has_next_link(meta.get("links", []))
    if has_more:
        new_state = {
            "params": {**params, "offset": offset + page_size},
            "offset": offset + page_size,
            "lat": resolved_lat,
            "lon": resolved_lon,
            "radius_m": radius,
        }
        next_token = encode_continuation_token(new_state)

    if meta.get("_truncated"):
        warnings.append(
            f"Results were truncated at {settings.max_inline_results} records. "
            "Use the continuation_token to retrieve more."
        )

    return {
        "query_summary": {
            "collection": _COLLECTION,
            "address": address,
            "latitude": resolved_lat,
            "longitude": resolved_lon,
            "radius_m": radius,
            "bbox": bbox,
            "municipality_name": municipality_name,
            "municipality_code": municipality_code,
            "well_use_code": well_use_code,
            "min_total_depth": min_total_depth,
            "max_total_depth": max_total_depth,
            "page_size": page_size,
        },
        "retrieval_timestamp": _now_iso(),
        "count": {
            "returned": len(enriched_records),
            "number_matched": number_matched,
        },
        "crs": "EPSG:4326 (WGS84)",
        "records": enriched_records,
        "continuation_token": next_token,
        "warnings": warnings,
        "data_quality_notes": [
            "Source data is from SGU Brunnsarkivet. Coordinates and measurements "
            "may be incomplete or approximate.",
            "Capacity values are reported values; they do not guarantee sustainable yield.",
        ],
    }


def _has_next_link(links: list[dict]) -> bool:
    return any(link.get("rel") == "next" for link in links)


def _now_iso() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()
