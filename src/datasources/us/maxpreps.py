"""
MaxPreps DataSource Adapter

Scrapes player and team statistics from MaxPreps.
UNIVERSAL COVERAGE: All 50 US states + DC.

**LEGAL WARNING**:
MaxPreps (CBS Sports Interactive) Terms of Service prohibit automated scraping.
This adapter is provided for:
1. Educational purposes
2. Research and analysis
3. With explicit permission from MaxPreps/CBS Sports

RECOMMENDED: Contact MaxPreps for commercial data licensing
Email: coachsupport@maxpreps.com | Phone: 800-329-7324

**DO NOT use this adapter for commercial purposes without authorization.**

Base URL: https://www.maxpreps.com
Data Available:
    - Player season stats (PPG, RPG, APG, FG%, 3P%, FT%, etc.)
    - Player game logs
    - Team schedules and scores
    - State rankings and leaderboards
    - Grad year, height, weight, position

Browser Automation: Required (MaxPreps uses React/dynamic content)
"""

from datetime import datetime
from typing import List, Optional

from ...models import (
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    Game,
    Player,
    PlayerGameStats,
    PlayerLevel,
    PlayerSeasonStats,
    Position,
    Team,
)
from ...utils import (
    clean_player_name,
    extract_table_data,
    get_text_or_none,
    parse_float,
    parse_html,
    parse_int,
)
from ...utils.browser_client import BrowserClient
from ...utils.scraping_helpers import (
    find_stat_table,
    parse_grad_year,
    standardize_stat_columns,
)
from ..base import BaseDataSource


class MaxPrepsDataSource(BaseDataSource):
    """
    MaxPreps data source adapter with universal US state coverage.

    Provides access to high school basketball statistics across all 50 US states + DC.
    Uses browser automation to handle React-based dynamic content.

    **IMPORTANT - LEGAL COMPLIANCE**:
    - MaxPreps Terms of Service prohibit scraping
    - This adapter should only be used with explicit permission
    - Recommended: Purchase commercial data license from MaxPreps
    - Alternative: Use for educational/research purposes only

    **Supported States**: All 50 US states + DC (51 total)

    **Data Quality**: High (official state stats partner in many states)

    **Rate Limiting**: Conservative (10 req/min default)

    **Caching**: Aggressive (2-hour TTL) to minimize network requests

    Base URL: https://www.maxpreps.com
    Browser Automation: Required (React rendering)
    """

    source_type = DataSourceType.MAXPREPS
    source_name = "MaxPreps"
    base_url = "https://www.maxpreps.com"
    region = DataSourceRegion.US

    # All US states + DC (51 total)
    ALL_US_STATES = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
    ]

    # State full names for metadata and logging
    STATE_NAMES = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
        "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
        "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
        "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
        "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
        "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
        "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
        "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
        "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
        "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
        "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
        "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"
    }

    # State normalization map - handles common variants and abbreviations
    # Maps all possible input formats to canonical 2-letter state codes
    # Enhancement 12.1: State Normalization (handles "Florida" → "FL", "Fla" → "FL", etc.)
    STATE_NORMALIZATION = {
        # Full state names (lowercase for case-insensitive matching)
        "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
        "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
        "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
        "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
        "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
        "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
        "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
        "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
        "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
        "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
        "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
        "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
        "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",

        # Common abbreviations and variants
        "ala": "AL", "alas": "AK", "ariz": "AZ", "ark": "AR",
        "calif": "CA", "cal": "CA", "cali": "CA", "colo": "CO", "conn": "CT", "del": "DE",
        "fla": "FL", "ga": "GA", "haw": "HI", "ida": "ID",
        "ill": "IL", "ind": "IN", "ia": "IA", "kans": "KS", "kan": "KS",
        "ky": "KY", "la": "LA", "mass": "MA", "mich": "MI", "minn": "MN", "miss": "MS",
        "mo": "MO", "mont": "MT", "neb": "NE", "nebr": "NE", "nev": "NV",
        "n.h.": "NH", "n.j.": "NJ", "n.m.": "NM", "n.y.": "NY",
        "n.c.": "NC", "n.d.": "ND", "okla": "OK",
        "ore": "OR", "oreg": "OR", "penn": "PA", "pa": "PA", "penna": "PA",
        "r.i.": "RI", "s.c.": "SC", "s.d.": "SD", "tenn": "TN",
        "tex": "TX", "vt": "VT", "va": "VA", "wash": "WA", "w.v.": "WV", "w.va.": "WV",
        "wis": "WI", "wisc": "WI", "wyo": "WY", "d.c.": "DC", "washington dc": "DC",

        # Already canonical (2-letter codes)
        "al": "AL", "ak": "AK", "az": "AZ", "ar": "AR",
        "ca": "CA", "co": "CO", "ct": "CT", "de": "DE",
        "fl": "FL", "ga": "GA", "hi": "HI", "id": "ID",
        "il": "IL", "in": "IN", "ia": "IA", "ks": "KS",
        "ky": "KY", "la": "LA", "me": "ME", "md": "MD",
        "ma": "MA", "mi": "MI", "mn": "MN", "ms": "MS",
        "mo": "MO", "mt": "MT", "ne": "NE", "nv": "NV",
        "nh": "NH", "nj": "NJ", "nm": "NM", "ny": "NY",
        "nc": "NC", "nd": "ND", "oh": "OH", "ok": "OK",
        "or": "OR", "pa": "PA", "ri": "RI", "sc": "SC",
        "sd": "SD", "tn": "TN", "tx": "TX", "ut": "UT",
        "vt": "VT", "va": "VA", "wa": "WA", "wv": "WV",
        "wi": "WI", "wy": "WY", "dc": "DC",
    }

    @staticmethod
    def normalize_state(raw_state: Optional[str]) -> Optional[str]:
        """
        Normalize state input to canonical 2-letter state code.

        Handles all common variants:
        - Full names: "Florida" → "FL"
        - Abbreviations: "Fla" → "FL", "Calif" → "CA"
        - Already canonical: "FL" → "FL"
        - Case-insensitive: "florida", "FLORIDA", "Florida" → "FL"
        - With periods: "N.Y." → "NY", "D.C." → "DC"

        Args:
            raw_state: Raw state input (any format)

        Returns:
            Canonical 2-letter state code or None if not recognized

        Examples:
            >>> MaxPrepsDataSource.normalize_state("Florida")
            "FL"
            >>> MaxPrepsDataSource.normalize_state("Fla")
            "FL"
            >>> MaxPrepsDataSource.normalize_state("fl")
            "FL"
            >>> MaxPrepsDataSource.normalize_state("N.Y.")
            "NY"
            >>> MaxPrepsDataSource.normalize_state("International")
            None
        """
        if not raw_state:
            return None

        # Clean input: strip whitespace, lowercase, remove extra periods
        cleaned = raw_state.strip().lower()

        # Try direct lookup in normalization map
        if cleaned in MaxPrepsDataSource.STATE_NORMALIZATION:
            return MaxPrepsDataSource.STATE_NORMALIZATION[cleaned]

        # Not found - likely international or invalid
        return None

    def __init__(self):
        """
        Initialize MaxPreps datasource with universal US coverage.

        Sets up:
        - Browser automation client (required for React content)
        - State-specific URL patterns for all 51 states
        - Aggressive caching to minimize network requests
        - Conservative rate limiting for ToS compliance
        """
        super().__init__()

        # Build state-specific URL patterns for all 51 states
        # URL Pattern: https://www.maxpreps.com/{state}/basketball/
        self.state_urls = {
            state: f"{self.base_url}/{state.lower()}/basketball"
            for state in self.ALL_US_STATES
        }

        # Initialize browser client for React content rendering
        # MaxPreps uses React for stats tables and dynamic content
        self.browser_client = BrowserClient(
            settings=self.settings,
            browser_type=getattr(self.settings, 'browser_type', "chromium"),
            headless=getattr(self.settings, 'browser_headless', True),
            timeout=getattr(self.settings, 'browser_timeout', 30000),
            cache_enabled=getattr(self.settings, 'browser_cache_enabled', True),
            cache_ttl=getattr(self.settings, 'browser_cache_ttl', 7200),  # 2 hours
        )

        self.logger.info(
            f"MaxPreps initialized with {len(self.ALL_US_STATES)} states",
            states_count=len(self.ALL_US_STATES),
            browser_automation=True,
            cache_ttl_hours=2,
        )

        # Log legal warning
        self.logger.warning(
            "MaxPreps ToS prohibits scraping - use with explicit permission only",
            recommendation="Contact MaxPreps for commercial data licensing",
        )

    def _validate_state(self, state: Optional[str]) -> str:
        """
        Validate and normalize state parameter.

        Uses normalize_state() to handle all variants (full names, abbreviations, etc.)
        Ensures state is valid 2-letter US state code.
        Fails fast to avoid unnecessary network calls.

        Enhancement 12.1: Now accepts "Florida", "Fla", "FL", etc.

        Args:
            state: State input (any format: "FL", "Florida", "Fla", etc.)

        Returns:
            Canonical 2-letter uppercase state code

        Raises:
            ValueError: If state is None, empty, or not recognized

        Example:
            >>> self._validate_state("ca")
            "CA"
            >>> self._validate_state("California")
            "CA"
            >>> self._validate_state("Calif")
            "CA"
            >>> self._validate_state("ZZ")
            ValueError: State 'ZZ' not recognized
        """
        if not state:
            raise ValueError(
                f"State parameter required. "
                f"Supported formats: 2-letter codes (CA, FL, TX), "
                f"full names (California, Florida, Texas), "
                f"or common abbreviations (Calif, Fla, Tex)"
            )

        # Use normalize_state to handle all variants
        normalized = self.normalize_state(state)

        if not normalized:
            raise ValueError(
                f"State '{state}' not recognized. "
                f"Supported: {', '.join(self.ALL_US_STATES[:10])}... "
                f"(and {len(self.ALL_US_STATES) - 10} more). "
                f"Use 2-letter codes, full names, or common abbreviations."
            )

        return normalized

    def _get_state_url(self, state: str, endpoint: str = "") -> str:
        """
        Build state-specific URL for MaxPreps endpoints.

        Constructs URLs for different MaxPreps pages (stats, rankings, teams, etc.)

        Args:
            state: Validated state code (must call _validate_state first)
            endpoint: Additional path segment (e.g., "stat-leaders", "rankings")

        Returns:
            Full URL for the requested state endpoint

        Example:
            >>> self._get_state_url("CA", "stat-leaders")
            "https://www.maxpreps.com/ca/basketball/stat-leaders"

            >>> self._get_state_url("TX")
            "https://www.maxpreps.com/tx/basketball"
        """
        base = self.state_urls[state]
        if endpoint:
            return f"{base}/{endpoint.lstrip('/')}"
        return base

    def _build_player_id(self, state: str, player_name: str, player_school: Optional[str] = None) -> str:
        """
        Build MaxPreps player ID with state and school context.

        Creates unique identifier for cross-referencing players.
        Format: maxpreps_{state}_{school}_{name} (all lowercase, underscores)

        Args:
            state: State code
            player_name: Player full name
            player_school: School name (optional but recommended for uniqueness)

        Returns:
            Player ID string

        Example:
            >>> self._build_player_id("CA", "John Doe", "Lincoln High")
            "maxpreps_ca_lincoln_high_john_doe"

            >>> self._build_player_id("TX", "Jane Smith")
            "maxpreps_tx_jane_smith"
        """
        clean_name = clean_player_name(player_name).lower().replace(" ", "_")

        if player_school:
            clean_school = player_school.lower().replace(" ", "_").replace("high_school", "hs")
            return f"maxpreps_{state.lower()}_{clean_school}_{clean_name}"

        return f"maxpreps_{state.lower()}_{clean_name}"

    def _extract_state_from_player_id(self, player_id: str) -> Optional[str]:
        """
        Extract state code from MaxPreps player ID.

        Parses player ID to determine which state the player is from.

        Args:
            player_id: Player ID (format: maxpreps_{state}_{school}_{name})

        Returns:
            State code or None if invalid format

        Example:
            >>> self._extract_state_from_player_id("maxpreps_ca_lincoln_hs_john_doe")
            "CA"

            >>> self._extract_state_from_player_id("invalid_id")
            None
        """
        parts = player_id.split("_")
        if len(parts) >= 2 and parts[0] == "maxpreps":
            state = parts[1].upper()
            return state if state in self.ALL_US_STATES else None
        return None

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by MaxPreps player ID.

        MaxPreps doesn't have direct player profile pages accessible by simple ID.
        This method extracts state from player_id and searches through stats tables.

        Args:
            player_id: Player identifier (format: maxpreps_{state}_{school}_{name})

        Returns:
            Player object or None if not found

        Example:
            >>> player = await maxpreps.get_player("maxpreps_ca_lincoln_hs_john_doe")
        """
        try:
            # Extract state from player_id
            state = self._extract_state_from_player_id(player_id)
            if not state:
                self.logger.warning(
                    "Could not extract state from player_id",
                    player_id=player_id
                )
                return None

            # Extract player name from ID (simplified)
            # Format: maxpreps_{state}_{school}_{firstname}_{lastname}
            name_parts = player_id.replace(f"maxpreps_{state.lower()}_", "").split("_")
            # Remove school part (usually first 1-2 segments)
            # This is a simplified extraction - may need refinement
            player_name = " ".join(name_parts[-2:]).title() if len(name_parts) >= 2 else " ".join(name_parts).title()

            # Search for player in state stats
            players = await self.search_players(state=state, name=player_name, limit=1)
            return players[0] if players else None

        except Exception as e:
            self.logger.error(
                "Failed to get player by ID",
                player_id=player_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    async def search_players(
        self,
        state: str,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[Player]:
        """
        Search for players in MaxPreps state stats tables.

        **PRIMARY METHOD** for finding players. Fetches state leaderboard/stats page
        and extracts player data from HTML tables.

        **Implementation Steps:**
        1. Validate state parameter (fail fast)
        2. Build stats URL for state
        3. Use BrowserClient to render React content
        4. Find stats table in rendered HTML
        5. Parse player rows and extract stats
        6. Filter by name/team if provided
        7. Return list of Player objects

        Args:
            state: US state code (required, e.g., "CA", "TX", "NY")
            name: Player name filter (partial match, case-insensitive)
            team: Team/school name filter (partial match, case-insensitive)
            season: Season filter (e.g., "2024-25") - currently uses latest
            limit: Maximum number of results to return

        Returns:
            List of Player objects matching search criteria

        Raises:
            ValueError: If state is invalid

        Example:
            >>> players = await maxpreps.search_players(
            ...     state="CA",
            ...     name="Smith",
            ...     team="Lincoln",
            ...     limit=10
            ... )
        """
        try:
            # Step 1: Validate state (fail fast before network call)
            state = self._validate_state(state)

            self.logger.info(
                "Searching MaxPreps players",
                state=state,
                state_name=self.STATE_NAMES.get(state),
                name_filter=name,
                team_filter=team,
                limit=limit
            )

            # Step 2: Build state stats/leaderboard URL
            # MaxPreps URL pattern: /[state]/basketball/stat-leaders/
            stats_url = self._get_state_url(state, "stat-leaders")

            # Step 3: Fetch rendered HTML using browser automation
            # MaxPreps uses React, so we need browser to render the content
            self.logger.debug(f"Fetching MaxPreps stats page", url=stats_url)

            html = await self.browser_client.get_rendered_html(
                url=stats_url,
                wait_for="table",  # Wait for stats table to render
                wait_timeout=30000,  # 30 seconds
                wait_for_network_idle=True,  # Ensure React finishes loading
            )

            # Step 4: Parse rendered HTML
            soup = parse_html(html)

            # Step 5: Find stats table (look for common MaxPreps table classes/IDs)
            stats_table = find_stat_table(soup)

            if not stats_table:
                self.logger.warning(
                    "No stats table found on MaxPreps page",
                    state=state,
                    url=stats_url
                )
                return []

            # Step 6: Extract table data
            rows = extract_table_data(stats_table)

            if not rows:
                self.logger.warning(
                    "Stats table found but no rows extracted",
                    state=state
                )
                return []

            self.logger.info(
                f"Extracted {len(rows)} rows from MaxPreps stats table",
                state=state,
                rows=len(rows)
            )

            # Step 7: Parse players from rows
            players = []
            data_source = self.create_data_source_metadata(
                url=stats_url,
                quality_flag=DataQualityFlag.COMPLETE,
                notes=f"MaxPreps {self.STATE_NAMES.get(state, state)} stats"
            )

            for row in rows[:limit * 2]:  # Parse 2x limit to allow for filtering
                player, _ = self._parse_player_and_stats_from_row(row, state, data_source)

                if player:
                    # Apply filters
                    if name and name.lower() not in player.full_name.lower():
                        continue

                    if team and player.school_name and team.lower() not in player.school_name.lower():
                        continue

                    players.append(player)

                    # Stop once we hit limit
                    if len(players) >= limit:
                        break

            self.logger.info(
                f"Found {len(players)} players after filtering",
                state=state,
                filters={"name": name, "team": team}
            )

            return players

        except ValueError as e:
            # State validation error - re-raise
            raise

        except Exception as e:
            self.logger.error(
                "Failed to search MaxPreps players",
                state=state,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def search_players_with_stats(
        self,
        state: str,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[tuple[Player, Optional[PlayerSeasonStats]]]:
        """
        Search for players AND their season statistics from MaxPreps.

        **ENHANCED METHOD** - Returns both Player and PlayerSeasonStats objects.

        This method fetches stat leader pages which typically include:
        - Player demographic info (name, school, class, position, height, weight)
        - Season statistics (PPG, RPG, APG, SPG, BPG, FG%, 3P%, FT%, etc.)

        This is the PRIMARY method for forecasting pipelines as it extracts
        ALL available data in a single request.

        Args:
            state: US state code (required, e.g., "CA", "TX", "NY")
            name: Player name filter (partial match, case-insensitive)
            team: Team/school name filter (partial match, case-insensitive)
            season: Season filter (e.g., "2024-25"), auto-detected if None
            limit: Maximum number of results to return

        Returns:
            List of (Player, PlayerSeasonStats) tuples
            If stats not available for a player: (Player, None)

        Example:
            >>> results = await maxpreps.search_players_with_stats(
            ...     state="CA",
            ...     name="Smith",
            ...     limit=10
            ... )
            >>> for player, stats in results:
            ...     if stats:
            ...         print(f"{player.full_name}: {stats.points_per_game} PPG")
        """
        try:
            # Step 1: Validate state
            state = self._validate_state(state)

            self.logger.info(
                "Searching MaxPreps players with stats",
                state=state,
                state_name=self.STATE_NAMES.get(state),
                name_filter=name,
                team_filter=team,
                limit=limit
            )

            # Step 2: Build stats URL
            stats_url = self._get_state_url(state, "stat-leaders")

            # Step 3: Fetch rendered HTML using browser automation
            self.logger.debug(f"Fetching MaxPreps stats page", url=stats_url)

            html = await self.browser_client.get_rendered_html(
                url=stats_url,
                wait_for="table",
                wait_timeout=30000,
                wait_for_network_idle=True,
            )

            # Step 4: Parse HTML
            soup = parse_html(html)

            # Step 5: Find stats table
            stats_table = find_stat_table(soup)

            if not stats_table:
                self.logger.warning(
                    "No stats table found on MaxPreps page",
                    state=state,
                    url=stats_url
                )
                return []

            # Step 6: Extract table data
            rows = extract_table_data(stats_table)

            if not rows:
                self.logger.warning(
                    "Stats table found but no rows extracted",
                    state=state
                )
                return []

            self.logger.info(
                f"Extracted {len(rows)} rows from MaxPreps stats table",
                state=state,
                rows=len(rows)
            )

            # Step 7: Parse players and stats
            results = []
            data_source = self.create_data_source_metadata(
                url=stats_url,
                quality_flag=DataQualityFlag.COMPLETE,
                notes=f"MaxPreps {self.STATE_NAMES.get(state, state)} stats"
            )

            for row in rows[:limit * 2]:  # Parse 2x limit to allow for filtering
                player, stats = self._parse_player_and_stats_from_row(
                    row, state, data_source, season
                )

                if player:
                    # Apply filters
                    if name and name.lower() not in player.full_name.lower():
                        continue

                    if team and player.school_name and team.lower() not in player.school_name.lower():
                        continue

                    results.append((player, stats))

                    # Stop once we hit limit
                    if len(results) >= limit:
                        break

            self.logger.info(
                f"Found {len(results)} players with stats after filtering",
                state=state,
                with_stats=sum(1 for _, s in results if s is not None),
                filters={"name": name, "team": team}
            )

            return results

        except ValueError as e:
            # State validation error - re-raise
            raise

        except Exception as e:
            self.logger.error(
                "Failed to search MaxPreps players with stats",
                state=state,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    def _parse_player_and_stats_from_row(
        self,
        row: dict,
        state: str,
        data_source,
        season: Optional[str] = None
    ) -> tuple[Optional[Player], Optional[PlayerSeasonStats]]:
        """
        Parse BOTH player info AND season statistics from MaxPreps stats table row.

        **ENHANCED VERSION** - Extracts ALL available metrics from stat leader pages.

        MaxPreps stat leader tables typically include:
        - Player info: Name, School, Class, Position, Height, Weight
        - Season stats: PPG, RPG, APG, SPG, BPG, FG%, 3P%, FT%, GP

        This method extracts EVERYTHING available to maximize data for forecasting.

        Args:
            row: Dictionary of column_name -> value from stats table
            state: State code for context
            data_source: DataSource metadata object
            season: Season string (e.g., "2024-25"), auto-detected if None

        Returns:
            Tuple of (Player, PlayerSeasonStats) or (None, None) if parsing fails
            If player found but no stats: (Player, None)

        Example row:
            {
                "Rank": "1",
                "Player": "John Doe",
                "School": "Lincoln High School",
                "Class": "2026",
                "Pos": "SG",
                "GP": "25",
                "PPG": "25.3",
                "RPG": "5.2",
                "APG": "4.1",
                "SPG": "2.3",
                "BPG": "0.8",
                "FG%": "52.5",
                "3P%": "38.2",
                "FT%": "85.0",
                ...
            }
        """
        try:
            # ========================================
            # STEP 1: Extract Player Information
            # ========================================

            # Extract player name (various possible column names)
            player_name = (
                row.get("Player") or
                row.get("NAME") or
                row.get("Name") or
                row.get("PLAYER") or
                row.get("Athlete")  # Some sites use "Athlete"
            )

            if not player_name:
                self.logger.debug("No player name found in row", row_keys=list(row.keys()))
                return None, None

            # Clean player name
            player_name = player_name.strip()

            # Split into first/last name
            name_parts = player_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            else:
                first_name = player_name
                last_name = ""

            # Extract school
            school_name = (
                row.get("School") or
                row.get("SCHOOL") or
                row.get("Team") or
                row.get("TEAM") or
                row.get("High School")
            )

            # Extract position
            position_str = (
                row.get("Pos") or
                row.get("POS") or
                row.get("Position") or
                row.get("POSITION")
            )

            position = None
            if position_str:
                # Map to Position enum (expanded)
                position_map = {
                    "PG": Position.PG, "SG": Position.SG,
                    "SF": Position.SF, "PF": Position.PF,
                    "C": Position.C, "G": Position.G,
                    "F": Position.F, "GF": Position.GF,
                    "FC": Position.FC
                }
                position = position_map.get(position_str.upper().strip())

            # Extract grad year
            grad_year = None
            class_str = (
                row.get("Class") or
                row.get("CLASS") or
                row.get("Yr") or
                row.get("Year") or
                row.get("Grad Year")
            )

            if class_str:
                grad_year = parse_grad_year(class_str)

            # Extract height (various formats: "6-5", "6'5\"", "77")
            height_str = (
                row.get("Ht") or
                row.get("Height") or
                row.get("HT") or
                row.get("H")
            )

            height_inches = None
            if height_str:
                try:
                    height_str = str(height_str).strip()
                    # Handle formats: "6-5", "6'5\"", or "77"
                    if "-" in height_str or "'" in height_str:
                        parts = height_str.replace("'", "-").replace('"', "").split("-")
                        if len(parts) == 2:
                            feet = parse_int(parts[0])
                            inches = parse_int(parts[1])
                            if feet and inches:
                                height_inches = (feet * 12) + inches
                    else:
                        # Direct inches
                        height_inches = parse_int(height_str)
                except:
                    pass

            # Extract weight
            weight_str = (
                row.get("Wt") or
                row.get("Weight") or
                row.get("WT") or
                row.get("W")
            )
            weight_lbs = parse_int(weight_str) if weight_str else None

            # Build player ID
            player_id = self._build_player_id(state, player_name, school_name)

            # Create Player object
            player = Player(
                player_id=player_id,
                first_name=first_name,
                last_name=last_name,
                full_name=player_name,
                height_inches=height_inches,
                weight_lbs=weight_lbs,
                position=position,
                school_name=school_name,
                school_state=state,
                school_country="USA",
                grad_year=grad_year,
                level=PlayerLevel.HIGH_SCHOOL,
                data_source=data_source,
            )

            # ========================================
            # STEP 2: Extract Season Statistics
            # ========================================

            # Games played
            gp = parse_int(
                row.get("GP") or
                row.get("Games") or
                row.get("G") or
                row.get("Games Played")
            )

            # Points per game / Total points
            ppg = parse_float(
                row.get("PPG") or
                row.get("Points") or
                row.get("PTS") or
                row.get("Pts/G")
            )

            total_points = parse_int(
                row.get("Total Points") or
                row.get("Total PTS") or
                row.get("Pts")
            )

            # If we have total points and GP, calculate PPG
            if not ppg and total_points and gp and gp > 0:
                ppg = round(total_points / gp, 1)

            # Rebounds per game / Total rebounds
            rpg = parse_float(
                row.get("RPG") or
                row.get("Rebounds") or
                row.get("REB") or
                row.get("Rebs/G")
            )

            total_rebounds = parse_int(
                row.get("Total Rebounds") or
                row.get("Total REB") or
                row.get("Rebs")
            )

            # Assists per game / Total assists
            apg = parse_float(
                row.get("APG") or
                row.get("Assists") or
                row.get("AST") or
                row.get("Asts/G")
            )

            total_assists = parse_int(
                row.get("Total Assists") or
                row.get("Total AST") or
                row.get("Asts")
            )

            # Steals per game / Total steals
            spg = parse_float(
                row.get("SPG") or
                row.get("Steals") or
                row.get("STL") or
                row.get("Stls/G")
            )

            total_steals = parse_int(
                row.get("Total Steals") or
                row.get("Total STL")
            )

            # Blocks per game / Total blocks
            bpg = parse_float(
                row.get("BPG") or
                row.get("Blocks") or
                row.get("BLK") or
                row.get("Blks/G")
            )

            total_blocks = parse_int(
                row.get("Total Blocks") or
                row.get("Total BLK")
            )

            # Minutes per game
            mpg = parse_float(
                row.get("MPG") or
                row.get("Minutes") or
                row.get("MIN") or
                row.get("Mins/G")
            )

            # Shooting percentages
            fg_pct = parse_float(
                row.get("FG%") or
                row.get("FG Pct") or
                row.get("Field Goal %")
            )

            three_pt_pct = parse_float(
                row.get("3P%") or
                row.get("3PT%") or
                row.get("3-PT%") or
                row.get("Three Point %")
            )

            ft_pct = parse_float(
                row.get("FT%") or
                row.get("FT Pct") or
                row.get("Free Throw %")
            )

            # Turnovers per game
            tpg = parse_float(
                row.get("TPG") or
                row.get("Turnovers") or
                row.get("TO") or
                row.get("TOs/G")
            )

            # Calculate season totals if we have per-game and GP
            if gp and gp > 0:
                if ppg and not total_points:
                    total_points = int(ppg * gp)
                if rpg and not total_rebounds:
                    total_rebounds = int(rpg * gp)
                if apg and not total_assists:
                    total_assists = int(apg * gp)
                if spg and not total_steals:
                    total_steals = int(spg * gp)
                if bpg and not total_blocks:
                    total_blocks = int(bpg * gp)

            # Only create PlayerSeasonStats if we have at least some stats
            has_stats = any([
                ppg, rpg, apg, spg, bpg, mpg,
                fg_pct, three_pt_pct, ft_pct,
                total_points, total_rebounds, total_assists
            ])

            if has_stats:
                # Determine season
                if not season:
                    current_year = datetime.now().year
                    # Assume current season (e.g., 2024-25)
                    season = f"{current_year}-{str(current_year + 1)[-2:]}"

                # Create PlayerSeasonStats object
                season_stats = PlayerSeasonStats(
                    player_id=player_id,
                    player_name=player_name,
                    season=season,
                    team_id=player_id,  # Use player_id as placeholder
                    team_name=school_name or "Unknown",

                    # Games
                    games_played=gp or 0,
                    games_started=None,  # Not typically provided

                    # Minutes
                    minutes_played=mpg,  # Per game average

                    # Scoring (totals)
                    points=total_points,

                    # Shooting percentages (percentages, not decimals)
                    field_goal_percentage=fg_pct,
                    three_point_percentage=three_pt_pct,
                    free_throw_percentage=ft_pct,

                    # Rebounds (totals)
                    total_rebounds=total_rebounds,
                    offensive_rebounds=None,  # Not typically provided
                    defensive_rebounds=None,

                    # Assists & Turnovers (totals)
                    assists=total_assists,
                    turnovers=int(tpg * gp) if tpg and gp else None,

                    # Defense (totals)
                    steals=total_steals,
                    blocks=total_blocks,

                    # Per-game averages stored in notes for reference
                    data_source=data_source,
                )

                return player, season_stats
            else:
                # No stats found, return just player
                return player, None

        except Exception as e:
            self.logger.warning(
                "Failed to parse player and stats from MaxPreps row",
                error=str(e),
                row_keys=list(row.keys()) if row else None
            )
            return None, None

    async def get_player_season_stats(
        self,
        player_id: str,
        season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics from MaxPreps.

        **NOT YET IMPLEMENTED** - Placeholder for future development.

        Would require:
        1. Extracting player MaxPreps URL from search results
        2. Fetching player profile page
        3. Parsing season stats table

        Args:
            player_id: MaxPreps player identifier
            season: Season string (e.g., "2024-25")

        Returns:
            PlayerSeasonStats or None

        TODO: Implement player profile page scraping
        """
        self.logger.warning(
            "get_player_season_stats not yet implemented for MaxPreps",
            player_id=player_id
        )
        return None

    async def get_player_game_stats(
        self,
        player_id: str,
        game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game statistics from MaxPreps.

        **NOT YET IMPLEMENTED** - Placeholder for future development.

        Would require:
        1. Accessing player game log page
        2. Finding specific game
        3. Extracting game stats

        Args:
            player_id: MaxPreps player identifier
            game_id: Game identifier

        Returns:
            PlayerGameStats or None

        TODO: Implement game log scraping
        """
        self.logger.warning(
            "get_player_game_stats not yet implemented for MaxPreps",
            player_id=player_id,
            game_id=game_id
        )
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team by ID from MaxPreps.

        **NOT YET IMPLEMENTED** - Placeholder for future development.

        Would require:
        1. Building team URL from team_id
        2. Fetching team page
        3. Parsing team roster, record, schedule

        Args:
            team_id: Team identifier

        Returns:
            Team object or None

        TODO: Implement team page scraping
        """
        self.logger.warning(
            "get_team not yet implemented for MaxPreps",
            team_id=team_id
        )
        return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        limit: int = 100,
    ) -> List[Game]:
        """
        Get games/schedule from MaxPreps.

        **NOT YET IMPLEMENTED** - Placeholder for future development.

        Would require:
        1. Accessing team schedule page
        2. Parsing game schedule table
        3. Extracting game details

        Args:
            team_id: Team identifier
            start_date: Filter by start date
            end_date: Filter by end date
            season: Season filter
            limit: Maximum results

        Returns:
            List of Game objects

        TODO: Implement schedule scraping
        """
        self.logger.warning(
            "get_games not yet implemented for MaxPreps",
            team_id=team_id
        )
        return []

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        """
        Get statistical leaderboard from MaxPreps.

        **PARTIALLY IMPLEMENTED** - Uses search_players with default state.

        For multi-state leaderboards, would need to:
        1. Fetch leaderboards from multiple states
        2. Aggregate results
        3. Sort by stat category

        Current implementation: Returns top players from one state.

        Args:
            stat: Stat category (e.g., 'points', 'rebounds', 'assists')
            season: Season filter
            limit: Maximum results

        Returns:
            List of leaderboard entries

        TODO: Implement true multi-state aggregation
        """
        self.logger.warning(
            "get_leaderboard partially implemented - single state only",
            stat=stat,
            note="Use search_players for state-specific leaderboards"
        )

        # Default to California for now (most data)
        try:
            players = await self.search_players(state="CA", limit=limit)

            # Convert to leaderboard entries
            return [
                {
                    "rank": idx + 1,
                    "player_id": player.player_id,
                    "player_name": player.full_name,
                    "school": player.school_name,
                    "stat_value": 0.0,  # Would need to extract from stats
                    "stat_category": stat,
                }
                for idx, player in enumerate(players)
            ]

        except Exception as e:
            self.logger.error(f"Failed to get leaderboard", stat=stat, error=str(e))
            return []

    async def close(self):
        """
        Close connections and browser instances.

        Cleanup method called when adapter is no longer needed.
        Browser is singleton so we don't close it here.
        """
        await super().close()
        # BrowserClient is singleton, managed globally
        # No explicit cleanup needed here
