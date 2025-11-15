"""
Minnesota Basketball Hub DataSource Adapter

Scrapes player and team statistics from Minnesota Basketball Hub.
One of the best free high school basketball stats hubs in the U.S.

Now supports Angular SPA rendering using browser automation.
Updated: 2025-11-11 - Added browser automation + updated URLs for 2025-26 season
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
from ...utils import (
    clean_player_name,
    extract_table_data,
    get_text_or_none,
    parse_float,
    parse_height_to_inches,
    parse_html,
    parse_int,
)
from ...utils.browser_client import BrowserClient
from ..base import BaseDataSource


class MNHubDataSource(BaseDataSource):
    """
    Minnesota Basketball Hub data source adapter with browser automation.

    The MN Hub website uses Angular for client-side rendering and has
    season-specific URLs, requiring browser automation to access stats.

    Integrated with Star Tribune Varsity platform.
    Public stats at https://stats.mnbasketballhub.com
    """

    source_type = DataSourceType.MN_HUB
    source_name = "Minnesota Basketball Hub"
    base_url = "https://stats.mnbasketballhub.com"
    region = DataSourceRegion.US

    def __init__(self):
        """Initialize MN Hub datasource with browser automation."""
        super().__init__()

        # Determine current season (format: 2025-26)
        now = datetime.now()
        if now.month >= 11:  # Season starts in November
            season_year = now.year
        else:
            season_year = now.year - 1

        self.current_season_year = season_year
        self.historical_url = f"{self.base_url}/historical-data"

        # Initialize browser client for Angular rendering
        # Browser settings optimized for MN Hub's Angular app
        self.browser_client = BrowserClient(
            settings=self.settings,
            browser_type=self.settings.browser_type if hasattr(self.settings, 'browser_type') else "chromium",
            headless=self.settings.browser_headless if hasattr(self.settings, 'browser_headless') else True,
            timeout=self.settings.browser_timeout if hasattr(self.settings, 'browser_timeout') else 60000,  # 60s for Angular + data loading
            cache_enabled=self.settings.browser_cache_enabled if hasattr(self.settings, 'browser_cache_enabled') else True,
            cache_ttl=self.settings.browser_cache_ttl if hasattr(self.settings, 'browser_cache_ttl') else 7200,
        )

        # Will be set by _find_available_season() on first use
        self.season = None
        self.leaderboards_url = None
        self._season_search_attempted = False

        self.logger.info(f"MN Hub initialized (will auto-detect available season)")

    async def close(self):
        """Close connections and browser instances."""
        await super().close()
        # Note: Browser is singleton, so we don't close it here

    async def _find_available_season(self) -> bool:
        """
        Find the first available season with published data using fallback strategy.

        Tries seasons in order: current → previous → 2 years ago → 3 years ago
        Updates self.season and self.leaderboards_url when found.

        Returns:
            True if a season was found, False otherwise
        """
        if self._season_search_attempted:
            return self.season is not None

        self._season_search_attempted = True

        # Generate seasons to try (current, -1, -2, -3 years)
        seasons_to_try = []
        for years_back in range(4):
            year = self.current_season_year - years_back
            season_str = f"{year}-{str(year + 1)[-2:]}"
            url = f"{self.base_url}/{season_str}-boys-basketball-stat-leaderboards"
            seasons_to_try.append((season_str, url))

        self.logger.info(
            f"Attempting season fallback detection (trying {len(seasons_to_try)} seasons)"
        )

        # Try each season URL to find one that works
        for season_str, url in seasons_to_try:
            try:
                self.logger.debug(f"Trying season: {season_str} at {url}")

                # Quick HEAD request to check if page exists (avoid full render)
                try:
                    response = await self.http_client.head(url, timeout=10.0)
                    status_code = response.status_code
                except Exception:
                    # If HEAD fails, try GET
                    response = await self.http_client.get(url, timeout=10.0)
                    status_code = response.status_code

                if status_code == 200:
                    self.logger.info(
                        f"✓ Found available season: {season_str}",
                        url=url,
                        status=status_code
                    )
                    self.season = season_str
                    self.leaderboards_url = url
                    return True
                elif status_code == 404:
                    self.logger.debug(
                        f"✗ Season {season_str} not found (404)",
                        url=url
                    )
                else:
                    self.logger.warning(
                        f"Unexpected status for season {season_str}: {status_code}",
                        url=url
                    )

            except Exception as e:
                self.logger.warning(
                    f"Error checking season {season_str}: {e}",
                    url=url
                )
                continue

        # No season found
        self.logger.error(
            "No available season found after trying all fallbacks",
            seasons_tried=[s[0] for s in seasons_to_try]
        )
        return False

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in MN Hub leaderboards.

        Uses browser automation to render Angular app and extract stats.
        Automatically detects available season using fallback strategy.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season (uses auto-detected season if None)
            limit: Maximum results

        Returns:
            List of Player objects
        """
        try:
            # Auto-detect available season if not already done
            if not await self._find_available_season():
                self.logger.error("No available season found - cannot fetch player stats")
                return []

            self.logger.info(f"Fetching MN Hub player stats (Angular rendering) - Season: {self.season}")

            # Use browser automation to render Angular app
            # Note: Page may not have data during off-season (November)
            try:
                html = await self.browser_client.get_rendered_html(
                    url=self.leaderboards_url,
                    wait_for="table:not([class*='gsc']):not([class*='gss'])",  # Wait for non-Google-Search tables
                    wait_timeout=self.browser_client.timeout,
                    wait_for_network_idle=True,  # Wait for Angular + data loading
                )
            except Exception as e:
                self.logger.warning(f"Stats table selector timeout, fetching anyway: {e}")
                html = await self.browser_client.get_rendered_html(
                    url=self.leaderboards_url,
                    wait_for_network_idle=True,
                )

            # Parse rendered HTML
            soup = parse_html(html)

            # Find stats tables (filter out Google Search tables)
            all_tables = soup.find_all("table")
            stats_tables = [
                table for table in all_tables
                if table.get("class") and not any(
                    cls.startswith(("gsc", "gss", "gstl")) for cls in table.get("class", [])
                )
            ]

            self.logger.info(f"Found {len(all_tables)} total tables, {len(stats_tables)} stats tables")

            if not stats_tables:
                self.logger.warning("No stats tables found on MN Hub leaderboards page after rendering")
                return []

            players = []
            seen_players = set()
            data_source = self.create_data_source_metadata(
                url=self.leaderboards_url, quality_flag=DataQualityFlag.PARTIAL
            )

            # Extract players from all tables
            for table in stats_tables:
                rows = extract_table_data(table)

                if not rows:
                    continue

                for row in rows:
                    player = self._parse_player_from_stats_row(row, data_source)
                    if not player:
                        continue

                    # Avoid duplicates
                    if player.player_id in seen_players:
                        continue

                    # Filter by name if provided
                    if name and name.lower() not in player.full_name.lower():
                        continue

                    # Filter by team if provided
                    if team and (
                        not player.team_name or team.lower() not in player.team_name.lower()
                    ):
                        continue

                    players.append(player)
                    seen_players.add(player.player_id)

                    if len(players) >= limit:
                        break

                if len(players) >= limit:
                    break

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
            # Common column names (may vary across tables)
            player_name = (
                row.get("Player") or
                row.get("NAME") or
                row.get("Name") or
                row.get("PLAYER")
            )

            team_name = (
                row.get("Team") or
                row.get("TEAM") or
                row.get("School")
            )

            position = row.get("Pos") or row.get("POS") or row.get("Position")

            if not player_name:
                return None

            # Clean player name
            player_name = clean_player_name(player_name)

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
            player_id = f"mnhub_{player_name.lower().replace(' ', '_').replace('.', '')}"

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "position": pos_enum,
                "team_name": team_name,
                "school_state": "MN",
                "school_country": "USA",
                "level": PlayerLevel.HIGH_SCHOOL,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Player, player_data, f"player {player_name}")

        except Exception as e:
            self.logger.error("Failed to parse player from row", error=str(e), row=row)
            return None

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        Note: MN Hub leaderboards don't have direct player profile pages.
        Need to search through leaderboards.

        Args:
            player_id: Player identifier

        Returns:
            Player object or None
        """
        # Extract player name from ID (format: mnhub_firstname_lastname)
        player_name = player_id.replace("mnhub_", "").replace("_", " ")

        # Search for player
        players = await self.search_players(name=player_name, limit=1)
        return players[0] if players else None

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics from leaderboards.

        Uses browser automation to render Angular app before extracting stats.
        Automatically detects available season using fallback strategy.

        Args:
            player_id: Player identifier
            season: Season (uses auto-detected season if None)

        Returns:
            PlayerSeasonStats object or None
        """
        try:
            # Auto-detect available season if not already done
            if not await self._find_available_season():
                self.logger.error("No available season found - cannot fetch stats")
                return None

            self.logger.info(f"Fetching season stats for player {player_id} - Season: {self.season}")

            # Render page with browser
            html = await self.browser_client.get_rendered_html(
                url=self.leaderboards_url,
                wait_for="table",
                wait_for_network_idle=True,
            )

            soup = parse_html(html)

            # Find all stats tables
            stats_tables = soup.find_all("table")

            if not stats_tables:
                self.logger.warning("No stats tables found")
                return None

            # Extract player name from ID
            player_name_from_id = player_id.replace("mnhub_", "").replace("_", " ")

            # Search all tables for player
            for table in stats_tables:
                rows = extract_table_data(table)

                for row in rows:
                    row_player_name = (
                        row.get("Player") or
                        row.get("NAME") or
                        row.get("Name", "")
                    )

                    # Clean and match player name
                    row_player_name = clean_player_name(row_player_name)

                    if row_player_name.lower() == player_name_from_id.lower():
                        return self._parse_season_stats_from_row(row, player_id)

            self.logger.warning(f"Player {player_id} not found in stats tables")
            return None

        except Exception as e:
            self.logger.error(f"Failed to get player season stats", player_id=player_id, error=str(e))
            return None

    def _parse_season_stats_from_row(self, row: dict, player_id: str) -> Optional[PlayerSeasonStats]:
        """Parse season stats from stats table row."""
        try:
            data_source = self.create_data_source_metadata(
                url=self.leaderboards_url, quality_flag=DataQualityFlag.PARTIAL
            )

            stats_data = {
                "player_id": player_id,
                "season": self.season,
                "games_played": parse_int(row.get("GP") or row.get("G") or row.get("Games") or row.get("GMS")),
                "points_per_game": parse_float(row.get("PPG") or row.get("PTS") or row.get("Points")),
                "rebounds_per_game": parse_float(row.get("RPG") or row.get("REB") or row.get("Rebounds")),
                "assists_per_game": parse_float(row.get("APG") or row.get("AST") or row.get("Assists")),
                "steals_per_game": parse_float(row.get("SPG") or row.get("STL") or row.get("Steals")),
                "blocks_per_game": parse_float(row.get("BPG") or row.get("BLK") or row.get("Blocks")),
                "field_goal_percentage": parse_float(row.get("FG%") or row.get("FG PCT")),
                "three_point_percentage": parse_float(row.get("3P%") or row.get("3PT%") or row.get("3PT PCT")),
                "free_throw_percentage": parse_float(row.get("FT%") or row.get("FT PCT")),
                "data_source": data_source,
            }

            return self.validate_and_log_data(
                PlayerSeasonStats, stats_data, f"season stats for {player_id}"
            )

        except Exception as e:
            self.logger.error("Failed to parse season stats", error=str(e), row=row)
            return None

    async def get_leaderboard(
        self, stat: str = "points", limit: int = 50
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        Uses browser automation to render Angular app before extracting leaderboard.
        Automatically detects available season using fallback strategy.

        Args:
            stat: Type of stat (points, rebounds, assists, etc.)
            limit: Maximum number of leaders to return

        Returns:
            List of leaderboard entries
        """
        try:
            # Auto-detect available season if not already done
            if not await self._find_available_season():
                self.logger.error("No available season found - cannot fetch leaderboard")
                return []

            self.logger.info(f"Fetching MN Hub {stat} leaderboard - Season: {self.season}")

            # Render leaderboards page
            html = await self.browser_client.get_rendered_html(
                url=self.leaderboards_url,
                wait_for="table",
                wait_for_network_idle=True,
            )

            soup = parse_html(html)

            # Find all stats tables
            stats_tables = soup.find_all("table")

            if not stats_tables:
                self.logger.warning("No stats tables found for leaderboard")
                return []

            # Map stat types to column names
            stat_column_map = {
                "points": ["PPG", "PTS", "Points"],
                "rebounds": ["RPG", "REB", "Rebounds"],
                "assists": ["APG", "AST", "Assists"],
                "steals": ["SPG", "STL", "Steals"],
                "blocks": ["BPG", "BLK", "Blocks"],
                "field_goal_pct": ["FG%", "FG PCT"],
                "three_point_pct": ["3P%", "3PT%", "3PT PCT"],
            }

            column_names = stat_column_map.get(stat, ["PPG"])

            # Search tables for matching stat column
            leaderboard = []

            for table in stats_tables:
                rows = extract_table_data(table)

                if not rows:
                    continue

                # Find matching column
                stat_column = None
                for col in column_names:
                    if col in rows[0]:
                        stat_column = col
                        break

                if not stat_column:
                    continue

                # Build leaderboard from this table
                for row in rows:
                    player_name = (
                        row.get("Player") or
                        row.get("NAME") or
                        row.get("Name")
                    )
                    stat_value = parse_float(row.get(stat_column))

                    if player_name and stat_value is not None:
                        leaderboard.append({
                            "player_name": clean_player_name(player_name),
                            "team_name": row.get("Team") or row.get("TEAM") or row.get("School"),
                            "stat_value": stat_value,
                            "stat_type": stat,
                        })

                # If we found data, stop searching tables
                if leaderboard:
                    break

            if not leaderboard:
                self.logger.warning(f"No leaderboard data found for {stat}")
                return []

            # Sort by stat value descending
            leaderboard.sort(key=lambda x: x["stat_value"], reverse=True)

            # Add ranks
            for i, entry in enumerate(leaderboard[:limit], 1):
                entry["rank"] = i

            self.logger.info(f"Generated {len(leaderboard[:limit])} leaderboard entries")
            return leaderboard[:limit]

        except Exception as e:
            self.logger.error("Failed to get leaderboard", stat=stat, error=str(e))
            return []

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player statistics for a specific game.

        Note: MN Hub leaderboards don't provide game-by-game breakdowns.
        This would require accessing individual game box scores.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            PlayerGameStats or None
        """
        self.logger.warning("get_player_game_stats not yet implemented for MN Hub")
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team by ID.

        Note: MN Hub has team pages but they're not yet scraped.
        Future implementation would parse team rosters.

        Args:
            team_id: Team identifier

        Returns:
            Team object or None
        """
        self.logger.warning("get_team not yet implemented for MN Hub")
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

        Note: MN Hub has schedule/game data but it's not yet scraped.
        Future implementation would parse schedules and game results.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            List of Game objects
        """
        self.logger.warning("get_games not yet implemented for MN Hub")
        return []
