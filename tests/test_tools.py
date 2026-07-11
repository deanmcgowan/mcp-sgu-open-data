"""Tests for search_wells and get_well tools with mocked SGU client."""

from __future__ import annotations

import re

import pytest
from pytest_httpx import HTTPXMock


@pytest.fixture
def sgu_base_url() -> str:
    return "https://api.sgu.se/oppnadata/brunnar/ogc/features/v1"


def sgu_url(sgu_base_url: str, path: str = "") -> re.Pattern:
    base = re.escape(sgu_base_url + path)
    return re.compile(rf"^{base}(\?.*)?$")


@pytest.mark.asyncio
async def test_search_wells_basic(
    httpx_mock: HTTPXMock, sgu_base_url, sample_feature_collection
) -> None:
    """search_wells returns records with interpretation."""
    httpx_mock.add_response(
        url=sgu_url(sgu_base_url, "/collections/brunnar/items"),
        json=sample_feature_collection,
        status_code=200,
    )

    import mcp_sgu.sgu_client as sgu_mod
    from mcp_sgu.sgu_client import SGUClient

    sgu_mod._client = SGUClient(base_url=sgu_base_url)

    from mcp_sgu.tools.search_wells import search_wells

    result = await search_wells(municipality_code="0180", page_size=10)

    assert "error" not in result
    assert "records" in result
    assert len(result["records"]) == 1
    record = result["records"][0]
    assert "feature" in record
    assert "interpretation" in record
    assert record["feature"]["properties"]["brunnsid"] == 123
    assert result["crs"] == "EPSG:4326 (WGS84)"


@pytest.mark.asyncio
async def test_search_wells_conflicting_inputs() -> None:
    """search_wells rejects address + lat/lon combination."""
    from mcp_sgu.tools.search_wells import search_wells

    result = await search_wells(
        address="Stockholm",
        latitude=59.33,
        longitude=18.07,
    )
    assert result["error"] == "conflicting_inputs"


@pytest.mark.asyncio
async def test_search_wells_invalid_bbox() -> None:
    """search_wells rejects invalid bbox."""
    from mcp_sgu.tools.search_wells import search_wells

    result = await search_wells(bbox=[1.0, 2.0, 3.0])  # Only 3 values
    assert result["error"] == "invalid_bbox"


@pytest.mark.asyncio
async def test_search_wells_invalid_sort_direction() -> None:
    """search_wells rejects invalid sort direction."""
    from mcp_sgu.tools.search_wells import search_wells

    result = await search_wells(sort_direction="random")
    assert result["error"] == "invalid_sort_direction"


@pytest.mark.asyncio
async def test_search_wells_radius_filter(
    httpx_mock: HTTPXMock, sgu_base_url, sample_well_feature
) -> None:
    """search_wells with radius filters out features outside the radius."""
    response = {
        "type": "FeatureCollection",
        "numberMatched": 1,
        "numberReturned": 1,
        "features": [sample_well_feature],
        "links": [],
    }
    httpx_mock.add_response(
        url=sgu_url(sgu_base_url, "/collections/brunnar/items"),
        json=response,
        status_code=200,
    )

    import mcp_sgu.sgu_client as sgu_mod
    from mcp_sgu.sgu_client import SGUClient

    sgu_mod._client = SGUClient(base_url=sgu_base_url)

    from mcp_sgu.tools.search_wells import search_wells

    # Feature is at (59.3293, 18.0686); search at same spot with 1000m radius
    result = await search_wells(
        latitude=59.3293,
        longitude=18.0686,
        radius_m=1000,
        page_size=10,
    )
    assert "error" not in result
    # Feature should be within radius (distance ≈ 0)
    assert len(result["records"]) == 1


@pytest.mark.asyncio
async def test_search_wells_radius_excludes_distant(
    httpx_mock: HTTPXMock, sgu_base_url, sample_well_feature
) -> None:
    """search_wells with radius excludes features far from the center."""
    response = {
        "type": "FeatureCollection",
        "numberMatched": 1,
        "numberReturned": 1,
        "features": [sample_well_feature],
        "links": [],
    }
    httpx_mock.add_response(
        url=sgu_url(sgu_base_url, "/collections/brunnar/items"),
        json=response,
        status_code=200,
    )

    import mcp_sgu.sgu_client as sgu_mod
    from mcp_sgu.sgu_client import SGUClient

    sgu_mod._client = SGUClient(base_url=sgu_base_url)

    from mcp_sgu.tools.search_wells import search_wells

    # Search at Gothenburg (57.71, 11.97), far from the feature in Stockholm
    result = await search_wells(
        latitude=57.71,
        longitude=11.97,
        radius_m=100,  # 100m radius
        page_size=10,
    )
    assert "error" not in result
    # The Stockholm feature should be excluded (> 400 km away)
    assert len(result["records"]) == 0


@pytest.mark.asyncio
async def test_get_well_by_fid(
    httpx_mock: HTTPXMock, sgu_base_url, sample_well_feature
) -> None:
    """get_well retrieves a well by OGC feature ID."""
    httpx_mock.add_response(
        url=sgu_url(sgu_base_url, "/collections/brunnar/items/brunnar.123"),
        json=sample_well_feature,
        status_code=200,
    )

    import mcp_sgu.sgu_client as sgu_mod
    from mcp_sgu.sgu_client import SGUClient

    sgu_mod._client = SGUClient(base_url=sgu_base_url)

    from mcp_sgu.tools.get_well import get_well

    result = await get_well(fid="brunnar.123")
    assert "error" not in result
    assert result["feature"]["properties"]["brunnsid"] == 123
    assert "interpretation" in result


@pytest.mark.asyncio
async def test_get_well_missing_identifier() -> None:
    """get_well returns error when no identifier is provided."""
    from mcp_sgu.tools.get_well import get_well

    result = await get_well()
    assert result["error"] == "missing_identifier"


@pytest.mark.asyncio
async def test_get_well_layers_basic(
    httpx_mock: HTTPXMock, sgu_base_url, sample_layer_feature
) -> None:
    """get_well_layers returns layer records."""
    response = {
        "type": "FeatureCollection",
        "numberMatched": 1,
        "numberReturned": 1,
        "features": [sample_layer_feature],
        "links": [],
    }
    httpx_mock.add_response(
        url=sgu_url(sgu_base_url, "/collections/brunnar-lager/items"),
        json=response,
        status_code=200,
    )

    import mcp_sgu.sgu_client as sgu_mod
    from mcp_sgu.sgu_client import SGUClient

    sgu_mod._client = SGUClient(base_url=sgu_base_url)

    from mcp_sgu.tools.get_well_layers import get_well_layers

    result = await get_well_layers(brunnsid=123)
    assert "error" not in result
    assert result["layer_count"] == 1
    layer = result["layers"][0]
    assert layer["layer_number"] == 1
    assert layer["start_depth_m"] == 0.0
    assert layer["end_depth_m"] == 5.0


@pytest.mark.asyncio
async def test_get_well_layers_missing_identifier() -> None:
    """get_well_layers returns error when no identifier is provided."""
    from mcp_sgu.tools.get_well_layers import get_well_layers

    result = await get_well_layers()
    assert result["error"] == "missing_identifier"


@pytest.mark.asyncio
async def test_summarize_well_area_requires_constraint() -> None:
    """summarize_well_area requires a spatial constraint."""
    from mcp_sgu.tools.summarize_well_area import summarize_well_area

    result = await summarize_well_area()
    assert result["error"] == "missing_spatial_constraint"
