-- Migration: Add mvp_data column to vmp_projects table
-- Module: MVP Development Suite (Module 3)
-- Purpose: Store VPS, BMC, Critique, and Refinement data
-- Date: 2025-01-15

-- Add mvp_data column if it doesn't exist
ALTER TABLE vmp_projects 
ADD COLUMN IF NOT EXISTS mvp_data JSONB DEFAULT '{}'::jsonb;

-- Create GIN index for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_vmp_projects_mvp_data 
ON vmp_projects USING gin(mvp_data);

-- Add comment to document the column
COMMENT ON COLUMN vmp_projects.mvp_data IS 'Stores MVP development data including VPS (v1, v2), BMC (v1, v2), critique, and VPC v3';

-- Verify the column was added successfully
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'vmp_projects' 
AND column_name = 'mvp_data';

-- Verify the index was created
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'vmp_projects' 
AND indexname = 'idx_vmp_projects_mvp_data';

-- Sample query to test the new column
SELECT 
    id, 
    name, 
    mvp_data,
    created_at 
FROM vmp_projects 
LIMIT 1;
