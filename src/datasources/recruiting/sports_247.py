"""
247Sports Recruiting DataSource Adapter

Scrapes player recruiting rankings, offers, and predictions from 247Sports.
Provides comprehensive college basketball recruiting intelligence.

**LEGAL WARNING**:
247Sports Terms of Service likely prohibit automated scraping.
This adapter is provided for:
1. Educational purposes
2. Research and analysis
3. With explicit permission from 247Sports

RECOMMENDED: Contact 247Sports for commercial data licensing or API access

**DO NOT use this adapter for commercial purposes without authorization.**

Base URL: https://247sports.com
Data Available:
    - National rankings (1-200+)
    - Position rankings
    - State rankings
    - Star ratings (5★ to 3★)
    - Composite rankings (aggregates all services)
    - Height, weight, position
    - School, city, state
    - College commitments
    - Crystal Ball predictions (if available)

Browser Automation: Required (247Sports uses React/dynamic content)

Author: Claude Code
Date: 2025-11-14
"""

from datetime import datetime
from typing import List, Optional

from ...models import (
    CollegeOffer,
    ConferenceLevel,
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    OfferStatus,
    Position,
    RecruitingPrediction,
    RecruitingProfile,
    RecruitingRank,
    RecruitingService,
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
from .base_recruiting import BaseRecruitingSource


class Sports247DataSource(BaseRecruitingSource):
    """
    247Sports recruiting data source adapter.

    Provides access to comprehensive college basketball recruiting rankings,
    offers, and predictions.

    **IMPORTANT - LEGAL COMPLIANCE**:
    - 247Sports ToS likely prohibits scraping
    - This adapter should only be used with explicit permission
    - Recommended: Purchase commercial data license from 247Sports
    - Alternative: Use for educational/research purposes only

    **Data Coverage**:
    - National rankings for all class years
    - Composite rankings (aggregates ESPN, Rivals, On3, 247Sports)
    - Position and state rankings
    - Star ratings and numerical ratings
    - Commitment tracking

    **Rate Limiting**: Conservative (10 req/min default)

    **Caching**: Aggressive (2-hour TTL) to minimize network requests

    Base URL: https://247sports.com
    Browser Automation: Required (React rendering)
    """

    source_type = DataSourceType.SPORTS_247
    source_name = "247Sports"
    base_url = "https://247sports.com"
    region = DataSourceRegion.US

    # Available class years (typically current + next 4 years)
    AVAILABLE_YEARS = [2025, 2026, 2027, 2028, 2029]

    # Position mapping
    POSITION_MAP = {
        "PG": Position.PG,
        "SG": Position.SG,
        "SF": Position.SF,
        "PF": Position.PF,
        "C": Position.C,
        "COMBO": Position.G,  # Combo guard
        "WING": Position.GF,  # Wing player
        "PF/C": Position.FC,
    }

    def __init__(self):
        """
        Initialize 247Sports datasource with browser automation.

        Sets up:
        - Browser automation client (required for React content)
        - Conservative rate limiting (10 req/min default)
        - Aggressive caching (2-hour TTL)
        """
        super().__init__()

        # Initialize browser client for React content rendering
        # 247Sports uses React for rankings tables and dynamic content
        self.browser_client = BrowserClient(
            settings=self.settings,
            browser_type=getattr(self.settings, 'browser_type', "chromium"),
            headless=getattr(self.settings, 'browser_headless', True),
            timeout=getattr(self.settings, 'browser_timeout', 30000),
            cache_enabled=getattr(self.settings, 'browser_cache_enabled', True),
            cache_ttl=getattr(self.settings, 'browser_cache_ttl', 7200),  # 2 hours
        )

        self.logger.info(
            "247Sports initialized",
            browser_automation=True,
            cache_ttl_hours=2,
        )

        # Log legal warning
        self.logger.warning(
            "247Sports ToS likely prohibits scraping - use with explicit permission only",
            recommendation="Contact 247Sports for commercial data licensing",
        )

    def _validate_class_year(self, class_year: int) -> int:
        """
        Validate class year parameter.

        Args:
            class_year: Graduation year (e.g., 2025, 2026)

        Returns:
            Validated class year

        Raises:
            ValueError: If class year is invalid

        Example:
            >>> self._validate_class_year(2025)
            2025
            >>> self._validate_class_year(2020)
            ValueError: Class year 2020 not available
        """
        if class_year < 2025 or class_year > 2035:
            raise ValueError(
                f"Class year {class_year} not available. "
                f"Supported years: 2025-2035"
            )
        return class_year

    def _build_rankings_url(
        self,
        class_year: int,
        ranking_type: str = "composite"
    ) -> str:
        """
        Build 247Sports rankings URL.

        Args:
            class_year: Graduation year
            ranking_type: Type of ranking ("composite", "247sports", "industry")

        Returns:
            Full URL for rankings page

        Example:
            >>> self._build_rankings_url(2025, "composite")
            "https://247sports.com/season/2025-basketball/compositerecruitrankings/"
        """
        # URL pattern: /season/{year}-basketball/{rankingtype}recruitrankings/
        ranking_types = {
            "composite": "composite",
            "247sports": "",  # Default 247Sports rankings
            "industry": "industry",  # Industry composite
        }

        ranking_path = ranking_types.get(ranking_type, "composite")
        return f"{self.base_url}/season/{class_year}-basketball/{ranking_path}recruitrankings/"

    def _build_player_id(self, player_name: str, player_247_id: Optional[str] = None) -> str:
        """
        Build 247Sports player ID.

        Args:
            player_name: Player name
            player_247_id: 247Sports internal ID (if available)

        Returns:
            Player ID string

        Example:
            >>> self._build_player_id("John Doe", "12345")
            "247_12345"
            >>> self._build_player_id("John Doe")
            "247_john_doe"
        """
        if player_247_id:
            return f"247_{player_247_id}"

        clean_name = clean_player_name(player_name).lower().replace(" ", "_")
        return f"247_{clean_name}"

    async def get_rankings(
        self,
        class_year: int,
        limit: int = 100,
        position: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[RecruitingRank]:
        """
        Get 247Sports recruiting rankings for a class year.

        **PRIMARY METHOD** for fetching rankings. Uses browser automation
        to render React content and extract rankings table.

        **Implementation Steps:**
        1. Validate class year
        2. Build rankings URL
        3. Use BrowserClient to render React content
        4. Find rankings table in rendered HTML
        5. Parse player rows and extract data
        6. Filter by position/state if provided
        7. Return list of RecruitingRank objects

        Args:
            class_year: Graduation year (e.g., 2025, 2026)
            limit: Maximum number of results (default: 100)
            position: Filter by position (optional)
            state: Filter by state (optional)

        Returns:
            List of RecruitingRank objects

        Raises:
            ValueError: If class year is invalid

        Example:
            >>> rankings = await sports247.get_rankings(class_year=2025, limit=50)
            >>> for rank in rankings[:5]:
            ...     print(f"{rank.rank_national}. {rank.player_name} ({rank.stars}★)")
        """
        try:
            # Step 1: Validate class year
            class_year = self._validate_class_year(class_year)

            self.logger.info(
                "Fetching 247Sports rankings",
                class_year=class_year,
                limit=limit,
                position_filter=position,
                state_filter=state
            )

            # Step 2: Build rankings URL
            rankings_url = self._build_rankings_url(class_year, "composite")

            # Step 3: Fetch rendered HTML using browser automation
            self.logger.debug("Fetching 247Sports rankings page", url=rankings_url)

            html = await self.browser_client.get_rendered_html(
                url=rankings_url,
                wait_for="table",  # Wait for rankings table to render
                wait_timeout=30000,  # 30 seconds
                wait_for_network_idle=True,  # Ensure React finishes loading
            )

            # Step 4: Parse rendered HTML
            soup = parse_html(html)

            # Step 5: Find rankings table
            # 247Sports uses various table classes - try multiple selectors
            rankings_table = (
                soup.find("table", class_=lambda x: x and "rankings" in str(x).lower()) or
                soup.find("table", class_=lambda x: x and "recruit" in str(x).lower()) or
                soup.find("table")  # Fallback to first table
            )

            if not rankings_table:
                self.logger.warning(
                    "No rankings table found on 247Sports page",
                    class_year=class_year,
                    url=rankings_url
                )
                return []

            # Step 6: Extract table data
            rows = extract_table_data(rankings_table)

            if not rows:
                self.logger.warning(
                    "Rankings table found but no rows extracted",
                    class_year=class_year
                )
                return []

            self.logger.info(
                f"Extracted {len(rows)} rows from 247Sports rankings table",
                class_year=class_year
            )

            # Step 7: Parse rankings from rows
            rankings = []
            data_source = self.create_data_source_metadata(
                url=rankings_url,
                quality_flag=DataQualityFlag.COMPLETE,
                notes=f"247Sports {class_year} Composite Rankings"
            )

            for row in rows[:limit * 2]:  # Parse 2x limit to allow for filtering
                rank = self._parse_ranking_from_row(row, class_year, data_source)

                if rank:
                    # Apply filters
                    if position and rank.position and str(rank.position) != position:
                        continue

                    if state and rank.state and rank.state.upper() != state.upper():
                        continue

                    rankings.append(rank)

                    # Stop once we hit limit
                    if len(rankings) >= limit:
                        break

            self.logger.info(
                f"Found {len(rankings)} rankings after filtering",
                class_year=class_year,
                filters={"position": position, "state": state}
            )

            return rankings

        except ValueError as e:
            # Class year validation error - re-raise
            raise

        except Exception as e:
            self.logger.error(
                "Failed to fetch 247Sports rankings",
                class_year=class_year,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    def _parse_ranking_from_row(
        self,
        row: dict,
        class_year: int,
        data_source
    ) -> Optional[RecruitingRank]:
        """
        Parse recruiting rank from 247Sports table row.

        247Sports ranking table typically includes:
        - Rank, Player Name, Position, Height, Weight
        - School, City, State
        - Rating (0.xxxx), Stars (5★ to 3★)
        - Commitment (college if committed)

        Args:
            row: Dictionary of column_name -> value from rankings table
            class_year: Graduation year
            data_source: DataSource metadata object

        Returns:
            RecruitingRank object or None if parsing fails

        Example row:
            {
                "Rank": "1",
                "Name": "John Doe",
                "Pos": "PG",
                "Ht": "6-2",
                "Wt": "180",
                "School": "Lincoln HS",
                "City": "Portland",
                "State": "OR",
                "Rating": "0.9985",
                "Stars": "5",
                "College": "Duke"
            }
        """
        try:
            # Extract player name
            player_name = (
                row.get("Name") or
                row.get("Player") or
                row.get("PLAYER") or
                row.get("Athlete")
            )

            if not player_name:
                return None

            player_name = player_name.strip()

            # Extract national rank
            rank_str = row.get("Rank") or row.get("RANK") or row.get("#")
            rank_national = parse_int(rank_str)

            # Extract position
            position_str = (
                row.get("Pos") or
                row.get("Position") or
                row.get("POS")
            )

            position = None
            if position_str:
                position = self.POSITION_MAP.get(position_str.upper().strip())

            # Extract height (format: "6-2" or "6'2\"")
            height_str = row.get("Ht") or row.get("Height") or row.get("HT")
            height = None
            if height_str:
                # Clean and format: "6-2" -> "6-2"
                height = height_str.replace("'", "-").replace('"', "").strip()

            # Extract weight
            weight_str = row.get("Wt") or row.get("Weight") or row.get("WT")
            weight = parse_int(weight_str)

            # Extract school info
            school = (
                row.get("School") or
                row.get("SCHOOL") or
                row.get("High School")
            )

            city = row.get("City") or row.get("CITY")
            state = row.get("State") or row.get("ST") or row.get("STATE")

            # Extract rating and stars
            rating_str = row.get("Rating") or row.get("RATING") or row.get("Score")
            rating = parse_float(rating_str)

            stars_str = row.get("Stars") or row.get("STARS") or row.get("★")
            stars = parse_int(stars_str)

            # Extract commitment
            committed_to = (
                row.get("College") or
                row.get("Commitment") or
                row.get("Committed To")
            )

            # Build player ID (try to extract 247 ID from profile URL if available)
            player_id = self._build_player_id(player_name)

            # Create RecruitingRank object
            return RecruitingRank(
                player_id=player_id,
                player_name=player_name,
                rank_national=rank_national,
                rank_position=None,  # Not in main table, would need separate fetch
                rank_state=None,  # Not in main table, would need separate fetch
                stars=stars,
                rating=rating,
                service=RecruitingService.COMPOSITE,  # Using composite rankings
                class_year=class_year,
                position=position,
                height=height,
                weight=weight,
                school=school,
                city=city,
                state=state,
                committed_to=committed_to if committed_to and committed_to != "N/A" else None,
                commitment_date=None,  # Not in table, would need player profile
                profile_url=None,  # Would need to construct from player ID
                data_source=data_source,
            )

        except Exception as e:
            self.logger.warning(
                "Failed to parse ranking from 247Sports row",
                error=str(e),
                row_keys=list(row.keys()) if row else None
            )
            return None

    async def get_player_recruiting_profile(
        self,
        player_id: str
    ) -> Optional[RecruitingProfile]:
        """
        Get comprehensive recruiting profile for a player.

        **NOT YET IMPLEMENTED** - Placeholder for future development.

        Would require:
        1. Building player profile URL from player_id
        2. Fetching player profile page
        3. Parsing rankings section
        4. Parsing offers section
        5. Parsing Crystal Ball predictions

        Args:
            player_id: 247Sports player identifier

        Returns:
            RecruitingProfile or None

        TODO: Implement player profile page scraping
        """
        self.logger.warning(
            "get_player_recruiting_profile not yet implemented for 247Sports",
            player_id=player_id
        )
        return None

    async def search_players(
        self,
        name: Optional[str] = None,
        class_year: Optional[int] = None,
        state: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 50,
    ) -> List[RecruitingRank]:
        """
        Search for players in 247Sports rankings.

        **IMPLEMENTATION**: Uses get_rankings() with filters.

        Args:
            name: Player name (partial match)
            class_year: Graduation year filter
            state: State filter
            position: Position filter
            limit: Maximum results

        Returns:
            List of RecruitingRank objects

        Example:
            >>> results = await sports247.search_players(
            ...     name="Smith",
            ...     class_year=2025,
            ...     limit=10
            ... )
        """
        try:
            # Default to current + next year if not specified
            if not class_year:
                current_year = datetime.now().year
                class_year = current_year + 1  # Default to next graduating class

            # Get rankings with filters
            rankings = await self.get_rankings(
                class_year=class_year,
                limit=limit * 3,  # Fetch more to allow for name filtering
                position=position,
                state=state
            )

            # Filter by name if provided
            if name:
                name_lower = name.lower()
                rankings = [
                    r for r in rankings
                    if name_lower in r.player_name.lower()
                ]

            return rankings[:limit]

        except Exception as e:
            self.logger.error(
                "Failed to search 247Sports players",
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def close(self):
        """
        Close connections and browser instances.

        Cleanup method called when adapter is no longer needed.
        """
        await super().close()
        # BrowserClient is singleton, managed globally
        # No explicit cleanup needed here
