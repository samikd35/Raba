# RABA Backend Setup Guide

Complete environment and service configuration guide.

## Prerequisites

- **Python 3.11+** - Required for type hints and async features
- **Redis** - For caching (cloud or local)
- **Supabase** - PostgreSQL database with pgvector
- **Google AI Studio** - For Gemini API access

## 1. Environment Variables

Create a `.env` file in the `Backend/` directory:

```bash
cp .env.example .env
```

### Required Variables

```env
# Google Gen AI - Single key for all Gemini models
GOOGLE_API_KEY=your_google_api_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_or_service_key

# Redis (Cloud Redis or local)
REDIS_URL=redis://your-redis-host:port
```

### Optional Variables

```env
# LangSmith Tracing (recommended for debugging)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=Raba

# Google Custom Search (for image search)
GOOGLE_CUSTOM_SEARCH_API_KEY=your_search_key
GOOGLE_CUSTOM_SEARCH_CX=your_search_engine_id

# App Settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
API_V1_PREFIX=/api/v1
```

## 2. Google AI Setup

### Get API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Click "Get API Key"
3. Create or select a project
4. Copy the API key to `GOOGLE_API_KEY`

### Models Used

| Model | Purpose |
|-------|---------|
| `gemini-2.5-flash` | Trend analysis, intent detection |
| `gemini-2.5-pro` | Deep research with grounding |
| `gemini-3-flash-preview` | Script generation |
| `gemini-3-pro-image-preview` | Image generation (Nano Banana Pro) |
| `veo-3.1` | Video generation |
| `deep-research-pro-preview` | Research agent |

## 3. Supabase Setup

### Create Project

1. Go to [Supabase](https://supabase.com/)
2. Create new project
3. Copy URL and anon key to `.env`

### Run Migrations

In Supabase SQL Editor, run these migrations in order:

```sql
-- 1. Create workflows table
-- migrations/001_create_workflows.sql

-- 2. Create tools table  
-- migrations/002_create_tools.sql

-- 3. Create media table
-- migrations/003_create_media.sql

-- 4. Create config table
-- migrations/004_create_config.sql

-- 5. Create usage_metrics table (for monitoring)
-- migrations/usage_metrics.sql

-- 6. Update duration limit to 60 seconds (if upgrading from 25s)
-- migrations/update_duration_limit.sql

-- 7. Add user-selected tool column (optional feature)
-- migrations/007_add_user_selected_tool.sql
```

### Storage Buckets

Create these storage buckets in Supabase:

1. **media** - For generated images and videos
2. **reference_images** - For user-uploaded reference images

```sql
-- Make buckets public (or configure RLS as needed)
INSERT INTO storage.buckets (id, name, public)
VALUES ('media', 'media', true);

INSERT INTO storage.buckets (id, name, public)
VALUES ('reference_images', 'reference_images', false);
```

## 4. Redis Setup

### Option A: Cloud Redis (Recommended)

**Redis Labs:**
1. Create account at [Redis Labs](https://redis.com/)
2. Create a free database
3. Copy the connection URL

**Upstash:**
1. Create account at [Upstash](https://upstash.com/)
2. Create a Redis database
3. Copy the Redis URL

### Option B: Local Redis

```bash
# macOS
brew install redis
brew services start redis

# Set in .env
REDIS_URL=redis://localhost:6379
```

### Verify Connection

```bash
redis-cli -u $REDIS_URL ping
# Should return: PONG
```

## 5. Install Dependencies

```bash
cd Backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 6. Verify Setup

### Run Health Check

```bash
# Start server
python -m uvicorn app.main:app --reload

# In another terminal
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "1.0.0",
  "services": {
    "redis": {"status": "healthy"}
  }
}
```

### Run Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test files
python -m pytest tests/test_cache.py -v
python -m pytest tests/test_api/test_integration.py -v
python -m pytest tests/test_e2e.py -v
```

## 7. LangSmith Setup (Optional)

For tracing and debugging agent workflows:

1. Create account at [LangSmith](https://smith.langchain.com/)
2. Create a project named "Raba"
3. Get API key from Settings
4. Add to `.env`:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key
LANGCHAIN_PROJECT=Raba
```

## 8. Rate Limits

The API has built-in rate limiting:

| Endpoint | Limit |
|----------|-------|
| `POST /api/v1/generate` | 5/minute |
| `POST /api/v1/generate/with-image` | 5/minute |
| `GET /api/v1/workflows/*` | 60/minute |

## 9. Monitoring

Track token usage and costs:

```bash
# Get usage summary (last 7 days)
curl http://localhost:8000/api/v1/monitoring/summary?days=7

# Get workflow-specific usage
curl http://localhost:8000/api/v1/monitoring/workflow/{workflow_id}

# View pricing
curl http://localhost:8000/api/v1/monitoring/pricing
```

## Troubleshooting

### Redis Connection Failed

```
ValueError: Redis URL must be configured
```

**Solution:** Ensure `REDIS_URL` is set in `.env`

### Supabase Connection Failed

```
ValueError: Supabase URL/Key must be configured
```

**Solution:** Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`

### Module Not Found

```
ModuleNotFoundError: No module named 'slowapi'
```

**Solution:** Use the correct Python environment:
```bash
python -m pip install slowapi
python -m pytest tests/ -v  # Use python -m prefix
```

### Rate Limit Exceeded

```
{"detail": "Rate limit exceeded: 5 per 1 minute"}
```

**Solution:** Wait 60 seconds or use a different IP
