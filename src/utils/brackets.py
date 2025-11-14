"""
Shared Bracket Parsing Utilities

Provides reusable functions for parsing tournament brackets across state associations.
Handles common patterns: seed extraction, team ID canonicalization, HTML parsing, metadata extraction.

Usage:
    from src.utils.brackets import extract_team_seed, canonical_team_id, parse_bracket_tables_and_divs
    from src.utils.brackets import infer_round, extract_venue, extract_tipoff, parse_block_meta
"""

import re
from datetime import datetime
from typing import Dict, Iterator, Optional, Tuple, List

# Import from parent utils module
from . import parse_int, get_text_or_none


# Seed extraction patterns (handles multiple formats)
SEED_PATTERNS = [
    re.compile(r"\((\d{1,2})\)"),          # "Lincoln (5)"
    re.compile(r"#\s?(\d{1,2})"),          # "Lincoln #5"
    re.compile(r"\bNo\.?\s?(\d{1,2})\b"),  # "Lincoln No. 5"
]


def extract_team_seed(text: str) -> Tuple[str, Optional[int]]:
    """
    Extract team name and seed from text containing both.

    Handles multiple formats:
    - "Team Name (5)" → ("Team Name", 5)
    - "Team Name #5" → ("Team Name", 5)
    - "Team Name No. 5" → ("Team Name", 5)
    - "Team Name" → ("Team Name", None)

    Args:
        text: Team name with optional seed indicator

    Returns:
        Tuple of (clean_team_name, seed_number_or_none)
    """
    s = (text or "").strip()

    for pat in SEED_PATTERNS:
        m = pat.search(s)
        if m:
            seed = int(m.group(1))
            # Remove seed pattern and clean up
            name = pat.sub("", s).strip(" -–")
            return name, seed

    return s, None


def canonical_team_id(prefix: str, name: str) -> str:
    """
    Create canonical team ID from team name.

    Ensures consistent IDs across parsing:
    - Lowercases
    - Replaces non-alphanumeric with underscores
    - Removes duplicate underscores
    - Trims leading/trailing underscores

    Args:
        prefix: State/source prefix (e.g., "cif_ss", "uil_tx")
        name: Team name to canonicalize

    Returns:
        Canonical ID: "{prefix}_{slug}"

    Examples:
        canonical_team_id("cif_ss", "De La Salle") → "cif_ss_de_la_salle"
        canonical_team_id("uil_tx", "South Grand Prairie") → "uil_tx_south_grand_prairie"
    """
    # Convert to lowercase, replace non-alphanumeric with underscores
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower().strip())
    # Remove duplicate underscores and trim
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"{prefix}_{slug}"


def parse_bracket_tables_and_divs(soup) -> Iterator[Tuple[str, str, Optional[int], Optional[int]]]:
    """
    Parse bracket data from HTML tables and divs.

    Handles two common bracket layouts:
    1. Table-based: <table> with rows containing team names and scores
    2. Div-based: <div class="bracket|matchup|game"> with team/score elements

    Args:
        soup: BeautifulSoup parsed HTML

    Yields:
        Tuples of (team1_name, team2_name, score1, score2)
        Scores may be None if game hasn't been played yet
    """
    # Strategy 1: Table-based brackets
    tables = soup.find_all("table")
    for t in tables:
        rows = t.find_all("tr")
        for r in rows[1:]:  # Skip header row
            cells = r.find_all(["td", "th"])
            texts: List[str] = [get_text_or_none(c) or "" for c in cells]

            # Find team names (longest non-digit tokens)
            teams = [x for x in texts if len(x) > 2 and not x.isdigit()]

            if len(teams) >= 2:
                team1, _ = extract_team_seed(teams[0])
                team2, _ = extract_team_seed(teams[1])

                # Extract scores (first two integers found)
                s1 = s2 = None
                for txt in texts:
                    val = parse_int(txt)
                    if val is not None:
                        if s1 is None:
                            s1 = val
                        elif s2 is None:
                            s2 = val
                            break

                if team1 and team2:  # Both teams must be present
                    yield (team1, team2, s1, s2)

    # Strategy 2: Div-based brackets
    divs = soup.find_all("div")
    for d in divs:
        cls = " ".join(d.get("class", [])).lower()

        # Look for bracket-related classes
        if any(k in cls for k in ["bracket", "matchup", "game", "round", "playoff", "tournament"]):
            teams = d.find_all(class_=re.compile(r"team", re.I))
            scores = d.find_all(class_=re.compile(r"score", re.I))

            if len(teams) >= 2:
                t1 = get_text_or_none(teams[0]) or ""
                t2 = get_text_or_none(teams[1]) or ""
                team1, _ = extract_team_seed(t1)
                team2, _ = extract_team_seed(t2)

                # Extract scores from score elements
                s1 = s2 = None
                if len(scores) >= 2:
                    s1 = parse_int(get_text_or_none(scores[0]))
                    s2 = parse_int(get_text_or_none(scores[1]))

                if team1 and team2:  # Both teams must be present
                    yield (team1, team2, s1, s2)


# ==============================================================================
# Metadata Extraction Helpers (Phase 18)
# ==============================================================================

# Round name mapping patterns
ROUND_MAP = {
    r"\bfirst\s*round\b": "First Round",
    r"\bround\s*of\s*32\b": "Round of 32",
    r"\bround\s*of\s*16\b|\bsweet\s*16\b": "Round of 16",
    r"\bquarter[-\s]*finals?\b": "Quarterfinal",
    r"\bsemi[-\s]*finals?\b|\bsemis?\b": "Semifinal",
    r"\b(final|championship)\b": "Final",
    r"\b(consolation)\b": "Consolation",
}

# Time parsing pattern (12:30 PM, 7:00pm, etc)
_TIME_RX = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{2})\s*(?P<ampm>[ap]\.?m\.?)", re.I)

# Date parsing pattern (January 15, 2025 or Jan 15)
_DATE_RX = re.compile(r"(?P<mon>\b\w+\b)\s+(?P<day>\d{1,2})(?:,\s*(?P<yr>\d{4}))?", re.I)


def infer_round(text: str) -> Optional[str]:
    """
    Infer tournament round from text description.

    Handles multiple formats:
    - "First Round" → "First Round"
    - "Quarterfinals" → "Quarterfinal"
    - "Semi-Finals" → "Semifinal"
    - "Championship" → "Final"
    - "Final Four" → "Semifinal"

    Args:
        text: Text containing round information

    Returns:
        Standardized round name or None if not found

    Examples:
        >>> infer_round("First Round - Region 1")
        'First Round'
        >>> infer_round("State Semi-Finals")
        'Semifinal'
    """
    if not text:
        return None

    txt = text.lower()

    # Try each pattern
    for pattern, label in ROUND_MAP.items():
        if re.search(pattern, txt):
            return label

    # Fallback special cases
    if "final four" in txt:
        return "Semifinal"

    return None


def extract_venue(text: str) -> Optional[str]:
    """
    Extract venue/location from text.

    Handles multiple formats:
    - "at Madison Square Garden"
    - "Venue: Target Center"
    - "Location: University of Dayton Arena"

    Args:
        text: Text containing venue information

    Returns:
        Venue name or None if not found

    Examples:
        >>> extract_venue("at Madison Square Garden | 7:00 PM")
        'Madison Square Garden'
        >>> extract_venue("Venue: UD Arena")
        'UD Arena'
    """
    if not text:
        return None

    # Common venue indicators
    m = re.search(r"(?:at|venue:|location:)\s*([^|,;•\n]+)", text, re.I)
    if m:
        return m.group(1).strip()

    return None


def extract_tipoff(text: str, default_year: Optional[int] = None) -> Optional[datetime]:
    """
    Extract tipoff datetime from text.

    Handles multiple formats:
    - "7:00 PM" → datetime with today's date
    - "January 15, 2025 at 7:00 PM" → full datetime
    - "Jan 15 7:00pm" → datetime with default_year or current year

    Args:
        text: Text containing date/time information
        default_year: Year to use if not specified in text

    Returns:
        datetime object or None if time not found

    Examples:
        >>> extract_tipoff("Game time: 7:30 PM")
        datetime.datetime(2025, 11, 12, 19, 30)  # today's date
        >>> extract_tipoff("March 15 at 6:00pm", default_year=2025)
        datetime.datetime(2025, 3, 15, 18, 0)
    """
    if not text:
        return None

    # Extract time (required)
    tm = _TIME_RX.search(text)
    if not tm:
        return None

    h = int(tm.group("h"))
    m = int(tm.group("m"))
    ampm = tm.group("ampm").lower()

    # Convert to 24-hour format
    if "p" in ampm and h < 12:
        h += 12
    if "a" in ampm and h == 12:
        h = 0

    # Extract date (optional)
    dt = datetime.now()
    dm = _DATE_RX.search(text)

    if dm:
        try:
            year = int(dm.group("yr")) if dm.group("yr") else (default_year or dt.year)
            month_str = dm.group("mon")
            day = int(dm.group("day"))

            # Parse full date
            dt = datetime.strptime(f"{month_str} {day} {year} {h}:{m}", "%B %d %Y %H:%M")
            return dt
        except Exception:
            # Try abbreviated month format
            try:
                dt = datetime.strptime(f"{month_str} {day} {year} {h}:{m}", "%b %d %Y %H:%M")
                return dt
            except Exception:
                pass

    # Fallback: use today's date with parsed time
    return dt.replace(hour=h, minute=m, second=0, microsecond=0)


def extract_game_meta(block_text: str, year: Optional[int] = None) -> Dict[str, str]:
    """
    Extract all available metadata from a block of text.

    Combines round, venue, and tipoff extraction into a single call.

    Args:
        block_text: Text block containing game metadata
        year: Default year for date parsing

    Returns:
        Dict with keys:
            - "round": Standardized round name (if found)
            - "venue": Venue name (if found)
            - "tipoff_local_iso": ISO 8601 datetime string (if found)

    Examples:
        >>> extract_game_meta("Quarterfinal at Madison Square Garden | March 15, 2025 7:00 PM")
        {'round': 'Quarterfinal', 'venue': 'Madison Square Garden', 'tipoff_local_iso': '2025-03-15T19:00:00'}
    """
    meta = {}

    # Extract round
    r = infer_round(block_text)
    if r:
        meta["round"] = r

    # Extract venue
    v = extract_venue(block_text)
    if v:
        meta["venue"] = v

    # Extract tipoff
    t = extract_tipoff(block_text, default_year=year)
    if t:
        meta["tipoff_local_iso"] = t.isoformat()

    return meta


def parse_block_meta(soup, year: Optional[int] = None) -> Dict[str, str]:
    """
    Parse metadata from a BeautifulSoup block.

    Joins all text from the soup block and extracts metadata.

    Args:
        soup: BeautifulSoup element (table, div, or full page)
        year: Default year for date parsing

    Returns:
        Dict with available metadata keys (round, venue, tipoff_local_iso)

    Examples:
        >>> from bs4 import BeautifulSoup
        >>> html = '<div>Semifinal at Target Center | Jan 20 6:00 PM</div>'
        >>> soup = BeautifulSoup(html, 'html.parser')
        >>> parse_block_meta(soup, year=2025)
        {'round': 'Semifinal', 'venue': 'Target Center', 'tipoff_local_iso': '2025-01-20T18:00:00'}
    """
    # Join all text from the block
    block_text = " ".join(soup.stripped_strings)
    return extract_game_meta(block_text, year=year)
