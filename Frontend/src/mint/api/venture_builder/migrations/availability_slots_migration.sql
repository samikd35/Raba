-- Migration: Update venture_builder_availability_profiles table
-- Changes from working hours model to specific session slots model
--
-- Before: day_of_week + start_time/end_time range + buffers (one entry per day)
-- After: day_of_week + session_start/session_end (multiple entries per day allowed)

-- Step 1: Drop old constraints
ALTER TABLE public.venture_builder_availability_profiles
    DROP CONSTRAINT IF EXISTS unique_vb_day;

ALTER TABLE public.venture_builder_availability_profiles
    DROP CONSTRAINT IF EXISTS valid_time_range;

ALTER TABLE public.venture_builder_availability_profiles
    DROP CONSTRAINT IF EXISTS valid_session_length;

ALTER TABLE public.venture_builder_availability_profiles
    DROP CONSTRAINT IF EXISTS valid_buffer_before;

ALTER TABLE public.venture_builder_availability_profiles
    DROP CONSTRAINT IF EXISTS valid_buffer_after;

ALTER TABLE public.venture_builder_availability_profiles
    DROP CONSTRAINT IF EXISTS valid_max_sessions;

-- Step 2: Drop old columns
ALTER TABLE public.venture_builder_availability_profiles
    DROP COLUMN IF EXISTS start_time;

ALTER TABLE public.venture_builder_availability_profiles
    DROP COLUMN IF EXISTS end_time;

ALTER TABLE public.venture_builder_availability_profiles
    DROP COLUMN IF EXISTS session_length_minutes;

ALTER TABLE public.venture_builder_availability_profiles
    DROP COLUMN IF EXISTS buffer_before_minutes;

ALTER TABLE public.venture_builder_availability_profiles
    DROP COLUMN IF EXISTS buffer_after_minutes;

ALTER TABLE public.venture_builder_availability_profiles
    DROP COLUMN IF EXISTS max_sessions_per_day;

-- Step 3: Add new columns
ALTER TABLE public.venture_builder_availability_profiles
    ADD COLUMN IF NOT EXISTS session_start TIME NOT NULL DEFAULT '09:00:00';

ALTER TABLE public.venture_builder_availability_profiles
    ADD COLUMN IF NOT EXISTS session_end TIME NOT NULL DEFAULT '10:00:00';

-- Remove defaults after adding columns
ALTER TABLE public.venture_builder_availability_profiles
    ALTER COLUMN session_start DROP DEFAULT;

ALTER TABLE public.venture_builder_availability_profiles
    ALTER COLUMN session_end DROP DEFAULT;

-- Step 4: Add new constraints
ALTER TABLE public.venture_builder_availability_profiles
    ADD CONSTRAINT valid_session_time_range CHECK (session_end > session_start);

-- Unique constraint on vb_id + day_of_week + session_start (allows multiple slots per day)
ALTER TABLE public.venture_builder_availability_profiles
    ADD CONSTRAINT unique_vb_day_session UNIQUE(vb_id, day_of_week, session_start);

-- Step 5: Update index
DROP INDEX IF EXISTS idx_vb_availability_vb_day;
CREATE INDEX IF NOT EXISTS idx_vb_availability_vb_day_session
    ON public.venture_builder_availability_profiles(vb_id, day_of_week, session_start);

-- Step 6: Update comments
COMMENT ON TABLE public.venture_builder_availability_profiles IS
'Stores VB availability slots. Each row represents a specific bookable time slot for a day of week.';

COMMENT ON COLUMN public.venture_builder_availability_profiles.session_start IS
'Start time of the availability slot';

COMMENT ON COLUMN public.venture_builder_availability_profiles.session_end IS
'End time of the availability slot (typically session_start + 1 hour)';
