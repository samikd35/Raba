-- Migration: Add mvp_requirements feature to module_features table
-- Purpose: Enable credit tracking for MVP Requirements Generator (AMRG)
-- Date: 2024-12-15
-- 
-- Table Schema Reference (from vmp_projects):
--   module_features:
--     - id uuid (auto-generated)
--     - name text NOT NULL
--     - display_name text NOT NULL
--     - description text
--     - feature_type text (generator|analyzer|validator|reporter)
--     - credit_cost integer DEFAULT 1
--     - is_active boolean DEFAULT true
--     - settings jsonb DEFAULT '{}'
--     - created_at timestamp

-- Insert mvp_requirements feature into module_features table
INSERT INTO module_features (
    name,
    display_name,
    description,
    feature_type,
    credit_cost,
    is_active,
    settings,
    created_at
)
SELECT 
    'mvp_requirements',
    'MVP Requirements Generator',
    'AI-powered PRD generation with template routing, clarifying questions, and JSON schema validation',
    'generator',
    5,  -- Credit cost per generation (adjust as needed)
    true,
    '{"version": "1.0.0", "module": "mvp"}'::jsonb,
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM module_features WHERE name = 'mvp_requirements'
);

-- Verify feature was added
DO $$
DECLARE
    v_feature_id UUID;
    v_feature_name TEXT;
BEGIN
    SELECT id, name INTO v_feature_id, v_feature_name 
    FROM module_features 
    WHERE name = 'mvp_requirements';
    
    IF v_feature_id IS NOT NULL THEN
        RAISE NOTICE '✅ Feature mvp_requirements added successfully with ID: %', v_feature_id;
    ELSE
        RAISE NOTICE '⚠️ Feature mvp_requirements may already exist or insertion failed';
    END IF;
END $$;
