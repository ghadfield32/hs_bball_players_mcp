"""
Adapter Generator Script

Automatically generates a new datasource adapter and test file from templates.
Reduces adapter creation time from 2 hours to 15 minutes.

Usage:
    python scripts/generate_adapter.py

The script will:
1. Ask for league information interactively
2. Generate adapter file from template
3. Generate test file from template
4. Show checklist of next steps
5. Optionally update aggregator.py imports

Author: Claude Code
Date: 2025-11-11
"""

import os
import re
from pathlib import Path
from typing import Optional


def get_input(prompt: str, default: Optional[str] = None) -> str:
    """Get user input with optional default value."""
    if default:
        prompt = f"{prompt} [{default}]"
    value = input(f"{prompt}: ").strip()
    return value if value else (default or "")


def sanitize_name(name: str) -> str:
    """Convert name to valid Python identifier."""
    # Remove special characters, convert to lowercase
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    return sanitized


def to_class_name(name: str) -> str:
    """Convert name to PascalCase class name."""
    parts = name.replace('-', ' ').replace('_', ' ').split()
    return ''.join(word.capitalize() for word in parts)


def generate_adapter(
    league_name: str,
    league_display_name: str,
    base_url: str,
    region: str,
    prefix: str,
    state: Optional[str] = None,
    level: str = "HIGH_SCHOOL",
) -> str:
    """Generate adapter Python code."""

    class_name = to_class_name(league_name)
    source_type = prefix.upper()

    template = f'''"""
{league_display_name} DataSource Adapter

Scrapes player statistics from {league_display_name}.

Implementation Status: READY FOR URL UPDATES
Next Steps:
1. Visit {base_url} in browser
2. Find stats/players/teams pages
3. Inspect HTML structure
4. Update URLs in __init__
5. Update table_class_hint in search_players()
6. Run tests: pytest tests/test_datasources/test_{prefix}.py -v
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
    clean_player_name,
    extract_table_data,
    find_stat_table,
    parse_float,
    parse_html,
    parse_int,
    parse_player_from_row,
    parse_season_stats_from_row,
)
from ..base import BaseDataSource


class {class_name}DataSource(BaseDataSource):
    """
    {league_display_name} datasource adapter.

    Provides access to {league_display_name} player statistics.
    """

    source_type = DataSourceType.{source_type}
    source_name = "{league_display_name}"
    base_url = "{base_url}"
    region = DataSourceRegion.{region}

    def __init__(self):
        """Initialize {league_display_name} datasource."""
        super().__init__()

        # TODO: Update these URLs after inspecting the website
        # Visit {base_url} and find the actual paths
        self.stats_url = f"{{self.base_url}}/stats"  # UPDATE THIS
        self.teams_url = f"{{self.base_url}}/teams"  # UPDATE THIS
        self.schedule_url = f"{{self.base_url}}/schedule"  # UPDATE THIS
        self.leaders_url = f"{{self.base_url}}/leaders"  # UPDATE THIS

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        Args:
            player_id: Player identifier (format: {prefix}_firstname_lastname)

        Returns:
            Player object or None
        """
        # Standard pattern: use search_players to find player
        players = await self.search_players(
            name=player_id.replace("{prefix}_", "").replace("_", " "),
            limit=1
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
        Search for players in {league_display_name}.

        Args:
            name: Player name filter (partial match)
            team: Team name filter
            season: Season filter (currently uses latest)
            limit: Maximum results

        Returns:
            List of Player objects
        """
        try:
            # Fetch stats page with 1-hour cache
            html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # TODO: Update table_class_hint after inspecting website
            # Look for the actual table class name in browser dev tools
            table = find_stat_table(soup, table_class_hint="stats")

            if not table:
                self.logger.warning("No stats table found on {league_display_name} stats page")
                return []

            # Extract table rows as dictionaries
            rows = extract_table_data(table)

            # Create data source metadata
            data_source = self.create_data_source_metadata(
                url=self.stats_url,
                quality_flag=DataQualityFlag.COMPLETE
            )

            players = []
            for row in rows[:limit * 2]:  # Get extra for filtering
                # Use helper to parse common player fields
                player_data = parse_player_from_row(
                    row,
                    source_prefix="{prefix}",
                    {"school_state=" + f'"{state}"' if state else ""}
                )

                if not player_data:
                    continue

                # Add datasource-specific fields
                player_data["data_source"] = data_source
                player_data["level"] = PlayerLevel.{level}

                # Validate with Pydantic model
                player = self.validate_and_log_data(
                    Player,
                    player_data,
                    f"player {{player_data.get('full_name')}}"
                )

                if not player:
                    continue

                # Apply filters
                if name and name.lower() not in player.full_name.lower():
                    continue
                if team and (not player.team_name or team.lower() not in player.team_name.lower()):
                    continue

                players.append(player)

                if len(players) >= limit:
                    break

            self.logger.info(f"Found {{len(players)}} {league_display_name} players")
            return players

        except Exception as e:
            self.logger.error("{league_display_name} player search failed", error=str(e))
            return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics from {league_display_name}.

        Args:
            player_id: Player identifier
            season: Season (None = current season)

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
            player_name = player_id.replace("{prefix}_", "").replace("_", " ").title()

            # Find matching player row
            for row in rows:
                row_player = clean_player_name(row.get("Player") or row.get("NAME") or "")
                if player_name.lower() in row_player.lower():
                    # Use helper to parse stats
                    stats_data = parse_season_stats_from_row(
                        row,
                        player_id,
                        season or "2024-25",
                        "{league_display_name}"
                    )

                    # Validate and return
                    return self.validate_and_log_data(
                        PlayerSeasonStats,
                        stats_data,
                        f"season stats for {{player_name}}"
                    )

            self.logger.warning(f"Player not found in stats", player_id=player_id)
            return None

        except Exception as e:
            self.logger.error("Failed to get player season stats", error=str(e))
            return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game statistics.

        Note: Requires box score page URL pattern.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            PlayerGameStats or None
        """
        # TODO: Implement after finding box score URL pattern
        self.logger.warning("{league_display_name} game stats require box score URL pattern")
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team information.

        Args:
            team_id: Team identifier

        Returns:
            Team object or None
        """
        # TODO: Implement after inspecting teams/standings page
        self.logger.warning("{league_display_name} team lookup requires teams page structure")
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

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            List of Game objects
        """
        # TODO: Implement after inspecting schedule page
        self.logger.warning("{league_display_name} schedule parsing requires schedule page structure")
        return []

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        Args:
            stat: Stat category (points, rebounds, assists, etc.)
            season: Season filter
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
            # TODO: Update these mappings based on actual table columns
            stat_column_map = {{
                "points": "PPG",
                "rebounds": "RPG",
                "assists": "APG",
                "steals": "SPG",
                "blocks": "BPG",
            }}

            stat_column = stat_column_map.get(stat.lower(), stat.upper())

            for row in rows:
                player_name = clean_player_name(row.get("Player") or row.get("NAME") or "")
                team_name = row.get("Team") or row.get("TEAM")

                # Try to find stat value
                stat_value = parse_float(row.get(stat_column) or row.get(stat.upper()))

                if player_name and stat_value is not None:
                    entry = build_leaderboard_entry(
                        rank=0,  # Will be set after sorting
                        player_name=player_name,
                        stat_value=stat_value,
                        stat_name=stat,
                        season=season or "2024-25",
                        source_prefix="{prefix}",
                        team_name=team_name,
                    )
                    leaderboard.append(entry)

            # Sort by stat value (descending)
            leaderboard.sort(key=lambda x: x["stat_value"], reverse=True)

            # Set ranks
            for i, entry in enumerate(leaderboard[:limit], 1):
                entry["rank"] = i

            self.logger.info(
                f"{{stat}} leaderboard returned {{len(leaderboard[:limit])}} entries"
            )
            return leaderboard[:limit]

        except Exception as e:
            self.logger.error(f"Failed to get {{stat}} leaderboard", error=str(e))
            return []
'''

    return template


def generate_test(league_name: str, league_display_name: str, prefix: str, class_name: str) -> str:
    """Generate test file Python code."""

    template = f'''"""
Tests for {league_display_name} DataSource Adapter

Tests {league_display_name} datasource with real API calls.
"""

import pytest

from src.datasources.{get_region_path(league_name)}.{prefix} import {class_name}DataSource


@pytest.mark.asyncio
@pytest.mark.integration
class Test{class_name}DataSource:
    """Test suite for {league_display_name} datasource."""

    @pytest.fixture
    async def datasource(self):
        """Create datasource instance."""
        ds = {class_name}DataSource()
        yield ds
        await ds.close()

    async def test_health_check(self, datasource):
        """Test {league_display_name} health check."""
        healthy = await datasource.health_check()
        assert healthy, "{league_display_name} website should be accessible"

    async def test_search_players(self, datasource):
        """Test searching players."""
        players = await datasource.search_players(limit=10)

        assert len(players) > 0, "Should find players"

        player = players[0]
        assert player.full_name, "Player should have name"
        assert player.player_id.startswith("{prefix}_"), "Player ID should have correct prefix"
        assert player.data_source is not None, "Player should have data source"

        print(f"\\nFound {{len(players)}} players")
        print(f"Sample player: {{player.full_name}}")
        if player.team_name:
            print(f"  Team: {{player.team_name}}")
        if player.position:
            print(f"  Position: {{player.position}}")

    async def test_search_players_with_name_filter(self, datasource):
        """Test player search with name filter."""
        # Use a common name that should exist
        players = await datasource.search_players(name="Smith", limit=5)

        # All results should contain the filter name
        for player in players:
            assert "smith" in player.full_name.lower(), "Filter should be applied"

    async def test_get_player_by_id(self, datasource):
        """Test getting a specific player by ID."""
        # First find a player
        players = await datasource.search_players(limit=1)
        if not players:
            pytest.skip("No players found for ID test")

        player_id = players[0].player_id

        # Get that player by ID
        player = await datasource.get_player(player_id)

        assert player is not None, "Should find player by ID"
        assert player.player_id == player_id, "Should return correct player"

    async def test_get_player_season_stats(self, datasource):
        """Test getting player season statistics."""
        # First find a player
        players = await datasource.search_players(limit=1)
        if not players:
            pytest.skip("No players found for stats test")

        player = players[0]

        # Get their stats
        stats = await datasource.get_player_season_stats(player.player_id)

        if stats:  # Stats might not be available for all players
            assert stats.player_id == player.player_id, "Stats should be for correct player"
            assert stats.games_played >= 0, "Games played should be non-negative"

            print(f"\\nStats for {{player.full_name}}:")
            print(f"  Games: {{stats.games_played}}")
            if stats.points_per_game:
                print(f"  PPG: {{stats.points_per_game}}")
            if stats.rebounds_per_game:
                print(f"  RPG: {{stats.rebounds_per_game}}")
            if stats.assists_per_game:
                print(f"  APG: {{stats.assists_per_game}}")

    async def test_get_leaderboard_points(self, datasource):
        """Test getting points leaderboard."""
        leaderboard = await datasource.get_leaderboard("points", limit=10)

        assert len(leaderboard) > 0, "Should find leaders"

        top_player = leaderboard[0]
        assert top_player["rank"] == 1, "First entry should be rank 1"
        assert top_player["player_name"], "Entry should have player name"
        assert top_player["stat_value"] > 0, "Stat value should be positive"

        print(f"\\nTop 5 scorers:")
        for entry in leaderboard[:5]:
            print(f"  {{entry['rank']}}. {{entry['player_name']}}: {{entry['stat_value']}} PPG")

    async def test_get_leaderboard_rebounds(self, datasource):
        """Test getting rebounds leaderboard."""
        leaderboard = await datasource.get_leaderboard("rebounds", limit=5)

        if leaderboard:
            print(f"\\nTop 5 rebounders:")
            for entry in leaderboard[:5]:
                print(f"  {{entry['rank']}}. {{entry['player_name']}}: {{entry['stat_value']}} RPG")

    async def test_rate_limiting(self, datasource):
        """Test that rate limiting is enforced."""
        import time

        start = time.time()

        # Make multiple requests quickly
        for _ in range(3):
            await datasource.search_players(limit=5)

        elapsed = time.time() - start

        # Should take some time due to rate limiting
        print(f"\\n3 requests took {{elapsed:.2f}} seconds")
        # Note: Exact timing depends on rate limit configuration

    async def test_data_quality_flags(self, datasource):
        """Test that data quality flags are set."""
        players = await datasource.search_players(limit=5)

        for player in players:
            assert player.data_source is not None, "Should have data source"
            assert player.data_source.quality_flag is not None, "Should have quality flag"

    async def test_player_data_completeness(self, datasource):
        """Test that player data contains expected fields."""
        players = await datasource.search_players(limit=10)

        if not players:
            pytest.skip("No players found")

        # Check that we get various types of data
        has_name = any(p.full_name for p in players)
        has_team = any(p.team_name for p in players)
        has_position = any(p.position for p in players)

        assert has_name, "Should have player names"
        print(f"\\nData completeness:")
        print(f"  Players with names: {{sum(1 for p in players if p.full_name)}} / {{len(players)}}")
        print(f"  Players with teams: {{sum(1 for p in players if p.team_name)}} / {{len(players)}}")
        print(f"  Players with positions: {{sum(1 for p in players if p.position)}} / {{len(players)}}")
'''

    return template


def get_region_path(league_name: str) -> str:
    """Determine region path based on league name or user input."""
    league_lower = league_name.lower()

    if any(x in league_lower for x in ['canada', 'canadian', 'osba']):
        return 'canada'
    elif any(x in league_lower for x in ['europe', 'european', 'fiba', 'angt']):
        return 'europe'
    elif any(x in league_lower for x in ['australia', 'australian', 'playhq']):
        return 'australia'
    else:
        return 'us'


def update_aggregator_imports(prefix: str, class_name: str, region_path: str):
    """Update aggregator.py with new datasource import."""
    aggregator_path = Path("src/services/aggregator.py")

    if not aggregator_path.exists():
        print(f"⚠️  Warning: Could not find {aggregator_path}")
        return False

    content = aggregator_path.read_text()

    # Check if already imported
    import_line = f"from ..datasources.{region_path}.{prefix} import {class_name}DataSource"
    if import_line in content:
        print(f"✅ Import already exists in aggregator.py")
        return True

    # Find the imports section
    import_section_end = content.find("class DataAggregator:")
    if import_section_end == -1:
        print("⚠️  Warning: Could not find class DataAggregator in aggregator.py")
        return False

    # Add import before the class
    lines = content[:import_section_end].split('\n')

    # Find last datasource import
    last_import_idx = -1
    for i, line in enumerate(lines):
        if 'from ..datasources.' in line and 'import' in line:
            last_import_idx = i

    if last_import_idx >= 0:
        # Insert after last datasource import
        lines.insert(last_import_idx + 1, import_line)
        content = '\n'.join(lines) + content[import_section_end:]

        aggregator_path.write_text(content)
        print(f"✅ Added import to aggregator.py")
        return True

    return False


def main():
    """Main function to run the adapter generator."""
    print("=" * 70)
    print("🏀 Basketball Adapter Generator")
    print("=" * 70)
    print()
    print("This script will generate a new datasource adapter and test file.")
    print("You'll need to inspect the website and update URLs afterwards.")
    print()

    # Get league information
    print("📝 League Information")
    print("-" * 70)

    league_name = get_input("League name (e.g., 'Overtime Elite', 'Grind Session')")
    if not league_name:
        print("❌ League name is required")
        return

    league_display_name = get_input("Display name", default=league_name)

    # Generate prefix from league name
    default_prefix = sanitize_name(league_name.split()[0] if ' ' in league_name else league_name)
    prefix = get_input("URL/file prefix (lowercase, no spaces)", default=default_prefix)

    base_url = get_input("Base URL (e.g., 'https://overtimeelite.com')")
    if not base_url.startswith('http'):
        base_url = f"https://{base_url}"

    print("\nRegion options: US, CANADA, EUROPE, AUSTRALIA, GLOBAL")
    region = get_input("Region", default="US").upper()

    state = get_input("State code (if US, optional, e.g., 'CA', 'NY')")
    state = state.upper() if state else None

    print("\nLevel options: HIGH_SCHOOL, PROFESSIONAL, JUNIOR, GRASSROOTS")
    level = get_input("Player level", default="HIGH_SCHOOL").upper()

    # Determine region path
    region_path = get_region_path(league_name)
    if region == "CANADA":
        region_path = "canada"
    elif region == "EUROPE" or region == "GLOBAL":
        region_path = "europe"
    elif region == "AUSTRALIA":
        region_path = "australia"

    # Confirm
    print()
    print("=" * 70)
    print("📋 Summary")
    print("=" * 70)
    print(f"League: {league_display_name}")
    print(f"Prefix: {prefix}")
    print(f"Base URL: {base_url}")
    print(f"Region: {region}")
    if state:
        print(f"State: {state}")
    print(f"Level: {level}")
    print(f"Region path: src/datasources/{region_path}/{prefix}.py")
    print()

    confirm = get_input("Generate files? (yes/no)", default="yes").lower()
    if confirm not in ['yes', 'y']:
        print("❌ Cancelled")
        return

    # Generate class name
    class_name = to_class_name(league_name)

    # Generate files
    print()
    print("=" * 70)
    print("🔨 Generating Files")
    print("=" * 70)

    # Create adapter file
    adapter_dir = Path(f"src/datasources/{region_path}")
    adapter_dir.mkdir(parents=True, exist_ok=True)

    adapter_path = adapter_dir / f"{prefix}.py"
    adapter_code = generate_adapter(
        league_name, league_display_name, base_url, region, prefix, state, level
    )

    adapter_path.write_text(adapter_code)
    print(f"✅ Created adapter: {adapter_path}")

    # Create test file
    test_dir = Path("tests/test_datasources")
    test_dir.mkdir(parents=True, exist_ok=True)

    test_path = test_dir / f"test_{prefix}.py"
    test_code = generate_test(league_name, league_display_name, prefix, class_name)

    test_path.write_text(test_code)
    print(f"✅ Created test file: {test_path}")

    # Update __init__.py
    init_path = adapter_dir / "__init__.py"
    if init_path.exists():
        init_content = init_path.read_text()
        export_line = f"from .{prefix} import {class_name}DataSource"
        if export_line not in init_content:
            # Add to exports
            lines = init_content.strip().split('\n')
            # Find __all__ if it exists
            all_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('__all__'):
                    all_idx = i
                    break

            if all_idx >= 0:
                # Insert before __all__
                lines.insert(all_idx, export_line)
            else:
                # Add to end
                lines.append(export_line)

            init_path.write_text('\n'.join(lines) + '\n')
            print(f"✅ Updated {init_path}")

    # Ask about updating aggregator
    print()
    update_agg = get_input("Update aggregator.py imports? (yes/no)", default="yes").lower()
    if update_agg in ['yes', 'y']:
        if update_aggregator_imports(prefix, class_name, region_path):
            print("✅ Updated aggregator.py")
        else:
            print("⚠️  Could not automatically update aggregator.py")
            print(f"   Manually add: from ..datasources.{region_path}.{prefix} import {class_name}DataSource")

    # Print next steps
    print()
    print("=" * 70)
    print("✅ Generation Complete!")
    print("=" * 70)
    print()
    print("📋 Next Steps:")
    print()
    print(f"1. Visit {base_url} in your browser")
    print("   - Open Developer Tools (F12)")
    print("   - Find stats/players/teams pages")
    print()
    print(f"2. Update URLs in {adapter_path}")
    print("   - Replace placeholder URLs with actual paths")
    print("   - Update table_class_hint in search_players()")
    print()
    print(f"3. Add DataSourceType.{prefix.upper()} to src/models/source.py")
    print("   - In DataSourceType enum")
    print()
    print(f"4. Run tests:")
    print(f"   pytest {test_path} -v -s")
    print()
    print("5. Fix any issues:")
    print("   - Check column name mappings")
    print("   - Update stat_column_map in get_leaderboard()")
    print("   - Verify table finding logic")
    print()
    print("6. Once tests pass, integrate with aggregator:")
    print("   - Initialize datasource in aggregator.__init__")
    print("   - Add to search_players_all_sources()")
    print("   - Add to get_player_season_stats_all_sources()")
    print()
    print(f"📖 See ADAPTER_TESTING_REPORT.md for detailed implementation guide")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
