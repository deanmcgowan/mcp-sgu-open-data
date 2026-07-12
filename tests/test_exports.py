"""Tests for export functionality."""

from __future__ import annotations

import csv
import io
import json
import time

import pytest


@pytest.fixture
def sample_features(sample_well_feature) -> list:
    return [sample_well_feature]


@pytest.mark.asyncio
async def test_create_csv_export(sample_features) -> None:
    """CSV export produces valid UTF-8 CSV content."""
    from mcp_sgu.exports import create_export, get_export

    meta = await create_export(sample_features, "csv", {"test": True})
    assert meta["format"] == "csv"
    assert meta["record_count"] == 1
    assert "export_id" in meta
    assert "download_url" in meta
    assert meta["download_url"].startswith("/api/exports/")

    record = await get_export(meta["export_id"])
    assert record is not None
    content = record.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["feature_id"] == "brunnar.123"


@pytest.mark.asyncio
async def test_create_geojson_export(sample_features) -> None:
    """GeoJSON export produces a valid FeatureCollection."""
    from mcp_sgu.exports import create_export, get_export

    meta = await create_export(sample_features, "geojson", {"test": True})
    assert meta["format"] == "geojson"

    record = await get_export(meta["export_id"])
    assert record is not None
    fc = json.loads(record.content)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1


@pytest.mark.asyncio
async def test_export_expiry(sample_features) -> None:
    """Expired exports are not retrievable."""
    from mcp_sgu import exports as exp_module
    from mcp_sgu.exports import create_export, get_export

    meta = await create_export(sample_features, "csv", {})
    export_id = meta["export_id"]

    # Manually expire by manipulating the expires_at
    async with exp_module._exports_lock:
        exp_module._exports[export_id].expires_at = time.time() - 1

    record = await get_export(export_id)
    assert record is None


@pytest.mark.asyncio
async def test_export_size_limit() -> None:
    """Export fails when record count exceeds MAX_EXPORT_RECORDS."""
    import os

    import mcp_sgu.config as cfg_module

    os.environ["MAX_EXPORT_RECORDS"] = "5"
    cfg_module._settings = None

    try:
        features = [
            {"type": "Feature", "id": str(i), "geometry": None, "properties": {"brunnsid": i}} for i in range(10)
        ]
        from mcp_sgu.exports import create_export

        with pytest.raises(ValueError, match="MAX_EXPORT_RECORDS"):
            await create_export(features, "csv", {})
    finally:
        os.environ["MAX_EXPORT_RECORDS"] = "1000"
        cfg_module._settings = None


@pytest.mark.asyncio
async def test_export_invalid_format(sample_features) -> None:
    """Invalid export format raises ValueError."""
    from mcp_sgu.exports import create_export

    with pytest.raises(ValueError, match="Unsupported export format"):
        await create_export(sample_features, "xlsx", {})


@pytest.mark.asyncio
async def test_export_not_found() -> None:
    """Non-existent export ID returns None."""
    from mcp_sgu.exports import get_export

    result = await get_export("nonexistent-id-xyz")
    assert result is None


@pytest.mark.asyncio
async def test_csv_has_coordinates(sample_features) -> None:
    """CSV export includes longitude and latitude columns."""
    from mcp_sgu.exports import create_export, get_export

    meta = await create_export(sample_features, "csv", {})
    record = await get_export(meta["export_id"])
    assert record is not None
    content = record.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    assert "longitude" in rows[0]
    assert "latitude" in rows[0]
    assert float(rows[0]["longitude"]) == pytest.approx(18.0592, abs=0.0001)
    assert float(rows[0]["latitude"]) == pytest.approx(59.3302, abs=0.0001)
