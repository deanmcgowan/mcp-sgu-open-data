"""Tests for Google geocoding client."""

from __future__ import annotations

import re

import pytest
from pytest_httpx import HTTPXMock

GEOCODING_URL_PATTERN = re.compile(r"https://maps\.googleapis\.com/maps/api/geocode/json.*")


@pytest.mark.asyncio
async def test_geocode_success(httpx_mock: HTTPXMock) -> None:
    """Successful geocoding returns normalized address and coordinates."""
    httpx_mock.add_response(
        url=GEOCODING_URL_PATTERN,
        json={
            "status": "OK",
            "results": [
                {
                    "formatted_address": "Kungsgatan 10, 111 35 Stockholm, Sweden",
                    "geometry": {
                        "location": {"lat": 59.3356, "lng": 18.0633},
                        "location_type": "ROOFTOP",
                    },
                    "place_id": "ChIJ123",
                    "address_components": [
                        {"long_name": "10", "short_name": "10", "types": ["street_number"]},
                        {"long_name": "Kungsgatan", "short_name": "Kungsgatan", "types": ["route"]},
                    ],
                }
            ],
        },
        status_code=200,
    )

    from mcp_sgu.geocoding import geocode_address

    result = await geocode_address("Kungsgatan 10, Stockholm", language="en")

    assert result["latitude"] == pytest.approx(59.3356)
    assert result["longitude"] == pytest.approx(18.0633)
    assert result["normalized_address"] == "Kungsgatan 10, 111 35 Stockholm, Sweden"
    assert result["location_type"] == "ROOFTOP"
    assert result["provider"] == "google_geocoding"
    assert len(result["warnings"]) >= 1
    # Warnings must mention parcel boundary
    assert "boundary" in " ".join(result["warnings"]).lower()


@pytest.mark.asyncio
async def test_geocode_zero_results(httpx_mock: HTTPXMock) -> None:
    """ZERO_RESULTS status raises GeocodingNoResultsError."""
    httpx_mock.add_response(
        url=GEOCODING_URL_PATTERN,
        json={"status": "ZERO_RESULTS", "results": []},
        status_code=200,
    )

    from mcp_sgu.geocoding import GeocodingNoResultsError, geocode_address

    with pytest.raises(GeocodingNoResultsError):
        await geocode_address("Nonexistent Place XYZ", language="en")


@pytest.mark.asyncio
async def test_geocode_api_error_status(httpx_mock: HTTPXMock) -> None:
    """Error API status raises GeocodingError."""
    httpx_mock.add_response(
        url=GEOCODING_URL_PATTERN,
        json={"status": "REQUEST_DENIED", "error_message": "API key invalid"},
        status_code=200,
    )

    from mcp_sgu.geocoding import GeocodingError, geocode_address

    with pytest.raises(GeocodingError, match="REQUEST_DENIED"):
        await geocode_address("Stockholm", language="en")


@pytest.mark.asyncio
async def test_geocode_no_api_key() -> None:
    """Missing API key raises GeocodingError before making any request."""
    import os

    import mcp_sgu.config as cfg_module

    cfg_module._settings = None
    original = os.environ.get("GOOGLE_MAPS_API_KEY")
    os.environ["GOOGLE_MAPS_API_KEY"] = ""
    cfg_module._settings = None

    try:
        from mcp_sgu.geocoding import GeocodingError, geocode_address

        with pytest.raises(GeocodingError, match="GOOGLE_MAPS_API_KEY"):
            await geocode_address("Stockholm")
    finally:
        if original is not None:
            os.environ["GOOGLE_MAPS_API_KEY"] = original
        else:
            del os.environ["GOOGLE_MAPS_API_KEY"]
        cfg_module._settings = None


@pytest.mark.asyncio
async def test_geocode_result_cached(httpx_mock: HTTPXMock) -> None:
    """Second geocoding call for same address uses cache."""
    httpx_mock.add_response(
        url=GEOCODING_URL_PATTERN,
        json={
            "status": "OK",
            "results": [
                {
                    "formatted_address": "Stockholm, Sweden",
                    "geometry": {
                        "location": {"lat": 59.33, "lng": 18.07},
                        "location_type": "APPROXIMATE",
                    },
                    "address_components": [],
                }
            ],
        },
        status_code=200,
    )

    from mcp_sgu.cache import get_address_cache
    from mcp_sgu.geocoding import geocode_address

    # Clear cache first
    await (get_address_cache()).clear()

    result1 = await geocode_address("Stockholm", language="en")
    assert result1["cache_hit"] is False

    # Second call (no extra mock needed — should use cache)
    result2 = await geocode_address("Stockholm", language="en")
    assert result2["cache_hit"] is True
    assert result2["latitude"] == result1["latitude"]
