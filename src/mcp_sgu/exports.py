"""Export functionality: CSV and GeoJSON exports with TTL management."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from mcp_sgu.config import get_settings
from mcp_sgu.logging_config import get_logger

logger = get_logger(__name__)

_exports: dict[str, ExportRecord] = {}
_exports_lock = asyncio.Lock()


@dataclass
class ExportRecord:
    """Metadata and content for a single export."""

    export_id: str
    format: str  # "csv" or "geojson"
    record_count: int
    created_at: float
    expires_at: float
    query_summary: dict[str, Any]
    content: bytes

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


async def create_export(
    features: list[dict[str, Any]],
    fmt: str,
    query_summary: dict[str, Any],
) -> dict[str, Any]:
    """Create an in-memory export and return its metadata.

    Parameters
    ----------
    features:
        List of GeoJSON Feature dicts.
    fmt:
        ``"csv"`` or ``"geojson"``.
    query_summary:
        Summary dict of the query that produced these features.

    Returns a metadata dict.
    """
    settings = get_settings()

    if len(features) > settings.max_export_records:
        raise ValueError(
            f"Export size {len(features)} exceeds MAX_EXPORT_RECORDS={settings.max_export_records}"
        )

    if fmt not in ("csv", "geojson"):
        raise ValueError(f"Unsupported export format: {fmt!r}. Use 'csv' or 'geojson'.")

    export_id = str(uuid.uuid4())
    now = time.time()
    expires_at = now + settings.export_ttl_seconds

    if fmt == "csv":
        content = _to_csv(features)
    else:
        content = _to_geojson(features)

    record = ExportRecord(
        export_id=export_id,
        format=fmt,
        record_count=len(features),
        created_at=now,
        expires_at=expires_at,
        query_summary=query_summary,
        content=content,
    )

    async with _exports_lock:
        _exports[export_id] = record
        # Purge expired exports opportunistically
        expired_keys = [k for k, v in _exports.items() if v.is_expired and k != export_id]
        for k in expired_keys:
            del _exports[k]
        if expired_keys:
            logger.info("Purged expired exports", extra={"count": len(expired_keys)})

    return {
        "export_id": export_id,
        "format": fmt,
        "record_count": len(features),
        "created_at": _iso(now),
        "expires_at": _iso(expires_at),
        "download_url": f"/api/exports/{export_id}",
        "query_summary": query_summary,
    }


async def get_export(export_id: str) -> ExportRecord | None:
    """Retrieve an export by ID. Returns None if not found or expired."""
    async with _exports_lock:
        record = _exports.get(export_id)
        if record is None:
            return None
        if record.is_expired:
            del _exports[export_id]
            return None
        return record


async def purge_all_exports() -> int:
    """Purge all expired exports. Returns number purged."""
    async with _exports_lock:
        expired = [k for k, v in _exports.items() if v.is_expired]
        for k in expired:
            del _exports[k]
        return len(expired)


def _to_csv(features: list[dict[str, Any]]) -> bytes:
    """Convert features to CSV bytes."""
    if not features:
        return b""

    buf = io.StringIO()
    # Collect all property keys
    all_keys: list[str] = []
    seen_keys: set[str] = set()
    for f in features:
        for k in (f.get("properties") or {}).keys():
            if k not in seen_keys:
                all_keys.append(k)
                seen_keys.add(k)

    fieldnames = ["feature_id", "geometry_type", "longitude", "latitude", *all_keys]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for f in features:
        row: dict[str, Any] = {
            "feature_id": f.get("id", ""),
            "geometry_type": (f.get("geometry") or {}).get("type", ""),
        }
        coords = (f.get("geometry") or {}).get("coordinates")
        if coords and (f.get("geometry") or {}).get("type") == "Point":
            row["longitude"] = coords[0]
            row["latitude"] = coords[1]
        row.update(f.get("properties") or {})
        writer.writerow(row)

    return buf.getvalue().encode("utf-8-sig")  # UTF-8 BOM for Excel compatibility


def _to_geojson(features: list[dict[str, Any]]) -> bytes:
    """Convert features to GeoJSON FeatureCollection bytes."""
    fc = {
        "type": "FeatureCollection",
        "features": features,
    }
    return json.dumps(fc, ensure_ascii=False, default=str).encode("utf-8")


def _iso(ts: float) -> str:
    """Return an ISO 8601 timestamp string."""
    import datetime

    return datetime.datetime.fromtimestamp(ts, tz=datetime.UTC).isoformat()
