-- =====================================================
-- Google Calendar Integration for Venture Builder
-- =====================================================
-- This migration adds:
-- 1. venture_builder_google_connections - OAuth tokens per VB
-- 2. venture_builder_availability_profiles - Working hours configuration
-- 3. agenda column to vb_sessions table

-- =====================================================
-- 1. VENTURE BUILDER GOOGLE CONNECTIONS TABLE
-- =====================================================
-- Stores OAuth tokens and calendar configuration for each VB
-- Tokens are encrypted at the application level before storage

CREATE TABLE IF NOT EXISTS public.venture_builder_google_connections (
    vb_id UUID PRIMARY KEY REFERENCES public.venture_builders(id) ON DELETE CASCADE,
    google_user_id TEXT NOT NULL,
    calendar_id TEXT,  -- Selected calendar ID, NULL until VB chooses one
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT NOT NULL,
    token_expiry TIMESTAMPTZ NOT NULL,
    time_zone TEXT DEFAULT 'UTC',
    is_valid BOOLEAN DEFAULT true,  -- Set to false if refresh token fails
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Index for checking valid connections
CREATE INDEX IF NOT EXISTS idx_vb_google_connections_valid
    ON public.venture_builder_google_connections(vb_id)
    WHERE is_valid = true;

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION public.update_vb_google_connections_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_vb_google_connections_updated_at ON public.venture_builder_google_connections;
CREATE TRIGGER trigger_vb_google_connections_updated_at
    BEFORE UPDATE ON public.venture_builder_google_connections
    FOR EACH ROW
    EXECUTE FUNCTION public.update_vb_google_connections_updated_at();

-- Enable RLS
ALTER TABLE public.venture_builder_google_connections ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.venture_builder_google_connections IS
'Stores Google OAuth credentials for Venture Builders to enable calendar integration. Tokens are encrypted at application level.';

COMMENT ON COLUMN public.venture_builder_google_connections.is_valid IS
'Set to false when refresh token fails, requiring VB to re-authenticate.';

-- =====================================================
-- 2. VENTURE BUILDER AVAILABILITY PROFILES TABLE
-- =====================================================
-- Stores VB working hours configuration
-- VBs can have multiple availability windows per day (future enhancement)
-- Currently supports one entry per day_of_week per VB

CREATE TABLE IF NOT EXISTS public.venture_builder_availability_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vb_id UUID NOT NULL REFERENCES public.venture_builders(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL,  -- 0=Sunday, 1=Monday, ..., 6=Saturday
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    session_length_minutes INTEGER NOT NULL DEFAULT 60,
    buffer_before_minutes INTEGER NOT NULL DEFAULT 0,
    buffer_after_minutes INTEGER NOT NULL DEFAULT 0,
    max_sessions_per_day INTEGER,  -- NULL = unlimited
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT valid_day_of_week CHECK (day_of_week >= 0 AND day_of_week <= 6),
    CONSTRAINT valid_time_range CHECK (end_time > start_time),
    CONSTRAINT valid_session_length CHECK (session_length_minutes > 0),
    CONSTRAINT valid_buffer_before CHECK (buffer_before_minutes >= 0),
    CONSTRAINT valid_buffer_after CHECK (buffer_after_minutes >= 0),
    CONSTRAINT valid_max_sessions CHECK (max_sessions_per_day IS NULL OR max_sessions_per_day > 0),

    -- One availability entry per VB per day
    CONSTRAINT unique_vb_day UNIQUE(vb_id, day_of_week)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_vb_availability_vb_id
    ON public.venture_builder_availability_profiles(vb_id);

CREATE INDEX IF NOT EXISTS idx_vb_availability_vb_day
    ON public.venture_builder_availability_profiles(vb_id, day_of_week);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION public.update_vb_availability_profiles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_vb_availability_profiles_updated_at ON public.venture_builder_availability_profiles;
CREATE TRIGGER trigger_vb_availability_profiles_updated_at
    BEFORE UPDATE ON public.venture_builder_availability_profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.update_vb_availability_profiles_updated_at();

-- Enable RLS
ALTER TABLE public.venture_builder_availability_profiles ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.venture_builder_availability_profiles IS
'Stores VB working hours configuration. Used to compute available booking slots.';

COMMENT ON COLUMN public.venture_builder_availability_profiles.day_of_week IS
'0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday';

COMMENT ON COLUMN public.venture_builder_availability_profiles.buffer_before_minutes IS
'Buffer time before session start (e.g., for prep). Slot will not be available if conflicts with this buffer.';

COMMENT ON COLUMN public.venture_builder_availability_profiles.buffer_after_minutes IS
'Buffer time after session end (e.g., for notes). Slot will not be available if conflicts with this buffer.';

COMMENT ON COLUMN public.venture_builder_availability_profiles.max_sessions_per_day IS
'Maximum number of sessions VB wants per day. NULL means unlimited.';

-- =====================================================
-- 3. ADD COLUMNS TO VB_SESSIONS
-- =====================================================
-- agenda: Stores the meeting agenda provided by the user during booking
-- calendar_event_id: Stores the Google Calendar event ID for session management
-- credit_consumption_id: Links to the credit consumption record for refunds

ALTER TABLE public.vb_sessions
ADD COLUMN IF NOT EXISTS agenda TEXT;

ALTER TABLE public.vb_sessions
ADD COLUMN IF NOT EXISTS calendar_event_id TEXT;

ALTER TABLE public.vb_sessions
ADD COLUMN IF NOT EXISTS credit_consumption_id UUID REFERENCES public.tenant_credit_consumptions(id);

COMMENT ON COLUMN public.vb_sessions.agenda IS
'Meeting agenda/notes provided by the user when booking the session. Included in calendar event description.';

COMMENT ON COLUMN public.vb_sessions.calendar_event_id IS
'Google Calendar event ID. Used to update/delete the event when session is modified/cancelled.';

COMMENT ON COLUMN public.vb_sessions.credit_consumption_id IS
'Reference to tenant_credit_consumptions.id. Used for credit refunds on session cancellation.';

-- Index for calendar event lookups (when syncing or checking)
CREATE INDEX IF NOT EXISTS idx_vb_sessions_calendar_event_id
    ON public.vb_sessions(calendar_event_id)
    WHERE calendar_event_id IS NOT NULL;

-- Index for credit consumption lookups
CREATE INDEX IF NOT EXISTS idx_vb_sessions_credit_consumption_id
    ON public.vb_sessions(credit_consumption_id)
    WHERE credit_consumption_id IS NOT NULL;

-- =====================================================
-- END OF MIGRATION
-- =====================================================
