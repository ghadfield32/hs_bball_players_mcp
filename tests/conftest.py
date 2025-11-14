"""
Pytest Configuration and Shared Fixtures

Provides shared fixtures for all test modules.
"""

import asyncio
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from src.config import get_settings
from src.datasources.us.eybl import EYBLDataSource
from src.datasources.us.fhsaa import FHSAADataSource
from src.datasources.us.hhsaa import HHSAADataSource
from src.datasources.us.mn_hub import MNHubDataSource
from src.datasources.us.psal import PSALDataSource
from src.datasources.us.rankone import RankOneDataSource
from src.datasources.us.sblive import SBLiveDataSource
from src.datasources.us.bound import BoundDataSource
from src.datasources.us.three_ssb import ThreeSSBDataSource
from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource
from src.datasources.us.wsn import WSNDataSource
from src.datasources.europe.fiba_youth import FIBAYouthDataSource
from src.main import app
from src.services.aggregator import DataSourceAggregator, get_aggregator
from src.services.duckdb_storage import DuckDBStorage, get_duckdb_storage
from src.services.parquet_exporter import ParquetExporter, get_parquet_exporter


# Configure pytest for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Get test settings."""
    return get_settings()


# API Client Fixtures
@pytest.fixture(scope="module")
def api_client():
    """Create FastAPI test client."""
    with TestClient(app) as client:
        yield client


# DataSource Fixtures
@pytest_asyncio.fixture(scope="module")
async def eybl_source() -> AsyncGenerator[EYBLDataSource, None]:
    """Create EYBL datasource for testing."""
    source = EYBLDataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def psal_source() -> AsyncGenerator[PSALDataSource, None]:
    """Create PSAL datasource for testing."""
    source = PSALDataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def fiba_source() -> AsyncGenerator[FIBAYouthDataSource, None]:
    """Create FIBA Youth datasource for testing."""
    source = FIBAYouthDataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def mn_hub_source() -> AsyncGenerator[MNHubDataSource, None]:
    """Create MN Hub datasource for testing."""
    source = MNHubDataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def rankone_source() -> AsyncGenerator[RankOneDataSource, None]:
    """Create RankOne datasource for testing."""
    source = RankOneDataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def fhsaa_source() -> AsyncGenerator[FHSAADataSource, None]:
    """Create FHSAA datasource for testing."""
    source = FHSAADataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def hhsaa_source() -> AsyncGenerator[HHSAADataSource, None]:
    """Create HHSAA datasource for testing."""
    source = HHSAADataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def sblive_source() -> AsyncGenerator[SBLiveDataSource, None]:
    """Create SBLive datasource for testing."""
    source = SBLiveDataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def bound_source() -> AsyncGenerator[BoundDataSource, None]:
    """Create Bound datasource for testing."""
    source = BoundDataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def three_ssb_source() -> AsyncGenerator[ThreeSSBDataSource, None]:
    """Create 3SSB datasource for testing."""
    source = ThreeSSBDataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def wsn_source() -> AsyncGenerator[WSNDataSource, None]:
    """Create WSN (Wisconsin Sports Network) datasource for testing."""
    source = WSNDataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def wisconsin_wiaa_source() -> AsyncGenerator[WisconsinWiaaDataSource, None]:
    """Create Wisconsin WIAA datasource for testing (LIVE mode by default).

    Note: Uses LIVE mode which may hit real WIAA website and get HTTP 403s.
    For stable CI tests, use wisconsin_wiaa_fixture_source instead.
    """
    source = WisconsinWiaaDataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def wisconsin_wiaa_fixture_source() -> AsyncGenerator[WisconsinWiaaDataSource, None]:
    """Create Wisconsin WIAA datasource in FIXTURE mode for stable testing.

    Uses local fixture files from tests/fixtures/wiaa/ instead of live HTTP.
    Currently supports: 2024 Boys/Girls Div1
    """
    from pathlib import Path
    from src.datasources.us.wisconsin_wiaa import DataMode

    source = WisconsinWiaaDataSource(
        data_mode=DataMode.FIXTURE,
        fixtures_dir=Path("tests/fixtures/wiaa")
    )
    yield source
    await source.close()


# Service Fixtures
@pytest_asyncio.fixture(scope="module")
async def aggregator() -> AsyncGenerator[DataSourceAggregator, None]:
    """Create aggregator service for testing."""
    agg = get_aggregator()
    yield agg
    await agg.close_all()


@pytest.fixture(scope="module")
def duckdb_storage() -> DuckDBStorage:
    """Create DuckDB storage for testing."""
    return get_duckdb_storage()


@pytest.fixture(scope="module")
def parquet_exporter() -> ParquetExporter:
    """Create Parquet exporter for testing."""
    return get_parquet_exporter()


# Test Data Fixtures
@pytest.fixture
def sample_player_search_params():
    """Sample player search parameters."""
    return {
        "name": "Smith",
        "limit": 5,
    }


@pytest.fixture
def sample_team_name():
    """Sample team name for testing."""
    return "Lakers"


@pytest.fixture
def sample_season():
    """Sample season for testing."""
    return "2024-25"


# Cleanup Fixtures
@pytest.fixture(autouse=True)
def cleanup_test_exports(test_settings):
    """Clean up test export files after each test."""
    yield
    # Cleanup logic here if needed
    # For now, we'll keep test exports for manual inspection


# Markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests requiring real APIs"
    )
    config.addinivalue_line(
        "markers", "datasource: marks tests for datasource adapters"
    )
    config.addinivalue_line(
        "markers", "service: marks tests for service layer"
    )
    config.addinivalue_line(
        "markers", "api: marks tests for API endpoints"
    )
