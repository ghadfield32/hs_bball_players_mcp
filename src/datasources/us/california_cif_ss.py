"""
CIF-SS (California Interscholastic Federation - Southern Section) DataSource Adapter

Provides authoritative tournament brackets, seeds, scores, and championship results
for Southern California high school basketball. This is the LARGEST state section in the US.

**Data Authority**: CIF-SS is the source of truth for:
- Tournament brackets (10+ divisions based on competitive equity)
- Seeds and matchups
- Game dates, times, locations
- Final scores and champions
- Historical tournament data

**Base URL**: https://www.cifss.org

**URL Pattern**:
```
Basketball Brackets: /brackets/{year}-{sport}/
Boys: /brackets/2025-boys-basketball/
Girls: /brackets/2025-girls-basketball/
Scores: https://scores.cifss.org/
```

**Coverage**:
- Divisions: Open Division, D1, D2, D3, D4, D5A, D5AA (7+ divisions, varies by year)
- Southern California: Los Angeles, Orange County, Riverside, San Bernardino, Ventura
- 1,600+ member schools (largest section in US)
- Boys and Girls tournaments

**California Basketball Context**:
- Largest state in US (40M population)
- Most competitive high school basketball in the nation
- Notable players: Russell Westbrook, James Harden, Kawhi Leonard, Paul George, DeMar DeRozan
- CIF-SS is the premier section (others: CIF-CS, CIF-NS, CIF-SD, etc.)
- Partially covered by MaxPreps for regular season

**Special Features**:
- **Competitive equity model** (not enrollment-based divisions)
- MaxPreps partnership for schedules
- Historical bracket data available

**Limitations**:
- Player statistics NOT available (state associations focus on brackets/lineage)
- Regular season schedules on MaxPreps (separate source)
- Box scores rarely available

**Recommended Use**: CIF-SS provides official tournament brackets.
For player-level stats, combine with MaxPreps or SBLive (covers CA).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import re
import json

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


class CaliforniaCIFSSDataSource(AssociationAdapterBase):
    """
    California Interscholastic Federation - Southern Section (CIF-SS) adapter.

    **PRIMARY PURPOSE**: Authoritative tournament bracket and postseason results.

    **LARGEST SECTION**: 1,600+ schools - more than most entire states.

    This adapter provides:
    1. Tournament brackets for all divisions (Open, D1-D5AA)
    2. Seeds, matchups, dates, locations
    3. Game scores and final results
    4. Historical tournament data

    **ARCHITECTURE**:
    - Inherits from AssociationAdapterBase
    - Prioritizes HTML parsing (bracket pages)
    - Enumerates divisions: Open, D1, D2, D3, D4, D5A, D5AA
    - Generates unique game IDs: cif_ss:{year}:{div}:{home}@{away}

    **DATA QUALITY**: HIGH (official source, authoritative)

    **LIMITATIONS**:
    - No player-level statistics (use MaxPreps for this)
    - No regular season schedules
    - Bracket-focused, not stats-focused
    """

    source_type = DataSourceType.CIF_SS
    source_name = "CIF-SS"
    base_url = "https://www.cifss.org"
    region = DataSourceRegion.US_CA

    # CIF-SS specific constants
    # Note: Divisions change by year; this is a typical structure
    DIVISIONS = ["Open", "D1", "D2", "D3", "D4", "D5A", "D5AA"]
    GENDERS = ["Boys", "Girls"]
    MIN_YEAR = 2015  # Historical data availability
    STATE_CODE = "CA"
    STATE_NAME = "California"
    SECTION = "Southern Section"

    def __init__(self):
        """Initialize CIF-SS datasource with California-specific configuration."""
        super().__init__()
        self.settings = get_settings()
        self.logger.info(
            "CIF-SS initialized",
            divisions=len(self.DIVISIONS),
            genders=len(self.GENDERS),
            min_year=self.MIN_YEAR,
            section=self.SECTION,
        )

    def _build_bracket_url(
        self, division: str, gender: str = "Boys", year: Optional[int] = None
    ) -> str:
        """
        Build URL for CIF-SS tournament bracket page.

        **CIF-SS URL Format** (verified 2024-11-13):
        ```
        /brackets/{year}-{gender}-basketball/

        Examples:
        /brackets/2024-boys-basketball/
        /brackets/2024-girls-basketball/
        ```

        **Important**: All divisions (Open, D1, D2AA, D2A, D3AA, D3A, D4AA, D4A, D5AA, D5A)
        are displayed on a SINGLE page using JavaScript tabs. Do NOT append division to URL.

        Args:
            division: Division name (ignored - all divisions on same page)
            gender: "Boys" or "Girls"
            year: Tournament year (optional)

        Returns:
            Full bracket URL (same URL for all divisions)
        """
        year = year or datetime.now().year
        gender_lower = gender.lower()

        # CIF-SS uses single page for all divisions with tabbed interface
        # All divisions (Open, D1-D5) are on this one page
        return f"{self.base_url}/brackets/{year}-{gender_lower}-basketball"

    def _extract_year(self, season: Optional[str]) -> int:
        """Extract year from season string."""
        if not season:
            return datetime.now().year
        year = int(season.split("-")[1]) if "-" in season else int(season)
        return year + 2000 if year < 100 else year

    async def get_tournament_brackets(
        self, season: Optional[str] = None, division: Optional[str] = None, gender: str = "Boys"
    ) -> Dict[str, Any]:
        """
        Get tournament brackets for a season.

        **ENUMERATION STRATEGY**:
        - If season provided: fetch brackets for that year
        - If division provided: only fetch that division's bracket
        - Otherwise: fetch current year, all divisions

        Args:
            season: Season string (e.g., "2024-25"), None for current
            division: Specific division (Open, D1, etc.), None for all
            gender: "Boys" or "Girls"

        Returns:
            Dict with keys:
                - games: List[Game] - all tournament games
                - teams: List[Team] - all participating teams
                - brackets: Dict[str, List[Game]] - games grouped by division
                - metadata: bracket metadata (year, updated timestamps)
        """
        year = self._extract_year(season)
        divisions = [division] if division else self.DIVISIONS

        all_games: List[Game] = []
        all_teams: Dict[str, Team] = {}
        brackets: Dict[str, List[Game]] = {}
        metadata: Dict[str, Any] = {}

        self.logger.info(
            f"Fetching CIF-SS tournament brackets",
            year=year,
            divisions=divisions,
            gender=gender,
        )

        # Enumerate all bracket combinations
        for div in divisions:
            bracket_key = f"div_{div.lower()}"

            try:
                url = self._build_bracket_url(div, gender, year)
                status, content, headers = await self.http_get(url, timeout=30.0)

                if status != 200:
                    self.logger.warning(
                        f"Failed to fetch bracket",
                        status=status,
                        division=div,
                        url=url,
                    )
                    continue

                html = content.decode("utf-8", errors="ignore")
                soup = parse_html(html)

                # Parse bracket HTML
                bracket_data = self._parse_bracket_html(soup, year, div, gender, url)

                self.logger.info(
                    f"Parsed CIF-SS bracket",
                    division=div,
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
                    division=div,
                    gender=gender,
                    error=str(e),
                )
                continue

        self.logger.info(
            f"Fetched all CIF-SS tournament brackets",
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
        self, soup, year: int, division: str, gender: str, url: str
    ) -> Dict[str, Any]:
        """
        Parse tournament bracket from HTML using shared bracket utilities.

        CIF-SS bracket pages typically contain:
        - Tournament tree/bracket visualization
        - Game results in tables or divs
        - Team names with seeds
        - Scores for completed games

        Args:
            soup: BeautifulSoup parsed HTML
            year: Tournament year
            division: Division name
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
                team1, team2, score1, score2, year, division, gender, url, extra=page_meta
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
                    teams[tid] = self._create_team(tid, name, division, season)

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
        division: str,
        gender: str,
        url: str,
        extra: Optional[Dict[str, str]] = None,
    ) -> Game:
        """Create Game object from parsed data using canonical team IDs.

        Phase 18 enhancement: Added optional extra parameter for metadata (round, venue, tipoff).
        """
        # Use shared canonical team ID generator
        team1_id = canonical_team_id("cif_ss", team1)
        team2_id = canonical_team_id("cif_ss", team2)

        return Game(
            game_id=f"cif_ss_{year}_{division.lower()}_{team1_id.split('_', 2)[2]}_vs_{team2_id.split('_', 2)[2]}",
            home_team_id=team1_id,
            home_team_name=team1,
            away_team_id=team2_id,
            away_team_name=team2,
            home_score=score1,
            away_score=score2,
            status=GameStatus.FINAL if score1 is not None and score2 is not None else GameStatus.SCHEDULED,
            game_type=GameType.PLAYOFF,
            level="high_school_varsity",
            league=f"CIF-SS {division}",
            season=f"{year-1}-{str(year)[2:]}",
            gender=gender.lower(),
            data_source=self.create_data_source_metadata(
                url=url, quality_flag=DataQualityFlag.VERIFIED, extra=extra or {}
            ),
        )

    def _create_team(
        self, team_id: str, name: str, division: str, season: str
    ) -> Team:
        """Create Team object."""
        return Team(
            team_id=team_id,
            team_name=name,
            school_name=name,
            state=self.STATE_CODE,
            country="USA",
            level=TeamLevel.HIGH_SCHOOL_VARSITY,
            league=f"CIF-SS {division}",
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
        bracket_data = self._parse_bracket_html(soup, year, "D1", "Boys", "")
        return {
            "teams": bracket_data["teams"],
            "games": bracket_data["games"],
            "season": season,
        }

    async def get_player(self, player_id: str) -> Optional[Player]:
        self.logger.warning("CIF-SS does not provide player data - use MaxPreps for CA")
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
