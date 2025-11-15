"""
Integration tests for advanced stats enrichment in aggregator.

Tests that PlayerSeasonStats are automatically enriched with advanced
metrics when retrieved through the aggregator service.
"""

import pytest

from src.models import DataSource, DataSourceType, PlayerSeasonStats, Region
from src.utils.advanced_stats import (
    enrich_player_season_stats,
    get_advanced_stats_summary,
)


class TestAdvancedStatsEnrichment:
    """Test advanced stats enrichment functionality."""

    @pytest.fixture
    def sample_player_stats(self):
        """Create sample PlayerSeasonStats for testing."""
        return PlayerSeasonStats(
            player_id="test_player_001",
            player_name="Test Player",
            season="2024-25",
            league="Test League",
            games_played=25,
            minutes_played=750.0,
            points=500.0,
            field_goals_made=180.0,
            field_goals_attempted=400.0,
            three_pointers_made=50.0,
            three_pointers_attempted=150.0,
            free_throws_made=90.0,
            free_throws_attempted=100.0,
            rebounds=200.0,
            assists=125.0,
            steals=50.0,
            blocks=25.0,
            turnovers=75.0,
            data_source=DataSource(
                source_type=DataSourceType.PSAL,
                source_name="Test Source",
                region=Region.US_NORTHEAST,
            ),
        )

    def test_enrich_player_season_stats(self, sample_player_stats):
        """Test that enrich_player_season_stats adds all advanced metrics."""
        enriched = enrich_player_season_stats(sample_player_stats)

        # Verify all 9 advanced metrics are added
        assert hasattr(enriched, "true_shooting_pct")
        assert hasattr(enriched, "effective_fg_pct")
        assert hasattr(enriched, "assist_to_turnover_ratio")
        assert hasattr(enriched, "two_point_pct")
        assert hasattr(enriched, "three_point_attempt_rate")
        assert hasattr(enriched, "free_throw_rate")
        assert hasattr(enriched, "points_per_shot_attempt")
        assert hasattr(enriched, "rebounds_per_40")
        assert hasattr(enriched, "points_per_40")

        # Verify values are calculated correctly
        assert enriched.true_shooting_pct > 0
        assert enriched.effective_fg_pct > 0
        assert enriched.assist_to_turnover_ratio > 0

    def test_advanced_stats_values_reasonable(self, sample_player_stats):
        """Test that calculated advanced stats have reasonable values."""
        enriched = enrich_player_season_stats(sample_player_stats)

        # TS% should be between 0 and 1
        assert 0 <= enriched.true_shooting_pct <= 1

        # eFG% should be between 0 and 1
        assert 0 <= enriched.effective_fg_pct <= 1

        # A/TO should be positive
        assert enriched.assist_to_turnover_ratio > 0

        # Per-40 stats should be scaled up from per-game
        ppg = sample_player_stats.points / sample_player_stats.games_played
        assert enriched.points_per_40 > ppg  # Should be higher since 40 > avg minutes

    def test_get_advanced_stats_summary(self, sample_player_stats):
        """Test that get_advanced_stats_summary returns all metrics."""
        summary = get_advanced_stats_summary(sample_player_stats)

        # Verify summary is a dict with 9 keys
        assert isinstance(summary, dict)
        assert len(summary) == 9

        # Verify all expected keys are present
        expected_keys = [
            "true_shooting_pct",
            "effective_fg_pct",
            "assist_to_turnover_ratio",
            "two_point_pct",
            "three_point_attempt_rate",
            "free_throw_rate",
            "points_per_shot_attempt",
            "rebounds_per_40",
            "points_per_40",
        ]

        for key in expected_keys:
            assert key in summary
            assert summary[key] is not None

    def test_edge_case_zero_attempts(self):
        """Test that zero attempts are handled gracefully."""
        stats = PlayerSeasonStats(
            player_id="test_player_zero",
            player_name="Zero Stats Player",
            season="2024-25",
            league="Test League",
            games_played=10,
            minutes_played=0.0,
            points=0.0,
            field_goals_made=0.0,
            field_goals_attempted=0.0,
            three_pointers_made=0.0,
            three_pointers_attempted=0.0,
            free_throws_made=0.0,
            free_throws_attempted=0.0,
            rebounds=0.0,
            assists=0.0,
            steals=0.0,
            blocks=0.0,
            turnovers=0.0,
            data_source=DataSource(
                source_type=DataSourceType.PSAL,
                source_name="Test Source",
                region=Region.US_NORTHEAST,
            ),
        )

        # Should not raise exception
        enriched = enrich_player_season_stats(stats)

        # Most metrics should be None due to zero denominators
        assert enriched.true_shooting_pct is None or enriched.true_shooting_pct == 0
        assert enriched.effective_fg_pct is None or enriched.effective_fg_pct == 0

    def test_edge_case_zero_turnovers(self, sample_player_stats):
        """Test A/TO ratio when turnovers = 0."""
        sample_player_stats.turnovers = 0.0

        enriched = enrich_player_season_stats(sample_player_stats)

        # A/TO should be 99.0 when assists > 0 and turnovers = 0
        assert enriched.assist_to_turnover_ratio == 99.0

    def test_original_stats_unchanged(self, sample_player_stats):
        """Test that enrichment doesn't modify original stats."""
        original_points = sample_player_stats.points
        original_fga = sample_player_stats.field_goals_attempted

        enriched = enrich_player_season_stats(sample_player_stats)

        # Original values should be unchanged
        assert enriched.points == original_points
        assert enriched.field_goals_attempted == original_fga

    def test_enrichment_returns_same_object(self, sample_player_stats):
        """Test that enrichment modifies and returns the same object."""
        enriched = enrich_player_season_stats(sample_player_stats)

        # Should be the same object (modified in place)
        assert enriched is sample_player_stats

    def test_multiple_enrichments_idempotent(self, sample_player_stats):
        """Test that enriching twice produces same result."""
        first_enrichment = enrich_player_season_stats(sample_player_stats)
        second_enrichment = enrich_player_season_stats(first_enrichment)

        # Values should be the same
        assert (
            first_enrichment.true_shooting_pct == second_enrichment.true_shooting_pct
        )
        assert (
            first_enrichment.effective_fg_pct == second_enrichment.effective_fg_pct
        )


@pytest.mark.integration
class TestAggregatorEnrichment:
    """
    Integration tests for aggregator enrichment.

    These tests verify that the aggregator automatically enriches stats
    when returning them from get_player_season_stats_all_sources.

    NOTE: These tests require a running aggregator with enabled datasources.
    Mark as @pytest.mark.integration to run separately from unit tests.
    """

    def test_aggregator_enriches_stats(self):
        """
        Test that aggregator enriches stats before returning.

        NOTE: This is a placeholder test. Actual implementation requires:
        1. Mock datasources returning PlayerSeasonStats
        2. Verify aggregator enriches them with advanced metrics
        3. Verify all 9 advanced metrics are present

        This test will be implemented when integration testing is set up.
        """
        # TODO: Implement when integration testing infrastructure is ready
        pytest.skip("Integration test - requires datasource mocking")

    def test_api_endpoint_returns_enriched_stats(self):
        """
        Test that API endpoint returns enriched stats with advanced metrics.

        NOTE: This is a placeholder test. Actual implementation requires:
        1. Test client making request to /api/v1/players/{name}/stats
        2. Verify response includes advanced metrics in JSON
        3. Verify OpenAPI docs mention advanced metrics

        This test will be implemented when API testing is set up.
        """
        # TODO: Implement when API testing infrastructure is ready
        pytest.skip("Integration test - requires API client")
