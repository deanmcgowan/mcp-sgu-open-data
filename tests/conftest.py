"""pytest configuration and shared fixtures."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest

# Set test environment before importing the app
os.environ.setdefault("MCP_BEARER_TOKEN", "test-token-12345")
os.environ.setdefault("GOOGLE_MAPS_API_KEY", "test-google-key")
os.environ.setdefault("SGU_BASE_URL", "https://api.sgu.se/oppnadata/brunnar/ogc/features/v1")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("MAX_INLINE_RESULTS", "100")
os.environ.setdefault("MAX_EXPORT_RECORDS", "1000")


@pytest.fixture(autouse=True)
def reset_settings_singleton() -> Generator[None, None, None]:
    """Reset the settings singleton between tests."""
    import mcp_sgu.config as cfg_module

    original = cfg_module._settings
    cfg_module._settings = None
    yield
    cfg_module._settings = original


@pytest.fixture(autouse=True)
def reset_sgu_client() -> Generator[None, None, None]:
    """Reset the SGU client singleton between tests."""
    import mcp_sgu.sgu_client as sgu_module

    original = sgu_module._client
    sgu_module._client = None
    yield
    sgu_module._client = original


@pytest.fixture(autouse=True)
def reset_caches() -> Generator[None, None, None]:
    """Reset all in-memory caches between tests."""
    import mcp_sgu.cache as cache_module

    cache_module._metadata_cache = None
    cache_module._address_cache = None
    cache_module._results_cache = None
    yield
    cache_module._metadata_cache = None
    cache_module._address_cache = None
    cache_module._results_cache = None


@pytest.fixture
def test_token() -> str:
    return "test-token-12345"


@pytest.fixture
def auth_headers(test_token: str) -> dict[str, str]:
    scheme = "Bearer"
    return {"Authorization": f"{scheme} {test_token}"}


@pytest.fixture
def app():
    """Create a fresh Starlette test application."""
    from mcp_sgu.app import create_app

    return create_app()


@pytest.fixture
def sample_well_feature() -> dict:
    """A sample SGU brunnar GeoJSON feature for testing."""
    return {
        "type": "Feature",
        "id": "brunnar.123",
        "geometry": {
            "type": "Point",
            "coordinates": [674032.357, 6580821.991],
        },
        "properties": {
            "brunnsid": 123,
            "obsplatsid": "OBS-456",
            "kommunkod": "0180",
            "kommunnamn": "Stockholm",
            "n": 6580821.991,
            "e": 674032.357,
            "kapacitet": 3000.0,
            "totaldjup": 80.5,
            "grundvattenniva": 5.2,
            "borrdatum": "2010-06-15",
            "anvandning_kod": "HUS",
            "anvandning": "Vattenförsörjning",
            "posvardering_kod": "0",
            "posvardering": "Maxfel <100 m",
        },
    }


@pytest.fixture
def sample_layer_feature() -> dict:
    """A sample SGU brunnar-lager GeoJSON feature for testing."""
    return {
        "type": "Feature",
        "id": "brunnar-lager.456",
        "geometry": None,
        "properties": {
            "brunnsid": 123,
            "obsplatsid": "OBS-456",
            "lagernr": 1,
            "djup_fran": 0.0,
            "djup_till": 5.0,
            "jordart_bergart": "Morän",
            "lageranmarkning": "Löst material",
        },
    }


@pytest.fixture
def sample_feature_collection(sample_well_feature: dict) -> dict:
    """A sample OGC features response."""
    return {
        "type": "FeatureCollection",
        "numberMatched": 1,
        "numberReturned": 1,
        "features": [sample_well_feature],
        "links": [],
    }
