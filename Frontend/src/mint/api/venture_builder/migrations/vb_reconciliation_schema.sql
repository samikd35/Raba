-- =====================================================
-- Venture Builder Reconciliation Schema Migration
-- Adds payment reconciliation tracking for VB earnings
-- =====================================================

-- =====================================================
-- 1. ADD SETTLED STATUS TO VB SESSION STATUS ENUM
-- =====================================================
-- Add 'settled' status to track sessions that have been paid/reconciled
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'settled'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'vb_session_status')
    ) THEN
        ALTER TYPE public.vb_session_status ADD VALUE 'settled';
    END IF;
END$$;

-- =====================================================
-- 2. ADD RECONCILIATION FIELD TO VENTURE BUILDERS
-- =====================================================
-- Track cumulative reconciled payments over VB's lifetime
ALTER TABLE public.venture_builders
ADD COLUMN IF NOT EXISTS total_reconciled_payments DECIMAL(12, 2) DEFAULT 0.00 NOT NULL;

-- Constraint to ensure non-negative reconciled amount
ALTER TABLE public.venture_builders
ADD CONSTRAINT valid_reconciled_payments CHECK (total_reconciled_payments >= 0);

-- =====================================================
-- 2. VB RECONCILIATIONS TABLE
-- =====================================================
-- Tracks each reconciliation event (payment settlement)
CREATE TABLE IF NOT EXISTS public.vb_reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_builder_id UUID NOT NULL REFERENCES public.venture_builders(id) ON DELETE CASCADE,
    reconciled_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- Financial amounts (in USD)
    amount_reconciled_usd DECIMAL(12, 2) NOT NULL,
    pending_amount_before DECIMAL(12, 2) NOT NULL,

    -- Session metadata
    session_count INTEGER NOT NULL DEFAULT 0,
    start_date TIMESTAMPTZ, -- Date range of sessions being reconciled
    end_date TIMESTAMPTZ,

    -- Additional context
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_reconciliation_amount CHECK (amount_reconciled_usd > 0),
    CONSTRAINT valid_pending_before CHECK (pending_amount_before >= 0),
    CONSTRAINT valid_session_count CHECK (session_count >= 0),
    CONSTRAINT valid_date_range CHECK (start_date IS NULL OR end_date IS NULL OR start_date <= end_date)
);

-- Indexes for efficient queries
CREATE INDEX idx_vb_reconciliations_vb ON public.vb_reconciliations(venture_builder_id);
CREATE INDEX idx_vb_reconciliations_reconciled_by ON public.vb_reconciliations(reconciled_by);
CREATE INDEX idx_vb_reconciliations_created_at ON public.vb_reconciliations(created_at DESC);

-- =====================================================
-- 3. HELPFUL VIEW - VB Reconciliation History
-- =====================================================
CREATE OR REPLACE VIEW public.vb_reconciliation_history AS
SELECT
    r.id,
    r.venture_builder_id,
    vb.contact_email as vb_email,
    up.full_name as reconciled_by_name,
    up.email as reconciled_by_email,
    r.amount_reconciled_usd,
    r.pending_amount_before,
    r.session_count,
    r.start_date,
    r.end_date,
    r.notes,
    r.created_at
FROM public.vb_reconciliations r
JOIN public.venture_builders vb ON r.venture_builder_id = vb.id
JOIN public.user_profiles up ON r.reconciled_by = up.id
ORDER BY r.created_at DESC;

-- =====================================================
-- 4. ENABLE ROW LEVEL SECURITY
-- =====================================================
ALTER TABLE public.vb_reconciliations ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- 5. COMMENT DOCUMENTATION
-- =====================================================
COMMENT ON TABLE public.vb_reconciliations IS 'Tracks payment reconciliation events for Venture Builders. Each record represents an admin action to mark pending earnings as settled/paid.';
COMMENT ON COLUMN public.venture_builders.total_reconciled_payments IS 'Cumulative total of all reconciled payments (in USD) since VB account creation. Updated on each reconciliation.';
COMMENT ON COLUMN public.vb_reconciliations.amount_reconciled_usd IS 'Amount being reconciled/settled in this transaction (USD)';
COMMENT ON COLUMN public.vb_reconciliations.pending_amount_before IS 'Snapshot of pending amount before this reconciliation (for audit trail)';
COMMENT ON COLUMN public.vb_reconciliations.session_count IS 'Number of completed sessions included in this reconciliation period';

-- =====================================================
-- END OF MIGRATION
-- =====================================================
