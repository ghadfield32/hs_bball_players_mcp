"""
GHSA (Georgia High School Association) DataSource Adapter

Provides tournament brackets, schedules, and results for Georgia high school basketball.
Major Southeast basketball state with strong talent pipeline to college/pro.

Base URL: https://www.ghsa.net
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
    Team,
    TeamLevel,
)
from ...utils import extract_table_data, get_text_or_none, parse_html, parse_int, parse_record
from ..base_association import AssociationAdapterBase


class GHSADataSource(AssociationAdapterBase):
    """
    Georgia High School Association data source adapter.

    Provides tournament brackets, schedules, and championship results.
    One of the top basketball talent states in the US.

    Coverage:
    - Tournament brackets (state championships)
    - Schedule data where available
    - Team rosters and records
    - Historical tournament data

    Limitations:
    - Player statistics not typically available
    - Schedules may be limited to tournament games
    """

    source_type = DataSourceType.GHSA
    source_name = "Georgia GHSA"
    base_url = "https://www.ghsa.net"
    region = DataSourceRegion.US_GA

    def _get_season_url(self, season: str) -> str:
        """Get URL for Georgia basketball season data."""
        # GHSA typically organizes by sport and year
        # Season 2024-25 maps to year 2025 for championship
        year = int(season.split("-")[0]) + 1
        return f"{self.base_url}/sports/basketball/boys/{year}"

    async def _parse_json_data(self, json_data: Dict[str, Any], season: str) -> Dict[str, Any]:
        """
        Parse JSON data from GHSA.

        GHSA may expose schedule/bracket data as JSON through calendar widgets.

        Args:
            json_data: JSON data from endpoint
            season: Season string

        Returns:
            Dict with teams, games, brackets
        """
        teams: List[Team] = []
        games: List[Game] = []

        # Parse based on JSON structure (to be implemented based on actual GHSA JSON format)
        # This is a template - actual implementation depends on GHSA's JSON schema

        if "teams" in json_data:
            for team_data in json_data.get("teams", []):
                team = self._parse_team_from_json(team_data, season)
                if team:
                    teams.append(team)

        if "games" in json_data or "schedule" in json_data:
            game_list = json_data.get("games") or json_data.get("schedule", [])
            for game_data in game_list:
                game = self._parse_game_from_json(game_data, season)
                if game:
                    games.append(game)

        self.logger.info(
            f"Parsed GHSA JSON data",
            season=season,
            teams=len(teams),
            games=len(games),
        )

        return {"teams": teams, "games": games, "season": season, "source": "json"}

    async def _parse_html_data(self, html: str, season: str) -> Dict[str, Any]:
        """
        Parse HTML data from GHSA.

        Extracts tournament brackets, schedules from HTML tables.

        Args:
            html: HTML content
            season: Season string

        Returns:
            Dict with teams, games, brackets
        """
        soup = parse_html(html)
        teams: List[Team] = []
        games: List[Game] = []

        # Look for bracket tables
        bracket_tables = soup.find_all("table", class_=["bracket", "tournament", "schedule"])

        for table in bracket_tables:
            # Extract games from bracket/schedule table
            rows = table.find_all("tr")

            for row in rows[1:]:  # Skip header
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    game = self._parse_game_from_row(cells, season)
                    if game:
                        games.append(game)

                        # Extract teams from game
                        if game.home_team_id and game.home_team_name:
                            teams.append(
                                self._create_team(game.home_team_id, game.home_team_name, season)
                            )
                        if game.away_team_id and game.away_team_name:
                            teams.append(
                                self._create_team(game.away_team_id, game.away_team_name, season)
                            )

        # Deduplicate teams by ID
        unique_teams = {team.team_id: team for team in teams}.values()
        teams = list(unique_teams)

        self.logger.info(
            f"Parsed GHSA HTML data",
            season=season,
            teams=len(teams),
            games=len(games),
        )

        return {"teams": teams, "games": games, "season": season, "source": "html"}

    def _parse_team_from_json(self, data: Dict[str, Any], season: str) -> Optional[Team]:
        """Parse team from JSON data."""
        try:
            team_name = data.get("name") or data.get("team_name")
            if not team_name:
                return None

            team_id = f"ghsa_{team_name.lower().replace(' ', '_')}"

            wins, losses = parse_record(data.get("record", ""))

            return Team(
                team_id=team_id,
                name=team_name,
                school=team_name,
                level=TeamLevel.HIGH_SCHOOL,
                conference=data.get("region") or data.get("classification"),
                season=season,
                wins=wins,
                losses=losses,
                data_source=self.create_data_source_metadata(
                    url=f"{self.base_url}/teams/{team_id}",
                    quality_flag=DataQualityFlag.VERIFIED,
                ),
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse team from JSON", error=str(e))
            return None

    def _parse_game_from_json(self, data: Dict[str, Any], season: str) -> Optional[Game]:
        """Parse game from JSON data."""
        try:
            home_team = data.get("home_team") or data.get("team1")
            away_team = data.get("away_team") or data.get("team2")

            if not home_team or not away_team:
                return None

            game_id = f"ghsa_{data.get('id', data.get('game_id', hash(str(data))))}"
            game_date_str = data.get("date") or data.get("game_date")
            game_date = None
            if game_date_str:
                try:
                    game_date = datetime.fromisoformat(game_date_str)
                except Exception:
                    pass

            return Game(
                game_id=game_id,
                home_team_name=home_team,
                away_team_name=away_team,
                home_team_id=f"ghsa_{home_team.lower().replace(' ', '_')}",
                away_team_id=f"ghsa_{away_team.lower().replace(' ', '_')}",
                game_date=game_date,
                game_type=GameType.TOURNAMENT,
                status=GameStatus.COMPLETED if data.get("final") else GameStatus.SCHEDULED,
                home_score=parse_int(data.get("home_score")),
                away_score=parse_int(data.get("away_score")),
                season=season,
                data_source=self.create_data_source_metadata(
                    url=f"{self.base_url}/games/{game_id}",
                    quality_flag=DataQualityFlag.VERIFIED,
                ),
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse game from JSON", error=str(e))
            return None

    def _parse_game_from_row(self, cells: List[Any], season: str) -> Optional[Game]:
        """Parse game from HTML table row."""
        try:
            if len(cells) < 3:
                return None

            # Typical bracket format: [Round, Team1 vs Team2, Score]
            home_team = get_text_or_none(cells[1])
            away_team = get_text_or_none(cells[2]) if len(cells) > 2 else None

            if not home_team or not away_team:
                return None

            # Try to extract score if present
            score_text = get_text_or_none(cells[3]) if len(cells) > 3 else None
            home_score = None
            away_score = None

            if score_text and "-" in score_text:
                parts = score_text.split("-")
                if len(parts) == 2:
                    home_score = parse_int(parts[0].strip())
                    away_score = parse_int(parts[1].strip())

            game_id = f"ghsa_{home_team.lower().replace(' ', '_')}_{away_team.lower().replace(' ', '_')}"

            return Game(
                game_id=game_id,
                home_team_name=home_team,
                away_team_name=away_team,
                home_team_id=f"ghsa_{home_team.lower().replace(' ', '_')}",
                away_team_id=f"ghsa_{away_team.lower().replace(' ', '_')}",
                game_type=GameType.TOURNAMENT,
                status=GameStatus.COMPLETED if home_score is not None else GameStatus.SCHEDULED,
                home_score=home_score,
                away_score=away_score,
                season=season,
                data_source=self.create_data_source_metadata(
                    url=f"{self.base_url}/basketball",
                    quality_flag=DataQualityFlag.UNVERIFIED,
                ),
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse game from HTML row", error=str(e))
            return None

    def _create_team(self, team_id: str, team_name: str, season: str) -> Team:
        """Create team object."""
        return Team(
            team_id=team_id,
            name=team_name,
            school=team_name,
            level=TeamLevel.HIGH_SCHOOL,
            season=season,
            data_source=self.create_data_source_metadata(
                url=f"{self.base_url}/teams",
                quality_flag=DataQualityFlag.UNVERIFIED,
            ),
        )
