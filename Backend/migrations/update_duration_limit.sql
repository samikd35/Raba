-- Update duration_seconds check constraint from 25 to 60 seconds
-- This allows for longer video generation with Veo 3.1 video extension

-- Drop the existing check constraint
ALTER TABLE public.workflows DROP CONSTRAINT IF EXISTS workflows_duration_seconds_check;

-- Add the new check constraint with 60 second limit
ALTER TABLE public.workflows ADD CONSTRAINT workflows_duration_seconds_check 
    CHECK (duration_seconds >= 8 AND duration_seconds <= 60);
