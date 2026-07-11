"""Tool: create_export — create a filtered export from search_wells."""

from __future__ import annotations

import datetime
from typing import Any

from mcp_sgu.coordinates import (
    feature_coordinates,
    haversine_distance_m,
    wgs84_radius_to_sweref_bbox,
)
from mcp_sgu.exports import create_export as _create_export
from mcp_sgu.filters import FilterError, add_filter, build_well_filter
from mcp_sgu.geocoding import GeocodingError, geocode_address
from mcp_sgu.logging_config import get_logger, set_tool_name
from mcp_sgu.sgu_client import SGUError, get_sgu_client

logger = get_logger(__name__)

_COLLECTION = "brunnar"


async def create_export(
    fmt: str = "csv",
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
) -> dict[str, Any]:
    """Create a downloadable export of well data.

    Parameters
    ----------
    fmt:
        Export format: ``"csv"`` or ``"geojson"``.
    address, latitude, longitude, radius_m, bbox:
        Spatial constraints (same as search_wells).
    municipality_name, municipality_code, well_use_code, ...:
        Attribute filters (same as search_wells).

    Returns metadata including a download URL.
    The download URL is protected by bearer authentication.
    """
    set_tool_name("create_export")

    from mcp_sgu.config import get_settings

    settings = get_settings()

    if fmt not in ("csv", "geojson"):
        return {
            "error": "invalid_format",
            "detail": "fmt must be 'csv' or 'geojson'.",
        }

    if address and (latitude is not None or longitude is not None):
        return {
            "error": "conflicting_inputs",
            "detail": "Provide either 'address' or 'latitude'/'longitude', not both.",
        }
    if (latitude is None) != (longitude is None):
        return {"error": "invalid_coordinates", "detail": "latitude and longitude must be supplied together."}
    if address and radius_m is None:
        return {"error": "missing_radius", "detail": "address requires radius_m."}

    resolved_lat = latitude
    resolved_lon = longitude

    if address:
        try:
            geo = await geocode_address(address)
            resolved_lat = geo["latitude"]
            resolved_lon = geo["longitude"]
        except GeocodingError as exc:
            return {"error": "geocoding_failed", "detail": str(exc)}

    params: dict[str, Any] = {}

    if radius_m and resolved_lat is not None and resolved_lon is not None:
        params["bbox"] = ",".join(map(str, wgs84_radius_to_sweref_bbox(resolved_lat, resolved_lon, radius_m)))
    elif bbox:
        params["bbox"] = ",".join(str(v) for v in bbox)

    try:
        add_filter(
            params,
            build_well_filter(
                municipality_code=municipality_code,
                municipality_name=municipality_name,
                well_use_code=well_use_code,
                min_total_depth=min_total_depth,
                max_total_depth=max_total_depth,
                min_capacity=min_capacity,
                max_capacity=max_capacity,
                position_quality_code=position_quality_code,
                drilling_date_from=drilling_date_from,
                drilling_date_to=drilling_date_to,
            ),
        )
    except FilterError as exc:
        return {"error": "invalid_filter", "detail": str(exc)}

    params["limit"] = settings.max_export_records

    client = get_sgu_client()
    try:
        features, meta = await client.get_items(_COLLECTION, params, max_records=settings.max_export_records)
    except SGUError as exc:
        return {"error": "sgu_unavailable", "detail": str(exc)}

    # Exact radius filtering
    if radius_m and resolved_lat is not None and resolved_lon is not None:
        features = [
            f
            for f in features
            if (coord := feature_coordinates(f)) is not None
            and haversine_distance_m(resolved_lat, resolved_lon, coord[0], coord[1]) <= radius_m
        ]

    if len(features) > settings.max_export_records:
        return {
            "error": "export_too_large",
            "detail": (
                f"The query would produce {len(features)} records, exceeding the "
                f"MAX_EXPORT_RECORDS limit of {settings.max_export_records}. "
                "Add more filters to reduce the result set."
            ),
        }

    query_summary = {
        "collection": _COLLECTION,
        "format": fmt,
        "address": address,
        "latitude": resolved_lat,
        "longitude": resolved_lon,
        "radius_m": radius_m,
        "bbox": bbox,
        "municipality_code": municipality_code,
        "municipality_name": municipality_name,
        "well_use_code": well_use_code,
    }

    try:
        metadata = await _create_export(features, fmt, query_summary)
    except ValueError as exc:
        return {"error": "export_failed", "detail": str(exc)}

    warnings: list[str] = []
    if meta.get("_truncated"):
        warnings.append(f"Export was truncated at {settings.max_export_records} records. Results may be incomplete.")

    return {
        **metadata,
        "warnings": warnings,
        "source": {
            "collection": _COLLECTION,
            "retrieval_timestamp": _now_iso(),
        },
    }


def _now_iso() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()
