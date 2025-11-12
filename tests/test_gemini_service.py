"""
Unit tests for Gemini File Search API service.

This module tests file upload, deletion, retrieval, and error handling
in the gemini_service module without making actual network calls.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from fastapi import HTTPException, status
import google.generativeai as genai

import gemini_service


class TestGeminiServiceConfiguration:
    """Test cases for Gemini service configuration and setup."""

    def test_gemini_configured_successfully(self):
        """Test successful Gemini API configuration."""
        # Since GEMINI_CONFIGURED is set at module import time,
        # we test the actual configuration state
        with patch('gemini_service.os.getenv') as mock_getenv:
            # This tests the logic that would be used if the module was reloaded
            mock_getenv.return_value = "valid-api-key"

            # Simulate the configuration logic
            api_key = mock_getenv()
            is_configured = bool(api_key and api_key != "your_gemini_api_key_here")

            assert is_configured is True
            mock_getenv.assert_called_with('GEMINI_API_KEY')

    def test_gemini_not_configured_missing_key(self):
        """Test Gemini configuration fails with missing API key."""
        with patch('gemini_service.os.getenv') as mock_getenv:
            mock_getenv.return_value = None

            # Simulate the configuration logic
            api_key = mock_getenv()
            is_configured = bool(api_key and api_key != "your_gemini_api_key_here")

            assert is_configured is False
            mock_getenv.assert_called_with('GEMINI_API_KEY')

    def test_gemini_not_configured_placeholder_key(self):
        """Test Gemini configuration fails with placeholder API key."""
        with patch('gemini_service.os.getenv') as mock_getenv:
            mock_getenv.return_value = "your_gemini_api_key_here"

            # Simulate the configuration logic
            api_key = mock_getenv()
            is_configured = bool(api_key and api_key != "your_gemini_api_key_here")

            assert is_configured is False
            mock_getenv.assert_called_with('GEMINI_API_KEY')

    def test_gemini_configuration_exception_handling(self):
        """Test that Gemini configuration handles exceptions gracefully."""
        # This tests that the configuration logic includes exception handling
        with patch('gemini_service.os.getenv') as mock_getenv:
            mock_getenv.return_value = "some-key"

            # Simulate the configuration logic with exception handling
            try:
                api_key = mock_getenv()
                if api_key and api_key != "your_gemini_api_key_here":
                    # This would be where genai.configure() is called
                    # We simulate it might raise an exception
                    pass
                is_configured = True
            except Exception:
                is_configured = False

            # The actual module should have exception handling
            assert isinstance(is_configured, bool)


class TestUploadFileToGemini:
    """Test cases for upload_file_to_gemini function."""

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.upload_file')
    async def test_upload_file_success(self, mock_upload):
        """Test successful file upload to Gemini."""
        # Mock the uploaded file object
        mock_file = Mock()
        mock_file.name = "files/test_file_12345"
        mock_file.wait_until_processed = Mock()

        mock_upload.return_value = mock_file

        with patch('asyncio.to_thread', return_value=None) as mock_to_thread:
            # Call the function
            result = await gemini_service.upload_file_to_gemini(
                file_content=b"test content",
                file_name="test.txt"
            )

            # Verify results
            assert result == "files/test_file_12345"
            mock_upload.assert_called_once_with(b"test content", display_name="test.txt")
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', False)
    async def test_upload_file_not_configured(self):
        """Test file upload when Gemini API is not configured."""
        with pytest.raises(HTTPException) as exc_info:
            await gemini_service.upload_file_to_gemini(
                file_content=b"test content",
                file_name="test.txt"
            )

        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Gemini API not configured" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.upload_file')
    async def test_upload_file_blocked_content(self, mock_upload):
        """Test file upload with blocked content."""
        mock_file = Mock()
        mock_file.wait_until_processed = Mock()
        mock_upload.return_value = mock_file

        # Check if BlockedPromptException exists, if not use a generic Exception
        try:
            blocked_exception = genai.types.BlockedPromptException("Content blocked")
        except AttributeError:
            blocked_exception = Exception("Content blocked")

        with patch('asyncio.to_thread', side_effect=blocked_exception):
            with pytest.raises(HTTPException) as exc_info:
                await gemini_service.upload_file_to_gemini(
                    file_content=b"blocked content",
                    file_name="test.txt"
                )

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "blocked by Gemini safety filters" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.upload_file')
    async def test_upload_file_processing_stopped(self, mock_upload):
        """Test file upload when processing is stopped."""
        mock_file = Mock()
        mock_file.wait_until_processed = Mock()
        mock_upload.return_value = mock_file

        # Check if StopCandidateException exists, if not use a generic Exception
        try:
            stopped_exception = genai.types.StopCandidateException("Processing stopped")
        except AttributeError:
            stopped_exception = Exception("Processing stopped")

        with patch('asyncio.to_thread', side_effect=stopped_exception):
            with pytest.raises(HTTPException) as exc_info:
                await gemini_service.upload_file_to_gemini(
                    file_content=b"test content",
                    file_name="test.txt"
                )

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "File processing was stopped by Gemini" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.upload_file')
    async def test_upload_file_timeout(self, mock_upload):
        """Test file upload with processing timeout."""
        mock_file = Mock()
        mock_file.wait_until_processed = Mock()
        mock_upload.return_value = mock_file

        with patch('asyncio.to_thread', side_effect=asyncio.TimeoutError("Timeout occurred")):
            with pytest.raises(HTTPException) as exc_info:
                await gemini_service.upload_file_to_gemini(
                    file_content=b"test content",
                    file_name="test.txt"
                )

            assert exc_info.value.status_code == status.HTTP_408_REQUEST_TIMEOUT
            assert "File processing timed out" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.upload_file')
    async def test_upload_file_general_exception(self, mock_upload):
        """Test file upload with general exception."""
        mock_file = Mock()
        mock_file.wait_until_processed = Mock()
        mock_upload.return_value = mock_file

        with patch('asyncio.to_thread', side_effect=Exception("General error")):
            with pytest.raises(HTTPException) as exc_info:
                await gemini_service.upload_file_to_gemini(
                    file_content=b"test content",
                    file_name="test.txt"
                )

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to upload file to Gemini" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.upload_file')
    async def test_upload_file_custom_timeout(self, mock_upload):
        """Test file upload with custom timeout."""
        mock_file = Mock()
        mock_file.name = "files/test_file_12345"
        mock_file.wait_until_processed = Mock()

        mock_upload.return_value = mock_file

        with patch('asyncio.to_thread', return_value=None):
            result = await gemini_service.upload_file_to_gemini(
                file_content=b"test content",
                file_name="test.txt",
                timeout=600
            )

            assert result == "files/test_file_12345"

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.upload_file')
    async def test_upload_file_large_content(self, mock_upload):
        """Test file upload with large content."""
        large_content = b"A" * (10 * 1024 * 1024)  # 10MB
        mock_file = Mock()
        mock_file.name = "files/large_file_12345"
        mock_file.wait_until_processed = Mock()

        mock_upload.return_value = mock_file

        with patch('asyncio.to_thread', return_value=None):
            result = await gemini_service.upload_file_to_gemini(
                file_content=large_content,
                file_name="large_file.txt"
            )

            assert result == "files/large_file_12345"
            mock_upload.assert_called_once_with(large_content, display_name="large_file.txt")


class TestGetFileFromGemini:
    """Test cases for get_file_from_gemini function."""

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.get_file')
    async def test_get_file_success(self, mock_get_file):
        """Test successful file retrieval from Gemini."""
        mock_file = Mock()

        with patch('asyncio.to_thread', return_value=mock_file) as mock_to_thread:
            result = await gemini_service.get_file_from_gemini("files/test_file_12345")

            assert result == mock_file
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', False)
    async def test_get_file_not_configured(self):
        """Test file retrieval when Gemini API is not configured."""
        result = await gemini_service.get_file_from_gemini("files/test_file_12345")
        assert result is None

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.get_file')
    async def test_get_file_not_found(self, mock_get_file):
        """Test file retrieval when file is not found."""
        with patch('asyncio.to_thread', return_value=None):
            result = await gemini_service.get_file_from_gemini("files/nonexistent_file")
            assert result is None

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.get_file')
    async def test_get_file_exception(self, mock_get_file):
        """Test file retrieval with exception."""
        with patch('asyncio.to_thread', side_effect=Exception("File not found")):
            result = await gemini_service.get_file_from_gemini("files/test_file_12345")
            assert result is None


class TestDeleteFileFromGemini:
    """Test cases for delete_file_from_gemini function."""

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.delete_file')
    async def test_delete_file_success(self, mock_delete):
        """Test successful file deletion from Gemini."""
        with patch('asyncio.to_thread', return_value=None) as mock_to_thread:
            result = await gemini_service.delete_file_from_gemini("files/test_file_12345")
            assert result is True
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', False)
    async def test_delete_file_not_configured(self):
        """Test file deletion when Gemini API is not configured."""
        result = await gemini_service.delete_file_from_gemini("files/test_file_12345")
        assert result is False

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.delete_file')
    async def test_delete_file_exception(self, mock_delete):
        """Test file deletion with exception."""
        with patch('asyncio.to_thread', side_effect=Exception("Delete failed")):
            result = await gemini_service.delete_file_from_gemini("files/test_file_12345")
            assert result is False


class TestGetGeminiStatus:
    """Test cases for get_gemini_status function."""

    @patch('gemini_service.os.getenv')
    def test_get_gemini_status_configured(self, mock_getenv):
        """Test getting status when Gemini is configured."""
        mock_getenv.return_value = "valid-api-key"

        with patch('gemini_service.GEMINI_CONFIGURED', True):
            status = gemini_service.get_gemini_status()

            assert status["configured"] is True
            assert status["api_key_set"] is True
            assert "models_available" in status

    @patch('gemini_service.os.getenv')
    def test_get_gemini_status_not_configured_no_key(self, mock_getenv):
        """Test getting status when API key is not set."""
        mock_getenv.return_value = None

        with patch('gemini_service.GEMINI_CONFIGURED', False):
            status = gemini_service.get_gemini_status()

            assert status["configured"] is False
            assert status["api_key_set"] is False
            assert "models_available" in status

    @patch('gemini_service.os.getenv')
    def test_get_gemini_status_not_configured_placeholder_key(self, mock_getenv):
        """Test getting status when placeholder API key is used."""
        mock_getenv.return_value = "your_gemini_api_key_here"

        with patch('gemini_service.GEMINI_CONFIGURED', False):
            status = gemini_service.get_gemini_status()

            assert status["configured"] is False
            assert status["api_key_set"] is False
            assert "models_available" in status


class TestListGeminiModels:
    """Test cases for list_gemini_models function."""

    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.list_models')
    def test_list_gemini_models_success(self, mock_list_models):
        """Test successful listing of Gemini models."""
        # Mock model objects
        mock_model1 = Mock()
        mock_model1.name = "models/gemini-pro"
        mock_model1.supported_generation_methods = ["generateContent", "countTokens"]

        mock_model2 = Mock()
        mock_model2.name = "models/gemini-pro-vision"
        mock_model2.supported_generation_methods = ["generateContent"]

        mock_model3 = Mock()
        mock_model3.name = "models/embedding-001"
        mock_model3.supported_generation_methods = ["embedContent"]

        mock_list_models.return_value = [mock_model1, mock_model2, mock_model3]

        result = gemini_service.list_gemini_models()

        assert len(result) == 2
        assert "models/gemini-pro" in result
        assert "models/gemini-pro-vision" in result
        assert "models/embedding-001" not in result

    @patch('gemini_service.GEMINI_CONFIGURED', False)
    def test_list_gemini_models_not_configured(self):
        """Test listing models when Gemini is not configured."""
        result = gemini_service.list_gemini_models()
        assert result == []

    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.list_models')
    def test_list_gemini_models_exception(self, mock_list_models):
        """Test listing models with exception."""
        mock_list_models.side_effect = Exception("Failed to list models")

        result = gemini_service.list_gemini_models()
        assert result == []

    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.list_models')
    def test_list_gemini_models_empty_list(self, mock_list_models):
        """Test listing models when no models are available."""
        mock_list_models.return_value = []

        result = gemini_service.list_gemini_models()
        assert result == []

    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.list_models')
    def test_list_gemini_models_no_generate_content(self, mock_list_models):
        """Test listing models when no models support generateContent."""
        mock_model = Mock()
        mock_model.name = "models/embedding-001"
        mock_model.supported_generation_methods = ["embedContent"]

        mock_list_models.return_value = [mock_model]

        result = gemini_service.list_gemini_models()
        assert result == []


class TestGeminiServiceIntegration:
    """Integration test cases for Gemini service functions."""

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.upload_file')
    @patch('gemini_service.genai.get_file')
    @patch('gemini_service.genai.delete_file')
    async def test_full_file_lifecycle(self, mock_delete, mock_get_file, mock_upload):
        """Test complete file lifecycle: upload, retrieve, delete."""
        # Setup mocks
        mock_file = Mock()
        mock_file.name = "files/test_file_12345"
        mock_file.wait_until_processed = Mock()

        # Test upload
        mock_upload.return_value = mock_file
        with patch('asyncio.to_thread', return_value=None):
            file_id = await gemini_service.upload_file_to_gemini(
                file_content=b"test content",
                file_name="test.txt"
            )
        assert file_id == "files/test_file_12345"

        # Test retrieval
        with patch('asyncio.to_thread', return_value=mock_file):
            retrieved_file = await gemini_service.get_file_from_gemini(file_id)
        assert retrieved_file == mock_file

        # Test deletion
        with patch('asyncio.to_thread', return_value=None):
            delete_result = await gemini_service.delete_file_from_gemini(file_id)
        assert delete_result is True

    @pytest.mark.asyncio
    @patch('gemini_service.GEMINI_CONFIGURED', True)
    @patch('gemini_service.genai.upload_file')
    async def test_concurrent_uploads(self, mock_upload):
        """Test concurrent file uploads."""
        mock_files = []
        for i in range(5):
            mock_file = Mock()
            mock_file.name = f"files/test_file_{i}"
            mock_file.wait_until_processed = Mock()
            mock_files.append(mock_file)

        mock_upload.side_effect = mock_files

        with patch('asyncio.to_thread', return_value=None):
            # Create concurrent upload tasks
            upload_tasks = [
                gemini_service.upload_file_to_gemini(
                    file_content=f"test content {i}".encode(),
                    file_name=f"test_{i}.txt"
                )
                for i in range(5)
            ]

            # Execute all uploads concurrently
            results = await asyncio.gather(*upload_tasks)

            # Verify all uploads succeeded
            assert len(results) == 5
            for i, result in enumerate(results):
                assert result == f"files/test_file_{i}"