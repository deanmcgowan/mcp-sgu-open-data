"""Tests for radius filtering and coordinate transformations."""

from __future__ import annotations

import pytest


def test_haversine_distance_zero() -> None:
    """Same point should return distance of 0."""
    from mcp_sgu.coordinates import haversine_distance_m

    assert haversine_distance_m(59.33, 18.07, 59.33, 18.07) == pytest.approx(0.0, abs=1e-6)


def test_haversine_distance_known() -> None:
    """Distance between Stockholm and Gothenburg is approximately 400 km."""
    from mcp_sgu.coordinates import haversine_distance_m

    # Stockholm: 59.33°N, 18.07°E
    # Gothenburg: 57.71°N, 11.97°E
    dist = haversine_distance_m(59.33, 18.07, 57.71, 11.97)
    # Expected roughly 400 km
    assert 380_000 < dist < 420_000


def test_radius_to_bbox_contains_point() -> None:
    """Bounding box generated from a radius must contain the center point."""
    from mcp_sgu.coordinates import radius_to_bbox

    lat, lon = 59.33, 18.07
    radius = 5000  # 5 km
    min_lon, min_lat, max_lon, max_lat = radius_to_bbox(lat, lon, radius)

    assert min_lon < lon < max_lon
    assert min_lat < lat < max_lat


def test_radius_to_bbox_covers_radius() -> None:
    """Points at exactly radius_m must be within the bbox."""
    from mcp_sgu.coordinates import radius_to_bbox

    lat, lon = 59.33, 18.07
    radius = 1000  # 1 km
    min_lon, min_lat, max_lon, max_lat = radius_to_bbox(lat, lon, radius)

    # The north point (lat + delta) should be within the bbox
    north_lat = lat + radius / 111_319.0
    assert north_lat < max_lat  # bbox is larger than radius by design


def test_feature_coordinates_point() -> None:
    """feature_coordinates extracts (lat, lon) from a Point feature."""
    from mcp_sgu.coordinates import feature_coordinates

    feature = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [18.07, 59.33]},
        "properties": {},
    }
    coord = feature_coordinates(feature)
    assert coord is not None
    lat, lon = coord
    assert lat == pytest.approx(59.33)
    assert lon == pytest.approx(18.07)


def test_feature_coordinates_no_geometry() -> None:
    """feature_coordinates returns None for features without geometry."""
    from mcp_sgu.coordinates import feature_coordinates

    feature = {"type": "Feature", "geometry": None, "properties": {}}
    assert feature_coordinates(feature) is None


def test_sweref99tm_roundtrip() -> None:
    """SWEREF99TM -> WGS84 -> SWEREF99TM should be lossless."""
    from mcp_sgu.coordinates import sweref99tm_to_wgs84, wgs84_to_sweref99tm

    # Stockholm area in SWEREF99TM
    easting, northing = 674_000.0, 6_580_000.0
    lon, lat = sweref99tm_to_wgs84(easting, northing)
    e2, n2 = wgs84_to_sweref99tm(lon, lat)

    assert e2 == pytest.approx(easting, abs=0.01)
    assert n2 == pytest.approx(northing, abs=0.01)
