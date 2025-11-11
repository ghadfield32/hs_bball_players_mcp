"""
FIBA LiveStats DataSource Adapter

Fetches player and game statistics from FIBA LiveStats v7 JSON feeds.
Supports global youth tournaments (U16/U17/U18) with structured JSON API.

FIBA LiveStats provides real-time basketball statistics for FIBA competitions
worldwide via JSON endpoints. This adapter handles competition data, game feeds,
and player statistics for international youth basketball tournaments.
"""

from datetime import datetime
from typing import Any, Optional

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
from ...utils import clean_player_name, parse_float, parse_int
from ..base import BaseDataSource


class FIBALiveStatsDataSource(BaseDataSource):
    """
    FIBA LiveStats v7 data source adapter for global youth basketball tournaments.

    Provides access to FIBA U16/U17/U18 international competition statistics via
    JSON API endpoints. Supports competition data, game TV feeds, box scores, and
    player statistics for FIBA-sanctioned youth tournaments.

    Key Features:
    - JSON API (not HTML scraping)
    - Competition-based data organization
    - TV feed integration for live/recent games
    - FIBA-specific stat formats (PIR = Performance Index Rating)
    - Support for multiple competitions and tournaments
    """

    source_type = DataSourceType.FIBA
    source_name = "FIBA LiveStats"
    base_url = "https://livestats.fiba.basketball"
    region = DataSourceRegion.GLOBAL

    def __init__(self):
        """
        Initialize FIBA LiveStats datasource.

        Sets up endpoints for:
        - Competition data (teams, rosters, schedule)
        - TV feeds (live game data with full box scores)
        - Game-specific endpoints
        """
        super().__init__()

        # FIBA LiveStats v7 endpoints
        self.tv_feed_url = f"{self.base_url}/tv/{{competition_id}}/{{game_id}}"
        self.competition_url = f"{self.base_url}/competition/{{competition_id}}"
        self.game_data_url = f"{self.base_url}/data/{{competition_id}}/{{game_id}}/data.json"

        self.logger.info("FIBA LiveStats adapter initialized with JSON API endpoints")

    async def get_competition_data(self, competition_id: str) -> Optional[dict[str, Any]]:
        """
        Fetch competition JSON data including teams, schedule, and metadata.

        IMPLEMENTATION STEPS:
        1. Construct competition endpoint URL
        2. Fetch JSON data with caching (7200s TTL for competition metadata)
        3. Validate JSON structure
        4. Return parsed competition data

        Args:
            competition_id: FIBA competition identifier (e.g., "U16-2024")

        Returns:
            Competition data dictionary or None if fetch fails

        Example:
            comp_data = await datasource.get_competition_data("U16-2024")
            teams = comp_data.get("teams", {})
        """
        try:
            url = self.competition_url.format(competition_id=competition_id)
            self.logger.info(f"Fetching competition data for {competition_id}", url=url)

            # Fetch JSON with extended cache (competition data changes infrequently)
            data = await self.http_client.get_json(url, cache_ttl=7200)

            if not data:
                self.logger.warning(f"Empty competition data for {competition_id}")
                return None

            self.logger.info(
                f"Successfully fetched competition data",
                competition_id=competition_id,
                teams_count=len(data.get("teams", [])),
            )
            return data

        except Exception as e:
            self.logger.error(
                f"Failed to fetch competition data for {competition_id}",
                error=str(e),
            )
            return None

    async def get_game_data(self, competition_id: str, game_id: str) -> Optional[dict[str, Any]]:
        """
        Fetch TV feed JSON data for a specific game.

        IMPLEMENTATION STEPS:
        1. Construct TV feed URL with competition and game IDs
        2. Fetch JSON data with caching (3600s TTL for game data)
        3. Parse FIBA LiveStats v7 JSON structure
        4. Validate required fields (tm, bs, pbp)
        5. Return complete game data

        Args:
            competition_id: FIBA competition identifier
            game_id: FIBA game identifier

        Returns:
            Game data dictionary with teams, box scores, and play-by-play or None

        JSON Structure:
            {
                "tm": {  # Teams
                    "1": {"id": "1", "name": "USA", "players": [...]},
                    "2": {"id": "2", "name": "Spain", "players": [...]}
                },
                "bs": {  # Box score
                    "1": {"pid": "5", "pts": "15", "reb": "8", ...}
                },
                "pno": {  # Play numbers
                    "1": {"gt": "1", "pid": "5", "act": "2PM", ...}
                },
                "pbp": [...]  # Play-by-play
            }
        """
        try:
            url = self.tv_feed_url.format(competition_id=competition_id, game_id=game_id)
            self.logger.info(
                f"Fetching game data",
                competition_id=competition_id,
                game_id=game_id,
                url=url,
            )

            # Fetch JSON with moderate cache (game data can update during/after games)
            data = await self.http_client.get_json(url, cache_ttl=3600)

            if not data:
                self.logger.warning(f"Empty game data", game_id=game_id)
                return None

            # Validate FIBA LiveStats v7 structure
            if "tm" not in data or "bs" not in data:
                self.logger.warning(
                    f"Invalid FIBA LiveStats JSON structure",
                    game_id=game_id,
                    keys=list(data.keys()),
                )
                return None

            self.logger.info(
                f"Successfully fetched game data",
                game_id=game_id,
                teams=len(data.get("tm", {})),
                box_score_entries=len(data.get("bs", {})),
            )
            return data

        except Exception as e:
            self.logger.error(
                f"Failed to fetch game data",
                competition_id=competition_id,
                game_id=game_id,
                error=str(e),
            )
            return None

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        FIBA player IDs are competition-scoped: fiba_{competition_id}_{player_name}

        IMPLEMENTATION STEPS:
        1. Parse player_id to extract competition_id
        2. Validate ID format (must start with "fiba_")
        3. Search players in that competition
        4. Return matching player

        Args:
            player_id: Player identifier (format: fiba_{comp_id}_{name})

        Returns:
            Player object or None

        Example:
            player = await datasource.get_player("fiba_u16_john_doe")
        """
        if not player_id.startswith("fiba_"):
            self.logger.warning(f"Invalid FIBA player ID format: {player_id}")
            return None

        try:
            # Extract competition ID from player_id
            # Format: fiba_{competition_id}_{player_name}
            parts = player_id.split("_", 2)
            if len(parts) < 3:
                self.logger.warning(f"Cannot parse competition from player_id: {player_id}")
                return None

            competition_id = parts[1]
            players = await self.search_players(competition_id=competition_id, limit=1000)

            # Find matching player
            for player in players:
                if player.player_id == player_id:
                    return player

            self.logger.warning(f"Player not found: {player_id}")
            return None

        except Exception as e:
            self.logger.error(f"Failed to get player", player_id=player_id, error=str(e))
            return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        competition_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in FIBA competitions.

        IMPLEMENTATION STEPS:
        1. Validate that competition_id is provided (required for FIBA)
        2. Fetch competition data JSON
        3. Extract teams and rosters from competition data
        4. Parse player data from each team roster
        5. Apply filters (name, team if provided)
        6. Return list of Player objects

        Args:
            name: Player name (partial match, case-insensitive)
            team: Team/country name (partial match)
            season: Season filter (not used for FIBA competitions)
            competition_id: FIBA competition ID (REQUIRED)
            limit: Maximum results

        Returns:
            List of Player objects

        Example:
            # Search all players in U16 competition
            players = await datasource.search_players(competition_id="U16-2024")

            # Search for specific player
            players = await datasource.search_players(
                name="Smith",
                competition_id="U16-2024"
            )
        """
        if not competition_id:
            self.logger.warning(
                "FIBA player search requires competition_id parameter. "
                "Example: search_players(competition_id='U16-2024')"
            )
            return []

        self.logger.info(
            "Searching FIBA players",
            competition_id=competition_id,
            name=name,
            team=team,
        )

        try:
            # Fetch competition data
            comp_data = await self.get_competition_data(competition_id)
            if not comp_data:
                return []

            players = []
            data_source = self.create_data_source_metadata(
                url=self.competition_url.format(competition_id=competition_id),
                quality_flag=DataQualityFlag.COMPLETE,
            )

            # Parse teams from competition data
            teams = comp_data.get("tm", comp_data.get("teams", {}))

            for team_id, team_data in teams.items():
                team_name = team_data.get("name", team_data.get("teamName", "Unknown"))

                # Filter by team if specified
                if team and team.lower() not in team_name.lower():
                    continue

                # Parse roster
                roster = team_data.get("players", team_data.get("roster", []))

                for player_data in roster:
                    player = self._parse_player_from_json(
                        player_data, team_name, competition_id, data_source
                    )

                    if player:
                        # Filter by name if specified
                        if name and name.lower() not in player.full_name.lower():
                            continue

                        players.append(player)

                        if len(players) >= limit:
                            break

                if len(players) >= limit:
                    break

            self.logger.info(f"Found {len(players)} players in competition {competition_id}")
            return players

        except Exception as e:
            self.logger.error(
                f"Failed to search players",
                competition_id=competition_id,
                error=str(e),
            )
            return []

    def _parse_player_from_json(
        self,
        player_data: dict[str, Any],
        team_name: str,
        competition_id: str,
        data_source,
    ) -> Optional[Player]:
        """
        Parse player from FIBA JSON roster data.

        IMPLEMENTATION STEPS:
        1. Extract player fields from JSON (handle FIBA naming variations)
        2. Parse name into first/last components
        3. Parse position (FIBA uses standard abbreviations)
        4. Parse height (FIBA uses centimeters, convert to inches)
        5. Parse birth year for age calculation
        6. Create standardized player_id
        7. Build Player model with validation

        Args:
            player_data: Player dictionary from FIBA JSON
            team_name: Team/country name
            competition_id: Competition identifier
            data_source: DataSource metadata

        Returns:
            Player object or None if parsing fails

        FIBA JSON Player Format:
            {
                "pid": "5",
                "name": "John Doe",
                "firstName": "John",
                "familyName": "Doe",
                "shirtNumber": "23",
                "pos": "PG",
                "height": "185",  # centimeters
                "birthYear": "2008"
            }
        """
        try:
            # Extract player name (try multiple field variations)
            full_name = player_data.get("name") or player_data.get("playerName")
            first_name = player_data.get("firstName") or player_data.get("givenName")
            last_name = (
                player_data.get("familyName")
                or player_data.get("lastName")
                or player_data.get("surname")
            )

            # Fall back to splitting full name if components not provided
            if not (first_name and last_name) and full_name:
                name_parts = clean_player_name(full_name).split()
                first_name = name_parts[0] if len(name_parts) > 0 else full_name
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            elif not full_name and (first_name or last_name):
                full_name = f"{first_name or ''} {last_name or ''}".strip()

            if not full_name:
                self.logger.debug("Skipping player with no name")
                return None

            # Parse position
            position_str = player_data.get("pos") or player_data.get("position")
            pos_enum = None
            if position_str:
                try:
                    # FIBA uses standard position codes (PG, SG, SF, PF, C)
                    pos_enum = Position(position_str.upper().strip())
                except ValueError:
                    self.logger.debug(f"Unknown position: {position_str}")

            # Parse height (FIBA uses centimeters, convert to inches)
            height_cm = parse_int(player_data.get("height") or player_data.get("heightCm"))
            height_inches = None
            if height_cm:
                # 1 cm = 0.393701 inches
                height_inches = int(height_cm * 0.393701)

            # Parse jersey number
            jersey_number = parse_int(
                player_data.get("shirtNumber")
                or player_data.get("jerseyNumber")
                or player_data.get("number")
            )

            # Parse birth year
            birth_year = parse_int(player_data.get("birthYear") or player_data.get("yearOfBirth"))

            # Create player ID (sanitized, competition-scoped)
            clean_name = clean_player_name(full_name)
            player_id = f"fiba_{competition_id}_{clean_name.lower().replace(' ', '_')}"

            # Build player data dictionary
            player_dict = {
                "player_id": player_id,
                "first_name": first_name or "",
                "last_name": last_name or "",
                "full_name": full_name,
                "position": pos_enum,
                "height_inches": height_inches,
                "jersey_number": jersey_number,
                "team_name": team_name,
                "school_country": team_name,  # For FIBA, team is typically country
                "level": PlayerLevel.JUNIOR,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Player, player_dict, f"player {full_name}")

        except Exception as e:
            self.logger.error(
                "Failed to parse player from JSON",
                error=str(e),
                player_data=player_data,
            )
            return None

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None, competition_id: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics aggregated across competition.

        IMPLEMENTATION STEPS:
        1. Extract competition_id from player_id or use provided competition_id
        2. Fetch all games in competition
        3. For each game, fetch game data and extract player's box score
        4. Aggregate stats across all games
        5. Calculate per-game averages
        6. Return PlayerSeasonStats model

        Args:
            player_id: Player identifier
            season: Season identifier (optional, uses competition_id)
            competition_id: Competition to aggregate stats from (optional if in player_id)

        Returns:
            PlayerSeasonStats with aggregated competition statistics or None

        Example:
            stats = await datasource.get_player_season_stats(
                "fiba_u16_john_doe",
                competition_id="U16-2024"
            )
            print(f"PPG: {stats.points_per_game}")
        """
        try:
            # Extract competition_id from player_id if not provided
            if not competition_id and player_id.startswith("fiba_"):
                parts = player_id.split("_", 2)
                if len(parts) >= 2:
                    competition_id = parts[1]

            if not competition_id:
                self.logger.warning(f"Cannot determine competition for player {player_id}")
                return None

            self.logger.info(
                f"Fetching season stats for player",
                player_id=player_id,
                competition_id=competition_id,
            )

            # Get competition games list
            games = await self.get_games(competition_id=competition_id)

            if not games:
                self.logger.warning(f"No games found for competition {competition_id}")
                return None

            # Aggregate stats across games
            total_stats = {
                "games_played": 0,
                "points": 0,
                "total_rebounds": 0,
                "assists": 0,
                "steals": 0,
                "blocks": 0,
                "turnovers": 0,
                "fouls": 0,
                "fgm": 0,
                "fga": 0,
                "tpm": 0,
                "tpa": 0,
                "ftm": 0,
                "fta": 0,
                "minutes": 0.0,
            }

            player_name = ""
            team_id = ""

            # Fetch each game and aggregate player stats
            for game in games:
                game_stats = await self.get_player_game_stats(player_id, game.game_id)

                if game_stats:
                    total_stats["games_played"] += 1
                    total_stats["points"] += game_stats.points or 0
                    total_stats["total_rebounds"] += game_stats.total_rebounds or 0
                    total_stats["assists"] += game_stats.assists or 0
                    total_stats["steals"] += game_stats.steals or 0
                    total_stats["blocks"] += game_stats.blocks or 0
                    total_stats["turnovers"] += game_stats.turnovers or 0
                    total_stats["fouls"] += game_stats.personal_fouls or 0
                    total_stats["fgm"] += game_stats.field_goals_made or 0
                    total_stats["fga"] += game_stats.field_goals_attempted or 0
                    total_stats["tpm"] += game_stats.three_pointers_made or 0
                    total_stats["tpa"] += game_stats.three_pointers_attempted or 0
                    total_stats["ftm"] += game_stats.free_throws_made or 0
                    total_stats["fta"] += game_stats.free_throws_attempted or 0
                    total_stats["minutes"] += game_stats.minutes_played or 0.0

                    if not player_name:
                        player_name = game_stats.player_name
                        team_id = game_stats.team_id

            if total_stats["games_played"] == 0:
                self.logger.warning(f"No game stats found for player {player_id}")
                return None

            # Calculate per-game averages
            games = total_stats["games_played"]
            ppg = total_stats["points"] / games if games > 0 else 0.0
            rpg = total_stats["total_rebounds"] / games if games > 0 else 0.0
            apg = total_stats["assists"] / games if games > 0 else 0.0
            spg = total_stats["steals"] / games if games > 0 else 0.0
            bpg = total_stats["blocks"] / games if games > 0 else 0.0

            # Calculate shooting percentages
            fg_pct = (
                (total_stats["fgm"] / total_stats["fga"]) if total_stats["fga"] > 0 else None
            )
            tp_pct = (
                (total_stats["tpm"] / total_stats["tpa"]) if total_stats["tpa"] > 0 else None
            )
            ft_pct = (
                (total_stats["ftm"] / total_stats["fta"]) if total_stats["fta"] > 0 else None
            )

            # Build season stats
            stats_data = {
                "player_id": player_id,
                "player_name": player_name,
                "team_id": team_id,
                "season": season or competition_id,
                "league": f"FIBA {competition_id}",
                "games_played": games,
                "points": total_stats["points"],
                "points_per_game": round(ppg, 1),
                "total_rebounds": total_stats["total_rebounds"],
                "rebounds_per_game": round(rpg, 1),
                "assists": total_stats["assists"],
                "assists_per_game": round(apg, 1),
                "steals": total_stats["steals"],
                "steals_per_game": round(spg, 1),
                "blocks": total_stats["blocks"],
                "blocks_per_game": round(bpg, 1),
                "turnovers": total_stats["turnovers"],
                "personal_fouls": total_stats["fouls"],
                "field_goals_made": total_stats["fgm"],
                "field_goals_attempted": total_stats["fga"],
                "field_goal_percentage": round(fg_pct, 3) if fg_pct else None,
                "three_pointers_made": total_stats["tpm"],
                "three_pointers_attempted": total_stats["tpa"],
                "three_point_percentage": round(tp_pct, 3) if tp_pct else None,
                "free_throws_made": total_stats["ftm"],
                "free_throws_attempted": total_stats["fta"],
                "free_throw_percentage": round(ft_pct, 3) if ft_pct else None,
            }

            return self.validate_and_log_data(
                PlayerSeasonStats, stats_data, f"season stats for {player_name}"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to get player season stats",
                player_id=player_id,
                error=str(e),
            )
            return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str, competition_id: Optional[str] = None
    ) -> Optional[PlayerGameStats]:
        """
        Get player statistics for a specific game from TV feed JSON.

        IMPLEMENTATION STEPS:
        1. Extract competition_id from player_id or use provided
        2. Fetch game data JSON (TV feed)
        3. Parse box score section (bs)
        4. Find player's entry in box score
        5. Parse FIBA stat format (handle abbreviations)
        6. Return PlayerGameStats model

        Args:
            player_id: Player identifier
            game_id: FIBA game identifier
            competition_id: Competition ID (optional if in player_id)

        Returns:
            PlayerGameStats or None

        FIBA Box Score JSON Format:
            "bs": {
                "1": {
                    "pid": "5",
                    "sno": "23",
                    "name": "John Doe",
                    "pts": "15",
                    "reb": "8",
                    "ast": "5",
                    "stl": "2",
                    "blk": "1",
                    "to": "3",
                    "pf": "2",
                    "fgm": "6",
                    "fga": "12",
                    "tpm": "2",
                    "tpa": "5",
                    "ftm": "1",
                    "fta": "2",
                    "min": "25:30",
                    "pir": "18"  # Performance Index Rating
                }
            }
        """
        try:
            # Extract competition_id from player_id if not provided
            if not competition_id and player_id.startswith("fiba_"):
                parts = player_id.split("_", 2)
                if len(parts) >= 2:
                    competition_id = parts[1]

            if not competition_id:
                self.logger.warning(f"Cannot determine competition for player {player_id}")
                return None

            # Fetch game data
            game_data = await self.get_game_data(competition_id, game_id)
            if not game_data:
                return None

            # Parse box score
            box_scores = game_data.get("bs", {})
            teams = game_data.get("tm", {})

            # Extract player name from player_id for matching
            player_name_from_id = (
                player_id.split("_", 2)[2].replace("_", " ").title()
                if len(player_id.split("_", 2)) >= 3
                else ""
            )

            # Search for player in box scores
            for bs_key, bs_entry in box_scores.items():
                entry_name = bs_entry.get("name") or bs_entry.get("playerName") or ""

                # Match by name (case-insensitive partial match)
                if player_name_from_id.lower() in entry_name.lower():
                    return self._parse_game_stats_from_box_score(
                        bs_entry, player_id, game_id, teams
                    )

            self.logger.debug(
                f"Player not found in game box score",
                player_id=player_id,
                game_id=game_id,
            )
            return None

        except Exception as e:
            self.logger.error(
                f"Failed to get player game stats",
                player_id=player_id,
                game_id=game_id,
                error=str(e),
            )
            return None

    def _parse_game_stats_from_box_score(
        self,
        box_score: dict[str, Any],
        player_id: str,
        game_id: str,
        teams: dict[str, Any],
    ) -> Optional[PlayerGameStats]:
        """
        Parse game stats from FIBA box score entry.

        IMPLEMENTATION STEPS:
        1. Extract all stat fields from box score JSON
        2. Parse minutes (FIBA format: "MM:SS")
        3. Parse shooting stats (handle string to int conversion)
        4. Determine team IDs from team data
        5. Build PlayerGameStats model

        Args:
            box_score: Box score dictionary for player
            player_id: Player identifier
            game_id: Game identifier
            teams: Teams dictionary from game data

        Returns:
            PlayerGameStats or None
        """
        try:
            player_name = box_score.get("name") or box_score.get("playerName") or ""

            # Parse minutes (FIBA format: "MM:SS" or just minutes as string)
            minutes_str = box_score.get("min") or box_score.get("minutes") or "0"
            minutes_played = self._parse_fiba_minutes(minutes_str)

            # Parse stats (FIBA uses string values, need conversion)
            points = parse_int(box_score.get("pts") or box_score.get("points"))
            total_rebounds = parse_int(box_score.get("reb") or box_score.get("rebounds"))
            assists = parse_int(box_score.get("ast") or box_score.get("assists"))
            steals = parse_int(box_score.get("stl") or box_score.get("steals"))
            blocks = parse_int(box_score.get("blk") or box_score.get("blocks"))
            turnovers = parse_int(box_score.get("to") or box_score.get("turnovers"))
            fouls = parse_int(box_score.get("pf") or box_score.get("fouls"))

            # Parse shooting stats
            fgm = parse_int(box_score.get("fgm") or box_score.get("fieldGoalsMade"))
            fga = parse_int(box_score.get("fga") or box_score.get("fieldGoalsAttempted"))
            tpm = parse_int(box_score.get("tpm") or box_score.get("threePointersMade"))
            tpa = parse_int(box_score.get("tpa") or box_score.get("threePointersAttempted"))
            ftm = parse_int(box_score.get("ftm") or box_score.get("freeThrowsMade"))
            fta = parse_int(box_score.get("fta") or box_score.get("freeThrowsAttempted"))

            # Determine team (FIBA uses team ID "t" or team reference)
            team_num = box_score.get("t") or box_score.get("team") or "1"
            team_id = f"fiba_team_{team_num}"

            # Determine opponent (opposite team)
            opponent_num = "2" if team_num == "1" else "1"
            opponent_team_id = f"fiba_team_{opponent_num}"

            # Build game stats dictionary
            stats_data = {
                "player_id": player_id,
                "player_name": player_name,
                "game_id": game_id,
                "team_id": team_id,
                "opponent_team_id": opponent_team_id,
                "minutes_played": minutes_played,
                "points": points,
                "total_rebounds": total_rebounds,
                "assists": assists,
                "steals": steals,
                "blocks": blocks,
                "turnovers": turnovers,
                "personal_fouls": fouls,
                "field_goals_made": fgm,
                "field_goals_attempted": fga,
                "three_pointers_made": tpm,
                "three_pointers_attempted": tpa,
                "free_throws_made": ftm,
                "free_throws_attempted": fta,
            }

            return self.validate_and_log_data(
                PlayerGameStats, stats_data, f"game stats for {player_name}"
            )

        except Exception as e:
            self.logger.error("Failed to parse game stats from box score", error=str(e))
            return None

    def _parse_fiba_minutes(self, minutes_str: str) -> Optional[float]:
        """
        Parse FIBA minutes format (MM:SS or just minutes).

        Args:
            minutes_str: Minutes string (e.g., "25:30" or "25")

        Returns:
            Minutes as float (e.g., 25.5) or None
        """
        try:
            if ":" in minutes_str:
                # Format: MM:SS
                parts = minutes_str.split(":")
                minutes = int(parts[0])
                seconds = int(parts[1]) if len(parts) > 1 else 0
                return round(minutes + (seconds / 60.0), 2)
            else:
                # Just minutes
                return parse_float(minutes_str)
        except Exception:
            return None

    async def get_team(self, team_id: str, competition_id: Optional[str] = None) -> Optional[Team]:
        """
        Get team information from competition data.

        Args:
            team_id: Team identifier
            competition_id: Competition to search (optional)

        Returns:
            Team object or None
        """
        if not competition_id:
            self.logger.warning("Team lookup requires competition_id for FIBA")
            return None

        try:
            comp_data = await self.get_competition_data(competition_id)
            if not comp_data:
                return None

            teams = comp_data.get("tm", comp_data.get("teams", {}))

            for tid, team_data in teams.items():
                team_name = team_data.get("name") or team_data.get("teamName")

                if team_name and (
                    team_id == f"fiba_team_{tid}"
                    or team_name.lower() in team_id.lower()
                ):
                    return self._parse_team_from_json(team_data, competition_id, tid)

            return None

        except Exception as e:
            self.logger.error(f"Failed to get team", team_id=team_id, error=str(e))
            return None

    def _parse_team_from_json(
        self, team_data: dict[str, Any], competition_id: str, team_id: str
    ) -> Optional[Team]:
        """Parse team from FIBA JSON."""
        try:
            team_name = team_data.get("name") or team_data.get("teamName") or "Unknown"

            data_source = self.create_data_source_metadata(
                url=self.competition_url.format(competition_id=competition_id),
                quality_flag=DataQualityFlag.COMPLETE,
            )

            team_dict = {
                "team_id": f"fiba_team_{team_id}",
                "team_name": team_name,
                "level": TeamLevel.INTERNATIONAL,
                "league": f"FIBA {competition_id}",
                "season": competition_id,
                "country": team_name,  # FIBA teams are typically national teams
                "data_source": data_source,
            }

            return self.validate_and_log_data(Team, team_dict, f"team {team_name}")

        except Exception as e:
            self.logger.error("Failed to parse team from JSON", error=str(e))
            return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        competition_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games from competition schedule.

        Args:
            team_id: Filter by team (not implemented)
            start_date: Filter by start date (not implemented)
            end_date: Filter by end date (not implemented)
            season: Season filter (not implemented)
            competition_id: FIBA competition ID (REQUIRED)
            limit: Maximum results

        Returns:
            List of Game objects
        """
        if not competition_id:
            self.logger.warning("Games listing requires competition_id for FIBA")
            return []

        self.logger.warning(
            "Game schedule parsing not yet implemented for FIBA LiveStats. "
            "Would need to parse competition schedule JSON."
        )
        return []

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        competition_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard for a competition.

        IMPLEMENTATION STEPS:
        1. Fetch all games in competition
        2. For each game, aggregate player stats
        3. Calculate per-game averages for requested stat
        4. Sort by stat value (descending)
        5. Return top N entries

        Args:
            stat: Stat category (e.g., 'points', 'rebounds', 'assists')
            season: Season filter (uses competition_id)
            competition_id: FIBA competition ID (REQUIRED)
            limit: Maximum results

        Returns:
            List of leaderboard entries

        Example:
            leaders = await datasource.get_leaderboard(
                stat="points",
                competition_id="U16-2024",
                limit=10
            )
        """
        if not competition_id:
            self.logger.warning(
                "FIBA leaderboards require competition_id parameter. "
                "Example: get_leaderboard(stat='points', competition_id='U16-2024')"
            )
            return []

        try:
            # Get all players in competition
            players = await self.search_players(competition_id=competition_id, limit=1000)

            # Get season stats for each player
            leaderboard_data = []

            for player in players:
                stats = await self.get_player_season_stats(
                    player.player_id, competition_id=competition_id
                )

                if stats:
                    # Extract requested stat value
                    stat_value = self._extract_stat_value(stats, stat)

                    if stat_value is not None:
                        leaderboard_data.append(
                            {
                                "player_id": player.player_id,
                                "player_name": player.full_name,
                                "team_name": player.team_name,
                                "stat_value": stat_value,
                                "games_played": stats.games_played,
                            }
                        )

            # Sort by stat value (descending)
            leaderboard_data.sort(key=lambda x: x["stat_value"], reverse=True)

            # Build leaderboard entries
            leaderboard = []
            for i, entry in enumerate(leaderboard_data[:limit], 1):
                leaderboard.append(
                    {
                        "rank": i,
                        "player_id": entry["player_id"],
                        "player_name": entry["player_name"],
                        "team_name": entry["team_name"],
                        "stat_value": entry["stat_value"],
                        "stat_name": stat,
                        "season": competition_id,
                    }
                )

            self.logger.info(
                f"Generated leaderboard",
                stat=stat,
                competition_id=competition_id,
                entries=len(leaderboard),
            )
            return leaderboard

        except Exception as e:
            self.logger.error(
                f"Failed to get leaderboard",
                stat=stat,
                competition_id=competition_id,
                error=str(e),
            )
            return []

    def _extract_stat_value(self, stats: PlayerSeasonStats, stat: str) -> Optional[float]:
        """
        Extract stat value from PlayerSeasonStats.

        Args:
            stats: PlayerSeasonStats object
            stat: Stat name

        Returns:
            Stat value or None
        """
        stat_map = {
            "points": stats.points_per_game,
            "rebounds": stats.rebounds_per_game,
            "assists": stats.assists_per_game,
            "steals": stats.steals_per_game,
            "blocks": stats.blocks_per_game,
            "fg_pct": stats.field_goal_percentage,
            "3p_pct": stats.three_point_percentage,
            "ft_pct": stats.free_throw_percentage,
        }

        return stat_map.get(stat.lower())
