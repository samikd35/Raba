-- RABA Migration: Add soft delete support to workflows
-- Version: 005
-- Adds deleted_at column and index for filtering

ALTER TABLE workflows
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_workflows_deleted_at ON workflows(deleted_at);

COMMENT ON COLUMN workflows.deleted_at IS 'Timestamp when workflow was soft-deleted (NULL means active)';

