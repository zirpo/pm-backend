"""
Test configuration and environment setup for comprehensive testing.

This module provides configuration for different test environments,
including SQLite for unit tests and PostgreSQL for integration tests.
"""

import os
import tempfile
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TestConfig:
    """Configuration class for test environments."""

    # Test environment types
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"

    def __init__(self, env_type: str = SQLITE):
        self.env_type = env_type
        self._setup_database_urls()
        self._setup_test_data()

    def _setup_database_urls(self):
        """Setup database URLs based on environment type."""
        if self.env_type == self.SQLITE:
            # Use temporary SQLite database for fast unit tests
            self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            self.database_url = f"sqlite:///{self.temp_db.name}"
            self.async_database_url = f"sqlite+aiosqlite:///{self.temp_db.name}"
        elif self.env_type == self.POSTGRESQL:
            # Use PostgreSQL for integration tests
            self.database_url = os.getenv(
                "TEST_DATABASE_URL",
                "postgresql+asyncpg://test_user:test_pass@localhost:5432/pm_test"
            )
            self.async_database_url = self.database_url
        else:
            raise ValueError(f"Unknown test environment type: {self.env_type}")

    def _setup_test_data(self):
        """Setup test data configuration."""
        self.test_api_key = "test-api-key-for-testing-only"
        self.test_gemini_api_key = os.getenv("GEMINI_API_KEY", "test-gemini-key")

        # Sample project data
        self.sample_project_data = {
            "name": "Test Project",
            "plan_json": {
                "tasks": [
                    {"id": 1, "name": "Design API", "status": "todo"},
                    {"id": 2, "name": "Implement Backend", "status": "todo"}
                ],
                "risks": ["Budget constraints"],
                "milestones": [
                    {"id": 1, "name": "MVP Release", "completed": False}
                ]
            }
        }

        # Sample document content
        self.sample_document_content = b"This is a test document for file upload testing."
        self.sample_document_name = "test_document.txt"

    def create_sync_engine(self):
        """Create synchronous database engine."""
        if self.env_type == self.SQLITE:
            return create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                echo=False
            )
        else:
            return create_engine(self.database_url, echo=False)

    def create_async_engine(self):
        """Create asynchronous database engine."""
        return create_async_engine(self.async_database_url, echo=False)

    def create_session_factory(self, engine):
        """Create session factory."""
        return sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            class_=AsyncSession if self.env_type == self.POSTGRESQL else None
        )

    def cleanup(self):
        """Cleanup test resources."""
        if hasattr(self, 'temp_db'):
            try:
                os.unlink(self.temp_db.name)
            except FileNotFoundError:
                pass


# Test configuration instances
UNIT_TEST_CONFIG = TestConfig(TestConfig.SQLITE)
INTEGRATION_TEST_CONFIG = TestConfig(TestConfig.POSTGRESQL)

# Test environment detection
def get_test_config() -> TestConfig:
    """Get appropriate test configuration based on environment."""
    test_env = os.getenv("TEST_ENV", "sqlite").lower()
    if test_env == "postgresql":
        return INTEGRATION_TEST_CONFIG
    else:
        return UNIT_TEST_CONFIG


# Mock configuration for LLM tests
class MockConfig:
    """Configuration for mock LLM responses."""

    # Mock responses for consistent testing
    MOCK_LLM_UPDATE_RESPONSE = {
        "tasks": [
            {"id": 1, "name": "Test Task from LLM", "status": "todo"}
        ],
        "risks": [],
        "milestones": []
    }

    MOCK_LLM_RECOMMENDATION = """# Project Analysis

## Current Status
Based on your project plan, you have 1 task in progress.

## Recommendations
1. Focus on completing the current task
2. Consider adding more specific milestones
3. Review and update risk assessments regularly

## Next Steps
- Prioritize high-impact tasks
- Set clear completion criteria
- Monitor progress closely"""

    MOCK_GEMINI_FILE_ID = "files/test_file_12345"
    MOCK_GEMINI_RESPONSE = "This is a mock response from Gemini for testing purposes."


# Performance test configuration
class PerformanceConfig:
    """Configuration for performance and stress tests."""

    # Concurrent request settings
    CONCURRENT_REQUESTS = 100
    CONCURRENT_UPLOADS = 10

    # File sizes for upload testing
    SMALL_FILE_SIZE = 1024 * 1024  # 1MB
    MEDIUM_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    LARGE_FILE_SIZE = 100 * 1024 * 1024  # 100MB

    # Response time thresholds (in milliseconds)
    API_RESPONSE_THRESHOLD = 1000  # 1 second
    UPLOAD_RESPONSE_THRESHOLD = 5000  # 5 seconds
    RAG_RESPONSE_THRESHOLD = 10000  # 10 seconds

    # Memory usage thresholds (in MB)
    MEMORY_USAGE_THRESHOLD = 512


# Environment validation
def validate_test_environment():
    """Validate that the test environment is properly configured."""
    errors = []

    # Check required environment variables
    required_vars = ["SUPER_SECRET_API_KEY"]
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")

    # Check optional but recommended variables
    recommended_vars = ["GEMINI_API_KEY", "TEST_DATABASE_URL"]
    for var in recommended_vars:
        if not os.getenv(var):
            print(f"Warning: Recommended environment variable not set: {var}")

    if errors:
        raise ValueError(f"Test environment validation failed: {errors}")

    return True


# Test data generators
def generate_test_project(name: str = None, task_count: int = 3) -> dict:
    """Generate test project data."""
    if name is None:
        name = f"Test Project {id(name)}"

    tasks = []
    for i in range(task_count):
        tasks.append({
            "id": i + 1,
            "name": f"Task {i + 1}",
            "status": "todo" if i > 0 else "in_progress"
        })

    return {
        "name": name,
        "plan_json": {
            "tasks": tasks,
            "risks": [f"Risk {i+1}" for i in range(2)],
            "milestones": [{"id": 1, "name": "MVP Release", "completed": False}]
        }
    }


def generate_test_document(size: int = 1024) -> tuple[bytes, str]:
    """Generate test document content."""
    content = b"A" * size
    filename = f"test_document_{size}.txt"
    return content, filename