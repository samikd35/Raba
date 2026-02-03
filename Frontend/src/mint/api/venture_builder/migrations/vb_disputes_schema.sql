-- =====================================================
-- VB Dispute Resolution System
-- =====================================================
-- Allows users to report issues with completed VB sessions
-- Admins can track and resolve disputes through a status workflow

-- =====================================================
-- 1. DISPUTE REASON ENUM
-- =====================================================
CREATE TYPE public.vb_dispute_reason AS ENUM (
    'missed_session',    -- VB no-show
    'time_theft',        -- VB arrived late or ended early
    'other'              -- Custom reason
);

-- =====================================================
-- 2. DISPUTE STATUS ENUM
-- =====================================================
CREATE TYPE public.vb_dispute_status AS ENUM (
    'submitted',         -- Initial state when user creates dispute
    'under_review',      -- Admin is reviewing the dispute
    'resolved'           -- Dispute has been resolved
);

-- =====================================================
-- 3. VB DISPUTES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS public.vb_disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Session reference
    session_id UUID NOT NULL REFERENCES public.vb_sessions(id) ON DELETE CASCADE,

    -- Parties involved
    user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    vb_id UUID NOT NULL REFERENCES public.venture_builders(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

    -- Dispute details
    reason public.vb_dispute_reason NOT NULL,
    custom_reason TEXT,  -- Only used when reason = 'other'
    description TEXT,    -- Optional detailed explanation

    -- Status tracking
    status public.vb_dispute_status DEFAULT 'submitted' NOT NULL,

    -- Admin resolution
    admin_notes TEXT,            -- Admin's notes/resolution details
    resolved_by UUID REFERENCES public.user_profiles(id),
    resolved_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_dispute_per_session UNIQUE(session_id),
    CONSTRAINT custom_reason_required CHECK (
        (reason != 'other') OR (custom_reason IS NOT NULL AND custom_reason != '')
    )
);

-- =====================================================
-- 4. INDEXES
-- =====================================================
CREATE INDEX idx_vb_disputes_session ON public.vb_disputes(session_id);
CREATE INDEX idx_vb_disputes_user ON public.vb_disputes(user_id);
CREATE INDEX idx_vb_disputes_vb ON public.vb_disputes(vb_id);
CREATE INDEX idx_vb_disputes_tenant ON public.vb_disputes(tenant_id);
CREATE INDEX idx_vb_disputes_status ON public.vb_disputes(status);
CREATE INDEX idx_vb_disputes_created_at ON public.vb_disputes(created_at DESC);

-- Index for admin queries: unresolved disputes
CREATE INDEX idx_vb_disputes_unresolved ON public.vb_disputes(status, created_at DESC)
    WHERE status IN ('submitted', 'under_review');

-- =====================================================
-- 5. TRIGGER FOR updated_at
-- =====================================================
CREATE TRIGGER trigger_vb_disputes_updated_at
    BEFORE UPDATE ON public.vb_disputes
    FOR EACH ROW
    EXECUTE FUNCTION public.update_vb_updated_at();

-- =====================================================
-- 6. ENABLE ROW LEVEL SECURITY
-- =====================================================
ALTER TABLE public.vb_disputes ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- 7. HELPFUL VIEW: Disputes with Session Details
-- =====================================================
CREATE OR REPLACE VIEW public.vb_disputes_with_details AS
SELECT
    d.id,
    d.session_id,
    d.user_id,
    d.vb_id,
    d.tenant_id,
    d.reason,
    d.custom_reason,
    d.description,
    d.status,
    d.admin_notes,
    d.resolved_by,
    d.resolved_at,
    d.created_at,
    d.updated_at,
    -- Session details
    s.session_datetime,
    s.credits_charged,
    s.status as session_status,
    -- User details
    u.full_name as user_name,
    u.email as user_email,
    -- VB details
    vb.contact_email as vb_email,
    -- Project details
    p.name as project_name
FROM public.vb_disputes d
JOIN public.vb_sessions s ON d.session_id = s.id
JOIN public.user_profiles u ON d.user_id = u.id
JOIN public.venture_builders vb ON d.vb_id = vb.id
LEFT JOIN public.vmp_projects p ON s.project_id = p.id;

-- =====================================================
-- 8. COMMENTS
-- =====================================================
COMMENT ON TABLE public.vb_disputes IS
'Dispute resolution system for VB coaching sessions. Users can report issues with completed sessions.';

COMMENT ON COLUMN public.vb_disputes.reason IS
'Reason for dispute: missed_session (VB no-show), time_theft (late/early), other (custom)';

COMMENT ON COLUMN public.vb_disputes.custom_reason IS
'Required when reason = other. Brief description of the custom reason.';

COMMENT ON COLUMN public.vb_disputes.description IS
'Optional detailed explanation from the user about the dispute.';

COMMENT ON COLUMN public.vb_disputes.status IS
'Lifecycle: submitted → under_review → resolved';

COMMENT ON CONSTRAINT unique_dispute_per_session ON public.vb_disputes IS
'Ensures only one dispute per session. Users cannot create duplicate disputes.';

-- =====================================================
-- END OF MIGRATION
-- =====================================================
