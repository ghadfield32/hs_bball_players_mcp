"""
Bound (formerly Varsity Bound) DataSource Adapter

Scrapes player and team statistics from Bound.
HIGH-PRIORITY multi-state adapter covering IA (flagship), SD, IL, MN.
Excellent player pages and comprehensive stats coverage.
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
    parse_html,
    parse_int,
    parse_record,
)
from ...utils.scraping_helpers import (
    build_leaderboard_entry,
    extract_links_from_table,
    find_stat_table,
    parse_grad_year,
    parse_player_from_row,
    parse_season_stats_from_row,
    standardize_stat_columns,
)
from ..base import BaseDataSource


class BoundDataSource(BaseDataSource):
    """
    Bound (formerly Varsity Bound) data source adapter.

    Provides access to high school basketball statistics across multiple Midwest states.
    Known for excellent player profile pages and detailed statistics.

    Supported States:
        - IA: Iowa (flagship state, best coverage)
        - SD: South Dakota
        - IL: Illinois
        - MN: Minnesota

    URL Pattern: https://www.{state}.bound.com/basketball
    Note: Each state has its own subdomain (different from SBLive pattern)
    """

    source_type = DataSourceType.BOUND
    source_name = "Bound"
    region = DataSourceRegion.US

    # Multi-state support (Midwest focus)
    SUPPORTED_STATES = ["IA", "SD", "IL", "MN"]

    # State full names for metadata
    STATE_NAMES = {
        "IA": "Iowa",
        "SD": "South Dakota",
        "IL": "Illinois",
        "MN": "Minnesota",
    }

    def __init__(self):
        """Initialize Bound datasource with multi-state support."""
        super().__init__()

        # Build state-specific base URLs
        # Note: Bound uses www.{state}.bound.com (subdomain pattern)
        self.state_base_urls = {
            state: f"https://www.{state.lower()}.bound.com"
            for state in self.SUPPORTED_STATES
        }

        # Build state-specific basketball URLs
        self.state_urls = {
            state: f"{self.state_base_urls[state]}/basketball"
            for state in self.SUPPORTED_STATES
        }

        self.logger.info(
            f"Bound initialized with {len(self.SUPPORTED_STATES)} states",
            states=self.SUPPORTED_STATES,
            flagship="IA",
        )

    def _validate_state(self, state: Optional[str]) -> str:
        """
        Validate and normalize state parameter.

        Args:
            state: State code (IA, SD, IL, MN)

        Returns:
            Uppercase state code

        Raises:
            ValueError: If state is invalid or not supported
        """
        if not state:
            raise ValueError(
                f"State parameter required. Supported states: {', '.join(self.SUPPORTED_STATES)}"
            )

        state = state.upper().strip()

        if state not in self.SUPPORTED_STATES:
            raise ValueError(
                f"State '{state}' not supported. Supported states: {', '.join(self.SUPPORTED_STATES)}"
            )

        return state

    def _get_state_base_url(self, state: str) -> str:
        """
        Get state-specific base URL.

        Args:
            state: State code (must be validated)

        Returns:
            State base URL

        Example:
            _get_state_base_url("IA") -> "https://www.ia.bound.com"
        """
        return self.state_base_urls[state]

    def _get_state_url(self, state: str, endpoint: str = "") -> str:
        """
        Build state-specific URL for basketball section.

        Args:
            state: State code (must be validated)
            endpoint: Additional endpoint path

        Returns:
            Full URL for state basketball endpoint

        Example:
            _get_state_url("IA", "stats") -> "https://www.ia.bound.com/basketball/stats"
        """
        base = self.state_urls[state]
        if endpoint:
            return f"{base}/{endpoint.lstrip('/')}"
        return base

    def _build_player_id(self, state: str, player_name: str) -> str:
        """
        Build Bound player ID with state prefix.

        Args:
            state: State code
            player_name: Player name

        Returns:
            Player ID in format: bound_{state}_{name}

        Example:
            _build_player_id("IA", "John Doe") -> "bound_ia_john_doe"
        """
        clean_name = clean_player_name(player_name).lower().replace(" ", "_")
        return f"bound_{state.lower()}_{clean_name}"

    def _extract_state_from_player_id(self, player_id: str) -> Optional[str]:
        """
        Extract state code from player ID.

        Args:
            player_id: Player ID in format bound_{state}_{name}

        Returns:
            State code or None
        """
        parts = player_id.split("_")
        if len(parts) >= 2 and parts[0] == "bound":
            state = parts[1].upper()
            return state if state in self.SUPPORTED_STATES else None
        return None

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        Bound has excellent player profile pages. This method attempts to fetch
        the player profile directly if available, or falls back to stats search.

        Args:
            player_id: Player identifier (format: bound_{state}_{name})

        Returns:
            Player object or None

        Example:
            player = await bound.get_player("bound_ia_john_doe")
        """
        try:
            # Extract state from player_id
            state = self._extract_state_from_player_id(player_id)
            if not state:
                self.logger.warning(
                    f"Could not extract state from player_id", player_id=player_id
                )
                return None

            # Extract player name from ID
            player_name = player_id.replace(f"bound_{state.lower()}_", "").replace("_", " ").title()

            # Try to fetch player profile page (Bound has good player pages)
            # Note: Actual URL pattern may vary, trying common patterns
            profile_url = self._get_state_url(state, f"player/{player_name.lower().replace(' ', '-')}")

            try:
                html = await self.http_client.get_text(profile_url, cache_ttl=3600)
                soup = parse_html(html)

                # Try to parse player profile if page exists
                player = self._parse_player_profile(soup, player_id, state, profile_url)
                if player:
                    return player
            except Exception:
                # Profile page not found or parse failed, fall back to search
                pass

            # Fallback: Search for player in state stats
            players = await self.search_players(state=state, name=player_name, limit=1)
            return players[0] if players else None

        except Exception as e:
            self.logger.error("Failed to get player", player_id=player_id, error=str(e))
            return None

    def _parse_player_profile(
        self, soup: BeautifulSoup, player_id: str, state: str, source_url: str
    ) -> Optional[Player]:
        """
        Parse player from profile page.

        Bound has excellent player pages with detailed information.

        Args:
            soup: Parsed HTML
            player_id: Player ID
            state: State code
            source_url: Source URL

        Returns:
            Player object or None
        """
        try:
            # Extract player name from heading
            name_heading = soup.find(["h1", "h2"], class_=lambda x: x and "player" in str(x).lower())
            if not name_heading:
                name_heading = soup.find(["h1", "h2"])

            if not name_heading:
                return None

            full_name = clean_player_name(get_text_or_none(name_heading) or "")
            if not full_name:
                return None

            name_parts = full_name.split()
            first_name = name_parts[0] if len(name_parts) > 0 else full_name
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            # Extract player details (look for info sections)
            position = None
            height_inches = None
            grad_year = None
            jersey_number = None
            school_name = None

            # Try to find player info section/table
            info_section = soup.find("div", class_=lambda x: x and "player-info" in str(x).lower())
            if info_section:
                # Look for position
                pos_elem = info_section.find(text=lambda x: x and "Position" in str(x))
                if pos_elem:
                    pos_text = pos_elem.find_next()
                    if pos_text:
                        try:
                            position = Position(get_text_or_none(pos_text).upper().strip())
                        except ValueError:
                            pass

                # Look for height
                ht_elem = info_section.find(text=lambda x: x and "Height" in str(x))
                if ht_elem:
                    ht_text = ht_elem.find_next()
                    if ht_text:
                        from ...utils.parser import parse_height_to_inches
                        height_inches = parse_height_to_inches(get_text_or_none(ht_text))

                # Look for class/grad year
                class_elem = info_section.find(text=lambda x: x and ("Class" in str(x) or "Year" in str(x)))
                if class_elem:
                    class_text = class_elem.find_next()
                    if class_text:
                        grad_year = parse_grad_year(get_text_or_none(class_text))

                # Look for school
                school_elem = info_section.find(text=lambda x: x and "School" in str(x))
                if school_elem:
                    school_text = school_elem.find_next()
                    if school_text:
                        school_name = get_text_or_none(school_text)

            data_source = self.create_data_source_metadata(
                url=source_url, quality_flag=DataQualityFlag.COMPLETE
            )

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name,
                "position": position,
                "height_inches": height_inches,
                "grad_year": grad_year,
                "jersey_number": jersey_number,
                "school_name": school_name,
                "school_state": state,
                "school_country": "USA",
                "level": PlayerLevel.HIGH_SCHOOL,
                "data_source": data_source,
            }

            return self.validate_and_log_data(
                Player, player_data, f"player profile {full_name} ({state})"
            )

        except Exception as e:
            self.logger.error("Failed to parse player profile", error=str(e))
            return None

    async def search_players(
        self,
        state: str,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in state stats tables.

        **IMPLEMENTATION STEPS:**
        1. Validate state parameter
        2. Fetch state stats page
        3. Find stats table using find_stat_table()
        4. Parse players using parse_player_from_row()
        5. Filter by name/team
        6. Enrich with state location data

        Args:
            state: State code (IA, SD, IL, MN) - REQUIRED
            name: Player name (partial match)
            team: Team/school name (partial match)
            season: Season filter (uses current if None)
            limit: Maximum results

        Returns:
            List of Player objects

        Example:
            # Iowa players (flagship state)
            players = await bound.search_players(state="IA", limit=10)
            # Illinois players named "Smith"
            players = await bound.search_players(state="IL", name="Smith", limit=20)
        """
        try:
            # STEP 1: Validate state
            state = self._validate_state(state)

            # STEP 2: Fetch state stats page
            stats_url = self._get_state_url(state, "stats")
            self.logger.info(f"Fetching stats for state", state=state, url=stats_url)

            html = await self.http_client.get_text(stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # STEP 3: Find stats table
            stats_table = find_stat_table(soup, table_class_hint="stats")
            if not stats_table:
                # Try alternative search
                stats_table = find_stat_table(soup, header_text="Season Leaders")

            if not stats_table:
                # Fallback to any table
                stats_table = soup.find("table")

            if not stats_table:
                self.logger.warning(f"No stats table found", state=state)
                return []

            # STEP 4: Extract table data
            rows = extract_table_data(stats_table)
            self.logger.debug(f"Found {len(rows)} rows in stats table", state=state)

            # STEP 5: Parse players
            players = []
            data_source = self.create_data_source_metadata(
                url=stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            for row in rows[:limit * 2]:  # Get extra rows for filtering
                player = self._parse_player_from_stats_row(row, state, data_source)
                if not player:
                    continue

                # STEP 6: Apply filters
                if name and name.lower() not in player.full_name.lower():
                    continue

                if team and (
                    not player.school_name or team.lower() not in player.school_name.lower()
                ):
                    continue

                players.append(player)

                if len(players) >= limit:
                    break

            self.logger.info(
                f"Found {len(players)} players",
                state=state,
                filters={"name": name, "team": team},
            )
            return players

        except ValueError as e:
            # State validation error
            self.logger.error("Invalid state", error=str(e))
            return []
        except Exception as e:
            self.logger.error("Failed to search players", state=state, error=str(e))
            return []

    def _parse_player_from_stats_row(
        self, row: dict, state: str, data_source
    ) -> Optional[Player]:
        """
        Parse player from stats table row with state enrichment.

        Args:
            row: Row dictionary from stats table
            state: State code
            data_source: DataSource metadata

        Returns:
            Player object or None
        """
        try:
            # Use helper to parse common fields
            player_data = parse_player_from_row(
                row,
                source_prefix=f"bound_{state.lower()}",
                default_level="HIGH_SCHOOL",
                school_state=state,
            )

            if not player_data:
                return None

            # Override player ID to include state
            player_name = player_data.get("full_name", "")
            player_data["player_id"] = self._build_player_id(state, player_name)

            # Enrich with state location data
            player_data["school_state"] = state
            player_data["school_country"] = "USA"
            player_data["level"] = PlayerLevel.HIGH_SCHOOL

            # Add data source
            player_data["data_source"] = data_source

            return self.validate_and_log_data(
                Player, player_data, f"player {player_name} ({state})"
            )

        except Exception as e:
            self.logger.error("Failed to parse player from row", state=state, error=str(e))
            return None

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None, state: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics from state stats page.

        **IMPLEMENTATION STEPS:**
        1. Extract state from player_id or use state parameter
        2. Fetch state stats page
        3. Find player row by name
        4. Parse stats using parse_season_stats_from_row()

        Args:
            player_id: Player identifier
            season: Season (uses current if None)
            state: State code (extracted from player_id if None)

        Returns:
            PlayerSeasonStats or None

        Example:
            stats = await bound.get_player_season_stats("bound_ia_john_doe", "2024-25")
        """
        try:
            # STEP 1: Determine state
            if not state:
                state = self._extract_state_from_player_id(player_id)
            if state:
                state = self._validate_state(state)
            else:
                self.logger.error("Could not determine state", player_id=player_id)
                return None

            # STEP 2: Fetch state stats page
            stats_url = self._get_state_url(state, "stats")
            html = await self.http_client.get_text(stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # STEP 3: Find stats table
            stats_table = find_stat_table(soup)
            if not stats_table:
                return None

            rows = extract_table_data(stats_table)

            # STEP 4: Find player row by name
            player_name = (
                player_id.replace(f"bound_{state.lower()}_", "").replace("_", " ").title()
            )

            for row in rows:
                row_player_name = clean_player_name(
                    row.get("Player") or row.get("NAME") or row.get("Name") or ""
                )
                if row_player_name and player_name.lower() in row_player_name.lower():
                    # STEP 5: Parse stats from row
                    return self._parse_season_stats_from_row(
                        row, player_id, season or "2024-25", state
                    )

            self.logger.warning(f"Player not found in stats", player_id=player_id, state=state)
            return None

        except Exception as e:
            self.logger.error(
                "Failed to get player season stats", player_id=player_id, error=str(e)
            )
            return None

    def _parse_season_stats_from_row(
        self, row: dict, player_id: str, season: str, state: str
    ) -> Optional[PlayerSeasonStats]:
        """
        Parse season stats from table row.

        Args:
            row: Row dictionary
            player_id: Player ID
            season: Season string
            state: State code

        Returns:
            PlayerSeasonStats or None
        """
        try:
            # Use helper to parse common stats
            stats_data = parse_season_stats_from_row(
                row, player_id, season, f"Bound {self.STATE_NAMES[state]}"
            )

            if not stats_data:
                return None

            # Add state context to league
            stats_data["league"] = f"Bound {self.STATE_NAMES[state]}"

            return self.validate_and_log_data(
                PlayerSeasonStats, stats_data, f"season stats for {player_id}"
            )

        except Exception as e:
            self.logger.error("Failed to parse season stats", error=str(e))
            return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str, state: Optional[str] = None
    ) -> Optional[PlayerGameStats]:
        """
        Get player game statistics from box score page.

        **IMPLEMENTATION STEPS:**
        1. Extract state from player_id or use parameter
        2. Fetch box score page
        3. Find player row in box score table
        4. Parse game stats

        Args:
            player_id: Player identifier
            game_id: Game identifier
            state: State code (extracted from player_id if None)

        Returns:
            PlayerGameStats or None

        Example:
            stats = await bound.get_player_game_stats("bound_ia_john_doe", "game_123")
        """
        try:
            # STEP 1: Determine state
            if not state:
                state = self._extract_state_from_player_id(player_id)
            if state:
                state = self._validate_state(state)
            else:
                self.logger.error("Could not determine state", player_id=player_id)
                return None

            # STEP 2: Build box score URL
            # Note: Actual box score URL format may vary
            box_score_url = self._get_state_url(state, f"boxscore/{game_id}")

            html = await self.http_client.get_text(box_score_url, cache_ttl=3600)
            soup = parse_html(html)

            # STEP 3: Find box score table
            box_score_table = find_stat_table(soup, header_text="Box Score")
            if not box_score_table:
                box_score_table = soup.find("table")

            if not box_score_table:
                self.logger.warning("No box score table found", game_id=game_id, state=state)
                return None

            rows = extract_table_data(box_score_table)

            # STEP 4: Find player row
            player_name = (
                player_id.replace(f"bound_{state.lower()}_", "").replace("_", " ").title()
            )

            for row in rows:
                row_player_name = clean_player_name(
                    row.get("Player") or row.get("NAME") or row.get("Name") or ""
                )
                if row_player_name and player_name.lower() in row_player_name.lower():
                    return self._parse_game_stats_from_row(row, player_id, game_id, state)

            self.logger.warning(
                "Player not found in box score", player_id=player_id, game_id=game_id
            )
            return None

        except Exception as e:
            self.logger.error(
                "Failed to get player game stats",
                player_id=player_id,
                game_id=game_id,
                error=str(e),
            )
            return None

    def _parse_game_stats_from_row(
        self, row: dict, player_id: str, game_id: str, state: str
    ) -> Optional[PlayerGameStats]:
        """Parse game stats from box score row."""
        try:
            player_name = clean_player_name(
                row.get("Player") or row.get("NAME") or row.get("Name") or ""
            )

            # Parse individual game stats
            points = parse_int(row.get("PTS") or row.get("Points"))
            rebounds = parse_int(row.get("REB") or row.get("Rebounds"))
            assists = parse_int(row.get("AST") or row.get("Assists"))
            steals = parse_int(row.get("STL") or row.get("Steals"))
            blocks = parse_int(row.get("BLK") or row.get("Blocks"))
            fgm = parse_int(row.get("FGM") or row.get("FG Made"))
            fga = parse_int(row.get("FGA") or row.get("FG Att"))
            tpm = parse_int(row.get("3PM") or row.get("3P Made"))
            tpa = parse_int(row.get("3PA") or row.get("3P Att"))
            ftm = parse_int(row.get("FTM") or row.get("FT Made"))
            fta = parse_int(row.get("FTA") or row.get("FT Att"))
            minutes = parse_int(row.get("MIN") or row.get("Minutes"))

            stats_data = {
                "player_id": player_id,
                "player_name": player_name,
                "game_id": game_id,
                "team_id": f"bound_{state.lower()}_team_unknown",
                "points": points,
                "total_rebounds": rebounds,
                "assists": assists,
                "steals": steals,
                "blocks": blocks,
                "field_goals_made": fgm,
                "field_goals_attempted": fga,
                "three_pointers_made": tpm,
                "three_pointers_attempted": tpa,
                "free_throws_made": ftm,
                "free_throws_attempted": fta,
                "minutes_played": minutes,
            }

            return self.validate_and_log_data(
                PlayerGameStats, stats_data, f"game stats for {player_name}"
            )

        except Exception as e:
            self.logger.error("Failed to parse game stats from row", error=str(e))
            return None

    async def get_team(self, team_id: str, state: Optional[str] = None) -> Optional[Team]:
        """
        Get team information from standings page.

        **IMPLEMENTATION STEPS:**
        1. Determine state from team_id or parameter
        2. Fetch state standings page
        3. Find team row
        4. Parse team data

        Args:
            team_id: Team identifier
            state: State code (can be extracted from team_id)

        Returns:
            Team object or None

        Example:
            team = await bound.get_team("bound_ia_team_roosevelt", state="IA")
        """
        try:
            # STEP 1: Determine state
            if not state:
                # Try to extract from team_id (format: bound_{state}_team_{name})
                parts = team_id.split("_")
                if len(parts) >= 3 and parts[0] == "bound":
                    state = parts[1].upper()

            if not state:
                self.logger.error("Could not determine state", team_id=team_id)
                return None

            state = self._validate_state(state)

            # STEP 2: Fetch standings page
            standings_url = self._get_state_url(state, "standings")
            html = await self.http_client.get_text(standings_url, cache_ttl=7200)
            soup = parse_html(html)

            # STEP 3: Find standings table
            standings_table = find_stat_table(soup, header_text="Standings")
            if not standings_table:
                standings_table = soup.find("table")

            if not standings_table:
                self.logger.warning("No standings table found", state=state)
                return None

            rows = extract_table_data(standings_table)

            # Extract team name from ID
            team_name = (
                team_id.replace(f"bound_{state.lower()}_team_", "").replace("_", " ").title()
            )

            # STEP 4: Find team row
            for row in rows:
                row_team = row.get("Team") or row.get("School") or row.get("SCHOOL")
                if row_team and team_name.lower() in row_team.lower():
                    return self._parse_team_from_standings_row(row, team_id, state, standings_url)

            self.logger.warning("Team not found in standings", team_id=team_id, state=state)
            return None

        except Exception as e:
            self.logger.error("Failed to get team", team_id=team_id, error=str(e))
            return None

    def _parse_team_from_standings_row(
        self, row: dict, team_id: str, state: str, source_url: str
    ) -> Optional[Team]:
        """Parse team from standings row."""
        try:
            team_name = row.get("Team") or row.get("School") or row.get("SCHOOL") or ""

            # Parse record
            record = row.get("Record") or row.get("W-L")
            wins, losses = parse_record(record) if record else (None, None)

            # Try separate columns
            if wins is None:
                wins = parse_int(row.get("W") or row.get("Wins"))
            if losses is None:
                losses = parse_int(row.get("L") or row.get("Losses"))

            # Get conference/division
            conference = row.get("Conference") or row.get("Division") or row.get("League")

            data_source = self.create_data_source_metadata(
                url=source_url, quality_flag=DataQualityFlag.COMPLETE
            )

            team_data = {
                "team_id": team_id,
                "team_name": team_name,
                "school_name": team_name,
                "state": state,
                "country": "USA",
                "level": TeamLevel.HIGH_SCHOOL_VARSITY,
                "league": f"Bound {self.STATE_NAMES[state]}",
                "conference": conference,
                "season": "2024-25",
                "wins": wins,
                "losses": losses,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Team, team_data, f"team {team_name} ({state})")

        except Exception as e:
            self.logger.error("Failed to parse team from standings row", error=str(e))
            return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        state: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games from state schedule page.

        **IMPLEMENTATION STEPS:**
        1. Validate state parameter
        2. Fetch state schedule page
        3. Find schedule table
        4. Parse games
        5. Filter by date/team

        Args:
            team_id: Filter by team
            state: State code (required for meaningful results)
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            List of Game objects

        Example:
            games = await bound.get_games(state="IA", limit=50)
        """
        try:
            if not state:
                if team_id:
                    # Try to extract from team_id
                    parts = team_id.split("_")
                    if len(parts) >= 3 and parts[0] == "bound":
                        state = parts[1].upper()

            if not state:
                self.logger.warning("State required for games query")
                return []

            state = self._validate_state(state)

            # STEP 2: Fetch schedule page
            schedule_url = self._get_state_url(state, "schedule")
            html = await self.http_client.get_text(schedule_url, cache_ttl=3600)
            soup = parse_html(html)

            # STEP 3: Find schedule table
            schedule_table = find_stat_table(soup, header_text="Schedule")
            if not schedule_table:
                schedule_table = soup.find("table")

            if not schedule_table:
                self.logger.warning("No schedule table found", state=state)
                return []

            rows = extract_table_data(schedule_table)

            # STEP 4: Parse games
            games = []
            data_source = self.create_data_source_metadata(
                url=schedule_url, quality_flag=DataQualityFlag.PARTIAL
            )

            for row in rows[:limit]:
                game = self._parse_game_from_schedule_row(row, state, data_source)
                if not game:
                    continue

                # Apply filters
                if team_id and team_id not in [game.home_team_id, game.away_team_id]:
                    continue

                games.append(game)

            self.logger.info(f"Found {len(games)} games", state=state)
            return games

        except Exception as e:
            self.logger.error("Failed to get games", state=state, error=str(e))
            return []

    def _parse_game_from_schedule_row(
        self, row: dict, state: str, data_source
    ) -> Optional[Game]:
        """Parse game from schedule row."""
        try:
            # Extract game info
            home_team = row.get("Home") or row.get("Home Team")
            away_team = row.get("Away") or row.get("Away Team")
            date_str = row.get("Date") or row.get("DATE")
            time_str = row.get("Time") or row.get("TIME")
            score = row.get("Score") or row.get("Result")

            if not home_team or not away_team:
                return None

            # Build team IDs
            home_team_id = f"bound_{state.lower()}_team_{home_team.lower().replace(' ', '_')}"
            away_team_id = f"bound_{state.lower()}_team_{away_team.lower().replace(' ', '_')}"

            # Generate game ID
            game_id = f"bound_{state.lower()}_game_{home_team.lower().replace(' ', '_')}_vs_{away_team.lower().replace(' ', '_')}"

            # Parse scores if available
            home_score = None
            away_score = None
            status = GameStatus.SCHEDULED

            if score and score.strip():
                # Try to parse score (format: "75-68" or "Home 75, Away 68")
                score_parts = score.replace("-", " ").split()
                if len(score_parts) >= 2:
                    home_score = parse_int(score_parts[0])
                    away_score = parse_int(score_parts[1])
                    if home_score is not None and away_score is not None:
                        status = GameStatus.FINAL

            game_data = {
                "game_id": game_id,
                "home_team_id": home_team_id,
                "home_team_name": home_team,
                "away_team_id": away_team_id,
                "away_team_name": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "status": status,
                "level": "high_school_varsity",
                "season": "2024-25",
                "game_type": GameType.REGULAR,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Game, game_data, f"game {game_id}")

        except Exception as e:
            self.logger.error("Failed to parse game from schedule row", error=str(e))
            return None

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard for a state.

        **IMPLEMENTATION STEPS:**
        1. Validate state parameter
        2. Fetch state leaders page
        3. Find leaderboard table for specific stat
        4. Sort and build entries using build_leaderboard_entry()

        Args:
            stat: Stat category (e.g., 'points', 'rebounds', 'assists')
            season: Season filter
            state: State code (required)
            limit: Maximum results

        Returns:
            List of leaderboard entries

        Example:
            # Iowa scoring leaders (flagship state)
            leaders = await bound.get_leaderboard("points", state="IA", limit=20)
        """
        try:
            if not state:
                self.logger.error("State parameter required for leaderboard")
                return []

            state = self._validate_state(state)

            # STEP 2: Fetch leaders/stats page
            leaders_url = self._get_state_url(state, "stats")
            html = await self.http_client.get_text(leaders_url, cache_ttl=3600)
            soup = parse_html(html)

            # STEP 3: Find stat-specific table
            # Try to find table for specific stat
            stat_variations = {
                "points": ["PPG", "Points", "Scoring"],
                "rebounds": ["RPG", "Rebounds", "Rebounding"],
                "assists": ["APG", "Assists"],
                "steals": ["SPG", "Steals"],
                "blocks": ["BPG", "Blocks"],
            }

            stat_keywords = stat_variations.get(stat.lower(), [stat])

            leaderboard_table = None
            for keyword in stat_keywords:
                leaderboard_table = find_stat_table(soup, header_text=keyword)
                if leaderboard_table:
                    break

            if not leaderboard_table:
                # Fallback to main stats table
                leaderboard_table = find_stat_table(soup)

            if not leaderboard_table:
                self.logger.warning("No leaderboard table found", state=state, stat=stat)
                return []

            rows = extract_table_data(leaderboard_table)

            # STEP 4: Build leaderboard entries
            leaderboard = []

            # Map stat name to column name
            stat_column_map = {
                "points": ["PPG", "Points", "PTS"],
                "rebounds": ["RPG", "Rebounds", "REB"],
                "assists": ["APG", "Assists", "AST"],
                "steals": ["SPG", "Steals", "STL"],
                "blocks": ["BPG", "Blocks", "BLK"],
            }

            stat_columns = stat_column_map.get(stat.lower(), [stat.upper()])

            for i, row in enumerate(rows[:limit], 1):
                player_name = clean_player_name(
                    row.get("Player") or row.get("NAME") or row.get("Name") or ""
                )
                team_name = row.get("Team") or row.get("School") or row.get("SCHOOL")

                # Find stat value
                stat_value = None
                for col in stat_columns:
                    stat_value = parse_float(row.get(col))
                    if stat_value is not None:
                        break

                if not player_name or stat_value is None:
                    continue

                # Build entry using helper
                entry = build_leaderboard_entry(
                    rank=i,
                    player_name=player_name,
                    stat_value=stat_value,
                    stat_name=stat,
                    season=season or "2024-25",
                    source_prefix=f"bound_{state.lower()}",
                    team_name=team_name,
                )

                # Add state context
                entry["state"] = state
                entry["league"] = f"Bound {self.STATE_NAMES[state]}"

                leaderboard.append(entry)

            self.logger.info(f"Built leaderboard", state=state, stat=stat, entries=len(leaderboard))
            return leaderboard

        except ValueError as e:
            self.logger.error("Invalid state", error=str(e))
            return []
        except Exception as e:
            self.logger.error("Failed to get leaderboard", state=state, stat=stat, error=str(e))
            return []

    async def get_leaderboards_all_states(
        self, stat: str, season: Optional[str] = None, limit: int = 50
    ) -> dict[str, list[dict]]:
        """
        Get leaderboards for all supported states.

        Convenience method for fetching leaderboards across all states.
        Particularly useful for comparing stats across Midwest states.

        Args:
            stat: Stat category
            season: Season filter
            limit: Maximum results per state

        Returns:
            Dictionary mapping state code to leaderboard entries

        Example:
            all_leaders = await bound.get_leaderboards_all_states("points", limit=10)
            ia_leaders = all_leaders["IA"]  # Iowa (flagship state)
            il_leaders = all_leaders["IL"]  # Illinois
        """
        results = {}

        for state in self.SUPPORTED_STATES:
            try:
                leaderboard = await self.get_leaderboard(
                    stat=stat, season=season, state=state, limit=limit
                )
                results[state] = leaderboard
                self.logger.info(f"Got leaderboard for {state}", entries=len(leaderboard))
            except Exception as e:
                self.logger.error(f"Failed to get leaderboard for {state}", error=str(e))
                results[state] = []

        return results
