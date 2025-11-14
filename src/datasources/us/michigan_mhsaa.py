"""
MHSAA (Michigan State Association) DataSource Adapter

Provides authoritative tournament brackets, seeds, scores, and championship results
for Michigan high school basketball.

**Data Authority**: MHSAA is the source of truth for:
- Tournament brackets (4 classifications: Division 1, Division 2, Division 3, Division 4)
- Seeds and matchups
- Game dates, times, locations
- Final scores and champions
- Historical tournament data

**Base URL**: https://www.mhsaa.com

**URL Pattern**:
```
Basketball: /sports/basketball/
Boys: /sports/basketball/boys/
Girls: /sports/basketball/girls/
Brackets: /brackets/{year}/
Playoffs: /playoffs/{year}/{classification}/
```

**Coverage**:
- Classifications: Division 1, Division 2, Division 3, Division 4 (enrollment-based)
- 750+ member schools
- Boys and Girls tournaments
- All regions of Michigan

**Michigan Basketball Context**:
- 750+ schools
- Strong basketball tradition
- MHSAA manages all high school athletics in Michigan
- Enrollment-based classifications (Division 1 highest, Division 4 lowest)
- Regional tournaments → state championships

**Special Features**:
- Historical bracket data available
- Regional tournament structure
- Digital presence with bracket updates

**Limitations**:
- Player statistics NOT available (state associations focus on brackets/lineage)
- Regular season schedules typically on MaxPreps (separate source)
- Box scores rarely available

**Recommended Use**: MHSAA provides official tournament brackets.
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
import re
from dataclasses import dataclass


@dataclass
class MHSAAGameRecord:
    """
    Temporary record for MHSAA text-line parsed games.

    MHSAA uses a text-based bracket layout (not tables), with lines like:
    - "Round 1 - District 64"
    - Team A name
    - Team A score
    - Team B name
    - Team B score
    """
    round_name: str
    district: str
    date: Optional[str]
    site: Optional[str]
    team_a: str
    score_a: int
    team_b: str
    score_b: int


# Regex patterns for MHSAA text parsing
ROUND_RE = re.compile(r"^Round\s+\d+\s*[-–]\s*(?P<district>.+)$")
DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}")
SCORE_RE = re.compile(r"^\d+$")


def parse_mhsaa_lines(lines: List[str]) -> List[MHSAAGameRecord]:
    """
    Parse MHSAA bracket from text lines.

    MHSAA brackets are text-based (not tables), structured as:
    - Round header: "Round 1 - District 64"
    - Optional date/time/site lines
    - Game blocks: team_a_name, score_a, team_b_name, score_b
    - "Bye" games are skipped

    Args:
        lines: List of stripped text lines from HTML

    Returns:
        List of MHSAAGameRecord objects
    """
    games: List[MHSAAGameRecord] = []
    current_round = None
    current_district = None
    current_date = None
    current_site = None

    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # 1) Round + district marker
        m_round = ROUND_RE.match(line)
        if m_round:
            current_round = line
            current_district = m_round.group("district")
            current_date = None
            current_site = None
            i += 1
            continue

        # 2) Date/time line (after a round)
        if DATE_RE.match(line):
            current_date = line
            i += 1
            # Next non-empty line is usually site
            if i < n and "High School" in lines[i]:
                current_site = lines[i]
                i += 1
            continue

        # 3) Detect a game block: name, score, name, score
        # Skip "Bye" games – they don't have two teams + scores
        if line.lower() == "bye":
            i += 1
            continue

        # Candidate team A
        team_a = line
        if i + 3 < n and SCORE_RE.match(lines[i+1]) and SCORE_RE.match(lines[i+3]):
            try:
                score_a = int(lines[i+1])
                team_b = lines[i+2]
                score_b = int(lines[i+3])

                games.append(
                    MHSAAGameRecord(
                        round_name=current_round or "",
                        district=current_district or "",
                        date=current_date,
                        site=current_site,
                        team_a=team_a,
                        score_a=score_a,
                        team_b=team_b,
                        score_b=score_b,
                    )
                )
                i += 4
                continue
            except (ValueError, IndexError):
                # Skip malformed game blocks
                pass

        i += 1

    return games


class MichiganMHSAADataSource(AssociationAdapterBase):
    """
    Michigan MHSAA adapter.

    **PRIMARY PURPOSE**: Authoritative tournament bracket and postseason results.

    **COVERAGE**: 750+ schools with basketball programs.

    This adapter provides:
    1. Tournament brackets for all classifications (Division 1, Division 2, Division 3, Division 4)
    2. Seeds, matchups, dates, locations
    3. Game scores and final results
    4. Historical tournament data
    5. Regional and state championship results

    **ARCHITECTURE**:
    - Inherits from AssociationAdapterBase
    - Prioritizes HTML parsing (bracket pages)
    - Enumerates classifications: Division 1, Division 2, Division 3, Division 4
    - Generates unique game IDs: mhsaa_{year}_{class}_{home}@{away}

    **DATA QUALITY**: HIGH (official source, authoritative)

    **LIMITATIONS**:
    - No player-level statistics (use MaxPreps for this)
    - No regular season schedules
    - Bracket-focused, not stats-focused
    """

    source_type = DataSourceType.MHSAA_MI
    source_name = "Michigan MHSAA"
    base_url = "https://my.mhsaa.com"
    region = DataSourceRegion.US_MI

    # MHSAA specific constants
    CLASSIFICATIONS = ["Division 1", "Division 2", "Division 3", "Division 4"]
    # Map classification names to numeric IDs used in URLs
    CLASSIFICATION_IDS = {"Division 1": "1", "Division 2": "2", "Division 3": "3", "Division 4": "4"}
    GENDERS = ["Boys", "Girls"]
    MIN_YEAR = 2015  # Historical data availability
    STATE_CODE = "MI"
    STATE_NAME = "Michigan"
    ORGANIZATION = "MHSAA"

    def __init__(self):
        """Initialize MHSAA datasource with Michigan-specific configuration."""
        super().__init__()
        self.settings = get_settings()
        self.logger.info(
            "MHSAA initialized",
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

        **MHSAA URL Format** (verified 2024-11-13):
        ```
        /Sports/MHSAA-Tournament-Brackets/BracketGroup/9/SportSeasonId/{season_id}/Classification/{class_id}

        Example:
        /Sports/MHSAA-Tournament-Brackets/BracketGroup/9/SportSeasonId/424465/Classification/1
        ```

        Note: MHSAA uses my.mhsaa.com subdomain and numeric classification IDs.
        SportSeasonId changes per year and needs to be discovered.

        Args:
            classification: Classification name (Division 1, Division 2, Division 3, Division 4)
            gender: "Boys" or "Girls"
            year: Tournament year (optional, defaults to current)

        Returns:
            Full bracket URL
        """
        year = year or datetime.now().year

        # Get numeric classification ID
        class_id = self.CLASSIFICATION_IDS.get(classification, "1")

        # SportSeasonId mapping (needs to be updated annually)
        # 2024-25 season ID: 424465 (verified)
        # For now, hardcode 2024-25 season; future: scrape from main page
        season_id = "424465" if year == 2024 else "424465"  # TODO: make dynamic

        # MHSAA my.mhsaa.com bracket format
        url = (
            f"{self.base_url}/Sports/MHSAA-Tournament-Brackets/BracketGroup/9/"
            f"SportSeasonId/{season_id}/Classification/{class_id}"
        )

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

        **STATUS: NOT IMPLEMENTED - Phase 2**

        Michigan MHSAA brackets require JavaScript execution or API reverse-engineering.
        The main bracket pages and BracketGroup pages only contain:
        - Image maps for navigation
        - Empty <div> containers that are populated via JavaScript
        - No static HTML content with game/team data

        To implement this adapter, one of the following approaches is required:
        1. Playwright/Selenium for JavaScript execution and post-render DOM extraction
        2. Reverse-engineer internal AJAX/JSON endpoints
        3. Alternative data source discovery

        See PROJECT_LOG.md Phase 2 for Michigan implementation planning.
        See src/state_sources.py for classification as JS_BRACKET.

        **ENUMERATION STRATEGY** (for future Phase 2 implementation):
        - If season provided: fetch brackets for that year
        - If classification provided: only fetch that classification's bracket
        - Otherwise: fetch current year, all classifications

        Args:
            season: Season string (e.g., "2024-25"), None for current
            classification: Specific classification (Division 1, Division 2, Division 3, Division 4), None for all
            gender: "Boys" or "Girls"

        Returns:
            Dict with keys:
                - games: List[Game] - all tournament games
                - teams: List[Team] - all participating teams
                - brackets: Dict[str, List[Game]] - games grouped by classification
                - metadata: bracket metadata (year, updated timestamps)

        Raises:
            NotImplementedError: Michigan MHSAA requires JavaScript execution (Phase 2)
        """
        raise NotImplementedError(
            "Michigan MHSAA brackets require JavaScript execution or API reverse-engineering. "
            "Static HTML pages only contain image maps and empty <div> containers. "
            "This adapter is deferred to Phase 2 (Playwright/browser automation). "
            "See PROJECT_LOG.md for details."
        )

        # Original implementation preserved for Phase 2 reference:
        year = self._extract_year(season)
        classifications = [classification] if classification else self.CLASSIFICATIONS

        all_games: List[Game] = []
        all_teams: Dict[str, Team] = {}
        brackets: Dict[str, List[Game]] = {}
        metadata: Dict[str, Any] = {}

        self.logger.info(
            f"Fetching MHSAA tournament brackets",
            year=year,
            classifications=classifications,
            gender=gender,
        )

        # Enumerate all bracket combinations
        for cls in classifications:
            bracket_key = f"class_{cls.lower()}"

            try:
                url = self._build_bracket_url(cls, gender, year)
                status, content, headers = await self.http_get(url, timeout=30.0)

                if status != 200:
                    self.logger.warning(
                        f"Failed to fetch bracket",
                        status=status,
                        classification=cls,
                        url=url,
                    )
                    continue

                html = content.decode("utf-8", errors="ignore")
                soup = parse_html(html)

                # Parse bracket HTML
                bracket_data = self._parse_bracket_html(soup, year, cls, gender, url)

                self.logger.info(
                    f"Parsed MHSAA bracket",
                    classification=cls,
                    games=len(bracket_data["games"]),
                    teams=len(bracket_data["teams"]),
                )

                # Collect games and teams
                for game in bracket_data["games"]:
                    all_games.append(game)
                    brackets.setdefault(bracket_key, []).append(game)

                for team in bracket_data["teams"]:
                    all_teams[team.team_id] = team

                # Collect metadata
                if bracket_data.get("metadata"):
                    metadata[bracket_key] = bracket_data["metadata"]

            except Exception as e:
                self.logger.warning(
                    f"Failed to fetch bracket",
                    year=year,
                    classification=cls,
                    gender=gender,
                    error=str(e),
                )
                continue

        self.logger.info(
            f"Fetched all MHSAA tournament brackets",
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
        Parse tournament bracket from HTML using MHSAA-specific text-line parser.

        MHSAA bracket pages use a text-based layout (NOT tables), structured as:
        - Round headers: "Round 1 - District 64"
        - Optional date/time/site lines
        - Game blocks: team_a_name, score_a, team_b_name, score_b
        - "Bye" games (skipped)

        This is different from most states which use HTML tables/divs.

        Args:
            soup: BeautifulSoup parsed HTML
            year: Tournament year
            classification: Classification name (Division 1-4)
            gender: Boys or Girls
            url: Source URL

        Returns:
            Dict with games, teams, metadata
        """
        games: List[Game] = []
        teams: Dict[str, Team] = {}
        seen_ids = set()  # Deduplication
        season = f"{year-1}-{str(year)[2:]}"

        # Extract text lines from HTML
        text = soup.get_text("\n")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        # Parse using MHSAA-specific line parser
        game_records = parse_mhsaa_lines(lines)

        self.logger.info(
            f"Parsed MHSAA text lines",
            total_lines=len(lines),
            game_records=len(game_records),
            classification=classification,
        )

        # Convert MHSAAGameRecord → Game objects
        for record in game_records:
            # Create Game object
            game = self._create_game(
                team1=record.team_a,
                team2=record.team_b,
                score1=record.score_a,
                score2=record.score_b,
                year=year,
                classification=classification,
                gender=gender,
                url=url,
                extra={
                    "round": record.round_name,
                    "district": record.district,
                    "date": record.date,
                    "site": record.site,
                }
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
            "metadata": {"source_url": url, "parser_type": "MHSAA_TEXT_LINES"},
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
        team1_id = canonical_team_id("mhsaa", team1)
        team2_id = canonical_team_id("mhsaa", team2)

        return Game(
            game_id=f"mhsaa_{year}_{classification.lower()}_{team1_id.split('_', 1)[1]}_vs_{team2_id.split('_', 1)[1]}",
            home_team_id=team1_id,
            home_team_name=team1,
            away_team_id=team2_id,
            away_team_name=team2,
            home_score=score1,
            away_score=score2,
            status=GameStatus.FINAL if score1 is not None and score2 is not None else GameStatus.SCHEDULED,
            game_type=GameType.PLAYOFF,
            level="high_school_varsity",
            league=f"MHSAA {classification}",
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
            league=f"MHSAA {classification}",
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
        self.logger.warning("MHSAA does not provide player data - use MaxPreps for Michigan")
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
