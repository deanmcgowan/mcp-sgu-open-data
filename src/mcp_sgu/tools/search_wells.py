"""Tool: search the SGU Brunnar collection."""

from __future__ import annotations

import datetime
from typing import Any

from mcp_sgu.coordinates import (
    feature_coordinates,
    haversine_distance_m,
    transform_feature_to_wgs84,
    wgs84_radius_to_sweref_bbox,
)
from mcp_sgu.field_defs import enrich_feature
from mcp_sgu.filters import FilterError, add_filter, build_well_filter
from mcp_sgu.geocoding import GeocodingError, geocode_address
from mcp_sgu.logging_config import set_tool_name
from mcp_sgu.pagination import ContinuationTokenError, decode_continuation_token, encode_continuation_token
from mcp_sgu.sgu_client import SGUError, get_sgu_client

_COLLECTION = "brunnar"
_MAX_RADIUS_M = 100_000
_ALLOWED_SORT_FIELDS = {"brunnsid", "kommunkod", "kommunnamn", "kapacitet", "totaldjup", "borrdatum"}


async def search_wells(
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
    """Search wells using a bounded spatial query and validated SGU filters."""
    set_tool_name("search_wells")
    from mcp_sgu.config import get_settings

    settings = get_settings()
    warnings: list[str] = []
    if continuation_token:
        try:
            state = decode_continuation_token(continuation_token)
            params, resolved_lat, resolved_lon, radius = state["params"], state["lat"], state["lon"], state["radius_m"]
        except (ContinuationTokenError, KeyError) as exc:
            return {"error": "invalid_continuation_token", "detail": str(exc)}
    else:
        error = _validate(address, latitude, longitude, radius_m, bbox, sort_field, sort_direction)
        if error:
            return error
        if address:
            try:
                geocoded = await geocode_address(address)
                latitude, longitude = geocoded["latitude"], geocoded["longitude"]
            except GeocodingError as exc:
                return {"error": "geocoding_failed", "detail": str(exc)}
        resolved_lat, resolved_lon, radius = latitude, longitude, radius_m
        params: dict[str, Any] = {}
        if radius:
            params["bbox"] = ",".join(map(str, wgs84_radius_to_sweref_bbox(resolved_lat, resolved_lon, radius)))
        elif bbox:
            # Caller bbox is WGS84; transform all corners for SGU's native CRS.
            min_lon, min_lat, max_lon, max_lat = bbox
            from mcp_sgu.coordinates import wgs84_to_sweref99tm

            points = [
                wgs84_to_sweref99tm(x, y)
                for x, y in ((min_lon, min_lat), (min_lon, max_lat), (max_lon, min_lat), (max_lon, max_lat))
            ]
            eastings, northings = zip(*points, strict=True)
            params["bbox"] = f"{min(eastings)},{min(northings)},{max(eastings)},{max(northings)}"
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
        if sort_field:
            params["sortby"] = f"{'+' if sort_direction == 'asc' else '-'}{sort_field}"
        if has_layers is not None:
            warnings.append(
                "has_layers is not supported because SGU does not expose layer presence as a well queryable."
            )
        params["limit"] = min(max(1, page_size), settings.max_inline_results)
    try:
        features, meta = await get_sgu_client().get_items(_COLLECTION, params, max_records=settings.max_inline_results)
    except SGUError as exc:
        return {"error": "sgu_unavailable", "detail": str(exc)}
    original_count = len(features)
    if radius and resolved_lat is not None and resolved_lon is not None:
        filtered: list[dict[str, Any]] = []
        for feature in features:
            if (coordinate := feature_coordinates(feature)) and haversine_distance_m(
                resolved_lat, resolved_lon, *coordinate
            ) <= radius:
                copied = dict(feature)
                copied["_distance_m"] = round(haversine_distance_m(resolved_lat, resolved_lon, *coordinate), 1)
                filtered.append(copied)
        features = sorted(filtered, key=lambda item: item["_distance_m"])
        if len(features) < original_count:
            warnings.append("Some features were outside the requested radius and were excluded.")
    records = [
        {
            "feature": transform_feature_to_wgs84(feature),
            "interpretation": enrich_feature(feature),
            "source_collection": _COLLECTION,
            "source_crs": "EPSG:3006 (SWEREF 99 TM)",
            "output_crs": "EPSG:4326 (WGS84)",
            "source_coordinates": {
                "n": (feature.get("properties") or {}).get("n"),
                "e": (feature.get("properties") or {}).get("e"),
            },
        }
        for feature in features
    ]
    next_link = next((link.get("href") for link in meta.get("links", []) if link.get("rel") == "next"), None)
    next_token = None
    if next_link:
        next_token = encode_continuation_token(
            {"params": {"_next_url": next_link}, "lat": resolved_lat, "lon": resolved_lon, "radius_m": radius}
        )
    if meta.get("_truncated"):
        warnings.append("Inline result limit reached; results are incomplete.")
    return {
        "query_summary": {
            "collection": _COLLECTION,
            "latitude": resolved_lat,
            "longitude": resolved_lon,
            "radius_m": radius,
            "bbox": bbox,
        },
        "retrieval_timestamp": datetime.datetime.now(tz=datetime.UTC).isoformat(),
        "count": {"returned": len(records), "number_matched": meta.get("numberMatched")},
        "source_crs": "EPSG:3006 (SWEREF 99 TM)",
        "output_crs": "EPSG:4326 (WGS84)",
        "records": records,
        "continuation_token": next_token,
        "warnings": warnings,
        "complete": not bool(next_link or meta.get("_truncated")),
    }


def _validate(
    address: str | None,
    latitude: float | None,
    longitude: float | None,
    radius: float | None,
    bbox: list[float] | None,
    sort: str | None,
    direction: str,
) -> dict[str, str] | None:
    if address and (latitude is not None or longitude is not None):
        return {"error": "conflicting_inputs", "detail": "Provide address or latitude/longitude, not both."}
    if (latitude is None) != (longitude is None):
        return {"error": "invalid_coordinates", "detail": "latitude and longitude must be supplied together."}
    if address and radius is None:
        return {"error": "missing_radius", "detail": "address requires radius_m to produce a bounded query."}
    if radius is not None and (radius <= 0 or radius > _MAX_RADIUS_M or latitude is None):
        return {"error": "invalid_radius", "detail": f"radius_m must be 1..{_MAX_RADIUS_M} and requires coordinates."}
    if bbox and (
        len(bbox) != 4
        or bbox[0] >= bbox[2]
        or bbox[1] >= bbox[3]
        or not (-180 <= bbox[0] <= 180 and -180 <= bbox[2] <= 180 and -90 <= bbox[1] <= 90 and -90 <= bbox[3] <= 90)
    ):
        return {
            "error": "invalid_bbox",
            "detail": "bbox must be valid [min_lon, min_lat, max_lon, max_lat] WGS84 coordinates.",
        }
    if sort and sort not in _ALLOWED_SORT_FIELDS:
        return {"error": "invalid_sort_field", "detail": f"sort_field must be one of {sorted(_ALLOWED_SORT_FIELDS)}"}
    if direction not in {"asc", "desc"}:
        return {"error": "invalid_sort_direction", "detail": "sort_direction must be asc or desc."}
    return None
