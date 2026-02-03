-- Migration: Add Module 3 Bootstrap columns to vmp_projects
-- Description: Enables direct Module 3 entry by adding bootstrap context support
-- Date: 2024-12-16

-- Add enhanced_context column for storing bootstrap-generated context pack
ALTER TABLE public.vmp_projects
  ADD COLUMN IF NOT EXISTS enhanced_context JSONB DEFAULT NULL;

-- Add context_mode column to distinguish normal vs bootstrap projects
ALTER TABLE public.vmp_projects
  ADD COLUMN IF NOT EXISTS context_mode TEXT NOT NULL DEFAULT 'normal';

-- Add context_status column for tracking bootstrap workflow state
ALTER TABLE public.vmp_projects
  ADD COLUMN IF NOT EXISTS context_status TEXT NOT NULL DEFAULT 'not_started';

-- Add context_version column for tracking edits to enhanced context
ALTER TABLE public.vmp_projects
  ADD COLUMN IF NOT EXISTS context_version INT NOT NULL DEFAULT 1;

-- Add check constraint for context_mode
ALTER TABLE public.vmp_projects
  DROP CONSTRAINT IF EXISTS vmp_projects_context_mode_check;
ALTER TABLE public.vmp_projects
  ADD CONSTRAINT vmp_projects_context_mode_check 
  CHECK (context_mode IN ('normal', 'bootstrap', 'hybrid'));

-- Add check constraint for context_status
ALTER TABLE public.vmp_projects
  DROP CONSTRAINT IF EXISTS vmp_projects_context_status_check;
ALTER TABLE public.vmp_projects
  ADD CONSTRAINT vmp_projects_context_status_check 
  CHECK (context_status IN (
    'not_started', 
    'embedding', 
    'questions_pending', 
    'answers_received', 
    'researching', 
    'payment_required', 
    'context_ready', 
    'context_confirmed', 
    'failed'
  ));

-- Make pv_report_id nullable for bootstrap projects (currently NOT NULL)
ALTER TABLE public.vmp_projects
  ALTER COLUMN pv_report_id DROP NOT NULL;

-- Add index for efficient querying by context_mode
CREATE INDEX IF NOT EXISTS idx_vmp_projects_context_mode 
  ON public.vmp_projects(context_mode);

-- Add index for efficient querying by context_status
CREATE INDEX IF NOT EXISTS idx_vmp_projects_context_status 
  ON public.vmp_projects(context_status);

-- Add comments for documentation
COMMENT ON COLUMN public.vmp_projects.enhanced_context IS 
  'Stores bootstrap-generated context pack with draft/confirmed fields and research citations';
COMMENT ON COLUMN public.vmp_projects.context_mode IS 
  'Project context source: normal=standard workflow, bootstrap=Module 3 direct entry, hybrid=mixed';
COMMENT ON COLUMN public.vmp_projects.context_status IS 
  'Status of bootstrap context generation workflow';
COMMENT ON COLUMN public.vmp_projects.context_version IS 
  'Version counter for enhanced context edits';

-- Register the bootstrap feature in module_features table (only if not exists)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.module_features WHERE name = 'module3_bootstrap_context') THEN
    INSERT INTO public.module_features (name, display_name, description, feature_type, credit_cost, is_active)
    VALUES (
      'module3_bootstrap_context',
      'Module 3 Bootstrap Context Generation',
      'Generate enhanced context pack for direct Module 3 entry without completing Modules 1-2',
      'generator',
      15,
      true
    );
  ELSE
    UPDATE public.module_features
    SET display_name = 'Module 3 Bootstrap Context Generation',
        description = 'Generate enhanced context pack for direct Module 3 entry without completing Modules 1-2',
        credit_cost = 15,
        is_active = true
    WHERE name = 'module3_bootstrap_context';
  END IF;
END $$;
