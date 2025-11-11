"""
Grind Session DataSource Adapter

Scrapes player statistics from Grind Session events and leagues.
Grind Session features elite prep and non-traditional HS players.

Implementation Status: REQUIRES WEBSITE INSPECTION
Before implementing, visit https://thegrindsession.com and:
1. Locate event pages and stats sections
2. Inspect HTML table structure for player stats
3. Identify event IDs and URL patterns
4. Note column names for stats (points, rebounds, assists, etc.)
5. Check robots.txt for scraping permissions
6. Understand event-based organization (multiple tournaments/sessions)
"""

from datetime import datetime
from typing import Optional

from ...models import (
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    Game,
    Player,
    PlayerGameStats,
    PlayerLevel,
    PlayerSeasonStats,
    Team,
    TeamLevel,
)
from ...utils import (
    build_leaderboard_entry,
    extract_table_data,
    find_stat_table,
    parse_float,
    parse_html,
    parse_player_from_row,
    parse_season_stats_from_row,
)
from ..base import BaseDataSource


class GrindSessionDataSource(BaseDataSource):
    """
    Grind Session datasource adapter.

    Provides access to player stats, team rosters, and event data.

    Grind Session Structure:
    - Event-based system (multiple tournaments throughout the year)
    - Each event has participating teams
    - Stats are organized by event, not by season
    - Focus on high school showcase tournaments
    - Players from various regions compete in events
    """

    source_type = DataSourceType.GRIND_SESSION
    source_name = "Grind Session"
    base_url = "https://thegrindsession.com"
    region = DataSourceRegion.US

    def __init__(self):
        """Initialize Grind Session datasource."""
        super().__init__()

        # STEP 1: Update these URLs after inspecting the website
        # Visit https://thegrindsession.com and find actual paths
        # Common patterns to check:
        # - /events, /tournaments
        # - /stats, /statistics
        # - /teams, /rosters
        # - /schedule, /games
        # - /event/{event-id}/stats
        # - /event/{event-id}/teams

        # TODO: Replace with actual Grind Session URLs
        self.events_url = f"{self.base_url}/events"  # UPDATE AFTER INSPECTION
        self.stats_url = f"{self.base_url}/stats"  # UPDATE AFTER INSPECTION
        self.teams_url = f"{self.base_url}/teams"  # UPDATE AFTER INSPECTION
        self.schedule_url = f"{self.base_url}/schedule"  # UPDATE AFTER INSPECTION

        # Event-specific URL patterns (update after inspection)
        # self.event_stats_url = f"{self.base_url}/event/{{event_id}}/stats"
        # self.event_teams_url = f"{self.base_url}/event/{{event_id}}/teams"

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID from Grind Session.

        Args:
            player_id: Grind Session player identifier (format: grindsession_firstname_lastname)

        Returns:
            Player object or None
        """
        # Pattern: Use search_players to find player
        # This is the standard approach when individual player pages
        # don't have predictable URLs
        players = await self.search_players(
            name=player_id.replace("grindsession_", ""), limit=1
        )
        return players[0] if players else None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in Grind Session events.

        IMPLEMENTATION STEPS:
        1. Visit https://thegrindsession.com/events (or similar)
        2. Find the most recent event or stats page
        3. Open browser DevTools (F12) -> Network tab
        4. Locate the stats table on the page
        5. Right-click the table -> Inspect
        6. Note the table's class name (e.g., "stats-table", "player-table")
        7. Note column headers: Player, Team, Pos, Height, Event, PPG, RPG, APG, etc.
        8. Note that stats may be organized by event, not season
        9. May need to iterate through multiple events to build comprehensive list
        10. Update find_stat_table() parameter below with actual class name
        11. Test the implementation

        Args:
            name: Player name filter (partial match)
            team: Team name filter
            season: Season filter (for Grind Session, may map to specific events)
            limit: Maximum results

        Returns:
            List of Player objects
        """
        try:
            # Fetch stats page with 1-hour cache
            # NOTE: Grind Session may require event-specific URLs
            html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # STEP 2: Find stats table
            # After inspecting website, update table_class_hint parameter
            # Try one of these strategies:

            # Strategy 1: Find by class hint
            table = find_stat_table(soup, table_class_hint="stats")

            # Strategy 2: Find by header text (uncomment if needed)
            # table = find_stat_table(soup, header_text="Player Statistics")

            # Strategy 3: Find by ID (uncomment if needed)
            # table = soup.find("table", id="player-stats")

            # Strategy 4: Fallback - first table (uncomment if needed)
            # if not table:
            #     table = soup.find("table")

            if not table:
                self.logger.warning("No stats table found on Grind Session stats page")
                return []

            # Extract table rows as dictionaries
            rows = extract_table_data(table)

            # Create data source metadata
            data_source = self.create_data_source_metadata(
                url=self.stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            players = []
            for row in rows[: limit * 2]:  # Get extra for filtering
                # Use helper to parse common player fields
                player_data = parse_player_from_row(
                    row,
                    source_prefix="grindsession",
                    default_level="HIGH_SCHOOL",  # Grind Session is HS showcase
                )

                if not player_data:
                    continue

                # Add Grind Session-specific fields
                player_data["data_source"] = data_source
                player_data["level"] = PlayerLevel.HIGH_SCHOOL

                # Grind Session may include event information in stats
                # Extract if available:
                # event_name = row.get("Event") or row.get("TOURNAMENT")
                # if event_name:
                #     player_data["notes"] = f"Event: {event_name}"

                # Validate with Pydantic model
                player = self.validate_and_log_data(
                    Player, player_data, f"player {player_data.get('full_name')}"
                )

                if not player:
                    continue

                # Apply filters
                if name and name.lower() not in player.full_name.lower():
                    continue
                if team and (
                    not player.team_name or team.lower() not in player.team_name.lower()
                ):
                    continue

                players.append(player)

                if len(players) >= limit:
                    break

            self.logger.info(f"Found {len(players)} Grind Session players")
            return players

        except Exception as e:
            self.logger.error("Grind Session player search failed", error=str(e))
            return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player event/season statistics from Grind Session.

        IMPLEMENTATION STEPS:
        1. The stats table from search_players() contains event or season averages
        2. Find the player's row in that table
        3. Parse their statistics using parse_season_stats_from_row()
        4. Note: Grind Session uses event-based stats, not traditional seasons
        5. May need to aggregate across multiple events for "season" stats
        6. Return PlayerSeasonStats object

        Args:
            player_id: Player identifier (format: grindsession_firstname_lastname)
            season: Season (None = current season/latest event)

        Returns:
            PlayerSeasonStats or None
        """
        try:
            # Fetch stats page
            html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find stats table
            table = find_stat_table(soup, table_class_hint="stats")
            if not table:
                self.logger.warning("No stats table found")
                return None

            # Extract rows
            rows = extract_table_data(table)

            # Extract player name from player_id
            # Format: "grindsession_john_doe" -> "John Doe"
            player_name = (
                player_id.replace("grindsession_", "").replace("_", " ").title()
            )

            # Find matching player row
            for row in rows:
                row_player = row.get("Player") or row.get("NAME") or ""
                if player_name.lower() in row_player.lower():
                    # Use helper to parse stats
                    stats_data = parse_season_stats_from_row(
                        row, player_id, season or "2024-25", "Grind Session"
                    )

                    # Validate and return
                    return self.validate_and_log_data(
                        PlayerSeasonStats,
                        stats_data,
                        f"season stats for {player_name}",
                    )

            self.logger.warning(f"Player not found in stats", player_id=player_id)
            return None

        except Exception as e:
            self.logger.error(
                "Failed to get Grind Session player season stats", error=str(e)
            )
            return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game statistics from Grind Session.

        IMPLEMENTATION STEPS:
        1. Visit Grind Session event page and find a completed game
        2. Look for box score or game stats section
        3. Note the URL pattern (e.g., /event/{event-id}/game/{game-id}/boxscore)
        4. Inspect the box score table structure
        5. Note column headers for game stats
        6. Implement parsing similar to OTE adapter
        7. Handle event-specific game IDs

        Args:
            player_id: Player identifier
            game_id: Game identifier (may include event_id)

        Returns:
            PlayerGameStats or None
        """
        try:
            # TODO: Implement after inspecting Grind Session box score pages
            # Typical URL patterns to try:
            # box_score_url = f"{self.base_url}/event/{event_id}/game/{game_id}/boxscore"
            # box_score_url = f"{self.base_url}/games/{game_id}/stats"
            # box_score_url = f"{self.base_url}/boxscore/{game_id}"

            # NOTE: May need to extract event_id from game_id
            # Example: game_id = "event123_game456"
            # event_id, actual_game_id = game_id.split("_game")

            self.logger.warning(
                "Grind Session game stats require box score URL pattern"
            )
            return None

        except Exception as e:
            self.logger.error(
                "Failed to get Grind Session player game stats", error=str(e)
            )
            return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team information from Grind Session.

        IMPLEMENTATION STEPS:
        1. Visit https://thegrindsession.com/events
        2. Click on an event to see participating teams
        3. Look for teams table or team cards
        4. Note available fields: team name, record, roster, etc.
        5. Note that teams may be event-specific
        6. Inspect HTML structure
        7. Implement parsing similar to OTE adapter

        Args:
            team_id: Team identifier (format: grindsession_team_name or grindsession_event_team)

        Returns:
            Team object or None
        """
        try:
            # TODO: Implement after inspecting Grind Session teams/event pages
            # Pattern similar to other adapters:
            # 1. Fetch teams/event page
            # 2. Find table or team cards
            # 3. Parse team info
            # 4. Return Team object

            # NOTE: Teams may vary by event
            # Example: "Team USA" may have different rosters in different events
            # Consider including event_id in team_id: "grindsession_event123_teamusa"

            self.logger.warning("Grind Session team lookup requires teams page structure")
            return None

        except Exception as e:
            self.logger.error(f"Failed to get Grind Session team {team_id}", error=str(e))
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
        Get games from Grind Session events.

        IMPLEMENTATION STEPS:
        1. Visit https://thegrindsession.com/events
        2. Click on an event to see the schedule
        3. Look for games table or schedule cards
        4. Note fields: date, time, teams, scores, status, location
        5. Inspect HTML structure
        6. Implement parsing similar to OTE adapter
        7. Handle multiple events

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season/event
            limit: Maximum results

        Returns:
            List of Game objects
        """
        try:
            # TODO: Implement after inspecting Grind Session schedule pages
            # Event-based structure means games are organized by event
            # May need to:
            # 1. List all events (or filter by season)
            # 2. For each event, fetch schedule
            # 3. Parse games and filter by criteria
            # 4. Return aggregated list

            self.logger.warning(
                "Grind Session schedule parsing requires event/schedule page structure"
            )
            return []

        except Exception as e:
            self.logger.error("Failed to get Grind Session games", error=str(e))
            return []

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard from Grind Session.

        IMPLEMENTATION STEPS:
        1. Grind Session may publish event-specific or season-wide leaderboards
        2. To get leaderboard, fetch the stats table and sort by requested stat
        3. The stats table from search_players() can be reused here
        4. Extract stat values and sort
        5. May need to aggregate across multiple events for season leaderboards

        Args:
            stat: Stat category (points, rebounds, assists, etc.)
            season: Season/event filter
            limit: Maximum results

        Returns:
            List of leaderboard entries
        """
        try:
            # Fetch stats page
            html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find stats table
            table = find_stat_table(soup, table_class_hint="stats")
            if not table:
                return []

            # Extract rows
            rows = extract_table_data(table)

            # Build leaderboard entries
            leaderboard = []

            # Map stat name to column name
            # UPDATE these after inspecting actual table headers
            stat_column_map = {
                "points": "PPG",
                "rebounds": "RPG",
                "assists": "APG",
                "steals": "SPG",
                "blocks": "BPG",
                "field_goal_pct": "FG%",
                "three_point_pct": "3P%",
                "free_throw_pct": "FT%",
            }

            stat_column = stat_column_map.get(stat.lower(), stat.upper())

            for row in rows:
                player_name = row.get("Player") or row.get("NAME")
                team_name = row.get("Team") or row.get("TEAM")
                event_name = row.get("Event") or row.get("TOURNAMENT")

                # Try to find stat value
                stat_value = parse_float(row.get(stat_column) or row.get(stat.upper()))

                if player_name and stat_value is not None:
                    entry = build_leaderboard_entry(
                        rank=0,  # Will be set after sorting
                        player_name=player_name,
                        stat_value=stat_value,
                        stat_name=stat,
                        season=season or "2024-25",
                        source_prefix="grindsession",
                        team_name=team_name,
                    )

                    # Add event info if available
                    if event_name:
                        entry["event"] = event_name

                    leaderboard.append(entry)

            # Sort by stat value (descending)
            leaderboard.sort(key=lambda x: x["stat_value"], reverse=True)

            # Set ranks
            for i, entry in enumerate(leaderboard[:limit], 1):
                entry["rank"] = i

            self.logger.info(
                f"Grind Session {stat} leaderboard returned {len(leaderboard[:limit])} entries"
            )
            return leaderboard[:limit]

        except Exception as e:
            self.logger.error(
                f"Failed to get Grind Session {stat} leaderboard", error=str(e)
            )
            return []


# ==============================================================================
# IMPLEMENTATION CHECKLIST
# ==============================================================================
# Before marking this adapter as complete, verify:
#
# [ ] 1. All URL endpoints are actual Grind Session URLs (not placeholders)
# [ ] 2. Understand event-based organization vs traditional season structure
# [ ] 3. Table finding logic tested with real HTML
# [ ] 4. Column name mappings verified against actual table headers
# [ ] 5. At least 3 test cases passing (search, stats, leaderboard)
# [ ] 6. Rate limiting tested (no 429 errors)
# [ ] 7. Data validation passing (no negative stats, valid ranges)
# [ ] 8. Error handling tested (404s, timeouts, malformed HTML)
# [ ] 9. Event ID handling implemented correctly
# [ ] 10. Multiple event aggregation working (if needed)
# [ ] 11. Logging statements provide useful debugging info
# [ ] 12. Integration tested through aggregation service
# [ ] 13. Documentation updated in PROJECT_LOG.md
#
# ==============================================================================
# TESTING COMMANDS
# ==============================================================================
# Run these commands to test the adapter:
#
# # Test player search
# pytest tests/test_datasources/test_grind_session.py::TestGrindSessionDataSource::test_search_players -v -s
#
# # Test season stats
# pytest tests/test_datasources/test_grind_session.py::TestGrindSessionDataSource::test_get_player_season_stats -v -s
#
# # Test leaderboard
# pytest tests/test_datasources/test_grind_session.py::TestGrindSessionDataSource::test_get_leaderboard -v -s
#
# # Test event handling
# pytest tests/test_datasources/test_grind_session.py::TestGrindSessionDataSource::test_event_handling -v -s
#
# # Test rate limiting
# pytest tests/test_datasources/test_grind_session.py::TestGrindSessionDataSource::test_rate_limiting -v -s
#
# # Run all Grind Session tests
# pytest tests/test_datasources/test_grind_session.py -v
#
# ==============================================================================
