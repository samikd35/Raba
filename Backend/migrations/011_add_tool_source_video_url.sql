-- RABA Database Migration: Add source_video_url to tools
-- Version: 011
-- Description: Store uploaded reference video URL for tools created from video

ALTER TABLE tools
ADD COLUMN IF NOT EXISTS source_video_url TEXT;

COMMENT ON COLUMN tools.source_video_url IS 'Public URL of the uploaded reference video used to create this tool';
