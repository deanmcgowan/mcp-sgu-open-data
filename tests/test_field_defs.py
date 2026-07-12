"""Tests for field definitions and feature enrichment."""

from __future__ import annotations


def test_known_field_definition() -> None:
    """Known fields return complete definitions."""
    from mcp_sgu.field_defs import get_field_definition

    defn = get_field_definition("kapacitet")
    assert defn is not None
    assert defn["source_field"] == "kapacitet"
    assert defn["unit"] == "l/h"
    assert defn["label_en"]
    assert defn["label_sv"]
    assert defn["source_reference"]


def test_unknown_field_returns_none() -> None:
    """Unknown fields return None."""
    from mcp_sgu.field_defs import get_field_definition

    assert get_field_definition("nonexistent_field") is None


def test_enrich_feature(sample_well_feature) -> None:
    """enrich_feature returns interpretation for known fields."""
    from mcp_sgu.field_defs import enrich_feature

    interpretation = enrich_feature(sample_well_feature)

    assert "kapacitet" in interpretation
    kap = interpretation["kapacitet"]
    assert kap["source_field"] == "kapacitet"
    assert kap["source_value"] == 3000.0
    assert kap["unit"] == "l/h"
    assert kap["label_en"]

    assert "brunnsid" in interpretation
    assert "kommunkod" in interpretation


def test_enrich_feature_use_code(sample_well_feature) -> None:
    """Enrich feature includes code translations for anvandning_kod."""
    from mcp_sgu.field_defs import enrich_feature

    interpretation = enrich_feature(sample_well_feature)
    anvandning = interpretation.get("anvandning_kod")
    assert anvandning is not None
    assert "Private" in anvandning["code_label_en"]
    assert "Enskild vattentäkt" in anvandning["code_label_sv"]


def test_enrich_feature_position_quality_code(sample_well_feature) -> None:
    """Enrich feature includes position quality translation."""
    from mcp_sgu.field_defs import enrich_feature

    interpretation = enrich_feature(sample_well_feature)
    pq = interpretation.get("posvardering_kod")
    assert pq is not None
    assert pq["code_label_en"] == "Maximum error <100 m"


def test_enrich_feature_does_not_modify_original(sample_well_feature) -> None:
    """enrich_feature must not modify the original feature."""
    import copy

    from mcp_sgu.field_defs import enrich_feature

    original = copy.deepcopy(sample_well_feature)
    enrich_feature(sample_well_feature)
    assert sample_well_feature == original


def test_well_use_codes_coverage() -> None:
    """Well use code list covers common codes."""
    from mcp_sgu.field_defs import WELL_USE_CODES

    assert "HUS" in WELL_USE_CODES
    assert "ENE" in WELL_USE_CODES
    assert "Private" in WELL_USE_CODES["HUS"]["en"]


def test_explain_field_known() -> None:
    """explain_field returns definition for known field."""
    import asyncio

    from mcp_sgu.tools.explain_field import explain_field

    result = asyncio.get_event_loop().run_until_complete(explain_field("totaldjup"))
    assert result["source_field"] == "totaldjup"
    assert result["unit"] == "m"
    assert result["label_en"]


def test_explain_field_unknown() -> None:
    """explain_field returns error for unknown field."""
    import asyncio

    from mcp_sgu.tools.explain_field import explain_field

    result = asyncio.get_event_loop().run_until_complete(explain_field("nonexistent"))
    assert result["error"] == "unknown_field"
    assert "available_fields" in result


def test_explain_field_code_list() -> None:
    """explain_field returns full code list for coded fields."""
    import asyncio

    from mcp_sgu.tools.explain_field import explain_field

    result = asyncio.get_event_loop().run_until_complete(explain_field("anvandning_kod"))
    assert "code_list" in result
    assert "HUS" in result["code_list"]


def test_explain_field_specific_code() -> None:
    """explain_field explains a specific code value."""
    import asyncio

    from mcp_sgu.tools.explain_field import explain_field

    result = asyncio.get_event_loop().run_until_complete(explain_field("anvandning_kod", code_value="ENE"))
    assert result["code_label_sv"].startswith("Energibrunn")
    assert "energy" in result["code_label_en"].lower()
