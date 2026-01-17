-- RABA Database Migration: Add character_reference_sheet to workflows
-- Version: 008
-- Description: Store character reference sheet (images, name, description) for workflows with lead characters

ALTER TABLE workflows
ADD COLUMN IF NOT EXISTS character_reference_sheet JSONB;

COMMENT ON COLUMN workflows.character_reference_sheet IS 'Character reference sheet: character_name, reference_images (view, url), character_description. Used when script has lead_character.';
