# **This is the main application file.**

# **It runs the API, defines the endpoints, and ties everything together.**

from fastapi import FastAPI, Depends, HTTPException  
from sqlalchemy.orm import Session  
from typing import Any, Dict

# **Import all our components from the other files**

from . import models, schemas  
from .database import SessionLocal, engine

# **\--- MOCK LLM FUNCTIONS \---**

# **This is where your actual API calls to Gemini would go.**

# **We mock the logic to keep this runnable.**

def mock\_llm\_state\_updater(current\_plan: Dict\[str, Any\], update\_text: str) \-\> Dict\[str, Any\]:  
"""  
MOCK FUNCTION: Simulates Prompt A (State Updater).  
It takes the current plan and update text, and returns a new plan.  
"""  
print(f"\[LLM MOCK\]: Updating state for plan: {current\_plan}")  
print(f"\[LLM MOCK\]: With update text: {update\_text}")  
\# Simple mock logic  
if "new\_plan" not in current\_plan:  
    current\_plan\["new\_plan"\] \= {"tasks": \[\], "risks": \[\]}

current\_plan\["new\_plan"\]\["tasks"\].append(  
    {"id": len(current\_plan\["new\_plan"\]\["tasks"\]) \+ 1, "desc": update\_text, "status": "todo"}  
)  
current\_plan\["last\_update"\] \= update\_text

print(f"\[LLM MOCK\]: Returning new plan: {current\_plan}")  
return current\_plan

def mock\_llm\_recommender(current\_plan: Dict\[str, Any\], user\_question: str) \-\> str:  
"""  
MOCK FUNCTION: Simulates Prompt B (Recommender).  
It takes the current plan and a question, and returns a Markdown report.  
"""  
print(f"\[LLM MOCK\]: Analyzing plan: {current\_plan}")  
print(f"\[LLM MOCK\]: With user question: {user\_question}")  
\# Simple mock logic  
task\_count \= len(current\_plan.get("new\_plan", {}).get("tasks", \[\]))

report \= f"""

# **Project Analysis**

## **Status**

* You asked: "{user\_question}"  
* The project currently has **{task\_count}** task(s).

## **✅ Prioritized To-Do List**

1. \[High\] Address the last update: "{current\_plan.get('last\_update', 'N/A')}"  
2. \[Medium\] Review all open tasks.  
   """  
   print(f"\[LLM MOCK\]: Returning report.")  
   return report

# **\--- DATABASE SETUP \---**

# **Create all the database tables defined in models.py**

models.Base.metadata.create\_all(bind=engine)

# **Initialize the FastAPI app**

app \= FastAPI()

# **Dependency: This function gets a database session for each API request**

# **and ensures it's closed afterward.**

def get\_db():  
db \= SessionLocal()  
try:  
yield db  
finally:  
db.close()

# **\--- API ENDPOINTS \---**

@app.post("/project/create", response\_model=schemas.Project)  
def create\_project(project: schemas.ProjectCreate, db: Session \= Depends(get\_db)):  
"""  
Creates a new, empty project in the database.  
"""  
\# Initialize with a default empty JSON plan  
db\_project \= models.Project(name=project.name, plan\_json="{}")  
db.add(db\_project)  
db.commit()  
db.refresh(db\_project)  
\# Manually parse the JSON string back to a dict for the response  
db\_project.plan\_json \= {}  
return db\_project  
@app.get("/project/{project\_id}", response\_model=schemas.Project)  
def get\_project(project\_id: int, db: Session \= Depends(get\_db)):  
"""  
Retrieves a single project and its plan from the database.  
"""  
db\_project \= db.query(models.Project).filter(models.Project.id \== project\_id).first()  
if db\_project is None:  
raise HTTPException(status\_code=404, detail="Project not found")  
\# Parse the JSON string from the DB into a dict for the Pydantic model  
import json  
db\_project.plan\_json \= json.loads(db\_project.plan\_json)  
return db\_project

@app.post("/project/update", response\_model=schemas.UpdateResponse)  
def update\_project\_state(request: schemas.UpdateRequest, db: Session \= Depends(get\_db)):  
"""  
ENDPOINT 1: The "State Updater"  
This is the core of your "write" logic.  
"""  
import json  
\# 1\. Get the project from the DB  
db\_project \= db.query(models.Project).filter(models.Project.id \== request.project\_id).first()  
if db\_project is None:  
    raise HTTPException(status\_code=404, detail="Project not found")

\# 2\. Load its current state (plan)  
current\_plan \= json.loads(db\_project.plan\_json)

\# 3\. Call the "State Updater" LLM (mocked)  
new\_plan \= mock\_llm\_state\_updater(current\_plan, request.update\_text)

\# 4\. Save the new state back to the DB  
db\_project.plan\_json \= json.dumps(new\_plan) \# Convert back to string for storage  
db.commit()

return schemas.UpdateResponse(project\_id=db\_project.id, new\_plan=new\_plan)

@app.post("/project/recommend", response\_model=schemas.RecommendResponse)  
def get\_project\_recommendation(request: schemas.RecommendRequest, db: Session \= Depends(get\_db)):  
"""  
ENDPOINT 2: The "Recommender"  
This is the core of your "read/analyze" logic.  
"""  
import json  
\# 1\. Get the project from the DB  
db\_project \= db.query(models.Project).filter(models.Project.id \== request.project\_id).first()  
if db\_project is None:  
    raise HTTPException(status\_code=404, detail="Project not found")

\# 2\. Load its current state (plan)  
current\_plan \= json.loads(db\_project.plan\_json)

\# 3\. Call the "Recommender" LLM (mocked)  
markdown\_report \= mock\_llm\_recommender(current\_plan, request.user\_question)

\# 4\. Return the report (This does NOT save anything)  
return schemas.RecommendResponse(  
    project\_id=db\_project.id,  
    recommendation\_markdown=markdown\_report  
)  
