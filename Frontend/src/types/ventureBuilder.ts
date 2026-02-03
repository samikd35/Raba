// types/ventureBuilder.ts
/**
 * Venture Builder Type Definitions
 *
 * This file contains all TypeScript interfaces and types for the Venture Builder feature:
 * - VB profiles, expertise areas, sessions, bookings, notes, earnings, disputes
 *
 * Base API: /api/venture-builder
 */

// ============================================================================
// ENUMS
// ============================================================================

export type VBStatus =
  | 'pending_profile'
  | 'pending_admin_review'
  | 'active'
  | 'inactive';

export type SessionStatus =
  | 'pending'
  | 'confirmed'
  | 'completed'
  | 'settled' // NEW - session has been paid/reconciled
  | 'canceled';

export type DisputeReason =
  | 'missed_session'
  | 'time_theft'
  | 'other';

export type DisputeStatus =
  | 'submitted'
  | 'under_review'
  | 'resolved';

// ============================================================================
// EXPERTISE AREAS
// ============================================================================

export interface ExpertiseArea {
  id: string; // UUID
  name: string;
  description?: string;
  display_order: number;
  is_active: boolean;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

export interface CreateExpertiseAreaPayload {
  name: string;
  description?: string;
  display_order: number;
}

export interface UpdateExpertiseAreaPayload {
  name?: string;
  description?: string;
  display_order?: number;
  is_active?: boolean;
}

// ============================================================================
// WORK EXPERIENCE
// ============================================================================

export interface WorkExperience {
  position: string;
  organization: string;
  years: string;
  description?: string;
}

// ============================================================================
// VB PROFILE
// ============================================================================

export interface VBProfile {
  id: string; // UUID
  user_id: string; // UUID
  name: string; // Full name (NEW - replaces first_name/last_name)
  contact_email?: string;
  main_expertise: string; // Primary expertise area (NEW)
  short_intro: string; // Short introduction (NEW)
  profile_picture_url?: string;
  biography: string; // 50-2000 chars
  linkedin_url?: string;
  work_experience?: WorkExperience[];
  expertise_areas?: ExpertiseArea[]; // Joined from expertise_ids
  areas_of_expertise?: ExpertiseArea[]; // Alternative field name from API
  status?: VBStatus;
  credit_price_per_hour?: number;
  calendar_booking_url?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
  // Deprecated fields (kept for backward compatibility)
  full_name?: string;
  first_name?: string;
  last_name?: string;
  // Google Calendar integration (DEPRECATED - removed from API)
  google_calendar_connected?: boolean;
  google_calendar_email?: string;
  selected_calendar_id?: string;
  calendar_timezone?: string;
}

export interface CreateVBProfilePayload {
  name: string; // Full name (NEW)
  contact_email: string;
  main_expertise: string; // Primary expertise (NEW)
  short_intro: string; // Short introduction (NEW)
  profile_picture_url?: string;
  biography: string; // 50-2000 chars
  linkedin_url?: string;
  work_experience: WorkExperience[];
  expertise_ids: string[]; // UUIDs
}

export interface UpdateVBProfilePayload {
  name?: string; // Full name (NEW)
  contact_email?: string;
  main_expertise?: string; // Primary expertise (NEW)
  short_intro?: string; // Short introduction (NEW)
  profile_picture_url?: string;
  biography?: string;
  linkedin_url?: string;
  work_experience?: WorkExperience[];
  expertise_ids?: string[];
}

export interface ApproveVBPayload {
  credit_price_per_hour: number;
  calendar_booking_url: string;
}

export interface UpdateVBPricingPayload {
  credit_price_per_hour: number;
}

export interface PublishVBPayload {
  is_active: boolean;
}

// ============================================================================
// VB BROWSE & SEARCH
// ============================================================================

export interface BrowseVBsParams {
  expertise_ids?: string[]; // UUIDs
  search_query?: string; // max 200 chars
  page?: number; // default 1
  page_size?: number; // default 20, max 100
}

export interface BrowseVBsResponse {
  total: number;
  items: VBProfile[];
  page: number;
  page_size: number;
}

// ============================================================================
// INVITATIONS
// ============================================================================

export interface SendVBInvitationPayload {
  email: string;
}

export interface SendVBInvitationResponse {
  success: boolean;
  message: string;
  token: string;
}

export interface ValidateInvitationPayload {
  token: string;
}

export interface ValidateInvitationResponse {
  valid: boolean;
  email: string | null;
  error: string | null;
}

// ============================================================================
// BOOKING
// ============================================================================

export interface TenantProject {
  id: string; // UUID
  name: string;
  tenant_id: string; // UUID
}

export interface CheckCreditsResponse {
  has_sufficient_credits: boolean;
  current_balance: number;
  required_credits: number;
  vb_credit_price: number;
}

export interface CreateBookingPayload {
  venture_builder_id: string; // UUID
  project_id: string; // UUID
  tenant_id: string; // UUID
  session_datetime: string; // ISO 8601
  accepted_terms_version: string; // e.g. "v1.0"
  agenda?: string; // NEW - optional session agenda/description
}

// ============================================================================
// SESSIONS
// ============================================================================

export interface VBSession {
  id: string; // UUID
  venture_builder_id: string; // UUID
  project_id: string; // UUID
  tenant_id: string; // UUID
  booked_by_user_id: string; // UUID (renamed from created_by_user_id)
  created_by_user_id?: string; // UUID (deprecated, kept for compatibility)
  session_datetime: string; // ISO datetime
  session_duration_minutes: number; // default 60
  status: SessionStatus;
  credits_charged: number;
  accepted_terms_version?: string;
  calendar_event_id?: string; // NEW
  agenda?: string; // NEW - session agenda/description
  created_at: string;
  updated_at?: string;
  // Joined data (NEW naming convention)
  vb_email?: string;
  vb_picture?: string;
  has_notes?: boolean;
  // Legacy joined data (kept for compatibility)
  venture_builder_name?: string;
  project_name?: string;
  tenant_name?: string;
  user_name?: string;
}

export interface GetSessionsParams {
  status_filter?: SessionStatus;
  start_date?: string; // ISO datetime
  end_date?: string; // ISO datetime
  page?: number;
  page_size?: number;
}

// ============================================================================
// SESSION NOTES
// ============================================================================

export interface SessionNote {
  id: string; // UUID
  vb_session_id: string; // UUID
  created_by_vb_id: string; // UUID
  main_outcomes: string; // 10-5000 chars
  key_takeaways: string; // 10-5000 chars
  next_steps?: string; // max 2000 chars
  visible_to_user: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateSessionNotePayload {
  vb_session_id: string; // UUID
  main_outcomes: string; // 10-5000 chars
  key_takeaways: string; // 10-5000 chars
  next_steps?: string; // max 2000 chars
  visible_to_user: boolean;
}

export interface UpdateSessionNotePayload {
  main_outcomes?: string;
  key_takeaways?: string;
  next_steps?: string;
  visible_to_user?: boolean;
}

// ============================================================================
// EARNINGS
// ============================================================================

export interface SessionEarning {
  id: string; // Session ID (NEW naming)
  session_id?: string; // Deprecated
  session_datetime: string; // NEW naming
  session_date?: string; // Deprecated
  tenant_name?: string;
  project_name?: string;
  credits_charged: number;
  earnings_usd: number; // NEW naming
  gross_usd?: number; // Deprecated
  commission_usd: number;
  net_earnings_usd: number; // NEW naming
  net_usd?: number; // Deprecated
  status: SessionStatus; // NEW - includes session status
}

export interface EarningsResponse {
  total_earned_credits: number;
  total_earnings_usd: number;
  commission_amount_usd: number;
  net_earnings_usd: number;
  total_reconciled_payments: number; // NEW - total lifetime reconciled
  pending_amount_usd: number; // NEW - pending earnings
  completed_sessions_period: number;
  total_sessions_all_time: number;
  sessions: SessionEarning[];
  date_range_start?: string; // ISO datetime
  date_range_end?: string; // ISO datetime
}

export interface GetEarningsParams {
  start_date?: string; // ISO datetime
  end_date?: string; // ISO datetime
}

export interface EarningsConfig {
  credit_to_usd_rate: number;
  commission_rate: number; // 0-1 (e.g., 0.2 for 20%)
  updated_at: string;
}

export interface UpdateEarningsConfigPayload {
  credit_to_usd_rate?: number;
  commission_rate?: number; // 0-1
}

// ============================================================================
// DISPUTES
// ============================================================================

export interface Dispute {
  id: string; // UUID
  session_id: string; // UUID (NEW naming)
  vb_session_id?: string; // UUID (deprecated)
  tenant_id: string; // UUID (NEW)
  created_by_user_id: string; // UUID
  reason: DisputeReason;
  custom_reason?: string; // required if reason=other, max 200 chars (NEW limit)
  description?: string; // max 2000 chars
  status: DisputeStatus;
  admin_notes?: string; // max 2000 chars
  resolved_by?: string; // UUID (NEW - admin who resolved)
  resolved_at?: string;
  created_at: string;
  updated_at: string;
  // Joined data (NEW)
  session_datetime?: string;
  vb_name?: string;
  user_email?: string;
  // Deprecated joined data
  venture_builder_name?: string;
  project_name?: string;
}

export interface CanOpenDisputeResponse {
  can_open_dispute: boolean;
  reason?: string;
}

export interface CreateDisputePayload {
  reason: DisputeReason;
  custom_reason?: string; // required if reason=other, max 200 chars
  description?: string; // max 2000 chars
}

export interface GetDisputesParams {
  page?: number; // default 1
  page_size?: number; // default 20, max 100
}

export interface GetDisputesResponse {
  disputes: Dispute[];
  total_count: number;
  page: number;
  total_pages: number;
}

export interface GetAdminDisputesParams {
  status?: DisputeStatus;
  vb_id?: string; // UUID
  start_date?: string; // ISO datetime
  end_date?: string; // ISO datetime
  page?: number;
  page_size?: number;
}

export interface UpdateDisputePayload {
  status?: DisputeStatus;
  admin_notes?: string; // max 2000 chars
}

// ============================================================================
// GOOGLE CALENDAR INTEGRATION
// ============================================================================

export type CalendarConnectionStatus =
  | 'not_connected'
  | 'connected_no_calendar'
  | 'connected'
  | 'error';

export interface GoogleCalendarConnection {
  connected: boolean;
  email?: string;
  selected_calendar_id?: string;
  calendar_name?: string;
  timezone?: string;
  last_sync?: string; // ISO datetime
  error?: string;
}

export interface GoogleCalendarList {
  id: string;
  summary: string; // Calendar name
  description?: string;
  timezone?: string; // Optional - may not always be returned by API
  primary?: boolean;
}

export interface ConnectCalendarResponse {
  oauth_url: string;
}

export interface SelectCalendarPayload {
  calendar_id: string;
}

export interface DisconnectCalendarResponse {
  success: boolean;
  message: string;
}

// ============================================================================
// AVAILABILITY SLOTS (NEW API)
// ============================================================================

// Day of week type (string for convenience, converted to number for API)
export type DayOfWeek =
  | 'sunday'
  | 'monday'
  | 'tuesday'
  | 'wednesday'
  | 'thursday'
  | 'friday'
  | 'saturday';

/**
 * A single 1-hour availability slot for a specific day of week
 * Each slot represents one bookable hour on a given weekday
 */
export interface AvailabilitySlot {
  id: string; // UUID
  vb_id: string; // UUID
  day_of_week: number; // 0=Sunday to 6=Saturday
  session_start: string; // HH:MM:SS format (e.g. "09:00:00")
  session_end: string; // HH:MM:SS format (computed, start + 1 hour)
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

/**
 * Payload for creating new availability slots
 * POST /{vb_id}/availability-slots
 */
export interface CreateAvailabilitySlotsPayload {
  slots: Array<{
    day_of_week: number; // 0=Sunday to 6=Saturday
    session_start: string; // HH:MM:SS format (e.g. "09:00:00")
  }>;
}

/**
 * Payload for deleting availability slots
 * DELETE /{vb_id}/availability-slots
 */
export interface DeleteAvailabilitySlotsPayload {
  slots: Array<{
    day_of_week: number; // 0=Sunday to 6=Saturday
    session_start: string; // HH:MM:SS format (e.g. "09:00:00")
  }>;
}

// ============================================================================
// BOOKABLE AVAILABILITY (Real-time availability for booking)
// ============================================================================

/**
 * A bookable time slot with availability status
 */
export interface BookableSlot {
  start: string; // ISO datetime (e.g. "2025-01-15T14:00:00+00:00")
  end: string; // ISO datetime (e.g. "2025-01-15T15:00:00+00:00")
  available: boolean; // true if slot is available for booking
}

/**
 * Parameters for fetching bookable slots
 * GET /{vb_id}/availability?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
 */
export interface GetAvailabilityParams {
  vb_id: string;
  start_date: string; // YYYY-MM-DD
  end_date: string; // YYYY-MM-DD
}

/**
 * Response from bookable slots endpoint
 */
export interface GetAvailabilityResponse {
  vb_id: string;
  time_zone: string; // e.g. "America/New_York"
  date_range: {
    start_date: string; // YYYY-MM-DD
    end_date: string; // YYYY-MM-DD
  };
  slots: BookableSlot[];
}

// ============================================================================
// LEGACY TYPES (kept for backward compatibility during migration)
// ============================================================================

/** @deprecated Use AvailabilitySlot instead */
export interface AvailabilityWindow {
  id?: string;
  day_of_week: DayOfWeek;
  start_time: string;
  end_time: string;
  session_length_minutes: number;
}

/** @deprecated Use AvailabilitySlot[] instead */
export interface AvailabilityProfile {
  vb_id: string;
  windows: AvailabilityWindow[];
  timezone: string;
  updated_at: string;
}

/** @deprecated Use CreateAvailabilitySlotsPayload instead */
export interface CreateAvailabilityWindowPayload {
  day_of_week: DayOfWeek;
  start_time: string;
  end_time: string;
  session_length_minutes?: number;
}

/** @deprecated Use CreateAvailabilitySlotsPayload instead */
export interface UpdateAvailabilityProfilePayload {
  profiles: Array<{
    day_of_week: number;
    start_time: string;
    end_time: string;
    session_length_minutes: number;
    buffer_before_minutes: number;
    buffer_after_minutes: number;
    max_sessions_per_day: number;
  }>;
}

/** @deprecated Use BookableSlot instead */
export interface AvailableSlot {
  start: string;
  end: string;
  duration_minutes: number;
}

// ============================================================================
// RESCHEDULE
// ============================================================================

export interface RescheduleSessionPayload {
  reason: string; // VB's reason for rescheduling
  apology_message?: string; // Optional personalized message
}

export interface RescheduleSessionResponse {
  success: boolean;
  reschedule_token: string;
  reschedule_url: string; // Frontend URL: /reschedule/{token}
  expires_at: string; // ISO datetime
}

export interface ValidateRescheduleTokenResponse {
  valid: boolean;
  session?: VBSession;
  vb_name?: string;
  original_time?: string;
  apology_message?: string;
  available_slots?: AvailableSlot[];
}

export interface RescheduleBookPayload {
  new_start: string; // ISO datetime
  new_end: string; // ISO datetime
}

export interface RescheduleBookResponse {
  success: boolean;
  updated_session: VBSession;
  message: string;
}

// ============================================================================
// VB PROJECTS (Portal Access)
// ============================================================================

export interface VBProject {
  id: string; // UUID
  name: string;
  tenant_id: string; // UUID
  description?: string;
  created_at: string;
}

// ============================================================================
// ADMIN - EXPERTISE MANAGEMENT
// ============================================================================

export interface AdminExpertiseAreaUpdate {
  name?: string;
  description?: string;
  display_order?: number;
  is_active?: boolean;
}

// ============================================================================
// ADMIN - RECONCILIATION
// ============================================================================

export interface ReconcilePayload {
  start_date?: string; // ISO datetime
  end_date?: string; // ISO datetime
  notes?: string;
}

export interface ReconciliationRecord {
  id: string; // UUID
  venture_builder_id: string; // UUID
  reconciled_by: string; // UUID
  reconciled_by_name?: string;
  reconciled_by_email?: string;
  amount_reconciled_usd: number;
  pending_amount_before: number;
  session_count: number;
  start_date?: string;
  end_date?: string;
  notes?: string;
  created_at: string;
}

export interface ReconcileResponse {
  reconciliation_id: string;
  venture_builder_id: string;
  amount_reconciled_usd: number;
  pending_amount_before: number;
  pending_amount_after: number;
  session_count: number;
  sessions_marked_settled: number;
  total_reconciled_lifetime: number;
  start_date?: string;
  end_date?: string;
  notes?: string;
  created_at: string;
}

export interface ReconciliationHistoryResponse {
  reconciliations: ReconciliationRecord[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}
