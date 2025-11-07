import json
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from typing import List
from starlette.exceptions import HTTPException as StarletteHTTPException

from database import create_db_and_tables, get_db
import models  # Import models to register them with SQLAlchemy
import schemas
import llm_agents  # Import LLM mock functions

app = FastAPI(title="AI-Assisted Project State API")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

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
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    default_plan = {'tasks': [], 'risks': [], 'milestones': []}
    db_project = models.Project(
        name=project.name,
        plan_json=json.dumps(default_plan)  # Default empty plan as JSON string
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # Create response object without modifying the database object
    return schemas.Project(
        id=db_project.id,
        name=db_project.name,
        plan_json=default_plan
    )

@app.get("/project/{project_id}", response_model=schemas.Project)
def get_project(project_id: int, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
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
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).all()
    # No need to deserialize plan_json for ProjectList schema
    return projects

@app.post("/project/update", response_model=schemas.UpdateResponse)
def update_project_state(request: schemas.UpdateRequest, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == request.project_id).first()
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
        db.commit()
        db.refresh(db_project)

        return {"project_id": db_project.id, "new_plan": new_plan}

    except Exception as e:
        # Catch any errors from LLM or validation and return 500
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"LLM State Update failed: {str(e)}")

@app.post("/project/recommend", response_model=schemas.RecommendResponse)
def recommend_project_state(request: schemas.RecommendRequest, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == request.project_id).first()
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