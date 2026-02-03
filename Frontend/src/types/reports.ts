// types/reports.ts

/**
 * Report type - specifies what is being reported
 */
export type ReportType = 'PROFILE' | 'MESSAGE';

/**
 * Report status - tracks lifecycle of a report
 */
export type ReportStatus = 'PENDING' | 'REVIEWED' | 'ACTIONED' | 'NO_ACTION';

/**
 * Report reason - why the content is being reported
 */
export type ReportReason =
  | 'SPAM_OR_SCAM'
  | 'HARASSMENT_OR_HATE'
  | 'MISREPRESENTATION'
  | 'OFF_PLATFORM_SOLICITATION'
  | 'ADULT_CONTENT'
  | 'DUPLICATE_ACCOUNT'
  | 'UNDERAGE_OR_NOT_FOUNDER'
  | 'OTHER';

/**
 * Human-readable labels for report reasons
 */
export const REPORT_REASON_LABELS: Record<ReportReason, string> = {
  SPAM_OR_SCAM: 'Spam or Scam',
  HARASSMENT_OR_HATE: 'Harassment or Hate Speech',
  MISREPRESENTATION: 'False Information or Impersonation',
  OFF_PLATFORM_SOLICITATION: 'Off-Platform Solicitation',
  ADULT_CONTENT: 'Inappropriate Adult Content',
  DUPLICATE_ACCOUNT: 'Duplicate Account',
  UNDERAGE_OR_NOT_FOUNDER: 'Does Not Meet Eligibility Requirements',
  OTHER: 'Other',
};

/**
 * Human-readable descriptions for report reasons
 */
export const REPORT_REASON_DESCRIPTIONS: Record<ReportReason, string> = {
  SPAM_OR_SCAM: 'This profile/message is spam or promoting scams',
  HARASSMENT_OR_HATE: 'This content contains harassment, threats, or hate speech',
  MISREPRESENTATION: 'This profile contains false information or is impersonating someone',
  OFF_PLATFORM_SOLICITATION: 'This user is trying to move the conversation off-platform inappropriately',
  ADULT_CONTENT: 'This content is inappropriate or contains adult material',
  DUPLICATE_ACCOUNT: 'This user has multiple accounts',
  UNDERAGE_OR_NOT_FOUNDER: 'This user does not meet the age or founder requirements',
  OTHER: 'Other reason (please provide details)',
};

/**
 * Report entity structure
 */
export interface Report {
  id: string;
  report_type: ReportType;
  reporter_user_id: string;
  reported_profile_id: string | null;
  reported_message_id: string | null;
  reason: ReportReason;
  description: string | null;
  status: ReportStatus;
  admin_notes: string | null;
  action_taken: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Request to report a profile
 */
export interface ReportProfileRequest {
  reported_profile_id: string;
  reason: ReportReason;
  description?: string;
}

/**
 * Request to report a message
 */
export interface ReportMessageRequest {
  message_id: string;
  reason: ReportReason;
  description?: string;
}

/**
 * Request to resolve a report (admin only)
 */
export interface ResolveReportRequest {
  status: 'REVIEWED' | 'ACTIONED' | 'NO_ACTION';
  admin_notes?: string;
  action_taken?: string;
}

/**
 * Report statistics for admin dashboard
 */
export interface ReportStatistics {
  total_reports: number;
  pending_reports: number;
  reviewed_reports: number;
  actioned_reports: number;
  no_action_reports: number;
  reports_by_reason: Record<ReportReason, number>;
}

/**
 * Report list response
 */
export interface ReportListResponse {
  success: boolean;
  message: string;
  data: Report[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Single report response
 */
export interface ReportResponse {
  success: boolean;
  message: string;
  data: Report;
}

/**
 * Report filters for listing
 */
export interface ReportFilters {
  status?: ReportStatus;
  report_type?: ReportType;
  page?: number;
  page_size?: number;
}
