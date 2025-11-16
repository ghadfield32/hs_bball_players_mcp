"""
PSAL (NYC Public Schools Athletic League) DataSource Adapter

Scrapes player and team statistics from PSAL (New York City).
Uses browser automation to handle JavaScript-rendered stats.

Updated: 2025-11-16 - Phase HS-5: Added browser automation for JavaScript stats
"""

from datetime import datetime
from typing import Optional

from ...models import (
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    Game,
    GameStatus,
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
    parse_html,
    parse_int,
    parse_record,
)
from ...utils.browser_client import BrowserClient
from ..base import BaseDataSource


class PSALDataSource(BaseDataSource):
    """
    PSAL (NYC Public Schools Athletic League) data source adapter.

    Provides access to NYC high school basketball statistics.
    Uses browser automation to handle JavaScript-based stats loading.

    **IMPORTANT**: Uses browser automation (Playwright) to render JavaScript stats.
    PSAL website uses client-side JavaScript to fetch and display stats from API.
    All requests are made via headless browser to ensure proper rendering.

    Public stats at https://www.psal.org
    Sport code 001 = Basketball
    """

    source_type = DataSourceType.PSAL
    source_name = "NYC PSAL"
    base_url = "https://www.psal.org"
    region = DataSourceRegion.US

    def __init__(self):
        """Initialize PSAL datasource with browser automation."""
        super().__init__()

        # PSAL-specific endpoints
        # Sport code 001 = Basketball
        self.basketball_url = f"{self.base_url}/sports/sport.aspx?spCode=001"
        self.standings_url = f"{self.base_url}/sports/standings.aspx?spCode=001"
        # CRITICAL: Hash fragment #001/Basketball required for JavaScript to load stats
        self.leaders_url = f"{self.base_url}/sports/top-player.aspx?spCode=001#001/Basketball"
        self.teams_url = f"{self.base_url}/sports/team.aspx?spCode=001"

        # Initialize browser client for JavaScript rendering
        # PSAL uses JavaScript to load stats from API, requires browser automation
        self.browser_client = BrowserClient(
            settings=self.settings,
            browser_type=self.settings.browser_type if hasattr(self.settings, 'browser_type') else "chromium",
            headless=self.settings.browser_headless if hasattr(self.settings, 'browser_headless') else True,
            timeout=self.settings.browser_timeout if hasattr(self.settings, 'browser_timeout') else 60000,  # 60s for slow JS
            cache_enabled=self.settings.browser_cache_enabled if hasattr(self.settings, 'browser_cache_enabled') else True,
            cache_ttl=self.settings.browser_cache_ttl if hasattr(self.settings, 'browser_cache_ttl') else 3600,
        )

        self.logger.info(
            "PSAL initialized with browser automation",
            base_url=self.base_url,
            leaders_url=self.leaders_url
        )

    async def close(self):
        """Close connections and browser instances."""
        await super().close()
        # Note: Browser is singleton, managed globally

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        PSAL doesn't have individual player profile pages.
        Search through leaderboards instead.

        Args:
            player_id: Player identifier

        Returns:
            Player object or None
        """
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
        Search for players in PSAL leaderboards.

        Uses browser automation to render JavaScript-based stats.
        PSAL loads stats dynamically from API via JavaScript AFTER dropdown selection.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season year (e.g. "2024-25"), defaults to current
            limit: Maximum results

        Returns:
            List of Player objects
        """
        try:
            self.logger.info("Fetching PSAL player leaderboards (browser automation with dropdown)")

            # PSAL requires special handling: must interact with dropdowns to trigger stats loading
            from playwright.async_api import async_playwright
            import asyncio

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.browser_client.headless
                )
                page = await browser.new_page()

                # Navigate to PSAL leaders page (with hash fragment!)
                self.logger.debug(f"Loading PSAL page: {self.leaders_url}")
                await page.goto(self.leaders_url, wait_until="networkidle", timeout=60000)

                # Wait for dropdowns to appear (JavaScript creates them)
                self.logger.debug("Waiting for dropdowns to load...")
                await page.wait_for_selector("#drpSeason", timeout=10000)
                await page.wait_for_selector("#drpCategor", timeout=10000)

                # Select current season (2024-2025 = value "2025")
                # PSAL defaults to FUTURE season "2026" which has no data!
                season_value = "2025"  # 2024-2025 season
                if season:
                    # Parse season like "2024-25" -> "2025"
                    if "-" in season:
                        season_value = season.split("-")[0].strip()
                        # Convert "2024" -> "2025" (PSAL uses end year)
                        season_value = str(int(season_value) + 1)

                self.logger.debug(f"Selecting season: {season_value}")
                await page.select_option("#drpSeason", value=season_value)

                # Select Points category (value=1) for now
                # TODO: Support other categories (assists, rebounds, etc.)
                await page.select_option("#drpCategor", value="1")

                # Wait for stats to load via AJAX
                self.logger.debug("Waiting for stats to load...")
                await asyncio.sleep(10)  # Give API time to return data

                # Get HTML after dropdown interaction
                html = await page.content()
                await browser.close()

                self.logger.debug("PSAL stats loaded successfully")

            # Parse rendered HTML
            soup = parse_html(html)

            # PSAL uses a specific div for stat leaders: id="top_player_list"
            # Table structure is unusual: data rows are in <thead> not <tbody>
            stats_div = soup.find("div", id="top_player_list")

            if not stats_div:
                self.logger.warning("No #top_player_list div found on PSAL leaders page")
                return []

            stat_table = stats_div.find("table")
            if not stat_table:
                self.logger.warning("No table found in #top_player_list div")
                return []

            # PSAL puts data rows in <thead> (unusual but confirmed)
            thead = stat_table.find("thead")
            if not thead:
                self.logger.warning("No <thead> found in stats table")
                return []

            all_rows = thead.find_all("tr")
            self.logger.info(f"Found {len(all_rows)} rows in PSAL stats table")

            if not all_rows:
                return []

            players = []
            seen_players = set()

            data_source = self.create_data_source_metadata(
                url=self.leaders_url, quality_flag=DataQualityFlag.PARTIAL
            )

            # Skip header rows (first 2 rows: error message row + column headers)
            data_rows = all_rows[2:] if len(all_rows) > 2 else []

            self.logger.debug(f"Processing {len(data_rows)} data rows (skipped 2 header rows)")

            for row in data_rows:
                # Check if this is a "No records found" row
                cells = row.find_all("td")
                if len(cells) == 1 and "no records" in cells[0].get_text().lower():
                    self.logger.info("PSAL shows 'No records found' - no players available")
                    return []

                # Parse row into dict format expected by _parse_player_from_leaders_row
                # PSAL format: RANK | PLAYER | GRADE | SCHOOL | POINTS/STAT | NO. OF GAMES
                if len(cells) < 5:
                    continue  # Skip malformed rows

                # PSAL has lots of whitespace padding in names - normalize it
                import re
                player_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                # Collapse multiple spaces to single space
                player_text = re.sub(r'\s+', ' ', player_text).strip()

                school_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                school_text = re.sub(r'\s+', ' ', school_text).strip()

                row_dict = {
                    "RANK": cells[0].get_text(strip=True) if len(cells) > 0 else "",
                    "PLAYER": player_text,
                    "GRADE": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                    "SCHOOL": school_text,
                    "POINTS": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                    "NO. OF GAMES": cells[5].get_text(strip=True) if len(cells) > 5 else "",
                }

                player = self._parse_player_from_leaders_row(row_dict, data_source)
                if not player:
                    continue

                # Avoid duplicates
                if player.player_id in seen_players:
                    continue

                # Apply filters
                if name and name.lower() not in player.full_name.lower():
                    continue
                if team and (
                    not player.school_name or team.lower() not in player.school_name.lower()
                ):
                    continue

                players.append(player)
                seen_players.add(player.player_id)

                if len(players) >= limit:
                    break

            self.logger.info(f"Found {len(players)} PSAL players", filters={"name": name, "team": team})
            return players

        except Exception as e:
            self.logger.error("Failed to search PSAL players", error=str(e))
            return []

    def _parse_player_from_leaders_row(self, row: dict, data_source) -> Optional[Player]:
        """Parse player from leaderboard row."""
        try:
            # PSAL column names vary by stat table
            # Common columns: RANK, PLAYER, GRADE, SCHOOL, [STAT], NO. OF GAMES
            player_name = (
                row.get("PLAYER") or
                row.get("Player") or
                row.get("NAME") or
                row.get("Name") or
                ""
            )

            if not player_name or len(player_name.strip()) == 0:
                return None

            # Clean player name
            player_name = clean_player_name(player_name)
            if not player_name:
                return None

            # Split into first and last name
            # Most names are "FIRSTNAME LASTNAME" but some have middle names
            name_parts = player_name.split()
            if len(name_parts) == 0:
                return None
            elif len(name_parts) == 1:
                # Single name - use as last name
                first_name = ""
                last_name = name_parts[0]
            elif len(name_parts) == 2:
                # Standard "FIRST LAST"
                first_name = name_parts[0]
                last_name = name_parts[1]
            else:
                # Multiple names - first word is first name, rest is last name
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])

            # Generate player ID
            player_id = f"psal_{player_name.lower().replace(' ', '_')}"

            # Extract school
            school_name = (
                row.get("SCHOOL") or
                row.get("School") or
                row.get("TEAM") or
                row.get("Team") or
                None
            )

            # Extract grade/year
            grade_str = row.get("GRADE") or row.get("Grade") or row.get("YR") or row.get("Yr")
            grad_year = None
            if grade_str:
                # PSAL uses text grades: "Freshman", "Sophomore", "Junior", "Senior"
                grade_str_lower = grade_str.lower()
                grade = None

                if "freshman" in grade_str_lower or grade_str == "9":
                    grade = 9
                elif "sophomore" in grade_str_lower or grade_str == "10":
                    grade = 10
                elif "junior" in grade_str_lower or grade_str == "11":
                    grade = 11
                elif "senior" in grade_str_lower or grade_str == "12":
                    grade = 12
                else:
                    # Try to parse as number
                    grade = parse_int(grade_str)

                if grade and 9 <= grade <= 12:
                    # Estimate grad year (12th grade in 2024-25 = class of 2025)
                    current_year = datetime.now().year
                    # If it's before June, we're still in the previous school year
                    import datetime as dt
                    if dt.datetime.now().month < 6:
                        current_year -= 1
                    grad_year = current_year + (12 - grade) + 1

            # Create player object
            player_data = {
                "player_id": player_id,
                "source_type": self.source_type,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "school_name": school_name,
                "school_city": "New York",  # PSAL is NYC only
                "school_state": "NY",
                "school_country": "USA",
                "level": PlayerLevel.HIGH_SCHOOL,
                "grad_year": grad_year,
                "data_source": data_source,
            }

            return self.validate_and_log_data(
                Player, player_data, f"PSAL player {player_name}"
            )

        except Exception as e:
            self.logger.error("Failed to parse player from leaderboard row", error=str(e))
            return None

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics.

        PSAL shows current season stats in leaderboards.
        Parse stats from the rendered stats tables.

        Args:
            player_id: Player identifier
            season: Season (uses current if None)

        Returns:
            PlayerSeasonStats or None
        """
        try:
            # Fetch leaders page with browser automation
            html = await self.browser_client.get_rendered_html(
                url=self.leaders_url,
                wait_for="table",
                wait_for_network_idle=True,
                cache_override_ttl=3600,
            )

            soup = parse_html(html)
            tables = soup.find_all("table")

            # Extract player name from ID
            player_name = player_id.replace("psal_", "").replace("_", " ").title()

            # Search for player in tables
            for table in tables:
                # Skip form tables
                table_classes = table.get('class', [])
                if 'feedTable' in table_classes or 'fieldWraper' in table_classes:
                    continue

                rows = extract_table_data(table)

                for row in rows:
                    row_player_name = clean_player_name(
                        row.get("PLAYER") or row.get("Player") or row.get("NAME") or row.get("Name") or ""
                    )

                    if row_player_name and player_name.lower() in row_player_name.lower():
                        # Found player - parse stats
                        return self._parse_season_stats_from_dict(row, player_id, season or "2024-25")

            self.logger.warning(f"Player not found in PSAL stats", player_id=player_id)
            return None

        except Exception as e:
            self.logger.error("Failed to get PSAL player season stats", player_id=player_id, error=str(e))
            return None

    def _parse_season_stats_from_dict(
        self, row: dict, player_id: str, season: str
    ) -> Optional[PlayerSeasonStats]:
        """Parse season stats from table row dictionary."""
        try:
            player_name = clean_player_name(
                row.get("PLAYER") or row.get("Player") or row.get("NAME") or row.get("Name") or ""
            )

            # Parse stats based on available columns
            # PSAL tables have different columns per stat category
            points = parse_int(row.get("POINTS") or row.get("Points") or row.get("PTS"))
            assists = parse_int(row.get("ASSISTS") or row.get("Assists") or row.get("AST"))
            rebounds = parse_int(row.get("REBOUNDS") or row.get("Rebounds") or row.get("REB"))
            games = parse_int(row.get("NO. OF GAMES") or row.get("GP") or row.get("Games"))

            # Per-game stats
            ppg = parse_float(row.get("POINTS/GAME") or row.get("PPG"))
            apg = parse_float(row.get("ASSISTS/GAME") or row.get("APG"))
            rpg = parse_float(row.get("REBOUNDS/GAME") or row.get("RPG"))

            # Calculate per-game if not provided
            if not ppg and points and games and games > 0:
                ppg = round(points / games, 1)
            if not apg and assists and games and games > 0:
                apg = round(assists / games, 1)
            if not rpg and rebounds and games and games > 0:
                rpg = round(rebounds / games, 1)

            stats_data = {
                "stat_id": f"{player_id}_{season}_psal",
                "player_id": player_id,
                "player_name": player_name,
                "season": season,
                "league": "NYC PSAL",
                "games_played": games,
                "points": points,
                "points_per_game": ppg,
                "assists": assists,
                "assists_per_game": apg,
                "total_rebounds": rebounds,
                "rebounds_per_game": rpg,
            }

            return self.validate_and_log_data(
                PlayerSeasonStats, stats_data, f"PSAL stats for {player_name}"
            )

        except Exception as e:
            self.logger.error("Failed to parse PSAL season stats", error=str(e))
            return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game statistics.

        PSAL doesn't provide individual game box scores on public stats pages.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            None (not available)
        """
        self.logger.warning("PSAL does not provide individual game box scores")
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team information from PSAL standings.

        Args:
            team_id: Team identifier

        Returns:
            Team object or None
        """
        try:
            # Fetch standings page with browser automation
            html = await self.browser_client.get_rendered_html(
                url=self.standings_url,
                wait_for="table",
                wait_for_network_idle=True,
                cache_override_ttl=7200,  # Cache for 2 hours
            )

            soup = parse_html(html)
            tables = soup.find_all("table")

            # Extract team name from ID
            team_name = team_id.replace("psal_", "").replace("_", " ").title()

            for table in tables:
                # Skip form tables
                table_classes = table.get('class', [])
                if 'feedTable' in table_classes:
                    continue

                rows = extract_table_data(table)

                for row in rows:
                    row_team = row.get("SCHOOL") or row.get("School") or row.get("TEAM") or row.get("Team") or ""

                    if row_team and team_name.lower() in row_team.lower():
                        return self._parse_team_from_standings_row(row, team_id)

            self.logger.warning(f"Team not found in PSAL standings", team_id=team_id)
            return None

        except Exception as e:
            self.logger.error("Failed to get PSAL team", team_id=team_id, error=str(e))
            return None

    def _parse_team_from_standings_row(self, row: dict, team_id: str) -> Optional[Team]:
        """Parse team from standings row."""
        try:
            team_name = row.get("SCHOOL") or row.get("School") or row.get("TEAM") or row.get("Team") or ""

            # Parse record
            wins = parse_int(row.get("W") or row.get("Wins"))
            losses = parse_int(row.get("L") or row.get("Losses"))

            # Parse conference/division
            conference = row.get("DIVISION") or row.get("Division") or row.get("CONFERENCE") or row.get("Conference")

            data_source = self.create_data_source_metadata(
                url=self.standings_url, quality_flag=DataQualityFlag.COMPLETE
            )

            team_data = {
                "team_id": team_id,
                "team_name": team_name,
                "school_name": team_name,
                "city": "New York",
                "state": "NY",
                "country": "USA",
                "level": TeamLevel.HIGH_SCHOOL_VARSITY,
                "league": "NYC PSAL",
                "conference": conference,
                "season": "2024-25",
                "wins": wins,
                "losses": losses,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Team, team_data, f"PSAL team {team_name}")

        except Exception as e:
            self.logger.error("Failed to parse team from standings", error=str(e))
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
        Get games from PSAL schedule.

        PSAL schedule page not implemented yet - requires additional work.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            Empty list (not implemented)
        """
        self.logger.warning("PSAL get_games() not implemented yet")
        return []

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get PSAL statistical leaderboard.

        Args:
            stat: Stat category (e.g., 'points', 'assists', 'rebounds')
            season: Season (uses current)
            limit: Maximum results

        Returns:
            List of leaderboard entries
        """
        try:
            # Fetch leaders page
            html = await self.browser_client.get_rendered_html(
                url=self.leaders_url,
                wait_for="table",
                wait_for_network_idle=True,
                cache_override_ttl=3600,
            )

            soup = parse_html(html)
            tables = soup.find_all("table")

            # Map stat to column name
            stat_column_map = {
                "points": ["POINTS", "Points", "PTS"],
                "assists": ["ASSISTS", "Assists", "AST"],
                "rebounds": ["REBOUNDS", "Rebounds", "REB"],
                "points_per_game": ["POINTS/GAME", "PPG"],
                "assists_per_game": ["ASSISTS/GAME", "APG"],
                "rebounds_per_game": ["REBOUNDS/GAME", "RPG"],
            }

            stat_columns = stat_column_map.get(stat.lower(), [stat.upper()])

            # Find table with matching stat column
            for table in tables:
                # Skip form tables
                table_classes = table.get('class', [])
                if 'feedTable' in table_classes or 'fieldWraper' in table_classes:
                    continue

                rows = extract_table_data(table)
                if not rows:
                    continue

                # Check if this table has our stat
                has_stat = any(
                    any(col in row for col in stat_columns)
                    for row in rows
                )

                if not has_stat:
                    continue

                # Build leaderboard from this table
                leaderboard = []

                for i, row in enumerate(rows[:limit], 1):
                    player_name = clean_player_name(
                        row.get("PLAYER") or row.get("Player") or row.get("NAME") or row.get("Name") or ""
                    )
                    school = row.get("SCHOOL") or row.get("School") or row.get("TEAM") or row.get("Team")

                    # Find stat value
                    stat_value = None
                    for col in stat_columns:
                        stat_value = parse_float(row.get(col))
                        if stat_value is not None:
                            break

                    if not player_name or stat_value is None:
                        continue

                    entry = {
                        "rank": i,
                        "player_name": player_name,
                        "player_id": f"psal_{player_name.lower().replace(' ', '_')}",
                        "team_name": school,
                        "stat_name": stat,
                        "stat_value": stat_value,
                        "season": season or "2024-25",
                        "league": "NYC PSAL",
                    }

                    leaderboard.append(entry)

                if leaderboard:
                    self.logger.info(f"Built PSAL leaderboard", stat=stat, entries=len(leaderboard))
                    return leaderboard

            self.logger.warning(f"No PSAL leaderboard found for stat", stat=stat)
            return []

        except Exception as e:
            self.logger.error("Failed to get PSAL leaderboard", stat=stat, error=str(e))
            return []
