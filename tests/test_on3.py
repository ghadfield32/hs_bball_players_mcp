"""
Smoke tests for On3/Rivals recruiting adapter.

Tests basic functionality:
- Page 1 fetching works
- Count validation works (pagination metadata)
- No parse errors

Author: Claude Code
Date: 2025-11-15
"""

import sys
from pathlib import Path

# Add parent directory to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.mark.asyncio
async def test_on3_page_1_basic():
    """Test fetching first page of On3 rankings."""
    from src.datasources.recruiting.on3 import On3DataSource

    on3 = On3DataSource()

    # Fetch top 10 players from 2025 class
    rankings = await on3.get_rankings(class_year=2025, limit=10)

    # Basic assertions
    assert rankings is not None, "Rankings should not be None"
    assert len(rankings) == 10, f"Expected 10 rankings, got {len(rankings)}"
    assert all(r.player_name for r in rankings), "All players should have names"
    assert all(r.rank_national for r in rankings), "All players should have ranks"


@pytest.mark.asyncio
async def test_on3_count_validation():
    """Test that pagination count metadata is extracted correctly."""
    from src.datasources.recruiting.on3 import On3DataSource

    on3 = On3DataSource()

    # Fetch 50 rankings (exactly 1 page)
    rankings = await on3.get_rankings(class_year=2025, limit=50)

    # Should get exactly 50 rankings from page 1
    assert len(rankings) == 50, f"Expected 50 rankings, got {len(rankings)}"

    # Check sequential ranking
    ranks = [r.rank_national for r in rankings]
    expected_ranks = list(range(1, 51))
    assert ranks == expected_ranks, "Rankings should be sequential from 1-50"


@pytest.mark.asyncio
async def test_on3_no_parse_errors():
    """Test that all players parse without errors."""
    from src.datasources.recruiting.on3 import On3DataSource

    on3 = On3DataSource()

    # Fetch 20 rankings
    rankings = await on3.get_rankings(class_year=2025, limit=20)

    # All should parse successfully
    assert len(rankings) == 20, "Should get 20 valid rankings"

    # Check all have required fields (no None for required fields)
    for rank in rankings:
        assert rank.player_name is not None, f"Player missing name: {rank}"
        assert rank.rank_national is not None, f"Player missing rank: {rank.player_name}"
        assert rank.stars is not None, f"Player missing stars: {rank.player_name}"
        assert rank.service == "industry", f"Wrong service: {rank.service}"


@pytest.mark.asyncio
async def test_on3_robust_field_extraction():
    """Test that _safe_get helper handles missing fields gracefully."""
    from src.datasources.recruiting.on3 import On3DataSource

    on3 = On3DataSource()

    # Test _safe_get with valid path
    test_obj = {
        "person": {
            "name": "Test Player",
            "rating": {
                "consensusRank": 1
            }
        }
    }

    assert on3._safe_get(test_obj, "person.name") == "Test Player"
    assert on3._safe_get(test_obj, "person.rating.consensusRank") == 1
    assert on3._safe_get(test_obj, "person.missing.field") is None
    assert on3._safe_get(test_obj, "person.missing.field", default=0) == 0


if __name__ == "__main__":
    # Allow running directly for quick testing
    import asyncio

    async def run_tests():
        print("Running On3 smoke tests...")
        await test_on3_page_1_basic()
        print("[PASS] test_on3_page_1_basic")

        await test_on3_count_validation()
        print("[PASS] test_on3_count_validation")

        await test_on3_no_parse_errors()
        print("[PASS] test_on3_no_parse_errors")

        await test_on3_robust_field_extraction()
        print("[PASS] test_on3_robust_field_extraction")

        print("\n=== All 4 On3 smoke tests passed ===")

    asyncio.run(run_tests())
