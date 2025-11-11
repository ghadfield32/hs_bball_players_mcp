"""
UIL Brackets DataSource (University Interscholastic League - Texas)

Scrapes Texas UIL playoff brackets and postseason schedules.
Provides tournament brackets, game results, and team lineage (seeds, rounds).

Coverage: Texas (all classifications: 1A-6A)
Data: Playoff brackets, schedules, results (no box scores typically)
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


class UILBracketsDataSource(BaseDataSource):
    """
    UIL (University Interscholastic League) Brackets adapter.

    Provides playoff brackets and postseason schedules for Texas high school basketball.
    """

    source_type = DataSourceType.UIL_BRACKETS if hasattr(DataSourceType, 'UIL_BRACKETS') else DataSourceType.FHSAA
    source_name = "UIL Brackets"
    base_url = "https://www.uiltexas.org"
    region = DataSourceRegion.US_TX if hasattr(DataSourceRegion, 'US_TX') else DataSourceRegion.US

    # UIL playoff bracket endpoints
    brackets_url = f"{base_url}/athletics/basketball/brackets"
    schedule_url = f"{base_url}/athletics/basketball/schedules"

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        UIL doesn't provide individual player pages.

        Returns:
            None (not supported)
        """
        self.logger.warning("get_player not supported for UIL Brackets (schedule-only source)")
        return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        UIL doesn't provide player search.

        Returns:
            Empty list (not supported)
        """
        self.logger.warning("search_players not supported for UIL Brackets (schedule-only source)")
        return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        UIL doesn't provide player stats.

        Returns:
            None (not supported)
        """
        self.logger.warning("get_player_season_stats not supported for UIL Brackets")
        return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        UIL doesn't provide player game stats.

        Returns:
            None (not supported)
        """
        self.logger.warning("get_player_game_stats not supported for UIL Brackets")
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team information by ID.

        Args:
            team_id: Team identifier (typically school name)

        Returns:
            Team object or None
        """
        try:
            # UIL teams are accessed via bracket/schedule pages
            # For now, return basic team info
            return Team(
                team_id=f"uil_{team_id}",
                team_name=team_id,
                school_name=team_id,
                state="TX",
                level="HIGH_SCHOOL",
                data_source=self.create_data_source_metadata(
                    url=self.brackets_url,
                    quality_flag=DataQualityFlag.PARTIAL,
                    notes="UIL team info (bracket-only)"
                ),
            )

        except Exception as e:
            self.logger.error(f"Failed to get team {team_id}", error=str(e))
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
        Get playoff games from UIL brackets.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Season filter (e.g., "2024")
            limit: Maximum results

        Returns:
            List of Game objects
        """
        try:
            season = season or str(datetime.now().year)
            url = f"{self.schedule_url}/{season}"

            response = await self.http_client.get(url)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            games = []

            # Parse schedule table (typical UIL structure)
            schedule_table = soup.find("table", class_="schedule")
            if not schedule_table:
                return []

            rows = schedule_table.find_all("tr")[1:]  # Skip header

            for row in rows[:limit]:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                # Extract game data
                date_str = cols[0].text.strip()
                home_team = cols[1].text.strip()
                away_team = cols[2].text.strip()
                venue = cols[3].text.strip() if len(cols) > 3 else None
                result = cols[4].text.strip() if len(cols) > 4 else None

                # Filter by team if specified
                if team_id and team_id not in [home_team, away_team]:
                    continue

                # Parse date
                try:
                    game_date = datetime.strptime(date_str, "%m/%d/%Y")
                except:
                    game_date = None

                # Filter by date range
                if game_date:
                    if start_date and game_date < start_date:
                        continue
                    if end_date and game_date > end_date:
                        continue

                # Parse result if available
                home_score = None
                away_score = None
                if result and "-" in result:
                    try:
                        scores = result.split("-")
                        home_score = int(scores[0].strip())
                        away_score = int(scores[1].strip())
                    except:
                        pass

                game = Game(
                    game_id=f"uil_{season}_{home_team}_{away_team}_{date_str}",
                    home_team=home_team,
                    away_team=away_team,
                    date=game_date,
                    venue=venue,
                    status="COMPLETED" if result else "SCHEDULED",
                    home_score=home_score,
                    away_score=away_score,
                    data_source=self.create_data_source_metadata(
                        url=url,
                        quality_flag=DataQualityFlag.COMPLETE,
                        notes="UIL playoff schedule"
                    ),
                )
                games.append(game)

            self.logger.info(f"Retrieved {len(games)} games from UIL Brackets")
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
        UIL doesn't provide statistical leaderboards.

        Returns:
            Empty list (not supported)
        """
        self.logger.warning("get_leaderboard not supported for UIL Brackets (bracket-only)")
        return []

    async def get_brackets(
        self,
        season: Optional[str] = None,
        classification: Optional[str] = None,
        gender: Optional[str] = None,
    ) -> list[dict]:
        """
        Get playoff brackets from UIL.

        Args:
            season: Season year (e.g., "2024")
            classification: Classification filter ("1A", "2A", "3A", "4A", "5A", "6A")
            gender: Gender filter ("boys", "girls")

        Returns:
            List of bracket data dicts
        """
        try:
            season = season or str(datetime.now().year)
            url = f"{self.brackets_url}/{season}"

            if classification:
                url = f"{url}/{classification}"
            if gender:
                url = f"{url}/{gender}"

            response = await self.http_client.get(url)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            brackets = []

            # Parse bracket structure (typical UIL structure)
            bracket_divs = soup.find_all("div", class_="bracket")

            for bracket_div in bracket_divs:
                bracket_data = {
                    "classification": bracket_div.get("data-classification"),
                    "gender": bracket_div.get("data-gender"),
                    "round": bracket_div.get("data-round"),
                    "teams": [],
                }

                # Extract teams from bracket
                team_elements = bracket_div.find_all("div", class_="team")
                for team_elem in team_elements:
                    team_name = team_elem.text.strip()
                    seed = team_elem.get("data-seed")
                    bracket_data["teams"].append({
                        "name": team_name,
                        "seed": seed,
                    })

                brackets.append(bracket_data)

            self.logger.info(f"Retrieved {len(brackets)} brackets from UIL")
            return brackets

        except Exception as e:
            self.logger.error(f"Failed to get brackets", error=str(e))
            return []
