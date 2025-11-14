"""
NYSPHSAA (New York State Public High School Athletic Association) DataSource Adapter

Provides authoritative tournament brackets, seeds, scores, and championship results
for New York high school basketball. Strong basketball state with 700+ schools.

**Data Authority**: NYSPHSAA is the source of truth for:
- Tournament brackets (5 classifications: AA, A, B, C, D)
- Seeds and matchups
- Game dates, times, locations
- Final scores and champions
- Historical tournament data

**Base URL**: https://www.nysphsaa.org

**URL Pattern**:
```
Basketball: /sports/basketball/
Boys: /sports/basketball/boys/
Girls: /sports/basketball/girls/
Brackets: /brackets/{year}/
Championships: /championships/{year}/{classification}/
```

**Coverage**:
- Classifications: AA, A, B, C, D (enrollment-based)
- 700+ member schools
- Boys and Girls tournaments
- All regions of New York
- Strong basketball tradition

**New York Basketball Context**:
- Strong basketball state (700+ schools)
- Notable tradition (Kareem Abdul-Jabbar, Bernard King, God Shammgod)
- NYSPHSAA manages public high school athletics in New York
- Enrollment-based classifications (AA largest, D smallest)
- Regional tournaments → state championships
- State championships held at Glens Falls Civic Center or similar venues
- NYC has separate PSAL league (covered by separate adapter)

**Special Features**:
- Historical bracket data available
- Section tournament structure (11 sections)
- Strong digital presence with bracket updates

**Limitations**:
- Player statistics NOT available (state associations focus on brackets/lineage)
- Regular season schedules typically on MaxPreps (separate source)
- Box scores rarely available
- NYC PSAL schools have separate governance (not NYSPHSAA)

**Recommended Use**: NYSPHSAA provides official tournament brackets.
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


class NewYorkNYSPHSAADataSource(AssociationAdapterBase):
    """
    New York State Public High School Athletic Association (NYSPHSAA) adapter.

    **PRIMARY PURPOSE**: Authoritative tournament bracket and postseason results.

    **STRONG BASKETBALL STATE**: 700+ schools with rich basketball tradition.

    This adapter provides:
    1. Tournament brackets for all classifications (AA, A, B, C, D)
    2. Seeds, matchups, dates, locations
    3. Game scores and final results
    4. Historical tournament data
    5. Section and state championship results

    **ARCHITECTURE**:
    - Inherits from AssociationAdapterBase
    - Prioritizes HTML parsing (bracket pages)
    - Enumerates classifications: AA, A, B, C, D
    - Generates unique game IDs: nysphsaa_{year}_{class}_{home}@{away}

    **DATA QUALITY**: HIGH (official source, authoritative)

    **LIMITATIONS**:
    - No player-level statistics (use MaxPreps for this)
    - No regular season schedules
    - Bracket-focused, not stats-focused
    - Does not cover NYC PSAL (separate league)
    """

    source_type = DataSourceType.NYSPHSAA
    source_name = "NYSPHSAA"
    base_url = "https://www.nysphsaa.org"
    region = DataSourceRegion.US_NY

    # NYSPHSAA specific constants
    # Note: NY uses letter classifications (AA, A, B, C, D) instead of numbers
    CLASSIFICATIONS = ["AA", "A", "B", "C", "D"]
    GENDERS = ["Boys", "Girls"]
    MIN_YEAR = 2015  # Historical data availability
    STATE_CODE = "NY"
    STATE_NAME = "New York"
    ORGANIZATION = "NYSPHSAA"

    def __init__(self):
        """Initialize NYSPHSAA datasource with New York-specific configuration."""
        super().__init__()
        self.settings = get_settings()
        self.logger.info(
            "NYSPHSAA initialized",
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

        **NYSPHSAA URL Format**:
        ```
        /sports/basketball/{gender}/brackets/{year}/{classification}/
        /sports/basketball/boys/brackets/2025/aa/
        /sports/basketball/girls/brackets/2025/a/

        Alternative patterns:
        /championships/{year}/basketball-{gender}-{classification}/
        /brackets/{year}-basketball-{classification}-{gender}
        ```

        Args:
            classification: Classification name (AA, A, B, C, D)
            gender: "Boys" or "Girls"
            year: Tournament year (optional)

        Returns:
            Full bracket URL
        """
        year = year or datetime.now().year
        gender_lower = gender.lower()
        class_lower = classification.lower()

        # Try multiple URL patterns (NYSPHSAA structure may vary)
        # Pattern 1: /sports/basketball/{gender}/brackets/{year}/{classification}
        url_pattern_1 = (
            f"{self.base_url}/sports/basketball/{gender_lower}/"
            f"brackets/{year}/{class_lower}"
        )

        # Pattern 2: /championships/{year}/basketball-{gender}-{classification}
        url_pattern_2 = (
            f"{self.base_url}/championships/{year}/basketball-{gender_lower}-{class_lower}"
        )

        # Return primary pattern (can try fallbacks in get_tournament_brackets)
        return url_pattern_1

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
            classification: Specific classification (AA, A, B, C, D), None for all
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
            f"Fetching NYSPHSAA tournament brackets",
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
                    f"Parsed NYSPHSAA bracket",
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
            f"Fetched all NYSPHSAA tournament brackets",
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

        NYSPHSAA bracket pages typically contain:
        - Tournament tree/bracket visualization
        - Game results in tables or divs
        - Team names with seeds
        - Scores for completed games
        - Section/state championship structure

        Args:
            soup: BeautifulSoup parsed HTML
            year: Tournament year
            classification: Classification name (AA, A, B, C, D)
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
        team1_id = canonical_team_id("nysphsaa", team1)
        team2_id = canonical_team_id("nysphsaa", team2)

        return Game(
            game_id=f"nysphsaa_{year}_{classification.lower()}_{team1_id.split('_', 1)[1]}_vs_{team2_id.split('_', 1)[1]}",
            home_team_id=team1_id,
            home_team_name=team1,
            away_team_id=team2_id,
            away_team_name=team2,
            home_score=score1,
            away_score=score2,
            status=GameStatus.FINAL if score1 is not None and score2 is not None else GameStatus.SCHEDULED,
            game_type=GameType.PLAYOFF,
            level="high_school_varsity",
            league=f"NYSPHSAA {classification}",
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
            league=f"NYSPHSAA {classification}",
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
        bracket_data = self._parse_bracket_html(soup, year, "AA", "Boys", "")
        return {
            "teams": bracket_data["teams"],
            "games": bracket_data["games"],
            "season": season,
        }

    async def get_player(self, player_id: str) -> Optional[Player]:
        self.logger.warning("NYSPHSAA does not provide player data - use MaxPreps for New York")
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
