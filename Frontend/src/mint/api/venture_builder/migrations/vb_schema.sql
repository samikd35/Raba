-- =====================================================
-- Venture Builder Schema Migration
-- All tables in public schema
-- RLS enabled but policies managed separately
-- =====================================================

-- =====================================================
-- 1. AREAS OF EXPERTISE TABLE
-- =====================================================
-- Admins can add, update, and delete expertise areas
CREATE TABLE IF NOT EXISTS public.vb_areas_of_expertise (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX idx_vb_expertise_active ON public.vb_areas_of_expertise(is_active);
CREATE INDEX idx_vb_expertise_order ON public.vb_areas_of_expertise(display_order);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION public.update_vb_expertise_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_vb_expertise_updated_at
    BEFORE UPDATE ON public.vb_areas_of_expertise
    FOR EACH ROW
    EXECUTE FUNCTION public.update_vb_expertise_updated_at();

-- =====================================================
-- 2. VENTURE BUILDERS TABLE
-- =====================================================
CREATE TYPE public.vb_status AS ENUM (
    'pending_profile',
    'pending_admin_review',
    'active',
    'inactive'
);

CREATE TABLE IF NOT EXISTS public.venture_builders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    name TEXT,
    contact_email TEXT NOT NULL,
    main_expertise TEXT,
    short_intro TEXT,
    profile_picture_url TEXT,
    work_experience JSONB, -- Array of {position, organization, years, description}
    biography TEXT,
    linkedin_url TEXT,
    calendar_booking_url TEXT,
    credit_price_per_hour INTEGER DEFAULT 0,
    status public.vb_status DEFAULT 'pending_profile',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_vb_user UNIQUE(user_id),
    CONSTRAINT valid_email CHECK (contact_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT valid_price CHECK (credit_price_per_hour >= 0)
);

-- Indexes
CREATE INDEX idx_vb_user_id ON public.venture_builders(user_id);
CREATE INDEX idx_vb_status ON public.venture_builders(status);
CREATE INDEX idx_vb_active ON public.venture_builders(status) WHERE status = 'active';

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION public.update_vb_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_vb_updated_at
    BEFORE UPDATE ON public.venture_builders
    FOR EACH ROW
    EXECUTE FUNCTION public.update_vb_updated_at();

-- =====================================================
-- 3. VB EXPERTISE JUNCTION TABLE (Many-to-Many)
-- =====================================================
CREATE TABLE IF NOT EXISTS public.vb_expertise_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_builder_id UUID NOT NULL REFERENCES public.venture_builders(id) ON DELETE CASCADE,
    expertise_id UUID NOT NULL REFERENCES public.vb_areas_of_expertise(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate mappings
    CONSTRAINT unique_vb_expertise UNIQUE(venture_builder_id, expertise_id)
);

-- Indexes for faster joins
CREATE INDEX idx_vb_expertise_mapping_vb ON public.vb_expertise_mapping(venture_builder_id);
CREATE INDEX idx_vb_expertise_mapping_expertise ON public.vb_expertise_mapping(expertise_id);

-- =====================================================
-- 4. VB SESSIONS (BOOKINGS) TABLE
-- =====================================================
CREATE TYPE public.vb_session_status AS ENUM (
    'pending',
    'confirmed',
    'completed',
    'canceled'
);

CREATE TABLE IF NOT EXISTS public.vb_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL, -- References organization/team/individual workspace
    booked_by_user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    venture_builder_id UUID NOT NULL REFERENCES public.venture_builders(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.vmp_projects(id) ON DELETE CASCADE,
    session_datetime TIMESTAMPTZ NOT NULL,
    session_duration_minutes INTEGER DEFAULT 60,
    credits_charged INTEGER NOT NULL,
    calendar_event_id TEXT, -- External Google Calendar event ID
    status public.vb_session_status DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_duration CHECK (session_duration_minutes > 0),
    CONSTRAINT valid_credits CHECK (credits_charged >= 0),
    CONSTRAINT future_session CHECK (session_datetime > created_at)
);

-- Indexes
CREATE INDEX idx_vb_sessions_tenant ON public.vb_sessions(tenant_id);
CREATE INDEX idx_vb_sessions_user ON public.vb_sessions(booked_by_user_id);
CREATE INDEX idx_vb_sessions_vb ON public.vb_sessions(venture_builder_id);
CREATE INDEX idx_vb_sessions_project ON public.vb_sessions(project_id);
CREATE INDEX idx_vb_sessions_status ON public.vb_sessions(status);
CREATE INDEX idx_vb_sessions_datetime ON public.vb_sessions(session_datetime);
CREATE INDEX idx_vb_sessions_vb_upcoming ON public.vb_sessions(venture_builder_id, session_datetime)
    WHERE status IN ('pending', 'confirmed');

-- Trigger to update updated_at
CREATE TRIGGER trigger_vb_sessions_updated_at
    BEFORE UPDATE ON public.vb_sessions
    FOR EACH ROW
    EXECUTE FUNCTION public.update_vb_updated_at();

-- =====================================================
-- 5. VB SESSION NOTES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS public.vb_session_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vb_session_id UUID NOT NULL REFERENCES public.vb_sessions(id) ON DELETE CASCADE,
    venture_builder_id UUID NOT NULL REFERENCES public.venture_builders(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    project_id UUID NOT NULL REFERENCES public.vmp_projects(id) ON DELETE CASCADE,
    created_by_user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    main_outcomes TEXT,
    key_takeaways TEXT,
    next_steps TEXT,
    visible_to_user BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- One note per session
    CONSTRAINT unique_session_note UNIQUE(vb_session_id)
);

-- Indexes
CREATE INDEX idx_vb_notes_session ON public.vb_session_notes(vb_session_id);
CREATE INDEX idx_vb_notes_vb ON public.vb_session_notes(venture_builder_id);
CREATE INDEX idx_vb_notes_tenant ON public.vb_session_notes(tenant_id);
CREATE INDEX idx_vb_notes_project ON public.vb_session_notes(project_id);

-- Trigger to update updated_at
CREATE TRIGGER trigger_vb_notes_updated_at
    BEFORE UPDATE ON public.vb_session_notes
    FOR EACH ROW
    EXECUTE FUNCTION public.update_vb_updated_at();

-- =====================================================
-- 6. VB TERMS ACCEPTANCES TABLE (Audit Log)
-- =====================================================
CREATE TABLE IF NOT EXISTS public.vb_terms_acceptances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    venture_builder_id UUID NOT NULL REFERENCES public.venture_builders(id) ON DELETE CASCADE,
    accepted_terms_version TEXT NOT NULL,
    accepted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_vb_terms_user ON public.vb_terms_acceptances(user_id);
CREATE INDEX idx_vb_terms_tenant ON public.vb_terms_acceptances(tenant_id);
CREATE INDEX idx_vb_terms_vb ON public.vb_terms_acceptances(venture_builder_id);

-- =====================================================
-- 7. VB EARNINGS CONFIG TABLE (System Configuration)
-- =====================================================
CREATE TABLE IF NOT EXISTS public.vb_earnings_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credit_to_usd_rate DECIMAL(10, 4) NOT NULL DEFAULT 1.0,
    commission_rate DECIMAL(5, 4) NOT NULL DEFAULT 0.15, -- 15% default
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES public.user_profiles(id),

    -- Constraints
    CONSTRAINT valid_usd_rate CHECK (credit_to_usd_rate > 0),
    CONSTRAINT valid_commission CHECK (commission_rate >= 0 AND commission_rate <= 1)
);

-- Only allow one config row
CREATE UNIQUE INDEX idx_vb_earnings_config_singleton ON public.vb_earnings_config((true));

-- Insert default config
INSERT INTO public.vb_earnings_config (credit_to_usd_rate, commission_rate)
VALUES (1.0, 0.15)
ON CONFLICT DO NOTHING;

-- Trigger to update updated_at
CREATE TRIGGER trigger_vb_earnings_config_updated_at
    BEFORE UPDATE ON public.vb_earnings_config
    FOR EACH ROW
    EXECUTE FUNCTION public.update_vb_updated_at();

-- =====================================================
-- 8. VB INVITATIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS public.vb_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    invited_by_user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    invited_by_email TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued', -- queued, sent, failed, accepted
    sent_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    accepted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_vb_invitations_email ON public.vb_invitations(email);
CREATE INDEX idx_vb_invitations_status ON public.vb_invitations(status);
CREATE INDEX idx_vb_invitations_invited_by ON public.vb_invitations(invited_by_user_id);

-- Trigger to update updated_at
CREATE TRIGGER trigger_vb_invitations_updated_at
    BEFORE UPDATE ON public.vb_invitations
    FOR EACH ROW
    EXECUTE FUNCTION public.update_vb_updated_at();

-- =====================================================
-- 9. ENABLE ROW LEVEL SECURITY (Policies managed separately)
-- =====================================================

ALTER TABLE public.vb_areas_of_expertise ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.venture_builders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vb_expertise_mapping ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vb_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vb_session_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vb_terms_acceptances ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vb_earnings_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vb_invitations ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- 10. SEED DATA - Sample Expertise Areas
-- =====================================================
INSERT INTO public.vb_areas_of_expertise (name, description, display_order, is_active) VALUES
    ('Product Development', 'Product strategy, design, and development', 1, true),
    ('Go-to-Market Strategy', 'Market entry, positioning, and launch strategies', 2, true),
    ('Business Model Innovation', 'Business model design and validation', 3, true),
    ('Fundraising & Investment', 'Investor relations, pitch preparation, fundraising', 4, true),
    ('Customer Discovery', 'Customer research, validation, and feedback', 5, true),
    ('Sales & Marketing', 'Sales processes, marketing strategies, growth hacking', 6, true),
    ('Operations & Scaling', 'Operations optimization, scaling strategies', 7, true),
    ('Technology & Engineering', 'Technical architecture, engineering best practices', 8, true),
    ('Financial Planning', 'Financial modeling, budgeting, unit economics', 9, true),
    ('Leadership & Team Building', 'Team management, hiring, organizational culture', 10, true)
ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- 11. HELPFUL VIEWS
-- =====================================================

-- View: VB with expertise areas (for listing page)
CREATE OR REPLACE VIEW public.vb_with_expertise AS
SELECT
    vb.id,
    vb.user_id,
    vb.contact_email,
    vb.name,
    vb.main_expertise,
    vb.short_intro,
    vb.profile_picture_url,
    vb.biography,
    vb.linkedin_url,
    vb.credit_price_per_hour,
    vb.status,
    vb.work_experience,
    vb.created_at,
    vb.updated_at,
    COALESCE(
        json_agg(
            json_build_object(
                'id', exp.id,
                'name', exp.name,
                'description', exp.description
            ) ORDER BY exp.display_order
        ) FILTER (WHERE exp.id IS NOT NULL),
        '[]'::json
    ) as areas_of_expertise
FROM public.venture_builders vb
LEFT JOIN public.vb_expertise_mapping vem ON vb.id = vem.venture_builder_id
LEFT JOIN public.vb_areas_of_expertise exp ON vem.expertise_id = exp.id AND exp.is_active = true
GROUP BY vb.id;

-- View: Session details with VB and user info
CREATE OR REPLACE VIEW public.vb_session_details AS
SELECT
    s.id,
    s.tenant_id,
    s.booked_by_user_id,
    s.venture_builder_id,
    s.project_id,
    s.session_datetime,
    s.session_duration_minutes,
    s.credits_charged,
    s.status,
    s.created_at,
    vb.contact_email as vb_email,
    vb.profile_picture_url as vb_picture,
    EXISTS(SELECT 1 FROM public.vb_session_notes n WHERE n.vb_session_id = s.id) as has_notes
FROM public.vb_sessions s
JOIN public.venture_builders vb ON s.venture_builder_id = vb.id;

-- =====================================================
-- END OF MIGRATION
-- =====================================================
