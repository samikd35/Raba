# Local Development Setup Guide

This guide explains how to connect the Frontend and Backend locally for development.

## Overview

- **Backend**: FastAPI running on `http://localhost:8000`
- **Frontend**: Next.js running on `http://localhost:3000` (or 3001 if 3000 is in use)
- **API Prefix**: `/api/v1`

## Setup Options

### Option 1: Next.js Rewrites (Recommended) ✅

This is the **recommended approach** for local development. It uses Next.js rewrites to proxy API requests, avoiding CORS issues.

**Configuration:**
- Already configured in `Frontend/next.config.mjs`
- Frontend makes requests to `/api/v1/*` (relative paths)
- Next.js automatically proxies these to `http://localhost:8000/api/v1/*`

**Advantages:**
- ✅ No CORS issues
- ✅ Works seamlessly with relative paths
- ✅ No environment variables needed
- ✅ Matches production setup (if using reverse proxy)

### Option 2: Environment Variable

If you prefer to connect directly to the backend without proxying:

1. Create or update `Frontend/.env.local`:
```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

2. Restart the Next.js dev server after adding the env var.

**Note:** This approach requires CORS to be properly configured on the backend (which it already is - `allow_origins=["*"]`).

## Step-by-Step Setup

### 1. Start the Backend

```bash
cd Backend
uvicorn app.main:app --reload
```

The backend will start on `http://localhost:8000`

**Verify it's running:**
- Visit `http://localhost:8000/health` - should return `{"status": "healthy", ...}`
- Visit `http://localhost:8000/docs` - should show Swagger UI

### 2. Start the Frontend

```bash
cd Frontend
npm run dev
```

The frontend will start on `http://localhost:3000` (or 3001 if 3000 is in use)

**Verify it's running:**
- Visit `http://localhost:3000` - should show the Create page
- Check browser console for any errors

### 3. Test the Connection

1. Open the frontend in your browser (`http://localhost:3000`)
2. Open browser DevTools (F12) → Network tab
3. Try creating a workflow (enter a topic and click "Generate Video →")
4. You should see API requests to `/api/v1/generate` in the Network tab
5. These requests should succeed (status 200) if the backend is running

## Troubleshooting

### Frontend shows "Request failed" or network errors

**Check:**
1. ✅ Backend is running on port 8000
   ```bash
   curl http://localhost:8000/health
   ```

2. ✅ Frontend is using the correct configuration
   - If using Option 1 (rewrites): Check `next.config.mjs` has the rewrites config
   - If using Option 2 (env var): Check `.env.local` has `NEXT_PUBLIC_API_BASE=http://localhost:8000`

3. ✅ Restart Next.js dev server after config changes
   ```bash
   # Stop the server (Ctrl+C) and restart
   npm run dev
   ```

### CORS Errors

If you see CORS errors in the browser console:
- **Option 1 users**: Should not see CORS errors (rewrites handle this)
- **Option 2 users**: Check backend CORS config in `Backend/app/main.py` (should allow all origins)

### Port Already in Use

If port 8000 is already in use:
```bash
# Find what's using the port
lsof -i :8000

# Or use a different port
uvicorn app.main:app --reload --port 8001
# Then update NEXT_PUBLIC_API_BASE to http://localhost:8001
```

If port 3000 is already in use:
- Next.js will automatically try 3001, 3002, etc.
- Just use the port shown in the terminal output

## API Endpoints Reference

The frontend makes requests to these endpoints:

- `POST /api/v1/generate` - Create workflow
- `POST /api/v1/generate/with-image` - Create workflow with reference image
- `GET /api/v1/workflows` - List workflows
- `GET /api/v1/workflows/:id` - Get workflow details
- `GET /api/v1/workflows/:id/gate` - Get HITL gate status
- `POST /api/v1/workflows/:id/feedback` - Submit HITL feedback
- `GET /api/v1/tools` - List tools
- `GET /api/v1/monitoring/summary` - Get monitoring data
- `GET /health` - Health check

All endpoints are automatically proxied through Next.js when using Option 1.

## Production Setup

For production, you'll typically:
1. Use a reverse proxy (nginx, Caddy, etc.) to route `/api/v1/*` to the backend
2. Keep frontend API calls as relative paths (`/api/v1/*`)
3. Or set `NEXT_PUBLIC_API_BASE` to your production backend URL

The current setup (Option 1 with rewrites) matches this pattern and will work seamlessly in production with a reverse proxy.
