"""
WIAA (Wisconsin State Association) DataSource Adapter

Provides authoritative tournament brackets, seeds, scores, and championship results
for Wisconsin high school basketball.

**Data Authority**: WIAA is the source of truth for:
- Tournament brackets (5 classifications: Division 1, Division 2, Division 3, Division 4, Division 5)
- Seeds and matchups
- Game dates, times, locations
- Final scores and champions
- Historical tournament data

**Base URL**: https://www.wiaawi.org

**URL Pattern**:
```
Basketball: /sports/basketball/
Boys: /sports/basketball/boys/
Girls: /sports/basketball/girls/
Brackets: /brackets/{year}/
Playoffs: /playoffs/{year}/{classification}/
```

**Coverage**:
- Classifications: Division 1, Division 2, Division 3, Division 4, Division 5 (enrollment-based)
- 400+ member schools
- Boys and Girls tournaments
- All regions of Wisconsin

**Wisconsin Basketball Context**:
- 400+ schools
- Notable tradition (Devin Harris,Jon Leuer,Sam Dekker)
- WIAA manages all high school athletics in Wisconsin
- Enrollment-based classifications (Division 1 highest, Division 5 lowest)
- Regional tournaments → state championships

**Special Features**:
- Historical bracket data available
- Regional tournament structure
- Digital presence with bracket updates

**Limitations**:
- Player statistics NOT available (state associations focus on brackets/lineage)
- Regular season schedules typically on MaxPreps (separate source)
- Box scores rarely available

**Recommended Use**: WIAA provides official tournament brackets.
For player-level stats, combine with MaxPreps or other stats providers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ...models import (
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    Game,
    GameStatus,
    GameType,
    Player,
    PlayerGameStats,
    PlayerSeasonStats,
    Team,
    TeamLevel,
)
from ...utils import get_text_or_none, parse_html, parse_int
from ...utils.brackets import parse_bracket_tables_and_divs, canonical_team_id, extract_team_seed, parse_block_meta
from ..base_association import AssociationAdapterBase
from ...config import get_settings


def discover_wiaa_brackets(index_html: str, year: int, gender: str, base_url: str) -> List[str]:
    """
    Discover bracket URLs from WIAA index page (Session 8 - Phase 24: Layout-aware discovery).

    WIAA tournament structure (based on actual site layout):
    - Main tournament page lists links to division/sectional brackets
    - Brackets are in tables and nested links
    - Many are PDFs under /Portals/0/PDFs/basketball_boys/
    - Year is NOT always in URL (filename can be generic like bboys1.pdf)
    - Links may use "View Bracket", "Division 1", etc.

    Discovery strategy:
    - Use domain/path filtering (not year filtering)
    - Accept basketball-related paths
    - Accept bracket keywords OR PDF files
    - Log detailed statistics for debugging

    Args:
        index_html: HTML content of the main tournament page
        year: Tournament year (for context, not strict filtering)
        gender: "Boys" or "Girls"
        base_url: Base URL for constructing absolute URLs

    Returns:
        List of discovered bracket URLs (deduplicated, absolute)
    """
    from ...utils.logger import get_logger
    from urllib.parse import urljoin

    logger = get_logger(__name__)

    soup = parse_html(index_html)
    discovered_urls = set()

    # Debug: Count total links
    all_links = soup.find_all("a", href=True)
    print(f"[DEBUG DISCOVERY] Total links found: {len(all_links)}")
    logger.info(f"[WIAA DISCOVERY] Starting discovery on page with {len(all_links)} total links")

    # Session 8 - Phase 24: Layout-aware discovery for WIAA
    # Strategy: Use domain/path filtering instead of strict year filtering

    gender_lower = gender.lower()

    # Year variants for optional informational matching (not required)
    year_variants = [str(year), str(year-1), f"{year-1}-{str(year)[2:]}", f"{year}-{str(year+1)[2:]}"]

    # Debug counters
    stats = {
        "total": len(all_links),
        "has_href": 0,
        "internal_only": 0,
        "basketball_related": 0,
        "bracket_keywords": 0,
        "year_match": 0,
        "pdf_files": 0,
        "discovered": 0
    }

    for idx, link in enumerate(all_links):
        try:
            href = link.get("href", "")
            link_text = (link.get_text(strip=True) or "").strip()

            if not href:
                continue
            stats["has_href"] += 1

            # Make absolute URL
            if href.startswith("http"):
                # External link - only accept wiaawi.org
                if "wiaawi.org" not in href.lower():
                    continue
                full_url = href
            elif href.startswith("/"):
                full_url = base_url + href
            else:
                full_url = base_url + "/" + href

            stats["internal_only"] += 1

            href_lower = full_url.lower()
            text_lower = link_text.lower()

            # Filter 1: Basketball-related paths
            basketball_indicators = [
                "basketball",
                f"{gender_lower}-basketball",
                f"basketball_{gender_lower}",
                f"b{gender_lower[0]}oys" if gender_lower == "boys" else f"b{gender_lower[0]}irls",
                "/portals/0/pdfs/basketball"  # WIAA PDF path
            ]
            is_basketball = any(ind in href_lower for ind in basketball_indicators)

            if not is_basketball:
                continue
            stats["basketball_related"] += 1

            # Filter 2: Bracket-related content (RELAXED - keyword OR PDF)
            bracket_indicators = [
                "division", "div.", "d1", "d2", "d3", "d4", "d5",
                "sectional", "regional", "bracket", "tournament", "state",
                "view bracket", "playoff", "championship"
            ]
            has_bracket_keyword = any(ind in text_lower or ind in href_lower for ind in bracket_indicators)
            is_pdf = href_lower.endswith(".pdf")

            if not (has_bracket_keyword or is_pdf):
                continue

            if has_bracket_keyword:
                stats["bracket_keywords"] += 1
            if is_pdf:
                stats["pdf_files"] += 1

            # Optional: Check for year match (informational only, not filtering)
            year_match = any(y in href or y in link_text for y in year_variants)
            if year_match:
                stats["year_match"] += 1

            # Accept this URL
            discovered_urls.add(full_url)
            stats["discovered"] += 1

            # Safe print for Windows console (Session 8 - Phase 24)
            safe_text = link_text[:40].encode('ascii', 'replace').decode('ascii')
            safe_url = full_url.encode('ascii', 'replace').decode('ascii')
            print(f"  [DISCOVERED #{stats['discovered']}] {safe_text} -> {safe_url}")

        except Exception as e:
            # Skip links that cause errors (Unicode, parsing, etc.)
            print(f"  [ERROR] Link {idx+1} caused error: {e}")
            continue

    # Log discovery statistics
    print(f"[DEBUG DISCOVERY STATS] {stats}")
    logger.info(
        f"[WIAA DISCOVERY COMPLETE] "
        f"Total: {stats['total']} | "
        f"Has href: {stats['has_href']} | "
        f"Internal: {stats['internal_only']} | "
        f"Basketball: {stats['basketball_related']} | "
        f"Bracket keywords: {stats['bracket_keywords']} | "
        f"PDFs: {stats['pdf_files']} | "
        f"Year match: {stats['year_match']} | "
        f"**DISCOVERED: {stats['discovered']}**"
    )

    return sorted(list(discovered_urls))


def parse_halftime_html_to_games(
    html_content: str,
    year: int,
    gender: str,
    division: int,
    sections: List[int],
    html_url: str,
    adapter,  # WisconsinWIAADataSource instance
    logger
) -> List:
    """
    Parse a WIAA Halftime HTML bracket page into Game objects.

    Session 8 - Phase 24: HTML bracket parsing for Wisconsin (PRIMARY METHOD).

    **Why HTML Parsing**:
    - HTML contains extractable text (no OCR needed)
    - Proven pattern across multiple years (2020-2025)
    - More reliable than PDF OCR
    - Faster processing

    **Expected HTML Structure** (extracted text):
    ```
    Sectional #1
    Thu, Mar 6
    7:00 PM
    #1 Almond-Bancroft
    #16 Elcho
    @Some High School
    64-52

    #8 School C
    #9 School D
    70-63
    ```

    **Parsing Strategy**:
    1. Extract text from HTML using BeautifulSoup
    2. Parse line by line tracking context (date, time, location, sectional)
    3. Match seed/team patterns: `#N Team Name`
    4. Match score patterns: `NN-NN`
    5. Build games with accumulated context

    Args:
        html_content: Raw HTML content
        year: Tournament year
        gender: "Boys" or "Girls"
        division: Division number (1-5)
        sections: List of section numbers (e.g., [1, 2])
        html_url: Source HTML URL
        logger: Logger instance

    Returns:
        List of Game objects
    """
    import re
    from ...models.game import Game, GameStatus, GameType
    from ...models.source import DataQualityFlag
    from ...utils.brackets import canonical_team_id

    games = []

    try:
        # Extract text from HTML
        soup = parse_html(html_content)
        text = soup.get_text("\n", strip=True)
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

        if not lines:
            logger.warning(f"HTML contains no text", url=html_url)
            return []

        # Session 8 - Phase 24: Line-based parsing with context tracking

        # Context tracking
        current_sectional = sections[0] if sections else 1
        current_round = "Unknown Round"
        round_order = 0
        current_date = None
        current_time = None
        current_location = None
        pending_teams = []  # List of (seed, team_name) tuples

        # Regex patterns
        sectional_pattern = re.compile(r'Sectional\s+#?(\d+)', re.IGNORECASE)
        round_patterns = [
            (r'Regional\s+Quarterfinals?', 'Regional Quarterfinal', 1),
            (r'Regional\s+Semifinals?', 'Regional Semifinal', 2),
            (r'Regional\s+Finals?', 'Regional Final', 3),
            (r'Sectional\s+Semifinals?', 'Sectional Semifinal', 4),
            (r'Sectional\s+Finals?', 'Sectional Final', 5),
            (r'State\s+Quarterfinals?', 'State Quarterfinal', 6),
            (r'State\s+Semifinals?', 'State Semifinal', 7),
            (r'State\s+Championship|State\s+Finals?', 'State Championship', 8),
        ]

        # Patterns for parsing
        seed_team_pattern = re.compile(r'^#(\d+)\s+(.+)$')
        score_pattern = re.compile(r'^(\d{1,3})-(\d{1,3})(?:\s*\((OT|2OT|3OT)\))?$')
        location_pattern = re.compile(r'^@(.+)$')
        time_pattern = re.compile(r'^\d{1,2}:\d{2}\s*(AM|PM)$', re.IGNORECASE)
        date_pattern = re.compile(r'^([A-Z][a-z]{2}),\s+([A-Z][a-z]{2})\s+(\d{1,2})$')

        for line in lines:
            # Check for sectional header
            m = sectional_pattern.search(line)
            if m:
                current_sectional = int(m.group(1))
                print(f"  [HTML PARSE] Sectional: {current_sectional}")
                continue

            # Check for round headers
            for pattern, round_name, order in round_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    current_round = round_name
                    round_order = order
                    print(f"  [HTML PARSE] Round: {current_round}")
                    break

            # Check for date
            m = date_pattern.match(line)
            if m:
                current_date = line
                continue

            # Check for time
            m = time_pattern.match(line)
            if m:
                current_time = line
                continue

            # Check for location
            m = location_pattern.match(line)
            if m:
                current_location = m.group(1).strip()
                continue

            # Check for seed + team
            m = seed_team_pattern.match(line)
            if m:
                seed = int(m.group(1))
                team_name = m.group(2).strip()
                pending_teams.append((seed, team_name))
                continue

            # Check for score
            m = score_pattern.match(line)
            if m and len(pending_teams) >= 2:
                # We have a score and at least 2 teams - create a game
                score_a = int(m.group(1))
                score_b = int(m.group(2))
                overtime = m.group(3) if m.group(3) else None

                # Get last two teams
                seed_a, team_a = pending_teams[-2]
                seed_b, team_b = pending_teams[-1]

                # Create canonical team IDs
                team_a_id = canonical_team_id("wiaa", team_a)
                team_b_id = canonical_team_id("wiaa", team_b)

                # Create game ID
                season_str = f"{year-1}-{str(year)[2:]}"
                game_id = f"wiaa_{year}_div{division}_sec{current_sectional}_{team_a_id.split('_', 1)[1]}_vs_{team_b_id.split('_', 1)[1]}"

                # Create Game object
                notes = f"Div{division} Sec{current_sectional} {current_round} | Seeds: #{seed_a} vs #{seed_b}"
                if overtime:
                    notes += f" | OT: {overtime}"
                if current_location:
                    notes += f" | @{current_location}"

                game = Game(
                    game_id=game_id,
                    home_team_id=team_a_id,
                    home_team_name=team_a,
                    away_team_id=team_b_id,
                    away_team_name=team_b,
                    home_score=score_a,
                    away_score=score_b,
                    status=GameStatus.FINAL,
                    game_type=GameType.PLAYOFF,
                    league=f"WIAA Division {division} {current_round}",
                    season=season_str,
                    round=current_round,
                    data_source=adapter.create_data_source_metadata(
                        url=html_url,
                        quality_flag=DataQualityFlag.VERIFIED,
                        notes=notes,
                    ),
                )
                games.append(game)

                print(f"    [GAME] #{seed_a} {team_a} {score_a} vs #{seed_b} {team_b} {score_b} ({current_round})")

                # Clear pending teams after creating game
                pending_teams = []

        logger.info(
            f"Parsed Halftime HTML",
            games=len(games),
            division=division,
            sections=sections
        )

    except Exception as e:
        logger.error(f"Failed to parse HTML", url=html_url, error=str(e))
        import traceback
        traceback.print_exc()
        return []

    return games


def parse_halftime_pdf_to_games(
    pdf_bytes: bytes,
    year: int,
    gender: str,
    division: int,
    sections: List[int],
    pdf_url: str,
    logger
) -> List:
    """
    Parse a WIAA Halftime bracket PDF into Game objects.

    Session 8 - Phase 24: PDF bracket parsing for Wisconsin.

    **Expected PDF Structure**:
    ```
    Division 1 Sectional Tournament

    Regional Quarterfinals – Tuesday, February 27
    #1 School A 65, #8 School B 54
    #4 School C 72, #5 School D 68

    Regional Semifinals – Thursday, February 29
    #1 School A 58, #4 School C 55

    Regional Final – Saturday, March 2
    #1 School A 71, #2 School E 67
    ```

    **Parsing Strategy**:
    1. Extract all text from PDF using pdfplumber
    2. Detect round headers (e.g., "Regional Quarterfinals", "Sectional Final")
    3. Parse game lines with regex: "#N Team A NN, #M Team B MM"
    4. Create Game objects with proper metadata

    Args:
        pdf_bytes: Raw PDF bytes
        year: Tournament year
        gender: "Boys" or "Girls"
        division: Division number (1-5)
        sections: List of section numbers (e.g., [1, 2])
        pdf_url: Source PDF URL
        logger: Logger instance

    Returns:
        List of Game objects
    """
    import re
    import io
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed - cannot parse PDFs")
        return []

    from ...models.game import Game, GameStatus, GameType
    from ...models.source import DataQualityFlag
    from ...models.team import Team, TeamLevel
    from ...utils.brackets import canonical_team_id

    games = []
    teams_dict = {}

    try:
        # Extract text from PDF
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() or ""

        if not full_text.strip():
            logger.warning(f"PDF contains no extractable text", url=pdf_url)
            return []

        # Session 8 - Phase 24: Parse bracket games with round tracking
        lines = full_text.split('\n')

        # Round tracking
        current_round = "Unknown Round"
        round_order = 0

        # Round detection patterns
        round_patterns = [
            (r'Regional\s+Quarterfinals?', 'Regional Quarterfinal', 1),
            (r'Regional\s+Semifinals?', 'Regional Semifinal', 2),
            (r'Regional\s+Finals?', 'Regional Final', 3),
            (r'Sectional\s+Semifinals?', 'Sectional Semifinal', 4),
            (r'Sectional\s+Finals?', 'Sectional Final', 5),
            (r'State\s+Quarterfinals?', 'State Quarterfinal', 6),
            (r'State\s+Semifinals?', 'State Semifinal', 7),
            (r'State\s+Championship|State\s+Finals?', 'State Championship', 8),
        ]

        # Game line pattern: "#1 School Name 65, #8 Other School 54"
        # Also handles: "School Name 65, Other School 54" (no seeds)
        game_pattern = re.compile(
            r'(?:#(\d+)\s+)?'  # Optional seed #1
            r'([^0-9,]+?)\s+'  # Team A name (non-greedy until number)
            r'(\d+)'  # Score A
            r'\s*,\s*'  # Comma separator
            r'(?:#(\d+)\s+)?'  # Optional seed #2
            r'([^0-9,]+?)\s+'  # Team B name
            r'(\d+)'  # Score B
            r'\s*$'  # End of line
        )

        for line in lines:
            line_stripped = line.strip()

            # Check for round headers
            for pattern, round_name, order in round_patterns:
                if re.search(pattern, line_stripped, re.IGNORECASE):
                    current_round = round_name
                    round_order = order
                    print(f"  [PDF PARSE] Round: {current_round}")
                    break

            # Check for game line
            match = game_pattern.match(line_stripped)
            if match:
                seed_a, team_a, score_a, seed_b, team_b, score_b = match.groups()

                # Clean team names
                team_a = team_a.strip()
                team_b = team_b.strip()
                score_a = int(score_a)
                score_b = int(score_b)

                # Create canonical team IDs
                team_a_id = canonical_team_id("wiaa", team_a)
                team_b_id = canonical_team_id("wiaa", team_b)

                # Determine winner
                winner_name = team_a if score_a > score_b else team_b

                # Create game ID
                season_str = f"{year-1}-{str(year)[2:]}"
                game_id = f"wiaa_{year}_div{division}_{''.join(map(str,sections))}_{team_a_id.split('_', 1)[1]}_vs_{team_b_id.split('_', 1)[1]}"

                # Create Game object
                game = Game(
                    game_id=game_id,
                    home_team_id=team_a_id,
                    home_team_name=team_a,
                    away_team_id=team_b_id,
                    away_team_name=team_b,
                    home_score=score_a,
                    away_score=score_b,
                    status=GameStatus.FINAL,
                    game_type=GameType.PLAYOFF,
                    level="high_school_varsity",
                    league=f"WIAA Division {division} {current_round}",
                    season=season_str,
                    gender=gender.lower(),
                    data_source={
                        "source": "wiaa_halftime_pdf",
                        "url": pdf_url,
                        "quality_flag": DataQualityFlag.VERIFIED,
                        "round": current_round,
                        "round_order": round_order,
                        "division": division,
                        "sections": sections,
                    },
                )
                games.append(game)

                # Track teams
                for name, tid, seed in [(team_a, team_a_id, seed_a), (team_b, team_b_id, seed_b)]:
                    if tid not in teams_dict:
                        teams_dict[tid] = {
                            "team_id": tid,
                            "team_name": name,
                            "seed": int(seed) if seed else None,
                            "division": division,
                            "sections": sections,
                        }

                print(f"    [GAME] {team_a} {score_a} vs {team_b} {score_b} ({current_round})")

        logger.info(
            f"Parsed Halftime PDF",
            games=len(games),
            teams=len(teams_dict),
            division=division,
            sections=sections
        )

    except Exception as e:
        logger.error(f"Failed to parse PDF", url=pdf_url, error=str(e))
        return []

    return games


def generate_halftime_pdf_urls(year: int, gender: str) -> List[Dict[str, Any]]:
    """
    Generate Halftime PDF URLs using known pattern enumeration.

    Session 8 - Phase 24: Direct URL construction for Wisconsin Halftime PDFs.

    Since WIAA's Tournament pages use JavaScript to load brackets dynamically,
    we use pattern-based URL generation instead of HTML link discovery.

    **PDF URL Pattern**:
    ```
    https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/PDF/
    {year}_Basketball_{gender}_Div{N}_Sec{N}_{N}.pdf
    ```

    **WIAA Tournament Structure**:
    - 5 Divisions (Division 1, 2, 3, 4, 5)
    - Each division has 4-8 sectionals
    - Sectionals are numbered 1-8 (varies by division)

    Args:
        year: Tournament year
        gender: "Boys" or "Girls"

    Returns:
        List of dicts with:
        - url: Full PDF URL to test
        - year: Tournament year
        - gender: Gender
        - division: Division number (1-5)
        - sections: List of section numbers
        - method: "pattern_generated"
    """
    pdf_urls = []
    halftime_base = "https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/PDF"
    gender_formatted = gender.capitalize()

    # WIAA has 5 divisions, each with multiple sectionals
    # Division 1-2: 8 sectionals each
    # Division 3-5: 6-8 sectionals (varies by year)
    # We'll generate all possible combinations and let HTTP 404s filter out non-existent ones

    for division in range(1, 6):  # Divisions 1-5
        # For each division, try all possible sectional combinations
        # Sectionals are typically paired in brackets: Sec1_2, Sec3_4, etc.
        max_sectionals = 8 if division <= 2 else 6

        for sec1 in range(1, max_sectionals + 1, 2):  # Odd sections: 1, 3, 5, 7
            sec2 = sec1 + 1  # Paired section: 2, 4, 6, 8

            if sec2 > max_sectionals:
                # Handle odd number of sectionals (rare)
                pdf_url = f"{halftime_base}/{year}_Basketball_{gender_formatted}_Div{division}_Sec{sec1}.pdf"
            else:
                # Standard paired sectional bracket
                pdf_url = f"{halftime_base}/{year}_Basketball_{gender_formatted}_Div{division}_Sec{sec1}_{sec2}.pdf"

            pdf_urls.append({
                "url": pdf_url,
                "year": year,
                "gender": gender_formatted,
                "division": division,
                "sections": [sec1] if sec2 > max_sectionals else [sec1, sec2],
                "method": "pattern_generated"
            })

    return pdf_urls


def generate_halftime_html_urls(year: int, gender: str) -> List[Dict[str, Any]]:
    """
    Generate Halftime HTML bracket URLs using known pattern enumeration.

    Session 8 - Phase 24: HTML bracket parsing for Wisconsin (PRIMARY METHOD).

    **Why HTML instead of PDF**:
    - Halftime HTML endpoints contain extractable text (no OCR needed)
    - Same URL pattern as PDFs: `/HTML/` instead of `/PDF/`, `.html` instead of `.pdf`
    - Proven stable across multiple years (2020-2025)
    - Faster and more reliable than OCR

    **HTML URL Pattern**:
    ```
    https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/
    {year}_Basketball_{gender}_Div{N}_Sec{N}_{N}.html
    ```

    **Example URLs**:
    - 2025_Basketball_Boys_Div5_Sec1_2.html
    - 2023_Basketball_Boys_Div1_Sec1_2.html
    - 2020_Basketball_Boys_Div1_Sec1_2.html

    **WIAA Tournament Structure**:
    - 5 Divisions (Division 1, 2, 3, 4, 5)
    - Each division has 4-8 sectionals
    - Sectionals are numbered 1-8 (varies by division)

    Args:
        year: Tournament year
        gender: "Boys" or "Girls"

    Returns:
        List of dicts with:
        - url: Full HTML URL to test
        - year: Tournament year
        - gender: Gender
        - division: Division number (1-5)
        - sections: List of section numbers
        - method: "pattern_generated_html"
    """
    html_urls = []
    halftime_base = "https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML"
    gender_formatted = gender.capitalize()

    # WIAA has 5 divisions, each with multiple sectionals
    # Division 1-2: 8 sectionals each
    # Division 3-5: 6-8 sectionals (varies by year)
    # We'll generate all possible combinations and let HTTP 404s filter out non-existent ones

    for division in range(1, 6):  # Divisions 1-5
        # For each division, try all possible sectional combinations
        # Sectionals are typically paired in brackets: Sec1_2, Sec3_4, etc.
        max_sectionals = 8 if division <= 2 else 6

        for sec1 in range(1, max_sectionals + 1, 2):  # Odd sections: 1, 3, 5, 7
            sec2 = sec1 + 1  # Paired section: 2, 4, 6, 8

            if sec2 > max_sectionals:
                # Handle odd number of sectionals (rare)
                html_url = f"{halftime_base}/{year}_Basketball_{gender_formatted}_Div{division}_Sec{sec1}.html"
            else:
                # Standard paired sectional bracket
                html_url = f"{halftime_base}/{year}_Basketball_{gender_formatted}_Div{division}_Sec{sec1}_{sec2}.html"

            html_urls.append({
                "url": html_url,
                "year": year,
                "gender": gender_formatted,
                "division": division,
                "sections": [sec1] if sec2 > max_sectionals else [sec1, sec2],
                "method": "pattern_generated_html"
            })

    return html_urls


async def discover_halftime_pdfs(
    http_get_func,
    navigation_urls: List[str],
    year: int,
    gender: str,
    logger,
) -> List[Dict[str, Any]]:
    """
    Follow navigation URLs to discover Halftime bracket PDFs.

    Session 8 - Phase 24: Halftime PDF discovery for Wisconsin.

    WIAA uses halftime.wiaawi.org for hosting bracket PDFs. This function:
    1. Follows navigation URLs from the main WIAA site
    2. Extracts links to Halftime PDF brackets
    3. Parses PDF URL metadata (year, division, sections)

    **PDF URL Pattern**:
    ```
    https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/PDF/
    {year}_Basketball_{gender}_Div{N}_Sec{N}_{N}.pdf
    ```

    Examples:
    - 2025_Basketball_Boys_Div1_Sec3_4.pdf
    - 2024_Basketball_Girls_Div2_Sec1_2.pdf

    Args:
        http_get_func: Async HTTP GET function from adapter
        navigation_urls: List of discovered navigation URLs from main site
        year: Tournament year
        gender: "Boys" or "Girls"
        logger: Logger instance

    Returns:
        List of dicts with:
        - url: Full PDF URL
        - year: Extracted year from URL
        - gender: Gender from URL
        - division: Division number (1-5)
        - sections: List of section numbers
        - source_nav_url: Navigation URL that led to this PDF
    """
    import re
    from urllib.parse import urljoin

    discovered_pdfs = []
    halftime_base = "https://halftime.wiaawi.org"

    # PDF URL pattern: 2025_Basketball_Boys_Div1_Sec3_4.pdf
    # Captures: year, gender, division, and up to 2 section numbers
    pdf_pattern = re.compile(
        r'(?P<year>\d{4})_Basketball_(?P<gender>Boys|Girls)_'
        r'Div(?P<division>\d+)(?:_Sec(?P<sec1>\d+)(?:_(?P<sec2>\d+))?)?\.pdf',
        re.IGNORECASE
    )

    print(f"[DEBUG HALFTIME] Starting PDF discovery from {len(navigation_urls)} navigation URLs")

    for idx, nav_url in enumerate(navigation_urls):
        try:
            # Safe print for Windows console
            safe_url = nav_url.encode('ascii', 'replace').decode('ascii')
            print(f"[DEBUG HALFTIME] [{idx+1}/{len(navigation_urls)}] Fetching: {safe_url}")

            # Fetch navigation page
            status, content, headers = await http_get_func(nav_url, timeout=30.0)

            if status != 200:
                logger.debug(f"Failed to fetch nav URL: {nav_url}", status=status)
                continue

            # Handle compression (using same logic as main index)
            import gzip
            import zlib
            try:
                import brotli
                HAS_BROTLI = True
            except ImportError:
                HAS_BROTLI = False

            content_encoding = headers.get('content-encoding', '').lower()

            if content_encoding == 'br' and HAS_BROTLI:
                content = brotli.decompress(content)
            elif content_encoding == 'gzip' or content[:2] == b'\x1f\x8b':
                content = gzip.decompress(content)
            elif content_encoding == 'deflate' or content[:2] in (b'\x78\x9c', b'\x78\x01'):
                content = zlib.decompress(content)

            # Parse HTML to find Halftime PDF links
            html = content.decode("utf-8", errors="ignore")
            soup = parse_html(html)

            found_in_page = 0
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")

                # Check if it's a Halftime PDF link
                if "halftime.wiaawi.org" in href.lower() and ".pdf" in href.lower():
                    # Parse PDF URL metadata
                    match = pdf_pattern.search(href)
                    if match:
                        # Extract sections (can be 1 or 2)
                        sections = []
                        if match.group("sec1"):
                            sections.append(int(match.group("sec1")))
                        if match.group("sec2"):
                            sections.append(int(match.group("sec2")))

                        pdf_metadata = {
                            "url": href if href.startswith("http") else urljoin(halftime_base, href),
                            "year": int(match.group("year")),
                            "gender": match.group("gender"),
                            "division": int(match.group("division")),
                            "sections": sections,
                            "source_nav_url": nav_url
                        }

                        # Avoid duplicates
                        if not any(p["url"] == pdf_metadata["url"] for p in discovered_pdfs):
                            discovered_pdfs.append(pdf_metadata)
                            found_in_page += 1

                            # Safe print
                            safe_pdf_url = pdf_metadata["url"].encode('ascii', 'replace').decode('ascii')
                            print(
                                f"  [HALFTIME PDF #{len(discovered_pdfs)}] Div{pdf_metadata['division']} "
                                f"Sections{sections} -> {safe_pdf_url}"
                            )
                    else:
                        # Halftime PDF but doesn't match expected pattern - log for investigation
                        safe_href = href[:80].encode('ascii', 'replace').decode('ascii')
                        print(f"  [HALFTIME PDF] Non-standard pattern: {safe_href}")

            if found_in_page > 0:
                print(f"  [DEBUG HALFTIME] Found {found_in_page} PDFs in this page")

        except Exception as e:
            logger.warning(f"Error discovering PDFs from {nav_url}", error=str(e))
            safe_error = str(e).encode('ascii', 'replace').decode('ascii')
            print(f"  [ERROR] {safe_error}")
            continue

    print(f"[DEBUG HALFTIME] Discovery complete: {len(discovered_pdfs)} total bracket PDFs found")
    logger.info(
        f"Discovered Halftime bracket PDFs",
        count=len(discovered_pdfs),
        year=year,
        gender=gender
    )

    return discovered_pdfs


class WisconsinWIAADataSource(AssociationAdapterBase):
    """
    Wisconsin WIAA adapter.

    **PRIMARY PURPOSE**: Authoritative tournament bracket and postseason results.

    **COVERAGE**: 400+ schools with basketball programs.

    This adapter provides:
    1. Tournament brackets for all classifications (Division 1, Division 2, Division 3, Division 4, Division 5)
    2. Seeds, matchups, dates, locations
    3. Game scores and final results
    4. Historical tournament data
    5. Regional and state championship results

    **ARCHITECTURE**:
    - Inherits from AssociationAdapterBase
    - Prioritizes HTML parsing (bracket pages)
    - Enumerates classifications: Division 1, Division 2, Division 3, Division 4, Division 5
    - Generates unique game IDs: wiaa_{year}_{class}_{home}@{away}

    **DATA QUALITY**: HIGH (official source, authoritative)

    **LIMITATIONS**:
    - No player-level statistics (use MaxPreps for this)
    - No regular season schedules
    - Bracket-focused, not stats-focused
    """

    source_type = DataSourceType.WIAA
    source_name = "WIAA"
    base_url = "https://www.wiaawi.org"
    region = DataSourceRegion.US_WI

    # WIAA specific constants
    CLASSIFICATIONS = ["Division 1", "Division 2", "Division 3", "Division 4", "Division 5"]
    GENDERS = ["Boys", "Girls"]
    MIN_YEAR = 2015  # Historical data availability
    STATE_CODE = "WI"
    STATE_NAME = "Wisconsin"
    ORGANIZATION = "WIAA"

    def __init__(self):
        """Initialize WIAA datasource with Wisconsin-specific configuration."""
        super().__init__()
        self.settings = get_settings()
        self.logger.info(
            "WIAA initialized",
            classifications=len(self.CLASSIFICATIONS),
            genders=len(self.GENDERS),
            min_year=self.MIN_YEAR,
            organization=self.ORGANIZATION,
        )

    def _build_bracket_url(
        self, classification: str, gender: str = "Boys", year: Optional[int] = None
    ) -> str:
        """
        Build URL for specific tournament bracket.

        **WIAA URL Format** (verified 2024-11-13):
        ```
        /Sports/{Gender}-Basketball/Tournament-Brackets

        For specific divisions/sectionals, WIAA uses different URL structure per year.
        Example 2024 pattern observed:
        - Main page lists links to division brackets
        - Each bracket is HTML with team names, scores, dates embedded
        ```

        Note: WIAA tournament structure uses divisions and sectionals.
        Brackets are typically published under main tournament page with
        links to specific division HTML pages.

        Args:
            classification: Classification name (Division 1-5)
            gender: "Boys" or "Girls"
            year: Tournament year (optional, defaults to current)

        Returns:
            Full bracket URL or main tournament page
        """
        year = year or datetime.now().year
        gender_formatted = gender.capitalize()

        # WIAA main tournament bracket page
        # Individual division brackets need to be discovered from this page
        url = f"{self.base_url}/Sports/{gender_formatted}-Basketball/Tournament-Brackets"

        return url

    def _extract_year(self, season: Optional[str]) -> int:
        """Extract year from season string."""
        if not season:
            return datetime.now().year
        year = int(season.split("-")[1]) if "-" in season else int(season)
        return year + 2000 if year < 100 else year

    async def get_tournament_brackets(
        self,
        season: Optional[str] = None,
        classification: Optional[str] = None,
        gender: str = "Boys",
    ) -> Dict[str, Any]:
        """
        Get tournament brackets for a season.

        **ENUMERATION STRATEGY**:
        - If season provided: fetch brackets for that year
        - If classification provided: only fetch that classification's bracket
        - Otherwise: fetch current year, all classifications

        Args:
            season: Season string (e.g., "2024-25"), None for current
            classification: Specific classification (Division 1, Division 2, Division 3, Division 4, Division 5), None for all
            gender: "Boys" or "Girls"

        Returns:
            Dict with keys:
                - games: List[Game] - all tournament games
                - teams: List[Team] - all participating teams
                - brackets: Dict[str, List[Game]] - games grouped by classification
                - metadata: bracket metadata (year, updated timestamps)
        """
        year = self._extract_year(season)
        classifications = [classification] if classification else self.CLASSIFICATIONS

        all_games: List[Game] = []
        all_teams: Dict[str, Team] = {}
        brackets: Dict[str, List[Game]] = {}
        metadata: Dict[str, Any] = {}

        self.logger.info(
            f"Fetching WIAA tournament brackets",
            year=year,
            classifications=classifications,
            gender=gender,
        )

        # Step 1: Fetch index page to discover bracket URLs
        index_url = self._build_bracket_url("", gender, year)  # Gets main page
        try:
            status, content, headers = await self.http_get(index_url, timeout=30.0)

            # Session 8 - Phase 24: Debug headers
            print(f"[DEBUG] Response headers: {dict(headers)}")
            print(f"[DEBUG] Content-Encoding: {headers.get('content-encoding', 'none')}")
            print(f"[DEBUG] Content-Type: {headers.get('content-type', 'unknown')}")

            if status != 200:
                self.logger.error(
                    f"Failed to fetch index page",
                    status=status,
                    url=index_url,
                )
                return {
                    "games": [],
                    "teams": [],
                    "brackets": {},
                    "metadata": {"error": f"HTTP {status}", "url": index_url},
                    "year": year,
                    "gender": gender,
                }

            # Session 8 - Phase 24: Handle compression based on Content-Encoding header
            import gzip
            import zlib
            try:
                import brotli
                HAS_BROTLI = True
            except ImportError:
                HAS_BROTLI = False
                print(f"[WARNING] brotli library not installed, cannot decompress br-encoded content")

            # Check Content-Encoding header to determine compression
            content_encoding = headers.get('content-encoding', '').lower()

            if content_encoding == 'br':
                # Brotli compression
                if HAS_BROTLI:
                    print(f"[DEBUG] Content is Brotli-compressed, decompressing...")
                    try:
                        content = brotli.decompress(content)
                        print(f"[DEBUG] Decompressed from {len(content)} bytes to actual size")
                    except Exception as e:
                        print(f"[DEBUG] Brotli decompression failed: {e}")
                else:
                    print(f"[ERROR] Content is Brotli-compressed but brotli library not available")
            elif content_encoding == 'gzip' or content[:2] == b'\x1f\x8b':
                # Gzip compression
                print(f"[DEBUG] Content is gzip-compressed, decompressing...")
                try:
                    content = gzip.decompress(content)
                    print(f"[DEBUG] Decompressed to {len(content)} bytes")
                except Exception as e:
                    print(f"[DEBUG] Gzip decompression failed: {e}")
            elif content_encoding == 'deflate' or content[:2] in (b'\x78\x9c', b'\x78\x01'):
                # Deflate/zlib compression
                print(f"[DEBUG] Content is zlib-compressed, decompressing...")
                try:
                    content = zlib.decompress(content)
                    print(f"[DEBUG] Decompressed to {len(content)} bytes")
                except Exception as e:
                    print(f"[DEBUG] Zlib decompression failed: {e}")
            else:
                print(f"[DEBUG] Content encoding: {content_encoding or 'none'}")

            index_html = content.decode("utf-8", errors="ignore")

            # Session 8 - Phase 24: Debug output (safe Unicode handling for Windows)
            try:
                print(f"[DEBUG] Fetched index page: {len(content)} bytes (raw)")
                print(f"[DEBUG] Decoded HTML: {len(index_html)} chars")
                # Safe print: remove non-ASCII for Windows console
                safe_preview = index_html[:500].encode('ascii', 'replace').decode('ascii')
                print(f"[DEBUG] First 500 chars: {safe_preview}")
            except Exception as e:
                print(f"[DEBUG] Error printing preview: {e}")

            # Step 2: Discover bracket URLs from index page
            discovered_urls = discover_wiaa_brackets(index_html, year, gender, self.base_url)

            self.logger.info(
                f"Discovered WIAA bracket URLs",
                count=len(discovered_urls),
                year=year,
                gender=gender,
            )

            # Session 8 - Phase 24: Step 3 - Generate Halftime HTML URLs (PRIMARY METHOD)
            # Since WIAA uses JavaScript-loaded brackets, we generate URLs directly
            # rather than parsing HTML links
            # HTML brackets are preferred over PDFs (no OCR needed)
            halftime_htmls = generate_halftime_html_urls(year, gender)
            self.logger.info(
                f"Generated Halftime HTML URLs using pattern enumeration",
                html_count=len(halftime_htmls),
                year=year,
                gender=gender
            )

            # Check if we have any HTML brackets to parse
            if not halftime_htmls:
                # No HTML brackets found - unexpected, as pattern is well-established
                self.logger.warning(
                    "No Halftime bracket HTML URLs generated",
                    nav_urls=len(discovered_urls),
                    url=index_url,
                )
                return {
                    "games": [],
                    "teams": [],
                    "brackets": {},
                    "metadata": {
                        "error": f"No Halftime bracket HTML URLs generated for {year} {gender}",
                        "url": index_url,
                        "year": year,
                        "gender": gender,
                        "nav_urls_found": len(discovered_urls),
                        "htmls_generated": 0,
                    },
                    "year": year,
                    "gender": gender,
                }

        except Exception as e:
            self.logger.error(
                f"Failed to discover bracket URLs",
                year=year,
                gender=gender,
                error=str(e),
            )
            return {
                "games": [],
                "teams": [],
                "brackets": {},
                "metadata": {"error": str(e)},
                "year": year,
                "gender": gender,
            }

        # Session 8 - Phase 24: Step 4 - Validate and fetch Halftime bracket HTML pages
        # First pass: Validate which generated URLs actually exist (filter out 404s)
        valid_htmls = []
        print(f"[DEBUG] Validating {len(halftime_htmls)} generated HTML URLs...")

        for idx, html_info in enumerate(halftime_htmls):
            html_url = html_info["url"]
            division = html_info.get("division", "Unknown")
            sections = html_info.get("sections", [])

            try:
                # Fetch HTML page
                try:
                    status, content, headers = await self.http_get(html_url, timeout=10.0)
                except Exception:
                    status = 0

                if status == 200:
                    # Decode content
                    html_content = content.decode("utf-8", errors="ignore")
                    valid_htmls.append({
                        **html_info,
                        "content": html_content,
                        "size": len(content)
                    })
                    print(f"  [VALID HTML {len(valid_htmls)}] Div{division} Sections{sections} ({len(content)} bytes)")
                elif status == 404:
                    # Expected - not all sectional combinations exist
                    pass
                else:
                    # Unexpected status
                    self.logger.debug(
                        f"Unexpected status for HTML",
                        status=status,
                        url=html_url
                    )

            except Exception as e:
                # Network errors, timeouts, etc. - skip this URL
                self.logger.debug(f"Error validating HTML URL", url=html_url, error=str(e))
                continue

        self.logger.info(
            f"Validated Halftime HTML brackets",
            valid=len(valid_htmls),
            total_generated=len(halftime_htmls),
            year=year,
            gender=gender
        )

        print(f"[DEBUG] Found {len(valid_htmls)} valid HTML brackets out of {len(halftime_htmls)} generated URLs")

        if not valid_htmls:
            # No valid HTML brackets found - return empty result
            return {
                "games": [],
                "teams": [],
                "brackets": {},
                "metadata": {
                    "error": f"No valid Halftime bracket HTML pages found for {year} {gender} (tried {len(halftime_htmls)} URLs)",
                    "year": year,
                    "gender": gender,
                    "urls_generated": len(halftime_htmls),
                    "valid_htmls": 0,
                },
                "year": year,
                "gender": gender,
            }

        # Second pass: Process each valid HTML bracket
        for idx, html_info in enumerate(valid_htmls):
            html_url = html_info["url"]
            division = html_info.get("division", "Unknown")
            sections = html_info.get("sections", [])
            content = html_info.get("content", "")
            bracket_key = f"Division {division}" if division != "Unknown" else f"bracket_{idx}"

            try:
                self.logger.info(
                    f"Processing Halftime HTML [{idx+1}/{len(valid_htmls)}]",
                    url=html_url,
                    division=division,
                    sections=sections,
                    size=len(content)
                )

                # Session 8 - Phase 24: Parse HTML bracket to extract games (PRIMARY METHOD)
                print(f"[DEBUG] Parsing HTML: Division {division}, Sections {sections}")

                # Parse HTML into Game objects
                parsed_games = parse_halftime_html_to_games(
                    html_content=content,
                    year=year,
                    gender=gender,
                    division=division,
                    sections=sections,
                    html_url=html_url,
                    adapter=self,  # Pass adapter instance for create_data_source_metadata()
                    logger=self.logger
                )

                if not parsed_games:
                    self.logger.warning(
                        f"No games parsed from HTML",
                        url=html_url,
                        division=division
                    )
                    # Store metadata even if parsing failed
                    metadata[bracket_key] = {
                        "html_url": html_url,
                        "division": division,
                        "sections": sections,
                        "status": "HTML_PARSE_FAILED",
                        "games_found": 0,
                    }
                    continue

                # Add games to results
                for game in parsed_games:
                    all_games.append(game)
                    brackets.setdefault(bracket_key, []).append(game)

                    # Extract teams from game
                    if game.home_team_id not in all_teams:
                        from ...models.team import Team, TeamLevel
                        all_teams[game.home_team_id] = Team(
                            team_id=game.home_team_id,
                            team_name=game.home_team_name,
                            school_name=game.home_team_name,
                            state=self.STATE_CODE,
                            country="USA",
                            level=TeamLevel.HIGH_SCHOOL_VARSITY,
                            league=f"WIAA Division {division}",
                            season=game.season,
                            data_source=self.create_data_source_metadata(
                                quality_flag=DataQualityFlag.VERIFIED
                            ),
                        )

                    if game.away_team_id not in all_teams:
                        from ...models.team import Team, TeamLevel
                        all_teams[game.away_team_id] = Team(
                            team_id=game.away_team_id,
                            team_name=game.away_team_name,
                            school_name=game.away_team_name,
                            state=self.STATE_CODE,
                            country="USA",
                            level=TeamLevel.HIGH_SCHOOL_VARSITY,
                            league=f"WIAA Division {division}",
                            season=game.season,
                            data_source=self.create_data_source_metadata(
                                quality_flag=DataQualityFlag.VERIFIED
                            ),
                        )

                # Store metadata for this bracket
                metadata[bracket_key] = {
                    "html_url": html_url,
                    "division": division,
                    "sections": sections,
                    "status": "HTML_PARSED_SUCCESS",
                    "games_found": len(parsed_games),
                    "year": year,
                    "gender": gender,
                }

                self.logger.info(
                    f"Parsed HTML bracket successfully",
                    division=division,
                    sections=sections,
                    games=len(parsed_games)
                )

            except Exception as e:
                self.logger.warning(
                    f"Failed to process HTML bracket",
                    year=year,
                    url=html_url,
                    error=str(e),
                )
                continue

        self.logger.info(
            f"Fetched all WIAA tournament brackets",
            year=year,
            total_games=len(all_games),
            total_teams=len(all_teams),
        )

        return {
            "games": all_games,
            "teams": list(all_teams.values()),
            "brackets": brackets,
            "metadata": metadata,
            "year": year,
            "gender": gender,
        }

    def _parse_bracket_html(
        self, soup, year: int, classification: str, gender: str, url: str
    ) -> Dict[str, Any]:
        """
        Parse tournament bracket from HTML using shared bracket utilities.

        WIAA bracket pages typically contain:
        - Tournament tree/bracket visualization
        - Game results in tables or divs
        - Team names with seeds
        - Scores for completed games
        - Regional/state championship structure

        Args:
            soup: BeautifulSoup parsed HTML
            year: Tournament year
            classification: Classification name (Division 1, Division 2, Division 3, Division 4, Division 5)
            gender: Boys or Girls
            url: Source URL

        Returns:
            Dict with games, teams, metadata
        """
        games: List[Game] = []
        teams: Dict[str, Team] = {}
        seen_ids = set()  # Deduplication
        season = f"{year-1}-{str(year)[2:]}"

        # Extract page-level metadata (round, venue, tipoff) - Phase 18 enhancement
        page_meta = parse_block_meta(soup, year=year) or {}

        # Use shared bracket parser (handles both table and div layouts)
        for team1, team2, score1, score2 in parse_bracket_tables_and_divs(soup):
            if not team1 or not team2:
                continue

            # Pass metadata to game creation - Phase 18 enhancement
            game = self._create_game(
                team1, team2, score1, score2, year, classification, gender, url, extra=page_meta
            )

            # Deduplicate games
            if game.game_id in seen_ids:
                continue
            seen_ids.add(game.game_id)
            games.append(game)

            # Extract teams using canonical IDs
            for name, tid in [
                (game.home_team_name, game.home_team_id),
                (game.away_team_name, game.away_team_id),
            ]:
                if tid not in teams:
                    teams[tid] = self._create_team(tid, name, classification, season)

        return {
            "games": games,
            "teams": list(teams.values()),
            "metadata": {"source_url": url},
        }

    def _create_game(
        self,
        team1: str,
        team2: str,
        score1: Optional[int],
        score2: Optional[int],
        year: int,
        classification: str,
        gender: str,
        url: str,
        extra: Optional[Dict[str, str]] = None,
    ) -> Game:
        """Create Game object from parsed data using canonical team IDs.

        Phase 18 enhancement: Added optional extra parameter for metadata (round, venue, tipoff).
        """
        # Use shared canonical team ID generator
        team1_id = canonical_team_id("wiaa", team1)
        team2_id = canonical_team_id("wiaa", team2)

        return Game(
            game_id=f"wiaa_{year}_{classification.lower()}_{team1_id.split('_', 1)[1]}_vs_{team2_id.split('_', 1)[1]}",
            home_team_id=team1_id,
            home_team_name=team1,
            away_team_id=team2_id,
            away_team_name=team2,
            home_score=score1,
            away_score=score2,
            status=GameStatus.FINAL if score1 is not None and score2 is not None else GameStatus.SCHEDULED,
            game_type=GameType.PLAYOFF,
            level="high_school_varsity",
            league=f"WIAA {classification}",
            season=f"{year-1}-{str(year)[2:]}",
            gender=gender.lower(),
            data_source=self.create_data_source_metadata(
                url=url, quality_flag=DataQualityFlag.VERIFIED, extra=extra or {}
            ),
        )

    def _create_team(
        self, team_id: str, name: str, classification: str, season: str
    ) -> Team:
        """Create Team object."""
        return Team(
            team_id=team_id,
            team_name=name,
            school_name=name,
            state=self.STATE_CODE,
            country="USA",
            level=TeamLevel.HIGH_SCHOOL_VARSITY,
            league=f"WIAA {classification}",
            season=season,
            data_source=self.create_data_source_metadata(
                quality_flag=DataQualityFlag.VERIFIED
            ),
        )

    # Required base methods (minimal implementation for bracket-only adapter)
    async def _parse_json_data(self, json_data: Dict, season: str) -> Dict:
        return {"teams": [], "games": [], "season": season}

    async def _parse_html_data(self, html: str, season: str) -> Dict:
        year = self._extract_year(season)
        soup = parse_html(html)
        bracket_data = self._parse_bracket_html(soup, year, "Division 1", "Boys", "")
        return {
            "teams": bracket_data["teams"],
            "games": bracket_data["games"],
            "season": season,
        }

    async def get_player(self, player_id: str) -> Optional[Player]:
        self.logger.warning("WIAA does not provide player data - use MaxPreps for Wisconsin")
        return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[Player]:
        return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        brackets = await self.get_tournament_brackets(season="2024-25")
        for team in brackets["teams"]:
            if team.team_id == team_id:
                return team
        return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        limit: int = 100,
    ) -> List[Game]:
        brackets = await self.get_tournament_brackets(season=season)
        games = brackets["games"]

        if team_id:
            games = [
                g for g in games if team_id in [g.home_team_id, g.away_team_id]
            ]
        if start_date:
            games = [g for g in games if g.game_date and g.game_date >= start_date]
        if end_date:
            games = [g for g in games if g.game_date and g.game_date <= end_date]

        return games[:limit]

    async def get_leaderboard(
        self, stat: str, season: Optional[str] = None, limit: int = 50
    ) -> List[Dict]:
        return []
