"""
State Coverage Registry - Single Source of Truth for Real Data Verification

This module tracks which states have verified real data and which seasons
have been successfully probed. Only states/seasons with confirmed real data
from live HTTP probes should be marked as verified.

NO SYNTHETIC DATA - All coverage is based on actual probe results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type, Any

from src.datasources.us import (
    # Phase 17 - High Impact
    CaliforniaCIFSSDataSource,
    TexasUILDataSource,
    FloridaFHSAADataSource,
    GeorgiaGHSADataSource,
    OhioOHSAADataSource,
    PennsylvaniaPIAADataSource,
    NewYorkNYSPHSAADataSource,
    # Phase 19
    IHSADataSource,
    NCHSAADataSource,
    VirginiaVHSLDataSource,
    WashingtonWIAADataSource,
    MassachusettsMiaaDataSource,
    # Phase 20
    IndianaIHSAADataSource,
    WisconsinWIAADataSource,
    MissouriMSHSAADataSource,
    MarylandMPSSAADataSource,
    MinnesotaMSHSLDataSource,
    # Phase 21
    MichiganMHSAADataSource,
    NewJerseyNJSIAADataSource,
    ArizonaAIADataSource,
    ColoradoCHSAADataSource,
    TennesseeTSSAADataSource,
    KentuckyKHSAADataSource,
    ConnecticutCIACDataSource,
    SouthCarolinaSCHSLDataSource,
    # Phase 22
    AlabamaAHSAADataSource,
    LouisianaLHSAADataSource,
    OregonOSAADataSource,
    MississippiMHSAA_MSDataSource,
    KansasKSHSAADataSource,
    ArkansasAAADataSource,
    NebraskaNSAADataSource,
    SouthDakotaSDHSAADataSource,
    IdahoIHSAADataSource,
    UtahUHSAADataSource,
)


@dataclass
class StateCoverage:
    """
    Canonical configuration for a state's data source.

    This is REAL-DATA AWARE - only mark capabilities as True
    and add seasons to verified_seasons once probe script confirms
    real data extraction from live HTTP endpoints.

    Attributes:
        id: Internal source ID (e.g., "ahsaa", "cif_ss")
        abbrev: Two-letter state code (e.g., "AL", "CA")
        org: Organization name (e.g., "AHSAA", "CIF-SS")
        datasource_cls: Adapter class reference
        has_brackets: True only if probe confirmed bracket data
        has_schedules: True only if confirmed schedule data
        has_boxscores: True only if confirmed boxscore data
        has_rosters: True only if confirmed roster data
        verified_seasons: List of years with confirmed real data
        target_seasons: Seasons we aim to support (for tracking gaps)
        notes: Human-readable status/issues (404s, SSL, etc.)
    """
    id: str
    abbrev: str
    org: str
    datasource_cls: Type[Any]
    has_brackets: bool = False
    has_schedules: bool = False
    has_boxscores: bool = False
    has_rosters: bool = False
    verified_seasons: List[int] = field(default_factory=list)
    target_seasons: List[int] = field(default_factory=list)
    notes: Optional[str] = None


# Single source of truth for state adapter coverage
# Updated based on probe_state_adapter.py results
STATE_REGISTRY: Dict[str, StateCoverage] = {
    # Phase 17 - High Impact States
    "CA": StateCoverage(
        id="cif_ss",
        abbrev="CA",
        org="CIF-SS",
        datasource_cls=CaliforniaCIFSSDataSource,
        has_brackets=False,  # Probe showed 0 games; needs URL pattern fix
        notes="Some divisions work, D5A/D5AA return 404 for 2024. URL discovery needed.",
    ),
    "TX": StateCoverage(
        id="uil_tx",
        abbrev="TX",
        org="UIL",
        datasource_cls=TexasUILDataSource,
        has_brackets=False,
        notes="Real-data probe pending for 2024 season.",
    ),
    "FL": StateCoverage(
        id="fhsaa_fl",
        abbrev="FL",
        org="FHSAA",
        datasource_cls=FloridaFHSAADataSource,
        has_brackets=False,
        notes="Connection timeout/network errors observed. Needs investigation.",
    ),
    "GA": StateCoverage(
        id="ghsa",
        abbrev="GA",
        org="GHSA",
        datasource_cls=GeorgiaGHSADataSource,
        has_brackets=False,
        notes="404 errors on bracket URLs for 2024. URL pattern discovery needed.",
    ),
    "OH": StateCoverage(
        id="ohsaa",
        abbrev="OH",
        org="OHSAA",
        datasource_cls=OhioOHSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "PA": StateCoverage(
        id="piaa",
        abbrev="PA",
        org="PIAA",
        datasource_cls=PennsylvaniaPIAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "NY": StateCoverage(
        id="nysphsaa",
        abbrev="NY",
        org="NYSPHSAA",
        datasource_cls=NewYorkNYSPHSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),

    # Phase 19 States
    "IL": StateCoverage(
        id="ihsa",
        abbrev="IL",
        org="IHSA",
        datasource_cls=IHSADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "NC": StateCoverage(
        id="nchsaa",
        abbrev="NC",
        org="NCHSAA",
        datasource_cls=NCHSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "VA": StateCoverage(
        id="vhsl",
        abbrev="VA",
        org="VHSL",
        datasource_cls=VirginiaVHSLDataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "WA": StateCoverage(
        id="wiaa_wa",
        abbrev="WA",
        org="WIAA (WA)",
        datasource_cls=WashingtonWIAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "MA": StateCoverage(
        id="miaa",
        abbrev="MA",
        org="MIAA",
        datasource_cls=MassachusettsMiaaDataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),

    # Phase 20 States
    "IN": StateCoverage(
        id="ihsaa",
        abbrev="IN",
        org="IHSAA",
        datasource_cls=IndianaIHSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "WI": StateCoverage(
        id="wiaa",
        abbrev="WI",
        org="WIAA",
        datasource_cls=WisconsinWIAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "MO": StateCoverage(
        id="mshsaa",
        abbrev="MO",
        org="MSHSAA",
        datasource_cls=MissouriMSHSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "MD": StateCoverage(
        id="mpssaa",
        abbrev="MD",
        org="MPSSAA",
        datasource_cls=MarylandMPSSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "MN": StateCoverage(
        id="mshsl",
        abbrev="MN",
        org="MSHSL",
        datasource_cls=MinnesotaMSHSLDataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),

    # Phase 21 States
    "MI": StateCoverage(
        id="mhsaa_mi",
        abbrev="MI",
        org="MHSAA (MI)",
        datasource_cls=MichiganMHSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "NJ": StateCoverage(
        id="njsiaa",
        abbrev="NJ",
        org="NJSIAA",
        datasource_cls=NewJerseyNJSIAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "AZ": StateCoverage(
        id="aia",
        abbrev="AZ",
        org="AIA",
        datasource_cls=ArizonaAIADataSource,
        has_brackets=False,
        notes="404 errors on 2024 bracket URLs. URL pattern discovery needed.",
    ),
    "CO": StateCoverage(
        id="chsaa",
        abbrev="CO",
        org="CHSAA",
        datasource_cls=ColoradoCHSAADataSource,
        has_brackets=False,
        notes="404 errors on 2024 bracket URLs. URL pattern discovery needed.",
    ),
    "TN": StateCoverage(
        id="tssaa",
        abbrev="TN",
        org="TSSAA",
        datasource_cls=TennesseeTSSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "KY": StateCoverage(
        id="khsaa",
        abbrev="KY",
        org="KHSAA",
        datasource_cls=KentuckyKHSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "CT": StateCoverage(
        id="ciac",
        abbrev="CT",
        org="CIAC",
        datasource_cls=ConnecticutCIACDataSource,
        has_brackets=False,
        notes="SSL certificate verification failed. Needs SSL bypass or cert update.",
    ),
    "SC": StateCoverage(
        id="schsl",
        abbrev="SC",
        org="SCHSL",
        datasource_cls=SouthCarolinaSCHSLDataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),

    # Phase 22 - Priority 3B States
    "AL": StateCoverage(
        id="ahsaa",
        abbrev="AL",
        org="AHSAA",
        datasource_cls=AlabamaAHSAADataSource,
        has_brackets=True,  # ✅ VERIFIED with real probe
        verified_seasons=[2024],  # Probe found 154 games, 43 teams for 2023-24
        target_seasons=[2020, 2021, 2022, 2023, 2024],
        notes="✅ Bracket data verified via probe for 2023-24 boys season (154 games, 43 teams).",
    ),
    "LA": StateCoverage(
        id="lhsaa",
        abbrev="LA",
        org="LHSAA",
        datasource_cls=LouisianaLHSAADataSource,
        has_brackets=False,
        notes="Probe returned 0 games; all bracket URLs 404 for 2024. URL pattern discovery needed.",
    ),
    "OR": StateCoverage(
        id="osaa",
        abbrev="OR",
        org="OSAA",
        datasource_cls=OregonOSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "MS": StateCoverage(
        id="mhsaa_ms",
        abbrev="MS",
        org="MHSAA (MS)",
        datasource_cls=MississippiMHSAA_MSDataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "KS": StateCoverage(
        id="kshsaa",
        abbrev="KS",
        org="KSHSAA",
        datasource_cls=KansasKSHSAADataSource,
        has_brackets=False,
        notes="Probe returned 0 games; 404s on current URL pattern. URL discovery needed.",
    ),
    "AR": StateCoverage(
        id="aaa_ar",
        abbrev="AR",
        org="Arkansas Activities Association",
        datasource_cls=ArkansasAAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "NE": StateCoverage(
        id="nsaa",
        abbrev="NE",
        org="NSAA",
        datasource_cls=NebraskaNSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "SD": StateCoverage(
        id="sdhsaa",
        abbrev="SD",
        org="SDHSAA",
        datasource_cls=SouthDakotaSDHSAADataSource,
        has_brackets=False,
        notes="Probe returned 0 games; 404s for B/other classifications. URL discovery needed.",
    ),
    "ID": StateCoverage(
        id="ihsaa_id",
        abbrev="ID",
        org="IHSAA (ID)",
        datasource_cls=IdahoIHSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
    "UT": StateCoverage(
        id="uhsaa",
        abbrev="UT",
        org="UHSAA",
        datasource_cls=UtahUHSAADataSource,
        has_brackets=False,
        notes="Real-data probe pending.",
    ),
}


def get_state_config(abbrev: str) -> StateCoverage:
    """
    Retrieve state configuration from registry.

    Args:
        abbrev: Two-letter state code (case-insensitive)

    Returns:
        StateCoverage instance for the requested state

    Raises:
        KeyError: If state abbreviation not found in registry
    """
    try:
        return STATE_REGISTRY[abbrev.upper()]
    except KeyError as exc:
        available = ", ".join(sorted(STATE_REGISTRY.keys()))
        raise KeyError(
            f"Unknown state abbreviation: {abbrev!r}. "
            f"Available states: {available}"
        ) from exc


def list_verified_states() -> List[str]:
    """Return list of state abbreviations with verified real data."""
    return [
        abbrev for abbrev, cfg in STATE_REGISTRY.items()
        if cfg.has_brackets and cfg.verified_seasons
    ]


def get_coverage_summary() -> Dict[str, Any]:
    """
    Generate coverage summary statistics.

    Returns:
        Dict with counts of total states, verified states, and coverage gaps
    """
    total = len(STATE_REGISTRY)
    verified = len(list_verified_states())

    # Count states by issue type
    needs_url_discovery = sum(
        1 for cfg in STATE_REGISTRY.values()
        if "404" in (cfg.notes or "") or "URL" in (cfg.notes or "")
    )
    has_ssl_issues = sum(
        1 for cfg in STATE_REGISTRY.values()
        if "SSL" in (cfg.notes or "")
    )
    pending_probe = sum(
        1 for cfg in STATE_REGISTRY.values()
        if "pending" in (cfg.notes or "")
    )

    return {
        "total_states": total,
        "verified_states": verified,
        "unverified_states": total - verified,
        "coverage_pct": round(verified / total * 100, 1) if total > 0 else 0.0,
        "needs_url_discovery": needs_url_discovery,
        "has_ssl_issues": has_ssl_issues,
        "pending_probe": pending_probe,
    }
