# Claude Code Instructions

## 🎯 Project Status: COMPLETE ✅

**Context-Aware AI PoC v2** - Fully Implemented RAG-Enabled Project Management System

- **Status**: ✅ **100% COMPLETE** - All 12 tasks successfully implemented
- **Implementation**: Production-ready with comprehensive testing
- **Repository**: Complete code committed and pushed to GitHub

## 📋 Quick Setup Guide

### 1. Environment Configuration
Create `.env` file in project root:
```env
# Required for RAG functionality
GEMINI_API_KEY=your-gemini-api-key-here

# Database connection
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/pm_backend

# API authentication
SUPER_SECRET_API_KEY=your-secret-api-key-here
```

### 2. Get Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in and create new API key
3. Add key to `.env` file

### 3. Database Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start server
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 🏗️ What Was Built

### Core System
- ✅ FastAPI application with async/await throughout
- ✅ PostgreSQL database migration from SQLite
- ✅ Global API key authentication system
- ✅ Alembic database migrations
- ✅ Complete Pydantic validation and OpenAPI documentation

### RAG System
- ✅ Gemini File Search API integration
- ✅ ProjectDocument model with database relationships
- ✅ Context-aware AI responses with document retrieval
- ✅ Experimental endpoints for A/B testing
- ✅ Complete source attribution and tracking

### API Endpoints
- **Core**: `POST /project/create`, `GET /project/{project_id}`, `POST /project/{project_id}/upload`
- **Documents**: `GET /project/{project_id}/documents`, `DELETE /document/{document_id}`
- **Control Group**: `POST /project/recommend`, `POST /project/update`
- **Experimental (RAG)**: `POST /project/recommend_with_docs`, `POST /project/update_with_docs`

## 📁 Key Files

- `main.py` - FastAPI application with all endpoints
- `gemini_rag_service.py` - Complete RAG logic implementation
- `gemini_service.py` - Gemini File Search API integration
- `database.py` - PostgreSQL async configuration
- `models.py` - Database models including ProjectDocument
- `schemas.py` - Pydantic validation models
- `app/auth.py` - Global API key authentication
- `alembic/` - Database migration files
- `IMPLEMENTATION_COMPLETE.md` - Comprehensive project documentation

## 🧪 Testing

```bash
# Run comprehensive integration tests
python test_final_rag_integration.py

# Test specific endpoints
python test_experimental_write.py
python test_experimental_read.py
```

## 🚀 Production Deployment

1. Configure PostgreSQL database
2. Add valid `GEMINI_API_KEY` to .env
3. Set `SUPER_SECRET_API_KEY` for authentication
4. Run `alembic upgrade head` for database setup
5. Deploy with `uvicorn main:app --host 0.0.0.0 --port 8000`

## 📖 Documentation

- `IMPLEMENTATION_COMPLETE.md` - Full project documentation
- Auto-generated OpenAPI docs at `http://localhost:8000/docs`
- Comprehensive error handling and logging throughout

---

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
