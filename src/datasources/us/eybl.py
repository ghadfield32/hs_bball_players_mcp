"""
EYBL (Nike Elite Youth Basketball League) DataSource Adapter

Scrapes player and game statistics from Nike EYBL public pages.
Now supports React SPA rendering using browser automation.

Updated: 2025-11-11 - Added browser automation support for React website
"""

from datetime import datetime
from typing import Optional

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
    Position,
    Team,
    TeamLevel,
)
from ...utils import extract_table_data, get_text_or_none, parse_float, parse_html, parse_int
from ...utils.browser_client import BrowserClient
from ..base import BaseDataSource


class EYBLDataSource(BaseDataSource):
    """
    Nike EYBL data source adapter with browser automation support.

    The EYBL website uses React for client-side rendering, requiring
    browser automation to access stats tables.

    Provides access to Nike EYBL stats, schedules, standings, and leaderboards.
    Public stats pages at https://nikeeyb.com
    """

    source_type = DataSourceType.EYBL
    source_name = "Nike EYBL"
    base_url = "https://nikeeyb.com"
    region = DataSourceRegion.US

    def __init__(self):
        """Initialize EYBL datasource with browser automation."""
        super().__init__()

        # EYBL-specific endpoints
        self.stats_url = f"{self.base_url}/cumulative-season-stats"
        self.schedule_url = f"{self.base_url}/schedule"
        self.standings_url = f"{self.base_url}/standings"

        # Initialize browser client for React rendering
        # Browser settings optimized for EYBL's React app
        self.browser_client = BrowserClient(
            settings=self.settings,
            browser_type=self.settings.browser_type if hasattr(self.settings, 'browser_type') else "chromium",
            headless=self.settings.browser_headless if hasattr(self.settings, 'browser_headless') else True,
            timeout=self.settings.browser_timeout if hasattr(self.settings, 'browser_timeout') else 30000,
            cache_enabled=self.settings.browser_cache_enabled if hasattr(self.settings, 'browser_cache_enabled') else True,
            cache_ttl=self.settings.browser_cache_ttl if hasattr(self.settings, 'browser_cache_ttl') else 7200,
        )

    async def close(self):
        """Close connections and browser instances."""
        await super().close()
        # Note: Browser is singleton, so we don't close it here
        # It will be closed globally when needed

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        Note: EYBL doesn't have direct player profile pages accessible by ID.
        Need to search through stats tables.

        Args:
            player_id: Player identifier (EYBL uses player name as ID)

        Returns:
            Player object or None
        """
        # Search for player in current season stats
        players = await self.search_players(name=player_id, limit=1)
        return players[0] if players else None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in EYBL stats tables.

        Uses browser automation to render React app and extract stats table.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season (currently uses latest)
            limit: Maximum results

        Returns:
            List of Player objects
        """
        try:
            self.logger.info("Fetching EYBL player stats (React rendering)")

            # Use browser automation to render React app
            # Wait for table element to appear (React renders asynchronously)
            html = await self.browser_client.get_rendered_html(
                url=self.stats_url,
                wait_for="table",  # Wait for stats table to render
                wait_timeout=self.browser_client.timeout,
                wait_for_network_idle=True,  # Wait for React to finish loading
            )

            # Parse rendered HTML
            soup = parse_html(html)

            # Find stats table (same parsing as before, but now has data!)
            stats_table = soup.find("table", class_=lambda x: x and "stats" in str(x).lower())
            if not stats_table:
                # Try finding any table
                stats_table = soup.find("table")

            if not stats_table:
                self.logger.warning("No stats table found on EYBL stats page after rendering")
                return []

            # Extract table data
            rows = extract_table_data(stats_table)

            if not rows:
                self.logger.warning("Stats table found but no rows extracted")
                return []

            self.logger.info(f"Extracted {len(rows)} rows from EYBL stats table")

            players = []
            data_source = self.create_data_source_metadata(
                url=self.stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            for row in rows[:limit]:
                # Parse player from row
                player = self._parse_player_from_stats_row(row, data_source)
                if player:
                    # Filter by name if provided
                    if name and name.lower() not in player.full_name.lower():
                        continue

                    # Filter by team if provided
                    if team and (
                        not player.team_name or team.lower() not in player.team_name.lower()
                    ):
                        continue

                    players.append(player)

            self.logger.info(f"Found {len(players)} players", filters={"name": name, "team": team})
            return players

        except Exception as e:
            self.logger.error("Failed to search players", error=str(e), error_type=type(e).__name__)
            return []

    def _parse_player_from_stats_row(self, row: dict, data_source) -> Optional[Player]:
        """
        Parse player from stats table row.

        Args:
            row: Row dictionary from stats table
            data_source: DataSource metadata

        Returns:
            Player object or None
        """
        try:
            # Common column names (may vary)
            player_name = row.get("Player") or row.get("NAME") or row.get("Name")
            team_name = row.get("Team") or row.get("TEAM") or row.get("Club")
            position = row.get("Pos") or row.get("POS") or row.get("Position")

            if not player_name:
                return None

            # Split name into first/last
            name_parts = player_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            else:
                first_name = player_name
                last_name = ""

            # Parse position
            pos_enum = None
            if position:
                try:
                    pos_enum = Position(position.upper().strip())
                except ValueError:
                    pass

            # Create player ID from name (sanitized)
            player_id = f"eybl_{player_name.lower().replace(' ', '_')}"

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "position": pos_enum,
                "team_name": team_name,
                "level": PlayerLevel.GRASSROOTS,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Player, player_data, f"player {player_name}")

        except Exception as e:
            self.logger.error("Failed to parse player from row", error=str(e), row=row)
            return None

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics from cumulative stats page.

        Uses browser automation to render React app before extracting stats.

        Args:
            player_id: Player identifier
            season: Season (uses current if None)

        Returns:
            PlayerSeasonStats object or None
        """
        try:
            self.logger.info(f"Fetching season stats for player {player_id}")

            # Render page with browser
            html = await self.browser_client.get_rendered_html(
                url=self.stats_url,
                wait_for="table",
                wait_for_network_idle=True,
            )

            soup = parse_html(html)

            # Find stats table
            stats_table = soup.find("table", class_=lambda x: x and "stats" in str(x).lower())
            if not stats_table:
                stats_table = soup.find("table")

            if not stats_table:
                self.logger.warning("No stats table found")
                return None

            # Extract rows and find matching player
            rows = extract_table_data(stats_table)

            # Extract player name from ID (format: eybl_firstname_lastname)
            player_name_from_id = player_id.replace("eybl_", "").replace("_", " ")

            for row in rows:
                row_player_name = row.get("Player") or row.get("NAME") or row.get("Name", "")

                # Match player
                if row_player_name.lower() == player_name_from_id.lower():
                    return self._parse_season_stats_from_row(row, player_id)

            self.logger.warning(f"Player {player_id} not found in stats table")
            return None

        except Exception as e:
            self.logger.error(f"Failed to get player season stats", player_id=player_id, error=str(e))
            return None

    def _parse_season_stats_from_row(self, row: dict, player_id: str) -> Optional[PlayerSeasonStats]:
        """Parse season stats from stats table row."""
        try:
            data_source = self.create_data_source_metadata(
                url=self.stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            # Extract games played for calculating totals
            games = parse_int(row.get("GP") or row.get("G") or row.get("Games"))

            # Extract ORB/DRB per-game if available
            orb_pg = parse_float(row.get("ORPG") or row.get("ORB/G"))
            drb_pg = parse_float(row.get("DRPG") or row.get("DRB/G"))

            # Calculate totals from per-game if available
            orb_total = int(orb_pg * games) if orb_pg and games else None
            drb_total = int(drb_pg * games) if drb_pg and games else None

            stats_data = {
                "player_id": player_id,
                "season": str(datetime.now().year),
                "games_played": games,
                "points_per_game": parse_float(row.get("PPG") or row.get("PTS")),
                "rebounds_per_game": parse_float(row.get("RPG") or row.get("REB")),
                "offensive_rebounds_per_game": orb_pg,
                "defensive_rebounds_per_game": drb_pg,
                "offensive_rebounds": orb_total,
                "defensive_rebounds": drb_total,
                "assists_per_game": parse_float(row.get("APG") or row.get("AST")),
                "steals_per_game": parse_float(row.get("SPG") or row.get("STL")),
                "blocks_per_game": parse_float(row.get("BPG") or row.get("BLK")),
                "field_goal_percentage": parse_float(row.get("FG%")),
                "three_point_percentage": parse_float(row.get("3P%") or row.get("3PT%")),
                "free_throw_percentage": parse_float(row.get("FT%")),
                "data_source": data_source,
            }

            return self.validate_and_log_data(
                PlayerSeasonStats, stats_data, f"season stats for {player_id}"
            )

        except Exception as e:
            self.logger.error("Failed to parse season stats", error=str(e), row=row)
            return None

    async def get_leaderboard(
        self, stat_type: str = "points", limit: int = 50
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        Uses browser automation to render React app before extracting leaderboard.

        Args:
            stat_type: Type of stat (points, rebounds, assists, etc.)
            limit: Maximum number of leaders to return

        Returns:
            List of leaderboard entries
        """
        try:
            self.logger.info(f"Fetching EYBL {stat_type} leaderboard")

            # Render cumulative stats page
            html = await self.browser_client.get_rendered_html(
                url=self.stats_url,
                wait_for="table",
                wait_for_network_idle=True,
            )

            soup = parse_html(html)

            # Find stats table
            stats_table = soup.find("table", class_=lambda x: x and "stats" in str(x).lower())
            if not stats_table:
                stats_table = soup.find("table")

            if not stats_table:
                self.logger.warning("No stats table found for leaderboard")
                return []

            # Extract table data
            rows = extract_table_data(stats_table)

            # Map stat types to column names
            stat_column_map = {
                "points": ["PPG", "PTS", "Points"],
                "rebounds": ["RPG", "REB", "Rebounds"],
                "assists": ["APG", "AST", "Assists"],
                "steals": ["SPG", "STL", "Steals"],
                "blocks": ["BPG", "BLK", "Blocks"],
                "field_goal_pct": ["FG%"],
                "three_point_pct": ["3P%", "3PT%"],
            }

            column_names = stat_column_map.get(stat_type, ["PPG"])

            # Find matching column
            stat_column = None
            for col in column_names:
                if col in rows[0] if rows else {}:
                    stat_column = col
                    break

            if not stat_column:
                self.logger.warning(f"Stat column not found for {stat_type}")
                return []

            # Build leaderboard
            leaderboard = []
            for row in rows:
                player_name = row.get("Player") or row.get("NAME") or row.get("Name")
                stat_value = parse_float(row.get(stat_column))

                if player_name and stat_value is not None:
                    leaderboard.append({
                        "player_name": player_name,
                        "team_name": row.get("Team") or row.get("TEAM"),
                        "stat_value": stat_value,
                        "stat_type": stat_type,
                    })

            # Sort by stat value descending
            leaderboard.sort(key=lambda x: x["stat_value"], reverse=True)

            # Add ranks
            for i, entry in enumerate(leaderboard[:limit], 1):
                entry["rank"] = i

            self.logger.info(f"Generated {len(leaderboard[:limit])} leaderboard entries")
            return leaderboard[:limit]

        except Exception as e:
            self.logger.error("Failed to get leaderboard", stat_type=stat_type, error=str(e))
            return []

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player statistics for a specific game.

        Note: EYBL cumulative stats page doesn't provide game-by-game breakdowns.
        This would require accessing individual game box scores.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            PlayerGameStats or None
        """
        self.logger.warning("get_player_game_stats not yet implemented for EYBL")
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team by ID.

        Note: EYBL has team pages but they're not yet scraped.
        Future implementation would parse team rosters and standings.

        Args:
            team_id: Team identifier

        Returns:
            Team object or None
        """
        self.logger.warning("get_team not yet implemented for EYBL")
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
        Get games with optional filters.

        Note: EYBL has schedule pages but they're not yet scraped.
        Future implementation would parse schedule and game results.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            List of Game objects
        """
        self.logger.warning("get_games not yet implemented for EYBL")
        return []
