"""
Wisconsin Sports Network (WSN / WisSports) DataSource Adapter

⚠️  WARNING - ADAPTER INACTIVE ⚠️
WSN (wissports.net) is a SPORTS NEWS website, NOT a statistics database.
Investigation (Phase 12.2) confirmed:
- Website EXISTS and is active (40k+ chars)
- Contains basketball NEWS articles
- Has NO statistics pages (all /basketball/* URLs return 404)
- Never had player/team stats - wrong site type for this adapter

Alternative Wisconsin Sources:
- WIAA (wiaa.com) - Official state association
- MaxPreps Wisconsin
- SBLive Wisconsin

See: PHASE_12_2_WSN_INVESTIGATION.md for full investigation details
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
    parse_height_to_inches,
    parse_html,
    parse_int,
    parse_record,
)
from ...utils.scraping_helpers import (
    build_leaderboard_entry,
    find_stat_table,
    parse_grad_year,
    parse_player_from_row,
    parse_season_stats_from_row,
)
from ..base import BaseDataSource


class WSNDataSource(BaseDataSource):
    """
    Wisconsin Sports Network (WSN / WisSports) data source adapter.

    ⚠️  ADAPTER STATUS: INACTIVE - NOT A STATS SITE ⚠️

    Investigation (Phase 12.2, 2025-11-12) found that wissports.net is a SPORTS NEWS
    website, not a statistics database. All basketball stats URLs return 404.

    Original intent: Access Wisconsin high school basketball statistics
    Actual website: Sports news articles, no player/team stats pages

    Recommendation: Use alternative Wisconsin sources:
    - WIAA (wiaa.com) - Official Wisconsin Interscholastic Athletic Association
    - MaxPreps Wisconsin coverage
    - SBLive Wisconsin section

    See PHASE_12_2_WSN_INVESTIGATION.md for full investigation details.
    """

    source_type = DataSourceType.WSN
    source_name = "Wisconsin Sports Network"
    base_url = "https://www.wissports.net"
    region = DataSourceRegion.US

    def __init__(self):
        """
        Initialize Wisconsin Sports Network datasource.

        IMPLEMENTATION STEPS:
        1. Call parent __init__
        2. Define WSN-specific endpoint URLs
        3. Set up Wisconsin-specific configurations
        """
        super().__init__()

        # WSN-specific endpoints
        self.stats_url = f"{self.base_url}/stats/basketball"
        self.players_url = f"{self.base_url}/players/basketball"
        self.teams_url = f"{self.base_url}/teams/basketball"
        self.schedule_url = f"{self.base_url}/schedule/basketball"
        self.leaders_url = f"{self.base_url}/leaders/basketball"
        self.standings_url = f"{self.base_url}/standings/basketball"

        # Wisconsin-specific state code
        self.state_code = "WI"
        self.league_name = "Wisconsin High School"
        self.league_abbrev = "WIAA"  # Wisconsin Interscholastic Athletic Association

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        IMPLEMENTATION STEPS:
        1. Try to construct player profile URL
        2. Fetch and parse player profile page
        3. Extract player demographics (name, school, position, height, grad year)
        4. Fall back to search_players if profile page not available
        5. Return Player object with Wisconsin location data

        Args:
            player_id: Player identifier (format: wsn_firstname_lastname)

        Returns:
            Player object or None if not found
        """
        try:
            # Try direct profile page
            profile_url = f"{self.players_url}/{player_id}"

            html = await self.http_client.get_text(profile_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find player info section
            player_info = soup.find("div", class_=lambda x: x and "player-info" in str(x).lower())
            if player_info:
                return self._parse_player_from_profile(soup, player_id, profile_url)

            # Fall back to search
            player_name = player_id.replace("wsn_", "").replace("_", " ").title()
            players = await self.search_players(name=player_name, limit=1)
            return players[0] if players else None

        except Exception as e:
            self.logger.error(f"Failed to get player", player_id=player_id, error=str(e))

            # Try fallback to search
            try:
                player_name = player_id.replace("wsn_", "").replace("_", " ").title()
                players = await self.search_players(name=player_name, limit=1)
                return players[0] if players else None
            except Exception:
                return None

    def _parse_player_from_profile(self, soup, player_id: str, url: str) -> Optional[Player]:
        """
        Parse player from profile page.

        IMPLEMENTATION STEPS:
        1. Extract player name from h1/h2 header
        2. Extract demographics from info fields (height, position, class, school)
        3. Parse grad year from class
        4. Auto-add school_state="WI", school_country="USA"
        5. Create Player object with complete data
        """
        try:
            # Extract player name
            name_elem = soup.find(
                ["h1", "h2"],
                class_=lambda x: x and ("player-name" in str(x).lower() or "name" in str(x).lower())
            )
            full_name = get_text_or_none(name_elem) if name_elem else ""

            if not full_name:
                # Try alternative selectors
                name_elem = soup.find("h1") or soup.find("h2")
                full_name = get_text_or_none(name_elem) if name_elem else ""

            if not full_name:
                return None

            # Clean name
            full_name = clean_player_name(full_name)

            # Split name
            name_parts = full_name.split()
            first_name = name_parts[0] if len(name_parts) > 0 else full_name
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            # Find info fields
            info_fields = soup.find_all(
                ["div", "span", "p", "td"],
                class_=lambda x: x and ("info" in str(x).lower() or "detail" in str(x).lower())
            )

            height = None
            position = None
            grad_year = None
            school = None
            team = None
            jersey_number = None

            # Also check for table-based layouts (common in Wisconsin sites)
            info_table = soup.find("table", class_=lambda x: x and "info" in str(x).lower())
            if info_table:
                rows = extract_table_data(info_table)
                for row in rows:
                    for key, value in row.items():
                        text = f"{key}: {value}"
                        info_fields.append(type('obj', (object,), {'get_text': lambda: text})())

            for field in info_fields:
                text = get_text_or_none(field)
                if not text:
                    continue

                text_lower = text.lower()

                # Parse different field types
                if "height" in text_lower or "'" in text or '"' in text:
                    height = parse_height_to_inches(text)
                elif "position" in text_lower or "pos" in text_lower:
                    # Extract position value
                    pos_text = text.split(":")[-1].strip().upper()
                    try:
                        if pos_text in ["PG", "SG", "SF", "PF", "C", "G", "F"]:
                            position = Position(pos_text)
                    except ValueError:
                        pass
                elif "class" in text_lower or "grade" in text_lower or "year" in text_lower:
                    # Grad year like '25, 2025, Sr, Junior, etc.
                    year_part = text.split(":")[-1].strip()
                    grad_year = parse_grad_year(year_part)
                elif "school" in text_lower:
                    school = text.replace("School:", "").replace("school:", "").strip()
                elif "team" in text_lower and "opponent" not in text_lower:
                    team = text.replace("Team:", "").replace("team:", "").strip()
                elif "jersey" in text_lower or "number" in text_lower or text.strip().startswith("#"):
                    number_text = text.replace("#", "").replace("Jersey:", "").strip()
                    jersey_number = parse_int(number_text)

            data_source = self.create_data_source_metadata(
                url=url, quality_flag=DataQualityFlag.COMPLETE
            )

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name,
                "height_inches": height,
                "position": position,
                "jersey_number": jersey_number,
                "grad_year": grad_year,
                "school_name": school or team,
                "school_state": self.state_code,
                "school_country": "USA",
                "team_name": team or school,
                "level": PlayerLevel.HIGH_SCHOOL,
                "profile_url": url,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Player, player_data, f"player {full_name}")

        except Exception as e:
            self.logger.error("Failed to parse player profile", error=str(e))
            return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in Wisconsin.

        IMPLEMENTATION STEPS:
        1. Fetch stats/leaders page containing player listings
        2. Find stats table using find_stat_table()
        3. Parse each row into Player object
        4. Auto-add school_state="WI", school_country="USA"
        5. Apply name and team filters
        6. Return up to limit results

        Args:
            name: Player name (partial match)
            team: Team/school name (partial match)
            season: Season filter (e.g., "2024-25")
            limit: Maximum results to return

        Returns:
            List of Player objects matching filters
        """
        try:
            # Get stats page which lists players
            html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find stats table
            stats_table = find_stat_table(soup, table_class_hint="stats")
            if not stats_table:
                # Try alternative approach
                stats_table = soup.find("table")

            if not stats_table:
                self.logger.warning("No stats table found")
                return []

            rows = extract_table_data(stats_table)
            players = []

            data_source = self.create_data_source_metadata(
                url=self.stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            for row in rows[:limit * 2]:  # Get more for filtering
                player = self._parse_player_from_stats_row(row, data_source)
                if not player:
                    continue

                # Apply filters
                if name and name.lower() not in player.full_name.lower():
                    continue
                if team and player.school_name and team.lower() not in player.school_name.lower():
                    continue

                players.append(player)

                if len(players) >= limit:
                    break

            self.logger.info(f"Found {len(players)} Wisconsin players")
            return players

        except Exception as e:
            self.logger.error("Failed to search players", error=str(e))
            return []

    def _parse_player_from_stats_row(self, row: dict, data_source) -> Optional[Player]:
        """
        Parse player from stats table row.

        IMPLEMENTATION STEPS:
        1. Use parse_player_from_row() helper
        2. Add Wisconsin-specific fields (state, country)
        3. Parse WIAA division if present
        4. Return validated Player object
        """
        try:
            # Use helper function for common parsing
            player_data = parse_player_from_row(
                row=row,
                source_prefix="wsn",
                default_level="HIGH_SCHOOL",
                school_state=self.state_code
            )

            if not player_data or not player_data.get("full_name"):
                return None

            # Add level if not set
            if "level" not in player_data:
                player_data["level"] = PlayerLevel.HIGH_SCHOOL

            # Add data source
            player_data["data_source"] = data_source

            # Wisconsin-specific: Parse division if present
            division = row.get("Division") or row.get("Div") or row.get("Class")
            if division:
                # Store in team_name or additional context
                if not player_data.get("team_name"):
                    player_data["team_name"] = f"{player_data.get('school_name', '')} ({division})"

            return self.validate_and_log_data(
                Player, player_data, f"player {player_data.get('full_name')}"
            )

        except Exception as e:
            self.logger.error("Failed to parse player from row", error=str(e))
            return None

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics.

        IMPLEMENTATION STEPS:
        1. Fetch stats page
        2. Find player's row by name
        3. Use parse_season_stats_from_row() helper
        4. Set league = "Wisconsin High School"
        5. Return PlayerSeasonStats object

        Args:
            player_id: Player identifier (format: wsn_firstname_lastname)
            season: Season string (e.g., "2024-25"), uses current if None

        Returns:
            PlayerSeasonStats object or None if not found
        """
        try:
            # Get from stats page
            html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
            soup = parse_html(html)

            stats_table = find_stat_table(soup, table_class_hint="stats")
            if not stats_table:
                stats_table = soup.find("table")

            if not stats_table:
                return None

            rows = extract_table_data(stats_table)

            # Find player row
            player_name = player_id.replace("wsn_", "").replace("_", " ").title()

            for row in rows:
                row_player = row.get("Player") or row.get("NAME") or row.get("Name")
                if row_player and player_name.lower() in clean_player_name(row_player).lower():
                    return self._parse_season_stats_from_row(
                        row, player_id, season or "2024-25"
                    )

            return None

        except Exception as e:
            self.logger.error("Failed to get player season stats", error=str(e))
            return None

    def _parse_season_stats_from_row(
        self, row: dict, player_id: str, season: str
    ) -> Optional[PlayerSeasonStats]:
        """
        Parse season stats from table row.

        IMPLEMENTATION STEPS:
        1. Use parse_season_stats_from_row() helper
        2. Set league_name to "Wisconsin High School"
        3. Calculate totals from averages if needed
        4. Return validated PlayerSeasonStats object
        """
        try:
            # Use helper function for common stat parsing
            stats_data = parse_season_stats_from_row(
                row=row,
                player_id=player_id,
                season=season,
                league_name=self.league_name
            )

            if not stats_data:
                return None

            # Override league if needed
            stats_data["league"] = self.league_name

            # Parse Wisconsin-specific stats if present
            # (e.g., WIAA tournament stats, division-specific stats)

            return self.validate_and_log_data(
                PlayerSeasonStats, stats_data, f"season stats for {player_id}"
            )

        except Exception as e:
            self.logger.error("Failed to parse season stats", error=str(e))
            return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game statistics.

        IMPLEMENTATION STEPS:
        1. Try to construct box score URL
        2. Fetch and parse box score page
        3. Find player in box score table
        4. Parse game stats (points, rebounds, assists, etc.)
        5. Return PlayerGameStats object

        Note: Box scores may require game-specific URLs.
        Falls back to None with warning if not available.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            PlayerGameStats object or None
        """
        self.logger.warning(
            "Individual game stats require box score access - checking availability"
        )

        try:
            # Try to construct box score URL
            box_score_url = f"{self.schedule_url}/boxscore/{game_id}"

            html = await self.http_client.get_text(box_score_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find box score tables
            tables = soup.find_all("table")

            player_name = player_id.replace("wsn_", "").replace("_", " ").title()

            for table in tables:
                rows = extract_table_data(table)

                for row in rows:
                    row_player = clean_player_name(
                        row.get("Player") or row.get("NAME") or ""
                    )
                    if player_name.lower() in row_player.lower():
                        # Found player in box score
                        return self._parse_game_stats_from_row(
                            row, player_id, game_id
                        )

            return None

        except Exception as e:
            self.logger.warning(f"Box scores not available: {str(e)}")
            return None

    def _parse_game_stats_from_row(
        self, row: dict, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """Parse game stats from box score row."""
        try:
            player_name = clean_player_name(
                row.get("Player") or row.get("NAME") or ""
            )

            # Parse game stats
            points = parse_int(row.get("PTS") or row.get("Points"))
            rebounds = parse_int(row.get("REB") or row.get("Rebounds"))
            assists = parse_int(row.get("AST") or row.get("Assists"))
            steals = parse_int(row.get("STL") or row.get("Steals"))
            blocks = parse_int(row.get("BLK") or row.get("Blocks"))
            turnovers = parse_int(row.get("TO") or row.get("Turnovers"))
            fouls = parse_int(row.get("PF") or row.get("Fouls"))
            minutes = parse_int(row.get("MIN") or row.get("Minutes"))

            # Shooting stats
            fgm = parse_int(row.get("FGM") or row.get("FG"))
            fga = parse_int(row.get("FGA"))
            tpm = parse_int(row.get("3PM") or row.get("3P"))
            tpa = parse_int(row.get("3PA"))
            ftm = parse_int(row.get("FTM") or row.get("FT"))
            fta = parse_int(row.get("FTA"))

            game_stats_data = {
                "player_id": player_id,
                "player_name": player_name,
                "game_id": game_id,
                "points": points,
                "total_rebounds": rebounds,
                "assists": assists,
                "steals": steals,
                "blocks": blocks,
                "turnovers": turnovers,
                "personal_fouls": fouls,
                "minutes_played": minutes,
                "field_goals_made": fgm,
                "field_goals_attempted": fga,
                "three_pointers_made": tpm,
                "three_pointers_attempted": tpa,
                "free_throws_made": ftm,
                "free_throws_attempted": fta,
            }

            return self.validate_and_log_data(
                PlayerGameStats, game_stats_data, f"game stats for {player_name}"
            )

        except Exception as e:
            self.logger.error("Failed to parse game stats", error=str(e))
            return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team information.

        IMPLEMENTATION STEPS:
        1. Fetch teams/standings page
        2. Find team by name
        3. Parse record (W-L), conference, division
        4. Auto-add state="WI", country="USA"
        5. Return Team object

        Args:
            team_id: Team identifier (format: wsn_schoolname)

        Returns:
            Team object or None if not found
        """
        try:
            # Try standings page first
            html = await self.http_client.get_text(self.standings_url, cache_ttl=7200)
            soup = parse_html(html)

            # WSN may have multiple division tables
            tables = soup.find_all("table")

            team_name = team_id.replace("wsn_", "").replace("_", " ").title()

            for table in tables:
                rows = extract_table_data(table)

                for row in rows:
                    row_team = row.get("Team") or row.get("School") or row.get("NAME")
                    if row_team and team_name.lower() in row_team.lower():
                        return self._parse_team_from_standings_row(row, team_id, table)

            # Fall back to teams page
            html = await self.http_client.get_text(self.teams_url, cache_ttl=7200)
            soup = parse_html(html)

            tables = soup.find_all("table")
            for table in tables:
                rows = extract_table_data(table)

                for row in rows:
                    row_team = row.get("Team") or row.get("School") or row.get("NAME")
                    if row_team and team_name.lower() in row_team.lower():
                        return self._parse_team_from_row(row, team_id)

            return None

        except Exception as e:
            self.logger.error("Failed to get team", error=str(e))
            return None

    def _parse_team_from_standings_row(
        self, row: dict, team_id: str, table
    ) -> Optional[Team]:
        """
        Parse team from standings row.

        IMPLEMENTATION STEPS:
        1. Extract team name, record (W-L)
        2. Parse conference/division from row or table header
        3. Add Wisconsin location data
        4. Return validated Team object
        """
        try:
            team_name = row.get("Team") or row.get("School") or row.get("NAME") or ""

            # Parse record
            record = row.get("Record") or row.get("W-L") or row.get("Overall")
            wins, losses = parse_record(record) if record else (None, None)

            # Try separate W/L columns
            if wins is None:
                wins = parse_int(row.get("W") or row.get("Wins"))
            if losses is None:
                losses = parse_int(row.get("L") or row.get("Losses"))

            # Get conference record if available
            conf_record = row.get("Conference") or row.get("Conf")
            conf_wins, conf_losses = None, None
            if conf_record and "-" in str(conf_record):
                conf_wins, conf_losses = parse_record(conf_record)

            # Get division/conference from table header or row
            division = row.get("Division") or row.get("Div") or row.get("Class")
            conference = row.get("Conference Name") or row.get("Conf Name")

            if not conference and not division:
                # Check table header
                header = table.find_previous(["h2", "h3", "h4"])
                if header:
                    header_text = get_text_or_none(header)
                    if header_text:
                        # Extract division (D1, D2, etc.) or conference name
                        if "Division" in header_text or "Class" in header_text:
                            division = header_text
                        else:
                            conference = header_text

            data_source = self.create_data_source_metadata(
                url=self.standings_url, quality_flag=DataQualityFlag.COMPLETE
            )

            team_data = {
                "team_id": team_id,
                "team_name": team_name,
                "school_name": team_name,
                "state": self.state_code,
                "country": "USA",
                "level": TeamLevel.HIGH_SCHOOL_VARSITY,
                "league": self.league_name,
                "conference": conference or division,
                "season": "2024-25",
                "wins": wins,
                "losses": losses,
                "conference_wins": conf_wins,
                "conference_losses": conf_losses,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Team, team_data, f"team {team_name}")

        except Exception as e:
            self.logger.error("Failed to parse team from standings", error=str(e))
            return None

    def _parse_team_from_row(self, row: dict, team_id: str) -> Optional[Team]:
        """Parse team from general teams page row."""
        try:
            team_name = row.get("Team") or row.get("School") or row.get("NAME") or ""

            wins = parse_int(row.get("W") or row.get("Wins"))
            losses = parse_int(row.get("L") or row.get("Losses"))
            conference = row.get("Conference") or row.get("Conf")
            division = row.get("Division") or row.get("Div") or row.get("Class")

            data_source = self.create_data_source_metadata(
                url=self.teams_url, quality_flag=DataQualityFlag.COMPLETE
            )

            team_data = {
                "team_id": team_id,
                "team_name": team_name,
                "school_name": team_name,
                "state": self.state_code,
                "country": "USA",
                "level": TeamLevel.HIGH_SCHOOL_VARSITY,
                "league": self.league_name,
                "conference": conference or division,
                "season": "2024-25",
                "wins": wins,
                "losses": losses,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Team, team_data, f"team {team_name}")

        except Exception as e:
            self.logger.error("Failed to parse team", error=str(e))
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
        Get games from schedule.

        IMPLEMENTATION STEPS:
        1. Fetch schedule page
        2. Filter by team_id if provided
        3. Parse game date, teams, scores
        4. Filter by date range if provided
        5. Return list of Game objects

        Args:
            team_id: Filter by team (format: wsn_schoolname)
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            List of Game objects
        """
        try:
            # Construct schedule URL
            schedule_url = self.schedule_url
            if team_id:
                team_name = team_id.replace("wsn_", "").replace("_", "-")
                schedule_url = f"{self.schedule_url}/{team_name}"

            html = await self.http_client.get_text(schedule_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find schedule table
            schedule_table = find_stat_table(soup, table_class_hint="schedule")
            if not schedule_table:
                schedule_table = soup.find("table")

            if not schedule_table:
                self.logger.warning("No schedule table found")
                return []

            rows = extract_table_data(schedule_table)
            games = []

            for row in rows[:limit]:
                game = self._parse_game_from_schedule_row(row, team_id)
                if not game:
                    continue

                # Apply date filters
                if start_date and game.game_date and game.game_date < start_date:
                    continue
                if end_date and game.game_date and game.game_date > end_date:
                    continue

                games.append(game)

            self.logger.info(f"Found {len(games)} games")
            return games

        except Exception as e:
            self.logger.warning(f"Failed to get games: {str(e)}")
            return []

    def _parse_game_from_schedule_row(
        self, row: dict, team_id: Optional[str]
    ) -> Optional[Game]:
        """Parse game from schedule row."""
        try:
            # Parse date
            date_str = row.get("Date") or row.get("DATE")
            game_date = None
            if date_str:
                try:
                    # Try common date formats
                    from datetime import datetime
                    for fmt in ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"]:
                        try:
                            game_date = datetime.strptime(date_str.strip(), fmt)
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

            # Parse teams
            home_team = row.get("Home") or row.get("Home Team")
            away_team = row.get("Away") or row.get("Visitor") or row.get("Opponent")

            # Parse scores
            home_score = parse_int(row.get("Home Score") or row.get("H"))
            away_score = parse_int(row.get("Away Score") or row.get("V") or row.get("Opp Score"))

            # Determine status
            status = GameStatus.SCHEDULED
            if home_score is not None and away_score is not None:
                status = GameStatus.FINAL
            elif game_date and game_date < datetime.now():
                status = GameStatus.IN_PROGRESS

            # Generate game ID
            game_id = f"wsn_game_{home_team}_{away_team}".lower().replace(" ", "_")
            if date_str:
                game_id += f"_{date_str.replace('/', '_')}"

            game_data = {
                "game_id": game_id,
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "game_date": game_date,
                "status": status,
                "game_type": GameType.REGULAR_SEASON,
                "league": self.league_name,
            }

            return self.validate_and_log_data(Game, game_data, f"game {game_id}")

        except Exception as e:
            self.logger.error("Failed to parse game", error=str(e))
            return None

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        IMPLEMENTATION STEPS:
        1. Fetch leaders page
        2. Find specific stat table (PPG, RPG, APG, etc.)
        3. Parse leaderboard entries
        4. Use build_leaderboard_entry() helper
        5. Return list of leaderboard dicts

        Args:
            stat: Stat category (e.g., "points", "rebounds", "assists")
            season: Season filter
            limit: Maximum results

        Returns:
            List of leaderboard entry dictionaries
        """
        try:
            # WSN has dedicated leaders page
            html = await self.http_client.get_text(self.leaders_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find the specific stat table
            # WSN likely has separate tables for PPG, RPG, APG, etc.
            tables = soup.find_all("table")

            # Normalize stat name for matching
            stat_variations = {
                "points": ["points", "ppg", "scoring", "pts"],
                "rebounds": ["rebounds", "rpg", "reb"],
                "assists": ["assists", "apg", "ast"],
                "steals": ["steals", "spg", "stl"],
                "blocks": ["blocks", "bpg", "blk"],
                "threes": ["3-pointers", "3pm", "three pointers", "threes"],
            }

            stat_keywords = stat_variations.get(stat.lower(), [stat.lower()])

            for table in tables:
                # Check if this is the right stat table
                header = table.find_previous(["h2", "h3", "h4"])
                header_text = get_text_or_none(header).lower() if header else ""

                # Check if header matches stat
                matches_stat = any(keyword in header_text for keyword in stat_keywords)

                if matches_stat:
                    rows = extract_table_data(table)
                    leaderboard = []

                    for i, row in enumerate(rows[:limit], 1):
                        player_name = clean_player_name(
                            row.get("Player") or row.get("NAME") or row.get("Name") or ""
                        )
                        school = row.get("School") or row.get("Team") or row.get("SCHOOL")

                        # Try to find stat value
                        stat_value = None
                        for col in ["PPG", "RPG", "APG", "SPG", "BPG", "Value", "AVG", "Total"]:
                            val = parse_float(row.get(col))
                            if val is not None:
                                stat_value = val
                                break

                        if player_name and stat_value is not None:
                            entry = build_leaderboard_entry(
                                rank=i,
                                player_name=player_name,
                                stat_value=stat_value,
                                stat_name=stat,
                                season=season or "2024-25",
                                source_prefix="wsn",
                                team_name=school
                            )
                            leaderboard.append(entry)

                    if leaderboard:
                        self.logger.info(
                            f"Found {len(leaderboard)} leaders for {stat}"
                        )
                        return leaderboard

            # If no specific table found, try to sort main stats page
            self.logger.warning(f"No specific leaderboard found for {stat}")
            return await self._get_leaderboard_from_stats(stat, season, limit)

        except Exception as e:
            self.logger.error("Failed to get leaderboard", error=str(e))
            return []

    async def _get_leaderboard_from_stats(
        self, stat: str, season: Optional[str], limit: int
    ) -> list[dict]:
        """
        Get leaderboard by extracting and sorting main stats page.

        Fallback method when dedicated leaders page is not available.
        """
        try:
            html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
            soup = parse_html(html)

            stats_table = find_stat_table(soup)
            if not stats_table:
                return []

            rows = extract_table_data(stats_table)

            # Map stat name to column
            stat_column_map = {
                "points": "PPG",
                "rebounds": "RPG",
                "assists": "APG",
                "steals": "SPG",
                "blocks": "BPG",
            }

            stat_column = stat_column_map.get(stat.lower())
            if not stat_column:
                return []

            # Extract and sort
            entries = []
            for row in rows:
                player_name = clean_player_name(
                    row.get("Player") or row.get("NAME") or ""
                )
                school = row.get("School") or row.get("Team")
                stat_value = parse_float(row.get(stat_column))

                if player_name and stat_value is not None:
                    entries.append({
                        "player_name": player_name,
                        "school": school,
                        "stat_value": stat_value
                    })

            # Sort by stat value descending
            entries.sort(key=lambda x: x["stat_value"], reverse=True)

            # Build leaderboard
            leaderboard = []
            for i, entry in enumerate(entries[:limit], 1):
                lb_entry = build_leaderboard_entry(
                    rank=i,
                    player_name=entry["player_name"],
                    stat_value=entry["stat_value"],
                    stat_name=stat,
                    season=season or "2024-25",
                    source_prefix="wsn",
                    team_name=entry["school"]
                )
                leaderboard.append(lb_entry)

            return leaderboard

        except Exception as e:
            self.logger.error("Failed to get leaderboard from stats", error=str(e))
            return []
