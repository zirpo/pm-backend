import json
import os
from typing import Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError
import schemas

# Load environment variables
load_dotenv()

# DeepSeek API Configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY environment variable not set. Please set it in your .env file.")

# Initialize OpenAI client with DeepSeek base URL
# Disable proxy to avoid compatibility issues
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1",
    http_client=None  # Use default httpx client
)
DEEPSEEK_MODEL = "deepseek-reasoner"  # Advanced reasoning model for project analysis

def call_deepseek_llm(messages: list, json_mode: bool = False, max_retries: int = 3) -> str:
    """
    Make a call to DeepSeek LLM with retry logic and proper error handling.

    Args:
        messages: List of message dictionaries for the chat completion
        json_mode: Whether to request JSON response format
        max_retries: Maximum number of retry attempts for transient errors

    Returns:
        str: The LLM response content

    Raises:
        RuntimeError: If the API call fails after all retries
    """
    import time

    for attempt in range(max_retries + 1):
        try:
            response_format = {"type": "json_object"} if json_mode else {"type": "text"}

            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=messages,
                response_format=response_format,
                temperature=0.7,
                max_tokens=4096
            )

            return response.choices[0].message.content

        except Exception as e:
            # Check if this is a transient error that should be retried
            error_str = str(e).lower()
            is_transient = any(keyword in error_str for keyword in [
                "rate limit", "timeout", "connection", "temporary", "try again"
            ])

            if attempt == max_retries or not is_transient:
                raise RuntimeError(f"DeepSeek LLM call failed after {attempt + 1} attempts: {e}")

            # Exponential backoff for retries
            wait_time = 2 ** attempt
            print(f"DeepSeek API error (attempt {attempt + 1}/{max_retries + 1}): {e}")
            print(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

def state_updater_llm(current_plan: Dict[str, Any], update_text: str) -> Dict[str, Any]:
    """
    Production State Updater LLM function using DeepSeek API.

    Args:
        current_plan: Current project plan as a dictionary
        update_text: Natural language instruction for updating the plan

    Returns:
        Dict[str, Any]: Updated project plan (validated against ProjectPlan schema)

    Raises:
        ValueError: If LLM returns invalid JSON or malformed response that doesn't match ProjectPlan schema
        RuntimeError: If the API call fails
    """
    prompt_messages = [
        {
            "role": "system",
            "content": (
                "You are an AI assistant that updates project plans. "
                "Your task is to integrate the 'update_text' into the 'current_plan' JSON. "
                "You MUST return a valid JSON object representing the ENTIRE updated project plan. "
                "Maintain all existing elements unless explicitly modified or removed by the update_text. "
                "The plan schema includes 'tasks', 'risks', 'milestones' as lists of dictionaries. "
                "Ensure the JSON is well-formed and complete. If the update is unclear, make a reasonable interpretation. "
                "Example plan structure: {'tasks': [{'id':1, 'name':'Task A', 'status':'todo'}], 'risks': [], 'milestones': []}"
            )
        },
        {
            "role": "user",
            "content": f"Current Plan: {json.dumps(current_plan)}\n\nUpdate Text: {update_text}\n\nReturn the new, complete project plan as a JSON object."
        }
    ]

    try:
        json_response_str = call_deepseek_llm(prompt_messages, json_mode=True)

        # Validate and parse the JSON response
        try:
            new_plan_dict = json.loads(json_response_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}\nResponse: {json_response_str}")

        # Validate against ProjectPlan schema
        try:
            validated_plan = schemas.ProjectPlan(**new_plan_dict)
        except ValidationError as e:
            raise ValueError(f"LLM returned invalid plan structure or data: {e}\nResponse: {json_response_str}")

        # Return as dict for compatibility with existing code
        return validated_plan.model_dump()

    except Exception as e:
        if isinstance(e, (ValueError, RuntimeError)):
            raise
        raise RuntimeError(f"State updater LLM failed: {e}")

def recommender_llm(current_plan: Dict[str, Any], user_question: str) -> str:
    """
    Production Recommender LLM function using DeepSeek API.

    Args:
        current_plan: Current project plan as a dictionary
        user_question: User's question about the project

    Returns:
        str: Markdown report answering the user's question

    Raises:
        ValueError: If LLM returns invalid or empty response
        RuntimeError: If the API call fails
    """
    prompt_messages = [
        {
            "role": "system",
            "content": (
                "You are an AI assistant specialized in project analysis. "
                "Analyze the provided 'current_plan' JSON and answer the 'user_question'. "
                "Your response MUST be a detailed markdown report. Do NOT modify the plan. "
                "Focus on providing actionable insights, summaries, or answers based on the plan data. "
                "Use proper markdown formatting with headings, bullet points, and bold text. "
                "Example: If asked 'What's next?', list incomplete tasks and their statuses."
            )
        },
        {
            "role": "user",
            "content": f"Current Plan: {json.dumps(current_plan)}\n\nUser Question: {user_question}\n\nProvide a detailed markdown report."
        }
    ]

    try:
        markdown_report = call_deepseek_llm(prompt_messages, json_mode=False)

        # Validate the response is a non-empty string
        if not isinstance(markdown_report, str):
            raise ValueError(f"LLM returned non-string response: {type(markdown_report).__name__}")

        if not markdown_report.strip():
            raise ValueError("LLM returned empty response")

        return markdown_report

    except Exception as e:
        if isinstance(e, (ValueError, RuntimeError)):
            raise
        raise RuntimeError(f"Recommender LLM failed: {e}")

# --- Mock Functions (kept for testing/fallback purposes) ---

def mock_state_updater_llm(current_plan: Dict[str, Any], update_text: str) -> Dict[str, Any]:
    """Mocks the State Updater LLM by performing a simple text-based update."""
    print(f"Mock State Updater: Applying '{update_text}' to plan.\nCurrent plan: {json.dumps(current_plan, indent=2)}")

    # Simple mock logic: If update_text mentions 'add task', create a new task.
    # In a real scenario, LLM would parse and merge.
    new_plan = current_plan.copy()
    if 'tasks' not in new_plan: new_plan['tasks'] = []

    if 'add task' in update_text.lower() or 'new task' in update_text.lower():
        task_name = update_text.replace('add task ', '').replace('new task ', '').strip().capitalize()
        if task_name and task_name not in [t['name'] for t in new_plan['tasks']]:
            new_plan['tasks'].append({'id': len(new_plan['tasks']) + 1, 'name': task_name, 'status': 'todo'})
    elif 'update task' in update_text.lower():
        # Mock updating an existing task status
        parts = update_text.split(' ') # e.g., 'update task 1 status to done'
        if len(parts) >= 5 and parts[0].lower() == 'update' and parts[1].lower() == 'task':
            try:
                task_id = int(parts[2])
                new_status = parts[len(parts)-1]
                for task in new_plan['tasks']:
                    if task['id'] == task_id:
                        task['status'] = new_status
                        break
            except ValueError: pass # ignore malformed mock update

    print(f"Mock State Updater: Returning new plan: {json.dumps(new_plan, indent=2)}")
    return new_plan

def mock_recommender_llm(current_plan: Dict[str, Any], user_question: str) -> str:
    """Mocks the Recommender LLM by generating a simple markdown report."""
    print(f"Mock Recommender: Analyzing plan for question '{user_question}'.\nCurrent plan: {json.dumps(current_plan, indent=2)}")

    # Simple mock logic: Generate a report based on the question and plan.
    report = f"# Project Analysis for question: '{user_question}'\n\n"
    report += f"Based on your current plan, which has {len(current_plan.get('tasks', []))} tasks.\n"

    if 'next steps' in user_question.lower() or 'whats next' in user_question.lower():
        todo_tasks = [t['name'] for t in current_plan.get('tasks', []) if t.get('status') == 'todo']
        if todo_tasks:
            report += "\n**Suggested next steps (TODO tasks):**\n"
            for task in todo_tasks:
                report += f"- {task}\n"
        else:
            report += "\nNo outstanding tasks found. Perhaps you've completed everything!\n"
    elif 'risks' in user_question.lower():
        risks = current_plan.get('risks', [])
        if risks:
            report += "\n**Identified Risks:**\n"
            for risk in risks:
                report += f"- {risk}\n"
        else:
            report += "\nNo specific risks are currently documented.\n"

    report += "\n*(This is a mock recommendation and does not reflect actual LLM capabilities.)*"
    print(f"Mock Recommender: Returning markdown report.\n")
    return report