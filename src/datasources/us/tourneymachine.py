"""
TournyMachine DataSource (Generic Tournament Platform)

Generic adapter for AAU-style tournaments hosted on TournyMachine platform.
Works with any tournament URL - walks Divisions → Brackets/Pools → Games → Scores.

This single adapter unlocks dozens of AAU events with zero per-event code.

Coverage: National (US) - any tournament on tourneymachine.com
Data: Teams, games, brackets, scores (when available)
"""

from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from ...models import (
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    Game,
    Player,
    PlayerGameStats,
    PlayerSeasonStats,
    Team,
)
from ..base import BaseDataSource


class TournyMachineDataSource(BaseDataSource):
    """
    TournyMachine adapter - generic tournament platform.

    Works with any tournament URL on tourneymachine.com.
    Walks: Tournament → Divisions → Brackets/Pools → Games
    """

    source_type = DataSourceType.TOURNEYMACHINE if hasattr(DataSourceType, 'TOURNEYMACHINE') else DataSourceType.GRIND_SESSION
    source_name = "TournyMachine"
    base_url = "https://www.tourneymachine.com"
    region = DataSourceRegion.US

    def __init__(self, tournament_id: Optional[str] = None):
        """
        Initialize TournyMachine adapter.

        Args:
            tournament_id: Specific tournament ID to track (optional)
        """
        super().__init__()
        self.tournament_id = tournament_id
        self.tournament_url = f"{self.base_url}/tournaments/{tournament_id}" if tournament_id else None

    async def get_tournament_info(self, tournament_id: str) -> Optional[dict]:
        """
        Get tournament metadata.

        Args:
            tournament_id: Tournament identifier

        Returns:
            Tournament info dict or None
        """
        try:
            url = f"{self.base_url}/tournaments/{tournament_id}"
            response = await self.http_client.get(url)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract tournament info
            title_elem = soup.find("h1", class_="tournament-title")
            date_elem = soup.find("div", class_="tournament-dates")
            location_elem = soup.find("div", class_="tournament-location")

            return {
                "tournament_id": tournament_id,
                "name": title_elem.text.strip() if title_elem else "",
                "dates": date_elem.text.strip() if date_elem else "",
                "location": location_elem.text.strip() if location_elem else "",
                "url": url,
            }

        except Exception as e:
            self.logger.error(f"Failed to get tournament info", error=str(e))
            return None

    async def get_divisions(self, tournament_id: str) -> list[dict]:
        """
        Get divisions/age groups for a tournament.

        Args:
            tournament_id: Tournament identifier

        Returns:
            List of division dicts
        """
        try:
            url = f"{self.base_url}/tournaments/{tournament_id}/divisions"
            response = await self.http_client.get(url)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            divisions = []

            # Parse divisions (TournyMachine structure)
            division_cards = soup.find_all("div", class_="division-card")

            for div_card in division_cards:
                div_id = div_card.get("data-division-id")
                div_name_elem = div_card.find("h3", class_="division-name")

                if div_name_elem and div_id:
                    divisions.append({
                        "division_id": div_id,
                        "name": div_name_elem.text.strip(),
                        "url": f"{url}/{div_id}",
                    })

            self.logger.info(f"Found {len(divisions)} divisions for tournament {tournament_id}")
            return divisions

        except Exception as e:
            self.logger.error(f"Failed to get divisions", error=str(e))
            return []

    async def get_teams_from_tournament(
        self, tournament_id: str, division_id: Optional[str] = None
    ) -> list[Team]:
        """
        Get all teams participating in a tournament.

        Args:
            tournament_id: Tournament identifier
            division_id: Optional division filter

        Returns:
            List of Team objects
        """
        try:
            url = f"{self.base_url}/tournaments/{tournament_id}/teams"
            if division_id:
                url = f"{url}?division={division_id}"

            response = await self.http_client.get(url)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            teams = []

            # Parse teams list
            team_items = soup.find_all("li", class_="team-item")

            for item in team_items:
                team_link = item.find("a", class_="team-link")
                if not team_link:
                    continue

                team_name = team_link.text.strip()
                team_id = team_link.get("data-team-id")

                # Extract location if available
                location_elem = item.find("span", class_="team-location")

                team = Team(
                    team_id=f"tm_{tournament_id}_{team_id or team_name}",
                    team_name=team_name,
                    city=location_elem.text.strip() if location_elem else None,
                    level="GRASSROOTS",
                    data_source=self.create_data_source_metadata(
                        url=url,
                        quality_flag=DataQualityFlag.COMPLETE,
                        notes=f"TournyMachine tournament {tournament_id}"
                    ),
                )
                teams.append(team)

            self.logger.info(f"Retrieved {len(teams)} teams from tournament {tournament_id}")
            return teams

        except Exception as e:
            self.logger.error(f"Failed to get teams", error=str(e))
            return []

    async def get_brackets(
        self, tournament_id: str, division_id: Optional[str] = None
    ) -> list[dict]:
        """
        Get bracket structure for a tournament.

        Args:
            tournament_id: Tournament identifier
            division_id: Optional division filter

        Returns:
            List of bracket data dicts
        """
        try:
            url = f"{self.base_url}/tournaments/{tournament_id}/brackets"
            if division_id:
                url = f"{url}/{division_id}"

            response = await self.http_client.get(url)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            brackets = []

            # Parse bracket rounds
            bracket_rounds = soup.find_all("div", class_="bracket-round")

            for round_div in bracket_rounds:
                round_name = round_div.get("data-round-name", "")
                matchups = round_div.find_all("div", class_="matchup")

                for matchup in matchups:
                    team1_elem = matchup.find("div", class_="team1")
                    team2_elem = matchup.find("div", class_="team2")

                    if team1_elem and team2_elem:
                        brackets.append({
                            "round": round_name,
                            "team1": team1_elem.text.strip(),
                            "team2": team2_elem.text.strip(),
                            "winner": matchup.get("data-winner"),
                        })

            self.logger.info(f"Retrieved {len(brackets)} bracket matchups")
            return brackets

        except Exception as e:
            self.logger.error(f"Failed to get brackets", error=str(e))
            return []

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID from TournyMachine.

        Note: Limited player data typically available.
        """
        self.logger.warning("get_player has limited data for TournyMachine")
        return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players across TournyMachine.

        Note: Player search typically not available.
        """
        self.logger.warning("search_players not typically available for TournyMachine")
        return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """Get player season stats - typically not available."""
        self.logger.warning("get_player_season_stats not available for TournyMachine")
        return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """Get player game stats - availability varies by tournament."""
        self.logger.warning("get_player_game_stats availability varies by tournament")
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get team info (uses get_teams_from_tournament)."""
        # Team ID format: tm_{tournament_id}_{team_id}
        parts = team_id.split("_")
        if len(parts) >= 3:
            tournament_id = parts[1]
            teams = await self.get_teams_from_tournament(tournament_id)
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
    ) -> list[Game]:
        """
        Get games from TournyMachine.

        Uses tournament_id if set, otherwise returns empty.
        """
        if not self.tournament_id:
            self.logger.warning("tournament_id not set - cannot retrieve games")
            return []

        try:
            url = f"{self.base_url}/tournaments/{self.tournament_id}/schedule"
            response = await self.http_client.get(url)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            games = []

            # Parse schedule table
            schedule_rows = soup.find_all("tr", class_="game-row")[:limit]

            for row in schedule_rows:
                # Extract game data
                date_elem = row.find("td", class_="game-date")
                time_elem = row.find("td", class_="game-time")
                court_elem = row.find("td", class_="court")
                team1_elem = row.find("td", class_="team1")
                team2_elem = row.find("td", class_="team2")
                score_elem = row.find("td", class_="score")

                if not all([team1_elem, team2_elem]):
                    continue

                team1 = team1_elem.text.strip()
                team2 = team2_elem.text.strip()

                # Filter by team if specified
                if team_id and team_id not in [f"tm_{self.tournament_id}_{team1}", f"tm_{self.tournament_id}_{team2}"]:
                    continue

                # Parse date/time
                game_date = None
                if date_elem and time_elem:
                    try:
                        date_str = f"{date_elem.text.strip()} {time_elem.text.strip()}"
                        game_date = datetime.strptime(date_str, "%m/%d/%Y %I:%M %p")
                    except:
                        pass

                # Filter by date range
                if game_date:
                    if start_date and game_date < start_date:
                        continue
                    if end_date and game_date > end_date:
                        continue

                # Parse score if available
                team1_score, team2_score = None, None
                if score_elem and "-" in score_elem.text:
                    try:
                        scores = score_elem.text.strip().split("-")
                        team1_score = int(scores[0].strip())
                        team2_score = int(scores[1].strip())
                    except:
                        pass

                game = Game(
                    game_id=f"tm_{self.tournament_id}_{team1}_{team2}_{date_elem.text if date_elem else ''}",
                    home_team=team1,
                    away_team=team2,
                    date=game_date,
                    venue=court_elem.text.strip() if court_elem else None,
                    status="COMPLETED" if team1_score is not None else "SCHEDULED",
                    home_score=team1_score,
                    away_score=team2_score,
                    data_source=self.create_data_source_metadata(
                        url=url,
                        quality_flag=DataQualityFlag.COMPLETE,
                        notes=f"TournyMachine tournament {self.tournament_id}"
                    ),
                )
                games.append(game)

            self.logger.info(f"Retrieved {len(games)} games from tournament {self.tournament_id}")
            return games

        except Exception as e:
            self.logger.error(f"Failed to get games", error=str(e))
            return []

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get leaderboard from TournyMachine.

        Note: Limited availability - depends on tournament tracking.
        """
        self.logger.warning("get_leaderboard availability varies by tournament")
        return []
