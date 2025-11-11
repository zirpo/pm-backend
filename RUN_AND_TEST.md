🚀 Quick Start: Run & Test Guide

Get the AI-Assisted Project State API running. This guide assumes a production-ready, configurable container.

📋 Prerequisites

Docker

DeepSeek API Key (get one at https://platform.deepseek.com)

🐳 Docker (Production)

1. Build the Image

# Build the Docker image
docker build -t project-state-api .


2. Run the Container (Commands)

A: Standard (Host 8000 -> Container 8000)

Use this if your local port 8000 is free.

docker run -p 8000:8000 --rm \
  -e DEEPSEEK_API_KEY="your_deepseek_api_key" \
  project-state-api


App will be at: http://localhost:8000

B: Conflicting Port (Host 8001 -> Container 8000)

Use this if your local port 8000 is busy. This is the command you failed to execute.

docker run -p 8001:8000 --rm \
  -e DEEPSEEK_API_KEY="your_deepseek_api_key" \
  project-state-api


App will be at: http://localhost:8001

C: Flexible Port (Host 8001 -> Container 9000)

Use this to run the app on a different port inside the container.

docker run -p 8001:9000 --rm \
  -e DEEPSEEK_API_KEY="your_deepseek_api_key" \
  -e PORT=9000 \
  project-state-api


App will be at: http://localhost:8001

🧪 Quick Test Suite

Run these commands, adjusting the port to match the one you exposed on your host (e.g., 8000 or 8001).

# 1. Health Check
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 2. Create Project
curl -X POST "http://localhost:8000/project/create" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project"}'
# Expected: {"name":"Test Project","id":1,"plan_json":{...}}

# 3. List Projects
curl http://localhost:8000/projects/
# Expected: Array with your project

# 4. AI Update (requires real API key)
curl -X POST "http://localhost:8000/project/update" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "update_text": "Add a task for testing"
  }'
# Expected: Updated project plan

# 5. Test Error Handling
curl http://localhost:8000/project/99999
# Expected: {"detail":"Project not found"}


🌐 Access Points

Once running, visit (adjust host port as needed):

API Documentation: http://localhost:8000/docs

Alternative Docs: http://localhost:8000/redoc

🔧 Troubleshooting

"Port is already allocated"

Problem: Another process is using your host port (e.g., 8000).
Solution 1 (Correct): Find and kill the conflicting process.

# Find the process
lsof -i :8000
# Kill the process
kill -9 <PID>


Solution 2 (Workaround): Use a different host port. (See Command B above).
docker run -p 8001:8000 ...

"Connection Refused"

Problem: You are mapping to the wrong container port.
Solution: Ensure your host port maps to the port Uvicorn is running on (default 8000).

WRONG: -p 8001:8001 (Your mistake)

RIGHT: -p 8001:8000