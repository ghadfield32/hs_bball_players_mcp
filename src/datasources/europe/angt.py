"""
ANGT (Adidas Next Generation Tournament) DataSource Adapter

Scrapes player statistics from EuroLeague Next Generation Tournament.
ANGT is the premier U18 club tournament in Europe.

Implementation Status: ACTIVATED (2025-11-16)
Website Inspection Findings:
1. Base URL: https://www.euroleaguebasketball.net/ngt
2. JavaScript-rendered stats (React/AJAX) - requires browser automation
3. URL patterns: /ngt/stats, /ngt/players, /ngt/teams, /ngt/game-center
4. Current season: 2025-26
5. Stats available: PIR, Points, Assists, Rebounds, Steals, Blocks
6. Filters: statisticMode, seasonMode, sortDirection, statistic
7. Pagination: size parameter (up to 1000 entries)
"""

from datetime import datetime
from typing import Optional

from ...models import (
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    Game,
    Player,
    PlayerGameStats,
    PlayerLevel,
    PlayerSeasonStats,
    Team,
    TeamLevel,
)
from ...utils import (
    build_leaderboard_entry,
    clean_player_name,
    extract_table_data,
    find_stat_table,
    get_text_or_none,
    parse_float,
    parse_html,
    parse_int,
    parse_player_from_row,
    parse_season_stats_from_row,
)
from ...utils.browser_client import BrowserClient
from ..base import BaseDataSource


class ANGTDataSource(BaseDataSource):
    """
    ANGT (Adidas Next Generation Tournament) datasource adapter.

    Provides access to player stats from European U18 elite tournaments.

    ANGT Structure:
    - Annual tournament featuring youth teams from top European clubs
    - Clubs include: Real Madrid, Barcelona, Maccabi, Olympiacos, Zalgiris, etc.
    - Tournament format: Group stage + knockout rounds
    - Stats include PIR (Performance Index Rating) - EuroLeague's efficiency metric
    - Uses EuroLeague's comprehensive data system
    """

    source_type = DataSourceType.ANGT
    source_name = "ANGT (Next Generation)"
    base_url = "https://www.euroleaguebasketball.net/ngt"
    region = DataSourceRegion.EUROPE

    def __init__(self):
        """Initialize ANGT datasource with browser automation."""
        super().__init__()

        # ANGT URLs (verified 2025-11-16)
        # Base: https://www.euroleaguebasketball.net/ngt
        # JavaScript-rendered (React/AJAX) - requires browser automation

        self.stats_url = f"{self.base_url}/stats"
        self.players_url = f"{self.base_url}/players"
        self.teams_url = f"{self.base_url}/teams"
        self.games_url = f"{self.base_url}/game-center"

        # Stats filters (for API parameters)
        # statisticMode: total, perGame, per40Minutes
        # seasonMode: Season, Tournament
        # statistic: PIR, points, assists, rebounds, steals, blocks
        # sortDirection: asc, desc
        # size: pagination limit (default 25, max appears to be 1000)

        # Current season (verified from website)
        self.current_season = "2025-26"

        # Initialize browser client for JavaScript rendering
        # ANGT uses React to load stats from API, requires browser automation
        self.browser_client = BrowserClient(
            settings=self.settings,
            browser_type=self.settings.browser_type if hasattr(self.settings, 'browser_type') else "chromium",
            headless=self.settings.browser_headless if hasattr(self.settings, 'browser_headless') else True,
            timeout=self.settings.browser_timeout if hasattr(self.settings, 'browser_timeout') else 60000,
            cache_enabled=self.settings.browser_cache_enabled if hasattr(self.settings, 'browser_cache_enabled') else True,
            cache_ttl=self.settings.browser_cache_ttl if hasattr(self.settings, 'browser_cache_ttl') else 3600,
        )

        self.logger.info(
            "ANGT initialized with browser automation",
            base_url=self.base_url,
            stats_url=self.stats_url
        )

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID from ANGT.

        Args:
            player_id: ANGT player identifier (format: angt_firstname_lastname)

        Returns:
            Player object or None
        """
        # Pattern: Use search_players to find player
        # ANGT may also support direct player lookup via /player/{player-code}
        players = await self.search_players(
            name=player_id.replace("angt_", ""), limit=1
        )
        return players[0] if players else None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in ANGT tournaments.

        Uses browser automation to render JavaScript-based stats (React/AJAX).
        ANGT website loads stats dynamically from EuroLeague API after page load.

        Args:
            name: Player name filter (partial match)
            team: Team/club name filter
            season: Season filter (e.g., "2025-26"), defaults to current
            limit: Maximum results

        Returns:
            List of Player objects
        """
        try:
            self.logger.info("Fetching ANGT player stats (browser automation with React)")

            # Use browser automation for JavaScript-rendered stats
            from playwright.async_api import async_playwright
            import asyncio

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.browser_client.headless
                )
                page = await browser.new_page()

                # Build URL with query parameters for better data loading
                # size=1000 gets max players in one page (efficient)
                # statistic=PIR gets players sorted by Performance Index Rating
                stats_url = f"{self.stats_url}?size=1000&statistic=PIR&statisticMode=perGame"

                self.logger.debug(f"Loading ANGT stats page: {stats_url}")
                await page.goto(stats_url, wait_until="networkidle", timeout=60000)

                # Wait for React table to render
                # ANGT likely uses standard table or div-based table structure
                self.logger.debug("Waiting for stats table to load...")

                # Try multiple selectors (React apps vary)
                table_selectors = [
                    "table",  # Standard table
                    "div[class*='table']",  # Div-based table
                    "div[class*='stats']",  # Stats container
                    "div[class*='players']",  # Players container
                ]

                table_loaded = False
                for selector in table_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                        self.logger.debug(f"Found stats table with selector: {selector}")
                        table_loaded = True
                        break
                    except:
                        continue

                if not table_loaded:
                    self.logger.warning("No stats table found, waiting for network idle")

                # Wait for network to settle (React may still be loading)
                await asyncio.sleep(5)

                # Get rendered HTML
                html = await page.content()
                await browser.close()

                self.logger.debug("ANGT stats loaded successfully")

            # Parse rendered HTML
            soup = parse_html(html)

            # Find stats table (EuroLeague standard structure)
            table = soup.find("table") or soup.find("div", class_=lambda x: x and "table" in x.lower())

            if not table:
                self.logger.warning("No stats table found in ANGT page")
                return []

            # Extract rows
            rows = table.find_all("tr") if hasattr(table, 'find_all') else []
            self.logger.info(f"Found {len(rows)} rows in ANGT stats table")

            if not rows:
                return []

            players = []
            seen_players = set()

            data_source = self.create_data_source_metadata(
                url=stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            # Skip header row
            data_rows = rows[1:] if len(rows) > 1 else []

            for row in data_rows:
                cells = row.find_all("td")
                if len(cells) < 3:  # Need at least player, club, stat
                    continue

                # Parse row into player
                # ANGT format (typical): Player | Club | Games | Points | Rebounds | Assists | PIR
                player_text = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                club_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""

                if not player_text:
                    continue

                # Clean player name
                player_name = clean_player_name(player_text)
                if not player_name:
                    continue

                # Split name into first/last
                name_parts = player_name.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = " ".join(name_parts[1:])
                else:
                    first_name = ""
                    last_name = player_name

                # Generate player ID
                player_id = f"angt_{player_name.lower().replace(' ', '_')}"

                # Avoid duplicates
                if player_id in seen_players:
                    continue

                # Apply filters
                if name and name.lower() not in player_name.lower():
                    continue
                if team and (not club_text or team.lower() not in club_text.lower()):
                    continue

                # Create Player object
                player = Player(
                    player_id=player_id,
                    first_name=first_name,
                    last_name=last_name,
                    full_name=player_name,
                    team_name=club_text if club_text else None,
                    level=PlayerLevel.YOUTH,  # ANGT is U18
                    data_source=data_source,
                )

                players.append(player)
                seen_players.add(player_id)

                if len(players) >= limit:
                    break

            self.logger.info(f"Found {len(players)} ANGT players", filters={"name": name, "team": team})
            return players

        except Exception as e:
            self.logger.error("Failed to search ANGT players", error=str(e))
            return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player tournament statistics from ANGT.

        IMPLEMENTATION STEPS:
        1. The stats table from search_players() contains tournament averages
        2. Find the player's row in that table
        3. Parse their statistics using parse_season_stats_from_row()
        4. Include PIR (Performance Index Rating) if available
        5. ANGT provides comprehensive stats via EuroLeague system
        6. Return PlayerSeasonStats object

        Args:
            player_id: Player identifier (format: angt_firstname_lastname)
            season: Season (None = current season)

        Returns:
            PlayerSeasonStats or None
        """
        try:
            # Use specified season or default to current
            season_to_use = season or self.current_season

            # Fetch stats page
            stats_url = f"{self.stats_url}/{season_to_use}"
            html = await self.http_client.get_text(stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find stats table
            table = find_stat_table(soup, table_class_hint="stats")
            if not table:
                self.logger.warning("No stats table found")
                return None

            # Extract rows
            rows = extract_table_data(table)

            # Extract player name from player_id
            # Format: "angt_john_doe" -> "John Doe"
            player_name = player_id.replace("angt_", "").replace("_", " ").title()

            # Find matching player row
            for row in rows:
                row_player = row.get("Player") or row.get("NAME") or ""
                if player_name.lower() in row_player.lower():
                    # Use helper to parse stats
                    stats_data = parse_season_stats_from_row(
                        row, player_id, season_to_use, "ANGT"
                    )

                    # Add ANGT-specific stat: PIR (Performance Index Rating)
                    pir = parse_float(row.get("PIR"))
                    if pir is not None and "advanced_stats" not in stats_data:
                        stats_data["advanced_stats"] = {}
                    if pir is not None:
                        # PIR can be stored in notes or as custom field
                        # For now, add to notes
                        pir_note = f"PIR: {pir}"
                        if stats_data.get("notes"):
                            stats_data["notes"] = f"{stats_data['notes']} | {pir_note}"
                        else:
                            stats_data["notes"] = pir_note

                    # Validate and return
                    return self.validate_and_log_data(
                        PlayerSeasonStats,
                        stats_data,
                        f"season stats for {player_name}",
                    )

            self.logger.warning(f"Player not found in stats", player_id=player_id)
            return None

        except Exception as e:
            self.logger.error(
                "Failed to get ANGT player season stats", error=str(e)
            )
            return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game statistics from ANGT.

        IMPLEMENTATION STEPS:
        1. Visit ANGT games page and click on a completed game
        2. Look for box score section (EuroLeague has comprehensive box scores)
        3. Note the URL pattern (e.g., /next-generation/game/{game-code}/boxscore)
        4. Inspect the box score table structure
        5. Note column headers: MIN, PTS, 2FG, 3FG, FT, REB, AST, STL, BLK, TO, PIR
        6. Implement parsing similar to FIBA Youth adapter
        7. Include PIR calculation

        Args:
            player_id: Player identifier
            game_id: Game identifier (game code)

        Returns:
            PlayerGameStats or None
        """
        try:
            # TODO: Implement after inspecting ANGT box score pages
            # Typical URL patterns to try:
            # box_score_url = f"{self.base_url}/game/{game_id}/boxscore"
            # box_score_url = f"{self.base_url}/game/{game_id}/stats"
            # box_score_url = f"https://www.euroleaguebasketball.net/next-generation/game/{game_id}"

            # EuroLeague box scores are very detailed with:
            # - Made/attempted field goals
            # - Made/attempted 3-pointers
            # - Made/attempted free throws
            # - Offensive/defensive rebounds
            # - Assists, steals, blocks, turnovers
            # - PIR calculation

            self.logger.warning("ANGT game stats require box score URL pattern")
            return None

        except Exception as e:
            self.logger.error("Failed to get ANGT player game stats", error=str(e))
            return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get club/team information from ANGT.

        IMPLEMENTATION STEPS:
        1. Visit https://www.euroleaguebasketball.net/next-generation/teams
        2. Look for teams/clubs list (typically cards or table)
        3. Note available fields: club name, country, roster, record, etc.
        4. Top clubs: Real Madrid, Barcelona, Maccabi, Olympiacos, Zalgiris, etc.
        5. Inspect HTML structure
        6. Implement parsing similar to OTE adapter
        7. Handle club codes (e.g., "MAD" for Madrid, "BAR" for Barcelona)

        Args:
            team_id: Team identifier (format: angt_club_name or club_code)

        Returns:
            Team object or None
        """
        try:
            # TODO: Implement after inspecting ANGT teams page
            # Pattern similar to other adapters:
            # 1. Fetch teams page
            # 2. Find table or team cards
            # 3. Parse team info
            # 4. Return Team object

            # Example ANGT clubs:
            # - Real Madrid
            # - FC Barcelona
            # - Maccabi Tel Aviv
            # - Olympiacos Piraeus
            # - Zalgiris Kaunas
            # - CSKA Moscow (may vary by year)

            self.logger.warning("ANGT team lookup requires teams page structure")
            return None

        except Exception as e:
            self.logger.error(f"Failed to get ANGT team {team_id}", error=str(e))
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
        Get games from ANGT tournament.

        IMPLEMENTATION STEPS:
        1. Visit https://www.euroleaguebasketball.net/next-generation/games
        2. Find tournament schedule/calendar page
        3. Look for games table or schedule cards
        4. Note fields: date, time, teams, scores, status, phase (Group/Knockout)
        5. Inspect HTML structure
        6. Implement parsing similar to FIBA Youth adapter
        7. Handle tournament phases (Group A, Group B, Semifinals, Final)

        Args:
            team_id: Filter by team/club
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            List of Game objects
        """
        try:
            # TODO: Implement after inspecting ANGT games page
            # Tournament structure:
            # - Group stage (typically 2 groups)
            # - Semifinals
            # - Third place game
            # - Final
            # All games typically occur during a single weekend event

            self.logger.warning("ANGT schedule parsing requires games page structure")
            return []

        except Exception as e:
            self.logger.error("Failed to get ANGT games", error=str(e))
            return []

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard from ANGT.

        IMPLEMENTATION STEPS:
        1. ANGT publishes comprehensive stat leaders via EuroLeague system
        2. To get leaderboard, fetch the stats table and sort by requested stat
        3. The stats table from search_players() can be reused here
        4. Extract stat values and sort
        5. Include PIR (Performance Index Rating) as a stat option

        Args:
            stat: Stat category (points, rebounds, assists, pir, etc.)
            season: Season filter
            limit: Maximum results

        Returns:
            List of leaderboard entries
        """
        try:
            # Use specified season or default to current
            season_to_use = season or self.current_season

            # Fetch stats page
            stats_url = f"{self.stats_url}/{season_to_use}"
            html = await self.http_client.get_text(stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find stats table
            table = find_stat_table(soup, table_class_hint="stats")
            if not table:
                return []

            # Extract rows
            rows = extract_table_data(table)

            # Build leaderboard entries
            leaderboard = []

            # Map stat name to column name
            # UPDATE these after inspecting actual table headers
            stat_column_map = {
                "points": "PTS",
                "rebounds": "REB",
                "assists": "AST",
                "steals": "STL",
                "blocks": "BLK",
                "pir": "PIR",  # Performance Index Rating
                "field_goal_pct": "FG%",
                "three_point_pct": "3P%",
                "free_throw_pct": "FT%",
                "minutes": "MIN",
            }

            stat_column = stat_column_map.get(stat.lower(), stat.upper())

            for row in rows:
                player_name = row.get("Player") or row.get("NAME")
                team_name = row.get("Club") or row.get("CLUB") or row.get("Team")

                # Try to find stat value
                stat_value = parse_float(row.get(stat_column) or row.get(stat.upper()))

                if player_name and stat_value is not None:
                    entry = build_leaderboard_entry(
                        rank=0,  # Will be set after sorting
                        player_name=player_name,
                        stat_value=stat_value,
                        stat_name=stat,
                        season=season_to_use,
                        source_prefix="angt",
                        team_name=team_name,
                    )
                    leaderboard.append(entry)

            # Sort by stat value (descending)
            leaderboard.sort(key=lambda x: x["stat_value"], reverse=True)

            # Set ranks
            for i, entry in enumerate(leaderboard[:limit], 1):
                entry["rank"] = i

            self.logger.info(
                f"ANGT {stat} leaderboard returned {len(leaderboard[:limit])} entries"
            )
            return leaderboard[:limit]

        except Exception as e:
            self.logger.error(f"Failed to get ANGT {stat} leaderboard", error=str(e))
            return []


# ==============================================================================
# IMPLEMENTATION CHECKLIST
# ==============================================================================
# Before marking this adapter as complete, verify:
#
# [ ] 1. All URL endpoints are actual ANGT URLs (not placeholders)
# [ ] 2. Understand EuroLeague data system and URL patterns
# [ ] 3. Table finding logic tested with real HTML
# [ ] 4. Column name mappings verified against actual table headers
# [ ] 5. PIR (Performance Index Rating) extraction working correctly
# [ ] 6. Club names properly extracted (may use "Club" instead of "Team")
# [ ] 7. At least 3 test cases passing (search, stats, leaderboard)
# [ ] 8. Rate limiting tested (no 429 errors)
# [ ] 9. Data validation passing (no negative stats, valid ranges)
# [ ] 10. Error handling tested (404s, timeouts, malformed HTML)
# [ ] 11. Tournament phase handling working (Group stage vs Finals)
# [ ] 12. Logging statements provide useful debugging info
# [ ] 13. Integration tested through aggregation service
# [ ] 14. Documentation updated in PROJECT_LOG.md
#
# ==============================================================================
# TESTING COMMANDS
# ==============================================================================
# Run these commands to test the adapter:
#
# # Test player search
# pytest tests/test_datasources/test_angt.py::TestANGTDataSource::test_search_players -v -s
#
# # Test season stats
# pytest tests/test_datasources/test_angt.py::TestANGTDataSource::test_get_player_season_stats -v -s
#
# # Test leaderboard
# pytest tests/test_datasources/test_angt.py::TestANGTDataSource::test_get_leaderboard -v -s
#
# # Test PIR extraction
# pytest tests/test_datasources/test_angt.py::TestANGTDataSource::test_pir_extraction -v -s
#
# # Test rate limiting
# pytest tests/test_datasources/test_angt.py::TestANGTDataSource::test_rate_limiting -v -s
#
# # Run all ANGT tests
# pytest tests/test_datasources/test_angt.py -v
#
# ==============================================================================
