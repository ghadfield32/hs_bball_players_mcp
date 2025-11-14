"""
Wisconsin WIAA DataSource Integration Tests

Tests Wisconsin WIAA datasource with real tournament bracket data.
"""

import pytest

from src.models import Game, Team


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestWisconsinWiaaDataSource:
    """Test suite for Wisconsin WIAA datasource with real bracket data."""

    @pytest.mark.asyncio
    async def test_health_check(self, wisconsin_wiaa_source):
        """Test Wisconsin WIAA health check."""
        is_healthy = await wisconsin_wiaa_source.health_check()
        assert is_healthy is True, "Wisconsin WIAA datasource should be healthy"

    @pytest.mark.asyncio
    async def test_get_tournament_brackets_boys_2024(self, wisconsin_wiaa_source):
        """Test fetching Boys 2024 tournament brackets."""
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

    @pytest.mark.asyncio
    async def test_get_tournament_brackets_girls_2024(self, wisconsin_wiaa_source):
        """Test fetching Girls 2024 tournament brackets."""
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

    @pytest.mark.asyncio
    async def test_no_self_games(self, wisconsin_wiaa_source):
        """Test that there are no self-games (team playing itself)."""
        games = await wisconsin_wiaa_source.get_tournament_brackets(
            year=2024,
            gender="Boys"
        )

        self_games = [
            g for g in games
            if g.home_team_name.lower() == g.away_team_name.lower()
        ]

        assert len(self_games) == 0, f"Found {len(self_games)} self-games (team vs itself)"

    @pytest.mark.asyncio
    async def test_no_duplicate_games(self, wisconsin_wiaa_source):
        """Test that there are no duplicate games."""
        games = await wisconsin_wiaa_source.get_tournament_brackets(
            year=2024,
            gender="Boys"
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
    async def test_valid_scores(self, wisconsin_wiaa_source):
        """Test that all scores are within valid range."""
        games = await wisconsin_wiaa_source.get_tournament_brackets(
            year=2024,
            gender="Boys"
        )

        invalid_scores = [
            g for g in games
            if (g.home_score is not None and (g.home_score < 0 or g.home_score > 200)) or
               (g.away_score is not None and (g.away_score < 0 or g.away_score > 200))
        ]

        assert len(invalid_scores) == 0, f"Found {len(invalid_scores)} games with invalid scores"

    @pytest.mark.asyncio
    async def test_round_parsing(self, wisconsin_wiaa_source):
        """Test that rounds are properly parsed."""
        games = await wisconsin_wiaa_source.get_tournament_brackets(
            year=2024,
            gender="Boys"
        )

        # Count rounds
        from collections import Counter
        round_counts = Counter(g.round for g in games)

        # Unknown round should be less than 20%
        unknown_count = round_counts.get("Unknown Round", 0)
        unknown_pct = (unknown_count / len(games) * 100) if games else 0

        assert unknown_pct < 20, f"Too many unknown rounds: {unknown_pct:.1f}% (should be < 20%)"

        # Should have recognizable tournament rounds
        expected_rounds = {"Regional", "Sectional", "State", "Regional Finals", "Sectional Finals"}
        found_rounds = set(round_counts.keys())
        overlap = expected_rounds & found_rounds

        assert len(overlap) > 0, f"No recognizable tournament rounds found. Found: {found_rounds}"

    @pytest.mark.asyncio
    async def test_wisconsin_location_data(self, wisconsin_wiaa_source):
        """Test that games have Wisconsin location context."""
        games = await wisconsin_wiaa_source.get_tournament_brackets(
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
    async def test_division_filtering(self, wisconsin_wiaa_source):
        """Test filtering by division."""
        div1_games = await wisconsin_wiaa_source.get_tournament_brackets(
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
    async def test_get_games_method(self, wisconsin_wiaa_source):
        """Test the standard get_games method."""
        games = await wisconsin_wiaa_source.get_games(
            season="2023-24",
            limit=50
        )

        assert isinstance(games, list)
        assert len(games) <= 50

        for game in games:
            assert isinstance(game, Game)

    @pytest.mark.asyncio
    async def test_historical_data_2023(self, wisconsin_wiaa_source):
        """Test accessing historical data from 2023."""
        games = await wisconsin_wiaa_source.get_tournament_brackets(
            year=2023,
            gender="Boys"
        )

        # Historical data may be less complete, but should be accessible
        assert isinstance(games, list)

    @pytest.mark.asyncio
    async def test_multiple_divisions(self, wisconsin_wiaa_source):
        """Test that we can fetch multiple divisions."""
        all_games = await wisconsin_wiaa_source.get_tournament_brackets(
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

    @pytest.mark.asyncio
    async def test_team_extraction(self, wisconsin_wiaa_source):
        """Test extracting unique teams from games."""
        games = await wisconsin_wiaa_source.get_tournament_brackets(
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

        assert len(teams) >= 30, f"Expected at least 30 teams in Div1, found {len(teams)}"

    @pytest.mark.asyncio
    async def test_error_handling_invalid_year(self, wisconsin_wiaa_source):
        """Test error handling with invalid year."""
        games = await wisconsin_wiaa_source.get_tournament_brackets(
            year=1999,  # Too far back
            gender="Boys"
        )

        # Should return empty list, not crash
        assert isinstance(games, list)

    @pytest.mark.asyncio
    async def test_data_completeness(self, wisconsin_wiaa_source):
        """Test that Wisconsin WIAA data is reasonably complete."""
        games = await wisconsin_wiaa_source.get_tournament_brackets(
            year=2024,
            gender="Boys"
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

    @pytest.mark.asyncio
    async def test_parser_statistics(self, wisconsin_wiaa_source):
        """Test that parser statistics are reasonable."""
        games = await wisconsin_wiaa_source.get_tournament_brackets(
            year=2024,
            gender="Boys"
        )

        # Should have a reasonable number of tournament games
        # Wisconsin has 5 divisions, each with multiple sectionals
        # Each sectional has regionals, sectional rounds, and state tournament
        # Expected: ~200-250 total games
        assert 150 <= len(games) <= 400, f"Unexpected game count: {len(games)}"

    @pytest.mark.asyncio
    async def test_season_data_method(self, wisconsin_wiaa_source):
        """Test the get_season_data method."""
        season_data = await wisconsin_wiaa_source.get_season_data("2023-24")

        assert isinstance(season_data, dict)
        assert "games" in season_data
        assert "teams" in season_data

        games = season_data["games"]
        teams = season_data["teams"]

        assert isinstance(games, list)
        assert isinstance(teams, list)

        if teams:
            for team in teams[:5]:
                assert isinstance(team, Team)
                assert team.team_id.startswith("wiaa_wi_")
                assert team.state == "WI"
                assert team.country == "USA"
