"""
NEPSAC (New England Preparatory School Athletic Council) DataSource Adapter

Provides access to prep school basketball statistics across New England states.
Multi-state platform covering CT, MA, ME, NH, RI, VT preparatory schools.

Base URL: https://www.nepsac.org
"""

from datetime import datetime
from typing import Dict, List, Optional

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
    find_stat_table,
    parse_grad_year,
)
from ..base import BaseDataSource


class NEPSACDataSource(BaseDataSource):
    """
    New England Preparatory School Athletic Council data source adapter.

    Provides access to prep school basketball statistics across New England.
    Covers preparatory schools in 6 states.

    Supported States:
        - CT: Connecticut
        - MA: Massachusetts
        - ME: Maine
        - NH: New Hampshire
        - RI: Rhode Island
        - VT: Vermont

    Base URL: https://www.nepsac.org
    """

    source_type = DataSourceType.NEPSAC
    source_name = "NEPSAC"
    base_url = "https://www.nepsac.org"
    region = DataSourceRegion.US

    # Multi-state support
    SUPPORTED_STATES = ["CT", "MA", "ME", "NH", "RI", "VT"]

    # State full names for metadata
    STATE_NAMES = {
        "CT": "Connecticut",
        "MA": "Massachusetts",
        "ME": "Maine",
        "NH": "New Hampshire",
        "RI": "Rhode Island",
        "VT": "Vermont",
    }

    # NEPSAC divisions (Class A, B, C)
    DIVISIONS = ["A", "B", "C"]

    def __init__(self):
        """Initialize NEPSAC datasource with multi-state support."""
        super().__init__()

        # Build division-specific URL patterns
        # NEPSAC organizes by division rather than state
        self.division_urls = {
            division: f"{self.base_url}/basketball/boys/class-{division.lower()}"
            for division in self.DIVISIONS
        }

        self.logger.info(
            f"NEPSAC initialized with {len(self.SUPPORTED_STATES)} states, {len(self.DIVISIONS)} divisions",
            states=self.SUPPORTED_STATES,
            divisions=self.DIVISIONS,
        )

    def _validate_state(self, state: Optional[str]) -> str:
        """
        Validate and normalize state parameter.

        Args:
            state: State abbreviation (e.g., 'MA', 'CT')

        Returns:
            Uppercase state abbreviation

        Raises:
            ValueError: If state is not supported
        """
        if not state:
            # Default to MA (largest concentration of prep schools)
            return "MA"

        state = state.upper()
        if state not in self.SUPPORTED_STATES:
            raise ValueError(
                f"State '{state}' not supported. Supported states: {', '.join(self.SUPPORTED_STATES)}"
            )

        return state

    def _validate_division(self, division: Optional[str]) -> str:
        """
        Validate and normalize division parameter.

        Args:
            division: Division letter (A, B, or C)

        Returns:
            Uppercase division letter

        Raises:
            ValueError: If division is not valid
        """
        if not division:
            return "A"  # Default to Class A (top division)

        division = division.upper()
        if division not in self.DIVISIONS:
            raise ValueError(
                f"Division '{division}' not valid. Valid divisions: {', '.join(self.DIVISIONS)}"
            )

        return division

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        NEPSAC player IDs are formatted as: nepsac_{school}_{name}

        Args:
            player_id: Player identifier

        Returns:
            Player object or None
        """
        # Extract school and name from player_id
        parts = player_id.split("_")
        if len(parts) < 3 or parts[0] != "nepsac":
            self.logger.warning(f"Invalid NEPSAC player ID format", player_id=player_id)
            return None

        school = parts[1]
        name = "_".join(parts[2:])

        # Search for player in all divisions
        for division in self.DIVISIONS:
            players = await self.search_players(name=name, limit=50)
            for player in players:
                if player.player_id == player_id:
                    return player

        return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        state: Optional[str] = None,
        division: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in NEPSAC prep schools.

        Args:
            name: Player name (partial match)
            team: Team/school name (partial match)
            season: Season (e.g., '2024-25')
            state: Filter by state (CT, MA, ME, NH, RI, VT)
            division: Filter by division (A, B, C)
            limit: Maximum results

        Returns:
            List of Player objects
        """
        players: List[Player] = []

        # Validate optional filters
        if state:
            state = self._validate_state(state)

        if division:
            division = self._validate_division(division)
        else:
            division = "A"  # Default to Class A

        # Build URL for division rosters
        roster_url = f"{self.base_url}/basketball/boys/class-{division.lower()}/rosters"

        try:
            response = await self.http_client.get(roster_url)
            response.raise_for_status()

            soup = parse_html(response.text)

            # Find roster tables (one per school)
            tables = soup.find_all("table", class_=["roster", "players"])

            for table in tables:
                # Extract school name from table header or caption
                school_elem = table.find_previous(["h3", "h4", "caption"])
                school_name = get_text_or_none(school_elem) if school_elem else "Unknown"

                # Parse player rows
                rows = table.find_all("tr")[1:]  # Skip header

                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue

                    player = self._parse_player_from_roster_row(
                        cells, school_name, division, season
                    )
                    if player:
                        # Apply filters
                        if name and name.lower() not in player.name.lower():
                            continue
                        if team and team.lower() not in school_name.lower():
                            continue
                        if state and player.state != state:
                            continue

                        players.append(player)

                        if len(players) >= limit:
                            break

                if len(players) >= limit:
                    break

            self.logger.info(
                f"Found {len(players)} NEPSAC players",
                division=division,
                state=state,
                limit=limit,
            )

        except Exception as e:
            self.logger.error(f"Error searching NEPSAC players", error=str(e))

        return players[:limit]

    def _parse_player_from_roster_row(
        self,
        cells: List,
        school: str,
        division: str,
        season: Optional[str],
    ) -> Optional[Player]:
        """
        Parse player from roster table row.

        Typical NEPSAC roster format:
        [Name, Year, Height, Position]

        Args:
            cells: Table cells
            school: School name
            division: Division (A, B, C)
            season: Season

        Returns:
            Player object or None
        """
        try:
            if len(cells) < 2:
                return None

            # Extract player name (usually first column)
            name = clean_player_name(get_text_or_none(cells[0]) or "")
            if not name:
                return None

            # Extract graduation year (usually second column)
            year_text = get_text_or_none(cells[1]) if len(cells) > 1 else None
            grad_year = parse_grad_year(year_text) if year_text else None

            # Extract height (usually third column)
            height_text = get_text_or_none(cells[2]) if len(cells) > 2 else None
            height_inches = None
            if height_text and "-" in height_text:
                parts = height_text.split("-")
                if len(parts) == 2:
                    feet = parse_int(parts[0])
                    inches = parse_int(parts[1])
                    if feet and inches:
                        height_inches = feet * 12 + inches

            # Extract position (usually fourth column)
            position_text = get_text_or_none(cells[3]) if len(cells) > 3 else None
            position = self._parse_position(position_text)

            # Generate player ID
            player_id = f"nepsac_{school.lower().replace(' ', '_')}_{name.lower().replace(' ', '_')}"

            return Player(
                player_id=player_id,
                name=name,
                school=school,
                level=PlayerLevel.PREP,
                position=position,
                height_inches=height_inches,
                graduation_year=grad_year,
                season=season,
                conference=f"NEPSAC Class {division}",
                data_source=self.create_data_source_metadata(
                    url=f"{self.base_url}/basketball",
                    quality_flag=DataQualityFlag.VERIFIED,
                ),
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse NEPSAC player from row", error=str(e))
            return None

    def _parse_position(self, position_text: Optional[str]) -> Optional[Position]:
        """Parse position from text."""
        if not position_text:
            return None

        position_text = position_text.upper().strip()

        # Map common position abbreviations
        position_map = {
            "PG": Position.PG,
            "SG": Position.SG,
            "G": Position.G,
            "SF": Position.SF,
            "PF": Position.PF,
            "F": Position.F,
            "C": Position.C,
        }

        return position_map.get(position_text)

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics.

        Note: NEPSAC typically does not publish detailed season statistics publicly.
        This returns None unless stats are available for specific divisions/schools.

        Args:
            player_id: Player identifier
            season: Season (None = current season)

        Returns:
            PlayerSeasonStats or None
        """
        self.logger.warning(
            f"NEPSAC does not typically provide public season statistics",
            player_id=player_id,
        )
        return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game statistics.

        Note: NEPSAC typically does not publish detailed game statistics publicly.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            PlayerGameStats or None
        """
        self.logger.warning(
            f"NEPSAC does not typically provide public game statistics",
            player_id=player_id,
        )
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team by ID.

        Args:
            team_id: Team identifier (e.g., 'nepsac_tilton_school')

        Returns:
            Team object or None
        """
        # Parse team_id to extract school name and division
        parts = team_id.split("_")
        if len(parts) < 2 or parts[0] != "nepsac":
            self.logger.warning(f"Invalid NEPSAC team ID format", team_id=team_id)
            return None

        school_name = " ".join(parts[1:]).title()

        # Search for team in divisions
        for division in self.DIVISIONS:
            standings_url = f"{self.base_url}/basketball/boys/class-{division.lower()}/standings"

            try:
                response = await self.http_client.get(standings_url)
                response.raise_for_status()

                soup = parse_html(response.text)
                tables = soup.find_all("table", class_=["standings", "teams"])

                for table in tables:
                    rows = table.find_all("tr")[1:]  # Skip header

                    for row in rows:
                        cells = row.find_all(["td", "th"])
                        if len(cells) < 2:
                            continue

                        team_name = get_text_or_none(cells[0])
                        if team_name and school_name.lower() in team_name.lower():
                            return self._parse_team_from_standings_row(cells, division)

            except Exception as e:
                self.logger.debug(f"Error checking division {division}", error=str(e))
                continue

        return None

    def _parse_team_from_standings_row(
        self, cells: List, division: str
    ) -> Optional[Team]:
        """Parse team from standings table row."""
        try:
            if len(cells) < 2:
                return None

            team_name = get_text_or_none(cells[0])
            if not team_name:
                return None

            # Parse record (usually second column)
            record_text = get_text_or_none(cells[1]) if len(cells) > 1 else None
            wins, losses = parse_record(record_text) if record_text else (None, None)

            team_id = f"nepsac_{team_name.lower().replace(' ', '_')}"

            return Team(
                team_id=team_id,
                name=team_name,
                school=team_name,
                level=TeamLevel.PREP,
                conference=f"NEPSAC Class {division}",
                wins=wins,
                losses=losses,
                data_source=self.create_data_source_metadata(
                    url=f"{self.base_url}/basketball",
                    quality_flag=DataQualityFlag.VERIFIED,
                ),
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse NEPSAC team from row", error=str(e))
            return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        division: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games with optional filters.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            division: Filter by division (A, B, C)
            limit: Maximum results

        Returns:
            List of Game objects
        """
        games: List[Game] = []

        if division:
            division = self._validate_division(division)
        else:
            division = "A"

        schedule_url = f"{self.base_url}/basketball/boys/class-{division.lower()}/schedule"

        try:
            response = await self.http_client.get(schedule_url)
            response.raise_for_status()

            soup = parse_html(response.text)
            tables = soup.find_all("table", class_=["schedule", "games"])

            for table in tables:
                rows = table.find_all("tr")[1:]  # Skip header

                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 3:
                        continue

                    game = self._parse_game_from_schedule_row(cells, division, season)
                    if game:
                        # Apply filters
                        if team_id and (
                            game.home_team_id != team_id and game.away_team_id != team_id
                        ):
                            continue
                        if start_date and game.game_date and game.game_date < start_date:
                            continue
                        if end_date and game.game_date and game.game_date > end_date:
                            continue

                        games.append(game)

                        if len(games) >= limit:
                            break

                if len(games) >= limit:
                    break

        except Exception as e:
            self.logger.error(f"Error fetching NEPSAC games", error=str(e))

        return games[:limit]

    def _parse_game_from_schedule_row(
        self, cells: List, division: str, season: Optional[str]
    ) -> Optional[Game]:
        """Parse game from schedule table row."""
        try:
            if len(cells) < 3:
                return None

            # Typical format: [Date, Home, Away, Score/Time]
            date_text = get_text_or_none(cells[0])
            home_team = get_text_or_none(cells[1])
            away_team = get_text_or_none(cells[2])

            if not home_team or not away_team:
                return None

            # Parse date
            game_date = None
            if date_text:
                try:
                    game_date = datetime.strptime(date_text.strip(), "%m/%d/%Y")
                except Exception:
                    pass

            # Parse score if available
            score_text = get_text_or_none(cells[3]) if len(cells) > 3 else None
            home_score = None
            away_score = None
            status = GameStatus.SCHEDULED

            if score_text and "-" in score_text:
                parts = score_text.split("-")
                if len(parts) == 2:
                    home_score = parse_int(parts[0].strip())
                    away_score = parse_int(parts[1].strip())
                    status = GameStatus.COMPLETED if home_score is not None else GameStatus.SCHEDULED

            game_id = f"nepsac_{home_team.lower().replace(' ', '_')}_{away_team.lower().replace(' ', '_')}"

            return Game(
                game_id=game_id,
                home_team_name=home_team,
                away_team_name=away_team,
                home_team_id=f"nepsac_{home_team.lower().replace(' ', '_')}",
                away_team_id=f"nepsac_{away_team.lower().replace(' ', '_')}",
                game_date=game_date,
                game_type=GameType.REGULAR_SEASON,
                status=status,
                home_score=home_score,
                away_score=away_score,
                season=season,
                conference=f"NEPSAC Class {division}",
                data_source=self.create_data_source_metadata(
                    url=f"{self.base_url}/basketball",
                    quality_flag=DataQualityFlag.VERIFIED,
                ),
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse NEPSAC game from row", error=str(e))
            return None

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        division: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        Note: NEPSAC typically does not publish public statistical leaderboards.

        Args:
            stat: Stat category
            season: Season filter
            division: Division filter (A, B, C)
            limit: Maximum results

        Returns:
            List of leaderboard entries (empty for NEPSAC)
        """
        self.logger.warning(
            f"NEPSAC does not typically provide public statistical leaderboards"
        )
        return []
