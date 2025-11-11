# Test Suite

Comprehensive test suite for the HS Basketball Players Multi-Datasource API.

## Overview

This test suite includes:
- **Datasource Tests**: Real API integration tests for EYBL, PSAL, FIBA Youth, and MN Hub
- **Service Tests**: Tests for aggregator, DuckDB storage, and Parquet exporter
- **API Tests**: End-to-end tests for all REST API endpoints

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Run only datasource tests
pytest -m datasource

# Run only service tests
pytest -m service

# Run only API tests
pytest -m api

# Run only integration tests
pytest -m integration

# Run fast tests only (skip slow tests)
pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Test EYBL datasource
pytest tests/test_datasources/test_eybl.py

# Test aggregator service
pytest tests/test_services/test_aggregator.py

# Test export endpoints
pytest tests/test_api/test_export_endpoints.py
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html --cov-report=term
```

Coverage report will be generated in `htmlcov/index.html`.

### Run with Verbose Output

```bash
pytest -v
pytest -vv  # Extra verbose
```

### Run Specific Test

```bash
pytest tests/test_datasources/test_eybl.py::TestEYBLDataSource::test_search_players_by_name
```

## Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.integration` - Integration tests with real APIs
- `@pytest.mark.datasource` - Datasource adapter tests
- `@pytest.mark.service` - Service layer tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.slow` - Slow tests (may take 10+ seconds)

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_datasources/        # Datasource adapter tests
│   ├── test_eybl.py        # EYBL integration tests
│   ├── test_psal.py        # PSAL integration tests
│   ├── test_fiba_youth.py  # FIBA Youth integration tests
│   └── test_mn_hub.py      # MN Hub integration tests
├── test_services/          # Service layer tests
│   ├── test_aggregator.py  # Multi-source aggregator tests
│   ├── test_duckdb_storage.py  # DuckDB storage tests
│   └── test_parquet_exporter.py  # Parquet exporter tests
└── test_api/               # API endpoint tests
    └── test_export_endpoints.py  # Export & analytics API tests
```

## Test Data

Tests use:
- **Real API calls** - Tests make actual HTTP requests to datasources
- **Test fixtures** - Shared fixtures defined in `conftest.py`
- **Temporary data** - Test exports are created in `data/exports/`

## Important Notes

### Rate Limiting

Datasource tests make real API calls and respect rate limits. If you see rate limit errors:
- Run with `pytest -m "not slow"` to skip heavy tests
- Run specific test files instead of the full suite
- Wait a few minutes between full test runs

### DuckDB Tests

DuckDB storage tests use the configured DuckDB database (from `.env`). In production, use a separate test database:

```bash
DUCKDB_PATH="./data/test_basketball_analytics.duckdb"
```

### Network Dependency

Integration tests require internet connectivity to access:
- Nike EYBL website
- PSAL website
- FIBA Youth website
- Minnesota Basketball Hub

### Test Duration

Full test suite takes approximately:
- **Fast tests only**: ~30 seconds
- **Full suite with integration tests**: 2-5 minutes

## Continuous Integration

For CI/CD pipelines:

```bash
# Fast tests only (for quick CI)
pytest -m "not slow" --tb=short

# Full suite with coverage (for main branch)
pytest --cov=src --cov-report=xml --tb=short
```

## Troubleshooting

### Tests Fail with Network Errors

Check internet connection and datasource availability:
```bash
pytest tests/test_datasources/test_eybl.py::TestEYBLDataSource::test_health_check
```

### Tests Fail with DuckDB Errors

Check DuckDB configuration in `.env`:
```bash
DUCKDB_ENABLED=true
DUCKDB_PATH="./data/basketball_analytics.duckdb"
```

### Tests Timeout

Increase timeout in pytest.ini or run fast tests:
```bash
pytest -m "not slow"
```

## Writing New Tests

### Datasource Tests

```python
@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestNewDataSource:
    @pytest.mark.asyncio
    async def test_search_players(self, new_source):
        players = await new_source.search_players(limit=5)
        assert isinstance(players, list)
```

### Service Tests

```python
@pytest.mark.integration
@pytest.mark.service
class TestNewService:
    @pytest.mark.asyncio
    async def test_service_method(self, new_service):
        result = await new_service.do_something()
        assert result is not None
```

### API Tests

```python
@pytest.mark.integration
@pytest.mark.api
class TestNewEndpoint:
    def test_endpoint(self, api_client):
        response = api_client.get("/api/v1/new-endpoint")
        assert response.status_code == 200
```

## Test Coverage Goals

Target coverage metrics:
- **Overall**: > 80%
- **Services**: > 90%
- **Datasources**: > 75%
- **API Endpoints**: > 85%

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
