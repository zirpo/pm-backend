"""
Unit tests for LLM mock functions
"""
import pytest
from llm_agents import mock_state_updater_llm, mock_recommender_llm


class TestMockStateUpdaterLLM:
    """Test cases for mock_state_updater_llm function"""

    def test_add_task_to_empty_plan(self):
        """Test adding a task to an empty plan"""
        empty_plan = {"tasks": [], "risks": [], "milestones": []}
        update_text = "add task Buy groceries"

        result = mock_state_updater_llm(empty_plan, update_text)

        # Verify return type and structure
        assert isinstance(result, dict)
        assert "tasks" in result
        assert len(result["tasks"]) == 1

        # Verify task structure
        task = result["tasks"][0]
        assert task["id"] == 1
        assert task["name"] == "Buy groceries"
        assert task["status"] == "todo"

    def test_add_task_with_new_task_keyword(self):
        """Test adding a task using 'new task' keyword"""
        empty_plan = {"tasks": [], "risks": [], "milestones": []}
        update_text = "new task Clean house"

        result = mock_state_updater_llm(empty_plan, update_text)

        assert isinstance(result, dict)
        assert len(result["tasks"]) == 1
        task = result["tasks"][0]
        assert task["name"] == "Clean house"
        assert task["status"] == "todo"

    def test_add_task_to_existing_plan(self):
        """Test adding a task to a plan that already has tasks"""
        existing_plan = {
            "tasks": [{"id": 1, "name": "Buy groceries", "status": "todo"}],
            "risks": [],
            "milestones": []
        }
        update_text = "add task Clean house"

        result = mock_state_updater_llm(existing_plan, update_text)

        assert len(result["tasks"]) == 2
        new_task = result["tasks"][1]
        assert new_task["id"] == 2
        assert new_task["name"] == "Clean house"
        assert new_task["status"] == "todo"

    def test_update_task_status(self):
        """Test updating an existing task's status"""
        plan_with_task = {
            "tasks": [{"id": 1, "name": "Buy groceries", "status": "todo"}],
            "risks": [],
            "milestones": []
        }
        update_text = "update task 1 status to done"

        result = mock_state_updater_llm(plan_with_task, update_text)

        assert len(result["tasks"]) == 1
        task = result["tasks"][0]
        assert task["id"] == 1
        assert task["status"] == "done"

    def test_no_matching_update_text(self):
        """Test that non-matching update text doesn't modify the plan"""
        original_plan = {
            "tasks": [{"id": 1, "name": "Buy groceries", "status": "todo"}],
            "risks": [],
            "milestones": []
        }
        update_text = "some random text that doesn't match patterns"

        result = mock_state_updater_llm(original_plan, update_text)

        # Plan should remain unchanged
        assert result == original_plan

    def test_duplicate_task_prevention(self):
        """Test that duplicate tasks are not added"""
        plan_with_existing_task = {
            "tasks": [{"id": 1, "name": "Buy groceries", "status": "todo"}],
            "risks": [],
            "milestones": []
        }
        update_text = "add task Buy groceries"

        result = mock_state_updater_llm(plan_with_existing_task, update_text)

        # Should not add duplicate task
        assert len(result["tasks"]) == 1


class TestMockRecommenderLLM:
    """Test cases for mock_recommender_llm function"""

    def test_next_steps_with_todo_tasks(self):
        """Test next steps question with TODO tasks"""
        plan_with_tasks = {
            "tasks": [
                {"id": 1, "name": "Buy groceries", "status": "todo"},
                {"id": 2, "name": "Clean house", "status": "done"}
            ],
            "risks": [],
            "milestones": []
        }
        question = "What are the next steps?"

        result = mock_recommender_llm(plan_with_tasks, question)

        # Verify return type
        assert isinstance(result, str)

        # Verify content contains expected elements
        assert "Project Analysis" in result
        assert "Buy groceries" in result
        assert "Clean house" not in result  # Should not include done tasks
        assert "Suggested next steps" in result

    def test_next_steps_with_all_done_tasks(self):
        """Test next steps question when all tasks are done"""
        plan_with_done_tasks = {
            "tasks": [
                {"id": 1, "name": "Buy groceries", "status": "done"},
                {"id": 2, "name": "Clean house", "status": "done"}
            ],
            "risks": [],
            "milestones": []
        }
        question = "whats next"

        result = mock_recommender_llm(plan_with_done_tasks, question)

        assert isinstance(result, str)
        assert "No outstanding tasks found" in result

    def test_risks_question_with_risks(self):
        """Test risks question when risks are documented"""
        plan_with_risks = {
            "tasks": [{"id": 1, "name": "Buy groceries", "status": "todo"}],
            "risks": ["Budget overrun", "Schedule delay"],
            "milestones": []
        }
        question = "What are the risks?"

        result = mock_recommender_llm(plan_with_risks, question)

        assert isinstance(result, str)
        assert "Project Analysis" in result
        assert "Budget overrun" in result
        assert "Schedule delay" in result
        assert "Identified Risks" in result

    def test_risks_question_with_no_risks(self):
        """Test risks question when no risks are documented"""
        plan_without_risks = {
            "tasks": [{"id": 1, "name": "Buy groceries", "status": "todo"}],
            "risks": [],
            "milestones": []
        }
        question = "What are the risks?"

        result = mock_recommender_llm(plan_without_risks, question)

        assert isinstance(result, str)
        assert "No specific risks are currently documented" in result

    def test_general_question(self):
        """Test a general question that doesn't match specific patterns"""
        plan = {
            "tasks": [{"id": 1, "name": "Buy groceries", "status": "todo"}],
            "risks": [],
            "milestones": []
        }
        question = "How is the project going?"

        result = mock_recommender_llm(plan, question)

        assert isinstance(result, str)
        assert "Project Analysis" in result
        assert "1 tasks" in result  # Should mention task count
        assert "mock recommendation" in result  # Should include disclaimer

    def test_empty_plan(self):
        """Test with an empty plan"""
        empty_plan = {"tasks": [], "risks": [], "milestones": []}
        question = "What are the next steps?"

        result = mock_recommender_llm(empty_plan, question)

        assert isinstance(result, str)
        assert "0 tasks" in result
        assert "No outstanding tasks found" in result


if __name__ == "__main__":
    pytest.main([__file__])