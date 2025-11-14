"""
State Source Registry

Central registry classifying all 35 state associations by data source type.
Enables routing to appropriate parser without per-state custom code.

Source Types:
    - HTML_BRACKET: Static HTML bracket tables (AL, TX)
    - HTML_RESULTS: Plain text game result pages (IN, others)
    - PDF: Text-based PDF results (KY, others)
    - THIRD_PARTY: External platforms like MaxPreps (GA, NC, SC, TN, OH)
    - IMAGE: Image-only brackets requiring OCR (SC, rare)

Usage:
    from src.state_sources import STATE_SOURCES

    config = STATE_SOURCES["in"]
    if config.source_type == "HTML_RESULTS":
        games = parse_html_results(html, config)
"""

from dataclasses import dataclass, field
from typing import Literal, Dict, Optional

SourceType = Literal[
    "HTML_BRACKET",    # Static HTML bracket (AL, TX)
    "HTML_RESULTS",    # Text game result lines (IN)
    "PDF",             # Text-based PDF (KY)
    "THIRD_PARTY",     # MaxPreps, external platforms (GA, NC, OH)
    "IMAGE",           # Image-only brackets (SC)
    "JS_BRACKET",      # JavaScript-injected brackets requiring browser automation (MI)
    "UNKNOWN"          # Not yet classified
]


@dataclass
class StateSourceConfig:
    """Configuration for a single state data source."""

    code: str                    # Two-letter state code (lowercase)
    association: str             # Association name (e.g., "GHSA", "IHSAA")
    source_type: SourceType      # Classification for parser routing
    notes: str = ""              # Implementation notes
    urls: Dict[str, str] = field(default_factory=dict)  # URL templates by type

    # Optional: Custom parser hints
    result_regex: Optional[str] = None    # Regex pattern for result lines
    pdf_page_range: Optional[tuple] = None  # (start, end) pages to parse


# ============================================================================
# STATE SOURCE REGISTRY - Central classification of all 35 states
# ============================================================================

STATE_SOURCES: Dict[str, StateSourceConfig] = {
    # ========== WORKING STATES (HTML_BRACKET) ==========
    "al": StateSourceConfig(
        code="al",
        association="AHSAA",
        source_type="HTML_BRACKET",
        urls={
            "bracket": "https://www.ahsaa.com/sports/basketball/boys/brackets/{year}/{classification}"
        },
        notes="Static HTML bracket tables - VERIFIED WORKING"
    ),

    "tx": StateSourceConfig(
        code="tx",
        association="UIL",
        source_type="HTML_BRACKET",
        urls={
            "bracket": "https://www.uiltexas.org/basketball/state-bracket/{season}-{classification}-boys-basketball-state-results"
        },
        notes="Static HTML with season format (2023-2024) - VERIFIED WORKING"
    ),

    # ========== HTML_RESULTS STATES ==========
    "in": StateSourceConfig(
        code="in",
        association="IHSAA",
        source_type="HTML_RESULTS",
        urls={
            "results": "https://www.ihsaa.org/sports/boys/basketball/{season}-tournament?round={round}"
        },
        notes="Archived seasons (e.g. 2007-08) are HTML_RESULTS; 2023-24 returns 403 and likely needs Playwright or historical data only",
        result_regex=r"(?P<round>.+?)\s+\|\s+(?P<team_a>.+?)\s+(?P<score_a>\d+),\s+(?P<team_b>.+?)\s+(?P<score_b>\d+)"
    ),

    # ========== PDF STATES ==========
    "ky": StateSourceConfig(
        code="ky",
        association="KHSAA",
        source_type="PDF",
        urls={
            "results_pdf": "https://www.khsaa.org/basketball/boys/sweet16/{year}/boysstatebracket{year}.pdf"
        },
        notes="Historic PDFs available; 2024 Sweet 16 bracket appears to be 404, bracket largely via MaxPreps now",
        result_regex=r"(?P<round>Regional \d+.*?|Sweet 16.*?|Semi[- ]?State.*?)(?:Game \d+)?[:\-]?\s+(?P<team_a>.+?)\s+(?P<score_a>\d+)(?:\s*(?:vs|,|-)\s*)(?P<team_b>.+?)\s+(?P<score_b>\d+)"
    ),

    # ========== THIRD_PARTY / COMPLEX STATES ==========
    "ar": StateSourceConfig(
        code="ar",
        association="AAA",
        source_type="THIRD_PARTY",
        urls={
            "bracket": "https://www.si.com/high-school/arkansas/aaa"
        },
        notes="SI.com platform with dynamic bracket IDs - COMPLEX"
    ),

    "az": StateSourceConfig(
        code="az",
        association="AIA",
        source_type="PDF",
        urls={
            "tournament_pdf": "https://aiaonline.org/files/18212/2024-aia-state-basketball-tournament-guide.pdf"
        },
        notes="PDF-only brackets - no HTML available"
    ),

    "ca": StateSourceConfig(
        code="ca",
        association="CIF-SS",
        source_type="THIRD_PARTY",
        urls={
            "bracket": "https://www.cifss.org/brackets/{year}-boys-basketball/"
        },
        notes="JavaScript-rendered brackets + PDF embedding - COMPLEX"
    ),

    "ga": StateSourceConfig(
        code="ga",
        association="GHSA",
        source_type="THIRD_PARTY",
        urls={
            "bracket": "https://www.ghsa.net/{season}-ghsa-class-{classification}-boys-state-basketball-championship-bracket"
        },
        notes="Links to MaxPreps for brackets, no native HTML bracket - COMPLEX"
    ),

    "nc": StateSourceConfig(
        code="nc",
        association="NCHSAA",
        source_type="THIRD_PARTY",
        urls={
            "bracket": "https://www.nchsaa.org/championships/basketball-state-championships/"
        },
        notes="Championship pages link to MaxPreps - THIRD_PARTY"
    ),

    "oh": StateSourceConfig(
        code="oh",
        association="OHSAA",
        source_type="THIRD_PARTY",
        urls={
            "bracket": "https://www.ohsaa.org"
        },
        notes="Links to MaxPreps for brackets - THIRD_PARTY"
    ),

    "sc": StateSourceConfig(
        code="sc",
        association="SCHSL",
        source_type="IMAGE",
        urls={
            "bracket": "https://schsl.org"
        },
        notes="Bracket pages show single embedded image, not HTML - IMAGE (OCR required)"
    ),

    "tn": StateSourceConfig(
        code="tn",
        association="TSSAA",
        source_type="THIRD_PARTY",
        urls={
            "bracket": "https://tmsaa.tssaa.org"
        },
        notes="Brackets on separate tssaasports.com site - THIRD_PARTY"
    ),

    # ========== UNKNOWN CLASSIFICATION ==========
    # These states need URL discovery + HTML inspection
    "co": StateSourceConfig(
        code="co",
        association="CHSAA",
        source_type="IMAGE",
        urls={
            "bracket_page": "https://chsaanow.com/sports/boys-basketball/tournaments"
        },
        notes="Bracket pages embed images only (no HTML text) - OCR required, defer to Phase 2"
    ),
    "ct": StateSourceConfig(code="ct", association="CIAC", source_type="UNKNOWN", notes="SSL errors - needs investigation"),
    "fl": StateSourceConfig(code="fl", association="FHSAA", source_type="UNKNOWN", notes="Network errors - needs investigation"),
    "ia": StateSourceConfig(code="ia", association="IHSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "id": StateSourceConfig(code="id", association="IHSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "il": StateSourceConfig(code="il", association="IHSA", source_type="UNKNOWN", notes="Not yet probed"),
    "ks": StateSourceConfig(code="ks", association="KSHSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "la": StateSourceConfig(code="la", association="LHSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "ma": StateSourceConfig(code="ma", association="MIAA", source_type="UNKNOWN", notes="Not yet probed"),
    "md": StateSourceConfig(code="md", association="MPSSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "mi": StateSourceConfig(
        code="mi",
        association="MHSAA",
        source_type="JS_BRACKET",
        urls={
            "bracket_root": "https://my.mhsaa.com/Sports/MHSAA-Tournament-Brackets/BracketGroup/9/SportSeasonId/424465/Classification/{classification}"
        },
        notes="Bracket HTML and scores injected via JavaScript; main HTML only contains image maps and empty <div> containers. Requires Playwright/headless browser or reverse-engineered API. Defer to Phase 2."
    ),
    "mn": StateSourceConfig(code="mn", association="MSHSL", source_type="UNKNOWN", notes="Not yet probed"),
    "mo": StateSourceConfig(code="mo", association="MSHSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "ms": StateSourceConfig(code="ms", association="MHSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "ne": StateSourceConfig(code="ne", association="NSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "nj": StateSourceConfig(code="nj", association="NJSIAA", source_type="UNKNOWN", notes="Not yet probed"),
    "nv": StateSourceConfig(code="nv", association="NIAA", source_type="UNKNOWN", notes="Not yet probed"),
    "ny": StateSourceConfig(code="ny", association="NYSPHSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "or": StateSourceConfig(code="or", association="OSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "pa": StateSourceConfig(code="pa", association="PIAA", source_type="UNKNOWN", notes="Not yet probed"),
    "sd": StateSourceConfig(code="sd", association="SDHSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "ut": StateSourceConfig(code="ut", association="UHSAA", source_type="UNKNOWN", notes="Not yet probed"),
    "va": StateSourceConfig(code="va", association="VHSL", source_type="UNKNOWN", notes="Not yet probed"),
    "wa": StateSourceConfig(code="wa", association="WIAA", source_type="UNKNOWN", notes="Not yet probed"),
    "wi": StateSourceConfig(
        code="wi",
        association="WIAA",
        source_type="HTML_BRACKET",
        urls={
            "bracket": "https://www.wiaawi.org/Sports/Boys-Basketball/Tournament-Brackets"
        },
        notes="Static HTML brackets with division/sectional structure - similar pattern to AL/TX"
    ),
}


def get_states_by_type(source_type: SourceType) -> list[str]:
    """Get list of state codes for a specific source type."""
    return [
        code for code, config in STATE_SOURCES.items()
        if config.source_type == source_type
    ]


def get_source_type_summary() -> Dict[SourceType, int]:
    """Get count of states by source type."""
    summary = {}
    for config in STATE_SOURCES.values():
        summary[config.source_type] = summary.get(config.source_type, 0) + 1
    return summary


# Convenience accessors
HTML_BRACKET_STATES = get_states_by_type("HTML_BRACKET")
HTML_RESULTS_STATES = get_states_by_type("HTML_RESULTS")
PDF_STATES = get_states_by_type("PDF")
THIRD_PARTY_STATES = get_states_by_type("THIRD_PARTY")
IMAGE_STATES = get_states_by_type("IMAGE")
UNKNOWN_STATES = get_states_by_type("UNKNOWN")
