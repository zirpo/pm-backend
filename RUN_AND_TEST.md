# 🚀 Quick Start: Run & Test Guide

Get the AI-Assisted Project State API running in minutes!

## 📋 Prerequisites

- **Docker** (recommended) OR **Python 3.11+**
- **DeepSeek API Key** (get one at https://platform.deepseek.com)

---

## 🐳 Option 1: Docker (Recommended)

### 1. Build & Run
```bash
# Build the Docker image
docker build -t project-state-api .

# Run with your API key
docker run -p 8000:8000 --rm \
  -e DEEPSEEK_API_KEY="your_deepseek_api_key" \
  project-state-api
```

### 2. Test the API
```bash
# Health check
curl http://localhost:8000/health

# Create a project
curl -X POST "http://localhost:8000/project/create" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Docker Test Project"}'

# List projects
curl http://localhost:8000/projects/
```

---

## 🐍 Option 2: Local Python

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY

# Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Test the API
Same commands as Docker (see above)

---

## 🧪 Quick Test Suite

Run these commands to verify everything works:

```bash
# 1. Health Check
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 2. Create Project
curl -X POST "http://localhost:8000/project/create" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project"}'
# Expected: {"name":"Test Project","id":1,"plan_json":{"tasks":[],"risks":[],"milestones":[]}}

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
# Expected: Updated project plan with new task

# 5. AI Recommendation (requires real API key)
curl -X POST "http://localhost:8000/project/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "user_question": "What should I do next?"
  }'
# Expected: Markdown recommendation

# 6. Test Error Handling
curl http://localhost:8000/project/99999
# Expected: {"detail":"Project not found"}
```

---

## 🌐 Access Points

Once running, visit:
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

---

## 🔧 Troubleshooting

### Docker Issues
```bash
# Check if port 8000 is available
lsof -i :8000

# Stop any existing containers on port 8000
docker stop $(docker ps -q --filter "publish=8000")

# Rebuild with no cache
docker build --no-cache -t project-state-api .
```

### Python Issues
```bash
# Check Python version
python --version

# Install specific requirements
pip install fastapi uvicorn sqlalchemy pydantic python-dotenv openai

# Check if port is available
netstat -an | grep 8000
```

### API Key Issues
- Verify your DeepSeek API key is valid
- Check that `.env` file contains: `DEEPSEEK_API_KEY="sk-your-actual-key"`
- Ensure no extra spaces or quotes in the key

---

## ✅ Success Indicators

You're all set when you see:
- ✅ Health check returns `{"status":"ok"}`
- ✅ Project creation works
- ✅ API documentation loads in browser
- ✅ AI features work (with valid API key)

**Happy coding! 🎉**