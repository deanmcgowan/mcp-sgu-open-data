"""Tool: get_well_layers — retrieve geological layers for a well."""

from __future__ import annotations

import datetime
from typing import Any

from mcp_sgu.field_defs import enrich_feature
from mcp_sgu.logging_config import get_logger, set_tool_name
from mcp_sgu.sgu_client import SGUError, get_sgu_client

logger = get_logger(__name__)

_COLLECTION = "brunnar-lager"


async def get_well_layers(
    brunnsid: int | str | None = None,
    obsplatsid: str | None = None,
) -> dict[str, Any]:
    """Retrieve geological layer records associated with a well.

    Parameters
    ----------
    brunnsid:
        SGU well ID (numeric).
    obsplatsid:
        SGU observation site ID.
    """
    set_tool_name("get_well_layers")

    if brunnsid is None and not obsplatsid:
        return {
            "error": "missing_identifier",
            "detail": "Provide at least one of: brunnsid or obsplatsid.",
        }

    client = get_sgu_client()
    cql_parts: list[str] = []
    if brunnsid is not None:
        cql_parts.append(f"brunnsid={brunnsid}")
    if obsplatsid:
        cql_parts.append(f"obsplatsid='{obsplatsid}'")

    params = {
        "filter": " AND ".join(cql_parts),
        "filter-lang": "cql2-text",
        "limit": 200,
        "sortby": "+lagernr",
    }

    try:
        features, meta = await client.get_items(
            _COLLECTION,
            params,
            max_records=200,
        )
    except SGUError as exc:
        return {"error": "sgu_unavailable", "detail": str(exc)}

    # Sort by layer number or start depth
    def sort_key(f: dict[str, Any]) -> tuple:
        props = f.get("properties") or {}
        return (
            props.get("lagernr") or 9999,
            props.get("startdjup") or 0.0,
        )

    features_sorted = sorted(features, key=sort_key)

    enriched = []
    for f in features_sorted:
        props = f.get("properties") or {}
        enriched.append({
            "feature": f,
            "interpretation": enrich_feature(f),
            "layer_number": props.get("lagernr"),
            "start_depth_m": props.get("startdjup"),
            "end_depth_m": props.get("slutdjup"),
            "material": props.get("jordart") or props.get("bergart"),
            "notes": props.get("lagernotering"),
        })

    warnings: list[str] = []
    if meta.get("_truncated"):
        warnings.append("Layer results were truncated; more layers may exist.")

    return {
        "brunnsid": brunnsid,
        "obsplatsid": obsplatsid,
        "source_collection": _COLLECTION,
        "retrieval_timestamp": _now_iso(),
        "layer_count": len(enriched),
        "layers": enriched,
        "warnings": warnings,
    }


def _now_iso() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()
