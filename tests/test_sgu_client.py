"""Tests for SGU client: metadata parsing and feature parsing."""

from __future__ import annotations

import re

import httpx
import pytest
from pytest_httpx import HTTPXMock


@pytest.fixture
def sgu_base_url() -> str:
    return "https://api.sgu.se/oppnadata/brunnar/ogc/features/v1"


def sgu_url(sgu_base_url: str, path: str = "") -> re.Pattern:
    """Return a regex that matches the SGU URL with optional query params."""
    base = re.escape(sgu_base_url + path)
    return re.compile(rf"^{base}(\?.*)?$")


@pytest.fixture
def landing_page_response() -> dict:
    return {
        "title": "SGU Brunnar OGC API",
        "description": "SGU well data",
        "links": [
            {"rel": "self", "href": "https://api.sgu.se/oppnadata/brunnar/ogc/features/v1"},
        ],
    }


@pytest.fixture
def collections_response() -> dict:
    return {
        "collections": [
            {
                "id": "brunnar",
                "title": "Brunnar",
                "description": "Well records",
                "links": [],
                "extent": {
                    "spatial": {"bbox": [[10.0, 55.0, 25.0, 70.0]]},
                },
            },
            {
                "id": "brunnar-lager",
                "title": "Brunnar - Lager",
                "description": "Geological layers",
                "links": [],
            },
        ]
    }


@pytest.fixture
def features_response(sample_feature_collection) -> dict:
    return sample_feature_collection


@pytest.mark.asyncio
async def test_get_landing_page(httpx_mock: HTTPXMock, sgu_base_url, landing_page_response) -> None:
    """SGU client fetches and returns the landing page."""
    httpx_mock.add_response(
        url=sgu_url(sgu_base_url),
        json=landing_page_response,
        status_code=200,
    )
    from mcp_sgu.sgu_client import SGUClient

    client = SGUClient(base_url=sgu_base_url)
    result = await client.get_landing_page()
    assert result["title"] == "SGU Brunnar OGC API"
    await client.close()


@pytest.mark.asyncio
async def test_get_collections(httpx_mock: HTTPXMock, sgu_base_url, collections_response) -> None:
    """SGU client fetches collections."""
    httpx_mock.add_response(
        url=sgu_url(sgu_base_url, "/collections"),
        json=collections_response,
        status_code=200,
    )
    from mcp_sgu.sgu_client import SGUClient

    client = SGUClient(base_url=sgu_base_url)
    result = await client.get_collections()
    collections = result["collections"]
    assert len(collections) == 2
    ids = [c["id"] for c in collections]
    assert "brunnar" in ids
    assert "brunnar-lager" in ids
    await client.close()


@pytest.mark.asyncio
async def test_get_items_basic(
    httpx_mock: HTTPXMock, sgu_base_url, features_response
) -> None:
    """SGU client fetches items from a collection."""
    httpx_mock.add_response(
        url=sgu_url(sgu_base_url, "/collections/brunnar/items"),
        json=features_response,
        status_code=200,
    )
    from mcp_sgu.sgu_client import SGUClient

    client = SGUClient(base_url=sgu_base_url)
    features, meta = await client.get_items("brunnar", {"limit": 10})
    assert len(features) == 1
    assert features[0]["properties"]["brunnsid"] == 123
    await client.close()


@pytest.mark.asyncio
async def test_get_items_pagination(
    httpx_mock: HTTPXMock, sgu_base_url, sample_well_feature
) -> None:
    """SGU client follows next links for pagination."""
    page1 = {
        "type": "FeatureCollection",
        "numberMatched": 2,
        "numberReturned": 1,
        "features": [sample_well_feature],
        "links": [
            {
                "rel": "next",
                "href": f"{sgu_base_url}/collections/brunnar/items?offset=1&limit=1",
            }
        ],
    }
    well2 = {**sample_well_feature, "id": "brunnar.456", "properties": {**sample_well_feature["properties"], "brunnsid": 456}}
    page2 = {
        "type": "FeatureCollection",
        "numberMatched": 2,
        "numberReturned": 1,
        "features": [well2],
        "links": [],
    }

    httpx_mock.add_response(
        url=sgu_url(sgu_base_url, "/collections/brunnar/items"),
        json=page1,
        status_code=200,
    )
    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(sgu_base_url)}/collections/brunnar/items\?offset=1"),
        json=page2,
        status_code=200,
    )

    from mcp_sgu.sgu_client import SGUClient

    client = SGUClient(base_url=sgu_base_url)
    features, meta = await client.get_items("brunnar", {"limit": 1}, max_records=10)
    assert len(features) == 2
    brunns_ids = {f["properties"]["brunnsid"] for f in features}
    assert brunns_ids == {123, 456}
    await client.close()


@pytest.mark.asyncio
async def test_get_items_deduplication(
    httpx_mock: HTTPXMock, sgu_base_url, sample_well_feature
) -> None:
    """SGU client deduplicates repeated features."""
    page1 = {
        "type": "FeatureCollection",
        "numberMatched": 1,
        "numberReturned": 1,
        "features": [sample_well_feature],
        "links": [
            {
                "rel": "next",
                "href": f"{sgu_base_url}/collections/brunnar/items?page=2",
            }
        ],
    }
    # Page 2 returns the same feature
    page2 = {
        "type": "FeatureCollection",
        "numberMatched": 1,
        "numberReturned": 1,
        "features": [sample_well_feature],
        "links": [],
    }

    httpx_mock.add_response(
        url=sgu_url(sgu_base_url, "/collections/brunnar/items"),
        json=page1,
        status_code=200,
    )
    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(sgu_base_url)}/collections/brunnar/items\?page=2"),
        json=page2,
        status_code=200,
    )

    from mcp_sgu.sgu_client import SGUClient

    client = SGUClient(base_url=sgu_base_url)
    features, _ = await client.get_items("brunnar", {"limit": 10}, max_records=10)
    # Duplicate should be removed
    assert len(features) == 1
    await client.close()


@pytest.mark.asyncio
async def test_get_items_max_records_enforced(
    httpx_mock: HTTPXMock, sgu_base_url, sample_well_feature
) -> None:
    """SGU client respects max_records limit."""
    features_list = [
        {**sample_well_feature, "id": f"brunnar.{i}", "properties": {**sample_well_feature["properties"], "brunnsid": i}}
        for i in range(1, 11)
    ]
    response = {
        "type": "FeatureCollection",
        "numberMatched": 100,
        "numberReturned": 10,
        "features": features_list,
        "links": [],
    }
    httpx_mock.add_response(
        url=sgu_url(sgu_base_url, "/collections/brunnar/items"),
        json=response,
        status_code=200,
    )
    from mcp_sgu.sgu_client import SGUClient

    client = SGUClient(base_url=sgu_base_url)
    features, _ = await client.get_items("brunnar", {}, max_records=5)
    assert len(features) <= 5
    await client.close()


@pytest.mark.asyncio
async def test_sgu_timeout_raises(httpx_mock: HTTPXMock, sgu_base_url) -> None:
    """SGU client raises SGUTimeoutError on timeout."""
    httpx_mock.add_exception(httpx.TimeoutException("timeout"), is_reusable=True)

    from mcp_sgu.sgu_client import SGUClient, SGUTimeoutError

    client = SGUClient(base_url=sgu_base_url)
    with pytest.raises(SGUTimeoutError):
        await client.get_landing_page()
    await client.close()
