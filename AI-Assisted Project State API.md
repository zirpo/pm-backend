# **Product Requirements Document (PRD)**

# **AI-Assisted Project State API**

| Version | 1.0 |
| :---- | :---- |
| **Status** | Definition |
| **Owner** | Senior Software Architect |
| **Purpose** | To define the backend API for a stateful, multi-project management tool that uses LLMs for state modification and analysis. |

## **1\. Problem Statement**

Manually tracking project plans, tasks, risks, and meeting notes across multiple unstructured text files (e.g., Markdown in Obsidian) is inefficient, error-prone, and unscalable.  
The current manual "process" relies on a human operator copy-pasting an entire project's history into a stateless LLM chat window. This workflow has two critical failure points:

1. **Data Loss:** The LLM is non-deterministic and "creatively" regenerates the entire plan, which leads to silently dropped tasks, corrupted requirements, and lost data.  
2. **Context Window Failure:** The entire workflow fails permanently the moment the project\_plan \+ update\_notes exceeds the LLM's context window.

## **2\. Proposed Solution**

A stateful backend API service that treats the project plan as a structured **JSON object** (the "state") stored in a central **SQLite database**.  
This API provides a stable, reliable foundation for any GUI to consume. It uses LLMs as specialized tools for two distinct, separate functions:

1. **State Updating (Write):** A non-conversational endpoint that takes text input (e.g., meeting notes) and intelligently merges it into the project's JSON state.  
2. **State Analysis (Read):** A read-only endpoint that analyzes a project's JSON state to answer questions and generate reports.

This architecture solves both core problems:

1. **Data Loss:** By operating on structured JSON, the LLM is forced to *modify* state, not *regenerate* it, ensuring data integrity.  
2. **Context Window Failure:** The database, not the prompt, is the project's memory. The context window is only used for the *update itself*, not the entire project history.

## **3\. Core Features (API Endpoints)**

This PRD defines a RESTful API service. All features are API endpoints.

### **Feature 3.1: Project CRUD**

**User Story:** "As a user, I need to create, read, and list my projects so I can manage them."

* **POST /project/create**  
  * **Request:** { "name": "New Project Name" }  
  * **Action:** Creates a new row in the projects table. Initializes its plan\_json column with an empty JSON object ({}).  
  * **Response:** The new Project object.  
* **GET /project/{project\_id}**  
  * **Request:** (Path parameter: project\_id)  
  * **Action:** Fetches the specified project from the database.  
  * **Response:** The Project object, with its plan\_json field parsed as a JSON dictionary.  
* **GET /projects/**  
  * **Action:** Fetches all projects from the database.  
  * **Response:** A list of Project objects (id and name only, plan\_json is excluded to keep the list lightweight).

### **Feature 3.2: State Updater (The "Write" Agent)**

**User Story:** "As a user, I need to provide simple text updates (like meeting notes or a new task) and have the system *intelligently and safely* merge this into my project plan without destroying existing data."

* **POST /project/update**  
  * **Request:** schemas.UpdateRequest  
    {  
      "project\_id": 1,  
      "update\_text": "The budget was cut by 20%. Add a new risk for this. Also, task 3 'Deploy to staging' is now complete."  
    }

  * **Action (Internal):**  
    1. Loads the plan\_json for project\_id=1 from the database.  
    2. Calls the **"State Updater" LLM (Prompt A)** with current\_plan and update\_text.  
    3. The LLM returns a new\_plan (as JSON).  
    4. The service validates this new\_plan.  
    5. The service overwrites the *entire* plan\_json column in the database with the new\_plan.  
  * **Response:** schemas.UpdateResponse  
    {  
      "project\_id": 1,  
      "new\_plan": { ... } // The complete new JSON plan  
    }

### **Feature 3.3: Recommender (The "Read" Agent)**

**User Story:** "As a user, I need to ask a question about my project (like 'what's next?' or 'what are the risks?') and get a simple, read-only report."

* **POST /project/recommend**  
  * **Request:** schemas.RecommendRequest  
    {  
      "project\_id": 1,  
      "user\_question": "What are the biggest risks right now and what's the next step?"  
    }

  * **Action (Internal):**  
    1. Loads the plan\_json for project\_id=1 from the database.  
    2. Calls the **"Recommender" LLM (Prompt B)** with current\_plan and user\_question.  
    3. The LLM returns a markdown\_report (String).  
  * **Response:** schemas.RecommendResponse  
    {  
      "project\_id": 1,  
      "recommendation\_markdown": "\# Project Analysis\\n\\n\#\# Risks\\n- \[High\] Budget cut of 20%...\\n\\n\#\# Next Steps\\n1.  \[High\] Re-scope features to meet new budget."  
    }

  * **CRITICAL CONSTRAINT:** This endpoint is **read-only**. It *must not* make any changes to the database.

## **4\. Non-Functional Requirements**

1. **Source of Truth:** The projects.db SQLite file is the single, non-negotiable source of truth for all project state.  
2. **Data Structure:** All project plans *must* be stored as a JSON string in the plan\_json column. A default schema (e.g., {"tasks": \[\], "risks": \[\], "milestones": \[\]}) should be used to initialize new plans.  
3. **Idempotency:** The "State Updater" (Feature 3.2) does not need to be idempotent, as it is merging, not just adding. The "Recommender" (Feature 3.3) is naturally idempotent as it is a POST request acting as a GET (query).  
4. **Error Handling:** The API must return standard HTTP error codes (404 for not found, 422 for bad validation, 500 for internal/LLM errors).  
5. **LLM Failure:** If the "State Updater" LLM fails to return valid JSON, the API *must* return a 500 error and *must not* save the corrupted data.

## **5\. Out of Scope (What We Are NOT Building)**

* **A "Chatbot":** This is not a conversational chat application. The GUI may *look* like a chat, but it is just a front-end for the update and recommend endpoints.  
* **File-Based Storage:** We will not use "one file per project" or "instances." This is a database application.  
* **RAG (Retrieval-Augmented Generation):** The database *is* the retrieval system. We are not vector-searching external documents.  
* **A GUI:** This PRD is exclusively for the backend API.