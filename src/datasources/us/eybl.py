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
        Search for players in EYBL leaderboard.

        Uses browser automation to render React app and extract leaderboard cards.
        Note: EYBL stats page shows leaderboards (top performers per category),
        not a complete player roster.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season (currently uses latest)
            limit: Maximum results

        Returns:
            List of Player objects from leaderboards
        """
        try:
            self.logger.info("Fetching EYBL player leaderboards (React rendering)")

            # Use browser automation to render React app
            # Wait for leaderboard container to appear (not table - EYBL uses custom divs)
            html = await self.browser_client.get_rendered_html(
                url=self.stats_url,
                wait_for=".sw-season-leaders",  # Wait for leaderboard container
                wait_timeout=self.browser_client.timeout,
                wait_for_network_idle=True,  # Wait for React to finish loading
            )

            # Parse rendered HTML
            soup = parse_html(html)

            # Find leaderboard cards (EYBL uses div-based layout, not tables)
            leader_cards = soup.find_all("div", class_="sw-leaders-card")

            if not leader_cards:
                self.logger.warning("No leaderboard cards found on EYBL stats page")
                return []

            self.logger.info(f"Found {len(leader_cards)} leaderboard categories")

            players = []
            data_source = self.create_data_source_metadata(
                url=self.stats_url, quality_flag=DataQualityFlag.PARTIAL
            )

            # Extract top players from each leaderboard card
            players_seen = set()  # Track duplicates across categories

            for card in leader_cards:
                # Extract category (e.g., "Points per Game")
                category_elem = card.find("div", class_="sw-leaders-card-category")
                category = category_elem.get_text(strip=True) if category_elem else "Unknown"

                # Find all player links in this card (top player + non-leaders)
                player_links = card.find_all("a", attrs={"data-sw-person-link": "true"})

                for link in player_links[:5]:  # Limit per category
                    player = self._parse_player_from_leaderboard_link(link, category, data_source)
                    if player and player.full_name not in players_seen:
                        # Filter by name if provided
                        if name and name.lower() not in player.full_name.lower():
                            continue

                        # Filter by team if provided
                        if team and (
                            not player.team_name or team.lower() not in player.team_name.lower()
                        ):
                            continue

                        players.append(player)
                        players_seen.add(player.full_name)

                        if len(players) >= limit:
                            break

                if len(players) >= limit:
                    break

            self.logger.info(f"Found {len(players)} unique players from leaderboards", filters={"name": name, "team": team})
            return players

        except Exception as e:
            self.logger.error("Failed to search players", error=str(e), error_type=type(e).__name__)
            return []

    def _parse_player_from_leaderboard_link(
        self, link_elem, category: str, data_source
    ) -> Optional[Player]:
        """
        Parse player from leaderboard link element.

        Args:
            link_elem: BeautifulSoup link element with data-sw-person-link attribute
            category: Stat category (e.g., "Points per Game")
            data_source: DataSource metadata

        Returns:
            Player object or None
        """
        try:
            # Extract player name from data attribute or link text
            player_name = link_elem.get("data-sw-person-link-person-name")

            if not player_name:
                # Fallback: get from link text
                text = link_elem.get_text(strip=True)
                # Remove rank number if present (e.g., "1. Jason Crowe Jr" -> "Jason Crowe Jr")
                if text and ". " in text:
                    player_name = text.split(". ", 1)[1]
                else:
                    player_name = text

            if not player_name:
                return None

            # Find team link (sibling or nearby)
            parent = link_elem.parent
            team_link = None
            team_name = None

            if parent:
                team_link = parent.find("a", attrs={"data-sw-team-link": "true"})
                if team_link:
                    team_name = team_link.get("data-sw-team-link-team-name") or team_link.get_text(strip=True)

            # Split name into first/last
            name_parts = player_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            else:
                first_name = player_name
                last_name = ""

            # Create player ID from name (sanitized)
            player_id = f"eybl_{player_name.lower().replace(' ', '_').replace('.', '')}"

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "team_name": team_name,
                "level": PlayerLevel.GRASSROOTS,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Player, player_data, f"player {player_name}")

        except Exception as e:
            self.logger.error("Failed to parse player from leaderboard link", error=str(e))
            return None

    def _parse_player_from_stats_row(self, row: dict, data_source) -> Optional[Player]:
        """
        Parse player from stats table row (legacy - tables no longer used).

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
        Get player season statistics from leaderboard page.

        Note: EYBL leaderboard shows category leaders, not complete stats tables.
        This method searches for the player across all leaderboard categories and
        extracts available stat values.

        Args:
            player_id: Player identifier
            season: Season (uses current if None)

        Returns:
            PlayerSeasonStats object or None (may have limited stats)
        """
        try:
            self.logger.info(f"Fetching season stats for player {player_id}")

            # Render page with browser
            html = await self.browser_client.get_rendered_html(
                url=self.stats_url,
                wait_for=".sw-season-leaders",
                wait_for_network_idle=True,
            )

            soup = parse_html(html)

            # Extract player name from ID (format: eybl_firstname_lastname)
            player_name_from_id = player_id.replace("eybl_", "").replace("_", " ").replace(".", "")

            # Find leaderboard cards
            leader_cards = soup.find_all("div", class_="sw-leaders-card")

            if not leader_cards:
                self.logger.warning("No leaderboard cards found")
                return None

            # Search for player across all leaderboards
            stats_data = {
                "player_id": player_id,
                "player_name": player_name_from_id,  # Required field
                "team_id": "unknown",  # Will update if found
                "season": season or str(datetime.now().year),
                "games_played": 0,  # Required field - will try to extract
            }
            player_found = False
            team_name = None

            for card in leader_cards:
                # Get category
                category_elem = card.find("div", class_="sw-leaders-card-category")
                category = category_elem.get_text(strip=True) if category_elem else ""

                # Find player links
                player_links = card.find_all("a", attrs={"data-sw-person-link": "true"})

                for link in player_links:
                    link_player_name = link.get("data-sw-person-link-person-name", "")

                    # Match player
                    if link_player_name.lower().replace(".", "") == player_name_from_id.lower():
                        player_found = True

                        # Extract team info if not already found
                        if team_name is None:
                            parent = link.parent
                            if parent:
                                team_link = parent.find("a", attrs={"data-sw-team-link": "true"})
                                if team_link:
                                    team_name = team_link.get("data-sw-team-link-team-name") or team_link.get_text(strip=True)
                                    if team_name:
                                        stats_data["team_id"] = f"eybl_{team_name.lower().replace(' ', '_')}"

                        # Found player! Extract stat value
                        # Find the stat value (usually in sibling div with class sw-leaders-*-result)
                        parent = link.parent
                        if parent:
                            result_elem = parent.find("div", class_=lambda x: x and "result" in str(x).lower())
                            if result_elem:
                                stat_value = parse_float(result_elem.get_text(strip=True))
                                # Map category to stat field
                                self._map_category_to_stat(category, stat_value, stats_data)

            # Only return stats if we found the player
            if player_found and len(stats_data) > 5:  # More than just the required base fields
                data_source = self.create_data_source_metadata(
                    url=self.stats_url, quality_flag=DataQualityFlag.PARTIAL
                )
                stats_data["data_source"] = data_source

                return self.validate_and_log_data(
                    PlayerSeasonStats, stats_data, f"season stats for {player_id}"
                )

            self.logger.warning(f"Player {player_id} not found in leaderboards")
            return None

        except Exception as e:
            self.logger.error(f"Failed to get player season stats", player_id=player_id, error=str(e))
            return None

    def _map_category_to_stat(self, category: str, value: float, stats_data: dict) -> None:
        """Map leaderboard category to stats field."""
        category_lower = category.lower()

        if "points" in category_lower or "ppg" in category_lower:
            stats_data["points_per_game"] = value
        elif "rebound" in category_lower or "rpg" in category_lower:
            stats_data["rebounds_per_game"] = value
        elif "assist" in category_lower or "apg" in category_lower:
            stats_data["assists_per_game"] = value
        elif "steal" in category_lower or "spg" in category_lower:
            stats_data["steals_per_game"] = value
        elif "block" in category_lower or "bpg" in category_lower:
            stats_data["blocks_per_game"] = value
        elif "fg%" in category_lower or "field goal" in category_lower:
            stats_data["field_goal_percentage"] = value / 100 if value > 1 else value
        elif "3p%" in category_lower or "three point" in category_lower:
            stats_data["three_point_percentage"] = value / 100 if value > 1 else value
        elif "ft%" in category_lower or "free throw" in category_lower:
            stats_data["free_throw_percentage"] = value / 100 if value > 1 else value

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
                wait_for=".sw-season-leaders",
                wait_for_network_idle=True,
            )

            soup = parse_html(html)

            # Find leaderboard cards
            leader_cards = soup.find_all("div", class_="sw-leaders-card")

            if not leader_cards:
                self.logger.warning("No leaderboard cards found")
                return []

            # Map stat types to category keywords
            category_keywords = {
                "points": ["points", "ppg"],
                "rebounds": ["rebound", "rpg"],
                "assists": ["assist", "apg"],
                "steals": ["steal", "spg"],
                "blocks": ["block", "bpg"],
                "field_goal_pct": ["fg%", "field goal"],
                "three_point_pct": ["3p%", "three point"],
            }

            keywords = category_keywords.get(stat_type, ["points"])

            # Find matching leaderboard card
            target_card = None
            for card in leader_cards:
                category_elem = card.find("div", class_="sw-leaders-card-category")
                if category_elem:
                    category = category_elem.get_text(strip=True).lower()
                    if any(kw in category for kw in keywords):
                        target_card = card
                        break

            if not target_card:
                self.logger.warning(f"No leaderboard card found for {stat_type}")
                return []

            # Extract players from card
            leaderboard = []
            player_links = target_card.find_all("a", attrs={"data-sw-person-link": "true"})

            for i, link in enumerate(player_links[:limit], 1):
                player_name = link.get("data-sw-person-link-person-name")

                # Get text if attribute not available
                if not player_name:
                    text = link.get_text(strip=True)
                    if ". " in text:
                        player_name = text.split(". ", 1)[1]
                    else:
                        player_name = text

                # Find team link
                parent = link.parent
                team_name = None
                if parent:
                    team_link = parent.find("a", attrs={"data-sw-team-link": "true"})
                    if team_link:
                        team_name = team_link.get("data-sw-team-link-team-name") or team_link.get_text(strip=True)

                # Find stat value
                stat_value = None
                if parent:
                    result_elem = parent.find("div", class_=lambda x: x and "result" in str(x).lower())
                    if result_elem:
                        stat_value = parse_float(result_elem.get_text(strip=True))

                if player_name:
                    leaderboard.append({
                        "rank": i,
                        "player_name": player_name,
                        "team_name": team_name,
                        "stat_value": stat_value,
                        "stat_type": stat_type,
                    })

            self.logger.info(f"Generated {len(leaderboard)} leaderboard entries")
            return leaderboard

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
