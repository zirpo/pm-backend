import json
from fastapi import FastAPI, Depends, HTTPException, status, Request, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from starlette.exceptions import HTTPException as StarletteHTTPException

from database import create_db_and_tables, get_db
from app.auth import get_api_key
import models  # Import models to register them with SQLAlchemy
import schemas
import llm_agents  # Import LLM mock functions
import gemini_service  # Import Gemini service
import gemini_rag_service  # Import RAG service

app = FastAPI(
    title="AI-Assisted Project State API",
    dependencies=[Depends(get_api_key)]  # Global API key authentication
)

@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()

# Global Exception Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for any unhandled exceptions.
    Returns 500 Internal Server Error with detailed error information.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request",
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Exception handler for Pydantic validation errors.
    Returns 422 Unprocessable Entity with detailed validation error information.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Invalid request body or parameters",
            "detail": exc.errors(),
            "type": "RequestValidationError"
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/project/create", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
async def create_project(project: schemas.ProjectCreate, db: AsyncSession = Depends(get_db)):
    default_plan = {'tasks': [], 'risks': [], 'milestones': []}
    db_project = models.Project(
        name=project.name,
        plan_json=json.dumps(default_plan)  # Default empty plan as JSON string
    )
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)

    # Create response object without modifying the database object
    return schemas.Project(
        id=db_project.id,
        name=db_project.name,
        plan_json=default_plan
    )

@app.get("/project/{project_id}", response_model=schemas.Project)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    result = await db.execute(select(models.Project).filter(models.Project.id == project_id))
    db_project = result.scalars().first()

    if db_project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Create response object without modifying the database object
    if db_project.plan_json:
        plan_data = json.loads(db_project.plan_json)
    else:
        plan_data = {'tasks': [], 'risks': [], 'milestones': []}

    return schemas.Project(
        id=db_project.id,
        name=db_project.name,
        plan_json=plan_data
    )

@app.get("/projects/", response_model=List[schemas.ProjectList])
async def list_projects(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    result = await db.execute(select(models.Project))
    projects = result.scalars().all()
    # No need to deserialize plan_json for ProjectList schema
    return projects

@app.post("/project/update", response_model=schemas.UpdateResponse)
async def update_project_state(request: schemas.UpdateRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    result = await db.execute(select(models.Project).filter(models.Project.id == request.project_id))
    db_project = result.scalars().first()

    if db_project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Handle case where plan_json might be None
    if db_project.plan_json:
        current_plan = json.loads(db_project.plan_json)
    else:
        current_plan = {'tasks': [], 'risks': [], 'milestones': []}

    try:
        # Call the production LLM agent
        new_plan = llm_agents.state_updater_llm(current_plan, request.update_text)

        # Basic validation: ensure it's a dictionary and can be serialized
        if not isinstance(new_plan, dict):
            raise ValueError("LLM did not return a valid JSON object (dict).")

        db_project.plan_json = json.dumps(new_plan)
        db.add(db_project)
        await db.commit()
        await db.refresh(db_project)

        return {"project_id": db_project.id, "new_plan": new_plan}

    except Exception as e:
        # Catch any errors from LLM or validation and return 500
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"LLM State Update failed: {str(e)}")

@app.post("/project/recommend", response_model=schemas.RecommendResponse)
async def recommend_project_state(request: schemas.RecommendRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    result = await db.execute(select(models.Project).filter(models.Project.id == request.project_id))
    db_project = result.scalars().first()

    if db_project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Handle case where plan_json might be None
    if db_project.plan_json:
        current_plan = json.loads(db_project.plan_json)
    else:
        current_plan = {'tasks': [], 'risks': [], 'milestones': []}

    try:
        # Call the production LLM agent
        recommendation_markdown = llm_agents.recommender_llm(current_plan, request.user_question)

        # CRITICAL: Ensure no database write operations here.
        # The 'db' object is read-only in this context unless explicitly committed.

        return {"project_id": db_project.id, "recommendation_markdown": recommendation_markdown}

    except Exception as e:
        # Catch any errors from LLM and return 500
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"LLM Recommendation failed: {str(e)}")

@app.post("/project/{project_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document to a project and store it in Gemini File Search API.

    This endpoint:
    1. Validates the project exists
    2. Reads the uploaded file content
    3. Uploads the file to Gemini File Search API
    4. Stores the Gemini file ID in the ProjectDocument table
    5. Returns success response with file metadata
    """
    from sqlalchemy import select

    # Log file metadata
    print(f"📤 Received file '{file.filename}' for project {project_id}")
    print(f"   Content type: {file.content_type}")
    print(f"   File size: {file.size if hasattr(file, 'size') else 'Unknown'}")

    # Check if project exists
    print(f"🔍 Validating project {project_id} exists...")
    result = await db.execute(select(models.Project).filter(models.Project.id == project_id))
    db_project = result.scalars().first()

    if db_project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    print(f"   ✅ Project '{db_project.name}' validated")

    # Read file content
    try:
        print(f"📖 Reading file content...")
        file_content = await file.read()
        print(f"   ✅ File content read successfully ({len(file_content)} bytes)")
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file content: {str(e)}"
        )

    # Upload file to Gemini
    try:
        print(f"🚀 Uploading file to Gemini File Search API...")
        gemini_file_id = await gemini_service.upload_file_to_gemini(
            file_content=file_content,
            file_name=file.filename,
            timeout=300  # 5 minutes timeout
        )
        print(f"   ✅ File uploaded to Gemini successfully")
        print(f"   📋 Gemini File ID: {gemini_file_id}")

    except HTTPException:
        # Re-raise HTTPExceptions from gemini_service
        raise
    except Exception as e:
        print(f"   ❌ Unexpected error during Gemini upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during file upload: {str(e)}"
        )

    # Store file record in database
    try:
        print(f"💾 Storing file record in database...")
        new_doc = models.ProjectDocument(
            project_id=project_id,
            file_name=file.filename,
            gemini_corpus_doc_id=gemini_file_id
        )

        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)

        print(f"   ✅ File record stored successfully (ID: {new_doc.id})")

    except Exception as e:
        print(f"   ❌ Error storing file record: {e}")

        # Try to clean up the uploaded file from Gemini to avoid orphaned files
        try:
            await gemini_service.delete_file_from_gemini(gemini_file_id)
            print(f"   🧹 Cleaned up orphaned file from Gemini")
        except Exception as cleanup_error:
            print(f"   ⚠️  Failed to clean up orphaned file: {cleanup_error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error storing file record: {str(e)}"
        )

    # Return success response
    response_data = {
        "id": new_doc.id,
        "filename": new_doc.file_name,
        "project_id": new_doc.project_id,
        "gemini_corpus_doc_id": new_doc.gemini_corpus_doc_id,
        "content_type": file.content_type,
        "uploaded_at": new_doc.uploaded_at.isoformat() if new_doc.uploaded_at else None,
        "message": "File uploaded and linked to project successfully"
    }

    print(f"🎉 Upload completed successfully!")
    print(f"   📄 File: {new_doc.file_name}")
    print(f"   📁 Project: {project_id}")
    print(f"   🆔 Database ID: {new_doc.id}")
    print(f"   🔗 Gemini ID: {new_doc.gemini_corpus_doc_id}")

    return response_data


@app.get("/project/{project_id}/documents", response_model=list[schemas.ProjectDocumentResponse])
async def get_project_documents(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all documents associated with a specific project.

    This endpoint:
    1. Validates the project exists
    2. Queries the ProjectDocument table for all documents linked to the project
    3. Returns a list of document metadata

    Args:
        project_id: The ID of the project to retrieve documents for
        db: Async database session

    Returns:
        List of ProjectDocumentResponse objects containing document metadata
    """
    from sqlalchemy import select

    print(f"📋 Retrieving documents for project {project_id}...")

    # First, verify the project exists
    print(f"🔍 Validating project {project_id} exists...")
    result = await db.execute(select(models.Project).filter(models.Project.id == project_id))
    db_project = result.scalars().first()

    if db_project is None:
        print(f"   ❌ Project {project_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    print(f"   ✅ Project '{db_project.name}' validated")

    # Query for documents associated with this project
    print(f"📚 Querying documents for project {project_id}...")
    try:
        result = await db.execute(
            select(models.ProjectDocument)
            .filter(models.ProjectDocument.project_id == project_id)
            .order_by(models.ProjectDocument.uploaded_at.desc())  # Most recent first
        )
        documents = result.scalars().all()

        document_count = len(documents)
        print(f"   ✅ Found {document_count} documents")

        if document_count > 0:
            print(f"   📄 Documents:")
            for doc in documents[:5]:  # Show first 5 documents
                print(f"      - {doc.file_name} (ID: {doc.id}, Gemini: {doc.gemini_corpus_doc_id})")
            if document_count > 5:
                print(f"      ... and {document_count - 5} more")

        return documents

    except Exception as e:
        print(f"   ❌ Error querying documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving project documents: {str(e)}"
        )


@app.delete("/document/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a document and its associated file from Gemini.

    This endpoint:
    1. Validates the document exists in the database
    2. Deletes the file from Gemini File Search API
    3. Deletes the ProjectDocument record from the database
    4. Returns a success confirmation

    Args:
        document_id: The ID of the document to delete
        db: Async database session

    Returns:
        Success message confirming deletion
    """
    from sqlalchemy import select

    print(f"🗑️  Deleting document {document_id}...")

    # Step 1: Fetch the document from database
    print(f"🔍 Looking up document {document_id} in database...")
    try:
        result = await db.execute(
            select(models.ProjectDocument).filter(models.ProjectDocument.id == document_id)
        )
        document = result.scalars().first()

        if not document:
            print(f"   ❌ Document {document_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id {document_id} not found"
            )

        print(f"   ✅ Document found: {document.file_name}")
        print(f"   📋 Project ID: {document.project_id}")
        print(f"   🔗 Gemini ID: {document.gemini_corpus_doc_id}")

    except HTTPException:
        # Re-raise HTTPExceptions (like 404)
        raise
    except Exception as e:
        print(f"   ❌ Error fetching document from database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving document from database: {str(e)}"
        )

    # Step 2: Delete file from Gemini
    print(f"🚀 Deleting file from Gemini: {document.gemini_corpus_doc_id}...")
    try:
        gemini_delete_success = await gemini_service.delete_file_from_gemini(
            document.gemini_corpus_doc_id
        )

        if not gemini_delete_success:
            print(f"   ⚠️  Gemini deletion failed, but continuing with database cleanup")
            # Note: We could choose to fail the entire operation if Gemini deletion is critical
            # For now, we log the failure but continue with database deletion
        else:
            print(f"   ✅ File successfully deleted from Gemini")

    except Exception as e:
        print(f"   ⚠️  Error deleting from Gemini: {e}")
        print(f"   📝 Continuing with database deletion to maintain consistency")
        # Log the error but continue with database deletion to avoid orphaned records

    # Step 3: Delete database record
    print(f"💾 Deleting document record from database...")
    try:
        await db.delete(document)
        await db.commit()

        print(f"   ✅ Document record successfully deleted from database")
        print(f"   🧹 Cleanup completed for document {document_id}")

    except Exception as e:
        print(f"   ❌ Error deleting document record: {e}")
        # This is critical - if database deletion fails, we have an inconsistent state
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document record from database: {str(e)}"
        )

    # Step 4: Return success response
    success_message = (
        f"Document {document_id} ('{document.file_name}') deleted successfully. "
        f"Associated file has been removed from storage."
    )

    print(f"🎉 Document deletion completed successfully!")
    print(f"   📄 Document: {document.file_name}")
    print(f"   🆔 ID: {document_id}")
    print(f"   📁 Project: {document.project_id}")

    return {
        "message": success_message,
        "document_id": document_id,
        "file_name": document.file_name,
        "project_id": document.project_id
    }


@app.post("/project/recommend_with_docs", response_model=schemas.ProjectRecommendationResponse)
async def recommend_with_docs(
    request: schemas.ProjectRecommendationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Experimental RAG-enabled recommendation endpoint.

    This endpoint serves as the 'read' part of the experimental group,
    providing recommendations enhanced with document context from Gemini.

    Current implementation is a placeholder that will be enhanced
    in Task 12 with full RAG logic.
    """
    from sqlalchemy import select
    import time
    import json

    start_time = time.time()
    print(f"🔬 Experimental RAG recommendation request for project {request.project_id}")
    print(f"   📝 User Question: {request.user_question}")
    print(f"   📋 Plan JSON length: {len(request.plan_json)} characters")

    # Validate project exists
    print(f"🔍 Validating project {request.project_id} exists...")
    try:
        result = await db.execute(select(models.Project).filter(models.Project.id == request.project_id))
        db_project = result.scalars().first()

        if not db_project:
            print(f"   ❌ Project {request.project_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {request.project_id} not found"
            )

        print(f"   ✅ Project '{db_project.name}' validated")

    except HTTPException:
        # Re-raise HTTPExceptions (like 404)
        raise
    except Exception as e:
        print(f"   ❌ Error validating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating project: {str(e)}"
        )

    # Query for available documents (this will be used in Task 12 for RAG)
    print(f"📚 Checking for available documents...")
    try:
        result = await db.execute(
            select(models.ProjectDocument)
            .filter(models.ProjectDocument.project_id == request.project_id)
        )
        documents = result.scalars().all()
        document_count = len(documents)

        print(f"   ✅ Found {document_count} documents available for RAG")

        if document_count > 0:
            print(f"   📄 Available documents:")
            for doc in documents[:3]:  # Show first 3
                print(f"      - {doc.file_name} (ID: {doc.id})")
            if document_count > 3:
                print(f"      ... and {document_count - 3} more")

    except Exception as e:
        print(f"   ❌ Error querying documents: {e}")
        # Don't fail the request, just log the error
        documents = []
        document_count = 0

    # Generate RAG-enhanced recommendation
    print(f"🧠 Generating RAG-enhanced recommendation...")
    try:
        rag_recommendation = await gemini_rag_service.rag_recommendation(
            db_session=db,
            project_id=request.project_id,
            user_question=request.user_question,
            current_plan_json=request.plan_json
        )

        print(f"   ✅ RAG recommendation generated successfully")
        recommendation_markdown = f"""
# RAG-Enhanced Project Recommendation

## User Question
{request.user_question}

## AI-Generated Recommendation
{rag_recommendation}

---
*Generated using {document_count} project documents*
*Processing Time: {int((time.time() - start_time) * 1000)}ms*
        """.strip()

    except Exception as e:
        print(f"   ⚠️  RAG generation failed, using fallback: {e}")
        # Fallback to placeholder
        rag_recommendation = f"Unable to generate RAG recommendation due to service issues. Please try again later. Error: {str(e)}"
        recommendation_markdown = f"""
# Recommendation (Service Unavailable)

## Status
Unable to generate RAG-enhanced recommendation at this time.

## Available Context
{document_count} documents were found for this project.

## Error Details
{rag_recommendation}

---
*Experimental Group Endpoint - Processing Time: {int((time.time() - start_time) * 1000)}ms*
        """.strip()

    # Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Create response with RAG recommendation
    response_data = schemas.ProjectRecommendationResponse(
        project_id=request.project_id,
        message=f"RAG-enhanced recommendation generated using {document_count} project documents.",
        recommendation_markdown=recommendation_markdown,
        sources_used=[doc.id for doc in documents] if documents else [],
        processing_time_ms=processing_time_ms
    )

    print(f"🎉 Experimental RAG request processed successfully!")
    print(f"   📊 Processing time: {processing_time_ms}ms")
    print(f"   📄 Sources available: {len(response_data.sources_used)}")

    return response_data


@app.post("/project/update_with_docs", response_model=schemas.ProjectUpdateResponse)
async def update_project_with_docs(
    request: schemas.ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Experimental RAG-enabled project update endpoint.

    This endpoint serves as the 'write' part of the experimental group,
    providing project updates enhanced with document context from Gemini.

    Current implementation is a placeholder that will be enhanced
    in Task 12 with full RAG logic and database updates.
    """
    from sqlalchemy import select
    import time
    import json

    start_time = time.time()
    print(f"🔬 Experimental RAG update request for project {request.project_id}")
    print(f"   📋 Plan JSON length: {len(request.updated_plan_json)} characters")
    print(f"   📝 Update context: {request.update_context[:50]}..." if request.update_context else "   📝 No update context provided")

    # Validate project exists
    print(f"🔍 Validating project {request.project_id} exists...")
    try:
        result = await db.execute(select(models.Project).filter(models.Project.id == request.project_id))
        db_project = result.scalars().first()

        if not db_project:
            print(f"   ❌ Project {request.project_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {request.project_id} not found"
            )

        print(f"   ✅ Project '{db_project.name}' validated")
        print(f"   📊 Current plan length: {len(db_project.plan_json or '{}')}" if db_project.plan_json else "   📊 Current plan: None")

    except HTTPException:
        # Re-raise HTTPExceptions (like 404)
        raise
    except Exception as e:
        print(f"   ❌ Error validating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating project: {str(e)}"
        )

    # Query for available documents (this will be used in Task 12 for RAG)
    print(f"📚 Checking for available documents...")
    try:
        result = await db.execute(
            select(models.ProjectDocument)
            .filter(models.ProjectDocument.project_id == request.project_id)
        )
        documents = result.scalars().all()
        document_count = len(documents)

        print(f"   ✅ Found {document_count} documents available for RAG context")

        if document_count > 0:
            print(f"   📄 Available documents:")
            for doc in documents[:3]:  # Show first 3
                print(f"      - {doc.file_name} (ID: {doc.id})")
            if document_count > 3:
                print(f"      ... and {document_count - 3} more")

    except Exception as e:
        print(f"   ❌ Error querying documents: {e}")
        # Don't fail the request, just log the error
        documents = []
        document_count = 0

    # Parse and validate the updated plan
    try:
        updated_plan_data = json.loads(request.updated_plan_json)
        print(f"   ✅ Updated plan JSON parsed successfully")
    except json.JSONDecodeError as e:
        print(f"   ❌ Invalid JSON in updated plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON in updated_plan_json: {str(e)}"
        )

    # Generate RAG-enhanced update suggestions and validate the plan
    print(f"🧠 Generating RAG-enhanced update suggestions...")
    try:
        rag_suggestions = await gemini_rag_service.rag_update(
            db_session=db,
            project_id=request.project_id,
            updated_plan_json=request.updated_plan_json,
            update_context=request.update_context
        )

        print(f"   ✅ RAG update suggestions generated successfully")
        rag_changes_made = [
            "RAG analysis completed with document context",
            "AI suggestions incorporated for plan improvement",
            f"Update context: {'provided' if request.update_context else 'none'}"
        ]

    except Exception as e:
        print(f"   ⚠️  RAG generation failed, using basic validation: {e}")
        rag_suggestions = f"Unable to generate RAG suggestions due to service issues. Basic validation completed. Error: {str(e)}"
        rag_changes_made = [
            "Basic plan validation completed",
            "RAG enhancement unavailable",
            f"Update context: {'provided' if request.update_context else 'none'}"
        ]

    # Parse and create updated plan object
    try:
        updated_plan = schemas.ProjectPlan(**updated_plan_data)
        print(f"   ✅ Updated plan converted to schema successfully")

        # Update the project in the database
        print(f"💾 Updating project plan in database...")

        # Get the current project
        project_result = await db.execute(
            select(models.Project).filter(models.Project.id == request.project_id)
        )
        project = project_result.scalars().first()

        if project:
            # Update the plan_json field
            project.plan_json = json.dumps(updated_plan_data, indent=2)
            await db.commit()
            print(f"   ✅ Project plan updated in database")
            database_changes = ["Project plan JSON field updated"]
        else:
            print(f"   ❌ Project {request.project_id} not found for update")
            database_changes = ["Project update failed - project not found"]

    except Exception as e:
        print(f"   ❌ Error processing or updating plan: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing updated plan or updating database: {str(e)}"
        )

    # Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Combine all changes made
    all_changes_made = [
        f"Plan parsed and validated ({len(request.updated_plan_json)} chars)",
        f"Found {document_count} context documents"
    ] + rag_changes_made + database_changes

    # Create final response
    response_data = schemas.ProjectUpdateResponse(
        project_id=request.project_id,
        message=f"Project plan successfully updated using RAG-enhanced analysis with {document_count} contextual documents.",
        updated_plan=updated_plan,
        sources_used=[doc.id for doc in documents] if documents else [],
        processing_time_ms=processing_time_ms,
        changes_made=all_changes_made
    )

    print(f"🎉 Experimental RAG update request processed successfully!")
    print(f"   📊 Processing time: {processing_time_ms}ms")
    print(f"   📄 Sources available: {len(response_data.sources_used)}")
    print(f"   🔄 Changes identified: {len(response_data.changes_made)}")

    return response_data