-- RABA Database Migration: Create workflows table
-- Version: 001
-- Description: Main table for storing video generation workflows

CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- User input parameters
    topic TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 18 CHECK (duration_seconds >= 8 AND duration_seconds <= 25),
    aspect_ratio VARCHAR(10) NOT NULL DEFAULT '9:16' CHECK (aspect_ratio IN ('9:16', '16:9')),
    resolution VARCHAR(10) NOT NULL DEFAULT '1080p' CHECK (resolution IN ('720p', '1080p')),
    category VARCHAR(50) NOT NULL DEFAULT 'auto',
    hitl_mode VARCHAR(10) NOT NULL DEFAULT 'auto' CHECK (hitl_mode IN ('auto', 'manual')),
    enable_audio BOOLEAN NOT NULL DEFAULT true,
    enable_subtitles BOOLEAN NOT NULL DEFAULT false,
    
    -- User reference image
    user_reference_image_url TEXT,
    
    -- Agent outputs (JSONB for flexibility)
    tool_selection JSONB,
    research_output JSONB,
    research_images JSONB,
    script_output JSONB,
    generated_images JSONB,
    video_output JSONB,
    
    -- HITL tracking
    current_hitl_gate VARCHAR(50),
    hitl_feedback JSONB DEFAULT '[]'::jsonb,
    
    -- Error tracking
    error TEXT,
    error_details JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
CREATE INDEX IF NOT EXISTS idx_workflows_created_at ON workflows(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflows_hitl_gate ON workflows(current_hitl_gate) WHERE current_hitl_gate IS NOT NULL;

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_workflows_updated_at ON workflows;
CREATE TRIGGER update_workflows_updated_at
    BEFORE UPDATE ON workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE workflows IS 'Main table for video generation workflows';
COMMENT ON COLUMN workflows.status IS 'Current workflow status: pending, running, awaiting_*, completed, failed';
COMMENT ON COLUMN workflows.hitl_mode IS 'Human-in-the-loop mode: auto (no stops) or manual (stops at gates)';
COMMENT ON COLUMN workflows.current_hitl_gate IS 'Current HITL gate if workflow is paused for approval';
