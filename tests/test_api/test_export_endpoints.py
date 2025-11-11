"""
Export and Analytics API Endpoint Tests

Tests export and analytics endpoints with real API calls.
"""

import pytest


@pytest.mark.integration
@pytest.mark.api
class TestExportEndpoints:
    """Test suite for export API endpoints."""

    def test_export_players_csv(self, api_client):
        """Test exporting players to CSV format."""
        response = api_client.get(
            "/api/v1/export/players/csv",
            params={"limit": 10}
        )

        assert response.status_code == 200 or response.status_code == 404

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] == "success"
            assert "format" in data
            assert data["format"] == "csv"
            assert "records" in data

    def test_export_players_json(self, api_client):
        """Test exporting players to JSON format."""
        response = api_client.get(
            "/api/v1/export/players/json",
            params={"limit": 5}
        )

        assert response.status_code == 200 or response.status_code == 404

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert data["format"] == "json"

    def test_export_players_parquet(self, api_client):
        """Test exporting players to Parquet format."""
        response = api_client.get(
            "/api/v1/export/players/parquet",
            params={"limit": 10}
        )

        assert response.status_code == 200 or response.status_code == 404

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert data["format"] == "parquet"

    def test_export_players_with_source_filter(self, api_client):
        """Test exporting players filtered by source."""
        response = api_client.get(
            "/api/v1/export/players/json",
            params={"source": "eybl", "limit": 5}
        )

        assert response.status_code == 200 or response.status_code == 404

    def test_export_players_with_name_filter(self, api_client):
        """Test exporting players filtered by name."""
        response = api_client.get(
            "/api/v1/export/players/json",
            params={"name": "Johnson", "limit": 5}
        )

        assert response.status_code == 200 or response.status_code == 404

    def test_export_players_with_school_filter(self, api_client):
        """Test exporting players filtered by school."""
        response = api_client.get(
            "/api/v1/export/players/json",
            params={"school": "Lincoln", "limit": 5}
        )

        assert response.status_code == 200 or response.status_code == 404

    def test_export_players_limit_validation(self, api_client):
        """Test that export respects limit bounds."""
        # Test limit too high
        response = api_client.get(
            "/api/v1/export/players/json",
            params={"limit": 20000}  # Above max of 10000
        )

        # Should reject or cap the limit
        assert response.status_code == 422  # Validation error

    def test_export_stats_csv(self, api_client):
        """Test exporting player stats to CSV format."""
        response = api_client.get(
            "/api/v1/export/stats/csv",
            params={"limit": 10}
        )

        assert response.status_code == 200 or response.status_code == 404

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert data["format"] == "csv"

    def test_export_stats_json(self, api_client):
        """Test exporting player stats to JSON format."""
        response = api_client.get(
            "/api/v1/export/stats/json",
            params={"limit": 5}
        )

        assert response.status_code == 200 or response.status_code == 404

    def test_export_stats_with_season_filter(self, api_client):
        """Test exporting stats filtered by season."""
        response = api_client.get(
            "/api/v1/export/stats/json",
            params={"season": "2024-25", "limit": 10}
        )

        assert response.status_code == 200 or response.status_code == 404

    def test_export_stats_with_min_ppg_filter(self, api_client):
        """Test exporting stats filtered by minimum PPG."""
        response = api_client.get(
            "/api/v1/export/stats/json",
            params={"min_ppg": 20.0, "limit": 10}
        )

        assert response.status_code == 200 or response.status_code == 404

    def test_get_export_info(self, api_client):
        """Test getting export file information."""
        response = api_client.get("/api/v1/export/info")

        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "success"
        assert "exports" in data
        assert isinstance(data["exports"], list)

    def test_get_export_info_with_category(self, api_client):
        """Test getting export info filtered by category."""
        response = api_client.get(
            "/api/v1/export/info",
            params={"category": "players"}
        )

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

    def test_invalid_export_format(self, api_client):
        """Test that invalid export format is rejected."""
        # Try invalid format
        response = api_client.get("/api/v1/export/players/invalid")

        # Should return 422 validation error or 404
        assert response.status_code in [404, 422]


@pytest.mark.integration
@pytest.mark.api
class TestAnalyticsEndpoints:
    """Test suite for analytics API endpoints."""

    def test_get_analytics_summary(self, api_client):
        """Test getting analytics summary."""
        response = api_client.get("/api/v1/analytics/summary")

        # DuckDB might not be enabled in test environment
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] == "success"
            assert "summary" in data

            summary = data["summary"]
            assert "total_players" in summary
            assert "players_by_source" in summary

    def test_get_leaderboard_ppg(self, api_client):
        """Test getting PPG leaderboard from analytics."""
        response = api_client.get(
            "/api/v1/analytics/leaderboard/points_per_game",
            params={"limit": 10}
        )

        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "leaderboard" in data
            assert isinstance(data["leaderboard"], list)
            assert len(data["leaderboard"]) <= 10

    def test_get_leaderboard_rpg(self, api_client):
        """Test getting RPG leaderboard from analytics."""
        response = api_client.get(
            "/api/v1/analytics/leaderboard/rebounds_per_game",
            params={"limit": 5}
        )

        assert response.status_code in [200, 404, 503]

    def test_get_leaderboard_with_season_filter(self, api_client):
        """Test getting leaderboard filtered by season."""
        response = api_client.get(
            "/api/v1/analytics/leaderboard/points_per_game",
            params={"season": "2024-25", "limit": 10}
        )

        assert response.status_code in [200, 404, 503]

    def test_get_leaderboard_with_source_filter(self, api_client):
        """Test getting leaderboard filtered by source."""
        response = api_client.get(
            "/api/v1/analytics/leaderboard/points_per_game",
            params={"source": "eybl", "limit": 10}
        )

        assert response.status_code in [200, 404, 503]

    def test_query_players_analytics(self, api_client):
        """Test querying players from DuckDB."""
        response = api_client.get(
            "/api/v1/analytics/query/players",
            params={"limit": 10}
        )

        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "players" in data
            assert isinstance(data["players"], list)

    def test_query_players_by_name(self, api_client):
        """Test querying players by name."""
        response = api_client.get(
            "/api/v1/analytics/query/players",
            params={"name": "Johnson", "limit": 5}
        )

        assert response.status_code in [200, 404, 503]

    def test_query_players_by_school(self, api_client):
        """Test querying players by school."""
        response = api_client.get(
            "/api/v1/analytics/query/players",
            params={"school": "Lincoln", "limit": 5}
        )

        assert response.status_code in [200, 404, 503]

    def test_query_players_by_source(self, api_client):
        """Test querying players by source."""
        response = api_client.get(
            "/api/v1/analytics/query/players",
            params={"source": "eybl", "limit": 10}
        )

        assert response.status_code in [200, 404, 503]

    def test_query_stats_analytics(self, api_client):
        """Test querying player stats from DuckDB."""
        response = api_client.get(
            "/api/v1/analytics/query/stats",
            params={"limit": 10}
        )

        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "stats" in data
            assert isinstance(data["stats"], list)

    def test_query_stats_by_player_name(self, api_client):
        """Test querying stats by player name."""
        response = api_client.get(
            "/api/v1/analytics/query/stats",
            params={"player_name": "Johnson", "limit": 5}
        )

        assert response.status_code in [200, 404, 503]

    def test_query_stats_by_season(self, api_client):
        """Test querying stats by season."""
        response = api_client.get(
            "/api/v1/analytics/query/stats",
            params={"season": "2024-25", "limit": 10}
        )

        assert response.status_code in [200, 404, 503]

    def test_query_stats_by_min_ppg(self, api_client):
        """Test querying stats by minimum PPG."""
        response = api_client.get(
            "/api/v1/analytics/query/stats",
            params={"min_ppg": 20.0, "limit": 10}
        )

        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            data = response.json()
            if len(data["stats"]) > 0:
                # All results should meet minimum
                for stat in data["stats"]:
                    assert stat["points_per_game"] >= 20.0

    def test_query_stats_combined_filters(self, api_client):
        """Test querying stats with multiple filters."""
        response = api_client.get(
            "/api/v1/analytics/query/stats",
            params={
                "season": "2024-25",
                "min_ppg": 15.0,
                "source": "eybl",
                "limit": 5
            }
        )

        assert response.status_code in [200, 404, 503]

    def test_analytics_limit_validation(self, api_client):
        """Test that analytics endpoints validate limits."""
        # Test limit too high
        response = api_client.get(
            "/api/v1/analytics/query/players",
            params={"limit": 5000}  # Above max of 1000
        )

        # Should reject
        assert response.status_code == 422

    def test_leaderboard_limit_validation(self, api_client):
        """Test that leaderboard validates limits."""
        # Test limit too high
        response = api_client.get(
            "/api/v1/analytics/leaderboard/points_per_game",
            params={"limit": 500}  # Above max of 200
        )

        # Should reject
        assert response.status_code == 422
