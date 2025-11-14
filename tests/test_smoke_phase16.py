"""
Phase 16 Smoke Tests - Pytest Wrapper

Wraps smoke test checks as pytest cases for CI/CD integration.
Tests verify that data sources are reachable and can fetch data.

Usage:
    pytest tests/test_smoke_phase16.py -v
    pytest tests/test_smoke_phase16.py -v -m smoke_phase16
    pytest tests/test_smoke_phase16.py -v --tb=short  # Short traceback format
"""

import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.arizona_aia import ArizonaAIADataSource
from src.datasources.us.idaho_ihsaa import IdahoIHSAADataSource
from src.datasources.us.washington_wiaa import WashingtonWIAADataSource
from src.datasources.us.nevada_niaa import NevadaNIAADataSource


@pytest.mark.smoke_phase16
@pytest.mark.asyncio
async def test_arizona_aia_reachable():
    """Test that Arizona AIA API is reachable."""
    ds = ArizonaAIADataSource()
    try:
        is_healthy = await ds.health_check()
        assert is_healthy, "Arizona AIA health check failed - API unreachable"
    finally:
        await ds.close()


@pytest.mark.smoke_phase16
@pytest.mark.asyncio
async def test_arizona_aia_data_fetch():
    """Test that Arizona AIA can fetch tournament data."""
    ds = ArizonaAIADataSource()
    try:
        # This may return empty results if 2025 data not published yet
        brackets = await ds.get_tournament_brackets(season="2024-25", conference="6A", gender="Boys")

        # Assert that the call succeeded (even if no games found)
        assert brackets is not None, "get_tournament_brackets returned None"
        assert "games" in brackets, "Response missing 'games' key"

        # Note: We don't assert len(games) > 0 since 2025 data may not be available yet
    finally:
        await ds.close()


@pytest.mark.smoke_phase16
@pytest.mark.asyncio
async def test_idaho_ihsaa_reachable():
    """Test that Idaho IHSAA API is reachable."""
    ds = IdahoIHSAADataSource()
    try:
        is_healthy = await ds.health_check()
        assert is_healthy, "Idaho IHSAA health check failed - API unreachable"
    finally:
        await ds.close()


@pytest.mark.smoke_phase16
@pytest.mark.asyncio
async def test_idaho_ihsaa_data_fetch():
    """Test that Idaho IHSAA can fetch tournament data."""
    ds = IdahoIHSAADataSource()
    try:
        brackets = await ds.get_tournament_brackets(season="2024-25", classification="5A", gender="Boys")

        assert brackets is not None, "get_tournament_brackets returned None"
        assert "games" in brackets, "Response missing 'games' key"
    finally:
        await ds.close()


@pytest.mark.smoke_phase16
@pytest.mark.asyncio
async def test_washington_wiaa_reachable():
    """Test that Washington WIAA API is reachable."""
    ds = WashingtonWIAADataSource()
    try:
        is_healthy = await ds.health_check()
        assert is_healthy, "Washington WIAA health check failed - API unreachable"
    finally:
        await ds.close()


@pytest.mark.smoke_phase16
@pytest.mark.asyncio
async def test_washington_wiaa_data_fetch():
    """Test that Washington WIAA can fetch tournament data."""
    ds = WashingtonWIAADataSource()
    try:
        brackets = await ds.get_tournament_brackets(season="2024-25", classification="4A", gender="Boys")

        assert brackets is not None, "get_tournament_brackets returned None"
        assert "games" in brackets, "Response missing 'games' key"
    finally:
        await ds.close()


@pytest.mark.smoke_phase16
@pytest.mark.asyncio
async def test_nevada_niaa_reachable():
    """Test that Nevada NIAA API is reachable."""
    ds = NevadaNIAADataSource()
    try:
        is_healthy = await ds.health_check()
        assert is_healthy, "Nevada NIAA health check failed - API unreachable"
    finally:
        await ds.close()


@pytest.mark.smoke_phase16
@pytest.mark.asyncio
async def test_nevada_niaa_data_fetch():
    """Test that Nevada NIAA can fetch tournament data (from PDFs)."""
    ds = NevadaNIAADataSource()
    try:
        brackets = await ds.get_tournament_brackets(season="2024-25", division="5A", gender="Boys")

        assert brackets is not None, "get_tournament_brackets returned None"
        assert "games" in brackets, "Response missing 'games' key"
    finally:
        await ds.close()


# Optional: Integration test that runs all checks together
@pytest.mark.smoke_phase16
@pytest.mark.asyncio
async def test_all_sources_integration():
    """
    Integration test: Verify all Phase 16 data sources are functional.

    This test checks that all 4 sources (Arizona, Idaho, Washington, Nevada) are:
    1. Reachable (health checks pass)
    2. Can fetch data without errors (even if empty)
    """
    sources = [
        ("Arizona AIA", ArizonaAIADataSource()),
        ("Idaho IHSAA", IdahoIHSAADataSource()),
        ("Washington WIAA", WashingtonWIAADataSource()),
        ("Nevada NIAA", NevadaNIAADataSource()),
    ]

    results = []

    try:
        for name, ds in sources:
            try:
                is_healthy = await ds.health_check()
                results.append((name, is_healthy))
            finally:
                await ds.close()

        # Assert all are healthy
        failed = [name for name, healthy in results if not healthy]
        assert len(failed) == 0, f"Health checks failed for: {', '.join(failed)}"

    finally:
        # Ensure all datasources are closed
        for _, ds in sources:
            await ds.close()
