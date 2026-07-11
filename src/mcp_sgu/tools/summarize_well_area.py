"""Tool: summarize_well_area — aggregate well statistics for a spatial area."""

from __future__ import annotations

import datetime
import statistics
from collections import Counter
from typing import Any

from mcp_sgu.coordinates import (
    feature_coordinates,
    haversine_distance_m,
    radius_to_bbox,
)
from mcp_sgu.geocoding import GeocodingError, geocode_address
from mcp_sgu.logging_config import get_logger, set_tool_name
from mcp_sgu.sgu_client import SGUError, get_sgu_client

logger = get_logger(__name__)

_COLLECTION = "brunnar"
_MAX_SCAN = 5000


async def summarize_well_area(
    address: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_m: float | None = None,
    bbox: list[float] | None = None,
    municipality_code: str | None = None,
    municipality_name: str | None = None,
) -> dict[str, Any]:
    """Return aggregate statistics for wells in a constrained area.

    A spatial constraint (address+radius, lat/lon+radius, bbox, or municipality)
    is required.

    Parameters
    ----------
    address:
        Free-text address (will be geocoded).
    latitude, longitude:
        Explicit coordinates (WGS84).
    radius_m:
        Search radius in metres.
    bbox:
        Bounding box [min_lon, min_lat, max_lon, max_lat].
    municipality_code:
        Filter by SCB municipality code.
    municipality_name:
        Filter by municipality name.
    """
    set_tool_name("summarize_well_area")

    # Require at least one spatial constraint
    has_spatial = any([
        address,
        (latitude is not None and longitude is not None and radius_m),
        bbox,
        municipality_code,
        municipality_name,
    ])
    if not has_spatial:
        return {
            "error": "missing_spatial_constraint",
            "detail": (
                "A spatial constraint is required. Provide one of: address+radius_m, "
                "latitude+longitude+radius_m, bbox, municipality_code, or municipality_name."
            ),
        }

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
        min_lon, min_lat, max_lon, max_lat = radius_to_bbox(resolved_lat, resolved_lon, radius_m)
        params["bbox"] = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    elif bbox:
        params["bbox"] = ",".join(str(v) for v in bbox)

    cql_parts: list[str] = []
    if municipality_code:
        cql_parts.append(f"kommunkod='{municipality_code}'")
    if municipality_name:
        cql_parts.append(f"kommunnamn ILIKE '%{municipality_name}%'")
    if cql_parts:
        params["filter"] = " AND ".join(cql_parts)
        params["filter-lang"] = "cql2-text"

    params["limit"] = _MAX_SCAN

    client = get_sgu_client()
    try:
        features, meta = await client.get_items(
            _COLLECTION, params, max_records=_MAX_SCAN
        )
    except SGUError as exc:
        return {"error": "sgu_unavailable", "detail": str(exc)}

    # Exact radius filtering
    if radius_m and resolved_lat is not None and resolved_lon is not None:
        features = [
            f for f in features
            if (coord := feature_coordinates(f)) is not None
            and haversine_distance_m(resolved_lat, resolved_lon, coord[0], coord[1]) <= radius_m
        ]

    total = len(features)
    if total == 0:
        return {
            "query_summary": {"address": address, "radius_m": radius_m, "bbox": bbox},
            "retrieval_timestamp": _now_iso(),
            "total_well_count": 0,
            "warnings": ["No wells found matching the given constraints."],
        }

    # Aggregate
    use_counter: Counter = Counter()
    pos_quality_counter: Counter = Counter()
    depths: list[float] = []
    capacities: list[float] = []
    wells_with_layers = 0
    wells_with_water_level = 0
    missing_depth = 0
    missing_capacity = 0
    missing_position = 0

    for f in features:
        props = f.get("properties") or {}

        use_code = props.get("anvandningskod") or "unknown"
        use_counter[use_code] += 1

        pq = props.get("positionskvalitetskod") or "unknown"
        pos_quality_counter[pq] += 1

        depth = props.get("totaldjup")
        if depth is not None:
            depths.append(float(depth))
        else:
            missing_depth += 1

        cap = props.get("kapacitet")
        if cap is not None:
            capacities.append(float(cap))
        else:
            missing_capacity += 1

        if props.get("vattenniva") is not None:
            wells_with_water_level += 1

        if f.get("_has_layers"):
            wells_with_layers += 1

        geom = f.get("geometry")
        if not geom:
            missing_position += 1

    def _stats(values: list[float]) -> dict[str, Any]:
        if not values:
            return {"count": 0}
        return {
            "count": len(values),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "mean": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2),
        }

    warnings: list[str] = []
    if meta.get("_truncated"):
        warnings.append(
            f"Statistics are based on a maximum of {_MAX_SCAN} records; "
            "the actual area may contain more wells."
        )

    return {
        "query_summary": {
            "address": address,
            "latitude": resolved_lat,
            "longitude": resolved_lon,
            "radius_m": radius_m,
            "bbox": bbox,
            "municipality_code": municipality_code,
            "municipality_name": municipality_name,
        },
        "retrieval_timestamp": _now_iso(),
        "total_well_count": total,
        "well_use_distribution": dict(use_counter.most_common()),
        "position_quality_distribution": dict(pos_quality_counter.most_common()),
        "depth_statistics_m": _stats(depths),
        "capacity_statistics_l_h": _stats(capacities),
        "wells_with_water_level_data": wells_with_water_level,
        "wells_with_layer_data": wells_with_layers,
        "missing_values": {
            "depth": missing_depth,
            "capacity": missing_capacity,
            "position": missing_position,
        },
        "warnings": warnings,
        "data_quality_notes": [
            "Capacity values are reported measurements; they do not represent guaranteed yield.",
            "Wells with missing coordinates are counted but excluded from spatial analyses.",
        ],
    }


def _now_iso() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()
