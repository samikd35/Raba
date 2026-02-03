# Cofounder Reports Database Schema

## Table: `public.cofounder_reports`

This table stores all reports (both profile and message reports) for the cofounder matching feature.

### SQL Schema

```sql
CREATE TABLE public.cofounder_reports (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Report type and target
    report_type VARCHAR(20) NOT NULL CHECK (report_type IN ('PROFILE', 'MESSAGE')),

    -- Reporter information
    reporter_user_id UUID NOT NULL,

    -- Reported entities
    reported_profile_id UUID,
    reported_user_id UUID,
    reported_message_id UUID,

    -- Report details
    reason VARCHAR(50) NOT NULL CHECK (reason IN (
        'SPAM_OR_SCAM',
        'HARASSMENT_OR_HATE',
        'MISREPRESENTATION',
        'OFF_PLATFORM_SOLICITATION',
        'ADULT_CONTENT',
        'DUPLICATE_ACCOUNT',
        'UNDERAGE_OR_NOT_FOUNDER',
        'OTHER'
    )),
    description TEXT,

    -- Report status
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN (
        'PENDING',
        'REVIEWED',
        'ACTIONED',
        'NO_ACTION'
    )),

    -- Admin resolution
    admin_notes TEXT,
    action_taken TEXT,
    resolved_by UUID,
    resolved_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_report_target CHECK (
        (report_type = 'PROFILE' AND reported_profile_id IS NOT NULL AND reported_message_id IS NULL) OR
        (report_type = 'MESSAGE' AND reported_message_id IS NOT NULL)
    ),
    CONSTRAINT description_required_for_other CHECK (
        reason != 'OTHER' OR description IS NOT NULL
    )
);

-- Indexes for performance
CREATE INDEX idx_cofounder_reports_status ON public.cofounder_reports(status);
CREATE INDEX idx_cofounder_reports_reporter ON public.cofounder_reports(reporter_user_id);
CREATE INDEX idx_cofounder_reports_reported_user ON public.cofounder_reports(reported_user_id);
CREATE INDEX idx_cofounder_reports_reported_profile ON public.cofounder_reports(reported_profile_id);
CREATE INDEX idx_cofounder_reports_reported_message ON public.cofounder_reports(reported_message_id);
CREATE INDEX idx_cofounder_reports_reason ON public.cofounder_reports(reason);
CREATE INDEX idx_cofounder_reports_created_at ON public.cofounder_reports(created_at DESC);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_cofounder_reports_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_cofounder_reports_updated_at
    BEFORE UPDATE ON public.cofounder_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_cofounder_reports_updated_at();

-- Enable Row Level Security
ALTER TABLE public.cofounder_reports ENABLE ROW LEVEL SECURITY;
```

## Field Descriptions

### Core Fields

- **id**: Unique identifier for the report (UUID)
- **report_type**: Type of report - either 'PROFILE' or 'MESSAGE'
- **reporter_user_id**: ID of the user who created the report
- **reported_profile_id**: ID of the profile being reported (for profile reports)
- **reported_user_id**: ID of the user who owns the reported profile (for easy querying)
- **reported_message_id**: ID of the message being reported (for message reports)

### Report Details

- **reason**: Reason for the report, must be one of:
  - `SPAM_OR_SCAM`: Spam or scam content
  - `HARASSMENT_OR_HATE`: Harassment or hate speech
  - `MISREPRESENTATION`: False information or impersonation
  - `OFF_PLATFORM_SOLICITATION`: Attempting to move conversation off-platform inappropriately
  - `ADULT_CONTENT`: Inappropriate adult content
  - `DUPLICATE_ACCOUNT`: User has multiple accounts
  - `UNDERAGE_OR_NOT_FOUNDER`: User doesn't meet eligibility requirements
  - `OTHER`: Other reason (requires description)

- **description**: Optional free text for additional context (required when reason is 'OTHER')

### Status and Resolution

- **status**: Current status of the report:
  - `PENDING`: Newly created, awaiting review
  - `REVIEWED`: Admin has reviewed but not yet taken action
  - `ACTIONED`: Admin has taken action (e.g., banned user, removed content)
  - `NO_ACTION`: Admin reviewed and determined no action needed

- **admin_notes**: Internal notes from the admin reviewing the report
- **action_taken**: Description of what action was taken (if any)
- **resolved_by**: User ID of the admin who resolved the report
- **resolved_at**: Timestamp when the report was resolved

### Timestamps

- **created_at**: When the report was created
- **updated_at**: When the report was last updated (auto-updated by trigger)

## API Endpoints

### User Endpoints

1. **POST /profiles/reports/profile** - Report a profile
2. **POST /profiles/reports/message** - Report a message

### Admin Endpoints

1. **GET /profiles/reports/** - List all reports (with filters)
2. **GET /profiles/reports/stats** - Get report statistics
3. **GET /profiles/reports/by-user/{user_id}** - Get all reports for a specific user
4. **GET /profiles/reports/by-profile/{profile_id}** - Get all reports for a specific profile
5. **GET /profiles/reports/{report_id}** - Get a specific report
6. **POST /profiles/reports/{report_id}/resolve** - Resolve a report

## Notes

- The `reported_user_id` field is populated automatically from the profile's user_id when creating a profile report
- Reports cannot be deleted, only resolved
- Users cannot report their own profiles
- Users cannot create duplicate reports (same reporter, same target, pending status)
- When reason is 'OTHER', description is required
- The constraint `valid_report_target` ensures that profile reports have a profile_id and message reports have a message_id
- Row Level Security is enabled but no policies are defined (access control handled at application level)
