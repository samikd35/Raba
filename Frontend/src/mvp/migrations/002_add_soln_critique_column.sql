-- Migration: Add soln_critique_data column to vmp_projects table
-- Purpose: Store solution critique analysis results
-- Date: 2024-01-20

-- Add soln_critique_data column to vmp_projects table
ALTER TABLE vmp_projects 
ADD COLUMN IF NOT EXISTS soln_critique_data JSONB DEFAULT NULL;

-- Add comment for documentation
COMMENT ON COLUMN vmp_projects.soln_critique_data IS 'Solution critique analysis results with citations';

-- Create GIN index for faster JSONB queries
CREATE INDEX IF NOT EXISTS idx_vmp_projects_soln_critique 
ON vmp_projects USING gin (soln_critique_data);

-- Add comment for index
COMMENT ON INDEX idx_vmp_projects_soln_critique IS 'GIN index for solution critique JSONB queries';

-- Verify column was added
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'vmp_projects' 
        AND column_name = 'soln_critique_data'
    ) THEN
        RAISE NOTICE 'Column soln_critique_data added successfully to vmp_projects table';
    ELSE
        RAISE EXCEPTION 'Failed to add soln_critique_data column';
    END IF;
END $$;
