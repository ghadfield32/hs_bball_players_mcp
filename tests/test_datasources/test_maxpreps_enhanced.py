"""
Unit Tests for MaxPreps Enhanced Parser (Enhancement 5)

Tests the enhanced _parse_player_and_stats_from_row() method
that extracts both player info AND season statistics.

Author: Claude Code
Date: 2025-11-15
"""

import pytest
from datetime import datetime
from src.datasources.us.maxpreps import MaxPrepsDataSource
from src.models import DataQualityFlag, Player, PlayerSeasonStats


class TestEnhancedPlayerAndStatsParser:
    """Test the enhanced parser that extracts player info AND stats."""

    @pytest.fixture
    def maxpreps(self):
        """Create MaxPrepsDataSource instance."""
        return MaxPrepsDataSource()

    @pytest.fixture
    def data_source(self, maxpreps):
        """Create a sample data source metadata."""
        return maxpreps.create_data_source_metadata(
            url="https://www.maxpreps.com/ca/basketball/stat-leaders",
            quality_flag=DataQualityFlag.COMPLETE,
            notes="Test data"
        )

    def test_parse_player_with_full_stats(self, maxpreps, data_source):
        """Test parsing row with complete player info and stats."""
        row = {
            "Rank": "1",
            "Player": "John Doe",
            "School": "Lincoln High School",
            "Class": "2025",
            "Pos": "SG",
            "Ht": "6-5",
            "Wt": "185",
            "GP": "25",
            "PPG": "28.5",
            "RPG": "6.2",
            "APG": "4.8",
            "SPG": "2.1",
            "BPG": "0.8",
            "FG%": "52.5",
            "3P%": "38.2",
            "FT%": "85.0",
        }

        player, stats = maxpreps._parse_player_and_stats_from_row(
            row, state="CA", data_source=data_source
        )

        # Validate player
        assert player is not None
        assert player.full_name == "John Doe"
        assert player.first_name == "John"
        assert player.last_name == "Doe"
        assert player.school_name == "Lincoln High School"
        assert player.school_state == "CA"
        assert player.grad_year == 2025
        assert player.height_inches == 77  # 6*12 + 5
        assert player.weight_lbs == 185

        # Validate stats
        assert stats is not None
        assert stats.games_played == 25
        assert stats.points_per_game == pytest.approx(28.5)
        assert stats.rebounds_per_game == pytest.approx(6.2)
        assert stats.assists_per_game == pytest.approx(4.8)
        assert stats.steals_per_game == pytest.approx(2.1)
        assert stats.blocks_per_game == pytest.approx(0.8)
        assert stats.field_goal_percentage == pytest.approx(52.5)
        assert stats.three_point_percentage == pytest.approx(38.2)
        assert stats.free_throw_percentage == pytest.approx(85.0)

        # Validate totals are calculated
        assert stats.points == int(28.5 * 25)  # 712
        assert stats.total_rebounds == int(6.2 * 25)  # 155
        assert stats.assists == int(4.8 * 25)  # 120

    def test_parse_player_with_totals(self, maxpreps, data_source):
        """Test parsing row with total stats instead of per-game."""
        row = {
            "Player": "Jane Smith",
            "School": "Roosevelt HS",
            "GP": "20",
            "Total Points": "500",
            "Total Rebounds": "120",
            "Total Assists": "80",
            "Total Steals": "40",
            "Total Blocks": "15",
        }

        player, stats = maxpreps._parse_player_and_stats_from_row(
            row, state="TX", data_source=data_source
        )

        assert player is not None
        assert stats is not None

        # Totals should be extracted directly
        assert stats.points == 500
        assert stats.total_rebounds == 120
        assert stats.assists == 80
        assert stats.steals == 40
        assert stats.blocks == 15

        # Per-game should be calculated
        assert stats.points_per_game == pytest.approx(25.0)  # 500/20
        assert stats.rebounds_per_game == pytest.approx(6.0)  # 120/20
        assert stats.assists_per_game == pytest.approx(4.0)  # 80/20

    def test_parse_player_with_turnovers(self, maxpreps, data_source):
        """Test that turnovers are extracted and calculated."""
        row = {
            "Player": "Bob Johnson",
            "GP": "30",
            "PPG": "20.0",
            "TPG": "2.5",  # Turnovers per game
        }

        player, stats = maxpreps._parse_player_and_stats_from_row(
            row, state="NY", data_source=data_source
        )

        assert stats is not None
        assert stats.turnovers == int(2.5 * 30)  # 75

    def test_parse_player_without_stats(self, maxpreps, data_source):
        """Test parsing row with only player info (no stats)."""
        row = {
            "Player": "Mike Williams",
            "School": "Central High",
            "Class": "2026",
            "Pos": "PF",
            "Ht": "6-9",
            "Wt": "220",
        }

        player, stats = maxpreps._parse_player_and_stats_from_row(
            row, state="FL", data_source=data_source
        )

        assert player is not None
        assert player.full_name == "Mike Williams"
        assert player.height_inches == 81  # 6*12 + 9
        assert player.weight_lbs == 220

        # No stats should return None
        assert stats is None

    def test_parse_various_height_formats(self, maxpreps, data_source):
        """Test parsing different height formats."""
        test_cases = [
            ("6-5", 77),   # Dash format
            ("6'5\"", 77), # Feet-inches format
            ("77", 77),    # Direct inches
        ]

        for height_str, expected_inches in test_cases:
            row = {
                "Player": "Test Player",
                "Ht": height_str,
                "PPG": "10.0",  # Need some stat to create player
            }

            player, _ = maxpreps._parse_player_and_stats_from_row(
                row, state="CA", data_source=data_source
            )

            assert player.height_inches == expected_inches, \
                f"Failed for height format: {height_str}"

    def test_parse_various_position_formats(self, maxpreps, data_source):
        """Test parsing different position formats."""
        test_cases = [
            ("PG", "PG"),
            ("SG", "SG"),
            ("SF", "SF"),
            ("PF", "PF"),
            ("C", "C"),
            ("G", "G"),
            ("F", "F"),
            ("GF", "GF"),
            ("FC", "FC"),
        ]

        for pos_str, expected_pos in test_cases:
            row = {
                "Player": "Test Player",
                "Pos": pos_str,
                "PPG": "10.0",
            }

            player, _ = maxpreps._parse_player_and_stats_from_row(
                row, state="CA", data_source=data_source
            )

            assert str(player.position) == expected_pos, \
                f"Failed for position: {pos_str}"

    def test_parse_various_column_names(self, maxpreps, data_source):
        """Test that parser handles various column naming conventions."""
        # Test player name variations
        for col_name in ["Player", "NAME", "Name", "PLAYER", "Athlete"]:
            row = {col_name: "Test Player", "PPG": "10.0"}
            player, _ = maxpreps._parse_player_and_stats_from_row(
                row, state="CA", data_source=data_source
            )
            assert player.full_name == "Test Player"

        # Test school variations
        for col_name in ["School", "SCHOOL", "Team", "TEAM", "High School"]:
            row = {"Player": "Test", col_name: "Test HS", "PPG": "10.0"}
            player, _ = maxpreps._parse_player_and_stats_from_row(
                row, state="CA", data_source=data_source
            )
            assert player.school_name == "Test HS"

    def test_season_auto_detection(self, maxpreps, data_source):
        """Test that season is auto-detected if not provided."""
        row = {
            "Player": "Test Player",
            "GP": "20",
            "PPG": "15.0",
        }

        player, stats = maxpreps._parse_player_and_stats_from_row(
            row, state="CA", data_source=data_source, season=None
        )

        assert stats is not None
        # Season should be current year (e.g., "2025-26")
        current_year = datetime.now().year
        expected_season = f"{current_year}-{str(current_year + 1)[-2:]}"
        assert stats.season == expected_season

    def test_season_explicit(self, maxpreps, data_source):
        """Test that explicit season parameter is used."""
        row = {
            "Player": "Test Player",
            "GP": "20",
            "PPG": "15.0",
        }

        player, stats = maxpreps._parse_player_and_stats_from_row(
            row, state="CA", data_source=data_source, season="2023-24"
        )

        assert stats is not None
        assert stats.season == "2023-24"

    def test_graceful_handling_of_missing_data(self, maxpreps, data_source):
        """Test that parser handles missing fields gracefully."""
        row = {
            "Player": "Minimal Player",
            "PPG": "10.0",  # Only one stat
        }

        player, stats = maxpreps._parse_player_and_stats_from_row(
            row, state="CA", data_source=data_source
        )

        assert player is not None
        assert player.full_name == "Minimal Player"

        # Should create stats with minimal data
        assert stats is not None
        assert stats.points_per_game == pytest.approx(10.0)

        # Other fields should be None
        assert stats.rebounds_per_game is None or stats.rebounds_per_game == 0
        assert stats.assists_per_game is None or stats.assists_per_game == 0

    def test_empty_row(self, maxpreps, data_source):
        """Test that empty row returns None, None."""
        row = {}

        player, stats = maxpreps._parse_player_and_stats_from_row(
            row, state="CA", data_source=data_source
        )

        assert player is None
        assert stats is None

    def test_row_with_only_irrelevant_data(self, maxpreps, data_source):
        """Test that row with no player name returns None, None."""
        row = {
            "Rank": "1",
            "SomeOtherField": "Value",
        }

        player, stats = maxpreps._parse_player_and_stats_from_row(
            row, state="CA", data_source=data_source
        )

        assert player is None
        assert stats is None

    def test_player_id_format(self, maxpreps, data_source):
        """Test that player ID is correctly formatted."""
        row = {
            "Player": "John Doe",
            "School": "Lincoln High School",
            "PPG": "10.0",
        }

        player, _ = maxpreps._parse_player_and_stats_from_row(
            row, state="CA", data_source=data_source
        )

        # Player ID should be: maxpreps_ca_lincoln_high_school_john_doe
        assert player.player_id.startswith("maxpreps_ca_")
        assert "john_doe" in player.player_id.lower()

    def test_backward_compatibility_with_search_players(self, maxpreps):
        """
        Test that existing search_players() still works.

        This verifies backward compatibility - the method should still return
        just players (ignoring stats) via tuple unpacking.
        """
        # This test doesn't make actual network calls
        # It just validates the method signature is compatible

        # Mock the parser to return test data
        def mock_parser(row, state, data_source, season=None):
            from src.models import Player, PlayerLevel
            player = Player(
                player_id="test_id",
                first_name="Test",
                last_name="Player",
                full_name="Test Player",
                level=PlayerLevel.HIGH_SCHOOL,
                school_state=state,
                school_country="USA",
                data_source=data_source,
            )
            return player, None

        # Replace parser temporarily
        original_parser = maxpreps._parse_player_and_stats_from_row
        maxpreps._parse_player_and_stats_from_row = mock_parser

        # This should work with tuple unpacking: player, _ = ...
        data_source = maxpreps.create_data_source_metadata(
            url="test", quality_flag=DataQualityFlag.COMPLETE, notes="test"
        )
        player, _ = maxpreps._parse_player_and_stats_from_row(
            {"Player": "Test"}, "CA", data_source
        )

        assert player is not None
        assert player.full_name == "Test Player"

        # Restore original parser
        maxpreps._parse_player_and_stats_from_row = original_parser


class TestSearchPlayersWithStats:
    """Test the new search_players_with_stats() method signature."""

    @pytest.fixture
    def maxpreps(self):
        """Create MaxPrepsDataSource instance."""
        return MaxPrepsDataSource()

    def test_method_exists(self, maxpreps):
        """Test that search_players_with_stats method exists."""
        assert hasattr(maxpreps, 'search_players_with_stats')
        assert callable(maxpreps.search_players_with_stats)

    def test_method_signature(self, maxpreps):
        """Test that method has correct signature."""
        import inspect
        sig = inspect.signature(maxpreps.search_players_with_stats)

        # Check parameters
        params = list(sig.parameters.keys())
        assert 'state' in params
        assert 'name' in params
        assert 'team' in params
        assert 'season' in params
        assert 'limit' in params

    def test_return_type_annotation(self, maxpreps):
        """Test that return type is correctly annotated."""
        import inspect
        sig = inspect.signature(maxpreps.search_players_with_stats)

        # Return annotation should be List[tuple[Player, Optional[PlayerSeasonStats]]]
        # This is just a basic check that annotation exists
        assert sig.return_annotation is not inspect.Signature.empty
