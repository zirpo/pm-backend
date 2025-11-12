"""
Unit tests for Pydantic schemas.

This module tests schema validation, serialization, deserialization,
and field constraints defined in the schemas module.
"""

import pytest
from pydantic import ValidationError, Field
from datetime import datetime
from typing import Dict, Any

import schemas


class TestProjectBase:
    """Test cases for ProjectBase schema."""

    def test_valid_project_base(self):
        """Test creating a valid ProjectBase instance."""
        project_data = {
            "name": "Test Project"
        }
        project = schemas.ProjectBase(**project_data)
        assert project.name == "Test Project"

    def test_project_base_empty_name(self):
        """Test ProjectBase with empty name."""
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectBase(name="")

        assert "name" in str(exc_info.value).lower()
        assert "string_too_short" in str(exc_info.value).lower()

    def test_project_base_whitespace_name(self):
        """Test ProjectBase with whitespace-only name - should pass as only min_length is enforced."""
        # Whitespace-only names should pass validation since only min_length=1 is required
        project = schemas.ProjectBase(name="   ")
        assert project.name == "   "

    def test_project_base_name_length_validation(self):
        """Test ProjectBase with very long name."""
        long_name = "A" * 300  # Exceeds max_length of 255
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectBase(name=long_name)

        assert "name" in str(exc_info.value).lower()
        assert "string_too_long" in str(exc_info.value).lower()

    def test_project_boundary_name_length(self):
        """Test ProjectBase with boundary name length."""
        boundary_name = "A" * 255  # Exactly max_length
        project = schemas.ProjectBase(name=boundary_name)
        assert project.name == boundary_name


class TestProjectCreate:
    """Test cases for ProjectCreate schema."""

    def test_valid_project_create(self):
        """Test creating a valid ProjectCreate instance."""
        project_data = {
            "name": "Test Project"
        }
        project = schemas.ProjectCreate(**project_data)
        assert project.name == "Test Project"

    def test_project_create_inherits_validation(self):
        """Test that ProjectCreate inherits validation from ProjectBase."""
        with pytest.raises(ValidationError):
            schemas.ProjectCreate(name="")

        with pytest.raises(ValidationError):
            schemas.ProjectCreate(name="A" * 300)


class TestProject:
    """Test cases for Project response schema."""

    def test_valid_project_response(self):
        """Test creating a valid Project response instance."""
        plan_data = schemas.ProjectPlan(tasks=[], risks=[], milestones=[])
        project_data = {
            "id": 1,
            "name": "Test Project",
            "plan_json": plan_data
        }
        project = schemas.Project(**project_data)
        assert project.id == 1
        assert project.name == "Test Project"
        assert project.plan_json == plan_data
        assert isinstance(project.plan_json, schemas.ProjectPlan)

    def test_project_response_missing_id(self):
        """Test Project response missing required id field."""
        project_data = {
            "name": "Test Project",
            "plan_json": {"tasks": [], "risks": [], "milestones": []}
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.Project(**project_data)

        assert "id" in str(exc_info.value).lower()

    def test_project_response_missing_name(self):
        """Test Project response missing required name field."""
        plan_data = schemas.ProjectPlan(tasks=[], risks=[], milestones=[])
        project_data = {
            "id": 1,
            "plan_json": plan_data
        }
        with pytest.raises(ValidationError):
            schemas.Project(**project_data)

    def test_project_response_missing_plan_json(self):
        """Test Project response missing plan_json field."""
        project_data = {
            "id": 1,
            "name": "Test Project"
        }
        with pytest.raises(ValidationError):
            schemas.Project(**project_data)

    def test_project_response_complex_plan(self):
        """Test Project response with complex plan_json structure."""
        complex_plan_dict = {
            "tasks": [
                {
                    "id": 1,
                    "name": "Design API",
                    "status": "completed",
                    "assignee": "Alice",
                    "priority": "high"
                }
            ],
            "risks": ["Budget constraints"],
            "milestones": [
                {
                    "id": 1,
                    "name": "MVP Release",
                    "completed": False
                }
            ]
        }
        complex_plan = schemas.ProjectPlan(**complex_plan_dict)
        project_data = {
            "id": 1,
            "name": "Complex Project",
            "plan_json": complex_plan
        }
        project = schemas.Project(**project_data)
        assert project.plan_json == complex_plan
        assert isinstance(project.plan_json, schemas.ProjectPlan)

    def test_project_serialization(self):
        """Test Project serialization to dict."""
        plan_data = schemas.ProjectPlan(tasks=[], risks=[], milestones=[])
        project_data = {
            "id": 1,
            "name": "Test Project",
            "plan_json": plan_data
        }
        project = schemas.Project(**project_data)
        project_dict = project.model_dump()

        # plan_json should be serialized as a dict when model_dump() is called
        expected_dict = {
            "id": 1,
            "name": "Test Project",
            "plan_json": {"tasks": [], "risks": [], "milestones": []}
        }
        assert project_dict == expected_dict

    def test_project_json_serialization(self):
        """Test Project serialization to JSON."""
        plan_data = schemas.ProjectPlan(tasks=[], risks=[], milestones=[])
        project_data = {
            "id": 1,
            "name": "Test Project",
            "plan_json": plan_data
        }
        project = schemas.Project(**project_data)
        project_json = project.model_dump_json()

        import json
        parsed_json = json.loads(project_json)
        expected_dict = {
            "id": 1,
            "name": "Test Project",
            "plan_json": {"tasks": [], "risks": [], "milestones": []}
        }
        assert parsed_json == expected_dict


class TestProjectList:
    """Test cases for ProjectList schema."""

    def test_valid_project_list(self):
        """Test creating a valid ProjectList instance."""
        project_data = {
            "id": 1,
            "name": "Test Project"
        }
        project = schemas.ProjectList(**project_data)
        assert project.id == 1
        assert project.name == "Test Project"

    def test_project_list_missing_id(self):
        """Test ProjectList missing required id field."""
        project_data = {
            "name": "Test Project"
        }
        with pytest.raises(ValidationError):
            schemas.ProjectList(**project_data)

    def test_project_list_missing_name(self):
        """Test ProjectList missing required name field."""
        project_data = {
            "id": 1
        }
        with pytest.raises(ValidationError):
            schemas.ProjectList(**project_data)


class TestUpdateRequest:
    """Test cases for UpdateRequest schema."""

    def test_valid_update_request(self):
        """Test creating a valid UpdateRequest instance."""
        update_data = {
            "project_id": 1,
            "update_text": "Add a new task for API development"
        }
        request = schemas.UpdateRequest(**update_data)
        assert request.project_id == 1
        assert request.update_text == "Add a new task for API development"

    def test_update_request_missing_project_id(self):
        """Test UpdateRequest missing project_id."""
        update_data = {
            "update_text": "Add a new task"
        }
        with pytest.raises(ValidationError):
            schemas.UpdateRequest(**update_data)

    def test_update_request_missing_update_text(self):
        """Test UpdateRequest missing update_text."""
        update_data = {
            "project_id": 1
        }
        with pytest.raises(ValidationError):
            schemas.UpdateRequest(**update_data)

    def test_update_request_negative_project_id(self):
        """Test UpdateRequest with negative project_id."""
        update_data = {
            "project_id": -1,
            "update_text": "Add a new task"
        }
        with pytest.raises(ValidationError):
            schemas.UpdateRequest(**update_data)

    def test_update_request_zero_project_id(self):
        """Test UpdateRequest with zero project_id."""
        update_data = {
            "project_id": 0,
            "update_text": "Add a new task"
        }
        with pytest.raises(ValidationError):
            schemas.UpdateRequest(**update_data)

    def test_update_request_empty_update_text(self):
        """Test UpdateRequest with empty update_text."""
        update_data = {
            "project_id": 1,
            "update_text": ""
        }
        with pytest.raises(ValidationError):
            schemas.UpdateRequest(**update_data)

    def test_update_request_whitespace_update_text(self):
        """Test UpdateRequest with whitespace-only update_text - should pass as only min_length is enforced."""
        update_data = {
            "project_id": 1,
            "update_text": "   "
        }
        # Whitespace-only should pass validation since only min_length=1 is required
        request = schemas.UpdateRequest(**update_data)
        assert request.update_text == "   "

    def test_update_request_long_update_text(self):
        """Test UpdateRequest with very long update_text."""
        long_text = "A" * 10000  # Test with very long text
        update_data = {
            "project_id": 1,
            "update_text": long_text
        }
        request = schemas.UpdateRequest(**update_data)
        assert request.update_text == long_text

    def test_update_request_complex_update_text(self):
        """Test UpdateRequest with complex update_text containing special characters."""
        complex_text = """
        Update the project plan as follows:
        1. Add new task: "Implement user authentication" with status "todo"
        2. Update task #2 status to "completed"
        3. Add risk: "API rate limiting may affect performance"
        4. Special characters: !@#$%^&*()_+-={}[]|\\:";'<>?,./
        """
        update_data = {
            "project_id": 1,
            "update_text": complex_text.strip()
        }
        request = schemas.UpdateRequest(**update_data)
        assert request.update_text == complex_text.strip()


class TestUpdateResponse:
    """Test cases for UpdateResponse schema."""

    def test_valid_update_response(self):
        """Test creating a valid UpdateResponse instance."""
        new_plan = schemas.ProjectPlan(tasks=[], risks=[], milestones=[])
        response_data = {
            "project_id": 1,
            "new_plan": new_plan
        }
        response = schemas.UpdateResponse(**response_data)
        assert response.project_id == 1
        assert response.new_plan == new_plan
        assert isinstance(response.new_plan, schemas.ProjectPlan)

    def test_update_response_missing_project_id(self):
        """Test UpdateResponse missing project_id."""
        new_plan = schemas.ProjectPlan(tasks=[], risks=[], milestones=[])
        response_data = {
            "new_plan": new_plan
        }
        with pytest.raises(ValidationError):
            schemas.UpdateResponse(**response_data)

    def test_update_response_missing_new_plan(self):
        """Test UpdateResponse missing new_plan."""
        response_data = {
            "project_id": 1
        }
        with pytest.raises(ValidationError):
            schemas.UpdateResponse(**response_data)

    def test_update_response_complex_plan(self):
        """Test UpdateResponse with complex plan structure."""
        complex_plan_dict = {
            "tasks": [
                {
                    "id": 1,
                    "name": "Design API",
                    "status": "completed",
                    "assignee": "Alice",
                    "priority": "high"
                },
                {
                    "id": 2,
                    "name": "Implement Backend",
                    "status": "in_progress",
                    "dependencies": [1]
                }
            ],
            "risks": [
                "Budget constraints",
                "Technical complexity"
            ],
            "milestones": [
                {
                    "id": 1,
                    "name": "MVP Release",
                    "due_date": "2024-03-01",
                    "completed": False
                }
            ]
        }
        complex_plan = schemas.ProjectPlan(**complex_plan_dict)
        response_data = {
            "project_id": 1,
            "new_plan": complex_plan
        }
        response = schemas.UpdateResponse(**response_data)
        assert response.project_id == 1
        assert response.new_plan == complex_plan
        assert isinstance(response.new_plan, schemas.ProjectPlan)


class TestRecommendRequest:
    """Test cases for RecommendRequest schema."""

    def test_valid_recommend_request(self):
        """Test creating a valid RecommendRequest instance."""
        request_data = {
            "project_id": 1,
            "user_question": "What are the next steps?"
        }
        request = schemas.RecommendRequest(**request_data)
        assert request.project_id == 1
        assert request.user_question == "What are the next steps?"

    def test_recommend_request_missing_project_id(self):
        """Test RecommendRequest missing project_id."""
        request_data = {
            "user_question": "What are the next steps?"
        }
        with pytest.raises(ValidationError):
            schemas.RecommendRequest(**request_data)

    def test_recommend_request_missing_user_question(self):
        """Test RecommendRequest missing user_question."""
        request_data = {
            "project_id": 1
        }
        with pytest.raises(ValidationError):
            schemas.RecommendRequest(**request_data)

    def test_recommend_request_negative_project_id(self):
        """Test RecommendRequest with negative project_id."""
        request_data = {
            "project_id": -1,
            "user_question": "What are the next steps?"
        }
        with pytest.raises(ValidationError):
            schemas.RecommendRequest(**request_data)

    def test_recommend_request_empty_user_question(self):
        """Test RecommendRequest with empty user_question."""
        request_data = {
            "project_id": 1,
            "user_question": ""
        }
        with pytest.raises(ValidationError):
            schemas.RecommendRequest(**request_data)

    def test_recommend_request_whitespace_user_question(self):
        """Test RecommendRequest with whitespace-only user_question - should pass as only min_length is enforced."""
        request_data = {
            "project_id": 1,
            "user_question": "   "
        }
        # Whitespace-only should pass validation since only min_length=1 is required
        request = schemas.RecommendRequest(**request_data)
        assert request.user_question == "   "

    def test_recommend_request_complex_question(self):
        """Test RecommendRequest with complex user_question."""
        complex_question = """
        Based on the current project status, please provide:
        1. Analysis of task dependencies
        2. Risk assessment for timeline
        3. Recommendations for resource allocation
        4. Suggestions for next milestones
        Consider that we have budget constraints and limited developer resources.
        """
        request_data = {
            "project_id": 1,
            "user_question": complex_question.strip()
        }
        request = schemas.RecommendRequest(**request_data)
        assert request.user_question == complex_question.strip()


class TestRecommendResponse:
    """Test cases for RecommendResponse schema."""

    def test_valid_recommend_response(self):
        """Test creating a valid RecommendResponse instance."""
        recommendation = "# Project Analysis\n\nBased on your current plan, here are the recommendations..."
        response_data = {
            "project_id": 1,
            "recommendation_markdown": recommendation
        }
        response = schemas.RecommendResponse(**response_data)
        assert response.project_id == 1
        assert response.recommendation_markdown == recommendation

    def test_recommend_response_missing_project_id(self):
        """Test RecommendResponse missing project_id."""
        recommendation = "# Analysis\n\nRecommendations..."
        response_data = {
            "recommendation_markdown": recommendation
        }
        with pytest.raises(ValidationError):
            schemas.RecommendResponse(**response_data)

    def test_recommend_response_missing_recommendation(self):
        """Test RecommendResponse missing recommendation_markdown."""
        response_data = {
            "project_id": 1
        }
        with pytest.raises(ValidationError):
            schemas.RecommendResponse(**response_data)

    def test_recommend_response_empty_recommendation(self):
        """Test RecommendResponse with empty recommendation_markdown."""
        response_data = {
            "project_id": 1,
            "recommendation_markdown": ""
        }
        # This should pass since there's no min_length constraint
        response = schemas.RecommendResponse(**response_data)
        assert response.recommendation_markdown == ""

    def test_recommend_response_markdown_recommendation(self):
        """Test RecommendResponse with markdown-formatted recommendation."""
        markdown_recommendation = """
        # Project Analysis Report

        ## Current Status
        - ✅ Task 1: Completed
        - 🔄 Task 2: In Progress
        - ⏳ Task 3: Pending

        ## Risk Assessment
        | Risk | Probability | Impact | Mitigation |
        |------|-------------|--------|------------|
        Budget overrun | Medium | High | Regular monitoring |

        ## Recommendations
        1. **Priority**: Focus on completing Task 2
        2. **Timeline**: Consider extending deadline by 1 week
        3. **Resources**: Allocate additional developer to Task 3

        ## Next Steps
        - Schedule review meeting
        - Update project timeline
        - Communicate with stakeholders
        """
        response_data = {
            "project_id": 1,
            "recommendation_markdown": markdown_recommendation.strip()
        }
        response = schemas.RecommendResponse(**response_data)
        assert response.recommendation_markdown == markdown_recommendation.strip()


class TestSchemaIntegration:
    """Integration tests for schema interactions."""

    def test_project_response_from_project_create(self):
        """Test converting ProjectCreate to Project response."""
        create_data = schemas.ProjectCreate(name="Test Project")

        # Simulate database response
        response_data = {
            "id": 1,
            "name": create_data.name,
            "plan_json": {"tasks": [], "risks": [], "milestones": []}
        }
        response = schemas.Project(**response_data)

        assert response.name == create_data.name

    def test_schema_serialization_roundtrip(self):
        """Test that schemas can be serialized and deserialized correctly."""
        original_data = {
            "id": 1,
            "name": "Roundtrip Test",
            "plan_json": {"tasks": [], "risks": [], "milestones": []}
        }

        # Create schema instance
        project = schemas.Project(**original_data)

        # Serialize to dict
        serialized = project.model_dump()

        # Deserialize back
        deserialized = schemas.Project(**serialized)

        assert deserialized.model_dump() == original_data

    def test_schema_validation_with_unicode(self):
        """Test schema validation with unicode characters."""
        unicode_name = "项目管理系统 📊 Projet de Gestion"
        unicode_text = "测试中文 validation ✓ ✓ ✓ Тест русский"

        # Test ProjectCreate
        project_create = schemas.ProjectCreate(name=unicode_name)
        assert project_create.name == unicode_name

        # Test UpdateRequest
        update_request = schemas.UpdateRequest(
            project_id=1,
            update_text=unicode_text
        )
        assert update_request.update_text == unicode_text

    def test_schema_field_types(self):
        """Test that schema fields have correct types."""
        plan = schemas.ProjectPlan(tasks=[{"id": 1, "name": "Task"}], risks=[], milestones=[])
        project = schemas.Project(
            id=1,
            name="Test",
            plan_json=plan
        )

        assert isinstance(project.id, int)
        assert isinstance(project.name, str)
        assert isinstance(project.plan_json, schemas.ProjectPlan)

        # Test complex plan in UpdateResponse
        complex_plan = schemas.ProjectPlan(tasks=[{"id": 1, "name": "Task"}], risks=[], milestones=[])
        update_response = schemas.UpdateResponse(project_id=1, new_plan=complex_plan)
        assert isinstance(update_response.new_plan, schemas.ProjectPlan)
        assert isinstance(update_response.new_plan.tasks, list)

    def test_schema_inheritance(self):
        """Test that inheritance works correctly between schemas."""
        # ProjectCreate should inherit from ProjectBase
        project_create = schemas.ProjectCreate(name="Test")
        assert hasattr(project_create, 'name')
        assert project_create.name == "Test"

        # ProjectList should also inherit from ProjectBase
        project_list = schemas.ProjectList(id=1, name="Test")
        assert hasattr(project_list, 'name')
        assert project_list.name == "Test"
        assert project_list.id == 1


class TestProjectPlan:
    """Test cases for ProjectPlan schema."""

    def test_valid_project_plan_minimal(self):
        """Test creating a valid ProjectPlan with minimal data."""
        plan_data = {}
        plan = schemas.ProjectPlan(**plan_data)
        assert plan.tasks == []
        assert plan.risks == []
        assert plan.milestones == []

    def test_valid_project_plan_with_data(self):
        """Test creating a valid ProjectPlan with complete data."""
        plan_data = {
            "tasks": [
                {"id": 1, "name": "Design API", "status": "todo"},
                {"id": 2, "name": "Implement Backend", "status": "in_progress"}
            ],
            "risks": ["Budget constraints", "Technical complexity"],
            "milestones": [
                {"id": 1, "name": "MVP Release", "completed": False}
            ]
        }
        plan = schemas.ProjectPlan(**plan_data)
        assert len(plan.tasks) == 2
        assert len(plan.risks) == 2
        assert len(plan.milestones) == 1
        assert plan.tasks[0]["name"] == "Design API"
        assert plan.risks[0] == "Budget constraints"
        assert plan.milestones[0]["name"] == "MVP Release"

    def test_project_plan_partial_data(self):
        """Test ProjectPlan with partial data."""
        plan_data = {
            "tasks": [{"id": 1, "name": "Single Task"}]
        }
        plan = schemas.ProjectPlan(**plan_data)
        assert len(plan.tasks) == 1
        assert plan.risks == []
        assert plan.milestones == []

    def test_project_plan_empty_lists(self):
        """Test ProjectPlan with explicitly empty lists."""
        plan_data = {
            "tasks": [],
            "risks": [],
            "milestones": []
        }
        plan = schemas.ProjectPlan(**plan_data)
        assert plan.tasks == []
        assert plan.risks == []
        assert plan.milestones == []

    def test_project_plan_complex_task_structure(self):
        """Test ProjectPlan with complex task structures."""
        complex_tasks = [
            {
                "id": 1,
                "name": "Design Database Schema",
                "status": "completed",
                "assignee": "Alice",
                "priority": "high",
                "estimated_hours": 8,
                "dependencies": [],
                "description": "Design the database schema for the project management system"
            },
            {
                "id": 2,
                "name": "Implement API Endpoints",
                "status": "in_progress",
                "assignee": "Bob",
                "priority": "high",
                "estimated_hours": 16,
                "dependencies": [1],
                "description": "Implement RESTful API endpoints for CRUD operations"
            }
        ]
        plan_data = {"tasks": complex_tasks}
        plan = schemas.ProjectPlan(**plan_data)
        assert len(plan.tasks) == 2
        assert plan.tasks[0]["dependencies"] == []
        assert plan.tasks[1]["dependencies"] == [1]

    def test_project_plan_various_risk_formats(self):
        """Test ProjectPlan with different risk formats."""
        risks_data = [
            "Budget overrun",
            "Technical complexity with integration",
            "Timeline constraints due to scope creep",
            "Resource allocation challenges",
            "Third-party dependency risks"
        ]
        plan_data = {"risks": risks_data}
        plan = schemas.ProjectPlan(**plan_data)
        assert len(plan.risks) == 5
        assert "Timeline constraints" in plan.risks[2]

    def test_project_plan_complex_milestone_structure(self):
        """Test ProjectPlan with complex milestone structures."""
        complex_milestones = [
            {
                "id": 1,
                "name": "API Design Complete",
                "description": "Complete API design and documentation",
                "due_date": "2024-02-01",
                "completed": True,
                "completion_date": "2024-01-28"
            },
            {
                "id": 2,
                "name": "Beta Release",
                "description": "Release beta version for testing",
                "due_date": "2024-03-01",
                "completed": False,
                "dependencies": [1]
            }
        ]
        plan_data = {"milestones": complex_milestones}
        plan = schemas.ProjectPlan(**plan_data)
        assert len(plan.milestones) == 2
        assert plan.milestones[0]["completed"] == True
        assert plan.milestones[1]["completed"] == False

    def test_project_plan_serialization(self):
        """Test ProjectPlan serialization to dict."""
        plan_data = {
            "tasks": [{"id": 1, "name": "Test Task"}],
            "risks": ["Test Risk"],
            "milestones": [{"id": 1, "name": "Test Milestone"}]
        }
        plan = schemas.ProjectPlan(**plan_data)
        serialized = plan.model_dump()
        assert serialized == plan_data

    def test_project_plan_json_serialization(self):
        """Test ProjectPlan serialization to JSON."""
        plan_data = {
            "tasks": [{"id": 1, "name": "Test Task"}],
            "risks": ["Test Risk"],
            "milestones": [{"id": 1, "name": "Test Milestone"}]
        }
        plan = schemas.ProjectPlan(**plan_data)
        plan_json = plan.model_dump_json()

        import json
        parsed_json = json.loads(plan_json)
        assert parsed_json == plan_data

    def test_project_plan_extra_fields_allowed(self):
        """Test that ProjectPlan allows extra fields."""
        # Should not raise ValidationError since extra="allow" is set
        plan_data = {
            "tasks": [],
            "risks": [],
            "milestones": [],
            "extra_field": "This should be allowed",
            "another_extra": {"nested": "data"}
        }
        plan = schemas.ProjectPlan(**plan_data)
        assert plan.tasks == []
        assert plan.risks == []
        assert plan.milestones == []
        # Extra fields should be accessible via model_dump()
        dumped = plan.model_dump()
        assert "extra_field" in dumped
        assert dumped["extra_field"] == "This should be allowed"

    def test_project_plan_field_types(self):
        """Test that ProjectPlan fields have correct types."""
        plan_data = {
            "tasks": [{"id": 1, "name": "Task"}],
            "risks": ["Risk"],
            "milestones": [{"id": 1, "name": "Milestone"}]
        }
        plan = schemas.ProjectPlan(**plan_data)

        assert isinstance(plan.tasks, list)
        assert isinstance(plan.risks, list)
        assert isinstance(plan.milestones, list)

        if plan.tasks:
            assert isinstance(plan.tasks[0], dict)
        if plan.risks:
            assert isinstance(plan.risks[0], str)
        if plan.milestones:
            assert isinstance(plan.milestones[0], dict)

    def test_project_plan_json_schema_example(self):
        """Test that ProjectPlan can validate against its JSON schema example."""
        example_data = {
            "tasks": [
                {"id": 1, "name": "Design API", "status": "done"},
                {"id": 2, "name": "Implement Backend", "status": "todo"}
            ],
            "risks": [
                "Budget overrun",
                "Technical complexity"
            ],
            "milestones": [
                {"id": 1, "name": "MVP Release", "completed": False}
            ]
        }
        plan = schemas.ProjectPlan(**example_data)
        assert len(plan.tasks) == 2
        assert len(plan.risks) == 2
        assert len(plan.milestones) == 1
        assert plan.tasks[0]["status"] == "done"
        assert plan.tasks[1]["status"] == "todo"

    def test_project_plan_from_dict_input(self):
        """Test ProjectPlan creation from dictionary input."""
        # This simulates how it would be used in the application
        plan_dict = {
            "tasks": [
                {"id": 1, "name": "Create frontend", "status": "todo"},
                {"id": 2, "name": "Setup database", "status": "completed"}
            ],
            "risks": ["Limited timeline"],
            "milestones": [{"id": 1, "name": "Backend Complete", "completed": True}]
        }

        # Should work without ValidationError
        plan = schemas.ProjectPlan(**plan_dict)
        assert plan.tasks[0]["name"] == "Create frontend"
        assert plan.risks[0] == "Limited timeline"


class TestProjectRecommendationRequest:
    """Test cases for ProjectRecommendationRequest schema."""

    def test_valid_recommendation_request(self):
        """Test creating a valid ProjectRecommendationRequest instance."""
        request_data = {
            "project_id": 42,
            "plan_json": '{"tasks": [{"id": 1, "name": "Design API", "status": "done"}], "risks": ["Budget overrun"], "milestones": []}',
            "user_question": "What are the next steps I should take for this project?"
        }
        request = schemas.ProjectRecommendationRequest(**request_data)
        assert request.project_id == 42
        assert request.plan_json == request_data["plan_json"]
        assert request.user_question == request_data["user_question"]

    def test_recommendation_request_missing_project_id(self):
        """Test ProjectRecommendationRequest missing project_id."""
        request_data = {
            "plan_json": '{"tasks": []}',
            "user_question": "What's next?"
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectRecommendationRequest(**request_data)
        assert "project_id" in str(exc_info.value).lower()

    def test_recommendation_request_negative_project_id(self):
        """Test ProjectRecommendationRequest with negative project_id."""
        request_data = {
            "project_id": -1,
            "plan_json": '{"tasks": []}',
            "user_question": "What's next?"
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectRecommendationRequest(**request_data)
        assert "project_id" in str(exc_info.value).lower()

    def test_recommendation_request_zero_project_id(self):
        """Test ProjectRecommendationRequest with zero project_id."""
        request_data = {
            "project_id": 0,
            "plan_json": '{"tasks": []}',
            "user_question": "What's next?"
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectRecommendationRequest(**request_data)
        assert "project_id" in str(exc_info.value).lower()

    def test_recommendation_request_missing_plan_json(self):
        """Test ProjectRecommendationRequest missing plan_json."""
        request_data = {
            "project_id": 42,
            "user_question": "What's next?"
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectRecommendationRequest(**request_data)
        assert "plan_json" in str(exc_info.value).lower()

    def test_recommendation_request_missing_user_question(self):
        """Test ProjectRecommendationRequest missing user_question."""
        request_data = {
            "project_id": 42,
            "plan_json": '{"tasks": []}'
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectRecommendationRequest(**request_data)
        assert "user_question" in str(exc_info.value).lower()

    def test_recommendation_request_empty_user_question(self):
        """Test ProjectRecommendationRequest with empty user_question."""
        request_data = {
            "project_id": 42,
            "plan_json": '{"tasks": []}',
            "user_question": ""
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectRecommendationRequest(**request_data)
        assert "user_question" in str(exc_info.value).lower()

    def test_recommendation_request_complex_plan_json(self):
        """Test ProjectRecommendationRequest with complex plan_json."""
        complex_plan = {
            "tasks": [
                {"id": 1, "name": "Design API", "status": "completed"},
                {"id": 2, "name": "Implement Backend", "status": "in_progress", "dependencies": [1]}
            ],
            "risks": ["Budget constraints", "Technical complexity"],
            "milestones": [
                {"id": 1, "name": "MVP Release", "completed": False, "due_date": "2024-03-01"}
            ]
        }
        import json
        request_data = {
            "project_id": 42,
            "plan_json": json.dumps(complex_plan),
            "user_question": "How should I prioritize these tasks?"
        }
        request = schemas.ProjectRecommendationRequest(**request_data)
        assert request.project_id == 42
        assert json.loads(request.plan_json) == complex_plan

    def test_recommendation_request_invalid_json(self):
        """Test ProjectRecommendationRequest with invalid JSON in plan_json."""
        request_data = {
            "project_id": 42,
            "plan_json": '{"tasks": [invalid json}',
            "user_question": "What's next?"
        }
        # This should pass validation since plan_json is just a string field
        request = schemas.ProjectRecommendationRequest(**request_data)
        assert request.plan_json == '{"tasks": [invalid json}'


class TestProjectRecommendationResponse:
    """Test cases for ProjectRecommendationResponse schema."""

    def test_valid_recommendation_response(self):
        """Test creating a valid ProjectRecommendationResponse instance."""
        response_data = {
            "project_id": 42,
            "message": "Recommendation generated successfully using RAG",
            "recommendation_markdown": "# Project Recommendations\n\nBased on your documents...",
            "sources_used": [1, 3, 5],
            "processing_time_ms": 1250
        }
        response = schemas.ProjectRecommendationResponse(**response_data)
        assert response.project_id == 42
        assert response.message == response_data["message"]
        assert response.recommendation_markdown == response_data["recommendation_markdown"]
        assert response.sources_used == [1, 3, 5]
        assert response.processing_time_ms == 1250

    def test_recommendation_response_minimal(self):
        """Test ProjectRecommendationResponse with minimal data (defaults)."""
        response_data = {
            "project_id": 42,
            "message": "Generated successfully"
        }
        response = schemas.ProjectRecommendationResponse(**response_data)
        assert response.project_id == 42
        assert response.message == "Generated successfully"
        assert response.recommendation_markdown == ""  # Default
        assert response.sources_used == []  # Default
        assert response.processing_time_ms == 0  # Default

    def test_recommendation_response_complex_markdown(self):
        """Test ProjectRecommendationResponse with complex markdown content."""
        complex_markdown = """
# Comprehensive Project Analysis

## Current Status Assessment
- ✅ **API Design**: Completed and documented
- 🔄 **Backend Implementation**: 60% complete
- ⏳ **Frontend Development**: Not started

## Risk Analysis
| Risk Category | Probability | Impact | Mitigation Strategy |
|---------------|-------------|--------|-------------------|
| Technical Debt | Medium | High | Regular code reviews |
| Timeline Delays | High | Medium | Agile sprints, buffer time |

## Detailed Recommendations
1. **Immediate Actions** (Next 2 weeks)
   - Complete backend API endpoints
   - Set up continuous integration pipeline

2. **Short-term Goals** (Next month)
   - Begin frontend development
   - Conduct security audit

3. **Long-term Strategy** (Next quarter)
   - Performance optimization
   - User acceptance testing

## Resource Allocation
```
Backend Development: 40%
Frontend Development: 35%
Testing & QA: 15%
Documentation: 10%
```
        """.strip()

        response_data = {
            "project_id": 42,
            "message": "Comprehensive analysis complete",
            "recommendation_markdown": complex_markdown,
            "sources_used": [1, 2, 3, 4, 5],
            "processing_time_ms": 2500
        }
        response = schemas.ProjectRecommendationResponse(**response_data)
        assert len(response.recommendation_markdown) > 500
        assert "## Current Status Assessment" in response.recommendation_markdown


class TestProjectUpdateRequest:
    """Test cases for ProjectUpdateRequest schema."""

    def test_valid_update_request(self):
        """Test creating a valid ProjectUpdateRequest instance."""
        request_data = {
            "project_id": 42,
            "updated_plan_json": '{"tasks": [{"id": 1, "name": "Design API", "status": "completed"}], "risks": [], "milestones": []}',
            "update_context": "Completed API design phase and starting backend implementation"
        }
        request = schemas.ProjectUpdateRequest(**request_data)
        assert request.project_id == 42
        assert request.updated_plan_json == request_data["updated_plan_json"]
        assert request.update_context == request_data["update_context"]

    def test_update_request_minimal(self):
        """Test ProjectUpdateRequest with minimal data (no update_context)."""
        request_data = {
            "project_id": 42,
            "updated_plan_json": '{"tasks": []}'
        }
        request = schemas.ProjectUpdateRequest(**request_data)
        assert request.project_id == 42
        assert request.update_context == ""  # Default

    def test_update_request_missing_project_id(self):
        """Test ProjectUpdateRequest missing project_id."""
        request_data = {
            "updated_plan_json": '{"tasks": []}'
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectUpdateRequest(**request_data)
        assert "project_id" in str(exc_info.value).lower()

    def test_update_request_negative_project_id(self):
        """Test ProjectUpdateRequest with negative project_id."""
        request_data = {
            "project_id": -1,
            "updated_plan_json": '{"tasks": []}'
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectUpdateRequest(**request_data)
        assert "project_id" in str(exc_info.value).lower()

    def test_update_request_missing_updated_plan_json(self):
        """Test ProjectUpdateRequest missing updated_plan_json."""
        request_data = {
            "project_id": 42
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectUpdateRequest(**request_data)
        assert "updated_plan_json" in str(exc_info.value).lower()

    def test_update_request_complex_updated_plan(self):
        """Test ProjectUpdateRequest with complex updated_plan_json."""
        complex_plan = {
            "tasks": [
                {
                    "id": 1,
                    "name": "Design API",
                    "status": "completed",
                    "completed_date": "2024-01-15",
                    "assignee": "Alice"
                },
                {
                    "id": 2,
                    "name": "Implement Backend",
                    "status": "in_progress",
                    "dependencies": [1],
                    "estimated_hours": 40
                }
            ],
            "risks": [
                "API integration complexity",
                "Third-party service limitations"
            ],
            "milestones": [
                {
                    "id": 1,
                    "name": "API Documentation Complete",
                    "completed": True,
                    "completion_date": "2024-01-15"
                }
            ]
        }
        import json
        request_data = {
            "project_id": 42,
            "updated_plan_json": json.dumps(complex_plan),
            "update_context": "Major progress update - API design completed, backend implementation started"
        }
        request = schemas.ProjectUpdateRequest(**request_data)
        assert json.loads(request.updated_plan_json) == complex_plan
        assert len(request.update_context) > 50


class TestProjectUpdateResponse:
    """Test cases for ProjectUpdateResponse schema."""

    def test_valid_update_response(self):
        """Test creating a valid ProjectUpdateResponse instance."""
        plan = schemas.ProjectPlan(tasks=[], risks=[], milestones=[])
        response_data = {
            "project_id": 42,
            "message": "Project updated successfully using RAG-enhanced context",
            "updated_plan": plan,
            "sources_used": [1, 3, 5],
            "processing_time_ms": 1850,
            "changes_made": ["Added new implementation task", "Updated timeline"]
        }
        response = schemas.ProjectUpdateResponse(**response_data)
        assert response.project_id == 42
        assert response.message == response_data["message"]
        assert response.updated_plan == plan
        assert response.sources_used == [1, 3, 5]
        assert response.processing_time_ms == 1850
        assert len(response.changes_made) == 2

    def test_update_response_minimal(self):
        """Test ProjectUpdateResponse with minimal data (defaults)."""
        plan = schemas.ProjectPlan(tasks=[], risks=[], milestones=[])
        response_data = {
            "project_id": 42,
            "message": "Updated successfully",
            "updated_plan": plan
        }
        response = schemas.ProjectUpdateResponse(**response_data)
        assert response.project_id == 42
        assert response.sources_used == []  # Default
        assert response.processing_time_ms == 0  # Default
        assert response.changes_made == []  # Default

    def test_update_response_complex_changes(self):
        """Test ProjectUpdateResponse with complex changes_made list."""
        plan = schemas.ProjectPlan(tasks=[], risks=[], milestones=[])
        response_data = {
            "project_id": 42,
            "message": "Comprehensive update completed",
            "updated_plan": plan,
            "changes_made": [
                "Added new task: 'Implement user authentication' with status 'todo'",
                "Updated task #2 status from 'in_progress' to 'completed'",
                "Added risk: 'API rate limiting may affect performance'",
                "Updated milestone due date from '2024-03-01' to '2024-03-15'",
                "Removed obsolete task: 'Legacy system maintenance'",
                "Added task dependencies between tasks #3 and #1",
                "Updated project timeline based on new estimates"
            ],
            "sources_used": [1, 2, 3, 4, 5, 6],
            "processing_time_ms": 3200
        }
        response = schemas.ProjectUpdateResponse(**response_data)
        assert len(response.changes_made) == 7
        assert "Added new task:" in response.changes_made[0]
        assert len(response.sources_used) == 6
        assert response.processing_time_ms == 3200


class TestProjectDocumentResponse:
    """Test cases for ProjectDocumentResponse schema."""

    def test_valid_document_response(self):
        """Test creating a valid ProjectDocumentResponse instance."""
        from datetime import datetime
        test_datetime = datetime(2024, 1, 15, 10, 30, 0)

        response_data = {
            "id": 1,
            "project_id": 42,
            "file_name": "project_requirements.pdf",
            "gemini_corpus_doc_id": "files/abc123def456",
            "uploaded_at": test_datetime
        }
        response = schemas.ProjectDocumentResponse(**response_data)
        assert response.id == 1
        assert response.project_id == 42
        assert response.file_name == "project_requirements.pdf"
        assert response.gemini_corpus_doc_id == "files/abc123def456"
        assert response.uploaded_at == test_datetime

    def test_document_response_missing_id(self):
        """Test ProjectDocumentResponse missing id."""
        response_data = {
            "project_id": 42,
            "file_name": "test.pdf",
            "gemini_corpus_doc_id": "files/test123",
            "uploaded_at": "2024-01-15T10:30:00"
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectDocumentResponse(**response_data)
        assert "id" in str(exc_info.value).lower()

    def test_document_response_missing_project_id(self):
        """Test ProjectDocumentResponse missing project_id."""
        response_data = {
            "id": 1,
            "file_name": "test.pdf",
            "gemini_corpus_doc_id": "files/test123",
            "uploaded_at": "2024-01-15T10:30:00"
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectDocumentResponse(**response_data)
        assert "project_id" in str(exc_info.value).lower()

    def test_document_response_missing_file_name(self):
        """Test ProjectDocumentResponse missing file_name."""
        response_data = {
            "id": 1,
            "project_id": 42,
            "gemini_corpus_doc_id": "files/test123",
            "uploaded_at": "2024-01-15T10:30:00"
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectDocumentResponse(**response_data)
        assert "file_name" in str(exc_info.value).lower()

    def test_document_response_empty_file_name(self):
        """Test ProjectDocumentResponse with empty file_name."""
        response_data = {
            "id": 1,
            "project_id": 42,
            "file_name": "",
            "gemini_corpus_doc_id": "files/test123",
            "uploaded_at": "2024-01-15T10:30:00"
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectDocumentResponse(**response_data)
        assert "file_name" in str(exc_info.value).lower()

    def test_document_response_long_file_name(self):
        """Test ProjectDocumentResponse with very long file_name."""
        long_name = "a" * 300  # Exceeds max_length of 255
        response_data = {
            "id": 1,
            "project_id": 42,
            "file_name": long_name,
            "gemini_corpus_doc_id": "files/test123",
            "uploaded_at": "2024-01-15T10:30:00"
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectDocumentResponse(**response_data)
        assert "file_name" in str(exc_info.value).lower()

    def test_document_response_various_file_types(self):
        """Test ProjectDocumentResponse with various file types."""
        file_types = [
            "requirements.pdf",
            "design.docx",
            "presentation.pptx",
            "spreadsheet.xlsx",
            "archive.zip",
            "code.py",
            "data.json",
            "config.xml",
            "image.png",
            "diagram.svg"
        ]

        for filename in file_types:
            response_data = {
                "id": 1,
                "project_id": 42,
                "file_name": filename,
                "gemini_corpus_doc_id": f"files/{filename}_id",
                "uploaded_at": "2024-01-15T10:30:00"
            }
            response = schemas.ProjectDocumentResponse(**response_data)
            assert response.file_name == filename

    def test_document_response_special_characters_in_filename(self):
        """Test ProjectDocumentResponse with special characters in filename."""
        special_filenames = [
            "project_v2.1_final.pdf",
            "test-file_name (copy).docx",
            "report [DRAFT].pdf",
            "data_export_2024-01-15.csv",
            "presentation @ team meeting.pptx"
        ]

        for filename in special_filenames:
            response_data = {
                "id": 1,
                "project_id": 42,
                "file_name": filename,
                "gemini_corpus_doc_id": "files/test123",
                "uploaded_at": "2024-01-15T10:30:00"
            }
            response = schemas.ProjectDocumentResponse(**response_data)
            assert response.file_name == filename

    def test_document_response_unicode_filename(self):
        """Test ProjectDocumentResponse with unicode characters in filename."""
        unicode_filenames = [
            "项目报告.pdf",
            "projet_final.docx",
            "проект_план.xlsx",
            "プロジェクト計画.pdf",
            "مشروع التقديم.pptx"
        ]

        for filename in unicode_filenames:
            response_data = {
                "id": 1,
                "project_id": 42,
                "file_name": filename,
                "gemini_corpus_doc_id": "files/test123",
                "uploaded_at": "2024-01-15T10:30:00"
            }
            response = schemas.ProjectDocumentResponse(**response_data)
            assert response.file_name == filename


class TestProjectDocumentList:
    """Test cases for ProjectDocumentList schema."""

    def test_valid_document_list(self):
        """Test creating a valid ProjectDocumentList instance."""
        from datetime import datetime
        test_datetime = datetime(2024, 1, 15, 10, 30, 0)

        doc1 = schemas.ProjectDocumentResponse(
            id=1,
            project_id=42,
            file_name="requirements.pdf",
            gemini_corpus_doc_id="files/abc123",
            uploaded_at=test_datetime
        )
        doc2 = schemas.ProjectDocumentResponse(
            id=2,
            project_id=42,
            file_name="design.docx",
            gemini_corpus_doc_id="files/def456",
            uploaded_at=test_datetime
        )

        list_data = {
            "documents": [doc1, doc2],
            "total_count": 2
        }
        doc_list = schemas.ProjectDocumentList(**list_data)
        assert len(doc_list.documents) == 2
        assert doc_list.total_count == 2
        assert doc_list.documents[0].file_name == "requirements.pdf"
        assert doc_list.documents[1].file_name == "design.docx"

    def test_document_list_empty(self):
        """Test ProjectDocumentList with empty documents list."""
        list_data = {
            "documents": [],
            "total_count": 0
        }
        doc_list = schemas.ProjectDocumentList(**list_data)
        assert doc_list.documents == []
        assert doc_list.total_count == 0

    def test_document_list_missing_total_count(self):
        """Test ProjectDocumentList missing total_count."""
        list_data = {
            "documents": []
        }
        with pytest.raises(ValidationError) as exc_info:
            schemas.ProjectDocumentList(**list_data)
        assert "total_count" in str(exc_info.value).lower()

    def test_document_list_single_document(self):
        """Test ProjectDocumentList with single document."""
        from datetime import datetime
        test_datetime = datetime(2024, 1, 15, 10, 30, 0)

        doc = schemas.ProjectDocumentResponse(
            id=1,
            project_id=42,
            file_name="single_document.pdf",
            gemini_corpus_doc_id="files/single123",
            uploaded_at=test_datetime
        )

        list_data = {
            "documents": [doc],
            "total_count": 1
        }
        doc_list = schemas.ProjectDocumentList(**list_data)
        assert len(doc_list.documents) == 1
        assert doc_list.total_count == 1
        assert doc_list.documents[0].file_name == "single_document.pdf"

    def test_document_list_mismatched_count(self):
        """Test ProjectDocumentList with mismatched total_count."""
        from datetime import datetime
        test_datetime = datetime(2024, 1, 15, 10, 30, 0)

        doc = schemas.ProjectDocumentResponse(
            id=1,
            project_id=42,
            file_name="test.pdf",
            gemini_corpus_doc_id="files/test123",
            uploaded_at=test_datetime
        )

        list_data = {
            "documents": [doc],
            "total_count": 5  # Mismatch - should be 1
        }
        # This should pass validation since schema doesn't enforce consistency
        doc_list = schemas.ProjectDocumentList(**list_data)
        assert len(doc_list.documents) == 1
        assert doc_list.total_count == 5

    def test_document_list_many_documents(self):
        """Test ProjectDocumentList with many documents."""
        from datetime import datetime
        test_datetime = datetime(2024, 1, 15, 10, 30, 0)

        documents = []
        for i in range(10):
            doc = schemas.ProjectDocumentResponse(
                id=i + 1,
                project_id=42,
                file_name=f"document_{i + 1}.pdf",
                gemini_corpus_doc_id=f"files/doc_{i + 1}_123",
                uploaded_at=test_datetime
            )
            documents.append(doc)

        list_data = {
            "documents": documents,
            "total_count": 10
        }
        doc_list = schemas.ProjectDocumentList(**list_data)
        assert len(doc_list.documents) == 10
        assert doc_list.total_count == 10
        assert doc_list.documents[0].file_name == "document_1.pdf"
        assert doc_list.documents[9].file_name == "document_10.pdf"