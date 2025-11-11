"""
Exposure Events DataSource (Exposure Basketball Events Platform)

Generic adapter for AAU-style tournaments hosted on Exposure Events platform.
Works with any event URL - walks Divisions → Pools/Brackets → Games → Box Scores.

This single adapter unlocks dozens of AAU events with zero per-event code.

Coverage: National (US) - any event on exposureevents.com
Data: Teams, games, rosters, box scores (when available)
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


class ExposureEventsDataSource(BaseDataSource):
    """
    Exposure Events adapter - generic AAU event platform.

    Works with any event URL on exposureevents.com.
    Walks: Event → Divisions → Pools/Brackets → Games → Box Scores
    """

    source_type = DataSourceType.EXPOSURE_EVENTS if hasattr(DataSourceType, 'EXPOSURE_EVENTS') else DataSourceType.GRIND_SESSION
    source_name = "Exposure Events"
    base_url = "https://www.exposureevents.com"
    region = DataSourceRegion.US

    def __init__(self, event_id: Optional[str] = None):
        """
        Initialize Exposure Events adapter.

        Args:
            event_id: Specific event ID to track (optional)
        """
        super().__init__()
        self.event_id = event_id
        self.event_url = f"{self.base_url}/events/{event_id}" if event_id else None

    async def get_event_info(self, event_id: str) -> Optional[dict]:
        """
        Get event metadata.

        Args:
            event_id: Event identifier

        Returns:
            Event info dict or None
        """
        try:
            url = f"{self.base_url}/events/{event_id}"
            response = await self.http_client.get(url)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract event info from page
            event_name = soup.find("h1", class_="event-title")
            event_date = soup.find("div", class_="event-date")
            event_location = soup.find("div", class_="event-location")

            return {
                "event_id": event_id,
                "name": event_name.text.strip() if event_name else "",
                "date": event_date.text.strip() if event_date else "",
                "location": event_location.text.strip() if event_location else "",
                "url": url,
            }

        except Exception as e:
            self.logger.error(f"Failed to get event info", error=str(e))
            return None

    async def get_divisions(self, event_id: str) -> list[dict]:
        """
        Get divisions/age groups for an event.

        Args:
            event_id: Event identifier

        Returns:
            List of division dicts
        """
        try:
            url = f"{self.base_url}/events/{event_id}/divisions"
            response = await self.http_client.get(url)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            divisions = []

            # Parse divisions (typical Exposure Events structure)
            division_links = soup.find_all("a", class_="division-link")

            for div_link in division_links:
                div_id = div_link.get("data-division-id")
                div_name = div_link.text.strip()

                divisions.append({
                    "division_id": div_id,
                    "name": div_name,
                    "url": f"{url}/{div_id}",
                })

            self.logger.info(f"Found {len(divisions)} divisions for event {event_id}")
            return divisions

        except Exception as e:
            self.logger.error(f"Failed to get divisions", error=str(e))
            return []

    async def get_teams_from_event(
        self, event_id: str, division_id: Optional[str] = None
    ) -> list[Team]:
        """
        Get all teams participating in an event.

        Args:
            event_id: Event identifier
            division_id: Optional division filter

        Returns:
            List of Team objects
        """
        try:
            url = f"{self.base_url}/events/{event_id}/teams"
            if division_id:
                url = f"{url}?division={division_id}"

            response = await self.http_client.get(url)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            teams = []

            # Parse teams table
            team_rows = soup.find_all("tr", class_="team-row")

            for row in team_rows:
                team_name_elem = row.find("td", class_="team-name")
                if not team_name_elem:
                    continue

                team_name = team_name_elem.text.strip()
                team_link = team_name_elem.find("a")
                team_id = team_link.get("data-team-id") if team_link else None

                # Extract additional info
                city_elem = row.find("td", class_="team-city")
                state_elem = row.find("td", class_="team-state")

                team = Team(
                    team_id=f"exposure_{event_id}_{team_id or team_name}",
                    team_name=team_name,
                    city=city_elem.text.strip() if city_elem else None,
                    state=state_elem.text.strip() if state_elem else None,
                    level="GRASSROOTS",
                    data_source=self.create_data_source_metadata(
                        url=url,
                        quality_flag=DataQualityFlag.COMPLETE,
                        notes=f"Exposure event {event_id}"
                    ),
                )
                teams.append(team)

            self.logger.info(f"Retrieved {len(teams)} teams from event {event_id}")
            return teams

        except Exception as e:
            self.logger.error(f"Failed to get teams", error=str(e))
            return []

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID from Exposure Events.

        Args:
            player_id: Player identifier

        Returns:
            Player object or None
        """
        try:
            url = f"{self.base_url}/players/{player_id}"
            response = await self.http_client.get(url)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract player info
            name_elem = soup.find("h1", class_="player-name")
            if not name_elem:
                return None

            full_name = name_elem.text.strip()
            name_parts = full_name.split()

            # Extract additional info
            height_elem = soup.find("div", class_="player-height")
            position_elem = soup.find("div", class_="player-position")
            grad_year_elem = soup.find("div", class_="grad-year")
            school_elem = soup.find("div", class_="player-school")

            return Player(
                player_id=f"exposure_{player_id}",
                first_name=name_parts[0] if name_parts else "",
                last_name=" ".join(name_parts[1:]) if len(name_parts) > 1 else "",
                full_name=full_name,
                height_inches=self._parse_height(height_elem.text.strip()) if height_elem else None,
                position=position_elem.text.strip() if position_elem else None,
                grad_year=int(grad_year_elem.text.strip()) if grad_year_elem and grad_year_elem.text.strip().isdigit() else None,
                school_name=school_elem.text.strip() if school_elem else None,
                level="GRASSROOTS",
                profile_url=url,
                data_source=self.create_data_source_metadata(
                    url=url,
                    quality_flag=DataQualityFlag.COMPLETE,
                ),
            )

        except Exception as e:
            self.logger.error(f"Failed to get player {player_id}", error=str(e))
            return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players across Exposure Events.

        Args:
            name: Player name filter
            team: Team name filter
            season: Season filter
            limit: Maximum results

        Returns:
            List of Player objects
        """
        try:
            params = {}
            if name:
                params["name"] = name
            if team:
                params["team"] = team
            if season:
                params["season"] = season

            url = f"{self.base_url}/search/players"
            response = await self.http_client.get(url, params=params)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            players = []

            # Parse search results
            result_rows = soup.find_all("tr", class_="player-result")[:limit]

            for row in result_rows:
                player_link = row.find("a", class_="player-link")
                if not player_link:
                    continue

                player_id = player_link.get("data-player-id")
                if player_id:
                    player = await self.get_player(player_id)
                    if player:
                        players.append(player)

            self.logger.info(f"Found {len(players)} players matching search")
            return players

        except Exception as e:
            self.logger.error(f"Failed to search players", error=str(e))
            return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season stats from Exposure Events.

        Note: Limited stat availability - depends on event tracking.
        """
        self.logger.warning("get_player_season_stats has limited data for Exposure Events")
        return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game stats from Exposure Events.

        Note: Box scores available only if event provides them.
        """
        self.logger.warning("get_player_game_stats availability varies by event")
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get team info (uses get_teams_from_event)."""
        # Team ID format: exposure_{event_id}_{team_id}
        parts = team_id.split("_")
        if len(parts) >= 3:
            event_id = parts[1]
            teams = await self.get_teams_from_event(event_id)
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
        Get games from Exposure Events.

        Uses event_id if set, otherwise returns empty.
        """
        if not self.event_id:
            self.logger.warning("event_id not set - cannot retrieve games")
            return []

        try:
            url = f"{self.base_url}/events/{self.event_id}/schedule"
            response = await self.http_client.get(url)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            games = []

            # Parse schedule table
            game_rows = soup.find_all("tr", class_="game-row")[:limit]

            for row in game_rows:
                # Extract game data
                date_elem = row.find("td", class_="game-date")
                time_elem = row.find("td", class_="game-time")
                home_team_elem = row.find("td", class_="home-team")
                away_team_elem = row.find("td", class_="away-team")
                venue_elem = row.find("td", class_="venue")
                score_elem = row.find("td", class_="score")

                if not all([home_team_elem, away_team_elem]):
                    continue

                home_team = home_team_elem.text.strip()
                away_team = away_team_elem.text.strip()

                # Filter by team if specified
                if team_id and team_id not in [f"exposure_{self.event_id}_{home_team}", f"exposure_{self.event_id}_{away_team}"]:
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
                home_score, away_score = None, None
                if score_elem and "-" in score_elem.text:
                    try:
                        scores = score_elem.text.strip().split("-")
                        home_score = int(scores[0].strip())
                        away_score = int(scores[1].strip())
                    except:
                        pass

                game = Game(
                    game_id=f"exposure_{self.event_id}_{home_team}_{away_team}_{date_elem.text if date_elem else ''}",
                    home_team=home_team,
                    away_team=away_team,
                    date=game_date,
                    venue=venue_elem.text.strip() if venue_elem else None,
                    status="COMPLETED" if home_score is not None else "SCHEDULED",
                    home_score=home_score,
                    away_score=away_score,
                    data_source=self.create_data_source_metadata(
                        url=url,
                        quality_flag=DataQualityFlag.COMPLETE,
                        notes=f"Exposure event {self.event_id}"
                    ),
                )
                games.append(game)

            self.logger.info(f"Retrieved {len(games)} games from event {self.event_id}")
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
        Get leaderboard from Exposure Events.

        Note: Limited availability - depends on event tracking.
        """
        self.logger.warning("get_leaderboard availability varies by event")
        return []

    def _parse_height(self, height_str: str) -> Optional[int]:
        """Parse height string to inches."""
        try:
            if "'" in height_str or '"' in height_str:
                # Format: 6'2" or 6'2
                parts = height_str.replace('"', '').split("'")
                feet = int(parts[0])
                inches = int(parts[1]) if len(parts) > 1 and parts[1].strip() else 0
                return feet * 12 + inches
        except:
            pass
        return None
