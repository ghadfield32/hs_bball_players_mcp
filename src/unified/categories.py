"""
Categorical Vocabularies and Encoders

Defines canonical categories for circuits, source types, levels, genders, etc.
Used for normalization and ML encoding across all data sources.
"""

from enum import Enum
from typing import Tuple


class SourceType(str, Enum):
    """Canonical source type categories."""

    CIRCUIT = "CIRCUIT"
    ASSOCIATION = "ASSOCIATION"
    PLATFORM = "PLATFORM"
    PREP = "PREP"
    LEAGUE = "LEAGUE"
    EVENT = "EVENT"


# Canonical circuit keys - maps internal source_key to display name
CIRCUIT_KEYS = {
    # US National Circuits
    "eybl": "EYBL",
    "eybl_girls": "EYBL_GIRLS",
    "three_ssb": "3SSB",
    "three_ssb_girls": "3SSB_GIRLS",
    "uaa": "UAA",
    "uaa_girls": "UAA_GIRLS",
    "ote": "OTE",
    "grind_session": "GRIND_SESSION",
    # European Youth Leagues
    "angt": "ANGT",
    "nbbl": "NBBL",
    "feb": "FEB",
    "lnb_espoirs": "LNB_ESPOIRS",
    "mkl": "MKL",
    # Global/International
    "osba": "OSBA",
    "playhq": "PLAYHQ",
    "fiba_youth": "FIBA_YOUTH",
    "fiba": "FIBA_YOUTH",
    "fiba_livestats": "FIBA_LIVESTATS",
    # US Multi-State Platforms
    "sblive": "SBLIVE",
    "bound": "BOUND",
    "wsn": "WSN",
    "psal": "PSAL",
    "mn_hub": "MN_HUB",
    "rankone": "RANK_ONE",
    "nepsac": "NEPSAC",
    # US State Associations - Southeast
    "fhsaa": "FHSAA",
    "ghsa": "GHSA",
    "nchsaa": "NCHSAA",
    "vhsl": "VHSL",
    "tssaa": "TSSAA",
    "schsl": "SCHSL",
    "ahsaa": "AHSAA",
    "lhsaa": "LHSAA",
    "mhsaa_ms": "MHSAA_MS",
    "aaa_ar": "AAA_AR",
    "khsaa": "KHSAA",
    "wvssac": "WVSSAC",
    # US State Associations - Northeast
    "ciac": "CIAC",
    "diaa": "DIAA",
    "miaa": "MIAA",
    "mpssaa": "MPSSAA",
    "mpa": "MPA",
    "nhiaa": "NHIAA",
    "njsiaa": "NJSIAA",
    "piaa": "PIAA",
    "riil": "RIIL",
    "vpa": "VPA",
    # US State Associations - Midwest
    "ihsaa": "IHSAA",
    "ohsaa": "OHSAA",
    "kshsaa": "KSHSAA",
    "mhsaa_mi": "MHSAA_MI",
    "mshsaa": "MSHSAA",
    "ndhsaa": "NDHSAA",
    "nsaa": "NSAA",
    # US State Associations - Southwest/West
    "chsaa": "CHSAA",
    "nmaa": "NMAA",
    "ossaa": "OSSAA",
    "uhsaa": "UHSAA",
    "asaa": "ASAA",
    "mhsa": "MHSA",
    "whsaa": "WHSAA",
    "dciaa": "DCIAA",
    "hhsaa": "HHSAA",
    "oia": "OIA",
    # Event Platforms
    "exposure_events": "EXPOSURE_EVENTS",
    "tourneymachine": "TOURNEYMACHINE",
    # State-specific platforms
    "texas_hoops": "TEXAS_HOOPS",
    "cifsshome": "CIFSSHOME",  # California CIF-SS
    "uil_brackets": "UIL_BRACKETS",  # Texas UIL
    # Canada
    "npa": "NPA",
}


# Per-source type classification
SOURCE_TYPES = {
    # Circuits
    "eybl": "CIRCUIT",
    "eybl_girls": "CIRCUIT",
    "three_ssb": "CIRCUIT",
    "three_ssb_girls": "CIRCUIT",
    "uaa": "CIRCUIT",
    "uaa_girls": "CIRCUIT",
    "ote": "CIRCUIT",
    "grind_session": "CIRCUIT",
    # European Leagues
    "angt": "LEAGUE",
    "nbbl": "LEAGUE",
    "feb": "LEAGUE",
    "lnb_espoirs": "LEAGUE",
    "mkl": "LEAGUE",
    # State/Prep/Platform
    "nepsac": "PREP",
    "psal": "ASSOCIATION",
    "mn_hub": "ASSOCIATION",
    "wsn": "PLATFORM",
    "sblive": "PLATFORM",
    "bound": "PLATFORM",
    "rankone": "PLATFORM",
    # State Associations
    "fhsaa": "ASSOCIATION",
    "ghsa": "ASSOCIATION",
    "nchsaa": "ASSOCIATION",
    "vhsl": "ASSOCIATION",
    "tssaa": "ASSOCIATION",
    "schsl": "ASSOCIATION",
    "ahsaa": "ASSOCIATION",
    "lhsaa": "ASSOCIATION",
    "mhsaa_ms": "ASSOCIATION",
    "aaa_ar": "ASSOCIATION",
    "khsaa": "ASSOCIATION",
    "wvssac": "ASSOCIATION",
    "ciac": "ASSOCIATION",
    "diaa": "ASSOCIATION",
    "miaa": "ASSOCIATION",
    "mpssaa": "ASSOCIATION",
    "mpa": "ASSOCIATION",
    "nhiaa": "ASSOCIATION",
    "njsiaa": "ASSOCIATION",
    "piaa": "ASSOCIATION",
    "riil": "ASSOCIATION",
    "vpa": "ASSOCIATION",
    "ihsaa": "ASSOCIATION",
    "ohsaa": "ASSOCIATION",
    "kshsaa": "ASSOCIATION",
    "mhsaa_mi": "ASSOCIATION",
    "mshsaa": "ASSOCIATION",
    "ndhsaa": "ASSOCIATION",
    "nsaa": "ASSOCIATION",
    "chsaa": "ASSOCIATION",
    "nmaa": "ASSOCIATION",
    "ossaa": "ASSOCIATION",
    "uhsaa": "ASSOCIATION",
    "asaa": "ASSOCIATION",
    "mhsa": "ASSOCIATION",
    "whsaa": "ASSOCIATION",
    "dciaa": "ASSOCIATION",
    "hhsaa": "ASSOCIATION",
    "oia": "ASSOCIATION",
    "uil_brackets": "ASSOCIATION",
    "cifsshome": "ASSOCIATION",
    # Event aggregators
    "exposure_events": "EVENT",
    "tourneymachine": "EVENT",
    # Global feeds
    "osba": "LEAGUE",
    "playhq": "PLATFORM",
    "fiba_youth": "LEAGUE",
    "fiba": "LEAGUE",
    "fiba_livestats": "LEAGUE",
    "npa": "PREP",
    "texas_hoops": "PLATFORM",
}


def normalize_gender(raw: str | None) -> str:
    """
    Normalize gender string to canonical M/F.

    Args:
        raw: Raw gender string (e.g., "girls", "women", "f", "boys", "men", "m")

    Returns:
        Normalized gender: "M" or "F"
    """
    if not raw:
        return "M"
    raw = raw.strip().lower()
    if raw in {"f", "girls", "women", "w", "female"}:
        return "F"
    return "M"


def normalize_level(source_key: str, age_group: str | None) -> str:
    """
    Normalize competition level to canonical categories.

    Args:
        source_key: Source identifier (e.g., "eybl", "nepsac")
        age_group: Age group string (e.g., "U17", "U18")

    Returns:
        Normalized level: HS, PREP, U14, U15, U16, U17, U18, U21
    """
    # Age group takes priority if present
    if age_group and age_group.upper().startswith("U"):
        return age_group.upper()

    # Prep schools
    if source_key in {"nepsac", "npa"}:
        return "PREP"

    # State associations are HS
    if source_key in {
        "psal",
        "mn_hub",
        "fhsaa",
        "ghsa",
        "nchsaa",
        "vhsl",
        "tssaa",
        "schsl",
        "ahsaa",
        "lhsaa",
        "mhsaa_ms",
        "aaa_ar",
        "khsaa",
        "wvssac",
        "ciac",
        "diaa",
        "miaa",
        "mpssaa",
        "mpa",
        "nhiaa",
        "njsiaa",
        "piaa",
        "riil",
        "vpa",
        "ihsaa",
        "ohsaa",
        "kshsaa",
        "mhsaa_mi",
        "mshsaa",
        "ndhsaa",
        "nsaa",
        "chsaa",
        "nmaa",
        "ossaa",
        "uhsaa",
        "asaa",
        "mhsa",
        "whsaa",
        "dciaa",
        "hhsaa",
        "oia",
    }:
        return "HS"

    # National circuits are HS
    if source_key in {"eybl", "eybl_girls", "three_ssb", "three_ssb_girls", "uaa", "uaa_girls", "ote", "grind_session"}:
        return "HS"

    # Default
    return "HS"


def map_source_meta(source_key: str) -> Tuple[str, str]:
    """
    Map source key to circuit name and source type.

    Args:
        source_key: Source identifier (e.g., "eybl", "fhsaa")

    Returns:
        Tuple of (circuit_name, source_type)
    """
    circuit = CIRCUIT_KEYS.get(source_key, source_key.upper())
    stype = SOURCE_TYPES.get(source_key, "PLATFORM")
    return circuit, stype
