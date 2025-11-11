"""
Gemini File Search API service for document upload and management.
This module handles the integration with Google's Generative AI for file storage and retrieval.
"""
import os
import asyncio
from typing import Optional
import google.generativeai as genai
from fastapi import HTTPException, status
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
try:
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if gemini_api_key and gemini_api_key != "your_gemini_api_key_here":
        genai.configure(api_key=gemini_api_key)
        GEMINI_CONFIGURED = True
        print("✅ Gemini API configured successfully")
    else:
        GEMINI_CONFIGURED = False
        print("⚠️  Gemini API key not configured. Set GEMINI_API_KEY in .env file")
except Exception as e:
    GEMINI_CONFIGURED = False
    print(f"❌ Error configuring Gemini API: {e}")


async def upload_file_to_gemini(file_content: bytes, file_name: str, timeout: int = 300) -> str:
    """
    Upload a file to Gemini File Search API and wait for processing.

    Args:
        file_content: The binary content of the file to upload
        file_name: The original filename for display purposes
        timeout: Maximum time to wait for file processing (default: 5 minutes)

    Returns:
        str: The Gemini file ID (format: "files/FILE_ID")

    Raises:
        HTTPException: If upload fails or processing times out
    """
    if not GEMINI_CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API not configured. Please set GEMINI_API_KEY."
        )

    try:
        print(f"📤 Uploading file '{file_name}' to Gemini...")

        # Upload file to Gemini
        uploaded_file = genai.upload_file(
            file_content,
            display_name=file_name
        )

        print(f"✅ File uploaded successfully. Gemini file ID: {uploaded_file.name}")
        print(f"⏳ Waiting for file processing (timeout: {timeout}s)...")

        # Wait for file processing to complete
        # This is crucial for files to be available for retrieval
        uploaded_file.wait_until_processed(timeout=timeout)

        print(f"✅ File processing completed. File is ready for retrieval.")

        return uploaded_file.name

    except genai.types.BlockedPromptException as e:
        print(f"❌ Gemini blocked prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content was blocked by Gemini safety filters."
        )

    except genai.types.StopCandidateException as e:
        print(f"❌ Gemini processing stopped: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File processing was stopped by Gemini."
        )

    except asyncio.TimeoutError as e:
        print(f"❌ File processing timed out after {timeout}s")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"File processing timed out after {timeout} seconds."
        )

    except Exception as e:
        print(f"❌ Error uploading file to Gemini: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to Gemini: {str(e)}"
        )


async def get_file_from_gemini(gemini_file_id: str) -> Optional[genai.types.File]:
    """
    Retrieve a file from Gemini File Search API.

    Args:
        gemini_file_id: The Gemini file ID (format: "files/FILE_ID")

    Returns:
        genai.types.File: The file object if found, None otherwise
    """
    if not GEMINI_CONFIGURED:
        print("⚠️  Gemini API not configured")
        return None

    try:
        print(f"📥 Retrieving file from Gemini: {gemini_file_id}")
        file_obj = genai.get_file(gemini_file_id)
        print(f"✅ File retrieved successfully")
        return file_obj

    except Exception as e:
        print(f"❌ Error retrieving file from Gemini: {e}")
        return None


async def delete_file_from_gemini(gemini_file_id: str) -> bool:
    """
    Delete a file from Gemini File Search API.

    Args:
        gemini_file_id: The Gemini file ID (format: "files/FILE_ID")

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    if not GEMINI_CONFIGURED:
        print("⚠️  Gemini API not configured")
        return False

    try:
        print(f"🗑️  Deleting file from Gemini: {gemini_file_id}")
        genai.delete_file(gemini_file_id)
        print(f"✅ File deleted successfully")
        return True

    except Exception as e:
        print(f"❌ Error deleting file from Gemini: {e}")
        return False


def get_gemini_status() -> dict:
    """
    Get the current status of Gemini API configuration.

    Returns:
        dict: Status information including API configuration state
    """
    return {
        "configured": GEMINI_CONFIGURED,
        "api_key_set": bool(os.getenv('GEMINI_API_KEY') and os.getenv('GEMINI_API_KEY') != "your_gemini_api_key_here"),
        "models_available": []
    }


def list_gemini_models() -> list:
    """
    List available Gemini models.

    Returns:
        list: List of available model names
    """
    if not GEMINI_CONFIGURED:
        return []

    try:
        models = list(genai.list_models())
        return [model.name for model in models if 'generateContent' in model.supported_generation_methods]
    except Exception as e:
        print(f"❌ Error listing Gemini models: {e}")
        return []