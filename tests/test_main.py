"""
Integration tests for main FastAPI application endpoints
"""
import pytest
import json
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import get_db, Base
import models


# Create a test database for isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_test_database():
    """Set up test database before each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self):
        """Test that health endpoint returns ok status"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCreateProjectEndpoint:
    """Test POST /project/create endpoint"""

    def test_create_project_valid(self):
        """Test creating a project with valid data"""
        project_data = {"name": "Test Project"}
        response = client.post("/project/create", json=project_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert "id" in data
        assert "plan_json" in data
        assert data["plan_json"] == {"tasks": [], "risks": [], "milestones": []}

    def test_create_project_invalid_empty_name(self):
        """Test creating a project with empty name"""
        project_data = {"name": ""}
        response = client.post("/project/create", json=project_data)

        assert response.status_code == 422  # Validation error

    def test_create_project_invalid_too_long_name(self):
        """Test creating a project with name too long"""
        project_data = {"name": "x" * 256}  # 256 characters
        response = client.post("/project/create", json=project_data)

        assert response.status_code == 422  # Validation error

    def test_create_project_missing_name(self):
        """Test creating a project without name field"""
        project_data = {}
        response = client.post("/project/create", json=project_data)

        assert response.status_code == 422  # Validation error


class TestGetProjectEndpoint:
    """Test GET /project/{project_id} endpoint"""

    def test_get_existing_project(self):
        """Test getting an existing project"""
        # First create a project
        project_data = {"name": "Test Project"}
        create_response = client.post("/project/create", json=project_data)
        project_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/project/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Test Project"
        assert "plan_json" in data
        assert isinstance(data["plan_json"], dict)

    def test_get_nonexistent_project(self):
        """Test getting a non-existent project"""
        response = client.get("/project/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"

    def test_get_project_with_database_stored_json(self):
        """Test that plan_json is stored as JSON string in database"""
        # Create a project
        project_data = {"name": "Test Project"}
        create_response = client.post("/project/create", json=project_data)
        project_id = create_response.json()["id"]

        # Check database directly
        db = TestingSessionLocal()
        db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
        assert db_project is not None
        assert isinstance(db_project.plan_json, str)  # Should be stored as string
        assert json.loads(db_project.plan_json) == {"tasks": [], "risks": [], "milestones": []}
        db.close()


class TestListProjectsEndpoint:
    """Test GET /projects/ endpoint"""

    def test_list_empty_projects(self):
        """Test listing projects when none exist"""
        response = client.get("/projects/")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_multiple_projects(self):
        """Test listing multiple projects"""
        # Create multiple projects
        projects = [
            {"name": "First Project"},
            {"name": "Second Project"},
            {"name": "Third Project"}
        ]

        created_projects = []
        for project_data in projects:
            response = client.post("/project/create", json=project_data)
            created_projects.append(response.json())

        # List all projects
        response = client.get("/projects/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Check that only id and name are included (no plan_json)
        for project in data:
            assert "id" in project
            assert "name" in project
            assert "plan_json" not in project

    def test_list_projects_returns_correct_structure(self):
        """Test that list endpoint returns correct ProjectList structure"""
        # Create a project
        project_data = {"name": "Test Project"}
        client.post("/project/create", json=project_data)

        # List projects
        response = client.get("/projects/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        project = data[0]
        assert set(project.keys()) == {"id", "name"}  # Only these fields should be present
        assert isinstance(project["id"], int)
        assert isinstance(project["name"], str)


class TestEndToEndWorkflow:
    """Test complete workflow scenarios"""

    def test_complete_crud_workflow(self):
        """Test complete Create -> Read -> List workflow"""
        # 1. Create project
        project_data = {"name": "Complete Test Project"}
        create_response = client.post("/project/create", json=project_data)
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # 2. Get individual project
        get_response = client.get(f"/project/{project_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Complete Test Project"

        # 3. List all projects (should include our new project)
        list_response = client.get("/projects/")
        assert list_response.status_code == 200
        projects = list_response.json()
        assert len(projects) >= 1
        assert any(p["id"] == project_id for p in projects)

    def test_multiple_projects_workflow(self):
        """Test workflow with multiple projects"""
        # Create several projects
        project_names = ["Alpha", "Beta", "Gamma"]
        created_ids = []

        for name in project_names:
            response = client.post("/project/create", json={"name": name})
            created_ids.append(response.json()["id"])

        # Verify all can be retrieved individually
        for i, project_id in enumerate(created_ids):
            response = client.get(f"/project/{project_id}")
            assert response.status_code == 200
            assert response.json()["name"] == project_names[i]

        # Verify all appear in list
        response = client.get("/projects/")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) >= len(project_names)

        # Check our projects are in the list
        returned_names = {p["name"] for p in projects}
        for name in project_names:
            assert name in returned_names

    def test_error_handling_workflow(self):
        """Test error handling throughout workflow"""
        # Try to get non-existent project
        response = client.get("/project/99999")
        assert response.status_code == 404

        # Try to create project with invalid data
        response = client.post("/project/create", json={"name": ""})
        assert response.status_code == 422

        # Create valid project and try invalid operations
        create_response = client.post("/project/create", json={"name": "Valid Project"})
        project_id = create_response.json()["id"]

        # Try to get with wrong type (FastAPI should handle this gracefully)
        response = client.get("/project/invalid")
        # This might return 422 or 404 depending on FastAPI validation
        assert response.status_code in [422, 404]


class TestRecommendEndpoint:
    """Test POST /project/recommend endpoint"""

    def test_recommend_existing_project(self):
        """Test recommending for an existing project"""
        # First create a project
        project_data = {"name": "Test Project"}
        create_response = client.post("/project/create", json=project_data)
        project_id = create_response.json()["id"]

        # Then get recommendation
        recommend_data = {"project_id": project_id, "user_question": "What are the next steps?"}
        response = client.post("/project/recommend", json=recommend_data)

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        assert "recommendation_markdown" in data
        assert isinstance(data["recommendation_markdown"], str)

    def test_recommend_nonexistent_project(self):
        """Test recommending for a non-existent project"""
        recommend_data = {"project_id": 99999, "user_question": "What are the next steps?"}
        response = client.post("/project/recommend", json=recommend_data)

        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"

    def test_recommend_with_project_having_tasks(self):
        """Test recommending for a project with existing tasks"""
        # Create a project
        project_data = {"name": "Test Project"}
        create_response = client.post("/project/create", json=project_data)
        project_id = create_response.json()["id"]

        # Add some tasks to the project
        update_data = {"project_id": project_id, "update_text": "add task Buy groceries"}
        client.post("/project/update", json=update_data)
        update_data = {"project_id": project_id, "update_text": "add task Clean house"}
        client.post("/project/update", json=update_data)

        # Get recommendation
        recommend_data = {"project_id": project_id, "user_question": "What are the next steps?"}
        response = client.post("/project/recommend", json=recommend_data)

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        assert "Buy groceries" in data["recommendation_markdown"]
        assert "Clean house" in data["recommendation_markdown"]

    def test_recommend_different_questions(self):
        """Test recommending with different types of questions"""
        # Create a project with tasks and risks
        project_data = {"name": "Test Project"}
        create_response = client.post("/project/create", json=project_data)
        project_id = create_response.json()["id"]

        # Add a task
        update_data = {"project_id": project_id, "update_text": "add task Complete project"}
        client.post("/project/update", json=update_data)

        # Test different question types
        questions = [
            "What are the next steps?",
            "What are the risks?",
            "How is the project going?"
        ]

        for question in questions:
            recommend_data = {"project_id": project_id, "user_question": question}
            response = client.post("/project/recommend", json=recommend_data)

            assert response.status_code == 200
            data = response.json()
            assert data["project_id"] == project_id
            assert "Project Analysis" in data["recommendation_markdown"]
            assert "mock recommendation" in data["recommendation_markdown"]

    def test_recommend_read_only_behavior(self):
        """Test that recommend endpoint doesn't modify the database"""
        # Create a project
        project_data = {"name": "Test Project"}
        create_response = client.post("/project/create", json=project_data)
        project_id = create_response.json()["id"]

        # Get initial project state
        initial_response = client.get(f"/project/{project_id}")
        initial_plan = initial_response.json()["plan_json"]

        # Call recommend endpoint multiple times
        recommend_data = {"project_id": project_id, "user_question": "What are the next steps?"}
        for _ in range(3):
            client.post("/project/recommend", json=recommend_data)

        # Verify project state hasn't changed
        final_response = client.get(f"/project/{project_id}")
        final_plan = final_response.json()["plan_json"]

        assert initial_plan == final_plan

    def test_recommend_invalid_project_id_zero(self):
        """Test recommending with project_id = 0"""
        recommend_data = {"project_id": 0, "user_question": "What are the next steps?"}
        response = client.post("/project/recommend", json=recommend_data)

        assert response.status_code == 422  # Validation error

    def test_recommend_invalid_project_id_negative(self):
        """Test recommending with negative project_id"""
        recommend_data = {"project_id": -1, "user_question": "What are the next steps?"}
        response = client.post("/project/recommend", json=recommend_data)

        assert response.status_code == 422  # Validation error

    def test_recommend_empty_question(self):
        """Test recommending with empty user_question"""
        recommend_data = {"project_id": 1, "user_question": ""}
        response = client.post("/project/recommend", json=recommend_data)

        assert response.status_code == 422  # Validation error

    def test_recommend_missing_fields(self):
        """Test recommending with missing required fields"""
        # Missing user_question
        response = client.post("/project/recommend", json={"project_id": 1})
        assert response.status_code == 422

        # Missing project_id
        response = client.post("/project/recommend", json={"user_question": "What's next?"})
        assert response.status_code == 422

        # Empty request
        response = client.post("/project/recommend", json={})
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__])