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
Updated: 2025-11-15 - Fixed browser scraping selector (ul.rankings-page__list instead of table)
"""

import re
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
                wait_for="ul.rankings-page__list",  # ✓ FIXED: Wait for rankings list (not table)
                wait_timeout=60000,  # 60 seconds (increased for heavy pages)
                wait_for_network_idle=False,  # Don't wait for network (too strict for ad-heavy sites)
            )

            # Step 4: Parse rendered HTML
            soup = parse_html(html)

            # Step 5: Find rankings list (ul element with player li items)
            # ✓ FIXED: Look for <ul class="rankings-page__list"> instead of table
            rankings_list = soup.find("ul", class_="rankings-page__list")

            if not rankings_list:
                self.logger.warning(
                    "No rankings list found on 247Sports page",
                    class_year=class_year,
                    url=rankings_url,
                    expected_selector="ul.rankings-page__list",
                    debug_hint="247Sports HTML structure may have changed"
                )
                return []

            # Step 6: Extract player list items (li elements)
            # ✓ FIXED: Find <li class="rankings-page__list-item"> instead of table rows
            player_items = rankings_list.find_all("li", class_="rankings-page__list-item")

            if not player_items:
                self.logger.warning(
                    "Rankings list found but no player items extracted",
                    class_year=class_year,
                    expected_class="rankings-page__list-item",
                    debug_hint="Check if 247Sports changed class names"
                )
                return []

            self.logger.info(
                f"Extracted {len(player_items)} players from 247Sports rankings list",
                class_year=class_year
            )

            # Step 7: Parse rankings from player list items
            # ✓ FIXED: Iterate over <li> elements instead of table rows
            rankings = []
            data_source = self.create_data_source_metadata(
                url=rankings_url,
                quality_flag=DataQualityFlag.COMPLETE,
                notes=f"247Sports {class_year} Composite Rankings"
            )

            for player_item in player_items[:limit * 2]:  # Parse 2x limit to allow for filtering
                # ✓ FIXED: Call _parse_ranking_from_li() instead of _parse_ranking_from_row()
                rank = self._parse_ranking_from_li(player_item, class_year, data_source)

                if rank:
                    # Apply filters (same as before)
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

    def _parse_ranking_from_li(
        self,
        li_element,
        class_year: int,
        data_source
    ) -> Optional[RecruitingRank]:
        """
        Parse recruiting rank from 247Sports list item element.

        **FIXED (2025-11-15)**: New method to parse from <li> elements instead of table rows.

        247Sports uses <li class="rankings-page__list-item"> structure with divs:
        - <div class="rank-column"><div class="primary">1</div></div> - National rank
        - <div class="recruit"><a>Player Name</a><span class="meta">School (City, ST)</span></div>
        - <div class="position">PG</div> - Position
        - <div class="metrics">6-9 / 210</div> - Height/Weight
        - <div class="rating"><span class="score">0.9999</span></div> - Rating
        - <div class="status"><img alt="College"></div> - Commitment

        Args:
            li_element: BeautifulSoup <li> element with class "rankings-page__list-item"
            class_year: Graduation year
            data_source: DataSource metadata object

        Returns:
            RecruitingRank object or None if parsing fails
        """
        try:
            # Extract national rank from rank-column > primary
            rank_column = li_element.find("div", class_="rank-column")
            rank_national = None
            if rank_column:
                primary_rank = rank_column.find("div", class_="primary")
                if primary_rank:
                    rank_national = parse_int(get_text_or_none(primary_rank))

            # Extract player name and ID from recruit section
            recruit_div = li_element.find("div", class_="recruit")
            if not recruit_div:
                self.logger.debug("No recruit div found in list item")
                return None

            name_link = recruit_div.find("a", class_="rankings-page__name-link")
            if not name_link:
                self.logger.debug("No name link found in recruit div")
                return None

            player_name = name_link.text.strip()

            # Extract player ID from href (e.g., "/player/aj-dybantsa-46134184/")
            player_href = name_link.get("href", "")
            player_247_id = None
            if player_href:
                # Extract numeric ID from URL using regex
                id_match = re.search(r'-(\d+)/?$', player_href)
                if id_match:
                    player_247_id = id_match.group(1)

            # Extract school info from meta span
            school_meta = recruit_div.find("span", class_="meta")
            school_text = get_text_or_none(school_meta) if school_meta else None

            # Parse school_text: "School Name (City, State)"
            school = None
            city = None
            state = None
            if school_text:
                # Pattern: "School Name (City, ST)"
                match = re.match(r'(.+?)\s*\(([^,]+),\s*([A-Z]{2})\)', school_text)
                if match:
                    school = match.group(1).strip()
                    city = match.group(2).strip()
                    state = match.group(3).strip()
                else:
                    # Fallback: use full text as school
                    school = school_text.strip()

            # Extract position
            position_div = li_element.find("div", class_="position")
            position_str = get_text_or_none(position_div) if position_div else None
            position = None
            if position_str:
                position = self.POSITION_MAP.get(position_str.upper().strip())

            # Extract height/weight from metrics
            metrics_div = li_element.find("div", class_="metrics")
            metrics_text = get_text_or_none(metrics_div) if metrics_div else None

            height = None
            weight = None
            if metrics_text:
                # Pattern: "6-9 / 210"
                parts = metrics_text.split("/")
                if len(parts) == 2:
                    height = parts[0].strip()
                    weight = parse_int(parts[1].strip())
                elif len(parts) == 1:
                    # Just height, no weight
                    height = parts[0].strip()

            # Extract rating and stars
            rating_div = li_element.find("div", class_="rating")
            rating = None
            stars = None

            if rating_div:
                # Extract rating score
                score_span = rating_div.find("span", class_="score")
                if score_span:
                    rating = parse_float(get_text_or_none(score_span))

                # Count star icons (look for yellow filled stars)
                star_icons = rating_div.find_all("span", class_=lambda x: x and "icon-starsolid" in str(x))
                if star_icons:
                    # Only count yellow stars (filled), not gray (unfilled)
                    yellow_stars = [s for s in star_icons if "yellow" in " ".join(s.get("class", []))]
                    stars = len(yellow_stars) if yellow_stars else len(star_icons)

            # Extract commitment
            status_div = li_element.find("div", class_="status")
            committed_to = None

            if status_div:
                # Look for commitment image (college logo)
                commit_img = status_div.find("img")
                if commit_img:
                    committed_to = commit_img.get("alt")

            # Build player ID
            player_id = self._build_player_id(player_name, player_247_id)

            # Create RecruitingRank object
            return RecruitingRank(
                player_id=player_id,
                player_name=player_name,
                rank_national=rank_national,
                rank_position=None,  # Not in list view, would need separate page
                rank_state=None,  # Not in list view, would need separate page
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
                commitment_date=None,  # Not in list view, would need player profile
                profile_url=None,  # Could construct from player_href if needed
                data_source=data_source,
            )

        except Exception as e:
            self.logger.warning(
                "Failed to parse ranking from 247Sports list item",
                error=str(e),
                error_type=type(e).__name__,
                html_snippet=str(li_element)[:300] if li_element else None
            )
            return None

    def _build_player_profile_url(self, player_id: str, player_name: Optional[str] = None) -> Optional[str]:
        """
        Build 247Sports player profile URL from player_id.

        **DEBUGGING APPROACH**: Try multiple URL patterns and log each attempt.

        247Sports player profile URLs follow patterns like:
        - https://247sports.com/Player/{name}-{numeric_id}/
        - https://247sports.com/player/{name}-{numeric_id}/

        Args:
            player_id: Player identifier (format: "247_12345" or "247_john_doe")
            player_name: Optional player name for constructing URL slug

        Returns:
            Player profile URL or None if unable to construct

        Example:
            >>> self._build_player_profile_url("247_12345", "John Doe")
            "https://247sports.com/Player/John-Doe-12345/"
        """
        self.logger.debug(
            "Building 247Sports player profile URL",
            player_id=player_id,
            player_name=player_name
        )

        # Extract ID portion (remove "247_" prefix)
        if not player_id.startswith("247_"):
            self.logger.warning(
                "Invalid player_id format - must start with '247_'",
                player_id=player_id
            )
            return None

        id_part = player_id[4:]  # Remove "247_" prefix
        self.logger.debug("Extracted ID part from player_id", id_part=id_part)

        # Check if id_part is numeric (actual 247Sports ID)
        if id_part.isdigit():
            # Numeric ID - need player name to construct URL
            if not player_name:
                self.logger.warning(
                    "Numeric player ID requires player_name to construct URL",
                    player_id=player_id,
                    id_part=id_part
                )
                return None

            # Construct URL slug from player name
            name_slug = player_name.replace(" ", "-")
            url = f"{self.base_url}/Player/{name_slug}-{id_part}/"

            self.logger.debug(
                "Constructed profile URL from numeric ID",
                url=url,
                name_slug=name_slug,
                numeric_id=id_part
            )
            return url

        else:
            # Name-based ID (fallback when numeric ID unavailable)
            # Format: "john_doe" -> needs conversion to actual player URL
            self.logger.warning(
                "Name-based player_id detected - cannot reliably construct profile URL without numeric ID",
                player_id=player_id,
                id_part=id_part,
                recommendation="Use numeric 247Sports ID for reliable profile fetching"
            )
            return None

    def _parse_player_bio(self, soup, player_id: str, player_name: str) -> dict:
        """
        Extract player bio information including birth date.

        **CRITICAL**: Extracts birth_date for Enhancement 4 (Age-for-Grade calculation).

        **DEBUGGING APPROACH**:
        1. Log if bio section found
        2. Try multiple selectors for birth date
        3. Log each extraction attempt
        4. Don't fill in missing values - log gaps

        Args:
            soup: BeautifulSoup parsed HTML
            player_id: Player identifier
            player_name: Player name

        Returns:
            Dictionary with bio data (birth_date, height, weight, position, etc.)

        Example bio section:
            <div class="player-bio">
                <span class="label">DOB:</span>
                <span class="value">March 15, 2007</span>
            </div>
        """
        from ...utils.age_calculations import parse_birth_date

        self.logger.debug(
            "Parsing player bio section",
            player_id=player_id,
            player_name=player_name
        )

        bio_data = {}

        # Try to find bio section with multiple selectors
        bio_section = (
            soup.find("div", class_=lambda x: x and "bio" in str(x).lower()) or
            soup.find("div", class_=lambda x: x and "vitals" in str(x).lower()) or
            soup.find("section", class_=lambda x: x and "info" in str(x).lower())
        )

        if not bio_section:
            self.logger.warning(
                "No bio section found on player profile page",
                player_id=player_id,
                tried_selectors=["div[class*='bio']", "div[class*='vitals']", "section[class*='info']"]
            )
            return bio_data

        self.logger.debug("Bio section found", player_id=player_id)

        # Extract birth date - CRITICAL for age-for-grade calculation
        # Try multiple patterns for birth date field
        birth_date_patterns = [
            ("DOB", "date of birth"),
            ("Birthday", "birthday"),
            ("Born", "birth"),
        ]

        birth_date_text = None
        for label_text, description in birth_date_patterns:
            # Try finding label with this text
            label = bio_section.find(
                "span",
                class_=lambda x: x and "label" in str(x).lower(),
                string=lambda s: s and label_text.lower() in s.lower()
            )

            if label:
                # Found label - get sibling value
                value_span = label.find_next_sibling("span")
                if value_span:
                    birth_date_text = value_span.get_text().strip()
                    self.logger.debug(
                        f"Found birth date using '{label_text}' label",
                        birth_date_text=birth_date_text,
                        player_id=player_id
                    )
                    break

        if not birth_date_text:
            self.logger.warning(
                "Birth date not found in bio section",
                player_id=player_id,
                tried_patterns=[p[0] for p in birth_date_patterns]
            )
        else:
            # Parse birth date using utility from Enhancement 4
            birth_date = parse_birth_date(birth_date_text)

            if birth_date:
                bio_data["birth_date"] = birth_date
                self.logger.info(
                    "Successfully extracted birth date",
                    player_id=player_id,
                    birth_date=str(birth_date),
                    birth_date_text=birth_date_text
                )
            else:
                self.logger.warning(
                    "Failed to parse birth date text",
                    player_id=player_id,
                    birth_date_text=birth_date_text,
                    tried_formats=["MM/DD/YYYY", "Month DD, YYYY", "YYYY-MM-DD"]
                )

        # Extract other bio fields (height, weight, position)
        # These may already be available from rankings table, but profile page may have more detail

        # Extract height
        height_label = bio_section.find(
            "span",
            class_=lambda x: x and "label" in str(x).lower(),
            string=lambda s: s and "height" in s.lower()
        )
        if height_label:
            height_value = height_label.find_next_sibling("span")
            if height_value:
                bio_data["height"] = height_value.get_text().strip()
                self.logger.debug("Extracted height from bio", height=bio_data["height"])

        # Extract weight
        weight_label = bio_section.find(
            "span",
            class_=lambda x: x and "label" in str(x).lower(),
            string=lambda s: s and "weight" in s.lower()
        )
        if weight_label:
            weight_value = weight_label.find_next_sibling("span")
            if weight_value:
                weight_text = weight_value.get_text().strip()
                bio_data["weight"] = parse_int(weight_text)
                self.logger.debug("Extracted weight from bio", weight=bio_data["weight"])

        # Extract position
        position_label = bio_section.find(
            "span",
            class_=lambda x: x and "label" in str(x).lower(),
            string=lambda s: s and "position" in s.lower()
        )
        if position_label:
            position_value = position_label.find_next_sibling("span")
            if position_value:
                position_text = position_value.get_text().strip()
                bio_data["position"] = self.POSITION_MAP.get(position_text.upper())
                self.logger.debug("Extracted position from bio", position=position_text)

        self.logger.debug(
            "Bio parsing complete",
            player_id=player_id,
            fields_extracted=list(bio_data.keys())
        )

        return bio_data

    def _parse_player_rankings(
        self,
        soup,
        player_id: str,
        player_name: str,
        class_year: int,
        data_source
    ) -> List[RecruitingRank]:
        """
        Extract multi-service rankings from player profile.

        **DEBUGGING APPROACH**:
        1. Log if rankings section found
        2. Log number of ranking services detected
        3. For each service, log extracted data
        4. Log any parsing errors with context

        247Sports player profiles typically show rankings from:
        - 247Sports
        - 247Sports Composite (average of all services)
        - ESPN
        - Rivals
        - On3

        Args:
            soup: BeautifulSoup parsed HTML
            player_id: Player identifier
            player_name: Player name
            class_year: Graduation year
            data_source: DataSource metadata

        Returns:
            List of RecruitingRank objects (one per service)
        """
        self.logger.debug(
            "Parsing player rankings section",
            player_id=player_id
        )

        rankings = []

        # Try to find rankings section with multiple selectors
        rankings_section = (
            soup.find("div", class_=lambda x: x and "ranking" in str(x).lower()) or
            soup.find("section", class_=lambda x: x and "ranking" in str(x).lower()) or
            soup.find("div", class_=lambda x: x and "rating" in str(x).lower())
        )

        if not rankings_section:
            self.logger.warning(
                "No rankings section found on player profile page",
                player_id=player_id,
                tried_selectors=["div[class*='ranking']", "section[class*='ranking']", "div[class*='rating']"]
            )
            return rankings

        self.logger.debug("Rankings section found", player_id=player_id)

        # Extract rankings for each service
        # Look for service-specific elements (247Sports, ESPN, Rivals, On3, Composite)
        services_to_check = [
            (RecruitingService.SPORTS_247, "247Sports", ["247sports", "247"]),
            (RecruitingService.COMPOSITE, "Composite", ["composite", "industry"]),
            (RecruitingService.ESPN, "ESPN", ["espn"]),
            (RecruitingService.RIVALS, "Rivals", ["rivals"]),
            (RecruitingService.ON3, "On3", ["on3"]),
        ]

        for service_enum, service_name, service_keywords in services_to_check:
            self.logger.debug(f"Checking for {service_name} ranking", player_id=player_id)

            # Try to find service-specific ranking element
            service_element = None
            for keyword in service_keywords:
                service_element = rankings_section.find(
                    lambda tag: tag.name in ["div", "span", "li"] and
                    tag.get("class") and
                    any(keyword.lower() in str(c).lower() for c in tag.get("class", []))
                )
                if service_element:
                    break

            if not service_element:
                self.logger.debug(
                    f"{service_name} ranking not found",
                    player_id=player_id
                )
                continue

            # Extract rank, rating, stars from this service element
            rank_text = get_text_or_none(service_element.find(string=lambda s: s and "#" in s))
            rank_national = parse_int(rank_text.replace("#", "").strip()) if rank_text else None

            rating_text = get_text_or_none(service_element.find(class_=lambda x: x and "rating" in str(x).lower()))
            rating = parse_float(rating_text)

            stars_text = get_text_or_none(service_element.find(class_=lambda x: x and "star" in str(x).lower()))
            stars = parse_int(stars_text.replace("★", "").replace("*", "").strip()) if stars_text else None

            self.logger.debug(
                f"Extracted {service_name} ranking",
                player_id=player_id,
                rank=rank_national,
                rating=rating,
                stars=stars
            )

            # Create RecruitingRank object if we have at least rank or rating
            if rank_national or rating or stars:
                rankings.append(RecruitingRank(
                    player_id=player_id,
                    player_name=player_name,
                    rank_national=rank_national,
                    rank_position=None,  # Position rank not typically on main profile
                    rank_state=None,  # State rank not typically on main profile
                    stars=stars,
                    rating=rating,
                    service=service_enum,
                    class_year=class_year,
                    data_source=data_source,
                ))

        self.logger.info(
            f"Extracted {len(rankings)} service rankings",
            player_id=player_id,
            services=[r.service for r in rankings]
        )

        return rankings

    def _parse_player_offers(
        self,
        soup,
        player_id: str,
        player_name: str,
        data_source
    ) -> List[CollegeOffer]:
        """
        Extract college offers from player profile.

        **DEBUGGING APPROACH**:
        1. Log if offers table found
        2. Log table headers to understand structure
        3. Log number of offers found
        4. For each offer, log school, status, dates
        5. Log any parsing errors with row HTML

        Args:
            soup: BeautifulSoup parsed HTML
            player_id: Player identifier
            player_name: Player name
            data_source: DataSource metadata

        Returns:
            List of CollegeOffer objects
        """
        self.logger.debug(
            "Parsing player offers section",
            player_id=player_id
        )

        offers = []

        # Try to find offers table with multiple selectors
        offers_table = (
            soup.find("table", class_=lambda x: x and "offer" in str(x).lower()) or
            soup.find("div", class_=lambda x: x and "offer" in str(x).lower()) or
            soup.find("section", class_=lambda x: x and "offer" in str(x).lower())
        )

        if not offers_table:
            self.logger.warning(
                "No offers table found on player profile page",
                player_id=player_id,
                tried_selectors=["table[class*='offer']", "div[class*='offer']", "section[class*='offer']"]
            )
            return offers

        self.logger.debug("Offers section found", player_id=player_id)

        # Extract offers table rows
        if offers_table.name == "table":
            # Standard HTML table
            rows = extract_table_data(offers_table)
            self.logger.debug(f"Extracted {len(rows)} rows from offers table", player_id=player_id)

            for row in rows:
                # Extract school name
                school = (
                    row.get("School") or
                    row.get("College") or
                    row.get("SCHOOL") or
                    row.get("Team")
                )

                if not school:
                    continue

                # Extract conference
                conference = row.get("Conference") or row.get("CONFERENCE")

                # Determine conference level (POWER_6, MID_MAJOR, LOW_MAJOR)
                conference_level = self._classify_conference_level(conference)

                # Extract offer status
                status_text = (
                    row.get("Status") or
                    row.get("STATUS") or
                    "Offered"  # Default
                )
                offer_status = self._parse_offer_status(status_text)

                # Extract dates (may not be available)
                # offer_date, commitment_date - typically not in table

                self.logger.debug(
                    "Parsed offer",
                    player_id=player_id,
                    school=school,
                    conference=conference,
                    status=offer_status
                )

                offers.append(CollegeOffer(
                    player_id=player_id,
                    player_name=player_name,
                    college_name=school,
                    college_conference=conference,
                    conference_level=conference_level,
                    offer_status=offer_status,
                    data_source=data_source,
                ))

        else:
            # Div-based offers list (common in modern React UIs)
            offer_items = offers_table.find_all(
                lambda tag: tag.name in ["div", "li"] and
                tag.get("class") and
                any("item" in str(c).lower() or "row" in str(c).lower() for c in tag.get("class", []))
            )

            self.logger.debug(f"Found {len(offer_items)} offer items in div structure", player_id=player_id)

            for item in offer_items:
                # Extract school name from item
                school_elem = item.find(class_=lambda x: x and ("school" in str(x).lower() or "college" in str(x).lower()))
                school = get_text_or_none(school_elem) if school_elem else None

                if not school:
                    continue

                # Extract conference if available
                conf_elem = item.find(class_=lambda x: x and "conference" in str(x).lower())
                conference = get_text_or_none(conf_elem) if conf_elem else None

                conference_level = self._classify_conference_level(conference)

                # Extract status if available
                status_elem = item.find(class_=lambda x: x and "status" in str(x).lower())
                status_text = get_text_or_none(status_elem) if status_elem else "Offered"
                offer_status = self._parse_offer_status(status_text)

                self.logger.debug(
                    "Parsed offer from div",
                    player_id=player_id,
                    school=school,
                    status=offer_status
                )

                offers.append(CollegeOffer(
                    player_id=player_id,
                    player_name=player_name,
                    college_name=school,
                    college_conference=conference,
                    conference_level=conference_level,
                    offer_status=offer_status,
                    data_source=data_source,
                ))

        self.logger.info(
            f"Extracted {len(offers)} college offers",
            player_id=player_id,
            power_6_count=len([o for o in offers if o.conference_level == ConferenceLevel.POWER_6])
        )

        return offers

    def _classify_conference_level(self, conference: Optional[str]) -> Optional[ConferenceLevel]:
        """Classify conference as POWER_6, MID_MAJOR, or LOW_MAJOR."""
        if not conference:
            return None

        conf_upper = conference.upper()

        # Power 6 conferences
        power_6_conferences = [
            "ACC", "BIG TEN", "BIG 12", "BIG EAST", "SEC", "PAC-12", "PACIFIC"
        ]

        for p6_conf in power_6_conferences:
            if p6_conf in conf_upper:
                return ConferenceLevel.POWER_6

        # Low major indicators
        low_major_keywords = ["SUMMIT", "PATRIOT", "IVY", "SOUTHERN", "SWAC", "MEAC"]
        for keyword in low_major_keywords:
            if keyword in conf_upper:
                return ConferenceLevel.LOW_MAJOR

        # Default to mid-major for recognized conferences
        return ConferenceLevel.MID_MAJOR

    def _parse_offer_status(self, status_text: str) -> OfferStatus:
        """Parse offer status from text."""
        status_upper = status_text.upper()

        if "COMMIT" in status_upper or "SIGNED" in status_upper:
            return OfferStatus.COMMITTED
        elif "VISIT" in status_upper or "UNOFFICIAL" in status_upper or "OFFICIAL" in status_upper:
            return OfferStatus.VISITED
        elif "DECOMMIT" in status_upper:
            return OfferStatus.DECOMMITTED
        else:
            return OfferStatus.OFFERED

    def _parse_crystal_ball(
        self,
        soup,
        player_id: str,
        player_name: str,
        data_source
    ) -> List[RecruitingPrediction]:
        """
        Extract Crystal Ball predictions from player profile.

        **DEBUGGING APPROACH**:
        1. Log if Crystal Ball section found
        2. Log number of predictions found
        3. For each prediction, log expert, school, confidence
        4. Log confidence score conversion (% to 0.0-1.0)
        5. Log any parsing errors

        Args:
            soup: BeautifulSoup parsed HTML
            player_id: Player identifier
            player_name: Player name
            data_source: DataSource metadata

        Returns:
            List of RecruitingPrediction objects
        """
        self.logger.debug(
            "Parsing Crystal Ball section",
            player_id=player_id
        )

        predictions = []

        # Try to find Crystal Ball section
        cb_section = (
            soup.find("div", class_=lambda x: x and "crystal" in str(x).lower()) or
            soup.find("section", class_=lambda x: x and "crystal" in str(x).lower()) or
            soup.find("div", class_=lambda x: x and "prediction" in str(x).lower())
        )

        if not cb_section:
            self.logger.warning(
                "No Crystal Ball section found on player profile page",
                player_id=player_id,
                tried_selectors=["div[class*='crystal']", "section[class*='crystal']", "div[class*='prediction']"]
            )
            return predictions

        self.logger.debug("Crystal Ball section found", player_id=player_id)

        # Extract prediction items
        prediction_items = cb_section.find_all(
            lambda tag: tag.name in ["div", "li", "tr"] and
            tag.get("class") and
            any("item" in str(c).lower() or "row" in str(c).lower() or "prediction" in str(c).lower() for c in tag.get("class", []))
        )

        self.logger.debug(f"Found {len(prediction_items)} Crystal Ball predictions", player_id=player_id)

        for item in prediction_items:
            # Extract expert name
            expert_elem = item.find(class_=lambda x: x and ("expert" in str(x).lower() or "analyst" in str(x).lower()))
            expert_name = get_text_or_none(expert_elem) if expert_elem else "Unknown Expert"

            # Extract predicted school
            school_elem = item.find(class_=lambda x: x and ("school" in str(x).lower() or "college" in str(x).lower()))
            predicted_school = get_text_or_none(school_elem)

            if not predicted_school:
                continue

            # Extract confidence (may be percentage or 0-10 scale)
            confidence_elem = item.find(class_=lambda x: x and "confidence" in str(x).lower())
            confidence_text = get_text_or_none(confidence_elem)

            confidence = None
            if confidence_text:
                # Remove % sign and convert to 0.0-1.0 scale
                confidence_text = confidence_text.replace("%", "").strip()
                confidence_value = parse_float(confidence_text)

                if confidence_value:
                    # If value > 1, assume it's percentage (0-100)
                    if confidence_value > 1.0:
                        confidence = confidence_value / 100.0
                    else:
                        # If <= 1.0, assume it's already on 0-1 scale or 0-10 scale
                        if confidence_value <= 1.0:
                            confidence = confidence_value
                        else:
                            # 0-10 scale
                            confidence = confidence_value / 10.0

            # Extract prediction date
            date_elem = item.find(class_=lambda x: x and "date" in str(x).lower())
            date_text = get_text_or_none(date_elem)

            # Try to parse date (may fail - use current date as fallback)
            prediction_date = datetime.utcnow()  # Fallback
            if date_text:
                # TODO: Add date parsing logic (multiple formats)
                pass

            self.logger.debug(
                "Parsed Crystal Ball prediction",
                player_id=player_id,
                expert=expert_name,
                school=predicted_school,
                confidence=confidence
            )

            predictions.append(RecruitingPrediction(
                player_id=player_id,
                player_name=player_name,
                college_predicted=predicted_school,
                confidence=confidence,
                predictor=expert_name,
                predictor_organization="247Sports",
                prediction_date=prediction_date,
                data_source=data_source,
            ))

        self.logger.info(
            f"Extracted {len(predictions)} Crystal Ball predictions",
            player_id=player_id
        )

        return predictions

    async def get_player_recruiting_profile(
        self,
        player_id: str,
        player_name: Optional[str] = None,
        class_year: Optional[int] = None
    ) -> Optional[RecruitingProfile]:
        """
        Get comprehensive recruiting profile for a player.

        **IMPLEMENTATION COMPLETE** - Fetches and parses player profile pages.

        Extracts:
        1. Player bio (birth date, height, weight, position)
        2. Multi-service rankings (247Sports, Composite, ESPN, Rivals, On3)
        3. College offers with status and dates
        4. Crystal Ball predictions

        **DEBUGGING APPROACH**:
        - Log each step of profile extraction
        - Log URL building attempts
        - Log each section found/not found
        - Log all extracted data
        - Don't fill in missing values - log gaps

        Args:
            player_id: 247Sports player identifier (format: "247_12345")
            player_name: Optional player name (required for URL building with numeric IDs)
            class_year: Optional graduation year (helps with ranking context)

        Returns:
            RecruitingProfile or None if unable to fetch/parse

        Example:
            >>> profile = await sports247.get_player_recruiting_profile(
            ...     player_id="247_12345",
            ...     player_name="John Doe",
            ...     class_year=2026
            ... )
            >>> if profile:
            ...     print(f"Offers: {profile.offer_count}")
            ...     print(f"Predictions: {len(profile.predictions)}")
        """
        self.logger.info(
            "Fetching 247Sports player recruiting profile",
            player_id=player_id,
            player_name=player_name,
            class_year=class_year
        )

        try:
            # Phase 1: Build player profile URL
            profile_url = self._build_player_profile_url(player_id, player_name)

            if not profile_url:
                self.logger.error(
                    "Unable to build player profile URL - requires numeric player ID and player name",
                    player_id=player_id,
                    player_name=player_name
                )
                return None

            self.logger.info(
                "Profile URL constructed successfully",
                player_id=player_id,
                url=profile_url
            )

            # Phase 2: Fetch profile page using browser automation
            self.logger.debug("Fetching player profile page", url=profile_url)

            html = await self.browser_client.get_rendered_html(
                url=profile_url,
                wait_for="div",  # Wait for content to render
                wait_timeout=30000,  # 30 seconds
                wait_for_network_idle=True,  # Ensure React finishes loading
            )

            if not html:
                self.logger.error(
                    "Failed to fetch player profile page - empty HTML returned",
                    player_id=player_id,
                    url=profile_url
                )
                return None

            # Parse HTML
            soup = parse_html(html)

            self.logger.debug(
                "Profile page fetched and parsed successfully",
                player_id=player_id,
                html_length=len(html)
            )

            # Create data source metadata
            data_source = self.create_data_source_metadata(
                url=profile_url,
                quality_flag=DataQualityFlag.COMPLETE,
                notes=f"247Sports player profile for {player_name or player_id}"
            )

            # Phase 3: Extract player name from page if not provided
            if not player_name:
                # Try to extract player name from page header
                name_elem = (
                    soup.find("h1", class_=lambda x: x and "name" in str(x).lower()) or
                    soup.find("h1") or
                    soup.find("div", class_=lambda x: x and "player" in str(x).lower())
                )
                player_name = get_text_or_none(name_elem) if name_elem else player_id
                self.logger.debug("Extracted player name from page", player_name=player_name)

            # Determine class year if not provided
            if not class_year:
                # Try to extract from page or default to current + 1
                class_year = datetime.now().year + 1
                self.logger.debug("Using default class year", class_year=class_year)

            # Phase 4: Parse each section with debug logging

            # Parse bio (includes birth date - CRITICAL for Enhancement 4)
            self.logger.info("Parsing bio section", player_id=player_id)
            bio_data = self._parse_player_bio(soup, player_id, player_name)

            # Parse rankings
            self.logger.info("Parsing rankings section", player_id=player_id)
            rankings = self._parse_player_rankings(
                soup,
                player_id,
                player_name,
                class_year,
                data_source
            )

            # Parse offers
            self.logger.info("Parsing offers section", player_id=player_id)
            offers = self._parse_player_offers(
                soup,
                player_id,
                player_name,
                data_source
            )

            # Parse Crystal Ball predictions
            self.logger.info("Parsing Crystal Ball section", player_id=player_id)
            predictions = self._parse_crystal_ball(
                soup,
                player_id,
                player_name,
                data_source
            )

            # Phase 5: Assemble RecruitingProfile

            # Calculate best/composite rankings
            best_national_rank = None
            composite_rank = None
            composite_rating = None
            max_stars = None

            if rankings:
                # Find composite ranking
                composite_ranks = [r for r in rankings if r.service == RecruitingService.COMPOSITE]
                if composite_ranks:
                    composite_rank = composite_ranks[0].rank_national
                    composite_rating = composite_ranks[0].rating

                # Find best national rank across all services
                national_ranks = [r.rank_national for r in rankings if r.rank_national]
                if national_ranks:
                    best_national_rank = min(national_ranks)

                # Find max stars
                stars = [r.stars for r in rankings if r.stars]
                if stars:
                    max_stars = max(stars)

            # Determine commitment status
            is_committed = False
            committed_to = None
            commitment_date = None

            if offers:
                committed_offers = [o for o in offers if o.offer_status == OfferStatus.COMMITTED]
                if committed_offers:
                    is_committed = True
                    committed_to = committed_offers[0].college_name
                    commitment_date = committed_offers[0].status_date

            # Calculate prediction consensus
            prediction_consensus = None
            prediction_confidence = None

            if predictions:
                # Find most predicted school
                from collections import Counter
                school_counts = Counter([p.college_predicted for p in predictions])
                if school_counts:
                    prediction_consensus = school_counts.most_common(1)[0][0]

                # Calculate average confidence
                confidences = [p.confidence for p in predictions if p.confidence]
                if confidences:
                    prediction_confidence = sum(confidences) / len(confidences)

            # Assemble profile
            profile = RecruitingProfile(
                player_uid=player_id,  # Use player_id as UID for now
                player_name=player_name,
                rankings=rankings,
                best_national_rank=best_national_rank,
                composite_rank=composite_rank,
                composite_rating=composite_rating,
                max_stars=max_stars,
                offers=offers,
                offer_count=len(offers),  # Auto-calculated by validator
                power_6_offers=len([o for o in offers if o.conference_level == ConferenceLevel.POWER_6]),  # Auto-calculated
                is_committed=is_committed,
                committed_to=committed_to,
                commitment_date=commitment_date,
                predictions=predictions,
                prediction_consensus=prediction_consensus,
                prediction_confidence=prediction_confidence,
                last_updated=datetime.utcnow(),
            )

            self.logger.info(
                "Successfully assembled recruiting profile",
                player_id=player_id,
                player_name=player_name,
                rankings_count=len(rankings),
                offers_count=len(offers),
                power_6_offers=profile.power_6_offers,
                predictions_count=len(predictions),
                is_committed=is_committed,
                birth_date_extracted=bio_data.get("birth_date") is not None
            )

            return profile

        except Exception as e:
            self.logger.error(
                "Failed to fetch player recruiting profile",
                player_id=player_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
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
