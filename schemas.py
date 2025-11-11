from pydantic import BaseModel, Field, conint
from typing import Dict, Any, List
from datetime import datetime

# Schema for validating LLM project plan outputs
class ProjectPlan(BaseModel):
    """Pydantic schema for validating LLM-generated project plan structure."""
    tasks: List[Dict[str, Any]] = Field(default_factory=list, description="List of project tasks")
    risks: List[str] = Field(default_factory=list, description="List of project risks")
    milestones: List[Dict[str, Any]] = Field(default_factory=list, description="List of project milestones")

    class Config:
        # Allow extra fields for flexibility
        extra = "allow"
        # Allow JSON schema generation
        json_schema_extra = {
            "example": {
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
        }

# Base Project Schema - common fields
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

# Schema for creating a new project (request body)
class ProjectCreate(ProjectBase):
    pass

# Schema for Project response (includes id and parsed plan_json)
class Project(ProjectBase):
    id: int
    plan_json: ProjectPlan  # Validated project plan structure

    class Config:
        # Allow mapping to/from ORM models (e.g., SQLAlchemy)
        from_attributes = True

# Schema for lightweight project listing (id and name only)
class ProjectList(ProjectBase):
    id: int

    class Config:
        from_attributes = True

# Schema for State Updater (Write Agent) request
class UpdateRequest(BaseModel):
    project_id: conint(gt=0)
    update_text: str = Field(..., min_length=1)

# Schema for State Updater (Write Agent) response
class UpdateResponse(BaseModel):
    project_id: int
    new_plan: ProjectPlan

# Schema for Experimental RAG-enabled project update request
class ProjectUpdateRequest(BaseModel):
    """Pydantic model for experimental RAG-enabled project update requests."""
    project_id: int = Field(..., gt=0, description="ID of the project to update")
    updated_plan_json: str = Field(..., description="Updated project plan in JSON format")
    update_context: str = Field(default="", description="Additional context for the update (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": 42,
                "updated_plan_json": '{"tasks": [{"id": 1, "name": "Design API", "status": "completed"}, {"id": 2, "name": "Implement Backend", "status": "in_progress"}], "risks": [], "milestones": []}',
                "update_context": "Completed API design phase and starting backend implementation"
            }
        }

# Schema for Experimental RAG-enabled project update response
class ProjectUpdateResponse(BaseModel):
    """Pydantic model for experimental RAG-enabled project update responses."""
    project_id: int = Field(..., description="ID of the updated project")
    message: str = Field(..., description="Response message from the RAG update system")
    updated_plan: ProjectPlan = Field(..., description="The updated project plan structure")
    sources_used: list[int] = Field(default_factory=list, description="List of document IDs used in generating the update")
    processing_time_ms: int = Field(default=0, description="Time taken to process the update in milliseconds")
    changes_made: list[str] = Field(default_factory=list, description="Summary of changes made to the plan")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": 42,
                "message": "Project updated successfully using RAG-enhanced context",
                "updated_plan": {
                    "tasks": [{"id": 1, "name": "Design API", "status": "completed"}],
                    "risks": [],
                    "milestones": []
                },
                "sources_used": [1, 3, 5],
                "processing_time_ms": 1850,
                "changes_made": ["Added new implementation task", "Updated timeline", "Added risk mitigation"]
            }
        }

# Schema for Recommender (Read Agent) request
class RecommendRequest(BaseModel):
    project_id: conint(gt=0)
    user_question: str = Field(..., min_length=1)

# Schema for Recommender (Read Agent) response
class RecommendResponse(BaseModel):
    project_id: int
    recommendation_markdown: str

# Schema for Experimental RAG-enabled recommendation request
class ProjectRecommendationRequest(BaseModel):
    """Pydantic model for experimental RAG-enabled recommendation requests."""
    project_id: int = Field(..., gt=0, description="ID of the project to get recommendations for")
    plan_json: str = Field(..., description="Current project plan in JSON format for RAG context")
    user_question: str = Field(..., min_length=1, description="User's question or request for recommendations")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": 42,
                "plan_json": '{"tasks": [{"id": 1, "name": "Design API", "status": "done"}], "risks": ["Budget overrun"], "milestones": []}',
                "user_question": "What are the next steps I should take for this project?"
            }
        }

# Schema for Experimental RAG-enabled recommendation response
class ProjectRecommendationResponse(BaseModel):
    """Pydantic model for experimental RAG-enabled recommendation responses."""
    project_id: int = Field(..., description="ID of the project")
    message: str = Field(..., description="Response message from the RAG system")
    recommendation_markdown: str = Field(default="", description="Formatted recommendation response in Markdown")
    sources_used: list[int] = Field(default_factory=list, description="List of document IDs used in generating the response")
    processing_time_ms: int = Field(default=0, description="Time taken to process the request in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": 42,
                "message": "Recommendation generated successfully using RAG",
                "recommendation_markdown": "# Project Recommendations\n\nBased on your documents, I recommend...",
                "sources_used": [1, 3, 5],
                "processing_time_ms": 1250
            }
        }

# Schema for Project Document responses
class ProjectDocumentResponse(BaseModel):
    """Pydantic model for ProjectDocument API responses."""
    id: int = Field(..., description="Unique identifier for the document")
    project_id: int = Field(..., description="ID of the project this document belongs to")
    file_name: str = Field(..., min_length=1, max_length=255, description="Original filename")
    gemini_corpus_doc_id: str = Field(..., description="Gemini File Search API document ID")
    uploaded_at: datetime = Field(..., description="Timestamp when document was uploaded")

    class Config:
        # Allow mapping from ORM models (SQLAlchemy)
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "project_id": 42,
                "file_name": "project_requirements.pdf",
                "gemini_corpus_doc_id": "files/abc123def456",
                "uploaded_at": "2024-01-15T10:30:00Z"
            }
        }

# Schema for listing multiple project documents
class ProjectDocumentList(BaseModel):
    """Pydantic model for a list of project documents."""
    documents: List[ProjectDocumentResponse] = Field(default_factory=list, description="List of project documents")
    total_count: int = Field(..., description="Total number of documents")

    class Config:
        json_schema_extra = {
            "example": {
                "documents": [
                    {
                        "id": 1,
                        "project_id": 42,
                        "file_name": "requirements.pdf",
                        "gemini_corpus_doc_id": "files/abc123",
                        "uploaded_at": "2024-01-15T10:30:00Z"
                    },
                    {
                        "id": 2,
                        "project_id": 42,
                        "file_name": "design.docx",
                        "gemini_corpus_doc_id": "files/def456",
                        "uploaded_at": "2024-01-16T14:20:00Z"
                    }
                ],
                "total_count": 2
            }
        }