-- Migration: Add role column to media table
-- Date: 2026-02-02
-- Purpose: Support "Ingredients" strategy for Veo 3.1

BEGIN;

DO $$
BEGIN
  IF to_regclass('public.media') IS NULL THEN
    RAISE NOTICE 'media table not found; skipping role column migration (apply 003_create_media.sql first)';
  ELSE
    ALTER TABLE IF EXISTS public.media
    ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'generated';

    COMMENT ON COLUMN public.media.role IS 'Ingredient type for Veo 3.1 multi-reference generation (subject, environment, object, master_style_frame, user_reference)';
  END IF;
END $$;

COMMIT;
