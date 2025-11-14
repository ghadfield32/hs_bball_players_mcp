"""
NIAA (Nevada Interscholastic Activities Association) DataSource Adapter

Provides authoritative tournament brackets, seeds, scores, and championship results
for Nevada high school basketball. This is the OFFICIAL source for postseason data.

**Data Authority**: NIAA is the source of truth for:
- Tournament brackets (4 divisions: 5A, 4A, 3A, 2A, 1A)
- Seeds and matchups
- Game dates, times, locations
- Final scores and champions
- **PDF brackets** (common format)
- Historical tournament data

**Base URL**: https://www.niaa.com

**URL Pattern**:
```
Basketball: /sports/basketball
Brackets: /sports/basketball/brackets
PDFs: /uploads/brackets/basketball/{division}/{year}.pdf
```

**Coverage**:
- Divisions: 5A (largest), 4A, 3A, 2A, 1A (smallest) - Based on school enrollment
- Boys and Girls tournaments
- State championships

**Nevada Basketball Context**:
- 32nd largest US state by population (3.2M)
- Growing basketball scene (Las Vegas metro area)
- Notable players: Armon Johnson, Marcus Banks
- 100+ NIAA member schools in basketball
- Partially covered by SBLive for regular season

**Special Features**:
- **PDF bracket parsing** with hash-based caching
- Stores `pdf_hash` and `extracted_text_len` for change detection
- Skips re-parsing unchanged PDFs

**Limitations**:
- Player statistics NOT available (state associations focus on brackets/lineage)
- Regular season schedules NOT available
- Box scores rarely available
- PDFs require text extraction

**Recommended Use**: NIAA provides official tournament lineage and brackets.
For player-level stats, combine with SBLive (covers NV).

**Dependencies**:
- pdfplumber>=0.10.0 (for PDF text extraction)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import re
import hashlib
import io

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
    Team,
    TeamLevel,
)
from ...utils import (
    extract_table_data,
    get_text_or_none,
    parse_html,
    parse_int,
    parse_record,
)
from ..base_association import AssociationAdapterBase

# Optional PDF support
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


class NevadaNIAADataSource(AssociationAdapterBase):
    """
    Nevada Interscholastic Activities Association (NIAA) data source adapter.

    **PRIMARY PURPOSE**: Authoritative tournament bracket and postseason results.

    **SPECIAL FEATURE**: PDF bracket parsing with hash-based caching to avoid re-parsing.

    This adapter provides:
    1. Tournament brackets for all divisions (5A-1A)
    2. Seeds, matchups, dates, locations
    3. Game scores and final results
    4. PDF text extraction with caching
    5. Historical tournament data

    **ARCHITECTURE**:
    - Inherits from AssociationAdapterBase for JSON-first discovery + HTML fallback
    - Implements PDF text extraction with hash-based caching
    - Tries HTML first, falls back to PDF if HTML not available
    - Stores pdf_hash to skip unchanged PDFs
    - Generates unique game IDs: niaa:{year}:{div}:{home}@{away}

    **DATA QUALITY**: HIGH (official source, authoritative)

    **LIMITATIONS**:
    - No player-level statistics (use SBLive for this)
    - No regular season schedules
    - Bracket-focused, not stats-focused
    - PDF parsing may be less reliable than HTML

    **PDF Caching Strategy**:
    - Hash PDF content (SHA-256)
    - Check cache for pdf_hash
    - Skip extraction if hash unchanged
    - Store extracted_text_len for verification
    """

    source_type = DataSourceType.NIAA
    source_name = "Nevada NIAA"
    base_url = "https://www.niaa.com"
    region = DataSourceRegion.US_NV

    # NIAA-specific constants
    DIVISIONS = ["5A", "4A", "3A", "2A", "1A"]  # 5A = largest, 1A = smallest
    GENDERS = ["Boys", "Girls"]
    MIN_YEAR = 2016  # Historical data availability
    STATE_CODE = "NV"
    STATE_NAME = "Nevada"

    def __init__(self):
        """Initialize NIAA datasource with Nevada-specific configuration."""
        super().__init__()

        # PDF cache (in-memory for now; could be Redis/file-based)
        self.pdf_cache: Dict[str, Dict[str, Any]] = {}

        self.logger.info(
            "NIAA initialized",
            divisions=len(self.DIVISIONS),
            genders=len(self.GENDERS),
            min_year=self.MIN_YEAR,
            pdf_support=PDF_SUPPORT,
        )

        if not PDF_SUPPORT:
            self.logger.warning(
                "pdfplumber not installed - PDF brackets will not be parsed. "
                "Install with: pip install pdfplumber>=0.10.0"
            )

    async def _fetch_pdf_with_conditional_request(self, url: str) -> Optional[bytes]:
        """
        Fetch PDF with conditional requests using ETag and Last-Modified headers.

        This avoids re-downloading unchanged PDFs by:
        - Storing ETag and Last-Modified headers in cache
        - Sending If-None-Match and If-Modified-Since on subsequent requests
        - Returning cached content on 304 Not Modified

        Args:
            url: PDF URL to fetch

        Returns:
            PDF bytes or None if 404/not found

        Raises:
            RuntimeError: On unexpected HTTP errors (not 200/304/404)
        """
        # Build cache key for metadata (separate from content hash cache)
        cache_key = f"pdf_meta:{url}"
        meta = self.pdf_cache.get(cache_key, {})

        # Build conditional request headers
        headers = {}
        if "ETag" in meta:
            headers["If-None-Match"] = meta["ETag"]
        if "Last-Modified" in meta:
            headers["If-Modified-Since"] = meta["Last-Modified"]

        # Make request
        status, content, response_headers = await self.http_get(url, timeout=60.0, headers=headers)

        # Handle 304 Not Modified
        if status == 304:
            self.logger.debug(f"PDF not modified, using cached version", url=url)
            return meta.get("content")

        # Handle 404 Not Found
        if status == 404:
            self.logger.info(f"PDF not found (may not be published yet)", url=url)
            return None

        # Handle success
        if status == 200:
            # Store new metadata and content
            self.pdf_cache[cache_key] = {
                "content": content,
                "ETag": response_headers.get("ETag") or response_headers.get("etag"),
                "Last-Modified": response_headers.get("Last-Modified") or response_headers.get("last-modified"),
                "fetched_at": datetime.now().isoformat(),
            }
            self.logger.debug(
                f"PDF fetched and cached",
                url=url,
                size_bytes=len(content),
                has_etag=bool(response_headers.get("ETag")),
            )
            return content

        # Other errors
        raise RuntimeError(f"Unexpected PDF fetch status {status} for {url}")

    def _get_season_url(self, season: str) -> str:
        """
        Get URL for Nevada basketball season data.

        Args:
            season: Season string (e.g., "2024-25")

        Returns:
            Base URL for basketball brackets
        """
        year = int(season.split("-")[1]) if "-" in season else int(season)
        if year < 100:
            year += 2000

        return f"{self.base_url}/sports/basketball"

    def _build_bracket_url(
        self, division: str, gender: str = "Boys", year: Optional[int] = None
    ) -> str:
        """
        Build URL for specific tournament bracket.

        **NIAA URL Format** (varies - may need URL discovery):
        ```
        HTML: /sports/basketball/brackets/{year}/{gender}/{division}
        PDF: /uploads/brackets/basketball/{division}/{year}_{gender.lower()}.pdf
        ```

        Args:
            division: Division name (5A, 4A, 3A, 2A, 1A)
            gender: "Boys" or "Girls"
            year: Tournament year (optional)

        Returns:
            Full bracket URL (HTML)
        """
        year = year or datetime.now().year
        gender_lower = gender.lower()

        # Try HTML URL first
        return f"{self.base_url}/sports/basketball/brackets/{year}/{gender_lower}/{division.lower()}"

    def _build_pdf_bracket_url(
        self, division: str, gender: str = "Boys", year: Optional[int] = None
    ) -> str:
        """
        Build URL for PDF bracket.

        Args:
            division: Division name
            gender: Boys or Girls
            year: Tournament year

        Returns:
            PDF bracket URL
        """
        year = year or datetime.now().year
        gender_lower = gender.lower()

        return f"{self.base_url}/uploads/brackets/basketball/{division.lower()}/{year}_{gender_lower}.pdf"

    async def get_tournament_brackets(
        self, season: Optional[str] = None, division: Optional[str] = None, gender: str = "Boys"
    ) -> Dict[str, Any]:
        """
        Get tournament brackets for a season.

        **ENUMERATION STRATEGY**:
        - Try HTML endpoint first
        - Fall back to PDF if HTML not available
        - Use PDF hash caching to skip unchanged PDFs
        - If season provided: fetch brackets for that year
        - If division provided: only fetch that division's bracket
        - Otherwise: fetch current year, all divisions

        Args:
            season: Season string (e.g., "2024-25"), None for current
            division: Specific division (5A, 4A, etc.), None for all
            gender: "Boys" or "Girls"

        Returns:
            Dict with keys:
                - games: List[Game] - all tournament games
                - teams: List[Team] - all participating teams
                - brackets: Dict[str, List[Game]] - games grouped by division
                - metadata: bracket metadata (year, updated timestamps, pdf_hashes)
        """
        # Determine year
        if season:
            year = int(season.split("-")[1]) if "-" in season else int(season)
            if year < 100:
                year += 2000
        else:
            year = datetime.now().year

        # Determine divisions to fetch
        divisions = [division] if division else self.DIVISIONS

        all_games: List[Game] = []
        all_teams: Dict[str, Team] = {}
        brackets: Dict[str, List[Game]] = {}
        metadata: Dict[str, Any] = {}

        self.logger.info(
            f"Fetching NIAA tournament brackets",
            year=year,
            divisions=divisions,
            gender=gender,
        )

        # Enumerate all bracket combinations
        for div in divisions:
            bracket_key = f"div_{div.lower()}"

            try:
                # Try HTML first
                html_url = self._build_bracket_url(div, gender, year)
                status, content, headers = await self.http_get(html_url, timeout=30.0)

                if status == 200:
                    # Parse HTML bracket
                    html = content.decode("utf-8")
                    soup = parse_html(html)

                    bracket_data = self._parse_bracket_html(soup, year, div, gender, html_url)

                    self.logger.info(
                        f"Parsed HTML bracket",
                        division=div,
                        games=len(bracket_data["games"]),
                        teams=len(bracket_data["teams"]),
                    )
                else:
                    # Fall back to PDF
                    if not PDF_SUPPORT:
                        self.logger.warning(
                            f"PDF support not available - skipping",
                            division=div,
                        )
                        continue

                    pdf_url = self._build_pdf_bracket_url(div, gender, year)
                    bracket_data = await self._fetch_and_parse_pdf(pdf_url, year, div, gender)

                    if not bracket_data:
                        self.logger.warning(
                            f"Failed to fetch/parse bracket",
                            division=div,
                        )
                        continue

                    self.logger.info(
                        f"Parsed PDF bracket",
                        division=div,
                        games=len(bracket_data["games"]),
                        teams=len(bracket_data["teams"]),
                    )

                # Collect games and teams
                for game in bracket_data["games"]:
                    all_games.append(game)
                    brackets.setdefault(bracket_key, []).append(game)

                for team in bracket_data["teams"]:
                    all_teams[team.team_id] = team

                # Collect metadata
                if bracket_data.get("metadata"):
                    metadata[bracket_key] = bracket_data["metadata"]

            except Exception as e:
                self.logger.warning(
                    f"Failed to fetch bracket",
                    year=year,
                    division=div,
                    gender=gender,
                    error=str(e),
                )
                continue

        self.logger.info(
            f"Fetched all tournament brackets",
            year=year,
            total_games=len(all_games),
            total_teams=len(all_teams),
        )

        return {
            "games": all_games,
            "teams": list(all_teams.values()),
            "brackets": brackets,
            "metadata": metadata,
            "year": year,
            "gender": gender,
        }

    async def _fetch_and_parse_pdf(
        self, pdf_url: str, year: int, division: str, gender: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch PDF, hash for cache, extract text, parse bracket.

        **PDF Caching Strategy**:
        1. Fetch PDF content
        2. Hash content (SHA-256)
        3. Check cache for pdf_hash
        4. If cached and unchanged, return cached data
        5. If new/changed, extract text and parse

        Args:
            pdf_url: PDF URL
            year: Tournament year
            division: Division name
            gender: Boys or Girls

        Returns:
            Dict with games, teams, metadata (including pdf_hash)
        """
        try:
            # Fetch PDF with conditional request (ETag/Last-Modified)
            content = await self._fetch_pdf_with_conditional_request(pdf_url)

            if content is None:
                # 404 or not available
                return None

            # Hash PDF for cache
            pdf_hash = hashlib.sha256(content).hexdigest()

            # Check cache
            if pdf_hash in self.pdf_cache:
                self.logger.info(f"PDF cache hit", pdf_hash=pdf_hash[:8], url=pdf_url)
                cached_data = self.pdf_cache[pdf_hash]
                return cached_data

            # Extract text from PDF
            self.logger.info(f"Extracting text from PDF", url=pdf_url)

            with pdfplumber.open(io.BytesIO(content)) as pdf:
                # Extract text from all pages
                text_pages = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_pages.append(page_text)

                full_text = "\n".join(text_pages)

            extracted_text_len = len(full_text)
            self.logger.info(
                f"Extracted PDF text",
                pages=len(text_pages),
                text_len=extracted_text_len,
            )

            # Parse bracket from text
            bracket_data = self._parse_bracket_text(full_text, year, division, gender, pdf_url)

            # Add PDF metadata
            bracket_data["metadata"]["pdf_hash"] = pdf_hash
            bracket_data["metadata"]["extracted_text_len"] = extracted_text_len
            bracket_data["metadata"]["source"] = "pdf"

            # Cache result
            self.pdf_cache[pdf_hash] = bracket_data

            return bracket_data

        except Exception as e:
            self.logger.error(f"Error fetching/parsing PDF", url=pdf_url, error=str(e))
            return None

    def _parse_bracket_text(
        self, text: str, year: int, division: str, gender: str, source_url: str
    ) -> Dict[str, Any]:
        """
        Parse bracket data from extracted PDF text.

        **Text Parsing Strategy**:
        - Look for team names (often in all caps or after "#" seed markers)
        - Look for scores (numeric patterns)
        - Look for dates (MM/DD/YY patterns)
        - Extract matchups from line-by-line parsing

        **Expected Text Patterns**:
        ```
        #1 Las Vegas Centennial vs #16 Reno High
        Score: 75-62
        Date: 3/1/2025
        ```

        Args:
            text: Extracted PDF text
            year: Tournament year
            division: Division name
            gender: Boys or Girls
            source_url: Source URL

        Returns:
            Dict with games, teams, metadata
        """
        games: List[Game] = []
        teams: Dict[str, Team] = {}
        metadata: Dict[str, Any] = {"last_updated": None, "bracket_status": "unknown"}

        # Split into lines
        lines = text.split("\n")

        # Track current matchup context
        current_team1 = None
        current_team2 = None
        current_score1 = None
        current_score2 = None

        for line in lines:
            line = line.strip()

            # Look for team vs team patterns
            vs_match = re.search(r"(.+?)\s+vs\.?\s+(.+)", line, re.I)
            if vs_match:
                team1_text = vs_match.group(1).strip()
                team2_text = vs_match.group(2).strip()

                # Extract teams and seeds
                team1_name, seed1 = self._extract_team_and_seed(team1_text)
                team2_name, seed2 = self._extract_team_and_seed(team2_text)

                if team1_name and team2_name:
                    current_team1 = team1_name
                    current_team2 = team2_name
                    # Look for scores in same or next line
                    score_match = re.search(r"(\d+)\s*[-–]\s*(\d+)", line)
                    if score_match:
                        current_score1 = int(score_match.group(1))
                        current_score2 = int(score_match.group(2))

                    continue

            # Look for score patterns
            if current_team1 and current_team2:
                score_match = re.search(r"(\d+)\s*[-–]\s*(\d+)", line)
                if score_match:
                    current_score1 = int(score_match.group(1))
                    current_score2 = int(score_match.group(2))

                    # Create game
                    game = self._create_game_from_matchup(
                        current_team1,
                        current_team2,
                        current_score1,
                        current_score2,
                        year,
                        division,
                        gender,
                        source_url,
                    )

                    if game:
                        games.append(game)

                        # Add teams
                        for team_name, team_id in [
                            (current_team1, game.home_team_id),
                            (current_team2, game.away_team_id),
                        ]:
                            if team_name and team_id:
                                team = self._create_team_from_game(
                                    team_id, team_name, division, f"{year-1}-{str(year)[2:]}"
                                )
                                teams[team_id] = team

                    # Reset context
                    current_team1 = None
                    current_team2 = None
                    current_score1 = None
                    current_score2 = None

        self.logger.debug(
            f"Parsed bracket text",
            division=division,
            games=len(games),
            teams=len(teams),
        )

        return {"games": games, "teams": list(teams.values()), "metadata": metadata}

    def _parse_bracket_html(
        self, soup, year: int, division: str, gender: str, url: str
    ) -> Dict[str, Any]:
        """Parse HTML bracket (reuse logic from AIA/OSAA)."""
        games: List[Game] = []
        teams: Dict[str, Team] = {}
        metadata: Dict[str, Any] = {"last_updated": None, "bracket_status": "unknown"}

        # Find bracket containers
        bracket_containers = soup.find_all("table") or soup.find_all(
            "div", class_=re.compile(r"bracket|game|matchup", re.I)
        )

        if not bracket_containers:
            self.logger.warning(f"No bracket containers found", url=url)
            return {"games": [], "teams": [], "metadata": metadata}

        # Parse containers
        for container in bracket_containers:
            if container.name == "table":
                rows = container.find_all("tr")
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue

                    game = self._parse_game_from_bracket_row(
                        cells, year, division, gender, url
                    )
                    if game:
                        games.append(game)

                        for team_name, team_id in [
                            (game.home_team_name, game.home_team_id),
                            (game.away_team_name, game.away_team_id),
                        ]:
                            if team_name and team_id:
                                team = self._create_team_from_game(
                                    team_id, team_name, division, f"{year-1}-{str(year)[2:]}"
                                )
                                teams[team_id] = team

        return {"games": games, "teams": list(teams.values()), "metadata": metadata}

    def _parse_game_from_bracket_row(
        self, cells: List, year: int, division: str, gender: str, source_url: str
    ) -> Optional[Game]:
        """Parse game from HTML table row."""
        try:
            cell_texts = [get_text_or_none(cell) or "" for cell in cells]

            team_cells = [
                text for text in cell_texts if text and len(text) > 2 and not text.isdigit()
            ]

            if len(team_cells) < 2:
                return None

            team1_full = team_cells[0]
            team2_full = team_cells[1] if len(team_cells) > 1 else ""

            team1_name, seed1 = self._extract_team_and_seed(team1_full)
            team2_name, seed2 = self._extract_team_and_seed(team2_full)

            if not team1_name or not team2_name:
                return None

            # Parse scores
            score1 = None
            score2 = None
            for text in cell_texts:
                val = parse_int(text)
                if val is not None:
                    if score1 is None:
                        score1 = val
                    elif score2 is None:
                        score2 = val
                        break

            return self._create_game_from_matchup(
                team1_name, team2_name, score1, score2, year, division, gender, source_url
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse game from bracket row", error=str(e))
            return None

    def _create_game_from_matchup(
        self,
        team1_name: str,
        team2_name: str,
        score1: Optional[int],
        score2: Optional[int],
        year: int,
        division: str,
        gender: str,
        source_url: str,
    ) -> Optional[Game]:
        """Create Game object from matchup data."""
        try:
            # Generate IDs
            home_team_slug = team1_name.lower().replace(" ", "_")
            away_team_slug = team2_name.lower().replace(" ", "_")
            game_id = f"niaa_{year}_div{division.lower()}_{home_team_slug}_vs_{away_team_slug}"
            home_team_id = f"niaa_nv_{home_team_slug}"
            away_team_id = f"niaa_nv_{away_team_slug}"

            # Determine status
            status = GameStatus.FINAL if (score1 is not None and score2 is not None) else GameStatus.SCHEDULED

            return Game(
                game_id=game_id,
                home_team_id=home_team_id,
                home_team_name=team1_name,
                away_team_id=away_team_id,
                away_team_name=team2_name,
                home_score=score1,
                away_score=score2,
                game_date=None,
                status=status,
                game_type=GameType.PLAYOFF,
                level="high_school_varsity",
                league=f"NIAA Division {division}",
                location=f"Nevada Division {division}",
                season=f"{year-1}-{str(year)[2:]}",
                gender=gender.lower(),
                data_source=self.create_data_source_metadata(
                    url=source_url,
                    quality_flag=DataQualityFlag.VERIFIED,
                ),
            )

        except Exception as e:
            self.logger.warning(f"Failed to create game from matchup", error=str(e))
            return None

    def _extract_team_and_seed(self, team_text: str) -> Tuple[str, Optional[int]]:
        """Extract team name and seed from text like "#1 Las Vegas Centennial" or "Reno High (2)"."""
        # Try "#1 Team" pattern
        match = re.search(r"^#?(\d+)\s+(.+)$", team_text.strip())
        if match:
            return match.group(2).strip(), int(match.group(1))

        # Try "Team (1)" pattern
        match = re.search(r"^(.+?)\s*\((\d+)\)$", team_text.strip())
        if match:
            return match.group(1).strip(), int(match.group(2))

        return team_text.strip(), None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from various formats."""
        date_str = date_str.strip()
        formats = [
            "%m/%d/%Y",
            "%m/%d/%y",
            "%m-%d-%Y",
            "%m-%d-%y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def _create_team_from_game(
        self, team_id: str, team_name: str, division: str, season: str
    ) -> Team:
        """Create Team object from game data."""
        return Team(
            team_id=team_id,
            team_name=team_name,
            school_name=team_name,
            state=self.STATE_CODE,
            country="USA",
            level=TeamLevel.HIGH_SCHOOL_VARSITY,
            league=f"NIAA Division {division}",
            season=season,
            data_source=self.create_data_source_metadata(
                url=f"{self.base_url}/teams/{team_id}",
                quality_flag=DataQualityFlag.VERIFIED,
            ),
        )

    # Override base class methods

    async def _parse_json_data(self, json_data: Dict[str, Any], season: str) -> Dict[str, Any]:
        """Parse JSON data (not typically available for NIAA)."""
        self.logger.info("NIAA JSON parsing not implemented - using HTML/PDF")
        return {"teams": [], "games": [], "season": season}

    async def _parse_html_data(self, html: str, season: str) -> Dict[str, Any]:
        """Parse HTML data from NIAA brackets."""
        year = int(season.split("-")[1]) if "-" in season else int(season)
        if year < 100:
            year += 2000

        soup = parse_html(html)
        division = "5A"  # Default

        bracket_data = self._parse_bracket_html(soup, year, division, "Boys", "")

        return {
            "teams": bracket_data["teams"],
            "games": bracket_data["games"],
            "season": season,
        }

    # Required BaseDataSource methods

    async def get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID - NOT SUPPORTED."""
        self.logger.warning("NIAA does not provide player data - use SBLive for NV instead")
        return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[Player]:
        """Search for players - NOT SUPPORTED."""
        self.logger.warning("NIAA does not provide player data - use SBLive for NV instead")
        return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """Get player season statistics - NOT SUPPORTED."""
        self.logger.warning("NIAA does not provide player stats - use SBLive for NV instead")
        return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """Get player game statistics - NOT SUPPORTED."""
        self.logger.warning("NIAA does not provide player stats - use SBLive for NV instead")
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get team information."""
        season = "2024-25"
        brackets = await self.get_tournament_brackets(season=season)

        for team in brackets["teams"]:
            if team.team_id == team_id:
                return team

        self.logger.warning(f"Team not found in tournament brackets", team_id=team_id)
        return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        limit: int = 100,
    ) -> List[Game]:
        """Get games from tournament brackets."""
        brackets = await self.get_tournament_brackets(season=season)
        games = brackets["games"]

        # Apply filters
        if team_id:
            games = [g for g in games if team_id in [g.home_team_id, g.away_team_id]]

        if start_date:
            games = [g for g in games if g.game_date and g.game_date >= start_date]

        if end_date:
            games = [g for g in games if g.game_date and g.game_date <= end_date]

        return games[:limit]

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get statistical leaderboard - NOT SUPPORTED."""
        self.logger.warning("NIAA does not provide leaderboards - use SBLive for NV instead")
        return []
