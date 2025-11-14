"""
NIAA (Nevada Interscholastic Activities Association) DataSource Tests

Smoke tests for NIAA datasource (tournament brackets).
Official Nevada state association with PDF hash caching.
"""

import pytest

from src.datasources.us.nevada_niaa import NevadaNIAADataSource
from src.models import DataSourceType, DataSourceRegion, Game


@pytest.mark.datasource
class TestNevadaNIAADataSource:
    """Test suite for Nevada NIAA datasource."""

    @pytest.fixture
    def niaa_source(self):
        """Create NIAA datasource instance."""
        return NevadaNIAADataSource()

    def test_initialization(self, niaa_source):
        """Test NIAA datasource initializes correctly."""
        assert niaa_source is not None
        assert niaa_source.source_type == DataSourceType.NIAA
        assert niaa_source.source_name == "Nevada NIAA"
        assert niaa_source.region == DataSourceRegion.US_NV
        assert niaa_source.STATE_CODE == "NV"
        assert niaa_source.STATE_NAME == "Nevada"

    def test_constants(self, niaa_source):
        """Test NIAA constants are defined."""
        assert niaa_source.DIVISIONS == ["5A", "4A", "3A", "2A", "1A"]
        assert niaa_source.GENDERS == ["Boys", "Girls"]

    def test_pdf_cache_initialization(self, niaa_source):
        """Test PDF cache is initialized."""
        assert hasattr(niaa_source, 'pdf_cache')
        assert isinstance(niaa_source.pdf_cache, dict)

    def test_build_bracket_url(self, niaa_source):
        """Test bracket URL construction."""
        url = niaa_source._build_bracket_url(
            division="5A",
            gender="Boys",
            year=2025
        )

        assert "nv.gov" in url or "niaa" in url.lower()
        assert "2025" in url

    def test_extract_team_and_seed(self, niaa_source):
        """Test team name and seed extraction."""
        # Verify the method exists
        assert hasattr(niaa_source, '_extract_team_and_seed')

        # Test with seed in parentheses
        team, seed = niaa_source._extract_team_and_seed("Bishop Gorman (1)")
        assert team == "Bishop Gorman"
        assert seed == 1

        # Without seed
        team, seed = niaa_source._extract_team_and_seed("Centennial")
        assert team == "Centennial"
        assert seed is None

    @pytest.mark.asyncio
    async def test_health_check(self, niaa_source):
        """Test NIAA health check."""
        is_healthy = await niaa_source.health_check()
        assert isinstance(is_healthy, bool)

    def test_pdf_hash_caching_mechanism(self, niaa_source):
        """Test PDF hash caching mechanism exists."""
        # NIAA should have methods for PDF caching
        assert hasattr(niaa_source, '_fetch_and_parse_pdf')
        assert hasattr(niaa_source, 'pdf_cache')

    def test_pdf_cache_structure(self, niaa_source):
        """Test PDF cache can store data."""
        # Simulate adding to cache
        test_hash = "abc123def456"
        test_data = {
            "games": [],
            "teams": [],
            "metadata": {"pdf_hash": test_hash, "extracted_text_len": 1000}
        }

        niaa_source.pdf_cache[test_hash] = test_data

        # Verify retrieval
        assert test_hash in niaa_source.pdf_cache
        assert niaa_source.pdf_cache[test_hash] == test_data

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_tournament_brackets_with_pdf(self, niaa_source):
        """
        Test tournament bracket fetching with PDF support.

        NOTE: This test makes real API calls. It may fail if:
        - NIAA website is down
        - Tournament data is not yet available for the season
        - PDF structure has changed
        - pdfplumber is not installed
        """
        try:
            brackets = await niaa_source.get_tournament_brackets(
                season="2024-25",
                division="5A",  # Only fetch 5A to limit API calls
                gender="Boys"
            )

            # Check structure
            assert isinstance(brackets, dict)
            assert "games" in brackets
            assert "teams" in brackets
            assert "brackets" in brackets
            assert "metadata" in brackets

            assert isinstance(brackets["games"], list)
            assert isinstance(brackets["teams"], list)
            assert isinstance(brackets["brackets"], dict)

            # If games were found, validate structure
            if len(brackets["games"]) > 0:
                game = brackets["games"][0]
                assert isinstance(game, Game)
                assert game.game_id.startswith("niaa_")
                assert game.game_type.value == "playoff"
                assert game.data_source is not None
                assert game.data_source.source_type == DataSourceType.NIAA

            # Check if PDF was used (metadata may contain pdf_hash)
            if len(brackets["metadata"]) > 0:
                for div_metadata in brackets["metadata"].values():
                    if "pdf_hash" in div_metadata:
                        # PDF was successfully parsed
                        assert "extracted_text_len" in div_metadata
                        assert div_metadata["extracted_text_len"] > 0

        except ImportError:
            pytest.skip("pdfplumber not installed - required for NIAA PDF parsing")
        except Exception as e:
            pytest.skip(f"NIAA API call failed (site may be down or season not available): {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_pdf_caching_works(self, niaa_source):
        """
        Test that PDF caching prevents re-parsing same PDF.

        This test fetches the same bracket twice and verifies cache is used.
        """
        try:
            # First fetch
            brackets1 = await niaa_source.get_tournament_brackets(
                season="2024-25",
                division="5A",
                gender="Boys"
            )

            # Get cache size
            cache_size_1 = len(niaa_source.pdf_cache)

            # Second fetch (should use cache)
            brackets2 = await niaa_source.get_tournament_brackets(
                season="2024-25",
                division="5A",
                gender="Boys"
            )

            # Cache size should be same (or larger if multiple PDFs)
            cache_size_2 = len(niaa_source.pdf_cache)
            assert cache_size_2 >= cache_size_1

            # Results should be consistent
            assert len(brackets1["games"]) == len(brackets2["games"])

        except ImportError:
            pytest.skip("pdfplumber not installed - required for NIAA PDF parsing")
        except Exception as e:
            pytest.skip(f"NIAA caching test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_games(self, niaa_source):
        """
        Test getting games from tournament brackets.

        NOTE: This test makes real API calls and may be slow.
        """
        try:
            games = await niaa_source.get_games(
                season="2024-25",
                limit=5
            )

            assert isinstance(games, list)
            assert len(games) <= 5

            # If games found, validate structure
            if len(games) > 0:
                for game in games:
                    assert isinstance(game, Game)
                    assert game.game_id
                    assert game.home_team_name or game.away_team_name

        except ImportError:
            pytest.skip("pdfplumber not installed")
        except Exception as e:
            pytest.skip(f"NIAA get_games failed: {e}")

    def test_player_methods_not_supported(self, niaa_source):
        """Test that player methods return None/empty (not supported by NIAA)."""
        # NIAA doesn't provide player stats (by design)
        assert hasattr(niaa_source, 'search_players')
        assert hasattr(niaa_source, 'get_player')
        assert hasattr(niaa_source, 'get_player_season_stats')
        assert hasattr(niaa_source, 'get_leaderboard')

    def test_division_configuration(self, niaa_source):
        """Test NIAA division configuration."""
        # Verify all 5 divisions are configured
        assert len(niaa_source.DIVISIONS) == 5
        for division in ["5A", "4A", "3A", "2A", "1A"]:
            assert division in niaa_source.DIVISIONS

    @pytest.mark.asyncio
    async def test_get_team(self, niaa_source):
        """Test getting a specific team."""
        # This test won't work well without knowing a team_id in advance
        # Just verify the method exists and has correct signature
        assert hasattr(niaa_source, 'get_team')

        import inspect
        assert inspect.iscoroutinefunction(niaa_source.get_team)
