-- =====================================================
-- VB Interest Submissions Schema
-- =====================================================
-- This migration creates the table for storing Venture Builder
-- Declaration of Interest form submissions.
-- 
-- Run this migration in Supabase SQL Editor or via CLI.
-- =====================================================

-- Create the vb_interest_submissions table
CREATE TABLE IF NOT EXISTS vb_interest_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Personal Information
    full_name TEXT NOT NULL,
    work_email TEXT NOT NULL,
    phone_country_code TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    
    -- Professional Profile
    primary_role TEXT NOT NULL,
    company_organization TEXT,
    linkedin_url TEXT NOT NULL,
    personal_website TEXT,
    
    -- Venture Building Experience
    has_founded_venture BOOLEAN NOT NULL DEFAULT FALSE,
    ventures_founded_count INTEGER,
    ventures_stage_reached TEXT,
    ventures_outcome TEXT,
    coaching_experience TEXT NOT NULL,
    programs_worked_with TEXT,
    
    -- Expertise & Coverage (stored as JSONB for flexibility with arrays)
    support_areas JSONB NOT NULL DEFAULT '[]'::jsonb,
    support_areas_other TEXT,
    industries_of_focus JSONB NOT NULL DEFAULT '[]'::jsonb,
    industries_other TEXT,
    founder_stages JSONB NOT NULL DEFAULT '[]'::jsonb,
    founder_stages_other TEXT,
    geographies JSONB NOT NULL DEFAULT '[]'::jsonb,
    geographies_specific_countries TEXT,
    languages JSONB NOT NULL DEFAULT '[]'::jsonb,
    languages_other TEXT,
    weekly_availability TEXT NOT NULL,
    weekly_availability_other TEXT,
    hourly_rate_usd DECIMAL(10, 2) NOT NULL,
    
    -- Submission Status
    status TEXT NOT NULL DEFAULT 'pending',
    
    -- Admin Review
    reviewed_by UUID REFERENCES auth.users(id),
    reviewed_at TIMESTAMPTZ,
    admin_notes TEXT,
    rejection_reason TEXT,
    
    -- Link to invitation (if approved and invited)
    vb_invitation_id UUID REFERENCES vb_invitations(id),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unique constraint on email to prevent duplicate submissions
CREATE UNIQUE INDEX IF NOT EXISTS idx_vb_interest_email_unique 
ON vb_interest_submissions(work_email);

-- Index for filtering by status
CREATE INDEX IF NOT EXISTS idx_vb_interest_status 
ON vb_interest_submissions(status);

-- Index for sorting by creation date
CREATE INDEX IF NOT EXISTS idx_vb_interest_created 
ON vb_interest_submissions(created_at DESC);

-- Check constraint for status values
ALTER TABLE vb_interest_submissions 
DROP CONSTRAINT IF EXISTS vb_interest_status_check;

ALTER TABLE vb_interest_submissions 
ADD CONSTRAINT vb_interest_status_check 
CHECK (status IN ('pending', 'approved', 'rejected', 'invited'));

-- Check constraint for coaching experience values
ALTER TABLE vb_interest_submissions 
DROP CONSTRAINT IF EXISTS vb_interest_coaching_check;

ALTER TABLE vb_interest_submissions 
ADD CONSTRAINT vb_interest_coaching_check 
CHECK (coaching_experience IN ('none', '1-2_years', '3-5_years', '5+_years'));

-- Check constraint for weekly availability values
ALTER TABLE vb_interest_submissions 
DROP CONSTRAINT IF EXISTS vb_interest_availability_check;

ALTER TABLE vb_interest_submissions 
ADD CONSTRAINT vb_interest_availability_check 
CHECK (weekly_availability IN ('2_hrs', '4_hrs', '6_hrs', '8_hrs', '10_hrs', 'other'));

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_vb_interest_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS vb_interest_updated_at_trigger ON vb_interest_submissions;

CREATE TRIGGER vb_interest_updated_at_trigger
    BEFORE UPDATE ON vb_interest_submissions
    FOR EACH ROW
    EXECUTE FUNCTION update_vb_interest_updated_at();

-- Enable RLS
ALTER TABLE vb_interest_submissions ENABLE ROW LEVEL SECURITY;

-- RLS Policies

-- Policy: Allow anonymous/public to insert (submit interest form)
DROP POLICY IF EXISTS "Allow public to submit interest" ON vb_interest_submissions;
CREATE POLICY "Allow public to submit interest"
ON vb_interest_submissions
FOR INSERT
TO anon, authenticated
WITH CHECK (true);

-- Policy: Allow admins to view all submissions
DROP POLICY IF EXISTS "Allow admins to view all submissions" ON vb_interest_submissions;
CREATE POLICY "Allow admins to view all submissions"
ON vb_interest_submissions
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM user_profiles up
        WHERE up.id = auth.uid()
        AND up.role IN ('admin', 'super_admin')
    )
);

-- Policy: Allow admins to update submissions
DROP POLICY IF EXISTS "Allow admins to update submissions" ON vb_interest_submissions;
CREATE POLICY "Allow admins to update submissions"
ON vb_interest_submissions
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM user_profiles up
        WHERE up.id = auth.uid()
        AND up.role IN ('admin', 'super_admin')
    )
);

-- Policy: Allow submitters to check their own submission status by email
-- Note: This is handled via service role in the API, not direct RLS

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON vb_interest_submissions TO authenticated;
GRANT INSERT ON vb_interest_submissions TO anon;

-- =====================================================
-- Migration Complete
-- =====================================================
