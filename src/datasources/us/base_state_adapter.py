"""
Base State Adapter Template

Abstract base class for US state high school basketball association adapters.
Enforces consistency and reduces duplication for state adapters added in Phase 25+.

This template provides:
1. Standardized bracket URL building with fallback patterns
2. Shared bracket parsing using src/utils/brackets.py utilities
3. Canonical team ID generation
4. Consistent game/team creation
5. Standard error handling and logging

Usage:
    Create a new state adapter by inheriting from StateAdapterBase:

    class NevadaNIAADataSource(StateAdapterBase):
        source_type = DataSourceType.NIAA
        source_name = "NIAA"
        base_url = "https://www.nevadapreps.com"
        region = DataSourceRegion.US_NV

        CLASSIFICATIONS = ["5A", "4A", "3A", "2A", "1A"]
        STATE_CODE = "NV"
        STATE_NAME = "Nevada"
        ORGANIZATION = "NIAA"

        def _build_bracket_url(self, classification, gender, year):
            return f"{self.base_url}/sports/basketball/{gender.lower()}/brackets/{year}/{classification.lower()}"

All standard methods are inherited. Only override if state has unique requirements.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from abc import abstractmethod

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
from ...utils.brackets import (
    parse_bracket_tables_and_divs,
    canonical_team_id,
    extract_team_seed,
    parse_block_meta
)
from ..base_association import AssociationAdapterBase
from ...config import get_settings


class StateAdapterBase(AssociationAdapterBase):
    """
    Abstract base class for state high school basketball association adapters.

    Child classes MUST define:
        - source_type: DataSourceType enum value
        - source_name: Human-readable source name (e.g., "NIAA")
        - base_url: State association base URL
        - region: DataSourceRegion enum value
        - CLASSIFICATIONS: List of classification names
        - STATE_CODE: Two-letter state abbreviation
        - STATE_NAME: Full state name
        - ORGANIZATION: State association acronym

    Child classes SHOULD override:
        - _build_bracket_url(): Customize URL pattern for state's website

    Child classes MAY override:
        - _parse_bracket_html(): If state has unique HTML structure
        - _create_game(): If state needs custom game metadata
        - _create_team(): If state needs custom team metadata
    """

    # Abstract class attributes - MUST be set by child classes
    source_type: DataSourceType = None  # type: ignore
    source_name: str = None  # type: ignore
    base_url: str = None  # type: ignore
    region: DataSourceRegion = None  # type: ignore

    CLASSIFICATIONS: List[str] = []
    GENDERS: List[str] = ["Boys", "Girls"]
    MIN_YEAR: int = 2015  # Default historical data availability
    STATE_CODE: str = None  # type: ignore
    STATE_NAME: str = None  # type: ignore
    ORGANIZATION: str = None  # type: ignore

    def __init__(self):
        """Initialize state adapter with configuration validation."""
        super().__init__()
        self.settings = get_settings()

        # Validate that child class set required attributes
        if self.STATE_CODE is None:
            raise NotImplementedError(f"{self.__class__.__name__} must define STATE_CODE")
        if self.STATE_NAME is None:
            raise NotImplementedError(f"{self.__class__.__name__} must define STATE_NAME")
        if self.ORGANIZATION is None:
            raise NotImplementedError(f"{self.__class__.__name__} must define ORGANIZATION")
        if not self.CLASSIFICATIONS:
            raise NotImplementedError(f"{self.__class__.__name__} must define CLASSIFICATIONS")

        self.logger.info(
            f"{self.ORGANIZATION} initialized",
            state=self.STATE_CODE,
            classifications=len(self.CLASSIFICATIONS),
            genders=len(self.GENDERS),
            min_year=self.MIN_YEAR,
        )

    @abstractmethod
    def _build_bracket_url(
        self, classification: str, gender: str = "Boys", year: Optional[int] = None
    ) -> str:
        """
        Build URL for specific tournament bracket.

        Child classes MUST implement this method with their state's URL pattern.

        Common patterns:
            Pattern 1: /sports/basketball/{gender}/brackets/{year}/{classification}/
            Pattern 2: /playoffs/{year}/basketball-{gender}-{classification}/
            Pattern 3: /{sport}/{year}/{classification}/{gender}/brackets/

        Args:
            classification: Classification name (e.g., "5A", "Division 1")
            gender: "Boys" or "Girls"
            year: Tournament year (optional, defaults to current year)

        Returns:
            Full bracket URL

        Example:
            def _build_bracket_url(self, classification, gender="Boys", year=None):
                year = year or datetime.now().year
                gender_lower = gender.lower()
                class_lower = classification.lower()
                return f"{self.base_url}/sports/basketball/{gender_lower}/brackets/{year}/{class_lower}"
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _build_bracket_url()"
        )

    def _extract_year(self, season: Optional[str]) -> int:
        """
        Extract year from season string.

        Supports formats:
            - "2024-25" → 2025
            - "2024" → 2024
            - None → current year

        Args:
            season: Season string (e.g., "2024-25")

        Returns:
            Tournament year as integer
        """
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

        Enumeration strategy:
        - If classification provided: fetch only that classification
        - Otherwise: fetch all classifications for the state

        Args:
            season: Season string (e.g., "2024-25"), None for current
            classification: Specific classification (None for all)
            gender: "Boys" or "Girls"

        Returns:
            Dict with keys:
                - games: List[Game] - all tournament games
                - teams: List[Team] - all participating teams
                - brackets: Dict[str, List[Game]] - games grouped by classification
                - metadata: bracket metadata
        """
        year = self._extract_year(season)
        classifications = [classification] if classification else self.CLASSIFICATIONS

        all_games: List[Game] = []
        all_teams: Dict[str, Team] = {}
        brackets: Dict[str, List[Game]] = {}
        metadata: Dict[str, Any] = {}

        self.logger.info(
            f"Fetching {self.ORGANIZATION} tournament brackets",
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
                    f"Parsed {self.ORGANIZATION} bracket",
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
            f"Fetched all {self.ORGANIZATION} tournament brackets",
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

        Uses shared utilities from src/utils/brackets.py:
        - parse_bracket_tables_and_divs: Extract matchups from HTML
        - canonical_team_id: Generate consistent team IDs
        - parse_block_meta: Extract page-level metadata (round, venue, tipoff)

        Args:
            soup: BeautifulSoup parsed HTML
            year: Tournament year
            classification: Classification name
            gender: Boys or Girls
            url: Source URL

        Returns:
            Dict with games, teams, metadata

        Override this method if state has unique HTML structure not handled
        by shared bracket utilities.
        """
        games: List[Game] = []
        teams: Dict[str, Team] = {}
        seen_ids = set()  # Deduplication
        season = f"{year-1}-{str(year)[2:]}"

        # Extract page-level metadata (round, venue, tipoff)
        page_meta = parse_block_meta(soup, year=year) or {}

        # Use shared bracket parser (handles both table and div layouts)
        for team1, team2, score1, score2 in parse_bracket_tables_and_divs(soup):
            if not team1 or not team2:
                continue

            # Create game with metadata
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
        """
        Create Game object from parsed data using canonical team IDs.

        Args:
            team1: Home team name
            team2: Away team name
            score1: Home team score (None if not played yet)
            score2: Away team score (None if not played yet)
            year: Tournament year
            classification: Classification name
            gender: Boys or Girls
            url: Source URL
            extra: Optional metadata (round, venue, tipoff)

        Returns:
            Game object

        Override this method if state needs custom game metadata or ID format.
        """
        # Use shared canonical team ID generator
        source_id = self.ORGANIZATION.lower()
        team1_id = canonical_team_id(source_id, team1)
        team2_id = canonical_team_id(source_id, team2)

        # Extract just the unique part after source prefix for game ID
        team1_short = team1_id.split('_', 1)[1] if '_' in team1_id else team1_id
        team2_short = team2_id.split('_', 1)[1] if '_' in team2_id else team2_id

        return Game(
            game_id=f"{source_id}_{year}_{classification.lower()}_{team1_short}_vs_{team2_short}",
            home_team_id=team1_id,
            home_team_name=team1,
            away_team_id=team2_id,
            away_team_name=team2,
            home_score=score1,
            away_score=score2,
            status=GameStatus.FINAL if score1 is not None and score2 is not None else GameStatus.SCHEDULED,
            game_type=GameType.PLAYOFF,
            level="high_school_varsity",
            league=f"{self.ORGANIZATION} {classification}",
            season=f"{year-1}-{str(year)[2:]}",
            gender=gender.lower(),
            data_source=self.create_data_source_metadata(
                url=url, quality_flag=DataQualityFlag.VERIFIED, extra=extra or {}
            ),
        )

    def _create_team(
        self, team_id: str, name: str, classification: str, season: str
    ) -> Team:
        """
        Create Team object.

        Args:
            team_id: Canonical team ID
            name: Team name
            classification: Classification name
            season: Season string

        Returns:
            Team object

        Override this method if state needs custom team metadata.
        """
        return Team(
            team_id=team_id,
            team_name=name,
            school_name=name,
            state=self.STATE_CODE,
            country="USA",
            level=TeamLevel.HIGH_SCHOOL_VARSITY,
            league=f"{self.ORGANIZATION} {classification}",
            season=season,
            data_source=self.create_data_source_metadata(
                quality_flag=DataQualityFlag.VERIFIED
            ),
        )

    # Required base methods (minimal implementation for bracket-only adapter)
    async def _parse_json_data(self, json_data: Dict, season: str) -> Dict:
        """Parse JSON data. Most state associations use HTML, not JSON."""
        return {"teams": [], "games": [], "season": season}

    async def _parse_html_data(self, html: str, season: str) -> Dict:
        """Parse HTML data using shared bracket parser."""
        year = self._extract_year(season)
        soup = parse_html(html)
        bracket_data = self._parse_bracket_html(
            soup, year, self.CLASSIFICATIONS[0] if self.CLASSIFICATIONS else "Default", "Boys", ""
        )
        return {
            "teams": bracket_data["teams"],
            "games": bracket_data["games"],
            "season": season,
        }

    # Player methods (state associations typically don't provide player data)
    async def get_player(self, player_id: str) -> Optional[Player]:
        """State associations don't provide player data - use MaxPreps."""
        self.logger.warning(f"{self.ORGANIZATION} does not provide player data")
        return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[Player]:
        """State associations don't provide player data."""
        return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """State associations don't provide player stats."""
        return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """State associations don't provide player stats."""
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID from tournament brackets."""
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
        """Get games from tournament brackets with optional filters."""
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
        """State associations don't provide leaderboards."""
        return []
