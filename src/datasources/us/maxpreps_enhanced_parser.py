"""
Enhanced MaxPreps Parser Methods

These methods replace the existing parsing logic in maxpreps.py
to extract ALL available statistics from MaxPreps stat leader pages.

**INTEGRATION**: Replace methods in src/datasources/us/maxpreps.py
with these enhanced versions.

Author: Claude Code
Date: 2025-11-14
"""

from typing import Optional, Tuple
from src.models import Player, PlayerSeasonStats, PlayerLevel, Position, DataSource
from src.utils import parse_float, parse_int


def _parse_player_and_stats_from_row(
    self,
    row: dict,
    state: str,
    data_source: DataSource,
    season: Optional[str] = None
) -> Tuple[Optional[Player], Optional[PlayerSeasonStats]]:
    """
    Parse BOTH player info AND season statistics from MaxPreps stats table row.

    **ENHANCED VERSION** - Extracts all available metrics from stat leader pages.

    MaxPreps stat leader tables typically include:
    - Player info: Name, School, Class, Position, Height, Weight
    - Season stats: PPG, RPG, APG, SPG, BPG, FG%, 3P%, FT%, GP

    Args:
        row: Dictionary of column_name -> value from stats table
        state: State code for context
        data_source: DataSource metadata object
        season: Season string (e.g., "2024-25")

    Returns:
        Tuple of (Player, PlayerSeasonStats) or (None, None) if parsing fails

    Example row:
        {
            "Rank": "1",
            "Player": "John Doe",
            "School": "Lincoln High School",
            "Class": "2026",
            "Pos": "SG",
            "GP": "25",
            "PPG": "25.3",
            "RPG": "5.2",
            "APG": "4.1",
            "SPG": "2.3",
            "BPG": "0.8",
            "FG%": "52.5",
            "3P%": "38.2",
            "FT%": "85.0",
            ...
        }
    """
    try:
        # ========================================
        # STEP 1: Extract Player Information
        # ========================================

        # Extract player name (various possible column names)
        player_name = (
            row.get("Player") or
            row.get("NAME") or
            row.get("Name") or
            row.get("PLAYER") or
            row.get("Athlete")  # Some sites use "Athlete"
        )

        if not player_name:
            self.logger.debug("No player name found in row", row_keys=list(row.keys()))
            return None, None

        # Clean player name
        player_name = player_name.strip()

        # Split into first/last name
        name_parts = player_name.split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
        else:
            first_name = player_name
            last_name = ""

        # Extract school
        school_name = (
            row.get("School") or
            row.get("SCHOOL") or
            row.get("Team") or
            row.get("TEAM") or
            row.get("High School")
        )

        # Extract position
        position_str = (
            row.get("Pos") or
            row.get("POS") or
            row.get("Position") or
            row.get("POSITION")
        )

        position = None
        if position_str:
            # Map to Position enum
            position_map = {
                "PG": Position.PG, "SG": Position.SG,
                "SF": Position.SF, "PF": Position.PF,
                "C": Position.C, "G": Position.G,
                "F": Position.F, "GF": Position.GF,
                "FC": Position.FC
            }
            position = position_map.get(position_str.upper().strip())

        # Extract grad year
        grad_year = None
        class_str = (
            row.get("Class") or
            row.get("CLASS") or
            row.get("Yr") or
            row.get("Year") or
            row.get("Grad Year")
        )

        if class_str:
            from src.utils.scraping_helpers import parse_grad_year
            grad_year = parse_grad_year(class_str)

        # Extract height (various formats: "6-5", "6'5\"", "77")
        height_str = (
            row.get("Ht") or
            row.get("Height") or
            row.get("HT") or
            row.get("H")
        )

        height_inches = None
        if height_str:
            try:
                height_str = str(height_str).strip()
                # Handle formats: "6-5", "6'5\"", or "77"
                if "-" in height_str or "'" in height_str:
                    parts = height_str.replace("'", "-").replace('"', "").split("-")
                    if len(parts) == 2:
                        feet = parse_int(parts[0])
                        inches = parse_int(parts[1])
                        if feet and inches:
                            height_inches = (feet * 12) + inches
                else:
                    # Direct inches
                    height_inches = parse_int(height_str)
            except:
                pass

        # Extract weight
        weight_str = (
            row.get("Wt") or
            row.get("Weight") or
            row.get("WT") or
            row.get("W")
        )
        weight_lbs = parse_int(weight_str) if weight_str else None

        # Build player ID
        player_id = self._build_player_id(state, player_name, school_name)

        # Create Player object
        player = Player(
            player_id=player_id,
            first_name=first_name,
            last_name=last_name,
            full_name=player_name,
            height_inches=height_inches,
            weight_lbs=weight_lbs,
            position=position,
            school_name=school_name,
            school_state=state,
            school_country="USA",
            grad_year=grad_year,
            level=PlayerLevel.HIGH_SCHOOL,
            data_source=data_source,
        )

        # ========================================
        # STEP 2: Extract Season Statistics
        # ========================================

        # Games played
        gp = parse_int(
            row.get("GP") or
            row.get("Games") or
            row.get("G") or
            row.get("Games Played")
        )

        # Points per game / Total points
        ppg = parse_float(
            row.get("PPG") or
            row.get("Points") or
            row.get("PTS") or
            row.get("Pts/G")
        )

        total_points = parse_int(
            row.get("Total Points") or
            row.get("Total PTS") or
            row.get("Pts")
        )

        # If we have total points and GP, calculate PPG
        if not ppg and total_points and gp and gp > 0:
            ppg = round(total_points / gp, 1)

        # Rebounds per game / Total rebounds
        rpg = parse_float(
            row.get("RPG") or
            row.get("Rebounds") or
            row.get("REB") or
            row.get("Rebs/G")
        )

        total_rebounds = parse_int(
            row.get("Total Rebounds") or
            row.get("Total REB") or
            row.get("Rebs")
        )

        # Assists per game / Total assists
        apg = parse_float(
            row.get("APG") or
            row.get("Assists") or
            row.get("AST") or
            row.get("Asts/G")
        )

        total_assists = parse_int(
            row.get("Total Assists") or
            row.get("Total AST") or
            row.get("Asts")
        )

        # Steals per game / Total steals
        spg = parse_float(
            row.get("SPG") or
            row.get("Steals") or
            row.get("STL") or
            row.get("Stls/G")
        )

        total_steals = parse_int(
            row.get("Total Steals") or
            row.get("Total STL")
        )

        # Blocks per game / Total blocks
        bpg = parse_float(
            row.get("BPG") or
            row.get("Blocks") or
            row.get("BLK") or
            row.get("Blks/G")
        )

        total_blocks = parse_int(
            row.get("Total Blocks") or
            row.get("Total BLK")
        )

        # Minutes per game
        mpg = parse_float(
            row.get("MPG") or
            row.get("Minutes") or
            row.get("MIN") or
            row.get("Mins/G")
        )

        # Shooting percentages
        fg_pct = parse_float(
            row.get("FG%") or
            row.get("FG Pct") or
            row.get("Field Goal %")
        )

        three_pt_pct = parse_float(
            row.get("3P%") or
            row.get("3PT%") or
            row.get("3-PT%") or
            row.get("Three Point %")
        )

        ft_pct = parse_float(
            row.get("FT%") or
            row.get("FT Pct") or
            row.get("Free Throw %")
        )

        # Turnovers per game
        tpg = parse_float(
            row.get("TPG") or
            row.get("Turnovers") or
            row.get("TO") or
            row.get("TOs/G")
        )

        # Calculate season totals if we have per-game and GP
        if gp and gp > 0:
            if ppg and not total_points:
                total_points = int(ppg * gp)
            if rpg and not total_rebounds:
                total_rebounds = int(rpg * gp)
            if apg and not total_assists:
                total_assists = int(apg * gp)
            if spg and not total_steals:
                total_steals = int(spg * gp)
            if bpg and not total_blocks:
                total_blocks = int(bpg * gp)

        # Only create PlayerSeasonStats if we have at least some stats
        has_stats = any([
            ppg, rpg, apg, spg, bpg, mpg,
            fg_pct, three_pt_pct, ft_pct,
            total_points, total_rebounds, total_assists
        ])

        if has_stats:
            # Determine season
            if not season:
                from datetime import datetime
                current_year = datetime.now().year
                # Assume current season (e.g., 2024-25)
                season = f"{current_year}-{str(current_year + 1)[-2:]}"

            # Create PlayerSeasonStats object
            season_stats = PlayerSeasonStats(
                player_id=player_id,
                player_name=player_name,
                season=season,
                team_id=player_id,  # Use player_id as placeholder
                team_name=school_name or "Unknown",

                # Games
                games_played=gp or 0,
                games_started=None,  # Not typically provided

                # Minutes
                minutes_played=mpg,  # Per game average

                # Scoring (totals)
                points=total_points,

                # Shooting percentages (percentages, not decimals)
                field_goal_percentage=fg_pct,
                three_point_percentage=three_pt_pct,
                free_throw_percentage=ft_pct,

                # Rebounds (totals)
                total_rebounds=total_rebounds,
                offensive_rebounds=None,  # Not typically provided
                defensive_rebounds=None,

                # Assists & Turnovers (totals)
                assists=total_assists,
                turnovers=int(tpg * gp) if tpg and gp else None,

                # Defense (totals)
                steals=total_steals,
                blocks=total_blocks,

                # Per-game averages (stored in notes or calculated)
                data_source=data_source,
            )

            return player, season_stats
        else:
            # No stats found, return just player
            return player, None

    except Exception as e:
        self.logger.warning(
            "Failed to parse player and stats from MaxPreps row",
            error=str(e),
            row_keys=list(row.keys()) if row else None
        )
        return None, None


async def search_players_with_stats(
    self,
    state: str,
    name: Optional[str] = None,
    team: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = 50,
) -> list[Tuple[Player, Optional[PlayerSeasonStats]]]:
    """
    Search for players AND their season statistics from MaxPreps.

    **ENHANCED VERSION** - Returns both Player and PlayerSeasonStats objects.

    This method fetches stat leader pages which typically include:
    - Player demographic info (name, school, class, position)
    - Season statistics (PPG, RPG, APG, etc.)

    Args:
        state: US state code (required)
        name: Player name filter (partial match)
        team: Team/school name filter (partial match)
        season: Season filter (e.g., "2024-25")
        limit: Maximum number of results

    Returns:
        List of (Player, PlayerSeasonStats) tuples

    Example:
        >>> results = await maxpreps.search_players_with_stats(state="CA", limit=10)
        >>> for player, stats in results:
        ...     print(f"{player.full_name}: {stats.points_per_game if stats else 'N/A'} PPG")
    """
    try:
        # Validate state
        state = self._validate_state(state)

        self.logger.info(
            "Searching MaxPreps players with stats",
            state=state,
            name_filter=name,
            team_filter=team,
            limit=limit
        )

        # Build stats URL
        stats_url = self._get_state_url(state, "stat-leaders")

        # Fetch rendered HTML
        self.logger.debug(f"Fetching MaxPreps stats page", url=stats_url)

        html = await self.browser_client.get_rendered_html(
            url=stats_url,
            wait_for="table",
            wait_timeout=30000,
            wait_for_network_idle=True,
        )

        # Parse HTML
        from src.utils import parse_html, extract_table_data
        soup = parse_html(html)

        # Find stats table
        from src.utils.scraping_helpers import find_stat_table
        stats_table = find_stat_table(soup)

        if not stats_table:
            self.logger.warning(
                "No stats table found on MaxPreps page",
                state=state,
                url=stats_url
            )
            return []

        # Extract table data
        rows = extract_table_data(stats_table)

        if not rows:
            self.logger.warning("Stats table found but no rows extracted", state=state)
            return []

        self.logger.info(
            f"Extracted {len(rows)} rows from MaxPreps stats table",
            state=state
        )

        # Parse players and stats
        results = []
        data_source = self.create_data_source_metadata(
            url=stats_url,
            quality_flag="complete",
            notes=f"MaxPreps {self.STATE_NAMES.get(state, state)} stats"
        )

        for row in rows[:limit * 2]:  # Parse 2x limit to allow for filtering
            player, stats = self._parse_player_and_stats_from_row(
                row, state, data_source, season
            )

            if player:
                # Apply filters
                if name and name.lower() not in player.full_name.lower():
                    continue

                if team and player.school_name and team.lower() not in player.school_name.lower():
                    continue

                results.append((player, stats))

                # Stop once we hit limit
                if len(results) >= limit:
                    break

        self.logger.info(
            f"Found {len(results)} players with stats after filtering",
            state=state,
            with_stats=sum(1 for _, s in results if s is not None)
        )

        return results

    except ValueError as e:
        # State validation error - re-raise
        raise

    except Exception as e:
        self.logger.error(
            "Failed to search MaxPreps players with stats",
            state=state,
            error=str(e),
            error_type=type(e).__name__
        )
        return []


# ========================================
# INTEGRATION NOTES
# ========================================

"""
To integrate these enhanced methods into maxpreps.py:

1. REPLACE the existing `_parse_player_from_stats_row` method with `_parse_player_and_stats_from_row`

2. ADD the new `search_players_with_stats` method

3. UPDATE the existing `search_players` method to use the new parser:

   Change line ~475 in search_players():
   FROM:
       player = self._parse_player_from_stats_row(row, state, data_source)
   TO:
       player, _ = self._parse_player_and_stats_from_row(row, state, data_source)

4. BENEFITS:
   - Extracts ALL available statistics from MaxPreps
   - Returns both Player and PlayerSeasonStats objects
   - Handles missing data gracefully
   - No breaking changes to existing search_players() method
   - New search_players_with_stats() method for advanced use cases

5. TESTING:
   - Run validation script: python scripts/validate_maxpreps.py --state CA
   - Check what metrics are actually available
   - Adjust parser based on actual HTML structure
"""
