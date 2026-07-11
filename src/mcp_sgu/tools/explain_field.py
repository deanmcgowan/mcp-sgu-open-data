"""Tool: explain_field — explain SGU field names and code values."""

from __future__ import annotations

from typing import Any

from mcp_sgu.field_defs import (
    FIELD_DEFINITIONS,
    POSITION_QUALITY_CODES,
    WELL_USE_CODES,
    get_field_definition,
)


async def explain_field(
    field_name: str,
    code_value: str | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Explain an SGU field name and optional code value.

    Parameters
    ----------
    field_name:
        The SGU source field name (e.g. ``"kapacitet"`` or ``"anvandning_kod"``).
    code_value:
        Optional code value to explain (e.g. ``"HUS"`` for ``anvandning_kod``).
    language:
        Response language: ``"en"`` or ``"sv"``.
    """
    if not field_name or not field_name.strip():
        return {"error": "invalid_input", "detail": "field_name must not be empty."}

    defn = get_field_definition(field_name.strip().lower())

    if defn is None:
        # List available fields as a helpful hint
        available = sorted(FIELD_DEFINITIONS.keys())
        return {
            "error": "unknown_field",
            "field_name": field_name,
            "detail": f"Field '{field_name}' is not in the known field definitions.",
            "available_fields": available,
        }

    result: dict[str, Any] = {
        "source_field": defn["source_field"],
        "label_sv": defn["label_sv"],
        "label_en": defn["label_en"],
        "description_sv": defn.get("description_sv"),
        "description_en": defn.get("description_en"),
        "type": defn.get("type"),
        "unit": defn.get("unit"),
        "caveats": defn.get("caveats", []),
        "source_reference": defn.get("source_reference"),
    }

    # Code value lookup
    code_map: dict[str, dict[str, str]] | None = None
    if defn["source_field"] == "anvandning_kod":
        code_map = WELL_USE_CODES
    elif defn["source_field"] == "posvardering_kod":
        code_map = POSITION_QUALITY_CODES

    if code_map:
        if code_value:
            code_entry = code_map.get(str(code_value).upper())
            if code_entry:
                result["code_value"] = code_value
                result["code_label_sv"] = code_entry["sv"]
                result["code_label_en"] = code_entry["en"]
            else:
                result["code_value"] = code_value
                result["code_warning"] = f"Code '{code_value}' is not in the known code list for this field."
        else:
            # Return all codes
            result["code_list"] = {k: {"sv": v["sv"], "en": v["en"]} for k, v in code_map.items()}

    return result
