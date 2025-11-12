"""
Unit tests for Gemini RAG (Retrieval-Augmented Generation) service.

This module tests RAG context retrieval, response generation, and error handling
in the gemini_rag_service module without making actual network calls.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from datetime import datetime, timezone
import google.generativeai as genai

import gemini_rag_service
import models
import schemas


class TestInitializeGeminiModel:
    """Test cases for initialize_gemini_model function."""

    def test_initialize_function_exists(self):
        """Test that the initialize function exists."""
        assert hasattr(gemini_rag_service, 'initialize_gemini_model')
        assert callable(gemini_rag_service.initialize_gemini_model)

    def test_model_is_initialized(self):
        """Test that the model gets initialized during import."""
        # The model should be initialized when the module loads
        assert hasattr(gemini_rag_service, '_gemini_model')
        # It should be a real Gemini model or None based on configuration
        from google.generativeai import GenerativeModel
        assert isinstance(gemini_rag_service._gemini_model, (GenerativeModel, type(None)))


class TestGetRagContext:
    """Test cases for get_rag_context function."""

    @pytest.mark.asyncio
    async def test_get_rag_context_no_documents(self):
        """Test getting RAG context when no documents exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await gemini_rag_service.get_rag_context(mock_session, 1)

        assert result == ""

    @pytest.mark.asyncio
    async def test_get_rag_context_with_documents(self):
        """Test getting RAG context with multiple documents."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Create mock documents
        doc1 = Mock()
        doc1.file_name = "requirements.pdf"
        doc1.gemini_corpus_doc_id = "files/doc1"
        doc1.uploaded_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        doc2 = Mock()
        doc2.file_name = "design.docx"
        doc2.gemini_corpus_doc_id = "files/doc2"
        doc2.uploaded_at = datetime(2024, 1, 16, 14, 20, 0, tzinfo=timezone.utc)

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [doc1, doc2]
        mock_session.execute.return_value = mock_result

        # Mock Gemini file retrieval
        mock_file1 = Mock()
        mock_file1.state = 'ACTIVE'
        mock_file1.text_content = "Requirements document content"

        mock_file2 = Mock()
        mock_file2.state = 'ACTIVE'
        mock_file2.text_content = "Design document content"

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = [mock_file1, mock_file2]

            result = await gemini_rag_service.get_rag_context(mock_session, 1, max_context_length=10000)

            assert "requirements.pdf" in result
            assert "design.docx" in result
            assert "Requirements document content" in result
            assert "Design document content" in result

    @pytest.mark.asyncio
    async def test_get_rag_context_file_not_active(self):
        """Test getting RAG context with non-active files."""
        mock_session = AsyncMock(spec=AsyncSession)

        doc1 = Mock()
        doc1.file_name = "requirements.pdf"
        doc1.gemini_corpus_doc_id = "files/doc1"
        doc1.uploaded_at = datetime.now()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [doc1]
        mock_session.execute.return_value = mock_result

        # Mock inactive file
        mock_file1 = Mock()
        mock_file1.state = 'PROCESSING'

        with patch('asyncio.to_thread', return_value=mock_file1):
            result = await gemini_rag_service.get_rag_context(mock_session, 1)

            assert result == ""

    @pytest.mark.asyncio
    async def test_get_rag_context_file_not_found(self):
        """Test getting RAG context when file is not found."""
        mock_session = AsyncMock(spec=AsyncSession)

        doc1 = Mock()
        doc1.file_name = "requirements.pdf"
        doc1.gemini_corpus_doc_id = "files/doc1"
        doc1.uploaded_at = datetime.now()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [doc1]
        mock_session.execute.return_value = mock_result

        with patch('asyncio.to_thread', return_value=None):
            result = await gemini_rag_service.get_rag_context(mock_session, 1)

            assert result == ""

    @pytest.mark.asyncio
    async def test_get_rag_context_content_too_large(self):
        """Test getting RAG context with content exceeding max length."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Create documents with large content
        docs = []
        for i in range(5):
            doc = Mock()
            doc.file_name = f"large_doc_{i}.txt"
            doc.gemini_corpus_doc_id = f"files/doc{i}"
            doc.uploaded_at = datetime.now()
            docs.append(doc)

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = docs
        mock_session.execute.return_value = mock_result

        # Mock large content files
        large_content = "A" * 10000  # 10KB per file
        mock_files = []
        for i in range(5):
            mock_file = Mock()
            mock_file.state = 'ACTIVE'
            mock_file.text_content = large_content
            mock_files.append(mock_file)

        with patch('asyncio.to_thread', side_effect=mock_files):
            result = await gemini_rag_service.get_rag_context(mock_session, 1, max_context_length=15000)

            # Should include some documents but stop before exceeding limit
            assert len(result) > 0
            assert "large_doc_0.txt" in result

    @pytest.mark.asyncio
    async def test_get_rag_context_database_exception(self):
        """Test getting RAG context with database exception."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = Exception("Database error")

        result = await gemini_rag_service.get_rag_context(mock_session, 1)

        assert result == ""

    @pytest.mark.asyncio
    async def test_get_rag_context_gemini_exception(self):
        """Test getting RAG context with Gemini API exception."""
        mock_session = AsyncMock(spec=AsyncSession)

        doc1 = Mock()
        doc1.file_name = "requirements.pdf"
        doc1.gemini_corpus_doc_id = "files/doc1"
        doc1.uploaded_at = datetime.now()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [doc1]
        mock_session.execute.return_value = mock_result

        with patch('asyncio.to_thread', side_effect=Exception("Gemini error")):
            result = await gemini_rag_service.get_rag_context(mock_session, 1)

            assert result == ""


class TestGetGeminiRagResponse:
    """Test cases for get_gemini_rag_response function."""

    @pytest.mark.asyncio
    @patch('gemini_rag_service._gemini_model')
    @patch('gemini_rag_service.get_rag_context')
    async def test_get_rag_response_success(self, mock_get_context, mock_model):
        """Test successful RAG response generation."""
        mock_get_context.return_value = "Document context content"

        mock_response = Mock()
        mock_response.text = "Generated response based on context"
        mock_model.generate_content.return_value = mock_response

        mock_session = AsyncMock(spec=AsyncSession)

        result = await gemini_rag_service.get_gemini_rag_response(
            mock_session, 1, "User question", "System prompt"
        )

        assert result == "Generated response based on context"
        mock_get_context.assert_called_once_with(mock_session, 1)
        mock_model.generate_content.assert_called_once()

    @pytest.mark.asyncio
    @patch('gemini_rag_service._gemini_model', None)
    @patch('gemini_rag_service.get_rag_context')
    async def test_get_rag_response_model_not_initialized(self, mock_get_context):
        """Test RAG response when model is not initialized."""
        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(HTTPException) as exc_info:
            await gemini_rag_service.get_gemini_rag_response(
                mock_session, 1, "User question"
            )

        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "RAG service not available" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('gemini_rag_service._gemini_model')
    @patch('gemini_rag_service.get_rag_context')
    async def test_get_rag_response_no_context(self, mock_get_context, mock_model):
        """Test RAG response when no context is available."""
        mock_get_context.return_value = ""

        mock_response = Mock()
        mock_response.text = "Response with no context"
        mock_model.generate_content.return_value = mock_response

        mock_session = AsyncMock(spec=AsyncSession)

        result = await gemini_rag_service.get_gemini_rag_response(
            mock_session, 1, "User question"
        )

        assert result == "Response with no context"
        mock_get_context.assert_called_once_with(mock_session, 1)

    @pytest.mark.asyncio
    @patch('gemini_rag_service._gemini_model')
    @patch('gemini_rag_service.get_rag_context')
    async def test_get_rag_response_without_system_prompt(self, mock_get_context, mock_model):
        """Test RAG response without system prompt."""
        mock_get_context.return_value = "Document context"

        mock_response = Mock()
        mock_response.text = "Generated response"
        mock_model.generate_content.return_value = mock_response

        mock_session = AsyncMock(spec=AsyncSession)

        result = await gemini_rag_service.get_gemini_rag_response(
            mock_session, 1, "User question"
        )

        assert result == "Generated response"
        # Verify that system prompt was not included
        call_args = mock_model.generate_content.call_args[0][0]
        assert "System:" not in call_args

    @pytest.mark.asyncio
    @patch('gemini_rag_service._gemini_model')
    @patch('gemini_rag_service.get_rag_context')
    async def test_get_rag_response_with_system_prompt(self, mock_get_context, mock_model):
        """Test RAG response with system prompt."""
        mock_get_context.return_value = "Document context"

        mock_response = Mock()
        mock_response.text = "Generated response"
        mock_model.generate_content.return_value = mock_response

        mock_session = AsyncMock(spec=AsyncSession)

        result = await gemini_rag_service.get_gemini_rag_response(
            mock_session, 1, "User question", "System instructions"
        )

        assert result == "Generated response"
        # Verify that system prompt was included
        call_args = mock_model.generate_content.call_args[0][0]
        assert "System: System instructions" in call_args

    @pytest.mark.asyncio
    @patch('gemini_rag_service._gemini_model')
    @patch('gemini_rag_service.get_rag_context')
    async def test_get_rag_response_generation_exception(self, mock_get_context, mock_model):
        """Test RAG response with generation exception."""
        mock_get_context.return_value = "Document context"
        mock_model.generate_content.side_effect = Exception("Generation failed")

        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(HTTPException) as exc_info:
            await gemini_rag_service.get_gemini_rag_response(
                mock_session, 1, "User question"
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error generating RAG response" in str(exc_info.value.detail)


class TestRagRecommendation:
    """Test cases for rag_recommendation function."""

    @pytest.mark.asyncio
    @patch('gemini_rag_service.get_gemini_rag_response')
    async def test_rag_recommendation_success(self, mock_get_response):
        """Test successful RAG recommendation generation."""
        mock_get_response.return_value = "# Recommendations\n\nBased on your project..."

        mock_session = AsyncMock(spec=AsyncSession)

        result = await gemini_rag_service.rag_recommendation(
            mock_session, 1, "What should I do next?", '{"tasks": []}'
        )

        assert "# Recommendations" in result
        assert "Based on your project" in result
        mock_get_response.assert_called_once()

    @pytest.mark.asyncio
    @patch('gemini_rag_service.get_gemini_rag_response')
    async def test_rag_recommendation_with_complex_plan(self, mock_get_response):
        """Test RAG recommendation with complex project plan."""
        mock_get_response.return_value = "Complex recommendation"

        complex_plan = {
            "tasks": [
                {"id": 1, "name": "Design API", "status": "completed"},
                {"id": 2, "name": "Implement Backend", "status": "in_progress"}
            ],
            "risks": ["Technical complexity"],
            "milestones": [{"id": 1, "name": "MVP", "completed": False}]
        }

        mock_session = AsyncMock(spec=AsyncSession)

        result = await gemini_rag_service.rag_recommendation(
            mock_session, 1, "How should I prioritize?", json.dumps(complex_plan)
        )

        assert result == "Complex recommendation"
        # Verify the complex plan was included in the base prompt
        call_args = mock_get_response.call_args[1]
        base_prompt = call_args['base_prompt']
        assert "Design API" in base_prompt
        assert "Technical complexity" in base_prompt

    @pytest.mark.asyncio
    @patch('gemini_rag_service.get_gemini_rag_response')
    async def test_rag_recommendation_exception(self, mock_get_response):
        """Test RAG recommendation with exception."""
        mock_get_response.side_effect = HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG service error"
        )

        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(HTTPException) as exc_info:
            await gemini_rag_service.rag_recommendation(
                mock_session, 1, "What's next?", '{"tasks": []}'
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestRagUpdate:
    """Test cases for rag_update function."""

    @pytest.mark.asyncio
    @patch('gemini_rag_service.get_gemini_rag_response')
    async def test_rag_update_success(self, mock_get_response):
        """Test successful RAG update generation."""
        mock_get_response.return_value = "# Update Analysis\n\nYour changes look good..."

        mock_session = AsyncMock(spec=AsyncSession)

        result = await gemini_rag_service.rag_update(
            mock_session, 1, '{"tasks": []}', "Added new features"
        )

        assert "# Update Analysis" in result
        assert "Your changes look good" in result
        mock_get_response.assert_called_once()

    @pytest.mark.asyncio
    @patch('gemini_rag_service.get_gemini_rag_response')
    async def test_rag_update_with_context(self, mock_get_response):
        """Test RAG update with detailed context."""
        mock_get_response.return_value = "Detailed update analysis"

        mock_session = AsyncMock(spec=AsyncSession)

        result = await gemini_rag_service.rag_update(
            mock_session, 1,
            '{"tasks": [{"id": 1, "name": "New task"}]}',
            "Major refactoring completed - removed legacy code and improved performance"
        )

        assert result == "Detailed update analysis"
        # Verify context was included
        call_args = mock_get_response.call_args[1]
        base_prompt = call_args['base_prompt']
        assert "Major refactoring completed" in base_prompt
        assert "New task" in base_prompt

    @pytest.mark.asyncio
    @patch('gemini_rag_service.get_gemini_rag_response')
    async def test_rag_update_exception(self, mock_get_response):
        """Test RAG update with exception."""
        mock_get_response.side_effect = HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Update service error"
        )

        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(HTTPException) as exc_info:
            await gemini_rag_service.rag_update(
                mock_session, 1, '{"tasks": []}', "Update context"
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestRagServiceIntegration:
    """Integration test cases for RAG service functions."""

    @pytest.mark.asyncio
    @patch('gemini_rag_service.get_gemini_rag_response')
    @patch('gemini_rag_service.get_rag_context')
    async def test_full_rag_workflow(self, mock_get_context, mock_get_response):
        """Test complete RAG workflow from context to response."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock document context
        mock_get_context.return_value = "Document: project_requirements.pdf\nContent: User authentication required"

        # Mock model response
        mock_response = Mock()
        mock_response.text = "# Analysis\n\nBased on the requirements, you should implement user authentication first."
        mock_get_response.return_value = mock_response.text

        with patch('gemini_rag_service._gemini_model') as mock_model:
            mock_model.generate_content.return_value = mock_response

            # Test recommendation
            recommendation = await gemini_rag_service.rag_recommendation(
                mock_session, 1, "What's the priority?", '{"tasks": []}'
            )

            assert "implement user authentication first" in recommendation.lower()
            mock_get_context.assert_called_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_rag_service_model_initialization(self):
        """Test that the RAG service initializes model on import."""
        # The model should be initialized when the module is imported
        assert hasattr(gemini_rag_service, '_gemini_model')
        # It should be a real Gemini model or None based on configuration
        from google.generativeai import GenerativeModel
        assert isinstance(gemini_rag_service._gemini_model, (GenerativeModel, type(None)))

    @pytest.mark.asyncio
    @patch('gemini_rag_service._gemini_model')
    async def test_concurrent_rag_requests(self, mock_model):
        """Test handling concurrent RAG requests."""
        mock_response = Mock()
        mock_response.text = "Response for request"
        mock_model.generate_content.return_value = mock_response

        mock_session = AsyncMock(spec=AsyncSession)

        with patch('gemini_rag_service.get_rag_context', return_value="Context"):
            # Create concurrent RAG requests
            rag_tasks = [
                gemini_rag_service.get_gemini_rag_response(
                    mock_session, 1, f"Question {i}"
                )
                for i in range(3)
            ]

            # Execute all requests concurrently
            results = await asyncio.gather(*rag_tasks)

            # Verify all requests succeeded
            assert len(results) == 3
            for result in results:
                assert result == "Response for request"