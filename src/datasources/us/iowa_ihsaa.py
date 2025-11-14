"""
IHSAA (Iowa High School Athletic Association) DataSource Adapter

Provides authoritative tournament brackets, seeds, scores, and championship results
for Iowa high school basketball. This is the OFFICIAL source for postseason data.

**Data Authority**: IHSAA is the source of truth for:
- Tournament brackets (4 classes: 1A, 2A, 3A, 4A)
- Game box scores (team + player statistics)
- Tournament schedules and locations
- Final scores and champions
- Historical tournament data (2015-present, estimated)

**Base URL**: https://www.iahsaa.org

**URL Patterns**:
```
Tournament Central: /basketball/state-tournament-central
Box Scores: /wp-content/uploads/{year}/03/{class}{number}.htm
Live Stats: https://stats.iahsaa.org/basketball/
```

**Coverage**:
- Classes: 1A (smallest), 2A, 3A, 4A (largest) - Based on school enrollment
- Years: 2015-present (estimated, needs validation)
- Boys tournament (Girls TBD)
- Tournament games only (no regular season)

**Iowa Basketball Context**:
- 327,000 population (30th largest US state)
- Historic basketball culture: Kirk Hinrich, Harrison Barnes, Doug McDermott
- Strong tradition of state tournament at Wells Fargo Arena, Des Moines
- Tournament held annually in early-mid March

**Limitations**:
- **Regular season data NOT available** (Bound.com blocked - 403 Forbidden)
- **Player search NOT available** (no aggregated leaderboards)
- **Tournament games only** (~32-64 games per year)
- Box scores only available for state tournament games

**Data Sources**:
1. **iahsaa.org/basketball/state-tournament-central** - Brackets, schedules, results
2. **stats.iahsaa.org/basketball/** - Live game statistics (legacy HTML platform)
3. **Bound.com** - Blocked (official stats platform with bot protection)

**Recommended Use**: IHSAA provides official tournament lineage and brackets.
For regular season data and player stats, consider alternative sources if available.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import re

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
    parse_float,
)
from ..base_association import AssociationAdapterBase


class IowaIHSAADataSource(AssociationAdapterBase):
    """
    Iowa High School Athletic Association (IHSAA) data source adapter.

    **PRIMARY PURPOSE**: Authoritative tournament bracket and postseason results.

    This adapter provides:
    1. Tournament brackets for all classes (1A-4A)
    2. Game box scores with team and player statistics
    3. Tournament schedules, dates, locations
    4. Historical tournament data (2015-present, estimated)

    **ARCHITECTURE**:
    - Inherits from AssociationAdapterBase for JSON-first discovery + HTML fallback
    - Parses tournament central page to discover bracket links
    - Fetches box score HTML files for game statistics
    - Generates unique game IDs: ihsaa_ia:{year}:{class}:{round}:{home}@{away}

    **DATA QUALITY**: HIGH (official source, authoritative)

    **LIMITATIONS**:
    - No player-level search (must extract from game rosters)
    - No regular season schedules (Bound.com blocked)
    - Tournament-focused, not stats-focused
    - Off-season data availability depends on archiving
    """

    source_type = DataSourceType.IHSAA_IA
    source_name = "Iowa IHSAA"
    base_url = "https://www.iahsaa.org"
    stats_url = "https://stats.iahsaa.org/basketball"
    region = DataSourceRegion.US_IA

    # IHSAA-specific constants
    CLASSES = ["1A", "2A", "3A", "4A"]  # 1A = smallest, 4A = largest
    GENDERS = ["Boys"]  # Girls TBD (may use separate website structure)
    MIN_YEAR = 2015  # Historical data availability (estimated, needs validation)
    STATE_CODE = "IA"
    STATE_NAME = "Iowa"

    def __init__(self):
        """Initialize IHSAA datasource with Iowa-specific configuration."""
        super().__init__()
        self.logger.info(
            "Iowa IHSAA initialized",
            classes=len(self.CLASSES),
            genders=len(self.GENDERS),
            min_year=self.MIN_YEAR,
        )

    def _get_season_url(self, season: str) -> str:
        """
        Get URL for Iowa basketball season data.

        IHSAA tournament data is accessed through tournament central page.
        Season "2024-25" → year 2025 (tournament year).

        Args:
            season: Season string (e.g., "2024-25")

        Returns:
            URL to tournament central page
        """
        # Extract tournament year from season
        year = int(season.split("-")[1]) if "-" in season else int(season)
        if year < 100:  # Handle 2-digit year (e.g., "25")
            year += 2000

        # Iowa IHSAA uses tournament central page for all bracket access
        return f"{self.base_url}/basketball/state-tournament-central"

    def _build_box_score_url(self, year: int, class_name: str, game_number: int) -> str:
        """
        Build URL for specific game box score HTML file.

        **URL Format**:
        ```
        /wp-content/uploads/{year}/03/{class}{number}.htm

        Examples:
        /wp-content/uploads/2025/03/4A1.htm  (Class 4A, game #1)
        /wp-content/uploads/2024/03/1A5.htm  (Class 1A, game #5)
        ```

        Args:
            year: Tournament year (e.g., 2025)
            class_name: Class name (1A, 2A, 3A, 4A)
            game_number: Game number within class bracket

        Returns:
            Full box score URL
        """
        # Box scores uploaded to WordPress media directory
        # Format: /wp-content/uploads/YYYY/03/ClassNumber.htm
        # Month is always 03 (March - tournament month)
        return f"{self.base_url}/wp-content/uploads/{year}/03/{class_name}{game_number}.htm"

    async def get_tournament_brackets(
        self, season: Optional[str] = None, class_name: Optional[str] = None, gender: str = "Boys"
    ) -> Dict[str, Any]:
        """
        Get tournament brackets for a season.

        **STRATEGY**:
        - Fetch tournament central page
        - Extract bracket results and matchups
        - Parse game information (teams, scores, dates)
        - Optionally fetch detailed box scores

        Args:
            season: Season string (e.g., "2024-25"), None for current
            class_name: Specific class (1A, 2A, 3A, 4A), None for all
            gender: "Boys" (Girls not yet supported)

        Returns:
            Dict with keys:
                - games: List[Game] - all tournament games
                - teams: List[Team] - all participating teams
                - brackets: Dict[str, List[Game]] - games grouped by class
                - metadata: bracket metadata (year, venue, dates)
        """
        # Determine year
        if season:
            year = int(season.split("-")[1]) if "-" in season else int(season)
            if year < 100:
                year += 2000
        else:
            year = datetime.now().year

        # Gender validation
        if gender not in self.GENDERS:
            self.logger.warning(
                f"Gender '{gender}' not supported, defaulting to Boys",
                gender=gender,
                supported=self.GENDERS,
            )
            gender = "Boys"

        # Determine classes to fetch
        classes = [class_name] if class_name else self.CLASSES

        self.logger.info(
            f"Fetching Iowa IHSAA tournament brackets",
            year=year,
            classes=classes,
            gender=gender,
        )

        # Fetch tournament central page
        tournament_url = self._get_season_url(f"{year-1}-{str(year)[-2:]}")
        try:
            html = await self.http_client.get_text(tournament_url, cache_ttl=7200)  # 2-hour cache
            soup = parse_html(html)
        except Exception as e:
            self.logger.error(
                f"Failed to fetch tournament central page",
                url=tournament_url,
                error=str(e),
            )
            return {
                "games": [],
                "teams": [],
                "brackets": {},
                "metadata": {},
                "year": year,
                "gender": gender,
            }

        # Parse tournament data
        all_games: List[Game] = []
        all_teams: Dict[str, Team] = {}  # Deduplicate by team_id
        brackets: Dict[str, List[Game]] = {}
        metadata: Dict[str, Any] = {}

        # Parse tournament central page for bracket structure
        tournament_data = self._parse_tournament_central(soup, year, classes, gender)

        # Collect games and teams
        for class_name in classes:
            bracket_key = f"class_{class_name.lower()}"
            class_data = tournament_data.get(bracket_key, {})

            for game in class_data.get("games", []):
                all_games.append(game)
                brackets.setdefault(bracket_key, []).append(game)

            for team in class_data.get("teams", []):
                all_teams[team.team_id] = team

            if class_data.get("metadata"):
                metadata[bracket_key] = class_data["metadata"]

            self.logger.info(
                f"Parsed bracket",
                class_name=class_name,
                games=len(class_data.get("games", [])),
                teams=len(class_data.get("teams", [])),
            )

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

    def _parse_tournament_central(
        self, soup, year: int, classes: List[str], gender: str
    ) -> Dict[str, Any]:
        """
        Parse tournament central page to extract bracket structure.

        **Tournament Central Structure**:
        - Contains championship results for all classifications
        - Game results typically in text format: "Team A 65, Team B 58"
        - Round information: Quarterfinals, Semifinals, Championships
        - Dates and locations listed

        **Parsing Strategy**:
        1. Find sections for each classification (1A, 2A, 3A, 4A)
        2. Extract game results (team names and scores)
        3. Identify rounds (QF, SF, Final)
        4. Build game objects

        Args:
            soup: BeautifulSoup parsed HTML
            year: Tournament year
            classes: List of classes to parse
            gender: Boys or Girls

        Returns:
            Dict with class_name keys containing games, teams, metadata
        """
        result = {}

        # Look for classification sections in tournament results
        # Iowa IHSAA typically displays results in text format with headers
        # Example: "Class 4A Championship: Team A 65, Team B 58"

        for class_name in classes:
            games: List[Game] = []
            teams: Dict[str, Team] = {}
            metadata: Dict[str, Any] = {
                "class": class_name,
                "year": year,
                "venue": "Wells Fargo Arena, Des Moines",
            }

            # Find all text mentioning this classification
            class_pattern = re.compile(rf"Class\s+{class_name}", re.IGNORECASE)
            class_sections = soup.find_all(text=class_pattern)

            for section in class_sections:
                # Try to parse game results from surrounding context
                parent = section.parent if section.parent else soup

                # Look for score patterns: "Team A 65, Team B 58" or "Team A def. Team B"
                # This is a simplified parser - may need enhancement based on actual HTML structure
                text_content = parent.get_text() if parent else ""

                # Extract game information using regex
                # Pattern: Team Name Score, Team Name Score
                score_pattern = re.compile(r"([A-Za-z\s\.]+)\s+(\d+),\s+([A-Za-z\s\.]+)\s+(\d+)")
                matches = score_pattern.findall(text_content)

                for match in matches:
                    team1_name, score1, team2_name, score2 = match
                    team1_name = team1_name.strip()
                    team2_name = team2_name.strip()

                    # Create team objects
                    team1_id = f"ihsaa_ia:{year}:{self._slugify(team1_name)}"
                    team2_id = f"ihsaa_ia:{year}:{self._slugify(team2_name)}"

                    if team1_id not in teams:
                        teams[team1_id] = self._create_team(team1_id, team1_name, class_name, f"{year-1}-{str(year)[-2:]}")

                    if team2_id not in teams:
                        teams[team2_id] = self._create_team(team2_id, team2_name, class_name, f"{year-1}-{str(year)[-2:]}")

                    # Create game object
                    game_id = f"ihsaa_ia:{year}:{class_name.lower()}:{self._slugify(team1_name)}_vs_{self._slugify(team2_name)}"

                    game = Game(
                        game_id=game_id,
                        date=f"{year}-03-15",  # Approximate - tournament typically mid-March
                        home_team_id=team1_id,
                        home_team_name=team1_name,
                        home_team_score=parse_int(score1),
                        away_team_id=team2_id,
                        away_team_name=team2_name,
                        away_team_score=parse_int(score2),
                        status=GameStatus.FINAL,
                        game_type=GameType.TOURNAMENT,
                        location="Wells Fargo Arena, Des Moines, IA",
                        season=f"{year-1}-{str(year)[-2:]}",
                        source=self.source_name,
                        data_quality_flags=[],
                    )

                    games.append(game)

            result[f"class_{class_name.lower()}"] = {
                "games": games,
                "teams": list(teams.values()),
                "metadata": metadata,
            }

        return result

    async def get_game_stats(self, game_id: str, year: int, class_name: str, game_number: int) -> Dict[str, Any]:
        """
        Fetch detailed game statistics from box score HTML file.

        **Box Score Structure**:
        - Team statistics: FG, 3PT, FT, REB, AST, TO, PF, PTS
        - Individual player statistics
        - Shooting percentages
        - Play-by-play data (optional)

        Args:
            game_id: Unique game identifier
            year: Tournament year
            class_name: Classification (1A-4A)
            game_number: Game number within bracket

        Returns:
            Dict with game statistics, player stats, team stats
        """
        url = self._build_box_score_url(year, class_name, game_number)

        try:
            html = await self.http_client.get_text(url, cache_ttl=86400)  # 24-hour cache (static data)
            soup = parse_html(html)
        except Exception as e:
            self.logger.warning(
                f"Failed to fetch box score",
                game_id=game_id,
                url=url,
                error=str(e),
            )
            return {}

        # Parse box score HTML
        return self._parse_box_score_html(soup, game_id, year, class_name)

    def _parse_box_score_html(self, soup, game_id: str, year: int, class_name: str) -> Dict[str, Any]:
        """
        Parse box score HTML to extract game and player statistics.

        **Box Score Format**:
        Iowa IHSAA uses legacy HTML tables with team and player stats.

        Args:
            soup: BeautifulSoup parsed HTML
            game_id: Game identifier
            year: Tournament year
            class_name: Classification

        Returns:
            Dict with team_stats, player_stats, game_info
        """
        # Find all tables (typically separate tables for each team)
        tables = soup.find_all("table")

        team_stats = []
        player_stats = []

        for table in tables:
            # Extract table data
            data = extract_table_data(table)

            if not data or len(data) < 2:
                continue

            headers = data[0]
            rows = data[1:]

            # Check if this is a player stats table (has Player/Name column)
            if any("player" in str(h).lower() or "name" in str(h).lower() for h in headers):
                # Parse player statistics
                for row in rows:
                    if len(row) < 2:
                        continue

                    player_name = str(row[0]).strip()
                    if not player_name or player_name.lower() in ["totals", "team", ""]:
                        continue

                    # Extract stats (varies by box score format)
                    # Common columns: Player, FG, 3PT, FT, REB, AST, PF, PTS
                    player_stat = {
                        "player_name": player_name,
                        "game_id": game_id,
                    }

                    # Try to map columns to stats
                    for i, header in enumerate(headers):
                        if i < len(row):
                            col_name = str(header).strip().lower()
                            value = row[i]

                            if "fg" in col_name and "3" not in col_name:
                                player_stat["fg"] = str(value)
                            elif "3pt" in col_name or "3p" in col_name:
                                player_stat["three_pt"] = str(value)
                            elif "ft" in col_name:
                                player_stat["ft"] = str(value)
                            elif "reb" in col_name:
                                player_stat["reb"] = parse_int(value)
                            elif "ast" in col_name:
                                player_stat["ast"] = parse_int(value)
                            elif "stl" in col_name or "steal" in col_name:
                                player_stat["stl"] = parse_int(value)
                            elif "blk" in col_name or "block" in col_name:
                                player_stat["blk"] = parse_int(value)
                            elif "to" in col_name or "turnover" in col_name:
                                player_stat["to"] = parse_int(value)
                            elif "pf" in col_name or "foul" in col_name:
                                player_stat["pf"] = parse_int(value)
                            elif "pts" in col_name or "point" in col_name:
                                player_stat["pts"] = parse_int(value)

                    player_stats.append(player_stat)

        return {
            "game_id": game_id,
            "team_stats": team_stats,
            "player_stats": player_stats,
            "year": year,
            "class": class_name,
        }

    def _create_team(self, team_id: str, team_name: str, class_name: str, season: str) -> Team:
        """
        Create Team object from tournament data.

        Args:
            team_id: Unique team identifier
            team_name: Team/school name
            class_name: Classification (1A-4A)
            season: Season string

        Returns:
            Team object
        """
        return Team(
            team_id=team_id,
            team_name=team_name,
            school_name=team_name,  # Typically same for high school
            level=TeamLevel.HIGH_SCHOOL_VARSITY,
            state=self.STATE_CODE,
            country="USA",
            league=f"IHSAA Class {class_name}",
            season=season,
            data_source=self.create_data_source_metadata(
                url=f"{self.base_url}/teams/{team_id}",
                quality_flag=DataQualityFlag.VERIFIED,
            ),
        )

    def _slugify(self, text: str) -> str:
        """
        Convert text to URL-safe slug.

        Args:
            text: Text to slugify

        Returns:
            Slugified text (lowercase, spaces to underscores, alphanumeric only)
        """
        # Convert to lowercase
        text = text.lower()
        # Replace spaces with underscores
        text = re.sub(r"\s+", "_", text)
        # Remove non-alphanumeric characters
        text = re.sub(r"[^a-z0-9_]", "", text)
        return text

    # BaseDataSource required method implementations

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        limit: int = 50,
        **filters,
    ) -> List[Player]:
        """
        Search for players (NOT SUPPORTED).

        Iowa IHSAA does not provide player search capability.
        Player data can only be extracted from game box scores.

        Raises:
            NotImplementedError: Always raised
        """
        raise NotImplementedError(
            f"{self.source_name} does not support player search. "
            f"Player data can be extracted from game box scores only."
        )

    async def get_games(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        team_id: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 100,
    ) -> List[Game]:
        """
        Get tournament games (limited to state tournament).

        Args:
            start_date: Not used (tournament has fixed dates)
            end_date: Not used (tournament has fixed dates)
            team_id: Optional team filter
            season: Season string (e.g., "2024-25")
            limit: Maximum games to return

        Returns:
            List of tournament games
        """
        # Get tournament brackets for season
        brackets = await self.get_tournament_brackets(season=season)
        games = brackets.get("games", [])

        # Filter by team if specified
        if team_id:
            games = [
                g for g in games
                if g.home_team_id == team_id or g.away_team_id == team_id
            ]

        # Apply limit
        return games[:limit]

    async def get_leaderboard(
        self, stat: str, season: Optional[str] = None, limit: int = 50, **filters
    ) -> List[Dict[str, Any]]:
        """
        Get stat leaderboard (NOT SUPPORTED).

        Iowa IHSAA does not provide aggregated leaderboards.

        Raises:
            NotImplementedError: Always raised
        """
        raise NotImplementedError(
            f"{self.source_name} does not provide stat leaderboards. "
            f"Only per-game statistics are available from box scores."
        )

    # Abstract method implementations required by AssociationAdapterBase

    async def _parse_json_data(self, json_data: Dict[str, Any], season: str) -> Dict[str, Any]:
        """
        Parse JSON data from association (if available).

        Iowa IHSAA tournament central is HTML-only (no JSON endpoints discovered).

        Args:
            json_data: JSON data
            season: Season string

        Returns:
            Empty dict (not implemented)
        """
        self.logger.warning("Iowa IHSAA does not provide JSON endpoints")
        return {}

    async def _parse_html_data(self, html: str, season: str) -> Dict[str, Any]:
        """
        Parse HTML data from tournament central page.

        Args:
            html: HTML content
            season: Season string

        Returns:
            Dict with tournament data
        """
        soup = parse_html(html)

        # Extract year from season
        year = int(season.split("-")[1]) if "-" in season else int(season)
        if year < 100:
            year += 2000

        # Parse tournament data
        return self._parse_tournament_central(soup, year, self.CLASSES, "Boys")
