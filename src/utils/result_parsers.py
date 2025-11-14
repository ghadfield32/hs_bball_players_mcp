"""
Shared Result Parsers

Reusable parsers for different state data source formats.
Enables single parser to serve multiple states with just config + regex tweaks.

Parser Types:
    - parse_html_results: Extract games from text result lines (IHSAA pattern)
    - parse_pdf_results: Extract games from text-based PDFs (KHSAA pattern)
"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from pathlib import Path


def parse_html_results(
    html: str,
    state: str,
    year: int,
    result_regex: Optional[str] = None
) -> List[Dict]:
    """
    Parse game results from HTML text lines.

    Handles IHSAA-style result pages where games are listed as:
    "Regional 1 Championship | Penn 73, Chesterton 60"
    "Semi-State | Carmel 67, Ben Davis 54"

    Args:
        html: HTML content
        state: State code (e.g., "IN")
        year: Tournament year
        result_regex: Custom regex pattern (or use default IHSAA pattern)

    Returns:
        List of game dicts with team names, scores, round info
    """
    # Default IHSAA pattern: "Round Name | Team A 73, Team B 60"
    if not result_regex:
        result_regex = (
            r"(?P<round>.+?)\s+\|\s+"
            r"(?P<team_a>.+?)\s+(?P<score_a>\d+),\s+"
            r"(?P<team_b>.+?)\s+(?P<score_b>\d+)"
        )

    pattern = re.compile(result_regex, re.IGNORECASE)
    soup = BeautifulSoup(html, "lxml")
    games = []

    # Search in all text elements (p, div, li, etc.)
    for element in soup.find_all(["p", "div", "li", "span"]):
        text = " ".join(element.get_text(strip=True).split())

        match = pattern.search(text)
        if not match:
            continue

        try:
            game = {
                "state": state.upper(),
                "year": year,
                "round": match.group("round").strip(),
                "team_a": match.group("team_a").strip(),
                "score_a": int(match.group("score_a")),
                "team_b": match.group("team_b").strip(),
                "score_b": int(match.group("score_b")),
                "source_type": "HTML_RESULTS"
            }
            games.append(game)
        except (ValueError, AttributeError) as e:
            # Skip malformed matches
            continue

    return games


def parse_pdf_results(
    pdf_content: bytes,
    state: str,
    year: int,
    result_regex: Optional[str] = None,
    page_range: Optional[tuple] = None
) -> List[Dict]:
    """
    Parse game results from text-based PDF.

    Handles KHSAA-style PDFs where game results are text lines:
    "Regional 1 - Game 1: Team A 73, Team B 60"
    "Sweet 16 Quarterfinal: Team C 85 vs Team D 78"

    Requires: pdfplumber

    Args:
        pdf_content: PDF file bytes
        state: State code (e.g., "KY")
        year: Tournament year
        result_regex: Custom regex pattern
        page_range: Optional (start, end) page numbers to parse

    Returns:
        List of game dicts with team names, scores, round info
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber required for PDF parsing. "
            "Install with: pip install pdfplumber"
        )

    # Default KHSAA pattern: "Regional 1 - Game 1: Team A 73, Team B 60"
    if not result_regex:
        result_regex = (
            r"(?P<round>Regional \d+.*?|Sweet 16.*?|Semi[- ]?State.*?)"
            r"(?:Game \d+)?[:\-]?\s+"
            r"(?P<team_a>.+?)\s+(?P<score_a>\d+)"
            r"(?:\s*(?:vs|,|-)\s*)"
            r"(?P<team_b>.+?)\s+(?P<score_b>\d+)"
        )

    pattern = re.compile(result_regex, re.IGNORECASE)
    games = []

    # Parse PDF from bytes
    import io
    pdf_file = io.BytesIO(pdf_content)

    with pdfplumber.open(pdf_file) as pdf:
        pages = pdf.pages
        if page_range:
            start, end = page_range
            pages = pages[start:end]

        for page in pages:
            text = page.extract_text() or ""

            for line in text.splitlines():
                line = " ".join(line.split())  # Normalize whitespace

                match = pattern.search(line)
                if not match:
                    continue

                try:
                    game = {
                        "state": state.upper(),
                        "year": year,
                        "round": match.group("round").strip(),
                        "team_a": match.group("team_a").strip(),
                        "score_a": int(match.group("score_a")),
                        "team_b": match.group("team_b").strip(),
                        "score_b": int(match.group("score_b")),
                        "source_type": "PDF"
                    }
                    games.append(game)
                except (ValueError, AttributeError):
                    continue

    return games


def normalize_game_dict(game: Dict, state_config) -> Dict:
    """
    Normalize parsed game dict to standard Game model format.

    Converts simple parser output to full Game object schema.

    Args:
        game: Raw game dict from parser
        state_config: StateSourceConfig for metadata

    Returns:
        Normalized game dict ready for Game model
    """
    # Generate game ID
    team_a_slug = game["team_a"].lower().replace(" ", "_")
    team_b_slug = game["team_b"].lower().replace(" ", "_")
    game_id = f"{game['state'].lower()}_{game['year']}_{team_a_slug}_vs_{team_b_slug}"

    # Determine winner
    winner = game["team_a"] if game["score_a"] > game["score_b"] else game["team_b"]

    return {
        "game_id": game_id,
        "state": game["state"],
        "year": game["year"],
        "round_label": game.get("round", "State Tournament"),
        "home_team": game["team_a"],
        "away_team": game["team_b"],
        "home_score": game["score_a"],
        "away_score": game["score_b"],
        "winner": winner,
        "game_type": "playoff",
        "source_type": game.get("source_type", "UNKNOWN"),
        "association": state_config.association,
    }


# Regex patterns library (can be referenced by state configs)
REGEX_PATTERNS = {
    "ihsaa": r"(?P<round>.+?)\s+\|\s+(?P<team_a>.+?)\s+(?P<score_a>\d+),\s+(?P<team_b>.+?)\s+(?P<score_b>\d+)",
    "khsaa": r"(?P<round>Regional \d+.*?|Sweet 16.*?)[:\-]?\s+(?P<team_a>.+?)\s+(?P<score_a>\d+).*?(?P<team_b>.+?)\s+(?P<score_b>\d+)",
    # Add more patterns as discovered
}
