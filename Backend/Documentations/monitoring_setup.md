RABA Monitoring Setup

Overview
- RABA now records usage for text (Gemini), image (Nano Banana), video (Veo), and research steps.
- Metrics are stored in Supabase table `usage_metrics` and surfaced via `/api/v1/monitoring` endpoints used by the Frontend Monitoring page.

Prerequisites
- Supabase URL and service role key configured in backend environment.
- FFmpeg optional (unrelated to metrics, for text overlays).

Database Migration
1) Apply the migration to create `usage_metrics`:
   - File: `Backend/migrations/usage_metrics.sql`
   - This version references `workflows(id)` (not `videos`) as the foreign key.
   - Run using Supabase SQL editor or your migration runner.

2) Verify the table:
   - `select * from usage_metrics limit 1;` (should succeed even if empty)

Behavior Notes
- If the table is missing, the backend will:
  - Log: "Monitoring table missing. Apply migration: Backend/migrations/usage_metrics.sql"
  - Disable further writes to avoid log spam until restart.
  - Monitoring API will return empty summaries (zeros) instead of 500s.

Frontend
- The Monitoring page (`/monitoring`) reads from `/api/v1/monitoring/summary?days=N`.
- It supports both legacy and new summary shapes; after migration, all KPIs and charts populate.

What’s Tracked
- Text: estimated input/output tokens, duration, model, success/failure.
- Image: aggregated prompt token estimate, num images, duration, model.
- Video: final video seconds (for cost), generation time, model, segments, resolution/aspect.
- Research: cache hit/miss, duration, strategy.

Troubleshooting
- PGRST205 (missing table): apply migration and restart backend.
- 42P01 relation "videos" does not exist: you’re trying an old migration; use the updated `usage_metrics.sql` that references `workflows`.
- Empty charts: ensure table exists and usage-generating actions have been performed.
