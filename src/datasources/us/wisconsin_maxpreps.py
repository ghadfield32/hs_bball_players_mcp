"""
MaxPreps Wisconsin DataSource Adapter

Provides comprehensive player and team statistics for Wisconsin high school basketball
from MaxPreps Wisconsin state hub. MaxPreps aggregates crowd-sourced stats with good
coverage of player-level data, team schedules, and season statistics.

**Data Coverage**: MaxPreps excels at:
- Player statistics (season averages, per-game stats)
- Team schedules and results
- Season leaderboards (points, rebounds, assists, etc.)
- Player profiles with grad year, height, position
- Regular season and some postseason data

**Base URL**: https://www.maxpreps.com/wi/basketball/

**URL Patterns**:
```
State Hub: /wi/basketball/
Leaders: /wi/basketball/leaders.htm?season={year}
Team Page: /wi/basketball/{school-slug}/home.htm
Player Profile: /wi/basketball/{school-slug}/roster/{player-name}.htm
Schedule: /wi/basketball/{school-slug}/schedule.htm
```

**Data Quality**: MEDIUM-HIGH (crowd-sourced, needs QA gates)
- Stats are user-submitted (coaches, scorekeepers, fans)
- Generally reliable but may have gaps or errors
- Use QA checks: plausibility ranges, missing data detection
- Validate against WIAA when combining sources

**Rate Limiting**: MaxPreps has rate limits, respect robots.txt
- Recommended: 15 req/min with caching
- Cache TTL: 1 hour for player data, 30 min for schedules

**Recommended Use**: Combine with WIAA for complete Wisconsin coverage:
- WIAA: Authoritative tournament brackets, seeds, postseason results
- MaxPreps: Player stats, team schedules, regular season depth
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


class MaxPrepsWisconsinDataSource(BaseDataSource):
    """
    MaxPreps Wisconsin data source adapter.

    **PRIMARY PURPOSE**: Player-level statistics and regular season depth for Wisconsin.

    This adapter provides:
    1. Player search via state leaderboards
    2. Season statistics (PPG, RPG, APG, etc.)
    3. Player profiles (height, position, grad year, school)
    4. Team schedules and results
    5. Team rosters with player links

    **ARCHITECTURE**:
    - Inherits from BaseDataSource
    - Uses HTTP client with caching (1-hour TTL for player data)
    - Starts from leaderboard pages to discover players
    - Crawls: leaderboards → team pages → player pages → stats
    - Marks data with MEDIUM quality flag (crowd-sourced)

    **DATA QUALITY**: MEDIUM-HIGH
    - Crowd-sourced stats (coaches/scorekeepers submit)
    - Generally reliable but may have gaps
    - Use QA gates: check for negative stats, implausible values (>100 PPG), missing fields

    **LIMITATIONS**:
    - Tournament brackets NOT available (use WIAA for this)
    - Box scores may be incomplete
    - Historical data may have gaps
    """

    source_type = DataSourceType.MAXPREPS_WI
    source_name = "MaxPreps Wisconsin"
    base_url = "https://www.maxpreps.com"
    region = DataSourceRegion.US_WI

    STATE_CODE = "WI"
    STATE_NAME = "Wisconsin"
    LEAGUE_NAME = "Wisconsin High School"

    def __init__(self):
        """Initialize MaxPreps Wisconsin datasource."""
        super().__init__()

        # MaxPreps Wisconsin-specific URLs
        self.state_hub_url = f"{self.base_url}/wi/basketball"
        self.leaders_url = f"{self.state_hub_url}/leaders.htm"
        self.search_url = f"{self.base_url}/search"

        self.logger.info(
            "MaxPreps Wisconsin initialized",
            state=self.STATE_CODE,
            hub_url=self.state_hub_url,
        )

    def _build_leaders_url(self, stat: str = "points", season: Optional[str] = None, gender: str = "boys") -> str:
        """
        Build URL for stat leaders page.

        **MaxPreps Leader URL Pattern**:
        ```
        /wi/basketball/leaders.htm?season={year}&stat={stat_code}&gender={gender}
        ```

        Args:
            stat: Stat type (points, rebounds, assists, steals, blocks, threes)
            season: Season string (e.g., "2024-25"), None for current
            gender: "boys" or "girls"

        Returns:
            Full leaders URL
        """
        # Convert season to year (2024-25 → 2024)
        if season:
            year = int(season.split("-")[0])
        else:
            year = datetime.now().year if datetime.now().month < 6 else datetime.now().year - 1

        # MaxPreps stat codes
        stat_codes = {
            "points": "pts",
            "rebounds": "reb",
            "assists": "ast",
            "steals": "stl",
            "blocks": "blk",
            "threes": "3pm",
            "field_goals": "fgm",
            "free_throws": "ftm",
        }

        stat_code = stat_codes.get(stat.lower(), "pts")

        return f"{self.leaders_url}?season={year}&stat={stat_code}&gender={gender}"

    def _build_player_id(self, player_name: str, school_slug: str) -> str:
        """
        Build MaxPreps player ID.

        Format: maxpreps_wi_{school_slug}_{player_name_slug}

        Args:
            player_name: Player name
            school_slug: School URL slug

        Returns:
            Player ID
        """
        name_slug = clean_player_name(player_name).lower().replace(" ", "_")
        return f"maxpreps_wi_{school_slug}_{name_slug}"

    def _build_team_id(self, school_slug: str) -> str:
        """
        Build MaxPreps team ID.

        Format: maxpreps_wi_{school_slug}

        Args:
            school_slug: School URL slug

        Returns:
            Team ID
        """
        return f"maxpreps_wi_{school_slug}"

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        MaxPreps doesn't support direct player lookup by ID.
        Extracts player name and school from ID, then searches.

        Args:
            player_id: Player identifier (format: maxpreps_wi_{school}_{name})

        Returns:
            Player object or None
        """
        try:
            # Extract school and name from player_id
            # Format: maxpreps_wi_{school_slug}_{player_name_slug}
            parts = player_id.split("_")
            if len(parts) < 4 or parts[0] != "maxpreps" or parts[1] != "wi":
                self.logger.warning(f"Invalid player_id format", player_id=player_id)
                return None

            school_slug = parts[2]
            player_name_slug = "_".join(parts[3:])
            player_name = player_name_slug.replace("_", " ").title()

            # Search for player
            players = await self.search_players(name=player_name, limit=10)

            # Filter by school slug if possible
            for player in players:
                if player.player_id == player_id:
                    return player

            # Return first match if exact match not found
            return players[0] if players else None

        except Exception as e:
            self.logger.error("Failed to get player", player_id=player_id, error=str(e))
            return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[Player]:
        """
        Search for players via MaxPreps leaderboards.

        **STRATEGY**:
        1. Fetch points leaders page (largest dataset)
        2. Parse player table to extract: name, school, stats
        3. Build Player objects with Wisconsin location data
        4. Apply filters (name, team)
        5. Return up to limit results

        Args:
            name: Player name (partial match)
            team: Team/school name (partial match)
            season: Season filter (e.g., "2024-25")
            limit: Maximum results

        Returns:
            List of Player objects
        """
        try:
            # Fetch points leaders (most comprehensive list)
            leaders_url = self._build_leaders_url(stat="points", season=season, gender="boys")
            self.logger.info(f"Fetching MaxPreps leaders", url=leaders_url)

            html = await self.http_client.get_text(leaders_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find leaders table
            # MaxPreps uses table with class "leaders-table" or similar
            leaders_table = find_stat_table(soup, table_class_hint="leaders")
            if not leaders_table:
                # Fallback: find any table with headers like "Player", "School", "PPG"
                leaders_table = soup.find("table")

            if not leaders_table:
                self.logger.warning("No leaders table found")
                return []

            # Extract table data
            rows = extract_table_data(leaders_table)
            self.logger.debug(f"Found {len(rows)} leader rows")

            players: List[Player] = []
            data_source = self.create_data_source_metadata(
                url=leaders_url,
                quality_flag=DataQualityFlag.PARTIAL,  # Crowd-sourced
            )

            for row in rows[:limit * 2]:  # Get extra for filtering
                player = self._parse_player_from_leader_row(row, season or "2024-25", data_source)
                if not player:
                    continue

                # Apply filters
                if name and name.lower() not in player.full_name.lower():
                    continue
                if team and (not player.school_name or team.lower() not in player.school_name.lower()):
                    continue

                players.append(player)

                if len(players) >= limit:
                    break

            self.logger.info(f"Found {len(players)} players", filters={"name": name, "team": team})
            return players

        except Exception as e:
            self.logger.error("Failed to search players", error=str(e))
            return []

    def _parse_player_from_leader_row(
        self, row: Dict[str, Any], season: str, data_source
    ) -> Optional[Player]:
        """
        Parse player from leaderboard table row.

        **Expected Columns**:
        - Player / Name
        - School / Team
        - Class / Gr (grad year)
        - Pos (position)
        - Ht (height)
        - PPG / Points

        Args:
            row: Row dictionary from leaderboard table
            season: Season string
            data_source: DataSource metadata

        Returns:
            Player object or None
        """
        try:
            # Extract player name
            player_name = clean_player_name(
                row.get("Player") or row.get("Name") or row.get("PLAYER") or ""
            )
            if not player_name:
                return None

            # Extract school
            school = str(
                row.get("School") or row.get("Team") or row.get("SCHOOL") or ""
            ).strip()

            # Extract grad year
            grad_year_text = row.get("Class") or row.get("Gr") or row.get("Year") or ""
            grad_year = parse_grad_year(grad_year_text) if grad_year_text else None

            # Extract position
            position_text = row.get("Pos") or row.get("Position") or ""
            position = None
            if position_text:
                pos_upper = position_text.strip().upper()
                try:
                    if pos_upper in ["PG", "SG", "SF", "PF", "C", "G", "F"]:
                        position = Position(pos_upper)
                except ValueError:
                    pass

            # Extract height
            height_text = row.get("Ht") or row.get("Height") or ""
            height_inches = parse_height_to_inches(height_text) if height_text else None

            # Build school slug for player ID (simple: lowercase + underscores)
            school_slug = school.lower().replace(" ", "_").replace("-", "_") if school else "unknown"

            # Build player ID
            player_id = self._build_player_id(player_name, school_slug)

            # Split name
            name_parts = player_name.split()
            first_name = name_parts[0] if len(name_parts) > 0 else player_name
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            return Player(
                player_id=player_id,
                first_name=first_name,
                last_name=last_name,
                full_name=player_name,
                height_inches=height_inches,
                position=position,
                grad_year=grad_year,
                school_name=school,
                school_state=self.STATE_CODE,
                school_country="USA",
                team_name=school,  # MaxPreps uses school name as team
                level=PlayerLevel.HIGH_SCHOOL,
                profile_url=f"{self.state_hub_url}/{school_slug}/roster/{player_name.lower().replace(' ', '-')}.htm",
                data_source=data_source,
            )

        except Exception as e:
            self.logger.error("Failed to parse player from leader row", error=str(e))
            return None

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics.

        **STRATEGY**:
        1. Extract player name and school from player_id
        2. Fetch leaderboard pages to find player row
        3. Parse season averages from row
        4. Return PlayerSeasonStats object

        Args:
            player_id: Player identifier
            season: Season string, None for current

        Returns:
            PlayerSeasonStats or None
        """
        try:
            # Extract player name from ID
            parts = player_id.split("_")
            if len(parts) < 4:
                return None

            player_name_slug = "_".join(parts[3:])
            player_name = player_name_slug.replace("_", " ").title()

            # Fetch points leaders to find player
            leaders_url = self._build_leaders_url(stat="points", season=season)
            html = await self.http_client.get_text(leaders_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find leaders table
            leaders_table = find_stat_table(soup)
            if not leaders_table:
                return None

            rows = extract_table_data(leaders_table)

            # Find player row
            for row in rows:
                row_player = clean_player_name(row.get("Player") or row.get("Name") or "")
                if row_player and player_name.lower() in row_player.lower():
                    return self._parse_season_stats_from_row(
                        row, player_id, season or "2024-25"
                    )

            return None

        except Exception as e:
            self.logger.error("Failed to get player season stats", error=str(e))
            return None

    def _parse_season_stats_from_row(
        self, row: Dict[str, Any], player_id: str, season: str
    ) -> Optional[PlayerSeasonStats]:
        """
        Parse season stats from leaderboard row.

        **Common MaxPreps Columns**:
        - PPG, RPG, APG, SPG, BPG (per-game averages)
        - FG%, 3P%, FT% (shooting percentages)
        - GP (games played)

        Args:
            row: Row dictionary
            player_id: Player ID
            season: Season string

        Returns:
            PlayerSeasonStats or None
        """
        try:
            # Use helper function for common parsing
            stats_data = parse_season_stats_from_row(
                row=row,
                player_id=player_id,
                season=season,
                league_name=self.LEAGUE_NAME,
            )

            if not stats_data:
                return None

            # Override league
            stats_data["league"] = self.LEAGUE_NAME

            # Add QA checks for crowd-sourced data
            # Check for implausible values
            ppg = stats_data.get("points_per_game")
            if ppg and ppg > 100:
                self.logger.warning(
                    f"Implausible PPG value detected",
                    player_id=player_id,
                    ppg=ppg,
                )
                stats_data["data_source"].quality_flag = DataQualityFlag.SUSPECT

            return self.validate_and_log_data(
                PlayerSeasonStats,
                stats_data,
                f"season stats for {player_id}",
            )

        except Exception as e:
            self.logger.error("Failed to parse season stats", error=str(e))
            return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game statistics from box score.

        **LIMITATION**: MaxPreps box scores require game-specific URLs.
        This method provides a fallback implementation.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            PlayerGameStats or None
        """
        self.logger.warning(
            "MaxPreps box scores require game-specific URLs - limited availability"
        )
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team information.

        **STRATEGY**:
        1. Extract school slug from team_id
        2. Fetch team page (schedule/standings)
        3. Parse team data (name, record, conference)
        4. Return Team object

        Args:
            team_id: Team identifier (format: maxpreps_wi_{school_slug})

        Returns:
            Team object or None
        """
        try:
            # Extract school slug from team_id
            # Format: maxpreps_wi_{school_slug}
            if not team_id.startswith("maxpreps_wi_"):
                return None

            school_slug = team_id.replace("maxpreps_wi_", "")

            # Build team page URL
            team_url = f"{self.state_hub_url}/{school_slug}/home.htm"

            html = await self.http_client.get_text(team_url, cache_ttl=7200)
            soup = parse_html(html)

            # Extract team name (usually in h1 or title)
            team_name_elem = soup.find("h1", class_=["team-name", "school-name"])
            if not team_name_elem:
                team_name_elem = soup.find("h1")

            team_name = (get_text_or_none(team_name_elem) or "").strip() if team_name_elem else school_slug.replace("_", " ").title()

            # Extract record (look for W-L pattern)
            record_pattern = re.compile(r"(\d+)-(\d+)")
            record_text = soup.find(text=record_pattern)
            wins, losses = None, None
            if record_text:
                match = record_pattern.search(str(record_text))
                if match:
                    wins = int(match.group(1))
                    losses = int(match.group(2))

            # Extract conference (if available)
            conference = None
            conf_elem = soup.find(text=re.compile(r"Conference", re.I))
            if conf_elem:
                # Get next sibling or parent for conference name
                parent = conf_elem.find_parent()
                if parent:
                    conference = parent.get_text().strip()

            data_source = self.create_data_source_metadata(
                url=team_url,
                quality_flag=DataQualityFlag.PARTIAL,
            )

            return Team(
                team_id=team_id,
                team_name=team_name,
                school_name=team_name,
                state=self.STATE_CODE,
                country="USA",
                level=TeamLevel.HIGH_SCHOOL_VARSITY,
                league=self.LEAGUE_NAME,
                conference=conference,
                season="2024-25",
                wins=wins,
                losses=losses,
                data_source=data_source,
            )

        except Exception as e:
            self.logger.error("Failed to get team", team_id=team_id, error=str(e))
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
        Get games from team schedules.

        **STRATEGY**:
        1. Extract school slug from team_id
        2. Fetch team schedule page
        3. Parse game rows (opponent, date, score, result)
        4. Return list of Game objects

        Args:
            team_id: Team identifier
            start_date: Filter by start date
            end_date: Filter by end date
            season: Season filter
            limit: Maximum results

        Returns:
            List of Game objects
        """
        if not team_id:
            self.logger.warning("team_id required for games query")
            return []

        try:
            # Extract school slug
            if not team_id.startswith("maxpreps_wi_"):
                return []

            school_slug = team_id.replace("maxpreps_wi_", "")

            # Build schedule URL
            schedule_url = f"{self.state_hub_url}/{school_slug}/schedule.htm"

            html = await self.http_client.get_text(schedule_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find schedule table
            schedule_table = find_stat_table(soup, table_class_hint="schedule")
            if not schedule_table:
                schedule_table = soup.find("table")

            if not schedule_table:
                return []

            rows = extract_table_data(schedule_table)
            games: List[Game] = []

            for row in rows[:limit]:
                game = self._parse_game_from_schedule_row(row, team_id, school_slug, schedule_url)
                if game:
                    games.append(game)

            return games

        except Exception as e:
            self.logger.error("Failed to get games", team_id=team_id, error=str(e))
            return []

    def _parse_game_from_schedule_row(
        self, row: Dict[str, Any], team_id: str, school_slug: str, source_url: str
    ) -> Optional[Game]:
        """Parse game from schedule table row."""
        try:
            # Extract opponent
            opponent = row.get("Opponent") or row.get("Team") or row.get("Vs/At")
            if not opponent:
                return None

            opponent = clean_text(opponent)

            # Determine home/away
            is_home = "vs" in opponent.lower() or "@" not in opponent
            opponent = opponent.replace("vs", "").replace("@", "").replace("at", "").strip()

            # Extract date
            date_str = row.get("Date") or row.get("DATE")
            game_date = None
            if date_str:
                # Try to parse date
                try:
                    game_date = datetime.strptime(clean_text(date_str), "%m/%d/%Y")
                except Exception:
                    pass

            # Extract score/result
            result = row.get("Result") or row.get("Score") or row.get("W/L")
            home_score, away_score = None, None
            status = GameStatus.SCHEDULED

            if result:
                result = clean_text(result)
                # Parse score pattern: "W 65-54" or "L 48-52" or "65-54"
                score_match = re.search(r"(\d+)-(\d+)", result)
                if score_match:
                    score1 = int(score_match.group(1))
                    score2 = int(score_match.group(2))

                    # Determine which score is home vs away
                    is_win = "W" in result.upper() or "Win" in result
                    if is_home:
                        home_score = score1 if is_win else score2
                        away_score = score2 if is_win else score1
                    else:
                        home_score = score2 if is_win else score1
                        away_score = score1 if is_win else score2

                    status = GameStatus.FINAL

            # Build game ID
            opponent_slug = opponent.lower().replace(" ", "_")
            game_id = f"maxpreps_wi_{school_slug}_vs_{opponent_slug}"
            if date_str:
                game_id += f"_{date_str.replace('/', '_')}"

            # Build team IDs
            home_team_id = team_id if is_home else f"maxpreps_wi_{opponent_slug}"
            away_team_id = f"maxpreps_wi_{opponent_slug}" if is_home else team_id
            home_team_name = school_slug.replace("_", " ").title() if is_home else opponent
            away_team_name = opponent if is_home else school_slug.replace("_", " ").title()

            return Game(
                game_id=game_id,
                home_team_id=home_team_id,
                home_team_name=home_team_name,
                away_team_id=away_team_id,
                away_team_name=away_team_name,
                home_score=home_score,
                away_score=away_score,
                game_date=game_date,
                status=status,
                game_type=GameType.REGULAR_SEASON,
                level="high_school_varsity",
                league=self.LEAGUE_NAME,
                season="2024-25",
                data_source=self.create_data_source_metadata(
                    url=source_url,
                    quality_flag=DataQualityFlag.PARTIAL,
                ),
            )

        except Exception as e:
            self.logger.error("Failed to parse game from schedule row", error=str(e))
            return None

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get statistical leaderboard.

        **STRATEGY**:
        1. Fetch stat-specific leaders page
        2. Parse leaderboard table
        3. Build leaderboard entries

        Args:
            stat: Stat category (points, rebounds, assists, steals, blocks)
            season: Season filter
            limit: Maximum results

        Returns:
            List of leaderboard entry dicts
        """
        try:
            # Build leaders URL
            leaders_url = self._build_leaders_url(stat=stat, season=season)

            html = await self.http_client.get_text(leaders_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find leaders table
            leaders_table = find_stat_table(soup)
            if not leaders_table:
                return []

            rows = extract_table_data(leaders_table)

            leaderboard: List[Dict[str, Any]] = []

            # Map stat names to column names
            stat_columns = {
                "points": ["PPG", "Points", "PTS"],
                "rebounds": ["RPG", "Rebounds", "REB"],
                "assists": ["APG", "Assists", "AST"],
                "steals": ["SPG", "Steals", "STL"],
                "blocks": ["BPG", "Blocks", "BLK"],
            }

            columns = stat_columns.get(stat.lower(), ["PPG"])

            for i, row in enumerate(rows[:limit], 1):
                player_name = clean_player_name(
                    row.get("Player") or row.get("Name") or ""
                )
                school = row.get("School") or row.get("Team") or ""

                # Find stat value
                stat_value = None
                for col in columns:
                    stat_value = parse_float(row.get(col))
                    if stat_value is not None:
                        break

                if not player_name or stat_value is None:
                    continue

                # Build entry
                school_slug = school.lower().replace(" ", "_") if school else "unknown"
                entry = build_leaderboard_entry(
                    rank=i,
                    player_name=player_name,
                    stat_value=stat_value,
                    stat_name=stat,
                    season=season or "2024-25",
                    source_prefix=f"maxpreps_wi_{school_slug}",
                    team_name=school,
                )

                # Add Wisconsin context
                entry["state"] = self.STATE_CODE
                entry["league"] = self.LEAGUE_NAME

                leaderboard.append(entry)

            self.logger.info(f"Built leaderboard", stat=stat, entries=len(leaderboard))
            return leaderboard

        except Exception as e:
            self.logger.error("Failed to get leaderboard", stat=stat, error=str(e))
            return []
