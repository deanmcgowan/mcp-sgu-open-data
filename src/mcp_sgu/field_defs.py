"""Current SGU Brunnar field definitions and code lists."""

from __future__ import annotations

from typing import Any

_SOURCE = "https://resource.sgu.se/dokument/produkter/brunnar-beskrivning.pdf"


def _field(
    label_sv: str, label_en: str, description_en: str, unit: str | None = None, caveats: list[str] | None = None
) -> dict[str, Any]:
    return {
        "source_field": "",
        "label_sv": label_sv,
        "label_en": label_en,
        "description_en": description_en,
        "unit": unit,
        "caveats": caveats or [],
        "source_reference": _SOURCE,
    }


FIELD_DEFINITIONS: dict[str, dict[str, Any]] = {
    "fid": _field("Objekt-ID", "Feature ID", "SGU feature identifier."),
    "obsplatsid": _field("Observationsplats-ID", "Observation site ID", "Links wells and layers."),
    "brunnsid": _field("Brunns-ID", "Well ID", "SGU well identifier."),
    "n": _field("Nordkoordinat", "Northing", "SWEREF 99 TM northing.", "m"),
    "e": _field("Östkoordinat", "Easting", "SWEREF 99 TM easting.", "m"),
    "posvardering_kod": _field("Positionsvärderingskod", "Position quality code", "Location accuracy code."),
    "posvardering": _field("Positionsvärdering", "Position quality", "Location accuracy description."),
    "kommunkod": _field("Kommunkod", "Municipality code", "Four-digit SCB municipality code."),
    "kommunnamn": _field("Kommunnamn", "Municipality name", "Municipality name."),
    "fastighet": _field("Fastighet", "Property", "Property designation."),
    "ort": _field("Ort", "Locality", "Locality name."),
    "lage_specifikt": _field("Läge specifikt", "Specific location", "Specific location description."),
    "borrdatum": _field(
        "Borrdatum",
        "Drilling date",
        "Date drilling occurred; it can be year-only or year-month.",
        caveats=["Partial dates are valid source values."],
    ),
    "tecken_vattenmangd": _field("Tecken vattenmängd", "Capacity qualifier", "Qualifier before capacity."),
    "kapacitet": _field("Kapacitet", "Reported capacity", "Reported capacity, not guaranteed yield.", "l/h"),
    "tecken_niva": _field("Tecken nivå", "Groundwater level qualifier", "Minus can indicate artesian level."),
    "grundvattenniva": _field("Grundvattennivå", "Groundwater level", "Metres below ground surface.", "m"),
    "nivadatum": _field("Nivådatum", "Water-level date", "Date of groundwater-level measurement."),
    "bottendiam": _field("Bottendiameter", "Bottom diameter", "Bottom or drilling diameter.", "mm"),
    "totaldjup": _field("Totaldjup", "Total depth", "Total well depth.", "m"),
    "tecken_jorddjup": _field("Tecken jorddjup", "Soil-depth qualifier", "Qualifier before soil depth."),
    "jorddjup": _field("Jorddjup", "Soil depth", "Soil depth.", "m"),
    "rorborrning_till": _field("Rörborrning till", "Drilling/casing depth", "Drilling or casing depth.", "m"),
    "stalror_till": _field("Stålrör till", "Steel casing depth", "Steel casing depth.", "m"),
    "plastror_till": _field("Plaströr till", "Plastic casing depth", "Plastic casing depth.", "m"),
    "tatning_kod": _field("Tätningskod", "Sealing code", "Coded sealing method."),
    "tatning": _field("Tätning", "Sealing", "Sealing description."),
    "anvandning_kod": _field("Användningskod", "Well-use code", "Coded intended well use."),
    "anvandning": _field("Användning", "Well use", "Well-use description."),
    "gradborrning": _field("Gradborrning", "Directional drilling", "Inclination and bearing."),
    "allman_anmarkning": _field("Allmän anmärkning", "General note", "General source note."),
    "grundvattenanmarkning": _field("Grundvattenanmärkning", "Groundwater note", "Groundwater source note."),
    "geom": _field("Geometri", "Geometry", "Source geometry in SWEREF 99 TM."),
    "lagerid": _field("Lager-ID", "Layer ID", "SGU geological layer identifier."),
    "lagernr": _field("Lagernummer", "Layer number", "Layer sequence number."),
    "djup_fran": _field("Djup från", "Layer start depth", "Layer start depth.", "m"),
    "djup_till": _field("Djup till", "Layer end depth", "Layer end depth.", "m"),
    "jordart_bergart": _field("Jordart/bergart", "Soil/bedrock description", "Source soil or bedrock description."),
    "lageranmarkning": _field("Lageranmärkning", "Layer note", "Layer source note."),
}
for _name, _definition in FIELD_DEFINITIONS.items():
    _definition["source_field"] = _name

WELL_USE_CODES = {
    "ÖVR": {"sv": "Annan användning", "en": "Other use"},
    "BEV": {"sv": "Bevattning, handelsträdgård", "en": "Irrigation, market garden"},
    "ENE": {"sv": "Energibrunn (värme, kyla)", "en": "Energy well (heating, cooling)"},
    "HUS": {"sv": "Enskild vattentäkt; hushåll, fritidshus, mindre lantbruk", "en": "Private water supply"},
    "IND": {"sv": "Industri(-vatten)", "en": "Industrial water"},
    "OBS": {"sv": "Observationsbrunn, -rör", "en": "Observation well or pipe"},
    "SAM": {"sv": "Samfälld vattentäkt (minst 10 hushåll)", "en": "Shared water supply"},
    "LAN": {"sv": "Större lantbruks vattentäkt", "en": "Large agricultural water supply"},
    "VAF": {"sv": "Vattenförsörjning/vattenförening", "en": "Water supply/water association"},
}
POSITION_QUALITY_CODES = {
    "9": {"sv": "Brunnen går ej att lägesbestämma", "en": "Well cannot be located"},
    "3": {"sv": "Ej lägeskontrollerad", "en": "Location not checked"},
    "0": {"sv": "Maxfel <100 m", "en": "Maximum error <100 m"},
    "1": {"sv": "Maxfel <250 m", "en": "Maximum error <250 m"},
    "2": {"sv": "Osäker position", "en": "Uncertain position"},
}
SEALING_CODES = {
    "T": {"sv": "Bentonit", "en": "Bentonite"},
    "C": {"sv": "Cementering", "en": "Cementing"},
    "B": {"sv": "Cementering och extra fodring", "en": "Cementing and extra casing"},
    "P": {"sv": "Extra plast/stålrörsfodring", "en": "Extra plastic/steel casing"},
    "L": {"sv": "Lera", "en": "Clay"},
    "M": {"sv": "Manschett", "en": "Sleeve"},
    "N": {"sv": "Nitning", "en": "Riveting"},
    "Ö": {"sv": "Övrig/annan tätning", "en": "Other sealing"},
}


def get_field_definition(field_name: str) -> dict[str, Any] | None:
    """Return a definition for a current SGU source field."""
    return FIELD_DEFINITIONS.get(field_name.lower())


def enrich_feature(feature: dict[str, Any]) -> dict[str, Any]:
    """Create contextual labels without changing source properties."""
    interpretation: dict[str, Any] = {}
    for field, value in (feature.get("properties") or {}).items():
        definition = get_field_definition(field)
        if not definition:
            continue
        entry = {
            "source_field": field,
            "source_value": value,
            "label_sv": definition["label_sv"],
            "label_en": definition["label_en"],
        }
        if definition["unit"]:
            entry["unit"] = definition["unit"]
        if definition["caveats"]:
            entry["caveats"] = definition["caveats"]
        codes = {
            "anvandning_kod": WELL_USE_CODES,
            "posvardering_kod": POSITION_QUALITY_CODES,
            "tatning_kod": SEALING_CODES,
        }.get(field)
        if codes and value is not None and (code := codes.get(str(value).upper())):
            entry["code_label_sv"], entry["code_label_en"] = code["sv"], code["en"]
        interpretation[field] = entry
    return interpretation
