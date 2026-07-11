"""Google Geocoding API client."""

from __future__ import annotations

import time
from typing import Any

import httpx

from mcp_sgu.cache import get_address_cache
from mcp_sgu.config import get_settings
from mcp_sgu.logging_config import get_logger, log_upstream_call

logger = get_logger(__name__)

_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class GeocodingError(Exception):
    """Geocoding request failed."""


class GeocodingNoResultsError(GeocodingError):
    """Geocoding returned no results."""


async def geocode_address(
    address: str,
    language: str = "en",
) -> dict[str, Any]:
    """Geocode an address using the Google Geocoding API.

    Returns a dict with:
    - original_address
    - normalized_address
    - latitude
    - longitude
    - address_components
    - location_type
    - provider
    - warnings
    """
    settings = get_settings()
    api_key = settings.google_maps_api_key
    if not api_key:
        raise GeocodingError("GOOGLE_MAPS_API_KEY is not configured")

    # Cache key - do NOT include the API key in cache key
    cache_key = f"geocode:{address.lower().strip()}:{language}"
    cache = get_address_cache()
    cached = await cache.get(cache_key)
    if cached is not None:
        logger.debug("Geocoding cache hit")
        return {**cached, "cache_hit": True}

    params = {
        "address": address,
        "language": language,
        "key": api_key,  # NOT logged
    }

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_GEOCODING_URL, params=params)
        duration_ms = (time.monotonic() - t0) * 1000
        log_upstream_call(logger, "google_geocoding", _GEOCODING_URL, resp.status_code, duration_ms)
        resp.raise_for_status()
    except httpx.TimeoutException as exc:
        raise GeocodingError("Google Geocoding API timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise GeocodingError(
            f"Google Geocoding API returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise GeocodingError(f"Google Geocoding API request failed: {exc}") from exc

    data = resp.json()
    status = data.get("status", "UNKNOWN")

    if status == "ZERO_RESULTS":
        raise GeocodingNoResultsError(f"No geocoding results for: {address!r}")
    if status != "OK":
        raise GeocodingError(f"Geocoding API returned status: {status}")

    results = data.get("results", [])
    if not results:
        raise GeocodingNoResultsError(f"No geocoding results for: {address!r}")

    best = results[0]
    geometry = best.get("geometry", {})
    location = geometry.get("location", {})

    result = {
        "original_address": address,
        "normalized_address": best.get("formatted_address", address),
        "latitude": location.get("lat"),
        "longitude": location.get("lng"),
        "address_components": best.get("address_components", []),
        "location_type": geometry.get("location_type"),
        "place_id": best.get("place_id"),
        "provider": "google_geocoding",
        "cache_hit": False,
        "warnings": [
            "The returned coordinates represent an address point, "
            "not a cadastral parcel (fastighet) boundary. "
            "The actual property boundary may differ significantly.",
        ],
    }

    # Cache for address TTL
    await cache.set(cache_key, result, ttl=600.0)
    return result
