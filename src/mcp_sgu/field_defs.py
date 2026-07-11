"""SGU field definitions, code lists, and contextual labels (Swedish/English)."""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Field definitions
# ---------------------------------------------------------------------------
FIELD_DEFINITIONS: dict[str, dict[str, Any]] = {
    "brunnsid": {
        "source_field": "brunnsid",
        "label_sv": "Brunns-ID",
        "label_en": "Well ID",
        "description_sv": "Unikt identifieringsnummer för brunnen i SGUs brunnsarkiv.",
        "description_en": "Unique numeric identifier for the well in SGU's well archive.",
        "unit": None,
        "type": "integer",
        "caveats": [],
        "source_reference": "https://resource.sgu.se/oppnadata/brunnar",
    },
    "obsplatsid": {
        "source_field": "obsplatsid",
        "label_sv": "Observationsplats-ID",
        "label_en": "Observation site ID",
        "description_sv": "Identifierare för observationsplatsen (kan koppla brunnar och lager).",
        "description_en": "Identifier for the observation site; used to link wells and geological layers.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": "https://resource.sgu.se/oppnadata/brunnar",
    },
    "kommunkod": {
        "source_field": "kommunkod",
        "label_sv": "Kommunkod",
        "label_en": "Municipality code (SCB)",
        "description_sv": "SCBs fyrsiffriga kommunkod.",
        "description_en": "Four-digit Statistics Sweden (SCB) municipality code.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": "https://www.scb.se/hitta-statistik/regional-statistik-och-kartor/regionala-indelningar/lan-och-kommuner/",
    },
    "kommunnamn": {
        "source_field": "kommunnamn",
        "label_sv": "Kommunnamn",
        "label_en": "Municipality name",
        "description_sv": "Kommunens namn.",
        "description_en": "Name of the municipality.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": None,
    },
    "lanskod": {
        "source_field": "lanskod",
        "label_sv": "Länskod",
        "label_en": "County code",
        "description_sv": "Tvåsiffrig länskod.",
        "description_en": "Two-digit Swedish county code.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": None,
    },
    "lansnamn": {
        "source_field": "lansnamn",
        "label_sv": "Länsnamn",
        "label_en": "County name",
        "description_sv": "Länets namn.",
        "description_en": "Name of the county.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": None,
    },
    "kapacitet": {
        "source_field": "kapacitet",
        "label_sv": "Kapacitet",
        "label_en": "Reported well capacity",
        "description_sv": "Rapporterad kapacitet för brunnen.",
        "description_en": (
            "Reported capacity associated with the well. "
            "This value must not automatically be interpreted as the guaranteed "
            "long-term sustainable yield; it may reflect a single pump test or "
            "an initial estimate."
        ),
        "unit": "l/h",
        "type": "number",
        "caveats": [
            "Capacity may reflect a single pump test, not long-term sustainable yield.",
            "Missing values are common.",
        ],
        "source_reference": "https://resource.sgu.se/oppnadata/brunnar",
    },
    "totaldjup": {
        "source_field": "totaldjup",
        "label_sv": "Totaldjup",
        "label_en": "Total well depth",
        "description_sv": "Totalt djup för brunnen.",
        "description_en": "Total depth of the well from ground surface.",
        "unit": "m",
        "type": "number",
        "caveats": ["May be approximate."],
        "source_reference": "https://resource.sgu.se/oppnadata/brunnar",
    },
    "borrdjup": {
        "source_field": "borrdjup",
        "label_sv": "Borrdjup",
        "label_en": "Drilled depth",
        "description_sv": "Borrdjup för brunnen.",
        "description_en": "The depth drilled into bedrock or soil.",
        "unit": "m",
        "type": "number",
        "caveats": [],
        "source_reference": None,
    },
    "vattenniva": {
        "source_field": "vattenniva",
        "label_sv": "Vattennivå",
        "label_en": "Static water level",
        "description_sv": "Stillastående vattennivå i brunnen (djup under markytan).",
        "description_en": (
            "Static (resting) water level measured as depth below ground surface. "
            "This may not represent current groundwater conditions; "
            "it is often measured close to the drilling date."
        ),
        "unit": "m",
        "type": "number",
        "caveats": [
            "May not represent current groundwater conditions.",
            "Often measured at or shortly after drilling.",
        ],
        "source_reference": None,
    },
    "borrningsstart": {
        "source_field": "borrningsstart",
        "label_sv": "Borrningsstart",
        "label_en": "Drilling start date",
        "description_sv": "Datum då borrningen påbörjades.",
        "description_en": "Date when drilling started. May be a partial date (year only).",
        "unit": None,
        "type": "date",
        "caveats": ["May be a partial date (year only)."],
        "source_reference": None,
    },
    "borrningsslut": {
        "source_field": "borrningsslut",
        "label_sv": "Borrningsslut",
        "label_en": "Drilling end date",
        "description_sv": "Datum då borrningen avslutades.",
        "description_en": "Date when drilling was completed. May be a partial date.",
        "unit": None,
        "type": "date",
        "caveats": ["May be a partial date (year only)."],
        "source_reference": None,
    },
    "anvandningskod": {
        "source_field": "anvandningskod",
        "label_sv": "Användningskod",
        "label_en": "Well use code",
        "description_sv": "Kod för brunnens användning.",
        "description_en": "Coded classification of the well's intended use.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": "https://resource.sgu.se/oppnadata/brunnar",
    },
    "anvandning": {
        "source_field": "anvandning",
        "label_sv": "Användning",
        "label_en": "Well use description",
        "description_sv": "Beskrivning av brunnens användning.",
        "description_en": "Textual description of the well's intended use.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": None,
    },
    "positionskvalitetskod": {
        "source_field": "positionskvalitetskod",
        "label_sv": "Positionskvalitetskod",
        "label_en": "Position quality code",
        "description_sv": "Kod som beskriver positonens noggrannhet.",
        "description_en": (
            "Code indicating the accuracy of the well's geographic position. "
            "Lower quality codes indicate greater positional uncertainty."
        ),
        "unit": None,
        "type": "string",
        "caveats": [
            "Lower position quality codes indicate greater positional uncertainty.",
            "Some wells may be positioned inaccurately.",
        ],
        "source_reference": "https://resource.sgu.se/oppnadata/brunnar",
    },
    "positionskvalitet": {
        "source_field": "positionskvalitet",
        "label_sv": "Positionskvalitet",
        "label_en": "Position quality description",
        "description_sv": "Beskrivning av positionens noggrannhet.",
        "description_en": "Textual description of the positional accuracy.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": None,
    },
    "brunnotyp": {
        "source_field": "brunnotyp",
        "label_sv": "Brunnotyp",
        "label_en": "Well type",
        "description_sv": "Typ av brunn (t.ex. bergborrad, grävd).",
        "description_en": "Type of well construction (e.g., bedrock-drilled, dug).",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": None,
    },
    "jorddjup": {
        "source_field": "jorddjup",
        "label_sv": "Jorddjup",
        "label_en": "Soil depth",
        "description_sv": "Djup till berg (jordlager ovanför berg).",
        "description_en": "Depth of the overburden soil layer above bedrock.",
        "unit": "m",
        "type": "number",
        "caveats": [],
        "source_reference": None,
    },
    "lagernr": {
        "source_field": "lagernr",
        "label_sv": "Lagernummer",
        "label_en": "Layer number",
        "description_sv": "Ordningsnummer för geologiskt lager.",
        "description_en": "Sequential number identifying the geological layer.",
        "unit": None,
        "type": "integer",
        "caveats": [],
        "source_reference": None,
    },
    "startdjup": {
        "source_field": "startdjup",
        "label_sv": "Startdjup",
        "label_en": "Layer start depth",
        "description_sv": "Lagrets startdjup under markytan.",
        "description_en": "Start depth of the geological layer below ground surface.",
        "unit": "m",
        "type": "number",
        "caveats": [],
        "source_reference": None,
    },
    "slutdjup": {
        "source_field": "slutdjup",
        "label_sv": "Slutdjup",
        "label_en": "Layer end depth",
        "description_sv": "Lagrets slutdjup under markytan.",
        "description_en": "End depth of the geological layer below ground surface.",
        "unit": "m",
        "type": "number",
        "caveats": [],
        "source_reference": None,
    },
    "jordart": {
        "source_field": "jordart",
        "label_sv": "Jordart",
        "label_en": "Soil/material type",
        "description_sv": "Jordartsbeteckning för lagret.",
        "description_en": "Soil or geological material classification for the layer.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": None,
    },
    "bergartskod": {
        "source_field": "bergartskod",
        "label_sv": "Bergartskod",
        "label_en": "Rock type code",
        "description_sv": "Kod för bergarten.",
        "description_en": "Code identifying the rock type.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": None,
    },
    "bergart": {
        "source_field": "bergart",
        "label_sv": "Bergart",
        "label_en": "Rock type",
        "description_sv": "Beskrivning av bergarten.",
        "description_en": "Description of the rock type.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": None,
    },
    "lagernotering": {
        "source_field": "lagernotering",
        "label_sv": "Lagernotering",
        "label_en": "Layer notes",
        "description_sv": "Fritext notering om lagret.",
        "description_en": "Free-text notes about the geological layer.",
        "unit": None,
        "type": "string",
        "caveats": [],
        "source_reference": None,
    },
}


# ---------------------------------------------------------------------------
# Well use code translations
# ---------------------------------------------------------------------------
WELL_USE_CODES: dict[str, dict[str, str]] = {
    "E": {"sv": "Energibrunn", "en": "Energy well (geothermal)"},
    "V": {"sv": "Vattenförsörjning", "en": "Water supply"},
    "A": {"sv": "Anläggning", "en": "Installation/construction"},
    "O": {"sv": "Observation", "en": "Observation/monitoring"},
    "P": {"sv": "Provbrunn", "en": "Test well"},
    "I": {"sv": "Infiltration", "en": "Infiltration"},
    "U": {"sv": "Uppvärmning", "en": "Heating"},
    "K": {"sv": "Kyla", "en": "Cooling"},
    "F": {"sv": "Forskning", "en": "Research"},
    "S": {"sv": "Sanering", "en": "Remediation"},
}

# ---------------------------------------------------------------------------
# Position quality code translations
# ---------------------------------------------------------------------------
POSITION_QUALITY_CODES: dict[str, dict[str, str]] = {
    "1": {
        "sv": "GPS-koordinat, hög noggrannhet",
        "en": "GPS coordinate, high accuracy (< 1 m)",
    },
    "2": {
        "sv": "Inmätt koordinat, god noggrannhet",
        "en": "Surveyed coordinate, good accuracy (1–10 m)",
    },
    "3": {
        "sv": "Kartbedömning, acceptabel noggrannhet",
        "en": "Map-estimated coordinate, acceptable accuracy (10–100 m)",
    },
    "4": {
        "sv": "Osäker position",
        "en": "Uncertain position (> 100 m)",
    },
    "5": {
        "sv": "Mycket osäker position",
        "en": "Very uncertain position",
    },
}


def get_field_definition(field_name: str) -> dict[str, Any] | None:
    """Return the definition for a known field, or None."""
    return FIELD_DEFINITIONS.get(field_name.lower())


def enrich_feature(feature: dict[str, Any]) -> dict[str, Any]:
    """Return a contextual interpretation object for a feature's properties.

    Does not modify the original feature; returns a separate interpretation dict.
    """
    props = feature.get("properties") or {}
    interpretation: dict[str, Any] = {}

    for field, value in props.items():
        defn = get_field_definition(field)
        if defn is None:
            continue

        entry: dict[str, Any] = {
            "source_field": field,
            "source_value": value,
            "label_sv": defn["label_sv"],
            "label_en": defn["label_en"],
        }
        if defn.get("unit"):
            entry["unit"] = defn["unit"]
        if defn.get("caveats"):
            entry["caveats"] = defn["caveats"]

        # Coded fields
        if field == "anvandningskod" and value:
            code_def = WELL_USE_CODES.get(str(value).upper())
            if code_def:
                entry["code_label_sv"] = code_def["sv"]
                entry["code_label_en"] = code_def["en"]

        if field == "positionskvalitetskod" and value:
            pq_def = POSITION_QUALITY_CODES.get(str(value))
            if pq_def:
                entry["code_label_sv"] = pq_def["sv"]
                entry["code_label_en"] = pq_def["en"]
                if str(value) in ("4", "5"):
                    entry["warnings"] = ["Position quality is low; coordinates may be inaccurate."]

        interpretation[field] = entry

    return interpretation
