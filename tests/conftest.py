"""
Pytest configuration and shared fixtures for testing.

This module provides common test fixtures for database sessions, test clients,
and sample data that can be reused across all test modules.
"""

import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from main import app
from database import Base, get_db
import models


# Use a file-based SQLite database for easier debugging and inspection
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def session():
    """Create a test database session with clean tables for each test session."""
    # Create test database engine
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False  # Set to True to see SQL queries in test output
    )

    # Create session factory
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session and yield to test
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        # Clean up database after tests
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(session):
    """Create a FastAPI TestClient with test database session dependency override."""
    def override_get_db():
        """Override the database dependency for testing."""
        yield session

    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create and yield test client
    with TestClient(app) as test_client:
        yield test_client

    # Clean up dependency override
    app.dependency_overrides.clear()


@pytest.fixture
def sample_project(session):
    """Create a sample project in the test database for testing."""
    project = models.Project(
        name="Test Project",
        plan_json='{"tasks": [], "risks": [], "milestones": []}'
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.fixture
def sample_project_with_tasks(session):
    """Create a sample project with existing tasks for testing update operations."""
    project = models.Project(
        name="Test Project with Tasks",
        plan_json='{"tasks": [{"id": 1, "name": "Existing Task", "status": "todo"}], "risks": [], "milestones": []}'
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.fixture
def multiple_projects(session):
    """Create multiple sample projects for testing list operations."""
    projects = []
    project_names = ["Project Alpha", "Project Beta", "Project Gamma"]

    for name in project_names:
        project = models.Project(
            name=name,
            plan_json='{"tasks": [], "risks": [], "milestones": []}'
        )
        session.add(project)
        projects.append(project)

    session.commit()

    # Refresh all projects to get their IDs
    for project in projects:
        session.refresh(project)

    return projects


@pytest.fixture
def complex_project(session):
    """Create a complex project with tasks, risks, and milestones for comprehensive testing."""
    plan_json = '''{
        "tasks": [
            {"id": 1, "name": "Design API", "status": "done"},
            {"id": 2, "name": "Implement Backend", "status": "todo"},
            {"id": 3, "name": "Create Frontend", "status": "todo"}
        ],
        "risks": [
            "Budget overrun",
            "Technical complexity",
            "Timeline constraints"
        ],
        "milestones": [
            {"id": 1, "name": "MVP Release", "completed": false},
            {"id": 2, "name": "Beta Launch", "completed": false}
        ]
    }'''

    project = models.Project(
        name="Complex Test Project",
        plan_json=plan_json.strip()
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


# Mock LLM responses for consistent testing
@pytest.fixture
def mock_llm_state_update_response():
    """Mock response for state updater LLM calls."""
    return {
        "tasks": [
            {"id": 1, "name": "Test Task from LLM", "status": "todo"}
        ],
        "risks": [],
        "milestones": []
    }


@pytest.fixture
def mock_llm_recommendation_response():
    """Mock response for recommender LLM calls."""
    return """# Project Analysis

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


@pytest.fixture
def mock_llm_json_update_response():
    """Mock JSON response for LLM state updates."""
    return '{"tasks": [{"id": 1, "name": "Updated Task", "status": "todo"}], "risks": [], "milestones": []}'


# Test configuration markers
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for API endpoints"
    )
    config.addinivalue_line(
        "markers", "llm: Tests involving LLM interactions"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer to execute"
    )
    config.addinivalue_line(
        "markers", "real_llm: Tests that make actual API calls to LLM services"
    )


# Environment configuration for tests
@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure environment variables for testing."""
    # Set test API key for LLM tests (can be overridden)
    os.environ["DEEPSEEK_API_KEY"] = "test_key_for_testing_only"

    # Disable any logging that might interfere with test output
    import logging
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)