-- RABA Database Migration: Create media table
-- Version: 003
-- Description: Track all generated and uploaded media files

CREATE TABLE IF NOT EXISTS media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Workflow reference
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    
    -- Media type and source
    media_type VARCHAR(20) NOT NULL CHECK (media_type IN ('image', 'video', 'audio')),
    source VARCHAR(50) NOT NULL CHECK (source IN ('user_upload', 'research', 'generated')),
    
    -- Storage
    storage_url TEXT NOT NULL,
    storage_bucket VARCHAR(100),
    storage_path TEXT,
    
    -- File metadata
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    width INTEGER,
    height INTEGER,
    duration_seconds FLOAT,
    
    -- Generation metadata
    metadata JSONB,
    generation_prompt TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_media_workflow_id ON media(workflow_id);
CREATE INDEX IF NOT EXISTS idx_media_type ON media(media_type);
CREATE INDEX IF NOT EXISTS idx_media_source ON media(source);

-- Comments
COMMENT ON TABLE media IS 'Track all media files (images, videos, audio) for workflows';
COMMENT ON COLUMN media.source IS 'Origin of media: user_upload, research (from web search), generated (by AI)';
COMMENT ON COLUMN media.storage_url IS 'Full URL to access the media file';
