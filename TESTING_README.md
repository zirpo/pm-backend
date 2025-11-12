# Testing Guide

This document provides comprehensive information about the testing infrastructure for the AI-Assisted Project State API.

## 📋 Test Suite Overview

Our test suite consists of **301 tests** covering all aspects of the application:

### Test Categories

1. **Unit Tests** (95 tests)
   - **Schemas** (`test_schemas.py`) - 40+ tests for Pydantic models
   - **Gemini Service** (`test_gemini_service.py`) - 25+ tests for file operations
   - **Gemini RAG Service** (`test_gemini_rag_service.py`) - 25+ tests for RAG functionality
   - **LLM Agents** (`test_llm_agents.py`) - 14 tests for agent logic

2. **Integration Tests** (206 tests)
   - **Authentication** - 7 tests for API key validation
   - **Core Endpoints** - 20+ tests for CRUD operations
   - **Document Endpoints** - 16+ tests for file upload/management
   - **Control Group Endpoints** - 12+ tests for update/recommend
   - **Experimental RAG Endpoints** - 10+ tests for RAG features
   - **API Integration** - 40+ tests for full API workflows
   - **Performance & Stress** - 6 tests for load testing

## 🚀 Quick Start

### Running All Tests
```bash
# Run complete test suite with coverage
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# Run specific test categories
pytest tests/test_schemas.py -v                    # Unit tests only
pytest tests/test_main.py::TestAuthentication -v  # Authentication tests
pytest tests/test_main.py::TestPerformanceAndStress -v  # Performance tests
```

### Running Tests by Category
```bash
# Unit tests
pytest tests/test_schemas.py tests/test_gemini_service.py tests/test_gemini_rag_service.py -v

# Integration tests
pytest tests/test_main.py -v

# Performance tests
pytest tests/test_main.py::TestPerformanceAndStress -v

# With coverage reporting
pytest tests/ --cov=. --cov-report=html --cov-fail-under=80
```

## 📊 Test Coverage

- **Target Coverage**: 80% minimum
- **Current Coverage**: See coverage report in `htmlcov/index.html`
- **Coverage Reports**: Generated in `coverage.xml` and `htmlcov/`

## 🔧 Test Configuration

### Environment Setup
Tests use `.env.test` configuration:
```env
TEST_ENV=test
DATABASE_URL=sqlite:///./test.db
SUPER_SECRET_API_KEY=test-api-key-for-testing-only
GEMINI_API_KEY=test-gemini-key-for-testing
DEEPSEEK_API_KEY=test-deepseek-key-for-testing
```

### Test Database
- **SQLite**: Used for unit tests (fast, lightweight)
- **PostgreSQL**: Used for integration tests (production-like)
- **Automatic Setup**: Database and tables created automatically

### Configuration Files
- `pytest.ini` - Pytest configuration with coverage settings
- `tests/test_config.py` - Shared test configuration and mocks

## 🏗️ Test Architecture

### Mocking Strategy
- **Unit Tests**: Full mocking of external services (Gemini API, database)
- **Integration Tests**: Real database, mocked external APIs
- **Performance Tests**: Measured with mocked services for consistency

### Test Fixtures
```python
# Example test structure
def test_example_endpoint():
    """Test example endpoint with proper authentication"""
    headers = {"X-API-Key": "test-api-key-for-testing-only"}
    response = client.get("/endpoint", headers=headers)
    assert response.status_code == 200
```

### Database Testing
```python
# Async database testing
@pytest.mark.asyncio
async def test_database_operation():
    async with TestSessionLocal() as session:
        # Test database operations
        result = await some_database_function(session)
        assert result is not None
```

## 🎯 CI/CD Pipeline

### GitHub Actions Workflows

#### 1. Main Pipeline (`.github/workflows/ci-cd.yml`)
- **Code Quality**: Black, isort, flake8, mypy
- **Security**: Bandit, safety scans
- **Testing**: Multi-Python version testing (3.11, 3.12)
- **Integration**: PostgreSQL integration tests
- **Performance**: Load testing with Locust
- **Documentation**: Auto-generated API docs

#### 2. Coverage Pipeline (`.github/workflows/coverage.yml`)
- **Coverage Reporting**: Detailed coverage analysis
- **Codecov Integration**: Coverage tracking and PR comments
- **Coverage Badges**: Auto-generated badges

### Pipeline Triggers
- **Push**: Runs on `main` and `develop` branches
- **Pull Request**: Runs on PRs to `main`
- **Performance**: Only on `main` branch pushes

## 🔍 Test Categories Explained

### Unit Tests
**Purpose**: Test individual functions and classes in isolation

**Examples**:
```python
# Schema validation
def test_project_plan_validation():
    plan = ProjectPlan(name="Test", tasks=[])
    assert plan.name == "Test"

# Service function mocking
@patch('gemini_service.upload_file_to_gemini')
def test_upload_success(mock_upload):
    mock_upload.return_value = "files/test"
    result = upload_file_to_gemini(b"content", "test.txt")
    assert result == "files/test"
```

### Integration Tests
**Purpose**: Test interaction between components

**Examples**:
```python
# API endpoint testing
def test_create_project_endpoint():
    response = client.post("/project/create",
                          json={"name": "Test Project"},
                          headers=headers)
    assert response.status_code == 201
    assert "id" in response.json()

# Workflow testing
def test_document_upload_workflow():
    # Create project
    # Upload document
    # Verify document appears in list
    # Delete document
    # Verify document removed
```

### Performance Tests
**Purpose**: Ensure system performs under load

**Examples**:
```python
def test_concurrent_requests():
    # Test 5 concurrent project creation requests
    # Verify all succeed within time limit

def test_large_file_upload():
    # Test upload performance with 1MB files
    # Verify completion within acceptable time
```

## 🐛 Debugging Tests

### Running Tests in Debug Mode
```bash
# Run with verbose output
pytest tests/ -v -s

# Run specific test with debugging
pytest tests/test_main.py::TestClass::test_method -v -s --tb=long

# Stop on first failure
pytest tests/ -x

# Run only failed tests
pytest tests/ --lf
```

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Clean test database
   rm test.db
   pytest tests/ -v
   ```

2. **Import Errors**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Mocking Issues**
   ```python
   # Ensure proper patching
   with patch('module.function') as mock_func:
       mock_func.return_value = expected_value
   ```

## 📈 Performance Benchmarks

### Current Benchmarks
- **Project Creation**: <200ms average
- **Document Upload**: <1s for 1MB files
- **RAG Recommendations**: <5s average
- **Concurrent Requests**: 10 req/s sustained

### Performance Test Results
Results are stored in `performance-results/` after CI/CD runs.

## 🔐 Security Testing

### Automated Security Scans
- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability scanner
- **Results**: Stored in `security-reports/` artifacts

### Security Test Coverage
- SQL injection prevention
- Authentication bypass attempts
- File upload validation
- API rate limiting

## 📚 Test Documentation

### Inline Documentation
- All tests include docstrings explaining purpose
- Complex test scenarios have detailed comments
- Edge cases are explicitly documented

### Generated Documentation
- **API Documentation**: Auto-generated from OpenAPI spec
- **Coverage Reports**: Interactive HTML reports
- **Test Results**: Artifacts stored in CI/CD

## 🎉 Best Practices

### Test Writing Guidelines
1. **Descriptive Names**: Test names should clearly state what's being tested
2. **AAA Pattern**: Arrange, Act, Assert structure
3. **One Assertion**: Prefer one assertion per test when possible
4. **Test Isolation**: Tests should not depend on each other
5. **Mock External Services**: Avoid real network calls in tests

### Example Good Test
```python
def test_project_create_rejects_empty_name():
    """Test that project creation rejects empty project names"""
    headers = {"X-API-Key": "test-api-key-for-testing-only"}
    project_data = {"name": ""}  # Empty name

    response = client.post("/project/create", json=project_data, headers=headers)

    assert response.status_code == 422  # Validation error
    assert "name" in response.json()["detail"][0]["loc"]
```

## 🚦 CI/CD Status Badges

[![Tests](https://github.com/your-repo/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/your-repo/actions)
[![Coverage](https://codecov.io/gh/your-repo/branch/main/graph/badge.svg)](https://codecov.io/gh/your-repo)
[![Security](https://github.com/your-repo/workflows/Security%20Scan/badge.svg)](https://github.com/your-repo/actions)

## 📞 Support

For testing questions or issues:
1. Check existing test files for examples
2. Review CI/CD pipeline logs for detailed error information
3. Consult this documentation for common solutions
4. Run tests locally with debug flags for detailed output