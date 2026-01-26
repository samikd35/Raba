-- RABA Usage Metrics Table
-- Stores token usage and cost tracking for monitoring
-- Phase 5 - Production Readiness
--
-- Note: References videos table (not workflows) per existing schema in tables.sql

CREATE TABLE IF NOT EXISTS usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
    generation_type TEXT NOT NULL CHECK (generation_type IN ('text', 'image', 'video', 'research', 'embedding')),
    model_name TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cached_tokens INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    duration_seconds DECIMAL(10, 2) DEFAULT 0,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_usage_metrics_workflow_id ON usage_metrics(workflow_id);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_generation_type ON usage_metrics(generation_type);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_model_name ON usage_metrics(model_name);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_created_at ON usage_metrics(created_at DESC);

-- Composite index for time-based aggregations
CREATE INDEX IF NOT EXISTS idx_usage_metrics_type_date ON usage_metrics(generation_type, created_at DESC);

-- RLS Policies (enable after testing)
-- ALTER TABLE usage_metrics ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read their own video metrics
-- CREATE POLICY "Users can view own video metrics"
--     ON usage_metrics FOR SELECT
--     USING (workflow_id IN (
--         SELECT id FROM workflows WHERE user_id = auth.uid()
--     ));

-- Allow service role full access
-- CREATE POLICY "Service role full access"
--     ON usage_metrics FOR ALL
--     USING (auth.role() = 'service_role');

COMMENT ON TABLE usage_metrics IS 'Token usage and cost tracking for text, image, video, and research by workflow';
COMMENT ON COLUMN usage_metrics.generation_type IS 'Type: text, image, video, research, embedding';
COMMENT ON COLUMN usage_metrics.cost_usd IS 'Calculated cost in USD based on model pricing';
COMMENT ON COLUMN usage_metrics.cached_tokens IS 'Tokens served from cache (no cost)';
