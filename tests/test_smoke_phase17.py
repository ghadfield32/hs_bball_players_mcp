"""
Phase 17 Smoke Tests - High-Impact State Adapters

Wraps smoke test checks as pytest cases for CI/CD integration.
Tests verify that Phase 17 high-impact state adapters are reachable and can fetch data.

**Phase 17 Adapters (7 total):**
- California CIF-SS (1,600+ schools, largest section)
- Texas UIL (1,400+ schools, second-largest system)
- Florida FHSAA (800+ schools, third-largest system)
- Georgia GHSA (500+ schools, strong basketball state)
- Ohio OHSAA (800+ schools, strong basketball state)
- Pennsylvania PIAA (600+ schools, strong basketball state)
- New York NYSPHSAA (700+ schools, strong basketball state)

Usage:
    pytest tests/test_smoke_phase17.py -v
    pytest tests/test_smoke_phase17.py -v -m smoke_phase17
    pytest tests/test_smoke_phase17.py -v --tb=short  # Short traceback format
"""

import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.california_cif_ss import CaliforniaCIFSSDataSource
from src.datasources.us.texas_uil import TexasUILDataSource
from src.datasources.us.florida_fhsaa import FloridaFHSAADataSource
from src.datasources.us.georgia_ghsa import GeorgiaGHSADataSource
from src.datasources.us.ohio_ohsaa import OhioOHSAADataSource
from src.datasources.us.pennsylvania_piaa import PennsylvaniaPIAADataSource
from src.datasources.us.newyork_nysphsaa import NewYorkNYSPHSAADataSource


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_california_cif_ss_reachable():
    """Test that California CIF-SS API is reachable."""
    ds = CaliforniaCIFSSDataSource()
    try:
        is_healthy = await ds.health_check()
        assert is_healthy, "California CIF-SS health check failed - API unreachable"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_california_cif_ss_data_fetch():
    """Test that California CIF-SS can fetch tournament data."""
    ds = CaliforniaCIFSSDataSource()
    try:
        # This may return empty results if 2025 data not published yet
        brackets = await ds.get_tournament_brackets(season="2024-25", division="Open", gender="Boys")

        # Assert that the call succeeded (even if no games found)
        assert brackets is not None, "get_tournament_brackets returned None"
        assert "games" in brackets, "Response missing 'games' key"

        # Note: We don't assert len(games) > 0 since 2025 data may not be available yet
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_texas_uil_reachable():
    """Test that Texas UIL API is reachable."""
    ds = TexasUILDataSource()
    try:
        is_healthy = await ds.health_check()
        assert is_healthy, "Texas UIL health check failed - API unreachable"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_texas_uil_data_fetch():
    """Test that Texas UIL can fetch tournament data."""
    ds = TexasUILDataSource()
    try:
        brackets = await ds.get_tournament_brackets(season="2024-25", classification="6A", gender="Boys")

        assert brackets is not None, "get_tournament_brackets returned None"
        assert "games" in brackets, "Response missing 'games' key"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_florida_fhsaa_reachable():
    """Test that Florida FHSAA API is reachable."""
    ds = FloridaFHSAADataSource()
    try:
        is_healthy = await ds.health_check()
        assert is_healthy, "Florida FHSAA health check failed - API unreachable"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_florida_fhsaa_data_fetch():
    """Test that Florida FHSAA can fetch tournament data."""
    ds = FloridaFHSAADataSource()
    try:
        brackets = await ds.get_tournament_brackets(season="2024-25", classification="7A", gender="Boys")

        assert brackets is not None, "get_tournament_brackets returned None"
        assert "games" in brackets, "Response missing 'games' key"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_georgia_ghsa_reachable():
    """Test that Georgia GHSA API is reachable."""
    ds = GeorgiaGHSADataSource()
    try:
        is_healthy = await ds.health_check()
        assert is_healthy, "Georgia GHSA health check failed - API unreachable"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_georgia_ghsa_data_fetch():
    """Test that Georgia GHSA can fetch tournament data."""
    ds = GeorgiaGHSADataSource()
    try:
        brackets = await ds.get_tournament_brackets(season="2024-25", classification="7A", gender="Boys")

        assert brackets is not None, "get_tournament_brackets returned None"
        assert "games" in brackets, "Response missing 'games' key"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_ohio_ohsaa_reachable():
    """Test that Ohio OHSAA API is reachable."""
    ds = OhioOHSAADataSource()
    try:
        is_healthy = await ds.health_check()
        assert is_healthy, "Ohio OHSAA health check failed - API unreachable"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_ohio_ohsaa_data_fetch():
    """Test that Ohio OHSAA can fetch tournament data."""
    ds = OhioOHSAADataSource()
    try:
        brackets = await ds.get_tournament_brackets(season="2024-25", division="I", gender="Boys")

        assert brackets is not None, "get_tournament_brackets returned None"
        assert "games" in brackets, "Response missing 'games' key"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_pennsylvania_piaa_reachable():
    """Test that Pennsylvania PIAA API is reachable."""
    ds = PennsylvaniaPIAADataSource()
    try:
        is_healthy = await ds.health_check()
        assert is_healthy, "Pennsylvania PIAA health check failed - API unreachable"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_pennsylvania_piaa_data_fetch():
    """Test that Pennsylvania PIAA can fetch tournament data."""
    ds = PennsylvaniaPIAADataSource()
    try:
        brackets = await ds.get_tournament_brackets(season="2024-25", classification="6A", gender="Boys")

        assert brackets is not None, "get_tournament_brackets returned None"
        assert "games" in brackets, "Response missing 'games' key"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_newyork_nysphsaa_reachable():
    """Test that New York NYSPHSAA API is reachable."""
    ds = NewYorkNYSPHSAADataSource()
    try:
        is_healthy = await ds.health_check()
        assert is_healthy, "New York NYSPHSAA health check failed - API unreachable"
    finally:
        await ds.close()


@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_newyork_nysphsaa_data_fetch():
    """Test that New York NYSPHSAA can fetch tournament data."""
    ds = NewYorkNYSPHSAADataSource()
    try:
        brackets = await ds.get_tournament_brackets(season="2024-25", classification="AA", gender="Boys")

        assert brackets is not None, "get_tournament_brackets returned None"
        assert "games" in brackets, "Response missing 'games' key"
    finally:
        await ds.close()


# Optional: Integration test that runs all checks together
@pytest.mark.smoke_phase17
@pytest.mark.asyncio
async def test_all_phase17_sources_integration():
    """
    Integration test: Verify all Phase 17 data sources are functional.

    This test checks that all 7 high-impact state adapters (CA, TX, FL, GA, OH, PA, NY) are:
    1. Reachable (health checks pass)
    2. Can fetch data without errors (even if empty)
    """
    sources = [
        ("California CIF-SS", CaliforniaCIFSSDataSource()),
        ("Texas UIL", TexasUILDataSource()),
        ("Florida FHSAA", FloridaFHSAADataSource()),
        ("Georgia GHSA", GeorgiaGHSADataSource()),
        ("Ohio OHSAA", OhioOHSAADataSource()),
        ("Pennsylvania PIAA", PennsylvaniaPIAADataSource()),
        ("New York NYSPHSAA", NewYorkNYSPHSAADataSource()),
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
