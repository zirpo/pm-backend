"""
Integration tests for FastAPI endpoints.

This module tests the complete API behavior including:
- Request/response handling
- Database operations
- LLM agent integration
- Error handling
- Status codes
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app
import models
import schemas
import llm_agents


class TestHealthEndpoint:
    """Test cases for the health check endpoint."""

    def test_health_check(self, client):
        """Test the health check endpoint returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCreateProjectEndpoint:
    """Test cases for the create project endpoint."""

    def test_create_project_success(self, client):
        """Test successful project creation."""
        project_data = {"name": "Test Project"}
        response = client.post("/project/create", json=project_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert "id" in data
        assert data["plan_json"] == {"tasks": [], "risks": [], "milestones": []}

    def test_create_project_invalid_data(self, client):
        """Test project creation with invalid data."""
        # Empty name
        response = client.post("/project/create", json={"name": ""})
        assert response.status_code == 422

        # Missing name
        response = client.post("/project/create", json={})
        assert response.status_code == 422

        # Too long name
        long_name = "A" * 300
        response = client.post("/project/create", json={"name": long_name})
        assert response.status_code == 422

    def test_create_project_with_unicode(self, client):
        """Test project creation with unicode characters."""
        unicode_name = "项目管理系统 📊 Projet de Gestion"
        response = client.post("/project/create", json={"name": unicode_name})

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == unicode_name

    def test_create_project_with_whitespace_name(self, client):
        """Test project creation with whitespace-only name."""
        # Should pass since only min_length=1 is required
        response = client.post("/project/create", json={"name": "   "})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "   "

    def test_create_multiple_projects(self, client):
        """Test creating multiple projects."""
        projects = [
            {"name": "Project Alpha"},
            {"name": "Project Beta"},
            {"name": "Project Gamma"}
        ]

        created_ids = []
        for project_data in projects:
            response = client.post("/project/create", json=project_data)
            assert response.status_code == 201
            created_ids.append(response.json()["id"])

        # Verify all IDs are unique
        assert len(set(created_ids)) == len(created_ids)


class TestGetProjectEndpoint:
    """Test cases for the get project endpoint."""

    def test_get_existing_project(self, client, sample_project):
        """Test retrieving an existing project."""
        response = client.get(f"/project/{sample_project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_project.id
        assert data["name"] == sample_project.name
        assert "plan_json" in data

    def test_get_nonexistent_project(self, client):
        """Test retrieving a non-existent project."""
        response = client.get("/project/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"

    def test_get_project_invalid_id(self, client):
        """Test retrieving project with invalid ID format."""
        response = client.get("/project/invalid")
        assert response.status_code == 422  # FastAPI validation error

    def test_get_project_negative_id(self, client):
        """Test retrieving project with negative ID."""
        response = client.get("/project/-1")
        # FastAPI may return 404 or 422 depending on validation
        assert response.status_code in [404, 422]

    def test_get_project_zero_id(self, client):
        """Test retrieving project with zero ID."""
        response = client.get("/project/0")
        # May return 404 or 422 depending on validation
        assert response.status_code in [404, 422]


class TestListProjectsEndpoint:
    """Test cases for the list projects endpoint."""

    @pytest.mark.skip(reason="Cannot test empty database in shared test session")
    def test_list_empty_projects(self, client):
        """Test listing projects when database is empty."""
        response = client.get("/projects/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_projects_with_data(self, client, multiple_projects):
        """Test listing projects when database has data."""
        response = client.get("/projects/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3  # At least the 3 projects we created

        # Verify structure of returned projects
        for project in data:
            assert "id" in project
            assert "name" in project
            # Should not include plan_json for ProjectList schema
            assert "plan_json" not in project

    def test_list_projects_order(self, client, multiple_projects):
        """Test that projects are returned in a consistent order."""
        response1 = client.get("/projects/")
        response2 = client.get("/projects/")

        assert response1.json() == response2.json()

    def test_list_projects_single_project(self, client, sample_project):
        """Test listing projects when only one exists."""
        response = client.get("/projects/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        # Find our sample project
        sample_ids = [p["id"] for p in data if p["name"] == sample_project.name]
        assert len(sample_ids) >= 1


class TestUpdateProjectEndpoint:
    """Test cases for the update project endpoint."""

    @patch('llm_agents.call_deepseek_llm')
    def test_update_project_success(self, mock_llm_call, client, sample_project):
        """Test successful project update."""
        # Mock LLM response
        mock_llm_call.return_value = json.dumps({
            "tasks": [{"id": 1, "name": "New Task", "status": "todo"}],
            "risks": [],
            "milestones": []
        })

        update_data = {
            "project_id": sample_project.id,
            "update_text": "Add a new task for API development"
        }

        response = client.post("/project/update", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == sample_project.id
        assert "new_plan" in data
        assert "tasks" in data["new_plan"]

    def test_update_nonexistent_project(self, client):
        """Test updating a non-existent project."""
        update_data = {
            "project_id": 99999,
            "update_text": "Add a new task"
        }

        response = client.post("/project/update", json=update_data)
        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"

    def test_update_project_invalid_data(self, client, sample_project):
        """Test project update with invalid request data."""
        # Missing project_id
        response = client.post("/project/update", json={"update_text": "Add task"})
        assert response.status_code == 422

        # Missing update_text
        response = client.post("/project/update", json={"project_id": sample_project.id})
        assert response.status_code == 422

        # Invalid project_id
        response = client.post("/project/update", json={
            "project_id": -1,
            "update_text": "Add task"
        })
        assert response.status_code == 422

        # Empty update_text
        response = client.post("/project/update", json={
            "project_id": sample_project.id,
            "update_text": ""
        })
        assert response.status_code == 422

    @patch('llm_agents.call_deepseek_llm')
    def test_update_project_llm_error(self, mock_llm_call, client, sample_project):
        """Test project update when LLM fails."""
        # Mock LLM to raise an exception
        mock_llm_call.side_effect = Exception("LLM API error")

        update_data = {
            "project_id": sample_project.id,
            "update_text": "Add a new task"
        }

        response = client.post("/project/update", json=update_data)
        assert response.status_code == 500
        assert "LLM State Update failed" in response.json()["detail"]

    @patch('llm_agents.call_deepseek_llm')
    def test_update_project_invalid_llm_response(self, mock_llm_call, client, sample_project):
        """Test project update when LLM returns invalid response."""
        # Mock LLM to return non-JSON response
        mock_llm_call.return_value = "This is not valid JSON"

        update_data = {
            "project_id": sample_project.id,
            "update_text": "Add a new task"
        }

        response = client.post("/project/update", json=update_data)
        assert response.status_code == 500
        assert "LLM State Update failed" in response.json()["detail"]

    @patch('llm_agents.call_deepseek_llm')
    def test_update_project_complex_request(self, mock_llm_call, client, sample_project):
        """Test project update with complex update text."""
        mock_llm_call.return_value = json.dumps({
            "tasks": [
                {"id": 1, "name": "Design API", "status": "completed"},
                {"id": 2, "name": "Implement Backend", "status": "in_progress"}
            ],
            "risks": ["Budget constraints"],
            "milestones": [{"id": 1, "name": "MVP", "completed": False}]
        })

        complex_update = """
        Update the project with the following changes:
        1. Mark API design as completed
        2. Add backend implementation task
        3. Add budget risk
        4. Set MVP milestone
        Include special characters: !@#$%^&*()
        """

        update_data = {
            "project_id": sample_project.id,
            "update_text": complex_update.strip()
        }

        response = client.post("/project/update", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert len(data["new_plan"]["tasks"]) == 2
        assert len(data["new_plan"]["risks"]) == 1
        assert len(data["new_plan"]["milestones"]) == 1


class TestRecommendProjectEndpoint:
    """Test cases for the recommend project endpoint."""

    @patch('llm_agents.call_deepseek_llm')
    def test_recommend_project_success(self, mock_llm_call, client, sample_project):
        """Test successful project recommendation."""
        # Mock LLM response
        mock_llm_call.return_value = """# Project Analysis

## Current Status
Based on your project plan, you have 0 tasks in progress.

## Recommendations
1. Focus on completing current tasks
2. Consider adding more specific milestones

## Next Steps
- Prioritize high-impact tasks
- Set clear completion criteria"""

        request_data = {
            "project_id": sample_project.id,
            "user_question": "What are the next steps?"
        }

        response = client.post("/project/recommend", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == sample_project.id
        assert "recommendation_markdown" in data
        assert "Project Analysis" in data["recommendation_markdown"]

    def test_recommend_nonexistent_project(self, client):
        """Test recommending for a non-existent project."""
        request_data = {
            "project_id": 99999,
            "user_question": "What are the next steps?"
        }

        response = client.post("/project/recommend", json=request_data)
        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"

    def test_recommend_project_invalid_data(self, client, sample_project):
        """Test project recommendation with invalid request data."""
        # Missing project_id
        response = client.post("/project/recommend", json={"user_question": "What next?"})
        assert response.status_code == 422

        # Missing user_question
        response = client.post("/project/recommend", json={"project_id": sample_project.id})
        assert response.status_code == 422

        # Invalid project_id
        response = client.post("/project/recommend", json={
            "project_id": -1,
            "user_question": "What next?"
        })
        assert response.status_code == 422

        # Empty user_question
        response = client.post("/project/recommend", json={
            "project_id": sample_project.id,
            "user_question": ""
        })
        assert response.status_code == 422

    @patch('llm_agents.call_deepseek_llm')
    def test_recommend_project_llm_error(self, mock_llm_call, client, sample_project):
        """Test project recommendation when LLM fails."""
        # Mock LLM to raise an exception
        mock_llm_call.side_effect = Exception("LLM API error")

        request_data = {
            "project_id": sample_project.id,
            "user_question": "What are the next steps?"
        }

        response = client.post("/project/recommend", json=request_data)
        assert response.status_code == 500
        assert "LLM Recommendation failed" in response.json()["detail"]

    @patch('llm_agents.call_deepseek_llm')
    def test_recommend_project_complex_question(self, mock_llm_call, client, complex_project):
        """Test project recommendation with complex question."""
        mock_llm_call.return_value = """# Comprehensive Project Analysis

## Current State Analysis
Your project has 3 tasks with mixed completion status.

## Risk Assessment
Timeline constraints require attention.

## Strategic Recommendations
1. Accelerate backend implementation
2. Allocate additional resources
3. Review milestone dependencies

## Resource Allocation
Consider developer workload balancing."""

        complex_question = """
        Based on the current project status, please provide:
        1. Analysis of task dependencies and critical path
        2. Risk assessment for timeline and budget
        3. Recommendations for resource allocation
        4. Suggestions for next milestones and their priorities
        Consider that we have budget constraints and limited developer resources.
        Also include special characters: 📊 📈 🎯
        """

        request_data = {
            "project_id": complex_project.id,
            "user_question": complex_question.strip()
        }

        response = client.post("/project/recommend", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "Comprehensive Project Analysis" in data["recommendation_markdown"]
        assert data["project_id"] == complex_project.id

    @patch('llm_agents.call_deepseek_llm')
    def test_recommend_project_unicode_question(self, mock_llm_call, client, sample_project):
        """Test project recommendation with unicode characters."""
        mock_llm_call.return_value = """# 项目分析报告

## 当前状态
项目有 0 个任务正在进行中。

## 建议
1. 专注于完成当前任务
2. 考虑添加更具体的里程碑

## 下一步
- 优先考虑高影响力的任务
- 设定明确的完成标准"""

        unicode_question = "项目下一步应该做什么？ 📊"

        request_data = {
            "project_id": sample_project.id,
            "user_question": unicode_question
        }

        response = client.post("/project/recommend", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "项目分析报告" in data["recommendation_markdown"]


class TestDatabaseIntegration:
    """Test cases for database integration across endpoints."""

    def test_create_then_get_project(self, client):
        """Test creating a project and then retrieving it."""
        # Create project
        create_data = {"name": "Integration Test Project"}
        create_response = client.post("/project/create", json=create_data)
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Get project
        get_response = client.get(f"/project/{project_id}")
        assert get_response.status_code == 200
        project_data = get_response.json()
        assert project_data["name"] == create_data["name"]

    def test_create_then_update_project(self, client):
        """Test creating a project and then updating it."""
        # Create project
        create_data = {"name": "Update Test Project"}
        create_response = client.post("/project/create", json=create_data)
        project_id = create_response.json()["id"]

        # Update project (using mock to avoid real LLM calls)
        with patch('llm_agents.call_deepseek_llm') as mock_llm:
            mock_llm.return_value = json.dumps({
                "tasks": [{"id": 1, "name": "Updated Task", "status": "todo"}],
                "risks": [],
                "milestones": []
            })

            update_data = {
                "project_id": project_id,
                "update_text": "Add updated task"
            }
            update_response = client.post("/project/update", json=update_data)
            assert update_response.status_code == 200

        # Verify update by getting project
        get_response = client.get(f"/project/{project_id}")
        assert get_response.status_code == 200
        updated_project = get_response.json()
        assert len(updated_project["plan_json"]["tasks"]) == 1
        assert updated_project["plan_json"]["tasks"][0]["name"] == "Updated Task"

    def test_multiple_operations_consistency(self, client):
        """Test that multiple operations maintain data consistency."""
        # Create multiple projects
        projects = []
        for i in range(3):
            response = client.post("/project/create", json={"name": f"Test Project {i}"})
            projects.append(response.json())

        # List all projects
        list_response = client.get("/projects/")
        listed_projects = list_response.json()

        # Verify all created projects are in the list
        created_ids = {p["id"] for p in projects}
        listed_ids = {p["id"] for p in listed_projects if "Test Project" in p["name"]}

        assert created_ids.issubset(listed_ids)

        # Get each project individually
        for project in projects:
            get_response = client.get(f"/project/{project['id']}")
            assert get_response.status_code == 200
            assert get_response.json()["name"] == project["name"]


class TestErrorHandling:
    """Test cases for error handling across endpoints."""

    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON in request body."""
        response = client.post(
            "/project/create",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_content_type(self, client):
        """Test handling of missing Content-Type header."""
        response = client.post(
            "/project/create",
            data='{"name": "Test"}'
        )
        # FastAPI might still handle this correctly, but should validate
        assert response.status_code in [201, 422]

    def test_database_connection_issues(self, client):
        """Test behavior when database has issues (simulated)."""
        # This would require more complex setup to simulate DB issues
        # For now, just test normal operation
        response = client.get("/projects/")
        assert response.status_code in [200, 500]

    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        import threading
        import time

        results = []

        def make_request():
            response = client.get("/health")
            results.append(response.status_code)

        # Create multiple threads making requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 10


@pytest.mark.integration
class TestWorkflowIntegration:
    """Integration tests for complete workflows."""

    @patch('llm_agents.call_deepseek_llm')
    def test_complete_project_workflow(self, mock_llm_call, client):
        """Test a complete project workflow from creation to recommendations."""
        # Setup mock LLM responses
        mock_llm_call.side_effect = [
            # First call for update
            json.dumps({
                "tasks": [
                    {"id": 1, "name": "Design API", "status": "completed"},
                    {"id": 2, "name": "Implement Backend", "status": "todo"}
                ],
                "risks": ["Timeline risk"],
                "milestones": []
            }),
            # Second call for recommendation
            """# Workflow Analysis

## Current Progress
API design is complete, backend implementation pending.

## Recommendations
1. Prioritize backend implementation
2. Monitor timeline risks
3. Plan next milestone"""
        ]

        # Step 1: Create project
        create_response = client.post("/project/create", json={"name": "Workflow Test"})
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Step 2: Update project with initial plan
        update_response = client.post("/project/update", json={
            "project_id": project_id,
            "update_text": "Add API design and backend tasks"
        })
        assert update_response.status_code == 200

        # Step 3: Get recommendation
        recommend_response = client.post("/project/recommend", json={
            "project_id": project_id,
            "user_question": "What should I work on next?"
        })
        assert recommend_response.status_code == 200

        # Step 4: Verify final state
        final_project = client.get(f"/project/{project_id}")
        assert final_project.status_code == 200
        project_data = final_project.json()

        # Verify workflow results
        assert project_data["name"] == "Workflow Test"
        assert len(project_data["plan_json"]["tasks"]) == 2
        assert "Workflow Analysis" in recommend_response.json()["recommendation_markdown"]

    def test_error_recovery_workflow(self, client):
        """Test workflow behavior when errors occur."""
        # Create project
        create_response = client.post("/project/create", json={"name": "Error Test"})
        project_id = create_response.json()["id"]

        # Try to update non-existent project (should fail gracefully)
        fail_response = client.post("/project/update", json={
            "project_id": 99999,
            "update_text": "This should fail"
        })
        assert fail_response.status_code == 404

        # Verify original project is still accessible
        get_response = client.get(f"/project/{project_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Error Test"