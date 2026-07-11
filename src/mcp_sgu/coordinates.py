"""Coordinate transformation utilities."""

from __future__ import annotations

import math
from typing import Any

try:
    from pyproj import Transformer

    _sweref99tm_to_wgs84 = Transformer.from_crs("EPSG:3006", "EPSG:4326", always_xy=True)
    _wgs84_to_sweref99tm = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True)
    _PYPROJ_AVAILABLE = True
except ImportError:
    _PYPROJ_AVAILABLE = False


def sweref99tm_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Convert SWEREF99TM (EPSG:3006) coordinates to WGS84 (lon, lat)."""
    if not _PYPROJ_AVAILABLE:
        raise RuntimeError("pyproj is not available for coordinate transformation")
    lon, lat = _sweref99tm_to_wgs84.transform(easting, northing)
    return float(lon), float(lat)


def wgs84_to_sweref99tm(lon: float, lat: float) -> tuple[float, float]:
    """Convert WGS84 (lon, lat) to SWEREF99TM (EPSG:3006) coordinates."""
    if not _PYPROJ_AVAILABLE:
        raise RuntimeError("pyproj is not available for coordinate transformation")
    easting, northing = _wgs84_to_sweref99tm.transform(lon, lat)
    return float(easting), float(northing)


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance in metres between two points."""
    R = 6_371_000.0  # Earth's mean radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def radius_to_bbox(lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    """Return an approximate bounding box (min_lon, min_lat, max_lon, max_lat)
    that fully encloses a circle of ``radius_m`` metres around (lat, lon).

    The approximation is conservative (the box is slightly larger than needed).
    Exact radius filtering is performed post-query.
    """
    # 1 degree of latitude ≈ 111_319 m; add 1% buffer so bbox is strictly larger
    lat_delta = radius_m / 111_319.0 * 1.01
    # 1 degree of longitude varies with latitude; add 1% buffer
    lon_delta = radius_m / (111_319.0 * math.cos(math.radians(lat))) * 1.01
    return (
        lon - lon_delta,
        lat - lat_delta,
        lon + lon_delta,
        lat + lat_delta,
    )


def feature_coordinates(feature: dict[str, Any]) -> tuple[float, float] | None:
    """Extract (lat, lon) from a GeoJSON feature, or None if not available."""
    geometry = feature.get("geometry")
    if not geometry:
        return None
    geom_type = geometry.get("type", "")
    coords = geometry.get("coordinates")
    if not coords:
        return None
    if geom_type == "Point":
        # GeoJSON: [lon, lat]
        return float(coords[1]), float(coords[0])
    return None
