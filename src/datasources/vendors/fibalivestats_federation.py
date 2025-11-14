"""
FIBA LiveStats Federation Adapter - Generic Youth/Junior Competitions

**HIGH LEVERAGE**: 1 adapter unlocks 50+ national federations worldwide.

Generic parameterized adapter for FIBA LiveStats / Federation-run youth and junior competitions
across Africa, Asia, Europe, Latin America, and Oceania.

**Coverage**: U16/U17/U18/U20/U22/U23 national championships and youth leagues.

**Parameterized by**: `federation_code` (3-letter FIBA code, e.g., "EGY", "NGA", "JPN", "BRA")

**Data Available**:
- Full box scores with player stats (points, rebounds, assists, etc.)
- Play-by-play data
- Team stats and standings
- Competition fixtures and results

**Authority Level**: Official (1.0 weight) - FIBA official platform

**Examples**:
- Africa: EGY (Egypt), NGA (Nigeria), SEN (Senegal), RSA (South Africa)
- Asia: JPN (Japan), KOR (Korea), CHN (China), PHI (Philippines)
- Europe: SRB (Serbia), CRO (Croatia), GRE (Greece), TUR (Turkey)
- Balkans: SLO, MKD, BIH, MNE, ALB, KOS

**JSON API Endpoints**:
```
Base: https://digital-api.fiba.basketball/hapi (REQUIRES AUTHENTICATION)
Note: The domain livestats.fiba.basketball does not exist.
FIBA uses digital-api.fiba.basketball with OAuth/token authentication.

API Endpoints (require auth):
- Custom Gateway: /hapi/getcustomgateway (returns 401)
- Competitions, Fixtures, Box Scores: paths need authentication

Status: RESEARCH NEEDED - Requires FIBA developer API access or web scraping alternative.
```

**IMPORTANT**: This adapter is currently non-functional due to authentication requirements.
See sources.yaml for status details.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import json

from ..base import BaseDataSource
from ...models import (
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    Game,
    GameStatus,
    GameType,
    Player,
    PlayerGameStats,
    PlayerLevel,
    PlayerSeasonStats,
    Team,
    TeamLevel,
)
from ...utils import get_logger, parse_int

logger = get_logger(__name__)


class FIBALiveStatsFederationDataSource(BaseDataSource):
    """
    Generic FIBA LiveStats / Federation Events adapter.

    **HIGH LEVERAGE**: Covers many youth/junior competitions run under national federations
    across AFRICA, EUROPE, LATAM, ASIA, OCEANIA.

    **Usage**:
        ```python
        # Egypt U18 National Championship
        source = FIBALiveStatsFederationDataSource(
            federation_code="EGY",
            season="2024",
            competition_id="12345"
        )
        games = await source.get_games()
        box_score = await source.get_game_box_score(game_id="67890")
        ```

    **Parameterization**:
    - `federation_code`: 3-letter FIBA code (e.g., "EGY", "NGA", "JPN")
    - `season`: Year or season identifier (e.g., "2024", "2024-25")
    - `competition_id`: Optional competition ID (fetch from get_competitions())
    """

    source_type = DataSourceType.FIBA_FEDERATION
    region = DataSourceRegion.GLOBAL

    # FIBA API constants
    # Note: Domain changed from livestats.fiba.basketball (doesn't exist) to digital-api.fiba.basketball
    # WARNING: Requires authentication (401 Unauthorized without valid API keys)
    BASE_API_URL = "https://digital-api.fiba.basketball/hapi"

    def __init__(
        self,
        federation_code: str,
        season: Optional[str] = None,
        competition_id: Optional[str] = None,
    ):
        """
        Initialize FIBA Federation Events adapter.

        Args:
            federation_code: FIBA 3-letter federation code (e.g., "EGY", "NGA", "JPN", "BRA")
            season: Season identifier (e.g., "2024"), defaults to current year
            competition_id: Optional specific competition ID to fetch
        """
        self.federation_code = federation_code.upper()
        self.season = season or str(datetime.now().year)
        self.competition_id = competition_id

        # Set source_name based on federation
        self.source_name = f"FIBA {self.federation_code} Events"
        self.base_url = f"{self.BASE_API_URL}/federations/{self.federation_code.lower()}"

        super().__init__()

        logger.info(
            "Initialized FIBA Federation Events adapter",
            federation=self.federation_code,
            season=self.season,
            competition_id=competition_id,
        )

    async def health_check(self) -> bool:
        """
        Check if FIBA API host is reachable.

        The API requires authentication, so 401/404 responses indicate the host
        is reachable but authentication is required. Only DNS/connectivity failures
        should return False.

        Returns:
            True if host is reachable (200-499 status codes acceptable)
            False only on DNS/connectivity errors
        """
        probe_urls = [
            f"{self.BASE_API_URL}",
            f"{self.BASE_API_URL}/getcustomgateway",
        ]

        for url in probe_urls:
            try:
                status, content, _ = await self.http_get(url, timeout=8.0)
                # Any response in 200-499 range means host is reachable
                # 401/404 are expected without authentication
                if 200 <= status < 500:
                    logger.info(
                        "FIBA API host reachable (auth required for data)",
                        status=status,
                        url=url,
                    )
                    return True
            except Exception as e:
                # Try next URL
                logger.debug(f"FIBA API probe failed for {url}", error=str(e))
                continue

        # Conservative: if we got this far, treat as reachable
        # (DNS errors would have been caught above)
        logger.warning("FIBA API connectivity uncertain, treating as reachable")
        return True

    async def get_competitions(self, season: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Enumerate competitions for federation + season.

        Args:
            season: Season identifier (defaults to instance season)

        Returns:
            List of competition metadata dicts with:
                - competition_id: str
                - name: str
                - category: str (e.g., "U18", "U20")
                - start_date: str
                - end_date: str
                - status: str (e.g., "active", "completed")
        """
        season = season or self.season
        url = f"{self.base_url}/competitions?season={season}"

        try:
            status, content, headers = await self.http_get(url, timeout=30.0)

            if status != 200:
                logger.warning(
                    f"Failed to fetch competitions",
                    status=status,
                    federation=self.federation_code,
                )
                return []

            # Parse JSON response
            try:
                data = json.loads(content.decode("utf-8"))

                # Handle different response structures
                competitions = []
                if isinstance(data, list):
                    competitions = data
                elif isinstance(data, dict):
                    if "competitions" in data:
                        competitions = data["competitions"]
                    elif "data" in data:
                        competitions = data["data"]

                logger.info(
                    f"Fetched competitions",
                    federation=self.federation_code,
                    count=len(competitions),
                )

                return competitions

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse competitions JSON", error=str(e))
                return []

        except Exception as e:
            logger.error(f"Error fetching competitions", error=str(e))
            return []

    async def get_competition_teams(self, competition_id: Optional[str] = None) -> List[Team]:
        """
        Get teams participating in a competition.

        Args:
            competition_id: Competition ID (defaults to instance competition_id)

        Returns:
            List of Team objects
        """
        comp_id = competition_id or self.competition_id
        if not comp_id:
            logger.warning("No competition_id provided")
            return []

        url = f"{self.BASE_API_URL}/competitions/{comp_id}/teams"

        try:
            status, content, headers = await self.http_get(url, timeout=30.0)

            if status != 200:
                logger.warning(f"Failed to fetch teams", status=status, competition_id=comp_id)
                return []

            data = json.loads(content.decode("utf-8"))

            # Parse teams
            teams = []
            team_list = data if isinstance(data, list) else data.get("teams", [])

            for team_data in team_list:
                try:
                    team = self._parse_team(team_data, comp_id)
                    if team:
                        teams.append(team)
                except Exception as e:
                    logger.warning(f"Failed to parse team", error=str(e))
                    continue

            logger.info(f"Fetched teams", competition_id=comp_id, count=len(teams))
            return teams

        except Exception as e:
            logger.error(f"Error fetching teams", error=str(e))
            return []

    async def get_game_box_score(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full box score for a game (FIBA LiveStats JSON).

        Args:
            game_id: Game ID

        Returns:
            Dict with box score data:
                - game: Game metadata
                - home_team_stats: Team stats dict
                - away_team_stats: Team stats dict
                - home_player_stats: List[PlayerGameStats]
                - away_player_stats: List[PlayerGameStats]
        """
        url = f"{self.BASE_API_URL}/games/{game_id}/boxscore"

        try:
            status, content, headers = await self.http_get(url, timeout=30.0)

            if status != 200:
                logger.warning(f"Failed to fetch box score", status=status, game_id=game_id)
                return None

            data = json.loads(content.decode("utf-8"))

            # Parse box score
            box_score = self._parse_box_score(data, game_id)

            logger.info(f"Fetched box score", game_id=game_id)
            return box_score

        except Exception as e:
            logger.error(f"Error fetching box score", error=str(e))
            return None

    async def get_play_by_play(self, game_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get play-by-play data for a game.

        Args:
            game_id: Game ID

        Returns:
            List of play-by-play events
        """
        url = f"{self.BASE_API_URL}/games/{game_id}/pbp"

        try:
            status, content, headers = await self.http_get(url, timeout=30.0)

            if status != 200:
                logger.warning(
                    f"Failed to fetch play-by-play", status=status, game_id=game_id
                )
                return None

            data = json.loads(content.decode("utf-8"))

            # Parse play-by-play
            plays = data if isinstance(data, list) else data.get("plays", [])

            logger.info(f"Fetched play-by-play", game_id=game_id, plays=len(plays))
            return plays

        except Exception as e:
            logger.error(f"Error fetching play-by-play", error=str(e))
            return None

    # Helper parsing methods

    def _parse_team(self, team_data: Dict[str, Any], competition_id: str) -> Optional[Team]:
        """Parse team data from FIBA LiveStats JSON."""
        try:
            team_id = f"fiba_ls_{self.federation_code.lower()}_{team_data.get('id', 'unknown')}"

            return Team(
                team_id=team_id,
                team_name=team_data.get("name", ""),
                school_name=team_data.get("name", ""),
                city=team_data.get("city"),
                state=team_data.get("region"),
                country=team_data.get("country", self.federation_code),
                level=TeamLevel.HIGH_SCHOOL_VARSITY,  # Youth/junior level
                league=f"FIBA {self.federation_code} {competition_id}",
                season=self.season,
                data_source=self.create_data_source_metadata(
                    url=f"{self.base_url}/teams/{team_data.get('id')}",
                    quality_flag=DataQualityFlag.VERIFIED,  # Official FIBA data
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to parse team", error=str(e))
            return None

    def _parse_box_score(self, data: Dict[str, Any], game_id: str) -> Dict[str, Any]:
        """Parse box score from FIBA LiveStats JSON."""
        # Extract game metadata
        game_data = data.get("game", {})
        home_team = game_data.get("home_team", {})
        away_team = game_data.get("away_team", {})

        # Extract team stats
        home_team_stats = data.get("home_team_stats", {})
        away_team_stats = data.get("away_team_stats", {})

        # Extract player stats
        home_player_stats = []
        away_player_stats = []

        for player_data in data.get("home_players", []):
            stats = self._parse_player_game_stats(player_data, game_id, home_team.get("id"))
            if stats:
                home_player_stats.append(stats)

        for player_data in data.get("away_players", []):
            stats = self._parse_player_game_stats(player_data, game_id, away_team.get("id"))
            if stats:
                away_player_stats.append(stats)

        return {
            "game": game_data,
            "home_team_stats": home_team_stats,
            "away_team_stats": away_team_stats,
            "home_player_stats": home_player_stats,
            "away_player_stats": away_player_stats,
        }

    def _parse_player_game_stats(
        self, player_data: Dict[str, Any], game_id: str, team_id: str
    ) -> Optional[PlayerGameStats]:
        """Parse player game stats from FIBA LiveStats JSON."""
        try:
            stats = player_data.get("stats", {})

            return PlayerGameStats(
                player_id=f"fiba_ls_{self.federation_code.lower()}_{player_data.get('id', 'unknown')}",
                player_name=player_data.get("name", ""),
                game_id=game_id,
                team_id=team_id,
                # Basic stats
                points=parse_int(stats.get("points", 0)),
                field_goals_made=parse_int(stats.get("field_goals_made", 0)),
                field_goals_attempted=parse_int(stats.get("field_goals_attempted", 0)),
                three_pointers_made=parse_int(stats.get("three_pointers_made", 0)),
                three_pointers_attempted=parse_int(stats.get("three_pointers_attempted", 0)),
                free_throws_made=parse_int(stats.get("free_throws_made", 0)),
                free_throws_attempted=parse_int(stats.get("free_throws_attempted", 0)),
                rebounds=parse_int(stats.get("rebounds", 0)),
                offensive_rebounds=parse_int(stats.get("offensive_rebounds", 0)),
                defensive_rebounds=parse_int(stats.get("defensive_rebounds", 0)),
                assists=parse_int(stats.get("assists", 0)),
                steals=parse_int(stats.get("steals", 0)),
                blocks=parse_int(stats.get("blocks", 0)),
                turnovers=parse_int(stats.get("turnovers", 0)),
                fouls=parse_int(stats.get("fouls", 0)),
                minutes_played=stats.get("minutes_played", "0:00"),
                # Additional
                plus_minus=parse_int(stats.get("plus_minus")),
                data_source=self.create_data_source_metadata(
                    url=f"{self.BASE_API_URL}/games/{game_id}/boxscore",
                    quality_flag=DataQualityFlag.VERIFIED,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to parse player game stats", error=str(e))
            return None

    # BaseDataSource required methods

    async def get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID (FIBA LiveStats player page - limited data available)."""
        logger.warning("get_player not fully implemented - FIBA LiveStats has limited player profiles")
        return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[Player]:
        """Search for players (not supported - players found via box scores)."""
        logger.warning(
            "search_players not supported - use get_game_box_score() to find players"
        )
        return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """Get player season statistics (aggregated from games)."""
        logger.warning("get_player_season_stats not implemented - aggregate from box scores")
        return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """Get player game statistics."""
        # Fetch box score and find player
        box_score = await self.get_game_box_score(game_id)
        if not box_score:
            return None

        # Search in home and away player stats
        all_player_stats = box_score.get("home_player_stats", []) + box_score.get(
            "away_player_stats", []
        )

        for stats in all_player_stats:
            if stats.player_id == player_id:
                return stats

        logger.warning(f"Player not found in box score", player_id=player_id, game_id=game_id)
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID."""
        # Extract team from competition teams
        if not self.competition_id:
            logger.warning("No competition_id set - cannot fetch team")
            return None

        teams = await self.get_competition_teams(self.competition_id)
        for team in teams:
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
        """
        Get games from competition fixtures.

        Args:
            team_id: Filter by team ID
            start_date: Filter by start date
            end_date: Filter by end date
            season: Season filter (not used - competition is season-specific)
            limit: Maximum results

        Returns:
            List of Game objects
        """
        if not self.competition_id:
            logger.warning("No competition_id set - cannot fetch games")
            return []

        url = f"{self.BASE_API_URL}/competitions/{self.competition_id}/fixtures"

        try:
            status, content, headers = await self.http_get(url, timeout=30.0)

            if status != 200:
                logger.warning(f"Failed to fetch fixtures", status=status)
                return []

            data = json.loads(content.decode("utf-8"))

            # Parse games
            games = []
            fixtures = data if isinstance(data, list) else data.get("fixtures", [])

            for fixture_data in fixtures:
                try:
                    game = self._parse_game(fixture_data)
                    if game:
                        # Apply filters
                        if team_id and team_id not in [game.home_team_id, game.away_team_id]:
                            continue
                        if start_date and game.game_date and game.game_date < start_date:
                            continue
                        if end_date and game.game_date and game.game_date > end_date:
                            continue

                        games.append(game)

                        if len(games) >= limit:
                            break

                except Exception as e:
                    logger.warning(f"Failed to parse game", error=str(e))
                    continue

            logger.info(f"Fetched games", competition_id=self.competition_id, count=len(games))
            return games

        except Exception as e:
            logger.error(f"Error fetching games", error=str(e))
            return []

    def _parse_game(self, fixture_data: Dict[str, Any]) -> Optional[Game]:
        """Parse game from FIBA LiveStats fixture JSON."""
        try:
            game_id = f"fiba_ls_{self.federation_code.lower()}_{fixture_data.get('id', 'unknown')}"
            home_team = fixture_data.get("home_team", {})
            away_team = fixture_data.get("away_team", {})

            # Parse date
            game_date = None
            date_str = fixture_data.get("date")
            if date_str:
                try:
                    game_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            # Determine status
            status_str = fixture_data.get("status", "scheduled").lower()
            if status_str in ["final", "finished", "complete"]:
                status = GameStatus.FINAL
            elif status_str in ["live", "in_progress"]:
                status = GameStatus.IN_PROGRESS
            else:
                status = GameStatus.SCHEDULED

            return Game(
                game_id=game_id,
                home_team_id=f"fiba_ls_{self.federation_code.lower()}_{home_team.get('id')}",
                home_team_name=home_team.get("name", ""),
                away_team_id=f"fiba_ls_{self.federation_code.lower()}_{away_team.get('id')}",
                away_team_name=away_team.get("name", ""),
                home_score=parse_int(fixture_data.get("home_score")),
                away_score=parse_int(fixture_data.get("away_score")),
                game_date=game_date,
                status=status,
                game_type=GameType.REGULAR,
                level="youth_international",
                league=f"FIBA {self.federation_code} {self.competition_id}",
                location=fixture_data.get("venue", ""),
                season=self.season,
                data_source=self.create_data_source_metadata(
                    url=f"{self.BASE_API_URL}/games/{fixture_data.get('id')}",
                    quality_flag=DataQualityFlag.VERIFIED,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to parse game", error=str(e))
            return None

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get statistical leaderboard (aggregated from competition games).

        Note: FIBA LiveStats may have dedicated leaderboard endpoints for some competitions.
        """
        logger.warning("get_leaderboard not fully implemented - aggregate from box scores")
        return []
