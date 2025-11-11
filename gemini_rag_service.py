"""
Gemini RAG (Retrieval-Augmented Generation) Service.

This module provides the core RAG functionality for the experimental endpoints,
combining document context from Gemini File Search API with LLM responses.
"""
import asyncio
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import google.generativeai as genai
from fastapi import HTTPException, status

# Import our models and schemas
from database import get_db
import models
import schemas

# Global model instance
_gemini_model = None

def initialize_gemini_model():
    """Initialize the Gemini model for RAG operations."""
    global _gemini_model
    try:
        # Check if Gemini API is configured
        import gemini_service
        if not gemini_service.GEMINI_CONFIGURED:
            print("⚠️  Gemini API not configured - RAG functionality will be limited")
            _gemini_model = None
            return False

        _gemini_model = genai.GenerativeModel('gemini-pro')
        print("✅ Gemini RAG model initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error initializing Gemini RAG model: {e}")
        _gemini_model = None
        return False


async def get_rag_context(db_session: AsyncSession, project_id: int, max_context_length: int = 50000) -> str:
    """
    Retrieve RAG context from all documents associated with a project.

    Args:
        db_session: Async database session
        project_id: ID of the project to fetch documents for
        max_context_length: Maximum character length for combined context

    Returns:
        Combined document content as a single string for RAG context
    """
    print(f"🔍 Getting RAG context for project {project_id}...")

    try:
        # Query all documents for the project
        result = await db_session.execute(
            select(models.ProjectDocument)
            .filter(models.ProjectDocument.project_id == project_id)
            .order_by(models.ProjectDocument.uploaded_at.asc())  # Oldest first
        )
        documents = result.scalars().all()

        if not documents:
            print(f"   📝 No documents found for project {project_id}")
            return ""

        print(f"   📄 Found {len(documents)} documents")

        context_parts = []
        total_length = 0

        for doc in documents:
            try:
                print(f"      Retrieving: {doc.file_name}")

                # Get file from Gemini
                gemini_file = await asyncio.to_thread(
                    genai.get_file, doc.gemini_corpus_doc_id
                )

                if not gemini_file:
                    print(f"      ⚠️  File not found: {doc.gemini_corpus_doc_id}")
                    continue

                # Check file state
                if gemini_file.state != 'ACTIVE':
                    print(f"      ⚠️  File not active: {gemini_file.state}")
                    continue

                # Get file content
                content = await asyncio.to_thread(gemini_file.text_content)

                if not content:
                    print(f"      ⚠️  No content available for {doc.file_name}")
                    continue

                # Add context with metadata
                doc_context = f"""--- Document: {doc.file_name} ---
Uploaded: {doc.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}
Gemini ID: {doc.gemini_corpus_doc_id}

{content}
--- End Document ---"""

                # Check if adding this would exceed our limit
                if total_length + len(doc_context) > max_context_length:
                    print(f"      ⚠️  Context length limit reached, skipping remaining documents")
                    break

                context_parts.append(doc_context)
                total_length += len(doc_context)

                print(f"      ✅ Added {len(content)} characters from {doc.file_name}")

            except Exception as e:
                print(f"      ❌ Error processing {doc.file_name}: {e}")
                continue

        combined_context = "\n\n".join(context_parts)
        print(f"   📊 Generated {len(combined_context)} characters of RAG context")

        return combined_context

    except Exception as e:
        print(f"   ❌ Error getting RAG context: {e}")
        return ""


async def get_gemini_rag_response(
    db_session: AsyncSession,
    project_id: int,
    base_prompt: str,
    system_prompt: Optional[str] = None
) -> str:
    """
    Generate a response using Gemini with RAG context.

    Args:
        db_session: Async database session
        project_id: ID of the project for context
        base_prompt: Base prompt/question from the user
        system_prompt: Optional system prompt to guide the response

    Returns:
        Generated response text from Gemini
    """
    print(f"🧠 Generating RAG response for project {project_id}")
    print(f"   📝 Base prompt length: {len(base_prompt)} characters")

    # Check if model is available
    if _gemini_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service not available - Gemini API not configured"
        )

    try:
        # Get RAG context
        context = await get_rag_context(db_session, project_id)

        if not context:
            print("   📝 No RAG context available, using base prompt only")
            context = "(No documents available for context)"

        # Construct the full prompt
        full_prompt_parts = []

        if system_prompt:
            full_prompt_parts.append(f"System: {system_prompt}")

        full_prompt_parts.append(f"""
Here is the current project information:
{base_prompt}

Here are relevant documents for context:
{context}

Based on the project information and the provided document context above, please provide a helpful and specific response. Reference specific details from the documents when relevant.
""".strip())

        full_prompt = "\n\n".join(full_prompt_parts)

        print(f"   📊 Full prompt length: {len(full_prompt)} characters")
        print(f"   🔤 Generating response...")

        # Generate response with Gemini
        response = await asyncio.to_thread(_gemini_model.generate_content, full_prompt)
        response_text = response.text

        print(f"   ✅ Generated response: {len(response_text)} characters")
        print(f"   📄 Response preview: {response_text[:100]}...")

        return response_text

    except Exception as e:
        print(f"   ❌ Error generating RAG response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating RAG response: {str(e)}"
        )


async def rag_recommendation(
    db_session: AsyncSession,
    project_id: int,
    user_question: str,
    current_plan_json: str
) -> str:
    """
    Generate a RAG-enhanced recommendation for a project.

    Args:
        db_session: Async database session
        project_id: ID of the project
        user_question: User's question or request
        current_plan_json: Current project plan in JSON format

    Returns:
        RAG-enhanced recommendation response
    """
    print(f"🔬 Generating RAG recommendation for project {project_id}")

    base_prompt = f"""User Question: {user_question}

Current Project Plan:
{current_plan_json}

Please provide recommendations, insights, or advice based on the project's current state and the user's specific question. Consider the timeline, risks, and potential next steps."""

    system_prompt = """You are an expert project management consultant. Provide helpful, actionable recommendations based on the user's question and the project documents. Focus on practical advice and specific next steps."""

    return await get_gemini_rag_response(
        db_session=db_session,
        project_id=project_id,
        base_prompt=base_prompt,
        system_prompt=system_prompt
    )


async def rag_update(
    db_session: AsyncSession,
    project_id: int,
    updated_plan_json: str,
    update_context: str
) -> str:
    """
    Generate a RAG-enhanced update for a project plan.

    Args:
        db_session: Async database session
        project_id: ID of the project
        updated_plan_json: Updated project plan in JSON format
        update_context: Additional context for the update

    Returns:
        RAG-enhanced update response and suggestions
    """
    print(f"🔄 Generating RAG update for project {project_id}")

    base_prompt = f"""Update Context: {update_context}

Updated Project Plan:
{updated_plan_json}

Please analyze this project update and provide:
1. Validation of the updated plan
2. Suggestions for improvement or next steps
3. Identification of potential risks or opportunities
4. Recommendations for project management"""

    system_prompt = """You are an expert project manager and technical consultant. Review the updated project plan and provide constructive feedback and actionable suggestions for improvement."""

    return await get_gemini_rag_response(
        db_session=db_session,
        project_id=project_id,
        base_prompt=base_prompt,
        system_prompt=system_prompt
    )


# Initialize the model when the module is imported
initialize_gemini_model()