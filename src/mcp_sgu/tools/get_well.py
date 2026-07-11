"""Tool: get_well — retrieve a single well record."""

from __future__ import annotations

import datetime
from typing import Any

from mcp_sgu.field_defs import enrich_feature
from mcp_sgu.logging_config import get_logger, set_tool_name
from mcp_sgu.sgu_client import SGUError, SGUResponseError, get_sgu_client

logger = get_logger(__name__)

_COLLECTION = "brunnar"
_LAYERS_COLLECTION = "brunnar-lager"


async def get_well(
    brunnsid: int | str | None = None,
    obsplatsid: str | None = None,
    fid: str | None = None,
    include_layers: bool = False,
) -> dict[str, Any]:
    """Retrieve a single well by identifier.

    One of ``brunnsid``, ``obsplatsid``, or ``fid`` must be provided.

    Parameters
    ----------
    brunnsid:
        SGU well ID (numeric).
    obsplatsid:
        SGU observation site ID.
    fid:
        OGC feature ID.
    include_layers:
        If True, also return associated geological layer records.
    """
    set_tool_name("get_well")

    # Validate input
    if not any([brunnsid is not None, obsplatsid, fid]):
        return {
            "error": "missing_identifier",
            "detail": "Provide one of: brunnsid, obsplatsid, or fid.",
        }

    client = get_sgu_client()
    feature = None

    # Try FID (OGC feature ID) first
    if fid:
        try:
            feature = await client.get_item(_COLLECTION, str(fid))
        except SGUResponseError as exc:
            return {"error": "not_found", "detail": str(exc), "fid": fid}
        except SGUError as exc:
            return {"error": "sgu_unavailable", "detail": str(exc)}

    # Try brunnsid via filter
    if feature is None and brunnsid is not None:
        try:
            features, _ = await client.get_items(
                _COLLECTION,
                {"filter": f"brunnsid={brunnsid}", "filter-lang": "cql2-text", "limit": 1},
                max_records=1,
            )
            if features:
                feature = features[0]
        except SGUError as exc:
            return {"error": "sgu_unavailable", "detail": str(exc)}

    # Try obsplatsid via filter
    if feature is None and obsplatsid:
        try:
            features, _ = await client.get_items(
                _COLLECTION,
                {"filter": f"obsplatsid='{obsplatsid}'", "filter-lang": "cql2-text", "limit": 1},
                max_records=1,
            )
            if features:
                feature = features[0]
        except SGUError as exc:
            return {"error": "sgu_unavailable", "detail": str(exc)}

    if feature is None:
        return {
            "error": "not_found",
            "detail": "Well not found.",
            "brunnsid": brunnsid,
            "obsplatsid": obsplatsid,
            "fid": fid,
        }

    result: dict[str, Any] = {
        "feature": feature,
        "interpretation": enrich_feature(feature),
        "source_collection": _COLLECTION,
        "retrieval_timestamp": _now_iso(),
        "crs": "EPSG:4326 (WGS84)",
    }

    if include_layers:
        from mcp_sgu.tools.get_well_layers import get_well_layers

        props = feature.get("properties") or {}
        layer_brunnsid = props.get("brunnsid")
        layer_obsplatsid = props.get("obsplatsid")

        layers_result = await get_well_layers(
            brunnsid=layer_brunnsid,
            obsplatsid=layer_obsplatsid,
        )
        result["layers"] = layers_result

    return result


def _now_iso() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()
