# RABA Backend

**AI-Powered Multi-Agent YouTube Shorts Generator**

RABA is a multi-agent AI pipeline that transforms topics into viral YouTube Shorts (8-25 seconds) using Google's Gemini family of models.

## Features

- **Multi-Agent Architecture**: Specialized agents for each step (Intent/Tool Selection, Research, Script, Image, Video)
- **LangGraph Orchestration**: Graph-based workflow with state persistence
- **HITL Support**: Human-in-the-loop mode with 5 approval gates
- **Multiple Visual Styles**: Surreal Realism, High-Octane Anime, Stylized 3D
- **Viral Optimization**: Scripts optimized for engagement with hooks and pattern interrupts

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI (Python 3.11+) |
| **Orchestration** | LangGraph |
| **LLMs** | Google Gemini (2.5 Flash, 2.5 Pro) |
| **Image Generation** | Nano Banana Pro (Gemini Image) |
| **Video Generation** | Veo 3.1 |
| **Database** | Supabase (PostgreSQL) |
| **Cache** | Redis |
| **Tracing** | LangSmith |

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Redis server
- Supabase project

### 2. Installation

```bash
cd Backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
```

Required environment variables:
- `GOOGLE_API_KEY` - Google AI Studio API key
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase anon key
- `REDIS_URL` - Redis connection URL

### 4. Database Setup

Run the SQL migrations in your Supabase project:

```bash
# In Supabase SQL Editor, run:
migrations/001_create_workflows.sql
migrations/002_create_tools.sql
migrations/003_create_media.sql
migrations/004_create_config.sql
```

### 5. Run the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8000

# Or run directly
python -m app.main
```

### 6. Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/generate` | Create video generation workflow |
| `GET` | `/api/v1/workflows/{id}` | Get workflow status |
| `GET` | `/api/v1/workflows` | List workflows |

### Create Workflow

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "How black holes work",
    "duration_seconds": 18,
    "aspect_ratio": "9:16",
    "resolution": "1080p",
    "category": "auto",
    "hitl_mode": "auto"
  }'
```

## Project Structure

```
Backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings & configuration
│   ├── agents/              # Agent implementations (Phase 2+)
│   ├── models/              # Pydantic models
│   ├── services/            # External service clients
│   ├── graph/               # LangGraph workflow
│   ├── tools/               # Tool repository
│   ├── api/routes/          # API route handlers
│   └── utils/               # Utilities & helpers
├── migrations/              # SQL migrations
├── tests/                   # Test suite
├── requirements.txt         # Dependencies
└── .env.example            # Environment template
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Linting & Formatting

```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint
ruff check app/ tests/
```

## Implementation Status

### Phase 1: Foundation ✅
- [x] Project setup
- [x] Environment configuration
- [x] Database schema
- [x] API scaffold
- [x] LangGraph base

### Phase 2: Core Agents (Pending)
- [ ] Intent/Tool Selector
- [ ] Deep Research
- [ ] Script Generator
- [ ] Tool Repository

### Phase 3: Generation (Pending)
- [ ] Image Generator
- [ ] Video Generator
- [ ] Output Processing

### Phase 4: Advanced (Pending)
- [ ] HITL System
- [ ] Multi-segment Video
- [ ] Caching Layer
- [ ] Monitoring

## Documentation

- [SRS.md](../Guides/SRS.md) - Software Requirements Specification
- [RABA_Architecture.md](../Guides/RABA_Architecture.md) - Technical Architecture
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Implementation Plan

## License

MIT
