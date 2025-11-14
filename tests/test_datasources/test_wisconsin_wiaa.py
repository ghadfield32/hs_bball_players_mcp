"""
Wisconsin WIAA DataSource Integration Tests

Tests Wisconsin WIAA datasource with both fixture and live tournament bracket data.

Updated to use fixture mode for 2024 Div1 tests (stable CI)
and live mode for integration tests (manual/optional).
"""

import pytest
from pathlib import Path

from src.models import Game, Team


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestWisconsinWiaaDataSource:
    """Test suite for Wisconsin WIAA datasource."""

    @pytest.mark.skip(reason="LIVE mode test - health check requires real WIAA access (may get 403s)")
    @pytest.mark.asyncio
    async def test_health_check(self, wisconsin_wiaa_source):
        """Test Wisconsin WIAA health check (LIVE mode - INTEGRATION TEST).

        Skipped by default because health check tries to fetch live data from WIAA website.
        """
        is_healthy = await wisconsin_wiaa_source.health_check()
        assert is_healthy is True, "Wisconsin WIAA datasource should be healthy"

    # ========== FIXTURE MODE TESTS (2024 Div1) - Stable for CI ==========

    @pytest.mark.asyncio
    async def test_get_tournament_brackets_boys_2024_div1(self, wisconsin_wiaa_fixture_source):
        """Test fetching Boys 2024 Div1 tournament brackets (FIXTURE mode)."""
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        assert isinstance(games, list)
        assert len(games) > 0, f"Expected games from Boys 2024 Div1 fixture, got {len(games)}"

        # Verify it's using fixtures (no HTTP calls)
        assert wisconsin_wiaa_fixture_source.http_stats["brackets_requested"] == 0, \
            "FIXTURE mode should not make HTTP requests"

        # Check structure
        for game in games[:10]:  # Check first 10
            assert isinstance(game, Game)
            assert game.game_id.startswith("wiaa_wi_")
            assert game.home_team_name
            assert game.away_team_name
            assert game.home_score is not None
            assert game.away_score is not None
            assert game.game_type.value == "tournament"
            assert game.data_source is not None
            assert game.data_source.source_type.value == "wiaa"

        # Verify known teams from fixture
        team_names = {g.home_team_name for g in games} | {g.away_team_name for g in games}
        assert "Arrowhead" in team_names, "Expected Arrowhead from Boys Div1 fixture"

    @pytest.mark.asyncio
    async def test_get_tournament_brackets_girls_2024_div1(self, wisconsin_wiaa_fixture_source):
        """Test fetching Girls 2024 Div1 tournament brackets (FIXTURE mode)."""
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Girls",
            division="Div1"
        )

        assert isinstance(games, list)
        assert len(games) > 0, f"Expected games from Girls 2024 Div1 fixture, got {len(games)}"

        # Verify it's using fixtures (no HTTP calls)
        assert wisconsin_wiaa_fixture_source.http_stats["brackets_requested"] == 0

        # Check structure
        for game in games[:10]:  # Check first 10
            assert isinstance(game, Game)
            assert game.game_id.startswith("wiaa_wi_")
            assert game.home_team_name
            assert game.away_team_name

        # Verify known teams from fixture
        team_names = {g.home_team_name for g in games} | {g.away_team_name for g in games}
        assert "Homestead" in team_names, "Expected Homestead from Girls Div1 fixture"

    @pytest.mark.asyncio
    async def test_no_self_games(self, wisconsin_wiaa_fixture_source):
        """Test that there are no self-games (team playing itself)."""
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        self_games = [
            g for g in games
            if g.home_team_name.lower() == g.away_team_name.lower()
        ]

        assert len(self_games) == 0, f"Found {len(self_games)} self-games (team vs itself)"

    @pytest.mark.asyncio
    async def test_no_duplicate_games(self, wisconsin_wiaa_fixture_source):
        """Test that there are no duplicate games."""
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        # Create signatures for each game
        seen_signatures = set()
        duplicates = []

        for game in games:
            # Normalize team order to catch reverse duplicates
            teams_sorted = tuple(sorted([game.home_team_name, game.away_team_name]))
            scores_sorted = tuple(sorted([game.home_score or 0, game.away_score or 0]))
            signature = (teams_sorted[0], teams_sorted[1], scores_sorted[0], scores_sorted[1])

            if signature in seen_signatures:
                duplicates.append(game)
            else:
                seen_signatures.add(signature)

        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate games"

    @pytest.mark.asyncio
    async def test_valid_scores(self, wisconsin_wiaa_fixture_source):
        """Test that all scores are within valid range."""
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        invalid_scores = [
            g for g in games
            if (g.home_score is not None and (g.home_score < 0 or g.home_score > 200)) or
               (g.away_score is not None and (g.away_score < 0 or g.away_score > 200))
        ]

        assert len(invalid_scores) == 0, f"Found {len(invalid_scores)} games with invalid scores"

    @pytest.mark.asyncio
    async def test_round_parsing(self, wisconsin_wiaa_fixture_source):
        """Test that rounds are properly parsed (UPDATED for full round names)."""
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        # Count rounds
        from collections import Counter
        round_counts = Counter(g.round for g in games)

        # Unknown round should be less than 20%
        unknown_count = round_counts.get("Unknown Round", 0)
        unknown_pct = (unknown_count / len(games) * 100) if games else 0

        assert unknown_pct < 20, f"Too many unknown rounds: {unknown_pct:.1f}% (should be < 20%)"

        # Should have recognizable tournament rounds (UPDATED: full names)
        expected_rounds = {
            "Regional Semifinals", "Regional Finals",
            "Sectional Semifinals", "Sectional Finals",
            "State Semifinals", "State Championship"
        }
        found_rounds = set(round_counts.keys())

        # Check for overlap (at least one expected round should be found)
        overlap = expected_rounds & found_rounds
        assert len(overlap) > 0, f"No recognizable tournament rounds found. Found: {found_rounds}"

        # Alternatively, check that we have each tournament tier represented
        assert any("Regional" in r for r in found_rounds), "Should have Regional rounds"
        assert any("Sectional" in r for r in found_rounds), "Should have Sectional rounds"
        assert any("State" in r for r in found_rounds), "Should have State rounds"

    @pytest.mark.asyncio
    async def test_wisconsin_location_data(self, wisconsin_wiaa_fixture_source):
        """Test that games have Wisconsin location context."""
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        assert len(games) > 0, "Should have Div1 games"

        # Check that team IDs indicate Wisconsin
        for game in games[:5]:
            assert game.home_team_id.startswith("wiaa_wi_")
            assert game.away_team_id.startswith("wiaa_wi_")

    @pytest.mark.asyncio
    async def test_division_filtering(self, wisconsin_wiaa_fixture_source):
        """Test filtering by division."""
        div1_games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        assert len(div1_games) > 0, "Should have Div1 games"

        # All games should be from Div1
        for game in div1_games:
            if hasattr(game, 'division') and game.division:
                assert game.division == "Div1"

    @pytest.mark.asyncio
    async def test_team_extraction(self, wisconsin_wiaa_fixture_source):
        """Test extracting unique teams from games."""
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        teams = set()
        for game in games:
            if game.home_team_name:
                teams.add(game.home_team_name)
            if game.away_team_name:
                teams.add(game.away_team_name)

        # Fixture has fewer teams than full live data
        assert len(teams) >= 5, f"Expected at least 5 teams in Div1 fixture, found {len(teams)}"

    @pytest.mark.asyncio
    async def test_data_completeness(self, wisconsin_wiaa_fixture_source):
        """Test that Wisconsin WIAA data is reasonably complete."""
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        assert len(games) > 0

        for game in games[:10]:
            assert game.game_id
            assert game.home_team_name
            assert game.away_team_name
            assert game.home_score is not None
            assert game.away_score is not None
            assert game.data_source
            assert game.data_source.source_url

    # ========== LIVE MODE TESTS (Optional/Integration) ==========

    @pytest.mark.skip(reason="LIVE mode test - requires real WIAA access (may get 403s)")
    @pytest.mark.asyncio
    async def test_get_tournament_brackets_boys_2024_live(self, wisconsin_wiaa_source):
        """Test fetching Boys 2024 tournament brackets (LIVE mode - INTEGRATION TEST).

        This test is skipped by default because:
        1. WIAA has anti-bot protection (HTTP 403s)
        2. Requires live network access
        3. Not suitable for CI

        To run manually:
        pytest tests/test_datasources/test_wisconsin_wiaa.py::TestWisconsinWiaaDataSource::test_get_tournament_brackets_boys_2024_live -v
        """
        games = await wisconsin_wiaa_source.get_tournament_brackets(
            year=2024,
            gender="Boys"
        )

        assert isinstance(games, list)
        assert len(games) >= 200, f"Expected at least 200 Boys tournament games, got {len(games)}"

        for game in games[:10]:  # Check first 10
            assert isinstance(game, Game)
            assert game.game_id.startswith("wiaa_wi_")
            assert game.home_team_name
            assert game.away_team_name
            assert game.home_score is not None
            assert game.away_score is not None
            assert game.game_type.value == "tournament"
            assert game.data_source is not None
            assert game.data_source.source_type.value == "wiaa"

    @pytest.mark.skip(reason="LIVE mode test - requires real WIAA access (may get 403s)")
    @pytest.mark.asyncio
    async def test_get_tournament_brackets_girls_2024_live(self, wisconsin_wiaa_source):
        """Test fetching Girls 2024 tournament brackets (LIVE mode - INTEGRATION TEST).

        Skipped by default - see test_get_tournament_brackets_boys_2024_live for details.
        """
        games = await wisconsin_wiaa_source.get_tournament_brackets(
            year=2024,
            gender="Girls"
        )

        assert isinstance(games, list)
        assert len(games) >= 200, f"Expected at least 200 Girls tournament games, got {len(games)}"

        for game in games[:10]:  # Check first 10
            assert isinstance(game, Game)
            assert game.game_id.startswith("wiaa_wi_")
            assert game.home_team_name
            assert game.away_team_name

    @pytest.mark.skip(reason="Requires fixtures for multiple divisions - not yet implemented")
    @pytest.mark.asyncio
    async def test_multiple_divisions(self, wisconsin_wiaa_fixture_source):
        """Test that we can fetch multiple divisions.

        NOTE: Currently only Div1 fixture exists.
        TODO: Add fixtures for Div2-Div4 to enable this test.
        """
        all_games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Boys"
        )

        # Extract divisions
        divisions = set()
        for game in all_games:
            if hasattr(game, 'division') and game.division:
                divisions.add(game.division)

        # Should have multiple divisions
        assert len(divisions) >= 2, f"Expected multiple divisions, found: {divisions}"

    # ========== UTILITY TESTS (work with both modes) ==========

    @pytest.mark.asyncio
    async def test_get_games_method(self, wisconsin_wiaa_fixture_source):
        """Test the standard get_games method."""
        games = await wisconsin_wiaa_fixture_source.get_games(
            season="2023-24",
            limit=50
        )

        assert isinstance(games, list)
        assert len(games) <= 50

        for game in games:
            assert isinstance(game, Game)

    @pytest.mark.skip(reason="Requires fixture for 2023 - not yet implemented")
    @pytest.mark.asyncio
    async def test_historical_data_2023(self, wisconsin_wiaa_fixture_source):
        """Test accessing historical data from 2023.

        NOTE: No 2023 fixture exists yet.
        TODO: Add 2023 fixtures to enable this test.
        """
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2023,
            gender="Boys",
            division="Div1"
        )

        # Historical data may be less complete, but should be accessible
        assert isinstance(games, list)
        assert len(games) > 0

    @pytest.mark.asyncio
    async def test_error_handling_invalid_year(self, wisconsin_wiaa_fixture_source):
        """Test error handling with invalid year."""
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=1999,  # Too far back - no fixture
            gender="Boys",
            division="Div1"
        )

        # Should return empty list, not crash
        assert isinstance(games, list)

    @pytest.mark.asyncio
    async def test_parser_statistics(self, wisconsin_wiaa_fixture_source):
        """Test that parser statistics are reasonable for Div1 fixture."""
        games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        # Div1 fixture has ~15 games
        # (Full live data would have 200+ across all divisions)
        assert len(games) >= 10, f"Expected at least 10 games in Div1 fixture, got {len(games)}"
        assert len(games) <= 50, f"Unexpected game count for Div1 fixture: {len(games)}"

    @pytest.mark.asyncio
    async def test_season_data_method(self, wisconsin_wiaa_fixture_source):
        """Test the get_season_data method (FIXTURE mode).

        Tests that get_season_data aggregates from available fixture files
        for the 2023-24 season (tournament year 2024).

        Currently we only have 2024 Boys Div1 and Girls Div1 fixtures,
        so this test validates aggregation from those two fixtures.
        """
        season_data = await wisconsin_wiaa_fixture_source.get_season_data("2023-24")

        # Check structure
        assert isinstance(season_data, dict)
        assert "games" in season_data
        assert "teams" in season_data
        assert "metadata" in season_data

        games = season_data["games"]
        teams = season_data["teams"]
        metadata = season_data["metadata"]

        # Check types
        assert isinstance(games, list)
        assert isinstance(teams, list)
        assert isinstance(metadata, dict)

        # Should have games from available 2024 fixtures (Boys Div1 + Girls Div1)
        assert len(games) > 0, "Expected games from available 2024 fixtures"

        # Should have teams extracted from those games
        assert len(teams) > 0, "Expected teams from available 2024 fixtures"

        # Check metadata
        assert metadata["year"] == 2024
        assert metadata["data_mode"] == "FIXTURE"
        assert "divisions_covered" in metadata

        # Check team structure
        if teams:
            for team in teams[:5]:
                assert isinstance(team, Team)
                assert team.team_id.startswith("wiaa_wi_")
                assert team.state == "WI"
