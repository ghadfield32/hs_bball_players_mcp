"""
On3/Rivals Recruiting Data Source

Fetches "Rivals Industry" composite rankings (247 + Rivals + ESPN).

Key Features:
- No anti-bot detection (unlike 247Sports)
- Clean JSON data (no HTML parsing)
- Complete player data: rankings, ratings, stars, physical stats, commitment status

The "Rivals Industry" ranking is an equal-weighted composite of:
- 247Sports rankings (33%)
- Rivals rankings (33%)
- ESPN rankings (33%)

URL Pattern:
    https://www.on3.com/rivals/rankings/industry-player/basketball/{year}/

Data Format:
    On3 uses Next.js with server-side rendered JSON embedded in
    <script id="__NEXT_DATA__"> tag. No HTML parsing needed.

Bot Detection:
    ✅ On3 allows headless browsers (unlike 247Sports)

Author: Claude Code
Date: 2025-11-15
"""

import json
import re
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup

from ...models.player import Position
from ...models.recruiting import RecruitingRank, RecruitingService, RecruitingProfile
from ...models.source import DataSource, DataSourceType, DataSourceRegion
from ...utils.browser_client import BrowserClient
from ...utils.logger import get_logger
from .base_recruiting import BaseRecruitingSource


logger = get_logger(__name__)


class On3DataSource(BaseRecruitingSource):
    """
    Data source for On3/Rivals "Industry" composite rankings.

    The "Rivals Industry" ranking is a composite of:
    - 247Sports rankings (33%)
    - Rivals rankings (33%)
    - ESPN rankings (33%)

    This provides a balanced view across all major recruiting services.

    Data Format:
        On3 uses Next.js with server-side rendered JSON embedded in
        <script id="__NEXT_DATA__"> tag. No HTML parsing needed.

    Bot Detection:
        ✅ On3 allows headless browsers (unlike 247Sports)

    Attributes:
        browser_client: Browser automation client for page rendering
        POSITION_MAP: Maps On3 position abbreviations to Position enum
    """

    # Required class attributes for BaseRecruitingSource
    source_type = DataSourceType.ON3
    source_name = "On3/Rivals"
    base_url = "https://www.on3.com/rivals/rankings/"
    region = DataSourceRegion.US

    # Position mapping (On3 uses standard abbreviations)
    POSITION_MAP = {
        "PG": Position.PG,
        "SG": Position.SG,
        "CG": Position.G,  # Combo guard -> generic guard
        "SF": Position.SF,
        "PF": Position.PF,
        "C": Position.C,
        "F": Position.F,
        "G": Position.G,
    }

    def __init__(self):
        """Initialize On3 data source."""
        super().__init__()
        self.browser_client = BrowserClient()

    @staticmethod
    def _safe_get(obj: dict, path: str, default=None):
        """
        Safely extract nested dictionary value using dot notation.

        Args:
            obj: Dictionary object
            path: Dot-separated path (e.g., "person.rating.consensusRank")
            default: Default value if path not found

        Returns:
            Value at path or default

        Example:
            rating = _safe_get(player_obj, "person.rating.consensusRating", 0.0)
        """
        keys = path.split('.')
        current = obj

        for key in keys:
            if not isinstance(current, dict):
                return default

            current = current.get(key)

            if current is None:
                return default

        return current

    def get_data_source(self) -> DataSource:
        """Return metadata about this data source."""
        return self.create_data_source_metadata(
            url="https://www.on3.com/rivals/rankings/industry-player/basketball/",
            notes="Rivals Industry composite rankings (247 + Rivals + ESPN equally weighted)",
        )

    async def get_rankings(
        self,
        class_year: int,
        limit: int = 100,
        position: Optional[Position] = None,
        state: Optional[str] = None,
    ) -> List[RecruitingRank]:
        """
        Fetch recruiting rankings from On3/Rivals Industry with pagination support.

        Args:
            class_year: Graduation year (e.g., 2025)
            limit: Maximum number of rankings to return
            position: Filter by position (optional)
            state: Filter by state (optional)

        Returns:
            List of recruiting rankings

        Example:
            rankings = await on3.get_rankings(class_year=2025, limit=150)
        """
        self.logger.info(
            "Fetching On3/Rivals Industry rankings",
            class_year=class_year,
            limit=limit,
            position=position,
            state=state,
        )

        data_source = self.get_data_source()
        all_rankings = []
        current_page = 1
        total_count = None
        items_per_page = 50  # On3 default
        page_count = None  # Total pages available

        # Fetch pages until we have enough rankings (accounting for filters)
        # We may need to fetch more pages than limit/50 if filters are applied
        while len(all_rankings) < limit:
            # Step 1: Build paginated URL
            if current_page == 1:
                rankings_url = f"https://www.on3.com/rivals/rankings/industry-player/basketball/{class_year}/"
            else:
                rankings_url = f"https://www.on3.com/rivals/rankings/industry-player/basketball/{class_year}/{current_page}/"

            self.logger.info(
                f"Fetching page {current_page}",
                url=rankings_url
            )

            # Step 2: Fetch rendered HTML
            html = await self.browser_client.get_rendered_html(
                url=rankings_url,
                wait_for="script#__NEXT_DATA__",
                wait_timeout=30000,
            )

            if not html:
                self.logger.warning(f"No HTML returned for page {current_page}")
                break

            # Step 3: Extract Next.js JSON data and pagination info
            page_data = self._parse_next_data_json(html)

            if not page_data:
                self.logger.warning(f"No player data found on page {current_page}")
                break

            # Extract pagination metadata from first page
            if current_page == 1:
                pagination = self._extract_pagination(html)
                if pagination:
                    total_count = pagination.get('count', 0)
                    items_per_page = pagination.get('itemsPerPage', 50)
                    page_count = pagination.get('pageCount', 1)

                    self.logger.info(
                        "Pagination info",
                        total_count=total_count,
                        items_per_page=items_per_page,
                        page_count=page_count
                    )

            self.logger.info(
                f"Extracted {len(page_data)} players from page {current_page}"
            )

            # Step 4: Parse players on this page
            page_rankings = []
            for player_obj in page_data:
                rank = self._parse_player_from_json(player_obj, class_year, data_source)

                if rank:
                    # Apply filters
                    if position and rank.position != position:
                        continue

                    if state and rank.state != state:
                        continue

                    page_rankings.append(rank)

            # Add this page's rankings to total
            all_rankings.extend(page_rankings)

            self.logger.info(
                f"Page {current_page} added {len(page_rankings)} rankings (total: {len(all_rankings)})"
            )

            # Check if we're done
            if len(page_data) < items_per_page:
                # Last page (partial page)
                self.logger.info("Reached last page (partial page)")
                break

            if total_count and len(all_rankings) >= total_count:
                # We've fetched all available data
                self.logger.info("Fetched all available rankings")
                break

            # Check if we've reached the last page according to pagination metadata
            if page_count and current_page >= page_count:
                self.logger.info(f"Reached last page according to pagination metadata (page {page_count})")
                break

            # Move to next page
            current_page += 1

            # Safety check: don't fetch more than 20 pages
            if current_page > 20:
                self.logger.warning("Hit safety limit of 20 pages")
                break

        # Trim to requested limit
        final_rankings = all_rankings[:limit]

        # Count validation: warn if actual count doesn't match expected
        if total_count is not None and len(all_rankings) != total_count:
            expected_count = min(total_count, limit)  # Can't get more than limit
            actual_count = len(all_rankings)

            if actual_count < expected_count:
                self.logger.warning(
                    "Count mismatch: fetched fewer rankings than expected",
                    expected=expected_count,
                    actual=actual_count,
                    difference=expected_count - actual_count,
                    total_count=total_count
                )
            elif filters_applied := (position is not None or state is not None):
                # If filters were applied, it's normal to have fewer results
                self.logger.info(
                    "Filters applied resulted in fewer rankings",
                    total_available=total_count,
                    after_filters=actual_count,
                    filters={"position": position, "state": state}
                )

        self.logger.info(
            f"Successfully fetched {len(final_rankings)} On3 rankings",
            class_year=class_year,
            pages_fetched=current_page,
            total_parsed=len(all_rankings),
            total_available=total_count
        )

        return final_rankings

    def _extract_pagination(self, html: str) -> Optional[dict]:
        """
        Extract pagination metadata from Next.js __NEXT_DATA__ JSON.

        Args:
            html: Page HTML

        Returns:
            Pagination dict with count, offset, limit, currentPage, pageCount
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})

            if not next_data_script or not next_data_script.string:
                return None

            data = json.loads(next_data_script.string)

            pagination = (
                data
                .get('props', {})
                .get('pageProps', {})
                .get('playerData', {})
                .get('pagination', {})
            )

            return pagination if pagination else None

        except Exception as e:
            self.logger.warning(f"Failed to extract pagination: {e}")
            return None

    def _parse_next_data_json(self, html: str) -> Optional[List[dict]]:
        """
        Extract player rankings from Next.js __NEXT_DATA__ JSON.

        On3 embeds data in: <script id="__NEXT_DATA__" type="application/json">
        Data path: props.pageProps.playerData.list[]

        Args:
            html: Page HTML

        Returns:
            List of player objects or None if not found
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find the __NEXT_DATA__ script tag
            next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})

            if not next_data_script or not next_data_script.string:
                self.logger.warning("No __NEXT_DATA__ script found in HTML")
                return None

            # Parse JSON
            data = json.loads(next_data_script.string)

            # Check for 404 page
            page_type = data.get('page', '')
            if page_type == '/404':
                self.logger.warning("Page returned 404 error")
                return None

            # Navigate to player data
            player_list = (
                data
                .get('props', {})
                .get('pageProps', {})
                .get('playerData', {})
                .get('list', [])
            )

            if not player_list:
                self.logger.warning("No player list found in __NEXT_DATA__.props.pageProps.playerData.list")
                return None

            return player_list

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse __NEXT_DATA__ JSON: {e}")
            return None

        except Exception as e:
            self.logger.error(f"Unexpected error parsing __NEXT_DATA__: {e}")
            return None

    def _parse_player_from_json(
        self,
        player_obj: dict,
        class_year: int,
        data_source: DataSource,
    ) -> Optional[RecruitingRank]:
        """
        Parse recruiting rank from On3 player JSON object.

        Args:
            player_obj: Player object from __NEXT_DATA__.props.pageProps.playerData.list[]
            class_year: Expected graduation year
            data_source: DataSource metadata

        Returns:
            RecruitingRank or None if parsing fails
        """
        try:
            # Required fields - use _safe_get for nested access
            player_name = self._safe_get(player_obj, 'person.name')
            if not player_name:
                self.logger.warning("Skipping player: missing name", player_obj_key=player_obj.get('key'))
                return None

            # Player ID (use On3 key)
            on3_key = self._safe_get(player_obj, 'person.key')
            player_id = f"on3_{on3_key}" if on3_key else None

            # Rating data - use _safe_get for robustness
            rank_national = self._safe_get(player_obj, 'person.rating.consensusNationalRank')
            rank_position = self._safe_get(player_obj, 'person.rating.consensusPositionRank')
            rank_state = self._safe_get(player_obj, 'person.rating.consensusStateRank')
            stars = self._safe_get(player_obj, 'person.rating.consensusStars')

            # Normalize rating from 0-100 scale to 0-1 scale
            rating_raw = self._safe_get(player_obj, 'person.rating.consensusRating')
            rating_value = rating_raw / 100.0 if rating_raw is not None else None

            # Position
            position_abbr = self._safe_get(player_obj, 'person.positionAbbreviation', '')
            position = self.POSITION_MAP.get(position_abbr.upper())

            # Physical stats
            height = self._safe_get(player_obj, 'person.formattedHeight')
            weight = self._safe_get(player_obj, 'person.weight')

            # School info
            school = self._safe_get(player_obj, 'person.highSchoolName')

            # Hometown (format: "City, ST")
            hometown = self._safe_get(player_obj, 'person.homeTownName', '')
            city, state = self._parse_hometown(hometown)

            # Commitment status
            is_committed = self._safe_get(player_obj, 'person.status.isCommitted', False)
            committed_to = None
            commitment_date = None

            if is_committed:
                # Use slug (e.g., "byu-cougars")
                committed_to = self._safe_get(player_obj, 'person.status.committedOrganizationSlug')

                # Parse ISO date
                commit_date_str = self._safe_get(player_obj, 'person.status.commitmentDate')
                if commit_date_str:
                    try:
                        commitment_date = datetime.fromisoformat(
                            commit_date_str.replace('Z', '+00:00')
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse commitment date: {commit_date_str}",
                            player=player_name,
                            error=str(e)
                        )

            # Profile URL
            player_slug = self._safe_get(player_obj, 'person.slug')
            profile_url = f"https://www.on3.com/{player_slug}" if player_slug else None

            # Build RecruitingRank
            return RecruitingRank(
                player_id=player_id,
                player_name=player_name,
                rank_national=rank_national,
                rank_position=rank_position,
                rank_state=rank_state,
                stars=stars,
                rating=rating_value,
                service=RecruitingService.INDUSTRY,  # Rivals Industry composite
                class_year=class_year,
                position=position,
                height=height,
                weight=weight,
                school=school,
                city=city,
                state=state,
                committed_to=committed_to,
                commitment_date=commitment_date,
                profile_url=profile_url,
                data_source=data_source,
            )

        except Exception as e:
            self.logger.warning(
                f"Failed to parse On3 player from JSON: {e}",
                player_obj=str(player_obj)[:200],
            )
            return None

    def _parse_hometown(self, hometown: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse hometown string into city and state.

        Format: "Brockton, MA" or "City Name, ST"

        Args:
            hometown: Hometown string

        Returns:
            Tuple of (city, state) or (None, None) if parsing fails
        """
        if not hometown:
            return None, None

        # Pattern: "City, ST"
        match = re.match(r'(.+?),\s*([A-Z]{2})$', hometown.strip())

        if match:
            return match.group(1).strip(), match.group(2).strip()

        # Fallback: treat full string as city
        return hometown.strip(), None

    async def get_player_recruiting_profile(
        self,
        player_id: str
    ) -> Optional[RecruitingProfile]:
        """
        Get comprehensive recruiting profile for a player.

        Args:
            player_id: Player identifier from On3 (e.g., "on3_156943")

        Returns:
            RecruitingProfile with rankings, offers, predictions

        Note: This is a stub implementation. Full profile fetching will be added in Phase 1.3.
        """
        self.logger.warning(
            "get_player_recruiting_profile not yet implemented for On3",
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
        Search for players in On3 recruiting database.

        Args:
            name: Player name (partial match)
            class_year: Graduation year filter
            state: State filter
            position: Position filter
            limit: Maximum results

        Returns:
            List of RecruitingRank objects

        Note: This is a stub implementation. Search will be added in Phase 1.3.
              For now, use get_rankings() with filters.
        """
        self.logger.warning(
            "search_players not yet implemented for On3",
            name=name,
            class_year=class_year,
            state=state,
            position=position
        )

        # Fallback: if class_year provided, use get_rankings
        if class_year:
            self.logger.info(
                "Falling back to get_rankings for search",
                class_year=class_year
            )
            return await self.get_rankings(
                class_year=class_year,
                limit=limit,
                position=position,
                state=state
            )

        return []
