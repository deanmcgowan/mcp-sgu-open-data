"""Tool: resolve_address — geocode a free-text address."""

from __future__ import annotations

from typing import Any

from mcp_sgu.geocoding import GeocodingError, GeocodingNoResultsError, geocode_address


async def resolve_address(
    address: str,
    language: str = "en",
) -> dict[str, Any]:
    """Resolve a free-text address to geographic coordinates.

    Uses the Google Geocoding API.

    Parameters
    ----------
    address:
        Free-text postal address or place name.
    language:
        Preferred response language, e.g. ``"en"`` or ``"sv"``.

    Returns
    -------
    dict with keys:
    - original_address
    - normalized_address
    - latitude
    - longitude
    - address_components
    - location_type
    - provider
    - warnings
    """
    if not address or not address.strip():
        return {
            "error": "invalid_input",
            "detail": "Address must not be empty.",
        }

    try:
        result = await geocode_address(address.strip(), language=language)
        return result
    except GeocodingNoResultsError as exc:
        return {
            "error": "no_results",
            "detail": str(exc),
            "original_address": address,
        }
    except GeocodingError as exc:
        return {
            "error": "geocoding_failed",
            "detail": str(exc),
            "original_address": address,
        }
