"""
Integration tests for Production DeepSeek LLM Integration
Tests cover error handling, API integration, and fallback behavior.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
import llm_agents


class TestProductionLLMIntegration:
    """Test production LLM integration with DeepSeek API"""

    def test_api_key_validation_on_import(self):
        """Test that missing API key raises ValueError on import"""
        # This test verifies the import-time validation
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': ''}, clear=True):
            # Remove the key from environment and reload the module
            import importlib
            import llm_agents

            # Clear cached module
            if 'llm_agents' in importlib.sys.modules:
                del importlib.sys.modules['llm_agents']

            # Should raise ValueError when importing without API key
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY environment variable not set"):
                importlib.import_module('llm_agents')

    def test_state_updater_llm_with_mock_api_success(self):
        """Test state_updater_llm with successful API response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "tasks": [{"id": 1, "name": "New Task", "status": "todo"}],
            "risks": [],
            "milestones": []
        })

        with patch('llm_agents.call_deepseek_llm', return_value=mock_response.choices[0].message.content):
            current_plan = {"tasks": [], "risks": [], "milestones": []}
            update_text = "add task New Task"

            result = llm_agents.state_updater_llm(current_plan, update_text)

            assert isinstance(result, dict)
            assert "tasks" in result
            assert "risks" in result
            assert "milestones" in result
            assert len(result["tasks"]) == 1
            assert result["tasks"][0]["name"] == "New Task"

    def test_state_updater_llm_with_invalid_json_response(self):
        """Test state_updater_llm handles invalid JSON response gracefully"""
        invalid_json = "This is not valid JSON {{ invalid"

        with patch('llm_agents.call_deepseek_llm', return_value=invalid_json):
            current_plan = {"tasks": [], "risks": [], "milestones": []}
            update_text = "add task Test"

            with pytest.raises(ValueError, match="LLM returned invalid JSON"):
                llm_agents.state_updater_llm(current_plan, update_text)

    def test_state_updater_llm_with_non_dict_response(self):
        """Test state_updater_llm handles non-dictionary JSON response"""
        array_response = json.dumps(["task1", "task2"])

        with patch('llm_agents.call_deepseek_llm', return_value=array_response):
            current_plan = {"tasks": [], "risks": [], "milestones": []}
            update_text = "add task Test"

            with pytest.raises(ValueError, match="LLM returned non-dictionary JSON"):
                llm_agents.state_updater_llm(current_plan, update_text)

    def test_recommender_llm_with_mock_api_success(self):
        """Test recommender_llm with successful API response"""
        mock_markdown = """# Project Analysis

Based on your current plan, here are the recommendations:

## Next Steps
- Complete task 1
- Review project risks

*This is a detailed analysis.*"""

        with patch('llm_agents.call_deepseek_llm', return_value=mock_markdown):
            current_plan = {"tasks": [{"id": 1, "name": "Test Task", "status": "todo"}], "risks": [], "milestones": []}
            user_question = "What are the next steps?"

            result = llm_agents.recommender_llm(current_plan, user_question)

            assert isinstance(result, str)
            assert "Project Analysis" in result
            assert "Next Steps" in result

    def test_call_deepseek_llm_api_error_handling(self):
        """Test call_deepseek_llm handles API errors gracefully"""
        api_error = Exception("Authentication failed")

        with patch('llm_agents.client.chat.completions.create', side_effect=api_error):
            messages = [{"role": "user", "content": "test"}]

            with pytest.raises(RuntimeError, match="DeepSeek LLM call failed"):
                llm_agents.call_deepseek_llm(messages)

    def test_call_deepseek_llm_retry_logic_for_transient_errors(self):
        """Test call_deepseek_llm implements retry logic for transient errors"""
        # First call fails with rate limit, second succeeds
        transient_error = Exception("Rate limit exceeded")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success response"

        with patch('llm_agents.client.chat.completions.create') as mock_create:
            mock_create.side_effect = [transient_error, mock_response]

            messages = [{"role": "user", "content": "test"}]

            with patch('time.sleep'):  # Mock sleep to speed up test
                result = llm_agents.call_deepseek_llm(messages)

            assert result == "Success response"
            assert mock_create.call_count == 2  # Should retry once

    def test_call_deepseek_llm_no_retry_for_non_transient_errors(self):
        """Test call_deepseek_llm doesn't retry non-transient errors"""
        non_transient_error = Exception("Invalid API key")

        with patch('llm_agents.client.chat.completions.create', side_effect=non_transient_error):
            messages = [{"role": "user", "content": "test"}]

            with pytest.raises(RuntimeError, match="DeepSeek LLM call failed"):
                llm_agents.call_deepseek_llm(messages)

    def test_state_updater_llm_ensures_required_keys(self):
        """Test state_updater_llm ensures required keys in response"""
        # Response missing required keys
        incomplete_response = json.dumps({"tasks": []})

        with patch('llm_agents.call_deepseek_llm', return_value=incomplete_response):
            current_plan = {"tasks": [], "risks": ["budget issues"], "milestones": []}
            update_text = "update task"

            result = llm_agents.state_updater_llm(current_plan, update_text)

            # Should add missing keys from current_plan
            assert "risks" in result
            assert "milestones" in result
            assert result["risks"] == ["budget issues"]


class TestProductionLLMEndpoints:
    """Test FastAPI endpoints with production LLM integration"""

    def test_update_endpoint_with_invalid_api_key(self, client):
        """Test update endpoint returns 500 when LLM API key is invalid"""
        # Create a project first
        project_data = {"name": "Test Project"}
        create_response = client.post("/project/create", json=project_data)
        project_id = create_response.json()["id"]

        # Try to update with invalid API key (should fail gracefully)
        update_data = {"project_id": project_id, "update_text": "add task Test task"}
        response = client.post("/project/update", json=update_data)

        assert response.status_code == 500
        assert "LLM State Update failed" in response.json()["detail"]

    def test_recommend_endpoint_with_invalid_api_key(self, client):
        """Test recommend endpoint returns 500 when LLM API key is invalid"""
        # Create a project first
        project_data = {"name": "Test Project"}
        create_response = client.post("/project/create", json=project_data)
        project_id = create_response.json()["id"]

        # Try to get recommendation with invalid API key (should fail gracefully)
        recommend_data = {"project_id": project_id, "user_question": "What are the next steps?"}
        response = client.post("/project/recommend", json=recommend_data)

        assert response.status_code == 500
        assert "LLM Recommendation failed" in response.json()["detail"]

    def test_error_message_contains_api_authentication_details(self, client):
        """Test that API authentication errors are properly propagated"""
        # Create a project
        project_data = {"name": "Test Project"}
        create_response = client.post("/project/create", json=project_data)
        project_id = create_response.json()["id"]

        # Try update to trigger API call
        update_data = {"project_id": project_id, "update_text": "add task Test"}
        response = client.post("/project/update", json=update_data)

        error_detail = response.json()["detail"]
        # Should contain information about the authentication failure
        assert "LLM State Update failed" in error_detail
        assert "Authentication" in error_detail or "api key" in error_detail.lower()


if __name__ == "__main__":
    pytest.main([__file__])