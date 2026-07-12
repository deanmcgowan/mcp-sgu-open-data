"""Validated CQL2-text filter construction for SGU Brunnar."""

from __future__ import annotations

import datetime
from typing import Any

from mcp_sgu.field_defs import POSITION_QUALITY_CODES, WELL_USE_CODES


class FilterError(ValueError):
    """A caller supplied an invalid SGU filter."""


def cql_string(value: str) -> str:
    """Return a CQL2 string literal with single quotes escaped."""
    return "'" + value.replace("'", "''") + "'"


def build_well_filter(
    *,
    municipality_code: str | None = None,
    municipality_name: str | None = None,
    well_use_code: str | None = None,
    min_total_depth: float | None = None,
    max_total_depth: float | None = None,
    min_capacity: float | None = None,
    max_capacity: float | None = None,
    position_quality_code: str | None = None,
    drilling_date_from: str | None = None,
    drilling_date_to: str | None = None,
) -> str | None:
    """Build only supported, validated equality and range predicates."""
    parts: list[str] = []
    if municipality_code:
        if not municipality_code.isdigit() or len(municipality_code) != 4:
            raise FilterError("municipality_code must be four digits")
        parts.append(f"kommunkod={cql_string(municipality_code)}")
    if municipality_name:
        parts.append(f"kommunnamn={cql_string(municipality_name)}")
    if well_use_code:
        code = well_use_code.upper()
        if code not in WELL_USE_CODES:
            raise FilterError(f"well_use_code must be one of: {', '.join(WELL_USE_CODES)}")
        parts.append(f"anvandning_kod={cql_string(code)}")
    if position_quality_code:
        if position_quality_code not in POSITION_QUALITY_CODES:
            raise FilterError(f"position_quality_code must be one of: {', '.join(POSITION_QUALITY_CODES)}")
        parts.append(f"posvardering_kod={cql_string(position_quality_code)}")
    for field, value, operator in (
        ("totaldjup", min_total_depth, ">="),
        ("totaldjup", max_total_depth, "<="),
        ("kapacitet", min_capacity, ">="),
        ("kapacitet", max_capacity, "<="),
    ):
        if value is not None:
            if not isinstance(value, (int, float)):
                raise FilterError(f"{field} must be numeric")
            parts.append(f"{field}{operator}{value}")
    for value, operator in ((drilling_date_from, ">="), (drilling_date_to, "<=")):
        if value:
            try:
                datetime.date.fromisoformat(value)
            except ValueError as exc:
                raise FilterError("drilling dates must be ISO YYYY-MM-DD values") from exc
            parts.append(f"borrdatum{operator}{cql_string(value)}")
    return " AND ".join(parts) or None


def add_filter(params: dict[str, Any], filter_text: str | None) -> None:
    """Add an already validated CQL2 filter to request parameters."""
    if filter_text:
        params["filter"] = filter_text
        params["filter-lang"] = "cql2-text"
