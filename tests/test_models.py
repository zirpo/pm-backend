"""
Unit tests for database models.

This module tests the SQLAlchemy models, field validations,
and database interactions at the model level.
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import Base
from models import Project


class TestProjectModel:
    """Test cases for the Project model."""

    def test_create_project_with_minimal_data(self, session):
        """Test creating a project with only required fields."""
        project = Project(name="Test Project")
        session.add(project)
        session.commit()
        session.refresh(project)

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.plan_json is None  # No default, should be None

    def test_create_project_with_plan_json(self, session):
        """Test creating a project with custom plan_json."""
        custom_plan = '{"tasks": [{"id": 1, "name": "Task 1"}], "risks": [], "milestones": []}'
        project = Project(
            name="Project with Plan",
            plan_json=custom_plan
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        assert project.name == "Project with Plan"
        assert project.plan_json == custom_plan

    def test_project_name_max_length(self, session):
        """Test project name length constraints."""
        # Test with very long name
        long_name = "A" * 255  # Assuming reasonable max length
        project = Project(name=long_name)
        session.add(project)
        session.commit()
        session.refresh(project)

        assert project.name == long_name

    def test_project_unique_names(self, session):
        """Test that project names can be duplicated (if not constrained)."""
        # Create first project
        project1 = Project(name="Duplicate Name")
        session.add(project1)
        session.commit()

        # Create second project with same name
        project2 = Project(name="Duplicate Name")
        session.add(project2)
        session.commit()
        session.refresh(project2)

        # Both should exist if names don't need to be unique
        assert project1.name == project2.name
        assert project1.id != project2.id

    def test_project_name_indexed(self, session):
        """Test that project name is properly indexed."""
        # This is more of a structural test - we can't directly test indexing
        # but we can create projects and query by name to ensure it works
        projects = [
            Project(name="Alpha Project"),
            Project(name="Beta Project"),
            Project(name="Gamma Project")
        ]

        for project in projects:
            session.add(project)
        session.commit()

        # Query by name to test index functionality
        found_project = session.query(Project).filter(Project.name == "Beta Project").first()
        assert found_project is not None
        assert found_project.name == "Beta Project"

    def test_plan_json_none_by_default(self, session):
        """Test that plan_json is None by default."""
        project = Project(name="Default Plan Test")
        session.add(project)
        session.commit()
        session.refresh(project)

        # Should be None since no default is provided
        assert project.plan_json is None

    def test_invalid_plan_json_handling(self, session):
        """Test handling of invalid JSON in plan_json field."""
        # SQLAlchemy will store invalid JSON as text since it's a Text field
        # The validation happens at application level
        invalid_json = '{"tasks": [invalid json]}'
        project = Project(
            name="Invalid JSON Project",
            plan_json=invalid_json
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        assert project.plan_json == invalid_json

    def test_project_to_dict_representation(self, session):
        """Test project object dictionary representation."""
        project = Project(
            name="Dict Test Project",
            plan_json='{"tasks": [], "risks": [], "milestones": []}'
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        project_dict = {
            'id': project.id,
            'name': project.name,
            'plan_json': project.plan_json
        }

        assert project_dict['id'] is not None
        assert project_dict['name'] == "Dict Test Project"
        assert project_dict['plan_json'] == '{"tasks": [], "risks": [], "milestones": []}'

    def test_update_project_name(self, session):
        """Test updating project name."""
        project = Project(name="Original Name")
        session.add(project)
        session.commit()

        # Update name
        project.name = "Updated Name"
        session.commit()
        session.refresh(project)

        assert project.name == "Updated Name"

    def test_update_plan_json(self, session):
        """Test updating plan_json."""
        project = Project(name="Plan Update Test")
        session.add(project)
        session.commit()

        # Update plan
        new_plan = '{"tasks": [{"id": 1, "name": "New Task"}], "risks": [], "milestones": []}'
        project.plan_json = new_plan
        session.commit()
        session.refresh(project)

        assert project.plan_json == new_plan

    def test_delete_project(self, session):
        """Test deleting a project."""
        project = Project(name="To Be Deleted")
        session.add(project)
        session.commit()
        project_id = project.id

        # Delete project
        session.delete(project)
        session.commit()

        # Verify deletion
        found_project = session.query(Project).filter(Project.id == project_id).first()
        assert found_project is None

    def test_multiple_projects_query(self, session):
        """Test querying multiple projects."""
        # Create multiple projects
        projects_data = [
            ("Project One", '{"tasks": [], "risks": [], "milestones": []}'),
            ("Project Two", '{"tasks": [{"id": 1}], "risks": [], "milestones": []}'),
            ("Project Three", '{"tasks": [], "risks": ["Risk 1"], "milestones": []}')
        ]

        for name, plan in projects_data:
            project = Project(name=name, plan_json=plan)
            session.add(project)
        session.commit()

        # Query all projects
        all_projects = session.query(Project).all()
        assert len(all_projects) >= 3

        # Query with filter
        filtered_projects = session.query(Project).filter(
            Project.name.like("Project %")
        ).all()
        assert len(filtered_projects) >= 3

    def test_project_with_empty_plan_json(self, session):
        """Test project with empty plan_json."""
        project = Project(
            name="Empty Plan",
            plan_json=''
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        assert project.plan_json == ''

    def test_project_with_null_plan_json(self, session):
        """Test project with None plan_json."""
        project = Project(
            name="Null Plan",
            plan_json=None
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        assert project.plan_json is None

    def test_project_string_representation(self, session):
        """Test the string representation of Project model."""
        project = Project(name="String Rep Test")
        session.add(project)
        session.commit()
        session.refresh(project)

        # Test that the object has a reasonable string representation
        str_repr = str(project)
        assert "String Rep Test" in str_repr or f"Project(id={project.id})" in str_repr

    def test_complex_plan_json_structure(self, session):
        """Test project with complex plan_json structure."""
        complex_plan = '''
        {
            "tasks": [
                {
                    "id": 1,
                    "name": "Design Database Schema",
                    "status": "completed",
                    "assignee": "Alice",
                    "priority": "high",
                    "estimated_hours": 8,
                    "dependencies": []
                },
                {
                    "id": 2,
                    "name": "Implement API Endpoints",
                    "status": "in_progress",
                    "assignee": "Bob",
                    "priority": "high",
                    "estimated_hours": 16,
                    "dependencies": [1]
                }
            ],
            "risks": [
                {
                    "id": 1,
                    "description": "Timeline may be affected by learning curve",
                    "probability": "medium",
                    "impact": "medium",
                    "mitigation": "Allocate extra time for research"
                }
            ],
            "milestones": [
                {
                    "id": 1,
                    "name": "API Design Complete",
                    "due_date": "2024-02-01",
                    "completed": true
                },
                {
                    "id": 2,
                    "name": "Beta Release",
                    "due_date": "2024-03-01",
                    "completed": false
                }
            ]
        }
        '''

        project = Project(
            name="Complex Project",
            plan_json=complex_plan.strip()
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        assert project.plan_json == complex_plan.strip()

        # Verify it's valid JSON
        import json
        parsed_plan = json.loads(project.plan_json)
        assert len(parsed_plan["tasks"]) == 2
        assert len(parsed_plan["risks"]) == 1
        assert len(parsed_plan["milestones"]) == 2