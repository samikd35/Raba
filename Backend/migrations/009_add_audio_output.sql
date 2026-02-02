-- RABA Database Migration: Add missing workflow columns
-- Version: 009
-- Description: Add audio_output, segment_contexts, and segment_context_status columns

-- Audio output for voice generation manifest
ALTER TABLE workflows
ADD COLUMN IF NOT EXISTS audio_output JSONB;

-- Segment contexts for video generation tracking
ALTER TABLE workflows
ADD COLUMN IF NOT EXISTS segment_contexts JSONB;

-- Segment context status for tracking video segment generation state
ALTER TABLE workflows
ADD COLUMN IF NOT EXISTS segment_context_status VARCHAR(50);

COMMENT ON COLUMN workflows.audio_output IS 'Voice generation output manifest containing segments, timing, and file paths';
COMMENT ON COLUMN workflows.segment_contexts IS 'Video segment contexts for multi-segment video generation';
COMMENT ON COLUMN workflows.segment_context_status IS 'Status of segment context generation: pending, completed, failed, audio_planned';
