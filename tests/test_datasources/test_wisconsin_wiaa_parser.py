"""
Wisconsin WIAA Parser Tests with Fixture Mode

Tests Wisconsin WIAA parser using local fixture files (FIXTURE mode).
This allows parser testing without network calls and avoids HTTP 403s.

Design:
- Uses DataMode.FIXTURE to load HTML from tests/fixtures/wiaa/
- Validates parser correctly extracts games from known fixture data
- Verifies no HTTP calls are made (http_stats remain at zero)
- Fast, reliable, CI-friendly (no network dependencies)
"""

import pytest
from pathlib import Path

from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource, DataMode
from src.models import Game


@pytest.fixture
def fixtures_dir():
    """Path to WIAA fixture files."""
    return Path(__file__).parent.parent / "fixtures" / "wiaa"


@pytest.fixture
async def wiaa_fixture_mode(fixtures_dir):
    """Create Wisconsin WIAA datasource in FIXTURE mode."""
    source = WisconsinWiaaDataSource(
        data_mode=DataMode.FIXTURE,
        fixtures_dir=fixtures_dir
    )
    yield source
    await source.close()


class TestWisconsinWiaaParser:
    """Test suite for Wisconsin WIAA parser using fixture data."""

    @pytest.mark.asyncio
    async def test_fixture_mode_boys_div1(self, wiaa_fixture_mode):
        """Test parsing Boys Division 1 fixture."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        # Should have parsed games from fixture
        assert isinstance(games, list)
        assert len(games) > 0, "Should have parsed games from Boys Div1 fixture"

        # Verify no HTTP calls were made (FIXTURE mode)
        assert wiaa_fixture_mode.http_stats["brackets_requested"] == 0, \
            "FIXTURE mode should not make HTTP requests"
        assert wiaa_fixture_mode.http_stats["brackets_successful"] == 0

        # Validate game structure
        for game in games:
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
    async def test_fixture_mode_girls_div1(self, wiaa_fixture_mode):
        """Test parsing Girls Division 1 fixture."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Girls",
            division="Div1"
        )

        # Should have parsed games from fixture
        assert isinstance(games, list)
        assert len(games) > 0, "Should have parsed games from Girls Div1 fixture"

        # Verify no HTTP calls were made (FIXTURE mode)
        assert wiaa_fixture_mode.http_stats["brackets_requested"] == 0, \
            "FIXTURE mode should not make HTTP requests"

        # Validate game structure
        for game in games:
            assert isinstance(game, Game)
            assert game.game_id.startswith("wiaa_wi_")
            assert game.home_team_name
            assert game.away_team_name

    @pytest.mark.asyncio
    async def test_parser_extracts_correct_teams_boys(self, wiaa_fixture_mode):
        """Test that parser extracts correct team names from Boys fixture."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        # Extract all team names
        teams = set()
        for game in games:
            if game.home_team_name:
                teams.add(game.home_team_name)
            if game.away_team_name:
                teams.add(game.away_team_name)

        # Verify known teams from fixture are present
        expected_teams = {
            "Arrowhead", "Mukwonago", "Hamilton", "Marquette",
            "Franklin", "Neenah", "Milwaukee Riverside"
        }

        for team in expected_teams:
            assert any(team in t for t in teams), \
                f"Expected team '{team}' not found in parsed games"

    @pytest.mark.asyncio
    async def test_parser_extracts_correct_teams_girls(self, wiaa_fixture_mode):
        """Test that parser extracts correct team names from Girls fixture."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Girls",
            division="Div1"
        )

        # Extract all team names
        teams = set()
        for game in games:
            if game.home_team_name:
                teams.add(game.home_team_name)
            if game.away_team_name:
                teams.add(game.away_team_name)

        # Verify known teams from fixture are present
        expected_teams = {
            "Homestead", "Muskego", "Appleton North",
            "Madison West", "Divine Savior Holy Angels"
        }

        for team in expected_teams:
            assert any(team in t for t in teams), \
                f"Expected team '{team}' not found in parsed games"

    @pytest.mark.asyncio
    async def test_parser_extracts_correct_scores(self, wiaa_fixture_mode):
        """Test that parser extracts correct scores from fixture."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        # Find specific known games from fixture
        # Boys Sectional #1 Finals: Arrowhead 70-68 (OT) Marquette
        arrowhead_marquette = [
            g for g in games
            if ("Arrowhead" in g.home_team_name and "Marquette" in g.away_team_name) or
               ("Marquette" in g.home_team_name and "Arrowhead" in g.away_team_name)
        ]

        assert len(arrowhead_marquette) > 0, "Should find Arrowhead vs Marquette game"

        # Verify scores (one team scored 70, other scored 68)
        game = arrowhead_marquette[0]
        scores = sorted([game.home_score, game.away_score])
        assert scores == [68, 70], f"Expected [68, 70], got {scores}"

    @pytest.mark.asyncio
    async def test_parser_no_self_games(self, wiaa_fixture_mode):
        """Test that parser doesn't create self-games (team vs itself)."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        self_games = [
            g for g in games
            if g.home_team_name.lower() == g.away_team_name.lower()
        ]

        assert len(self_games) == 0, \
            f"Found {len(self_games)} self-games (team vs itself)"

    @pytest.mark.asyncio
    async def test_parser_no_duplicate_games(self, wiaa_fixture_mode):
        """Test that parser doesn't create duplicate games."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
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
    async def test_parser_valid_scores(self, wiaa_fixture_mode):
        """Test that all parsed scores are within valid range."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        invalid_scores = [
            g for g in games
            if (g.home_score is not None and (g.home_score < 0 or g.home_score > 200)) or
               (g.away_score is not None and (g.away_score < 0 or g.away_score > 200))
        ]

        assert len(invalid_scores) == 0, \
            f"Found {len(invalid_scores)} games with invalid scores"

    @pytest.mark.asyncio
    async def test_parser_round_extraction(self, wiaa_fixture_mode):
        """Test that parser correctly extracts round information."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        # Extract rounds
        from collections import Counter
        round_counts = Counter(g.round for g in games)

        # Should have recognizable tournament rounds
        expected_rounds = {"Regional Semifinals", "Regional Finals", "Sectional Semifinals",
                           "Sectional Finals", "State Semifinals", "State Championship"}
        found_rounds = set(round_counts.keys())

        # Check for overlap
        overlap = expected_rounds & found_rounds
        assert len(overlap) > 0, \
            f"No recognizable tournament rounds found. Found: {found_rounds}"

    @pytest.mark.asyncio
    async def test_fixture_missing_file(self, wiaa_fixture_mode):
        """Test behavior when fixture file doesn't exist."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div5"  # Div5 fixture doesn't exist
        )

        # Should return empty list, not crash
        assert isinstance(games, list)
        assert len(games) == 0, "Non-existent fixture should return empty list"

        # Still no HTTP calls
        assert wiaa_fixture_mode.http_stats["brackets_requested"] == 0

    @pytest.mark.asyncio
    async def test_parser_state_championship_game(self, wiaa_fixture_mode):
        """Test that parser correctly identifies state championship game."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        # Find state championship game (Arrowhead 76-71 Neenah)
        championship_games = [
            g for g in games
            if "State Championship" in g.round or "Championship" in g.round
        ]

        # Should have at least one championship game
        assert len(championship_games) > 0, \
            "Should find state championship game in fixture"

        # Verify championship game has valid data
        for game in championship_games:
            assert game.home_team_name
            assert game.away_team_name
            assert game.home_score is not None
            assert game.away_score is not None

    @pytest.mark.asyncio
    async def test_parser_overtime_notation(self, wiaa_fixture_mode):
        """Test that parser handles overtime notation correctly."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        # Boys fixture has "70-68 (OT)" in Sectional Finals
        # Girls fixture has "70-65 (OT)" in Sectional Finals
        # Parser should extract scores correctly, ignoring (OT) notation

        # All scores should be integers, not strings with "(OT)"
        for game in games:
            assert isinstance(game.home_score, int), \
                f"home_score should be int, got {type(game.home_score)}"
            assert isinstance(game.away_score, int), \
                f"away_score should be int, got {type(game.away_score)}"

    @pytest.mark.asyncio
    async def test_parser_data_completeness(self, wiaa_fixture_mode):
        """Test that parser extracts complete data from fixtures."""
        games = await wiaa_fixture_mode.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        assert len(games) > 0

        # Check data completeness for all games
        for game in games:
            assert game.game_id, "game_id should be set"
            assert game.home_team_name, "home_team_name should be set"
            assert game.away_team_name, "away_team_name should be set"
            assert game.home_score is not None, "home_score should be set"
            assert game.away_score is not None, "away_score should be set"
            assert game.data_source, "data_source should be set"
            assert game.data_source.source_url, "source_url should be set"
            assert game.home_team_id, "home_team_id should be set"
            assert game.away_team_id, "away_team_id should be set"

    @pytest.mark.asyncio
    async def test_fixture_mode_vs_live_mode_interface(self, fixtures_dir):
        """Test that FIXTURE mode has same interface as LIVE mode."""
        # Create instances in both modes
        fixture_mode = WisconsinWiaaDataSource(
            data_mode=DataMode.FIXTURE,
            fixtures_dir=fixtures_dir
        )
        live_mode = WisconsinWiaaDataSource(
            data_mode=DataMode.LIVE
        )

        # Both should have same methods
        assert hasattr(fixture_mode, "get_tournament_brackets")
        assert hasattr(live_mode, "get_tournament_brackets")
        assert hasattr(fixture_mode, "health_check")
        assert hasattr(live_mode, "health_check")

        # Both should have http_stats
        assert hasattr(fixture_mode, "http_stats")
        assert hasattr(live_mode, "http_stats")

        # Clean up
        await fixture_mode.close()
        await live_mode.close()

    @pytest.mark.asyncio
    async def test_backwards_compatibility_default_mode(self):
        """Test that default instantiation still works (LIVE mode)."""
        # Default should be LIVE mode
        source = WisconsinWiaaDataSource()

        assert source.data_mode == DataMode.LIVE
        assert source.fixtures_dir == Path("tests/fixtures/wiaa")

        await source.close()
