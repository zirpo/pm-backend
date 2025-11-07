from pydantic import BaseModel, Field, conint
from typing import Dict, Any, List

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

# Schema for Recommender (Read Agent) request
class RecommendRequest(BaseModel):
    project_id: conint(gt=0)
    user_question: str = Field(..., min_length=1)

# Schema for Recommender (Read Agent) response
class RecommendResponse(BaseModel):
    project_id: int
    recommendation_markdown: str