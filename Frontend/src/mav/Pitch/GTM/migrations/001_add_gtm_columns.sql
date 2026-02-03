-- Migration: Add GTM Strategy columns to vmp_projects
-- Purpose: Store Go-To-Market strategy versions and generation status
-- Date: 2024-12-24

-- Add gtm_data column to store GTM strategy versions (JSONB)
-- Structure: { "current_version": int, "versions": [...] }
ALTER TABLE public.vmp_projects 
ADD COLUMN IF NOT EXISTS gtm_data JSONB DEFAULT '{}'::jsonb;

-- Add gtm_status column to track generation status
ALTER TABLE public.vmp_projects 
ADD COLUMN IF NOT EXISTS gtm_status VARCHAR DEFAULT 'not_started'
CHECK (gtm_status IN ('not_started', 'processing', 'completed', 'failed'));

-- Create index for faster status queries
CREATE INDEX IF NOT EXISTS idx_vmp_projects_gtm_status ON public.vmp_projects(gtm_status);

-- Add comment for documentation
COMMENT ON COLUMN public.vmp_projects.gtm_data IS 'JSONB storage for GTM Strategy Pack versions with citations and run traces';
COMMENT ON COLUMN public.vmp_projects.gtm_status IS 'GTM generation status: not_started, processing, completed, failed';
