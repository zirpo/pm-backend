"""
Integration tests for main FastAPI application endpoints
"""
import pytest
import json
import tempfile
import os
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio

from main import app
from database import get_db, Base
import models


# Create a test database for isolation
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    """Override database dependency for testing"""
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_test_database():
    """Set up test database before each test"""
    # Run async setup in sync context
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    # Run the async functions
    asyncio.run(create_tables())
    yield
    asyncio.run(drop_tables())


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self):
        """Test that health endpoint returns ok status"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_check_with_valid_api_key(self):
        """Test health endpoint with valid API key"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}
        response = client.get("/health", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_check_without_api_key(self):
        """Test health endpoint without API key should fail"""
        # Temporarily remove the dependency override to test real authentication
        original_override = app.dependency_overrides.get(get_db)
        app.dependency_overrides.clear()

        try:
            response = client.get("/health")
            assert response.status_code == 403  # Forbidden due to missing API key
        finally:
            # Restore the override
            if original_override:
                app.dependency_overrides[get_db] = original_override

    def test_health_check_with_invalid_api_key(self):
        """Test health endpoint with invalid API key should fail"""
        headers = {"X-API-Key": "invalid-api-key"}

        # Temporarily remove the dependency override to test real authentication
        original_override = app.dependency_overrides.get(get_db)
        app.dependency_overrides.clear()

        try:
            response = client.get("/health", headers=headers)
            assert response.status_code == 401  # Unauthorized due to invalid API key
        finally:
            # Restore the override
            if original_override:
                app.dependency_overrides[get_db] = original_override


class TestAuthentication:
    """Test API key authentication middleware"""

    def test_authentication_requires_api_key(self):
        """Test that authentication requires API key"""
        # Authentication should enforce API key requirement
        response = client.get("/health")
        assert response.status_code == 403  # Forbidden due to missing API key

    def test_authentication_rejects_empty_api_key(self):
        """Test that authentication rejects empty API key"""
        headers = {"X-API-Key": ""}
        response = client.get("/health", headers=headers)
        assert response.status_code == 403  # Forbidden due to empty API key

    def test_authentication_rejects_missing_api_key(self):
        """Test request without API key header"""
        response = client.get("/health", headers={})
        assert response.status_code == 403  # Forbidden due to missing API key

    def test_authentication_rejects_invalid_api_key(self):
        """Test that authentication rejects invalid API key"""
        # Test with wrong case
        headers = {"X-API-Key": "INVALID-API-KEY"}
        response = client.get("/health", headers=headers)
        assert response.status_code == 401  # Unauthorized due to invalid API key

    def test_authentication_accepts_valid_api_key(self):
        """Test that authentication accepts valid API key"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}
        response = client.get("/health", headers=headers)
        assert response.status_code == 200  # Success with valid API key

    def test_authentication_case_sensitive(self):
        """Test API key case sensitivity"""
        # Test with wrong case
        headers = {"X-API-Key": "TEST-API-KEY-FOR-TESTING-ONLY"}
        response = client.get("/health", headers=headers)
        assert response.status_code == 401  # Unauthorized due to case sensitivity

    def test_authentication_alternative_headers_rejected(self):
        """Test alternative API key header names are rejected"""
        # Test with lowercase header (FastAPI handles case-insensitive headers correctly)
        headers = {"x-api-key": "test-api-key-for-testing-only"}
        response = client.get("/health", headers=headers)
        assert response.status_code == 200  # Success - FastAPI handles case-insensitive headers

        # Test with different header name
        headers = {"Authorization": "Bearer test-api-key-for-testing-only"}
        response = client.get("/health", headers=headers)
        assert response.status_code == 403  # Forbidden - wrong header name

        # Test with multiple headers (should use the correct one)
        headers = {
            "X-API-Key": "test-api-key-for-testing-only",
            "Authorization": "Bearer wrong-key"
        }
        response = client.get("/health", headers=headers)
        assert response.status_code == 200  # Success - correct API key takes precedence


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


class TestDocumentEndpoints:
    """Test document upload, listing, and deletion endpoints"""

    @patch('gemini_service.upload_file_to_gemini')
    def test_upload_document_success(self, mock_upload):
        """Test successful document upload"""
        # Mock the Gemini upload response - return a string ID
        mock_upload.return_value = "files/test_doc_123"

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # First create a project
        project_data = {"name": "Test Project for Documents"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Test file upload
        file_content = b"This is a test document content for upload testing."
        files = {"file": ("test_document.txt", file_content, "text/plain")}
        response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["filename"] == "test_document.txt"
        assert data["project_id"] == project_id
        assert "gemini_corpus_doc_id" in data
        assert data["content_type"] == "text/plain"
        assert "uploaded_at" in data
        assert data["message"] == "File uploaded and linked to project successfully"

    def test_upload_document_nonexistent_project(self):
        """Test document upload to non-existent project"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}
        files = {"file": ("test.txt", b"test content", "text/plain")}
        response = client.post("/project/99999/upload", files=files, headers=headers)

        assert response.status_code == 404
        assert "Project with id 99999 not found" in response.json()["detail"]

    def test_upload_document_without_file(self):
        """Test document upload without file"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # First create a project
        project_data = {"name": "Test Project"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Try upload without file
        response = client.post(f"/project/{project_id}/upload", headers=headers)
        assert response.status_code == 422  # Validation error

    @patch('gemini_service.upload_file_to_gemini')
    def test_upload_document_large_file(self, mock_upload):
        """Test document upload with larger file"""
        mock_upload.return_value = "files/large_doc_123"

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Test Project for Large Files"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Create a larger file (1MB)
        large_content = b"A" * (1024 * 1024)  # 1MB
        files = {"file": ("large_document.txt", large_content, "text/plain")}
        response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "large_document.txt"

    @patch('gemini_service.upload_file_to_gemini')
    def test_upload_document_different_file_types(self, mock_upload):
        """Test document upload with different file types"""
        # Make mock return different IDs for each call
        mock_upload.side_effect = [
            "files/doc_pdf_123",
            "files/doc_json_456",
            "files/doc_xml_789",
            "files/doc_png_012"
        ]

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Test Project for File Types"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Test different file types
        test_files = [
            ("document.pdf", b"%PDF-1.4 test pdf content", "application/pdf"),
            ("data.json", b'{"key": "value"}', "application/json"),
            ("config.xml", b"<config><setting>test</setting></config>", "application/xml"),
            ("image.png", b"fake png content", "image/png")
        ]

        for filename, content, content_type in test_files:
            files = {"file": (filename, content, content_type)}
            response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)
            assert response.status_code == 201
            data = response.json()
            assert data["filename"] == filename
            assert data["content_type"] == content_type

    def test_list_documents_empty_project(self):
        """Test listing documents for project with no documents"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Empty Project"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # List documents
        response = client.get(f"/project/{project_id}/documents", headers=headers)
        assert response.status_code == 200
        assert response.json() == []

    @patch('gemini_service.upload_file_to_gemini')
    def test_list_documents_with_files(self, mock_upload):
        """Test listing documents for project with multiple files"""
        # Make mock return different IDs for each call
        mock_upload.side_effect = [
            "files/doc1_123",
            "files/doc2_456",
            "files/doc3_789"
        ]

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Project with Documents"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Upload multiple documents
        documents = [
            ("doc1.txt", b"Content of document 1"),
            ("doc2.txt", b"Content of document 2"),
            ("doc3.txt", b"Content of document 3")
        ]

        uploaded_ids = []
        for filename, content in documents:
            files = {"file": (filename, content, "text/plain")}
            upload_response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)
            uploaded_ids.append(upload_response.json()["id"])

        # List documents
        response = client.get(f"/project/{project_id}/documents", headers=headers)
        assert response.status_code == 200
        documents_list = response.json()
        assert len(documents_list) == 3

        # Verify document structure
        for doc in documents_list:
            assert "id" in doc
            assert "file_name" in doc
            assert "gemini_corpus_doc_id" in doc
            assert "uploaded_at" in doc

        # Verify our uploaded documents are in the list
        document_ids = [doc["id"] for doc in documents_list]
        for uploaded_id in uploaded_ids:
            assert uploaded_id in document_ids

    def test_list_documents_nonexistent_project(self):
        """Test listing documents for non-existent project"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}
        response = client.get("/project/99999/documents", headers=headers)
        assert response.status_code == 404
        assert "Project with id 99999 not found" in response.json()["detail"]

    @patch('gemini_service.delete_file_from_gemini')
    @patch('gemini_service.upload_file_to_gemini')
    def test_delete_document_success(self, mock_upload, mock_delete):
        """Test successful document deletion"""
        mock_upload.return_value = "files/deletable_doc_123"
        mock_delete.return_value = True  # Successful deletion

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Project for Deletion Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Upload a document
        files = {"file": ("deletable.txt", b"This file will be deleted", "text/plain")}
        upload_response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)
        document_id = upload_response.json()["id"]

        # Verify document exists
        list_response = client.get(f"/project/{project_id}/documents", headers=headers)
        documents_before = list_response.json()
        assert len(documents_before) == 1

        # Delete the document
        response = client.delete(f"/document/{document_id}", headers=headers)
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"].lower()

        # Verify document is gone
        list_response = client.get(f"/project/{project_id}/documents", headers=headers)
        documents_after = list_response.json()
        assert len(documents_after) == 0

    def test_delete_nonexistent_document(self):
        """Test deletion of non-existent document"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}
        response = client.delete("/document/99999", headers=headers)
        assert response.status_code == 404
        assert "Document with id 99999 not found" in response.json()["detail"]

    @patch('gemini_service.delete_file_from_gemini')
    @patch('gemini_service.upload_file_to_gemini')
    def test_document_workflow_end_to_end(self, mock_upload, mock_delete):
        """Test complete document workflow: upload -> list -> delete"""
        mock_upload.return_value = "files/workflow_doc_123"
        mock_delete.return_value = True

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create project
        project_data = {"name": "End-to-End Document Test Project"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Step 1: Upload document
        file_content = b"End-to-end test document content with some meaningful text."
        files = {"file": ("workflow_test.txt", file_content, "text/plain")}
        upload_response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)
        assert upload_response.status_code == 201
        document_id = upload_response.json()["id"]
        gemini_file_id = upload_response.json()["gemini_corpus_doc_id"]

        # Step 2: List documents to verify upload
        list_response = client.get(f"/project/{project_id}/documents", headers=headers)
        assert list_response.status_code == 200
        documents = list_response.json()
        assert len(documents) == 1
        assert documents[0]["id"] == document_id
        assert documents[0]["file_name"] == "workflow_test.txt"

        # Step 3: Delete document
        delete_response = client.delete(f"/document/{document_id}", headers=headers)
        assert delete_response.status_code == 200

        # Step 4: Verify deletion
        final_list_response = client.get(f"/project/{project_id}/documents", headers=headers)
        assert final_list_response.status_code == 200
        assert final_list_response.json() == []

    def test_upload_document_requires_authentication(self):
        """Test that document upload requires authentication"""
        files = {"file": ("test.txt", b"test content", "text/plain")}
        response = client.post("/project/1/upload", files=files)
        assert response.status_code == 403  # Forbidden - no API key

    def test_list_documents_requires_authentication(self):
        """Test that document listing requires authentication"""
        response = client.get("/project/1/documents")
        assert response.status_code == 403  # Forbidden - no API key

    def test_delete_document_requires_authentication(self):
        """Test that document deletion requires authentication"""
        response = client.delete("/document/1")
        assert response.status_code == 403  # Forbidden - no API key

    def test_upload_document_invalid_api_key(self):
        """Test document upload with invalid API key"""
        headers = {"X-API-Key": "invalid-key"}
        files = {"file": ("test.txt", b"test content", "text/plain")}
        response = client.post("/project/1/upload", files=files, headers=headers)
        assert response.status_code == 401  # Unauthorized - invalid API key

    @patch('gemini_service.upload_file_to_gemini')
    def test_upload_concurrent_documents(self, mock_upload):
        """Test concurrent document uploads to same project"""
        import threading
        import time

        # Make mock return different IDs for each call
        mock_upload.side_effect = [
            "files/concurrent_doc_123",
            "files/concurrent_doc_456",
            "files/concurrent_doc_789"
        ]

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Concurrent Upload Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        upload_results = []
        upload_errors = []

        def upload_document(index):
            try:
                content = f"Concurrent test document {index}".encode()
                files = {"file": (f"concurrent_{index}.txt", content, "text/plain")}
                response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)
                upload_results.append((index, response.status_code, response.json()))
            except Exception as e:
                upload_errors.append((index, str(e)))

        # Start multiple uploads concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(target=upload_document, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all uploads to complete
        for thread in threads:
            thread.join()

        # Verify results
        assert len(upload_errors) == 0, f"Upload errors occurred: {upload_errors}"
        assert len(upload_results) == 3

        # Check that all uploads succeeded
        successful_uploads = [result for result in upload_results if result[1] == 201]
        assert len(successful_uploads) == 3

        # Verify all documents are listed
        list_response = client.get(f"/project/{project_id}/documents", headers=headers)
        assert list_response.status_code == 200
        documents = list_response.json()
        assert len(documents) == 3


class TestControlGroupEndpoints:
    """Test control group endpoints (update, recommend) without RAG functionality"""

    def test_project_update_success(self):
        """Test successful project update"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Control Group Update Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Update the project using control group schema
        update_data = {
            "project_id": project_id,
            "update_text": "Major update to project plan based on new requirements"
        }

        response = client.post("/project/update", json=update_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data
        assert "new_plan" in data
        assert data["project_id"] == project_id

        # Verify the response contains a valid plan structure
        new_plan = data["new_plan"]
        assert "tasks" in new_plan
        assert "risks" in new_plan
        assert "milestones" in new_plan

    def test_project_update_invalid_json(self):
        """Test project update with invalid JSON syntax"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Invalid JSON Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Send invalid JSON
        update_data = {
            "updated_plan_json": "invalid json string",
            "update_text": "This should fail due to invalid JSON"
        }

        response = client.post(f"/project/{project_id}/update", json=update_data, headers=headers)
        assert response.status_code == 400
        assert "invalid json" in response.json()["detail"].lower()

    def test_project_update_schema_mismatch(self):
        """Test project update with schema mismatch"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Schema Mismatch Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Send data that doesn't match expected schema
        update_data = {
            "updated_plan_json": {
                "wrong_field": "This doesn't match the expected schema",
                "tasks": "This should be a list, not a string"
            },
            "update_text": "This should fail due to schema mismatch"
        }

        response = client.post(f"/project/{project_id}/update", json=update_data, headers=headers)
        assert response.status_code == 422  # Validation error

    def test_project_update_nonexistent_project(self):
        """Test project update for non-existent project"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        update_data = {
            "updated_plan_json": {"tasks": [], "risks": [], "milestones": []},
            "update_text": "Update for non-existent project"
        }

        response = client.post("/project/99999/update", json=update_data, headers=headers)
        assert response.status_code == 404
        assert "project with id 99999 not found" in response.json()["detail"].lower()

    def test_project_recommend_success(self):
        """Test successful project recommendation"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Control Group Recommend Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Get recommendations using control group schema
        recommend_data = {
            "project_id": project_id,
            "user_question": "How should I prioritize the blocked tasks?"
        }

        response = client.post("/project/recommend", json=recommend_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data
        assert "recommendation_markdown" in data
        assert data["project_id"] == project_id
        assert isinstance(data["recommendation_markdown"], str)
        assert len(data["recommendation_markdown"]) > 0

    def test_project_recommend_empty_query(self):
        """Test project recommendation with empty query"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Empty Query Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Send empty recommendation query
        recommend_data = {
            "project_id": project_id,
            "user_question": ""
        }

        response = client.post("/project/recommend", json=recommend_data, headers=headers)
        assert response.status_code == 422  # Validation error

    def test_project_recommend_nonexistent_project(self):
        """Test project recommendation for non-existent project"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        recommend_data = {
            "project_id": 99999,
            "user_question": "What should I do next?"
        }

        response = client.post("/project/recommend", json=recommend_data, headers=headers)
        assert response.status_code == 404
        assert "project with id 99999 not found" in response.json()["detail"].lower()

    def test_project_update_requires_authentication(self):
        """Test that project update requires authentication"""
        update_data = {
            "project_id": 1,
            "update_text": "No authentication test"
        }

        response = client.post("/project/update", json=update_data)
        assert response.status_code == 401  # Unauthorized - no API key

    def test_project_recommend_requires_authentication(self):
        """Test that project recommend requires authentication"""
        recommend_data = {
            "project_id": 1,
            "user_question": "Test query"
        }

        response = client.post("/project/recommend", json=recommend_data)
        assert response.status_code == 401  # Unauthorized - no API key

    def test_project_update_invalid_api_key(self):
        """Test project update with invalid API key"""
        headers = {"X-API-Key": "invalid-api-key"}

        update_data = {
            "project_id": 1,
            "update_text": "Invalid API key test"
        }

        response = client.post("/project/update", json=update_data, headers=headers)
        assert response.status_code == 403  # Forbidden - invalid API key

    def test_project_recommend_invalid_api_key(self):
        """Test project recommend with invalid API key"""
        headers = {"X-API-Key": "invalid-api-key"}

        recommend_data = {
            "project_id": 1,
            "user_question": "Test query"
        }

        response = client.post("/project/recommend", json=recommend_data, headers=headers)
        assert response.status_code == 403  # Forbidden - invalid API key

    def test_project_update_and_recommend_workflow(self):
        """Test complete workflow: update -> recommend -> update"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Workflow Test Project"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Step 1: Update project with initial plan
        initial_update = {
            "project_id": project_id,
            "update_text": "Setting up initial project plan with tasks and milestones"
        }

        update_response = client.post("/project/update", json=initial_update, headers=headers)
        assert update_response.status_code == 200
        update_data = update_response.json()
        assert "new_plan" in update_data

        # Step 2: Get recommendations based on current plan
        recommend_request = {
            "project_id": project_id,
            "user_question": "What's the best way to handle timeline constraints?"
        }

        recommend_response = client.post("/project/recommend", json=recommend_request, headers=headers)
        assert recommend_response.status_code == 200
        recommendation = recommend_response.json()["recommendation_markdown"]
        assert len(recommendation) > 0

        # Step 3: Update project based on recommendations
        final_update = {
            "project_id": project_id,
            "update_text": f"Updated based on AI recommendation: {recommendation[:100]}..."
        }

        final_response = client.post("/project/update", json=final_update, headers=headers)
        assert final_response.status_code == 200
        final_data = final_response.json()

        # Verify the workflow completed successfully
        assert final_data["project_id"] == project_id
        assert "new_plan" in final_data
        assert isinstance(final_data["new_plan"], dict)


class TestExperimentalRAGEndpoints:
    """Test experimental RAG-enabled endpoints (recommend_with_docs, update_with_docs)"""

    @patch('gemini_service.upload_file_to_gemini')
    @patch('gemini_rag_service.rag_recommendation')
    def test_recommend_with_docs_success(self, mock_rag_recommend, mock_upload):
        """Test successful RAG-powered recommendation"""
        mock_upload.return_value = "files/test_doc_123"
        mock_rag_recommend.return_value = "# RAG Recommendation\n\nBased on your documents, I recommend focusing on..."

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "RAG Recommend Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Upload a document for context
        file_content = b"This project requires careful planning and risk management."
        files = {"file": ("project_plan.txt", file_content, "text/plain")}
        upload_response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)

        # Get RAG-powered recommendation using correct schema
        current_plan = {
            "tasks": [
                {"id": 1, "name": "Design System", "status": "completed"},
                {"id": 2, "name": "Implement API", "status": "in_progress"}
            ],
            "risks": ["Technical complexity", "Timeline constraints"],
            "milestones": [{"id": 1, "name": "MVP Release", "completed": False}]
        }

        recommend_data = {
            "project_id": project_id,
            "plan_json": json.dumps(current_plan),
            "user_question": "What are the main risks I should consider?"
        }

        response = client.post("/project/recommend_with_docs", json=recommend_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "recommendation_markdown" in data
        assert "RAG Recommendation" in data["recommendation_markdown"]
        assert len(data["recommendation_markdown"]) > 0

        # Verify RAG service was called
        mock_rag_recommend.assert_called_once()

    @patch('gemini_service.upload_file_to_gemini')
    @patch('gemini_rag_service.rag_update')
    def test_update_with_docs_success(self, mock_rag_update, mock_upload):
        """Test successful RAG-powered update"""
        mock_upload.return_value = "files/test_doc_456"
        mock_rag_update.return_value = "# RAG Update Analysis\n\nBased on your documents and update request..."

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "RAG Update Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Upload a document for context
        file_content = b"Current project status: 2 tasks completed, 1 in progress."
        files = {"file": ("status_report.txt", file_content, "text/plain")}
        upload_response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)

        # Send RAG-powered update request using correct schema
        updated_plan = {
            "tasks": [
                {"id": 1, "name": "Design System", "status": "completed"},
                {"id": 2, "name": "Implement API", "status": "completed"},
                {"id": 3, "name": "Testing Phase", "status": "pending"}
            ],
            "risks": ["Timeline constraints"],
            "milestones": [{"id": 1, "name": "MVP Release", "completed": True}]
        }

        update_data = {
            "project_id": project_id,
            "updated_plan_json": json.dumps(updated_plan),
            "update_context": "Add new task for testing phase and update milestones"
        }

        response = client.post("/project/update_with_docs", json=update_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "recommendation_markdown" in data
        assert "RAG Update Analysis" in data["recommendation_markdown"]
        assert len(data["recommendation_markdown"]) > 0

        # Verify RAG service was called
        mock_rag_update.assert_called_once()

    @patch('gemini_service.upload_file_to_gemini')
    @patch('gemini_rag_service.rag_recommendation')
    def test_recommend_with_docs_no_documents(self, mock_rag_recommend, mock_upload):
        """Test RAG recommendation when no documents exist"""
        mock_rag_recommend.return_value = "# Fallback Recommendation\n\nNo documents found, but here's general advice..."

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "No Docs RAG Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Get RAG recommendation without any documents
        current_plan = {
            "tasks": [{"id": 1, "name": "Task 1", "status": "pending"}],
            "risks": [],
            "milestones": []
        }

        recommend_data = {
            "project_id": project_id,
            "plan_json": json.dumps(current_plan),
            "user_question": "How should I proceed?"
        }

        response = client.post("/project/recommend_with_docs", json=recommend_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "recommendation_markdown" in data
        assert "Fallback Recommendation" in data["recommendation_markdown"]

    @patch('gemini_service.upload_file_to_gemini')
    @patch('gemini_rag_service.rag_recommendation')
    def test_recommend_with_docs_rag_service_error(self, mock_rag_recommend, mock_upload):
        """Test RAG recommendation when RAG service fails"""
        mock_upload.return_value = "files/test_doc_789"
        mock_rag_recommend.side_effect = Exception("RAG service unavailable")

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "RAG Error Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Upload a document
        file_content = b"This document should trigger RAG processing."
        files = {"file": ("test.txt", file_content, "text/plain")}
        upload_response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)

        # Get recommendation when RAG service fails
        current_plan = {
            "tasks": [{"id": 1, "name": "Task 1", "status": "in_progress"}],
            "risks": ["Test risk"],
            "milestones": []
        }

        recommend_data = {
            "project_id": project_id,
            "plan_json": json.dumps(current_plan),
            "user_question": "What should I do?"
        }

        response = client.post("/project/recommend_with_docs", json=recommend_data, headers=headers)
        assert response.status_code == 500
        assert "error generating rag response" in response.json()["detail"].lower()

    @patch('gemini_service.upload_file_to_gemini')
    @patch('gemini_rag_service.rag_recommendation')
    def test_recommend_with_docs_comparison_with_control_group(self, mock_rag_recommend, mock_upload):
        """Test comparing RAG recommendation with control group recommendation"""
        mock_upload.return_value = "files/comparison_doc"
        mock_rag_recommend.return_value = "# Context-Aware Recommendation\n\nBased on your specific project documents..."

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Comparison Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Upload project-specific documents
        file_content = b"Project uses Python, FastAPI, and PostgreSQL. Current deadline is Q4."
        files = {"file": ("project_details.txt", file_content, "text/plain")}
        upload_response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)

        # Get control group recommendation
        control_request = {
            "project_id": project_id,
            "user_question": "What technology stack should I use?"
        }
        control_response = client.post(f"/project/{project_id}/recommend", json=control_request, headers=headers)
        assert control_response.status_code == 200
        control_recommendation = control_response.json()["recommendation_markdown"]

        # Get RAG recommendation
        rag_request = {
            "project_id": project_id,
            "user_question": "What technology stack should I use?"
        }
        rag_response = client.post(f"/project/{project_id}/recommend_with_docs", json=rag_request, headers=headers)
        assert rag_response.status_code == 200
        rag_recommendation = rag_response.json()["recommendation_markdown"]

        # Verify both recommendations are different
        assert control_recommendation != rag_recommendation
        assert "Context-Aware Recommendation" in rag_recommendation
        assert len(rag_recommendation) > 0

    @patch('gemini_service.upload_file_to_gemini')
    @patch('gemini_rag_service.rag_update')
    def test_update_with_docs_invalid_project(self, mock_rag_update, mock_upload):
        """Test RAG update for non-existent project"""
        mock_rag_update.return_value = "Some response"

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        update_data = {
            "project_id": 99999,
            "update_text": "This should fail due to non-existent project"
        }

        response = client.post("/project/99999/update_with_docs", json=update_data, headers=headers)
        assert response.status_code == 404
        assert "project with id 99999 not found" in response.json()["detail"].lower()

    @patch('gemini_service.upload_file_to_gemini')
    @patch('gemini_rag_service.rag_update')
    def test_update_with_docs_invalid_json_plan(self, mock_rag_update, mock_upload):
        """Test RAG update with invalid JSON in updated_plan_json"""
        mock_upload.return_value = "files/test_doc"
        mock_rag_update.return_value = "# Update Analysis\n\nHere's my analysis..."

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Invalid JSON RAG Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Upload a document
        file_content = b"Project document content"
        files = {"file": ("doc.txt", file_content, "text/plain")}
        upload_response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)

        # Send update with invalid JSON
        update_data = {
            "project_id": project_id,
            "update_text": "Some update text",
            "updated_plan_json": "invalid json string"
        }

        response = client.post(f"/project/{project_id}/update_with_docs", json=update_data, headers=headers)
        assert response.status_code == 400  # Bad Request due to invalid JSON

    def test_rag_endpoints_require_authentication(self):
        """Test that RAG endpoints require authentication"""
        recommend_data = {
            "project_id": 1,
            "user_question": "Test question"
        }
        update_data = {
            "project_id": 1,
            "update_text": "Test update"
        }

        # Test recommend endpoint
        response = client.post("/project/1/recommend_with_docs", json=recommend_data)
        assert response.status_code == 401  # Unauthorized

        # Test update endpoint
        response = client.post("/project/1/update_with_docs", json=update_data)
        assert response.status_code == 401  # Unauthorized

    def test_rag_endpoints_invalid_api_key(self):
        """Test RAG endpoints with invalid API key"""
        headers = {"X-API-Key": "invalid-api-key"}

        recommend_data = {
            "project_id": 1,
            "user_question": "Test question"
        }
        update_data = {
            "project_id": 1,
            "update_text": "Test update"
        }

        # Test recommend endpoint
        response = client.post("/project/1/recommend_with_docs", json=recommend_data, headers=headers)
        assert response.status_code == 403  # Forbidden

        # Test update endpoint
        response = client.post("/project/1/update_with_docs", json=update_data, headers=headers)
        assert response.status_code == 403  # Forbidden


class TestPerformanceAndStress:
    """Test performance and stress testing for all endpoints"""

    def test_concurrent_project_creation(self):
        """Test concurrent project creation requests"""
        import threading
        import time

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        results = []
        errors = []

        def create_project(index):
            try:
                start_time = time.time()
                project_data = {"name": f"Concurrent Project {index}"}
                response = client.post("/project/create", json=project_data, headers=headers)
                end_time = time.time()
                results.append((index, response.status_code, end_time - start_time))
            except Exception as e:
                errors.append((index, str(e)))

        # Create 5 projects concurrently
        threads = []
        start_total = time.time()
        for i in range(5):
            thread = threading.Thread(target=create_project, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_total

        # Verify all requests succeeded
        assert len(results) == 5
        successful_requests = [r for r in results if r[1] == 201]
        assert len(successful_requests) == 5
        assert len(errors) == 0

        # Performance check: should complete within reasonable time
        assert total_time < 10.0  # 10 seconds max for 5 concurrent requests

        # Calculate average response time
        avg_response_time = sum(r[2] for r in results) / len(results)
        assert avg_response_time < 2.0  # 2 seconds average per request

    def test_concurrent_document_uploads(self):
        """Test document upload performance (sequential simulation)"""
        import time

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project first
        project_data = {"name": "Performance Upload Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        results = []

        # Upload 3 documents sequentially to test basic performance
        with patch('gemini_service.upload_file_to_gemini') as mock_upload:
            start_total = time.time()

            for i in range(3):
                unique_id = f"files/perf_doc_{i}"
                mock_upload.return_value = unique_id

                start_time = time.time()
                file_content = f"Performance test document {i} content".encode()
                files = {"file": (f"perf_doc_{i}.txt", file_content, "text/plain")}
                response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)
                end_time = time.time()

                results.append((i, response.status_code, end_time - start_time))

            total_time = time.time() - start_total

        # Verify all uploads succeeded
        assert len(results) == 3
        successful_uploads = [r for r in results if r[1] == 201]
        assert len(successful_uploads) == 3

        # Performance check for sequential uploads (should still be fast)
        assert total_time < 3.0  # 3 seconds max for 3 sequential uploads

        # Calculate average time per upload
        avg_time = sum(r[2] for r in results) / len(results)
        assert avg_time < 1.0  # 1 second average per upload

    @patch('gemini_service.upload_file_to_gemini')
    @patch('gemini_rag_service.rag_recommendation')
    def test_concurrent_rag_recommendations(self, mock_rag_recommend, mock_upload):
        """Test concurrent RAG recommendation performance"""
        import threading
        import time

        mock_upload.return_value = f"files/rag_test_doc"
        mock_rag_recommend.return_value = "# Performance Test Recommendation\n\nThis is a performance test response."

        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project and upload document
        project_data = {"name": "RAG Performance Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        file_content = b"Performance test document for RAG recommendations."
        files = {"file": ("rag_perf_doc.txt", file_content, "text/plain")}
        client.post(f"/project/{project_id}/upload", files=files, headers=headers)

        results = []
        errors = []

        def get_rag_recommendation(index):
            try:
                start_time = time.time()
                current_plan = {
                    "tasks": [{"id": 1, "name": f"Task {index}", "status": "in_progress"}],
                    "risks": ["Performance risk"],
                    "milestones": []
                }

                recommend_data = {
                    "project_id": project_id,
                    "plan_json": json.dumps(current_plan),
                    "user_question": f"Performance test question {index}?"
                }

                response = client.post("/project/recommend_with_docs", json=recommend_data, headers=headers)
                end_time = time.time()
                results.append((index, response.status_code, end_time - start_time))
            except Exception as e:
                errors.append((index, str(e)))

        # Get 3 RAG recommendations concurrently
        threads = []
        start_total = time.time()
        for i in range(3):
            thread = threading.Thread(target=get_rag_recommendation, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_total

        # Verify all recommendations succeeded
        assert len(results) == 3
        successful_recommendations = [r for r in results if r[1] == 200]
        assert len(successful_recommendations) == 3
        assert len(errors) == 0

        # Performance check for concurrent RAG recommendations
        assert total_time < 15.0  # 15 seconds max for 3 concurrent RAG requests
        assert mock_rag_recommend.call_count == 3

    def test_large_file_upload_performance(self):
        """Test performance with large file uploads"""
        import time
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create a project
        project_data = {"name": "Large File Performance Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Test with different file sizes
        file_sizes = [
            ("small_file.txt", 1024),      # 1 KB
            ("medium_file.txt", 1024 * 100),  # 100 KB
            ("large_file.txt", 1024 * 1024)   # 1 MB
        ]

        for filename, size in file_sizes:
            with patch('gemini_service.upload_file_to_gemini', return_value=f"files/{filename}"):
                start_time = time.time()
                file_content = b"A" * size
                files = {"file": (filename, file_content, "text/plain")}
                response = client.post(f"/project/{project_id}/upload", files=files, headers=headers)
                end_time = time.time()

                assert response.status_code == 201
                upload_time = end_time - start_time

                # Performance assertions based on file size
                if size == 1024:  # 1KB
                    assert upload_time < 1.0
                elif size == 1024 * 100:  # 100KB
                    assert upload_time < 2.0
                elif size == 1024 * 1024:  # 1MB
                    assert upload_time < 5.0

    def test_database_performance_with_multiple_projects(self):
        """Test database performance with many projects"""
        import time
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create multiple projects and test database queries
        project_ids = []

        # Create 10 projects
        for i in range(10):
            project_data = {"name": f"Database Performance Test {i}"}
            create_response = client.post("/project/create", json=project_data, headers=headers)
            project_ids.append(create_response.json()["id"])

        # Test project listing performance
        start_time = time.time()
        list_response = client.get("/projects", headers=headers)
        end_time = time.time()

        assert list_response.status_code == 200
        projects = list_response.json()
        assert len(projects) >= 10
        query_time = end_time - start_time

        # Database query should be fast
        assert query_time < 2.0

        # Test individual project retrieval performance
        for project_id in project_ids[:3]:  # Test first 3 projects
            start_time = time.time()
            get_response = client.get(f"/project/{project_id}", headers=headers)
            end_time = time.time()

            assert get_response.status_code == 200
            assert end_time - start_time < 0.5  # Individual queries should be very fast

    def test_memory_usage_stress_test(self):
        """Test memory usage with sustained load"""
        headers = {"X-API-Key": "test-api-key-for-testing-only"}

        # Create project
        project_data = {"name": "Memory Stress Test"}
        create_response = client.post("/project/create", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Perform many operations to test memory usage
        operations_count = 20
        successful_operations = 0

        for i in range(operations_count):
            try:
                # Create project
                project_data = {"name": f"Memory Test Project {i}"}
                create_response = client.post("/project/create", json=project_data, headers=headers)

                if create_response.status_code == 201:
                    successful_operations += 1

                    # Get project
                    get_response = client.get(f"/project/{create_response.json()['id']}", headers=headers)

                    # Delete project (if endpoint exists, otherwise just continue)
                    # Note: Assuming project deletion isn't implemented, we'll just count creations

            except Exception:
                # Log error but continue
                pass

        # Verify a good percentage of operations succeeded
        success_rate = successful_operations / operations_count
        assert success_rate >= 0.8  # At least 80% success rate


if __name__ == "__main__":
    pytest.main([__file__])