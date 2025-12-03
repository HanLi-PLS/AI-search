# Testing Guide for AI-Search Stock Tracker

## Overview

This document describes the testing infrastructure for the AI-Search public company tracker. The test suite includes unit tests for individual components and integration tests for API endpoints.

## Test Structure

```
backend/tests/
├── conftest.py                 # Shared fixtures and pytest configuration
├── unit/                       # Unit tests (no external dependencies)
│   ├── test_stock_data_service.py
│   ├── test_athena_ipo_service.py
│   └── test_news_analysis_service.py
└── integration/               # Integration tests (API endpoints)
    ├── test_stock_routes.py
    └── test_watchlist_routes.py
```

## Prerequisites

### Install Test Dependencies

```bash
cd backend
pip install -r requirements.txt

# Ensure pytest and related packages are installed
pip install pytest pytest-asyncio pytest-mock pytest-cov
```

### Environment Setup

Create a `.env.test` file or set test environment variables:

```bash
export TESTING=true
export TUSHARE_API_TOKEN=your-test-token
export FINNHUB_API_KEY=your-test-key
export OPENAI_API_KEY=your-test-key
```

## Running Tests

### Run All Tests

```bash
# From project root
pytest

# Or from backend directory
cd backend && pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Tests for specific service
pytest -m stock_data
pytest -m athena
pytest -m news

# API endpoint tests
pytest -m api
```

### Run Specific Test Files

```bash
# Run stock data service tests
pytest backend/tests/unit/test_stock_data_service.py

# Run Athena IPO service tests
pytest backend/tests/unit/test_athena_ipo_service.py

# Run news analysis service tests
pytest backend/tests/unit/test_news_analysis_service.py

# Run stock routes tests
pytest backend/tests/integration/test_stock_routes.py

# Run watchlist routes tests
pytest backend/tests/integration/test_watchlist_routes.py
```

### Run Specific Test Functions

```bash
# Run a single test
pytest backend/tests/unit/test_stock_data_service.py::TestStockDataService::test_init

# Run tests matching a pattern
pytest -k "test_get_latest_date"
```

### Verbose Output

```bash
# Show detailed test output
pytest -v

# Show print statements
pytest -s

# Show detailed failure information
pytest -vv
```

### Exclude Slow Tests

```bash
# Skip slow tests
pytest -m "not slow"
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests that don't require external dependencies
- `@pytest.mark.integration` - Integration tests that may require DB, API keys
- `@pytest.mark.slow` - Tests that take more than 1 second
- `@pytest.mark.stock_data` - Tests for stock data service
- `@pytest.mark.athena` - Tests for Athena IPO service
- `@pytest.mark.news` - Tests for news analysis service
- `@pytest.mark.api` - Tests for API endpoints

## Test Coverage

### Generate Coverage Report

```bash
# Run tests with coverage
pytest --cov=backend/app --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Requirements

- **Overall Coverage**: Aim for 80%+ coverage
- **Critical Services**: 90%+ coverage (stock_data, athena_ipo, news_analysis)
- **API Routes**: 70%+ coverage

## Test Fixtures

### Available Fixtures (from conftest.py)

```python
# Mock data fixtures
- mock_stock_data: Standard stock data
- mock_big_mover_stock: Stock with ≥10% move
- mock_historical_data: Historical price data
- mock_ipo_data: IPO data from Athena
- mock_watchlist_items: Watchlist items

# Mock service fixtures
- mock_tushare_response: Mocked Tushare API response
- mock_athena_client: Mocked boto3 Athena client
- mock_db_session: Mocked SQLAlchemy session
- mock_openai_response: Mocked OpenAI API response
```

### Using Fixtures in Tests

```python
def test_example(mock_stock_data, mock_db_session):
    """Test using fixtures"""
    # Use mock_stock_data and mock_db_session in your test
    pass
```

## Writing New Tests

### Unit Test Template

```python
"""
Unit tests for YourService
"""
import pytest
from unittest.mock import Mock, patch
from backend.app.services.your_service import YourService


@pytest.mark.unit
class TestYourService:
    """Test suite for YourService"""

    def test_your_function(self):
        """Test description"""
        service = YourService()
        result = service.your_function()
        assert result is not None
```

### Integration Test Template

```python
"""
Integration tests for Your API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.integration
@pytest.mark.api
class TestYourRoutes:
    """Test suite for your API routes"""

    def test_endpoint(self, client):
        """Test endpoint description"""
        response = client.get('/api/your-endpoint')
        assert response.status_code == 200
```

## Continuous Integration

### GitHub Actions (Example)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        run: pytest
        env:
          TESTING: true
```

## Mocking External Services

### Mocking Tushare

```python
@patch('backend.app.services.stock_data.ts')
def test_with_tushare(mock_ts):
    mock_pro = Mock()
    mock_ts.pro_api.return_value = mock_pro
    # Your test code
```

### Mocking AWS Athena

```python
@patch('backend.app.services.athena_ipo.boto3')
def test_with_athena(mock_boto3):
    mock_client = Mock()
    mock_boto3.client.return_value = mock_client
    # Your test code
```

### Mocking OpenAI

```python
@patch('backend.app.services.stock_news_analysis.OpenAI')
def test_with_openai(mock_openai):
    mock_completion = Mock()
    mock_openai.return_value.chat.completions.create.return_value = mock_completion
    # Your test code
```

## Debugging Tests

### Run with PDB

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb
```

### Show Warnings

```bash
# Show all warnings
pytest -W all

# Show specific warning categories
pytest -W error::DeprecationWarning
```

### Verbose Logging

```python
# In your test
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Common Issues

### Issue: Import Errors

**Solution**: Ensure PYTHONPATH is set correctly

```bash
export PYTHONPATH=/path/to/AI-search:$PYTHONPATH
```

### Issue: Database Connection Errors

**Solution**: Tests should use mocked database sessions, not real connections. Check that `mock_db_session` fixture is being used.

### Issue: API Key Required

**Solution**: Set test environment variables or use mocked services

```bash
export TESTING=true  # Disables real API calls
```

### Issue: Slow Tests

**Solution**: Mark slow tests and skip them during development

```python
@pytest.mark.slow
def test_slow_operation():
    pass

# Run without slow tests
pytest -m "not slow"
```

## Test Data

### Creating Test Data

Test data should be:
- **Minimal**: Only include fields needed for the test
- **Realistic**: Use realistic values (e.g., actual ticker formats)
- **Deterministic**: Same input = same output
- **Isolated**: Each test should be independent

### Example Test Data

```python
mock_stock_data = {
    'ticker': '1801.HK',
    'name': 'BeiGene',
    'current_price': 100.50,
    'change_percent': 5.79
}
```

## Performance Testing

### Marking Slow Tests

```python
@pytest.mark.slow
def test_large_dataset():
    # Test with large dataset
    pass
```

### Measuring Test Performance

```bash
# Show slowest tests
pytest --durations=10

# Show all test durations
pytest --durations=0
```

## Best Practices

1. **Test Independence**: Each test should run independently
2. **Mock External Services**: Don't make real API calls in tests
3. **Clear Test Names**: Use descriptive test function names
4. **Arrange-Act-Assert**: Follow AAA pattern in test structure
5. **One Assertion Per Test**: Focus each test on one behavior
6. **Use Fixtures**: Reuse common test setup via fixtures
7. **Test Edge Cases**: Include tests for error conditions
8. **Keep Tests Fast**: Unit tests should run in milliseconds

## Example Test Session

```bash
# 1. Run quick smoke test
pytest -m "unit and not slow" --maxfail=1

# 2. Run full unit test suite
pytest -m unit -v

# 3. Run integration tests (requires backend running)
pytest -m integration -v

# 4. Generate coverage report
pytest --cov=backend/app --cov-report=html

# 5. View coverage
open htmlcov/index.html
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

## Maintenance

### Updating Tests

When adding new features:
1. Write tests first (TDD approach recommended)
2. Run tests to verify they fail
3. Implement feature
4. Run tests to verify they pass
5. Update test documentation

### Reviewing Test Coverage

```bash
# Monthly coverage check
pytest --cov=backend/app --cov-report=term-missing

# Identify untested code
# Look for files with <80% coverage
```

## Support

For questions or issues with tests:
1. Check this documentation
2. Review existing tests for examples
3. Check pytest documentation
4. Review test output and error messages
