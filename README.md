# AI-Assisted Project State API

A FastAPI application that provides AI-powered project management capabilities with LLM integration for intelligent project plan updates and recommendations.

## 🚀 Features

- **Project Management**: Create, read, and manage projects with structured plans
- **AI-Powered Updates**: LLM-intelligent project state updates using natural language
- **Smart Recommendations**: AI-driven insights and recommendations based on project data
- **Robust Error Handling**: Comprehensive validation and error responses
- **Docker Support**: Fully containerized for easy deployment
- **Database Persistence**: SQLAlchemy-based data storage with SQLite

## 📋 Prerequisites

- **Python 3.11+**
- **Docker** (optional, for containerized deployment)
- **DeepSeek API Key** (for LLM functionality)

## 🛠 Installation

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd pm-backend
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your DEEPSEEK_API_KEY
   ```

4. **Run the application**:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Docker Deployment

1. **Build the Docker image**:
   ```bash
   docker build -t project-state-api .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8000:8000 --rm \
     -e DEEPSEEK_API_KEY="your_deepseek_api_key" \
     project-state-api
   ```

## 📚 API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🎯 API Endpoints

### Core Operations

#### Health Check
```http
GET /health
```
Returns application health status.

#### Create Project
```http
POST /project/create
Content-Type: application/json

{
  "name": "My Project"
}
```

#### List All Projects
```http
GET /projects/
```

#### Get Specific Project
```http
GET /project/{project_id}
```

### AI-Powered Features

#### Update Project State (AI)
```http
POST /project/update
Content-Type: application/json

{
  "project_id": 1,
  "update_text": "Add a new task for API documentation"
}
```

#### Get AI Recommendations
```http
POST /project/recommend
Content-Type: application/json

{
  "project_id": 1,
  "user_question": "What are the next priority tasks?"
}
```

## 🗂 Project Structure

```
pm-backend/
├── main.py              # FastAPI application and routes
├── models.py            # SQLAlchemy database models
├── schemas.py           # Pydantic request/response schemas
├── llm_agents.py        # LLM integration functions
├── database.py          # Database connection and setup
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
├── .dockerignore       # Docker build exclusions
├── .env.example        # Environment variables template
├── tests/              # Test files
└── README.md           # This file
```

## 🧪 Testing

### Running Tests
```bash
pytest
```

### API Testing Examples

1. **Create a project**:
   ```bash
   curl -X POST "http://localhost:8000/project/create" \
     -H "Content-Type: application/json" \
     -d '{"name": "Test Project"}'
   ```

2. **Update project with AI**:
   ```bash
   curl -X POST "http://localhost:8000/project/update" \
     -H "Content-Type: application/json" \
     -d '{
       "project_id": 1,
       "update_text": "Add testing milestone and update task priorities"
     }'
   ```

3. **Get recommendations**:
   ```bash
   curl -X POST "http://localhost:8000/project/recommend" \
     -H "Content-Type: application/json" \
     -d '{
       "project_id": 1,
       "user_question": "What risks should I consider?"
     }'
   ```

## 🔧 Configuration

### Environment Variables

- **DEEPSEEK_API_KEY**: Required for LLM functionality
- **DATABASE_URL**: Optional database connection string (defaults to SQLite)

### LLM Models

The application uses DeepSeek's reasoning model (`deepseek-reasoner`) for:
- **State Updates**: Intelligent project plan modifications
- **Recommendations**: Contextual insights and suggestions

## 🚨 Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid input data
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation errors
- **500 Internal Server Error**: Server-side errors with detailed information

## 🐳 Docker Configuration

### Dockerfile Features
- **Base Image**: `python:3.11-slim-bookworm`
- **Multi-stage Build**: Optimized layer caching
- **Security**: Excludes sensitive files via `.dockerignore`
- **Port**: Exposes 8000 for FastAPI

### .dockerignore
Excludes:
- Virtual environments (`.venv/`, `__pycache__/`)
- Sensitive files (`.env`, `*.sqlite*`)
- Development tools (`.git/`, `.taskmaster/`)
- IDE files (`.vscode/`, `.cursor/`)

## 📊 Project Plan Schema

Projects store structured plans with the following schema:

```json
{
  "tasks": [
    {
      "id": 1,
      "name": "Task name",
      "status": "todo|in-progress|done"
    }
  ],
  "risks": [
    "Risk description"
  ],
  "milestones": [
    {
      "id": 1,
      "name": "Milestone name",
      "completed": false
    }
  ]
}
```

## 🔒 Security Considerations

- **API Keys**: Never commit API keys to version control
- **Input Validation**: All inputs validated using Pydantic schemas
- **Error Messages**: Sanitized error responses prevent information leakage
- **Docker Security**: Minimal base image and excluded sensitive files

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- Check the [API Documentation](http://localhost:8000/docs)
- Review the error logs for detailed information
- Ensure all environment variables are properly configured

---

**Built with ❤️ using FastAPI, SQLAlchemy, and DeepSeek AI**