"""
Wisconsin Interscholastic Athletic Association (WIAA) DataSource Adapter

Provides tournament brackets and results for Wisconsin high school basketball.

Base URLs:
- Main site: https://www.wiaawi.org
- Tournament brackets: https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/

Data Coverage:
- Boys and Girls basketball
- Tournament brackets (Regional, Sectional, State)
- Historical data (2015-2025)
- All divisions (D1-D5 typically)

Implementation Phases:
- Phase 1: Enhanced parser with duplicate detection, round parsing, self-game filtering
- Phase 2: URL discovery from navigation links (not pattern-based)
- Phase 3: Girls basketball support
- Phase 4: Historical backfill (2015-2025)
- Phase 5: Validation and diagnostics
- Phase 6: Metadata enhancements (venues, neutral courts, etc.)
- Phase 7: Fixture-based testing mode (avoids HTTP 403s)
"""

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ...models import (
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    Game,
    GameStatus,
    GameType,
    Team,
    TeamLevel,
)
from ...utils import get_text_or_none, parse_html, parse_int
from ..base_association import AssociationAdapterBase


class DataMode(str, Enum):
    """
    Data fetching mode for Wisconsin WIAA adapter.

    LIVE: Fetch bracket data from halftime.wiaawi.org via HTTP (production mode)
    FIXTURE: Load bracket data from local HTML files (testing mode, avoids HTTP 403s)
    """

    LIVE = "live"
    FIXTURE = "fixture"


class WisconsinWiaaDataSource(AssociationAdapterBase):
    """
    Wisconsin Interscholastic Athletic Association data source adapter.

    Parses tournament brackets from halftime.wiaawi.org HTML pages.
    Handles both Boys and Girls basketball across all divisions.
    """

    source_type = DataSourceType.WIAA
    source_name = "Wisconsin WIAA"
    base_url = "https://www.wiaawi.org"
    brackets_url = "https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML"
    region = DataSourceRegion.US_WI

    # Parser configuration
    MIN_SCORE = 0
    MAX_SCORE = 200
    DIVISIONS = ["Div1", "Div2", "Div3", "Div4", "Div5"]
    GENDERS = ["Boys", "Girls"]

    def __init__(
        self,
        data_mode: DataMode = DataMode.LIVE,
        fixtures_dir: Optional[Path] = None
    ):
        """
        Initialize Wisconsin WIAA datasource.

        Args:
            data_mode: Data fetching mode (LIVE or FIXTURE)
                - LIVE: Fetch from halftime.wiaawi.org via HTTP (default, production mode)
                - FIXTURE: Load from local HTML files (testing mode, no network calls)
            fixtures_dir: Directory containing fixture HTML files (only used in FIXTURE mode)
                Defaults to tests/fixtures/wiaa if not specified
        """
        super().__init__()
        self.state_code = "WI"
        self.league_name = "Wisconsin High School"
        self.league_abbrev = "WIAA"

        # Data fetching mode
        self.data_mode = data_mode
        self.fixtures_dir = fixtures_dir or Path("tests/fixtures/wiaa")

        # HTTP statistics tracking (only relevant in LIVE mode)
        self.http_stats = {
            "brackets_requested": 0,
            "brackets_successful": 0,
            "brackets_404": 0,
            "brackets_403": 0,
            "brackets_500": 0,
            "brackets_timeout": 0,
            "brackets_other_error": 0
        }

    async def _fetch_bracket_with_retry(
        self,
        url: str,
        max_retries: int = 3,
        initial_delay: float = 1.0
    ) -> Optional[str]:
        """
        Fetch bracket HTML with robust error handling and retry logic.

        Handles:
        - 404: Not Found (bracket doesn't exist) - log as debug, return None
        - 403: Forbidden (anti-bot) - retry with backoff, then return None
        - 500+: Server errors - retry with backoff
        - Network timeouts - retry with backoff

        Args:
            url: Bracket URL to fetch
            max_retries: Maximum retry attempts for transient errors
            initial_delay: Initial delay between retries (doubles each retry)

        Returns:
            HTML content if successful, None if not found or permanently failed
        """
        import asyncio
        import httpx

        self.http_stats["brackets_requested"] += 1

        delay = initial_delay
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # Set custom headers to appear more like a browser
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }

                html = await self.http_client.get_text(
                    url,
                    cache_ttl=3600,
                    headers=headers
                )

                self.http_stats["brackets_successful"] += 1
                return html

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                if status_code == 404:
                    # Bracket doesn't exist - this is expected for some divisions/sections
                    self.http_stats["brackets_404"] += 1
                    self.logger.debug(
                        f"Bracket not found (404)",
                        url=url,
                        message="Bracket page does not exist (expected for some divisions/sections)"
                    )
                    return None

                elif status_code == 403:
                    # Anti-bot protection - retry with backoff
                    self.http_stats["brackets_403"] += 1
                    last_error = f"403 Forbidden (anti-bot)"

                    if attempt < max_retries:
                        self.logger.warning(
                            f"Bracket fetch blocked (403), retrying",
                            url=url,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay
                        )
                        await asyncio.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                    else:
                        self.logger.error(
                            f"Bracket fetch permanently blocked after retries",
                            url=url,
                            attempts=max_retries + 1
                        )
                        return None

                elif status_code >= 500:
                    # Server error - retry with backoff
                    self.http_stats["brackets_500"] += 1
                    last_error = f"{status_code} Server Error"

                    if attempt < max_retries:
                        self.logger.warning(
                            f"Server error ({status_code}), retrying",
                            url=url,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay
                        )
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    else:
                        self.logger.error(
                            f"Server error persists after retries",
                            url=url,
                            status_code=status_code,
                            attempts=max_retries + 1
                        )
                        return None
                else:
                    # Other HTTP error
                    self.http_stats["brackets_other_error"] += 1
                    self.logger.error(
                        f"HTTP error fetching bracket",
                        url=url,
                        status_code=status_code
                    )
                    return None

            except (httpx.TimeoutException, asyncio.TimeoutError) as e:
                # Timeout - retry
                self.http_stats["brackets_timeout"] += 1
                last_error = "Timeout"

                if attempt < max_retries:
                    self.logger.warning(
                        f"Timeout fetching bracket, retrying",
                        url=url,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                else:
                    self.logger.error(
                        f"Timeout persists after retries",
                        url=url,
                        attempts=max_retries + 1
                    )
                    return None

            except Exception as e:
                # Unexpected error
                self.http_stats["brackets_other_error"] += 1
                self.logger.error(
                    f"Unexpected error fetching bracket",
                    url=url,
                    error=str(e),
                    error_type=type(e).__name__
                )
                return None

        # Should never reach here, but just in case
        return None

    def get_http_stats(self) -> Dict[str, int]:
        """
        Get HTTP request statistics.

        Returns:
            Dict with counts of various HTTP outcomes
        """
        stats = self.http_stats.copy()

        # Calculate success rate
        if stats["brackets_requested"] > 0:
            stats["success_rate"] = stats["brackets_successful"] / stats["brackets_requested"]
            stats["error_rate"] = 1.0 - stats["success_rate"]
        else:
            stats["success_rate"] = 0.0
            stats["error_rate"] = 0.0

        return stats

    def _load_bracket_fixture(
        self,
        year: int,
        gender: str,
        division: str
    ) -> Optional[str]:
        """
        Load bracket HTML from local fixture file (FIXTURE mode only).

        Constructs filename from year, gender, and division, then loads HTML from
        fixtures_dir. This enables testing without network calls and avoids HTTP 403s.

        Args:
            year: Tournament year (e.g., 2024)
            gender: "Boys" or "Girls"
            division: Division string (e.g., "Div1", "Div2")

        Returns:
            HTML content as string, or None if fixture file not found

        Raises:
            FileNotFoundError: If fixture file doesn't exist
            IOError: If file cannot be read

        Example:
            For year=2024, gender="Boys", division="Div1":
            Loads from: tests/fixtures/wiaa/2024_Basketball_Boys_Div1.html
        """
        # Construct fixture filename matching WIAA URL pattern
        filename = f"{year}_Basketball_{gender}_{division}.html"
        fixture_path = self.fixtures_dir / filename

        try:
            if not fixture_path.exists():
                self.logger.debug(
                    f"Fixture file not found",
                    path=str(fixture_path),
                    year=year,
                    gender=gender,
                    division=division
                )
                return None

            # Load HTML from fixture file
            html = fixture_path.read_text(encoding="utf-8")

            self.logger.debug(
                f"Loaded bracket fixture",
                path=str(fixture_path),
                html_length=len(html)
            )

            return html

        except FileNotFoundError:
            self.logger.warning(
                f"Fixture file not found",
                path=str(fixture_path)
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Error loading fixture file",
                path=str(fixture_path),
                error=str(e)
            )
            return None

    async def _fetch_or_load_bracket(
        self,
        url: str,
        year: int,
        gender: str,
        division: Optional[str]
    ) -> Optional[str]:
        """
        Fetch bracket HTML from live source or load from fixture based on data_mode.

        This is the unified entry point for bracket data retrieval. Routes to:
        - LIVE mode: _fetch_bracket_with_retry() with HTTP retries/backoff
        - FIXTURE mode: _load_bracket_fixture() from local HTML files

        Args:
            url: Bracket URL (only used in LIVE mode)
            year: Tournament year
            gender: "Boys" or "Girls"
            division: Division string (e.g., "Div1")

        Returns:
            HTML content as string, or None if unavailable
        """
        if self.data_mode == DataMode.FIXTURE:
            # Load from fixture file (no network call)
            if division is None:
                self.logger.warning("Division required for FIXTURE mode")
                return None
            return self._load_bracket_fixture(year, gender, division)

        else:  # DataMode.LIVE
            # Fetch from live HTTP source with retries
            return await self._fetch_bracket_with_retry(url)

    def _get_season_url(self, season: str, gender: str = "Boys") -> str:
        """
        Get URL for Wisconsin basketball season data.

        Args:
            season: Season string (e.g., "2024-25")
            gender: "Boys" or "Girls"

        Returns:
            URL for season tournament brackets
        """
        # Extract year (e.g., "2024-25" -> 2025 for tournament year)
        year = int(season.split("-")[0]) + 1

        # Default to Div1, Sec1_2 as starting point for URL discovery
        return f"{self.brackets_url}/{year}_Basketball_{gender}_Div1_Sec1_2.html"

    async def get_tournament_brackets(
        self,
        year: Optional[int] = None,
        gender: str = "Boys",
        division: Optional[str] = None
    ) -> List[Game]:
        """
        Get tournament bracket games for a specific year and gender.

        Args:
            year: Tournament year (e.g., 2025 for 2024-25 season), defaults to current
            gender: "Boys" or "Girls"
            division: Specific division (e.g., "Div1"), or None for all

        Returns:
            List of Game objects from tournament brackets
        """
        if year is None:
            # Determine current tournament year
            now = datetime.now()
            year = now.year + 1 if now.month >= 8 else now.year

        self.logger.info(
            f"Fetching Wisconsin WIAA tournament brackets",
            year=year,
            gender=gender,
            division=division
        )

        # In FIXTURE mode, use simplified URL generation (no discovery, no HTTP calls)
        if self.data_mode == DataMode.FIXTURE:
            bracket_urls = self._generate_fixture_urls(year, gender, division)
        else:
            # LIVE mode: Discover bracket URLs via HTTP
            bracket_urls = await self._discover_bracket_urls(year, gender, division)

            if not bracket_urls:
                self.logger.warning(
                    f"No bracket URLs discovered for Wisconsin WIAA",
                    year=year,
                    gender=gender
                )
                # Fall back to pattern-based URL generation
                bracket_urls = self._generate_bracket_urls(year, gender, division)

        # Parse all discovered brackets
        all_games: List[Game] = []
        for url_info in bracket_urls:
            # Fetch HTML (LIVE mode) or load fixture (FIXTURE mode)
            html = await self._fetch_or_load_bracket(
                url=url_info["url"],
                year=year,
                gender=gender,
                division=url_info.get("division")
            )

            if html is None:
                # Bracket fetch/load failed or doesn't exist - skip silently
                continue

            try:
                games = self._parse_halftime_html_to_games(
                    html,
                    year=year,
                    gender=gender,
                    division=url_info.get("division"),
                    source_url=url_info["url"]
                )

                all_games.extend(games)

                self.logger.info(
                    f"Parsed bracket page",
                    url=url_info["url"],
                    games=len(games),
                    division=url_info.get("division")
                )

            except Exception as e:
                # Parse error - log and continue
                self.logger.warning(
                    f"Failed to parse bracket",
                    url=url_info["url"],
                    error=str(e),
                    error_type=type(e).__name__
                )

        self.logger.info(
            f"Total Wisconsin WIAA tournament games parsed",
            year=year,
            gender=gender,
            total_games=len(all_games)
        )

        return all_games

    async def get_season_data(self, season: Optional[str] = None) -> Dict[str, Any]:
        """
        Get season-level data for Wisconsin WIAA basketball.

        In FIXTURE mode: Aggregates tournament games from available fixtures for the season.
        In LIVE mode: Delegates to base class implementation (may query WIAA APIs).

        Args:
            season: Season string (e.g., "2023-24", "2024-25"), None for current

        Returns:
            Dict with season data:
                - games: List[Game] - All tournament games for the season
                - teams: List[Team] - Unique teams participating
                - metadata: Dict - Season info (year, divisions covered, etc.)

        Example:
            # FIXTURE mode - aggregates from local HTML fixtures
            source = WisconsinWiaaDataSource(data_mode=DataMode.FIXTURE)
            season_data = await source.get_season_data("2023-24")
            # Returns games from all available 2024 Boys/Girls Div1-4 fixtures

            # LIVE mode - queries WIAA website
            source = WisconsinWiaaDataSource(data_mode=DataMode.LIVE)
            season_data = await source.get_season_data("2023-24")
        """
        # In FIXTURE mode, aggregate from available fixtures
        if self.data_mode == DataMode.FIXTURE:
            return await self._get_season_data_from_fixtures(season)

        # LIVE mode: delegate to base class
        return await super().get_season_data(season)

    async def _get_season_data_from_fixtures(self, season: Optional[str] = None) -> Dict[str, Any]:
        """
        Get season data by aggregating from available fixture files.

        This method is only called in FIXTURE mode. It loads all available
        fixtures for the given season and aggregates them into season-level data.

        Args:
            season: Season string (e.g., "2023-24"), None for current

        Returns:
            Dict with games, teams, and metadata
        """
        # Parse season to get tournament year
        # Season "2023-24" -> tournament year 2024 (spring year)
        if season is None:
            now = datetime.now()
            year = now.year + 1 if now.month >= 8 else now.year
        else:
            # Parse season like "2023-24" -> 2024
            parts = season.split("-")
            if len(parts) == 2:
                year = int(parts[1]) + 2000 if len(parts[1]) == 2 else int(parts[1])
            else:
                # Single year format
                year = int(parts[0])

        self.logger.info(
            f"Getting season data from fixtures",
            season=season,
            year=year,
            mode="FIXTURE"
        )

        # Collect all games from available fixtures for this year
        all_games: List[Game] = []
        divisions_covered = set()

        for gender in self.GENDERS:
            for division in self.DIVISIONS:
                # Check if fixture exists
                fixture_path = self.fixtures_dir / f"{year}_Basketball_{gender}_{division}.html"
                if not fixture_path.exists():
                    self.logger.debug(
                        f"Fixture not found, skipping",
                        year=year,
                        gender=gender,
                        division=division
                    )
                    continue

                try:
                    games = await self.get_tournament_brackets(
                        year=year,
                        gender=gender,
                        division=division
                    )

                    all_games.extend(games)
                    divisions_covered.add(f"{gender}_{division}")

                    self.logger.info(
                        f"Loaded games from fixture",
                        year=year,
                        gender=gender,
                        division=division,
                        games_count=len(games)
                    )

                except Exception as e:
                    self.logger.warning(
                        f"Failed to load fixture",
                        year=year,
                        gender=gender,
                        division=division,
                        error=str(e)
                    )

        # Extract unique teams
        teams_dict: Dict[str, Team] = {}
        for game in all_games:
            # Home team
            if game.home_team_id not in teams_dict:
                teams_dict[game.home_team_id] = Team(
                    team_id=game.home_team_id,
                    team_name=game.home_team_name,
                    state=self.state_code,
                    level=TeamLevel.HIGH_SCHOOL_VARSITY,
                    conference=f"WIAA {self.state_code}",
                    data_source=game.data_source
                )

            # Away team
            if game.away_team_id not in teams_dict:
                teams_dict[game.away_team_id] = Team(
                    team_id=game.away_team_id,
                    team_name=game.away_team_name,
                    state=self.state_code,
                    level=TeamLevel.HIGH_SCHOOL_VARSITY,
                    conference=f"WIAA {self.state_code}",
                    data_source=game.data_source
                )

        teams = list(teams_dict.values())

        self.logger.info(
            f"Season data aggregated from fixtures",
            season=season,
            year=year,
            total_games=len(all_games),
            total_teams=len(teams),
            divisions_covered=sorted(divisions_covered)
        )

        return {
            "games": all_games,
            "teams": teams,
            "metadata": {
                "season": season or f"{year-1}-{str(year)[-2:]}",
                "year": year,
                "divisions_covered": sorted(divisions_covered),
                "fixture_count": len(divisions_covered),
                "data_mode": "FIXTURE"
            }
        }

    async def _discover_bracket_urls(
        self,
        year: int,
        gender: str,
        division: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Discover bracket URLs by parsing navigation links from index pages.

        This is the Phase 2 enhancement - discovery-first approach instead of
        pattern-based URL generation.

        Args:
            year: Tournament year
            gender: "Boys" or "Girls"
            division: Optional specific division

        Returns:
            List of dicts with {"url": str, "division": str, "sections": str}
        """
        discovered_urls: List[Dict[str, str]] = []

        # Try to fetch a known bracket page to find navigation links
        divisions_to_check = [division] if division else self.DIVISIONS

        for div in divisions_to_check:
            # Try common sectional groupings
            for sec_group in ["Sec1_2", "Sec3_4", "Sec5_6", "Sec7_8"]:
                url = f"{self.brackets_url}/{year}_Basketball_{gender}_{div}_{sec_group}.html"
                html = await self._fetch_bracket_with_retry(url)

                if html is None:
                    # Bracket doesn't exist - try next URL
                    continue

                try:
                    # Parse HTML to find navigation links
                    soup = parse_html(html)

                    # Look for links to other bracket pages
                    # Pattern: href containing "/CustomApps/Tournaments/Brackets/HTML/"
                    links = soup.find_all("a", href=re.compile(r'/CustomApps/Tournaments/Brackets/HTML/'))

                    for link in links:
                        href = link.get("href", "")
                        if not href:
                            continue

                        # Extract full URL
                        if href.startswith("http"):
                            full_url = href
                        elif href.startswith("/"):
                            full_url = f"https://halftime.wiaawi.org{href}"
                        else:
                            full_url = f"{self.brackets_url}/{href}"

                        # Parse division and sections from URL
                        # Format: 2025_Basketball_Girls_Div1_Sec3_4.html
                        match = re.search(
                            r'(\d{4})_Basketball_(Boys|Girls)_(Div\d+)_(Sec[\d_]+)\.html',
                            full_url
                        )

                        if match:
                            url_year, url_gender, url_div, url_secs = match.groups()

                            if (int(url_year) == year and
                                url_gender == gender and
                                (not division or url_div == division)):

                                discovered_urls.append({
                                    "url": full_url,
                                    "division": url_div,
                                    "sections": url_secs,
                                    "year": url_year,
                                    "gender": url_gender
                                })

                    # If we found links, we can break
                    if discovered_urls:
                        break

                except Exception as e:
                    # Silently continue - page may not exist
                    continue

            if discovered_urls:
                break

        # Deduplicate URLs
        seen_urls = set()
        unique_urls = []
        for url_info in discovered_urls:
            if url_info["url"] not in seen_urls:
                seen_urls.add(url_info["url"])
                unique_urls.append(url_info)

        return unique_urls

    def _generate_bracket_urls(
        self,
        year: int,
        gender: str,
        division: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Generate bracket URLs using pattern-based approach.

        Fallback for when discovery fails (historical years, etc.)

        Args:
            year: Tournament year
            gender: "Boys" or "Girls"
            division: Optional specific division

        Returns:
            List of dicts with {"url": str, "division": str}
        """
        urls: List[Dict[str, str]] = []

        divisions = [division] if division else self.DIVISIONS

        # Common sectional groupings
        sectional_groups = [
            "Sec1_2", "Sec3_4", "Sec5_6", "Sec7_8",
            "Sec9_10", "Sec11_12", "Sec13_14", "Sec15_16"
        ]

        for div in divisions:
            for sec_group in sectional_groups:
                url = f"{self.brackets_url}/{year}_Basketball_{gender}_{div}_{sec_group}.html"
                urls.append({
                    "url": url,
                    "division": div,
                    "sections": sec_group,
                    "year": str(year),
                    "gender": gender
                })

        return urls

    def _generate_fixture_urls(
        self,
        year: int,
        gender: str,
        division: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Generate fixture URLs for FIXTURE mode.

        Uses simplified URL pattern matching fixture file naming:
        {year}_Basketball_{gender}_{division}.html

        Args:
            year: Tournament year
            gender: "Boys" or "Girls"
            division: Optional specific division

        Returns:
            List of dicts with {"url": str, "division": str}
        """
        urls: List[Dict[str, str]] = []
        divisions = [division] if division else self.DIVISIONS

        for div in divisions:
            # Simple fixture filename (no sectional suffix)
            filename = f"{year}_Basketball_{gender}_{div}.html"
            url = f"{self.brackets_url}/{filename}"

            urls.append({
                "url": url,
                "division": div,
                "year": str(year),
                "gender": gender
            })

        return urls

    def _parse_halftime_html_to_games(
        self,
        html: str,
        year: int,
        gender: str,
        division: Optional[str],
        source_url: str
    ) -> List[Game]:
        """
        Parse halftime.wiaawi.org HTML to extract games.

        Enhanced Phase 1 parser with:
        - Self-game detection and skipping
        - Duplicate game detection
        - Improved round parsing
        - Invalid score filtering
        - Comprehensive logging

        Args:
            html: HTML content from bracket page
            year: Tournament year
            gender: "Boys" or "Girls"
            division: Division (e.g., "Div1")
            source_url: Source URL for reference

        Returns:
            List of Game objects
        """
        soup = parse_html(html)

        # Convert HTML to text for line-by-line parsing
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        games: List[Game] = []
        seen_games: Set[Tuple[str, str, int, int]] = set()  # (team1, team2, score1, score2)

        # Parsing state
        current_sectional: Optional[str] = None
        current_round: str = "Unknown Round"
        current_date: Optional[datetime] = None
        current_time: Optional[str] = None
        current_location: Optional[str] = None
        pending_teams: List[Tuple[str, int]] = []  # [(team_name, seed), ...]

        # Statistics for logging
        stats = {
            "total_lines": len(lines),
            "games_found": 0,
            "skipped_self_games": 0,
            "skipped_duplicates": 0,
            "skipped_invalid_scores": 0,
            "rounds_detected": set()
        }

        # Regex patterns
        sectional_pattern = re.compile(r'^Sectional\s*#?(\d+)', re.IGNORECASE)
        round_patterns = [
            (re.compile(r'Regional\s+Semi-?finals?', re.IGNORECASE), "Regional Semifinals"),
            (re.compile(r'Regional\s+Finals?', re.IGNORECASE), "Regional Finals"),
            (re.compile(r'Sectional\s+Semi-?finals?', re.IGNORECASE), "Sectional Semifinals"),
            (re.compile(r'Sectional\s+Finals?', re.IGNORECASE), "Sectional Finals"),
            (re.compile(r'State\s+Semi-?finals?', re.IGNORECASE), "State Semifinals"),
            (re.compile(r'State\s+Championship', re.IGNORECASE), "State Championship"),
            (re.compile(r'Regionals?', re.IGNORECASE), "Regional"),
            (re.compile(r'Sectionals?', re.IGNORECASE), "Sectional"),
            (re.compile(r'State', re.IGNORECASE), "State"),
        ]
        team_pattern = re.compile(r'^#?(\d+)\s+(.+)$')
        score_pattern = re.compile(r'^(\d{1,3})-(\d{1,3})(?:\s*\((OT|2OT|3OT)\))?$')
        location_pattern = re.compile(r'^@(.+)$')
        date_pattern = re.compile(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(\w+)\s+(\d+)')
        time_pattern = re.compile(r'(\d{1,2}):(\d{2})\s*(AM|PM)', re.IGNORECASE)

        for line_num, line in enumerate(lines, 1):
            # Check for sectional header
            sectional_match = sectional_pattern.search(line)
            if sectional_match:
                current_sectional = f"Sectional {sectional_match.group(1)}"
                continue

            # Check for round header
            for pattern, round_name in round_patterns:
                if pattern.search(line):
                    current_round = round_name
                    stats["rounds_detected"].add(round_name)
                    break

            # Check for date
            date_match = date_pattern.search(line)
            if date_match:
                # Parse date (month name to date)
                # For now, just store the string - full date parsing could be added
                current_date = None  # TODO: Implement full date parsing
                continue

            # Check for time
            time_match = time_pattern.search(line)
            if time_match:
                current_time = time_match.group(0)
                continue

            # Check for location
            location_match = location_pattern.search(line)
            if location_match:
                current_location = location_match.group(1).strip()
                continue

            # Check for team (seed + name)
            team_match = team_pattern.match(line)
            if team_match:
                seed = int(team_match.group(1))
                team_name = team_match.group(2).strip()
                pending_teams.append((team_name, seed))
                continue

            # Check for score
            score_match = score_pattern.match(line)
            if score_match:
                score1 = int(score_match.group(1))
                score2 = int(score_match.group(2))
                overtime = score_match.group(3) if len(score_match.groups()) >= 3 else None

                # Validate score
                if not (self.MIN_SCORE <= score1 <= self.MAX_SCORE and
                        self.MIN_SCORE <= score2 <= self.MAX_SCORE):
                    stats["skipped_invalid_scores"] += 1
                    pending_teams = []
                    continue

                # We need exactly 2 teams for a game
                if len(pending_teams) == 2:
                    team1_name, team1_seed = pending_teams[0]
                    team2_name, team2_seed = pending_teams[1]

                    # Skip self-games (team playing itself)
                    if team1_name.lower() == team2_name.lower():
                        stats["skipped_self_games"] += 1
                        pending_teams = []
                        continue

                    # Check for duplicates
                    # Normalize team order to catch reverse duplicates
                    teams_sorted = tuple(sorted([team1_name, team2_name]))
                    scores_sorted = tuple(sorted([score1, score2]))
                    game_key = (teams_sorted[0], teams_sorted[1], scores_sorted[0], scores_sorted[1])

                    if game_key in seen_games:
                        stats["skipped_duplicates"] += 1
                        pending_teams = []
                        continue

                    seen_games.add(game_key)

                    # Determine home/away based on higher seed (higher seed typically home)
                    if team1_seed < team2_seed:  # Lower seed number = higher seed
                        home_team, home_score = team1_name, score1
                        away_team, away_score = team2_name, score2
                    else:
                        home_team, home_score = team2_name, score2
                        away_team, away_score = team1_name, score1

                    # Create game ID
                    game_id = self._generate_game_id(
                        year, gender, division, current_sectional, current_round,
                        home_team, away_team
                    )

                    # Create Game object
                    # Use placeholder date if current_date is None (TODO: full date parsing)
                    if current_date is None:
                        current_date = datetime(year, 3, 1)  # Default to March 1st for tournament games

                    game = Game(
                        game_id=game_id,
                        home_team_name=home_team,
                        away_team_name=away_team,
                        home_team_id=f"wiaa_wi_{home_team.lower().replace(' ', '_')}",
                        away_team_id=f"wiaa_wi_{away_team.lower().replace(' ', '_')}",
                        home_score=home_score,
                        away_score=away_score,
                        game_date=current_date,
                        game_type=GameType.TOURNAMENT,
                        status=GameStatus.FINAL,
                        season=f"{year-1}-{str(year)[-2:]}",
                        round=current_round,
                        location=current_location,
                        overtime_periods=self._parse_overtime(overtime) if overtime else None,
                        gender=gender,
                        division=division,
                        sectional=current_sectional,
                        data_source=self.create_data_source_metadata(
                            url=source_url,
                            quality_flag=DataQualityFlag.VERIFIED
                        )
                    )

                    games.append(game)
                    stats["games_found"] += 1

                    # Clear pending teams
                    pending_teams = []

                continue

        # Log statistics
        self.logger.info(
            f"Wisconsin WIAA bracket parsing complete",
            **stats,
            url=source_url
        )

        return games

    def _generate_game_id(
        self,
        year: int,
        gender: str,
        division: Optional[str],
        sectional: Optional[str],
        round: str,
        home_team: str,
        away_team: str
    ) -> str:
        """Generate unique game ID."""
        parts = [
            "wiaa_wi",
            str(year),
            gender.lower(),
            division.lower() if division else "unknown",
            round.lower().replace(" ", "_"),
            home_team.lower().replace(" ", "_")[:15],
            away_team.lower().replace(" ", "_")[:15]
        ]
        return "_".join(parts)

    def _parse_overtime(self, overtime_str: str) -> int:
        """Parse overtime string to number of periods."""
        if not overtime_str:
            return 0

        if overtime_str == "OT":
            return 1
        elif overtime_str == "2OT":
            return 2
        elif overtime_str == "3OT":
            return 3

        return 0

    async def _parse_json_data(self, json_data: Dict[str, Any], season: str) -> Dict[str, Any]:
        """
        Parse JSON data from Wisconsin WIAA.

        WIAA primarily uses HTML, so JSON parsing is minimal.
        """
        self.logger.debug("Wisconsin WIAA uses HTML brackets, not JSON")
        return {"teams": [], "games": [], "season": season, "source": "json"}

    async def _parse_html_data(self, html: str, season: str) -> Dict[str, Any]:
        """
        Parse HTML data from Wisconsin WIAA.

        Args:
            html: HTML content
            season: Season string

        Returns:
            Dict with teams and games
        """
        # Extract year and default to Boys
        year = int(season.split("-")[0]) + 1

        # Parse games from HTML
        games = self._parse_halftime_html_to_games(
            html,
            year=year,
            gender="Boys",
            division=None,
            source_url=self.base_url
        )

        # Extract unique teams from games
        teams_dict: Dict[str, Team] = {}

        for game in games:
            # Add home team
            if game.home_team_id and game.home_team_id not in teams_dict:
                teams_dict[game.home_team_id] = Team(
                    team_id=game.home_team_id,
                    name=game.home_team_name,
                    school=game.home_team_name,
                    level=TeamLevel.HIGH_SCHOOL,
                    season=season,
                    state=self.state_code,
                    country="USA",
                    data_source=self.create_data_source_metadata(
                        url=self.base_url,
                        quality_flag=DataQualityFlag.VERIFIED
                    )
                )

            # Add away team
            if game.away_team_id and game.away_team_id not in teams_dict:
                teams_dict[game.away_team_id] = Team(
                    team_id=game.away_team_id,
                    name=game.away_team_name,
                    school=game.away_team_name,
                    level=TeamLevel.HIGH_SCHOOL,
                    season=season,
                    state=self.state_code,
                    country="USA",
                    data_source=self.create_data_source_metadata(
                        url=self.base_url,
                        quality_flag=DataQualityFlag.VERIFIED
                    )
                )

        teams = list(teams_dict.values())

        self.logger.info(
            f"Parsed Wisconsin WIAA HTML data",
            season=season,
            teams=len(teams),
            games=len(games)
        )

        return {"teams": teams, "games": games, "season": season, "source": "html"}

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

        Overrides base class to add gender support.
        """
        # Determine year from season
        if season:
            year = int(season.split("-")[0]) + 1
        else:
            now = datetime.now()
            year = now.year + 1 if now.month >= 8 else now.year

        # Get both Boys and Girls games
        boys_games = await self.get_tournament_brackets(year=year, gender="Boys")
        girls_games = await self.get_tournament_brackets(year=year, gender="Girls")

        games = boys_games + girls_games

        # Apply filters
        if team_id:
            games = [g for g in games if g.home_team_id == team_id or g.away_team_id == team_id]

        if start_date:
            games = [g for g in games if g.game_date and g.game_date >= start_date]

        if end_date:
            games = [g for g in games if g.game_date and g.game_date <= end_date]

        return games[:limit]
