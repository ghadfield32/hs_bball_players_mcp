"""
KHSAA (Kentucky State Association) DataSource Adapter

Provides authoritative tournament brackets, seeds, scores, and championship results
for Kentucky high school basketball.

**Data Authority**: KHSAA is the source of truth for:
- Tournament brackets (16 classifications: Region 1, Region 2, Region 3, Region 4, Region 5, Region 6, Region 7, Region 8, Region 9, Region 10, Region 11, Region 12, Region 13, Region 14, Region 15, Region 16)
- Seeds and matchups
- Game dates, times, locations
- Final scores and champions
- Historical tournament data

**Base URL**: https://www.khsaa.org

**URL Pattern**:
```
Basketball: /sports/basketball/
Boys: /sports/basketball/boys/
Girls: /sports/basketball/girls/
Brackets: /brackets/{year}/
Playoffs: /playoffs/{year}/{classification}/
```

**Coverage**:
- Classifications: Region 1, Region 2, Region 3, Region 4, Region 5, Region 6, Region 7, Region 8, Region 9, Region 10, Region 11, Region 12, Region 13, Region 14, Region 15, Region 16 (enrollment-based)
- 280+ member schools
- Boys and Girls tournaments
- All regions of Kentucky

**Kentucky Basketball Context**:
- 280+ schools
- Strong basketball tradition
- KHSAA manages all high school athletics in Kentucky
- Enrollment-based classifications (Region 1 highest, Region 16 lowest)
- Regional tournaments → state championships

**Special Features**:
- Historical bracket data available
- Regional tournament structure
- Digital presence with bracket updates

**Limitations**:
- Player statistics NOT available (state associations focus on brackets/lineage)
- Regular season schedules typically on MaxPreps (separate source)
- Box scores rarely available

**Recommended Use**: KHSAA provides official tournament brackets.
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
from ...utils.result_parsers import parse_pdf_results, normalize_game_dict
from ..base_association import AssociationAdapterBase
from ...config import get_settings


class KentuckyKHSAADataSource(AssociationAdapterBase):
    """
    Kentucky KHSAA adapter.

    **PRIMARY PURPOSE**: Authoritative tournament bracket and postseason results.

    **COVERAGE**: 280+ schools with basketball programs.

    This adapter provides:
    1. Tournament brackets for all classifications (Region 1, Region 2, Region 3, Region 4, Region 5, Region 6, Region 7, Region 8, Region 9, Region 10, Region 11, Region 12, Region 13, Region 14, Region 15, Region 16)
    2. Seeds, matchups, dates, locations
    3. Game scores and final results
    4. Historical tournament data
    5. Regional and state championship results

    **ARCHITECTURE**:
    - Inherits from AssociationAdapterBase
    - Prioritizes HTML parsing (bracket pages)
    - Enumerates classifications: Region 1, Region 2, Region 3, Region 4, Region 5, Region 6, Region 7, Region 8, Region 9, Region 10, Region 11, Region 12, Region 13, Region 14, Region 15, Region 16
    - Generates unique game IDs: khsaa_{year}_{class}_{home}@{away}

    **DATA QUALITY**: HIGH (official source, authoritative)

    **LIMITATIONS**:
    - No player-level statistics (use MaxPreps for this)
    - No regular season schedules
    - Bracket-focused, not stats-focused
    """

    source_type = DataSourceType.KHSAA
    source_name = "KHSAA"
    base_url = "https://www.khsaa.org"
    region = DataSourceRegion.US_KY

    # KHSAA specific constants
    CLASSIFICATIONS = ["Region 1", "Region 2", "Region 3", "Region 4", "Region 5", "Region 6", "Region 7", "Region 8", "Region 9", "Region 10", "Region 11", "Region 12", "Region 13", "Region 14", "Region 15", "Region 16"]
    GENDERS = ["Boys", "Girls"]
    MIN_YEAR = 2015  # Historical data availability
    STATE_CODE = "KY"
    STATE_NAME = "Kentucky"
    ORGANIZATION = "KHSAA"

    def __init__(self):
        """Initialize KHSAA datasource with Kentucky-specific configuration."""
        super().__init__()
        self.settings = get_settings()
        self.logger.info(
            "KHSAA initialized",
            classifications=len(self.CLASSIFICATIONS),
            genders=len(self.GENDERS),
            min_year=self.MIN_YEAR,
            organization=self.ORGANIZATION,
        )

    def _build_pdf_url(
        self, gender: str = "Boys", year: Optional[int] = None
    ) -> str:
        """
        Build URL for Sweet 16 tournament PDF.

        **KHSAA URL Format** (PDF pattern - verified 2024-11-13):
        ```
        /basketball/{gender}/sweet16/{year}/{gender}statebracket{year}.pdf
        /basketball/boys/sweet16/2024/boystatebracket2024.pdf
        /basketball/girls/sweet16/2024/girlstatebracket2024.pdf
        ```

        KHSAA publishes PDF files with text-based game results:
        "Regional 1 - Game 1: Team A 73, Team B 60"
        "Sweet 16 Quarterfinal: Team C 85 vs Team D 78"

        Args:
            gender: "Boys" or "Girls"
            year: Tournament year (optional, e.g., 2024)

        Returns:
            Full PDF URL
        """
        year = year or datetime.now().year
        gender_lower = gender.lower()

        # KHSAA Sweet 16 PDF format (verified pattern)
        url = (
            f"{self.base_url}/basketball/{gender_lower}/sweet16/{year}/"
            f"{gender_lower}statebracket{year}.pdf"
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
        Get tournament results from Sweet 16 PDF.

        **KHSAA SOURCE TYPE**: PDF
        - Fetches Sweet 16 PDF with tournament game results
        - Parses text result lines using shared PDF parser
        - Example: "Regional 1 - Game 1: Team A 73, Team B 60"

        Args:
            season: Season string (e.g., "2024-25"), None for current
            classification: Ignored (Sweet 16 PDF contains all games)
            gender: "Boys" or "Girls"

        Returns:
            Dict with keys:
                - games: List[Game] - all tournament games
                - teams: List[Team] - all participating teams
                - brackets: Dict[str, List[Game]] - games grouped by classification
                - metadata: results metadata (year, source URL)
        """
        year = self._extract_year(season)
        season_str = f"{year-1}-{str(year)[2:]}"

        all_games: List[Game] = []
        all_teams: Dict[str, Team] = {}
        brackets: Dict[str, List[Game]] = {}
        metadata: Dict[str, Any] = {}

        self.logger.info(
            f"Fetching KHSAA tournament results (PDF pattern)",
            year=year,
            gender=gender,
        )

        try:
            # Fetch PDF
            url = self._build_pdf_url(gender, year)
            status, content, headers = await self.http_get(url, timeout=30.0)

            if status != 200:
                self.logger.warning(
                    f"Failed to fetch PDF",
                    status=status,
                    url=url,
                )
                return {
                    "games": [],
                    "teams": [],
                    "brackets": {},
                    "metadata": {"error": f"HTTP {status}", "url": url},
                    "year": year,
                    "gender": gender,
                }

            # Use shared PDF parser
            # Pattern: "Regional N - Game N: Team A 73, Team B 60"
            result_regex = (
                r"(?P<round>Regional \d+.*?|Sweet 16.*?|Semi[- ]?State.*?)"
                r"(?:Game \d+)?[:\-]?\s+"
                r"(?P<team_a>.+?)\s+(?P<score_a>\d+)"
                r"(?:\s*(?:vs|,|-)\s*)"
                r"(?P<team_b>.+?)\s+(?P<score_b>\d+)"
            )

            parsed_games = parse_pdf_results(
                pdf_content=content,
                state=self.STATE_CODE,
                year=year,
                result_regex=result_regex,
                page_range=None  # Parse all pages
            )

            self.logger.info(
                f"Parsed KHSAA PDF results",
                games=len(parsed_games),
            )

            # Convert parsed games to Game objects
            for game_dict in parsed_games:
                # Create Game object
                team1 = game_dict["team_a"]
                team2 = game_dict["team_b"]
                score1 = game_dict["score_a"]
                score2 = game_dict["score_b"]
                round_label = game_dict["round"]

                # Use canonical team IDs
                team1_id = canonical_team_id("khsaa", team1)
                team2_id = canonical_team_id("khsaa", team2)

                game = Game(
                    game_id=f"khsaa_{year}_{team1_id.split('_', 1)[1]}_vs_{team2_id.split('_', 1)[1]}",
                    home_team_id=team1_id,
                    home_team_name=team1,
                    away_team_id=team2_id,
                    away_team_name=team2,
                    home_score=score1,
                    away_score=score2,
                    status=GameStatus.FINAL,
                    game_type=GameType.PLAYOFF,
                    level="high_school_varsity",
                    league=f"KHSAA {round_label}",
                    season=season_str,
                    gender=gender.lower(),
                    data_source=self.create_data_source_metadata(
                        url=url, quality_flag=DataQualityFlag.VERIFIED
                    ),
                )
                all_games.append(game)

                # Create teams
                for name, tid in [(team1, team1_id), (team2, team2_id)]:
                    if tid not in all_teams:
                        all_teams[tid] = Team(
                            team_id=tid,
                            team_name=name,
                            school_name=name,
                            state=self.STATE_CODE,
                            country="USA",
                            level=TeamLevel.HIGH_SCHOOL_VARSITY,
                            league="KHSAA",
                            season=season_str,
                            data_source=self.create_data_source_metadata(
                                quality_flag=DataQualityFlag.VERIFIED
                            ),
                        )

            metadata = {"source_url": url, "source_type": "PDF"}

        except Exception as e:
            self.logger.error(
                f"Failed to fetch KHSAA PDF results",
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

        self.logger.info(
            f"Fetched KHSAA tournament results",
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

        KHSAA bracket pages typically contain:
        - Tournament tree/bracket visualization
        - Game results in tables or divs
        - Team names with seeds
        - Scores for completed games
        - Regional/state championship structure

        Args:
            soup: BeautifulSoup parsed HTML
            year: Tournament year
            classification: Classification name (Region 1, Region 2, Region 3, Region 4, Region 5, Region 6, Region 7, Region 8, Region 9, Region 10, Region 11, Region 12, Region 13, Region 14, Region 15, Region 16)
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
        team1_id = canonical_team_id("khsaa", team1)
        team2_id = canonical_team_id("khsaa", team2)

        return Game(
            game_id=f"khsaa_{year}_{classification.lower()}_{team1_id.split('_', 1)[1]}_vs_{team2_id.split('_', 1)[1]}",
            home_team_id=team1_id,
            home_team_name=team1,
            away_team_id=team2_id,
            away_team_name=team2,
            home_score=score1,
            away_score=score2,
            status=GameStatus.FINAL if score1 is not None and score2 is not None else GameStatus.SCHEDULED,
            game_type=GameType.PLAYOFF,
            level="high_school_varsity",
            league=f"KHSAA {classification}",
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
            league=f"KHSAA {classification}",
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
        bracket_data = self._parse_bracket_html(soup, year, "Region 1", "Boys", "")
        return {
            "teams": bracket_data["teams"],
            "games": bracket_data["games"],
            "season": season,
        }

    async def get_player(self, player_id: str) -> Optional[Player]:
        self.logger.warning("KHSAA does not provide player data - use MaxPreps for Kentucky")
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
