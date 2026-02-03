// types/cofounder.ts

export type ProfileStatus = 'draft' | 'submitted' | 'approved' | 'rejected';

export type Commitment = 'Full-time' | 'Part-time';

export type Importance = 'non_negotiable' | 'important';

export type Gender = 'Male' | 'Female' | 'Prefer not to say';

/**
 * Employment history entry
 */
export interface EmploymentEntry {
  organization: string;
  role: string;
  start_date: string; // YYYY-MM format
  end_date: string | null; // YYYY-MM or null for "Present"
  is_current: boolean;
  responsibilities: string; // 280-600 characters
}

/**
 * Employment history structure
 */
export interface EmploymentHistory {
  entries: EmploymentEntry[];
}

/**
 * Language with importance metadata
 */
export interface LanguagePreference {
  language: string; // Language ID (e.g., 'english', 'spanish') - transformed to/from language_id for API
  code?: string; // Backend may send 'code' in some responses - for backwards compatibility
  importance: Importance;
}

/**
 * Age preference settings
 */
export interface AgePreference {
  enabled: boolean;
  min: number | null; // 20-50
  max: number | null; // 20-50
  importance: Importance | null;
}

/**
 * Complete Profile Version structure
 * This represents a snapshot of a user's cofounder profile at a specific point in time
 */
export interface ProfileVersion {
  // Metadata
  id: string;
  profile_id: string;
  user_id?: string; // User ID - included in directory search results for messaging
  status: ProfileStatus;
  review_reason: string | null;

  // Identity - Basic Information
  first_name: string;
  last_name: string;
  gender: Gender;
  date_of_birth: string; // YYYY-MM-DD (never displayed publicly, used for age matching)
  email: string;
  profile_picture_url: string;
  country: string; // Country of residence
  linkedin_url: string;
  website_url: string | null;

  // Background & Experience
  education: string[]; // Array of education entries (e.g., "University of Nairobi — MSc Finance — 2018")
  employment_history: EmploymentHistory; // Structured employment history
  achievement: string; // Notable achievement
  personal_statement: string; // Bio / Personal statement (2-4 sentences recommended)
  social_links: Record<string, string>; // Additional social media links
  professional_background: string; // Display-only field (e.g., "Software", "Finance")

  // Matching Preferences - What user offers and needs
  industries_of_interest: string[]; // Industries/topics of interest (2-5 recommended)
  responsibilities_offered: string[]; // What responsibilities user can own
  skills_needed: string[]; // Skills needed in a cofounder

  // Location & Communication
  preferred_languages: LanguagePreference[]; // Languages with per-language importance
  language_importance: Importance; // Overall language matching importance
  preferred_country: string; // Preferred cofounder country
  preferred_country_importance: Importance; // Country matching importance

  // Commitment & Stage
  expected_commitment: Commitment; // User's own commitment level
  preferred_commitment: Commitment; // Expected cofounder commitment
  commitment_importance: Importance; // Commitment matching importance
  venture_stage: string[]; // User's current entrepreneurial stage
  preferred_venture_stage: string[]; // Preferred cofounder venture stages

  // Optional Age Filtering
  age_enabled: boolean;
  age_min: number | null;
  age_max: number | null;
  age_importance: Importance | null;

  // Timestamps
  submitted_at: string | null; // ISO-8601
  reviewed_at: string | null; // ISO-8601
  created_at: string; // ISO-8601
  updated_at?: string; // ISO-8601
  ideal_cofounder_description?: string; // Optional description of ideal cofounder
}

/**
 * Profile summary from GET /profiles/me/
 */
export interface ProfileSummary {
  profile: {
    id: string;
    user_id: string;
    status: ProfileStatus;
    last_approved_version_id: string | null;
  } | null;
  last_approved: ProfileVersion | null;
  latest_version: ProfileVersion | null;
}

/**
 * Draft profile input (for creating/updating drafts)
 * All fields from ProfileVersion except metadata
 */
export type DraftProfileIn = Omit<
  ProfileVersion,
  'id' | 'profile_id' | 'status' | 'review_reason' | 'submitted_at' | 'reviewed_at' | 'created_at' | 'updated_at'
>;

/**
 * Submit response
 */
export interface SubmitResponse {
  ok: boolean;
  version_id: string;
}

/**
 * List response wrapper
 */
export interface ProfileVersionsListResponse {
  items: ProfileVersion[];
}

// ============================================================================
// ADMIN TYPES
// ============================================================================

/**
 * Admin approval response
 */
export interface AdminActionResponse {
  ok: boolean;
}

/**
 * Admin rejection request
 */
export interface AdminRejectRequest {
  reason: string;
}

// ============================================================================
// ENUMS TYPES
// ============================================================================

/**
 * Enum item structure (industries, responsibilities, commitments, venture stages)
 */
export interface EnumItem {
  id: string;
  slug: string; // Auto-generated from name
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Enum create/update payload
 */
export interface EnumItemPayload {
  name: string;
  description?: string;
  is_active?: boolean;
}

/**
 * Enum list response
 */
export interface EnumListResponse {
  success: boolean;
  message: string;
  data: EnumItem[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Enum single item response
 */
export interface EnumItemResponse {
  success: boolean;
  message: string;
  data: EnumItem;
}

/**
 * Enum resource types
 */
export type EnumResource = 'industries' | 'responsibilities' | 'commitment' | 'venture_stages' | 'languages';

// ============================================================================
// DIRECTORY & BROWSE TYPES
// ============================================================================

/**
 * Profile data returned from directory search with additional fields
 */
export interface DirectoryProfile {
  // Profile identifiers
  profile_id: string;
  version_id: string;
  user_id: string;

  // Basic info
  full_name: string;
  first_name?: string;
  last_name?: string;
  profile_picture_url: string;
  professional_background?: string;
  date_of_birth?: string;

  // Location
  country: string;

  // Messaging
  can_message?: boolean; // Whether user can message this cofounder (rate limiting)

  // Preferences
  preferred_commitment?: string;
  preferred_languages?: Array<{ code?: string; language?: string; importance?: string }>;
  preferred_venture_stage?: string[];

  // Match score data (only present in matches endpoint)
  score?: number;
  components?: {
    industries?: number;
    skills_comp?: number;
    language?: number;
    country?: number;
    commitment?: number;
    venture?: number;
    age?: number;
  };

  // Match-specific fields
  candidate_profile_id?: string;
  candidate_version_id?: string;
}

// ============================================================================
// FORM STATE TYPES (for wizard UI)
// ============================================================================

/**
 * Form data structure for the profile wizard
 * Matches the 6-step wizard in UI requirements
 *
 * NOTE: profile_picture_url is used for DISPLAY/PREVIEW only in the form.
 * - When uploading: Contains blob URL (blob:...) for local preview
 * - When editing existing: Contains actual URL from backend
 * - The actual FILE upload is handled separately via FormData
 */
export interface ProfileFormData {
  // Step 1: Identity
  first_name: string;
  last_name: string;
  gender: Gender;
  date_of_birth: string;
  email: string;
  profile_picture_url: string; // For preview only - actual file sent separately
  country: string;
  linkedin_url: string;
  website_url: string;
  education: string[];
  employment_history: EmploymentHistory;
  achievement: string;
  personal_statement: string;
  social_links: Record<string, string>;

  // Step 2: Professional & Interests
  professional_background: string;
  industries_of_interest: string[];

  // Step 3: Capabilities
  responsibilities_offered: string[];
  skills_needed: string[];

  // Step 4: Languages & Location
  preferred_country: string;
  preferred_country_importance: Importance;
  preferred_languages: LanguagePreference[];

  // Step 5: Commitment & Stage
  expected_commitment: Commitment;
  preferred_commitment: Commitment;
  commitment_importance: Importance;
  venture_stage: string[];
  preferred_venture_stage: string[];

  // Step 6: Age Preference
  age_preference: AgePreference;
}

/**
 * Wizard step validation state
 */
export interface StepValidation {
  isValid: boolean;
  errors: string[];
}

/**
 * Wizard step (0 = Community Declaration, 1-6 = Profile Steps)
 */
export type WizardStep = 0 | 1 | 2 | 3 | 4 | 5 | 6;

/**
 * Profile state for UI
 */
export type ProfileUIState =
  | 'no_profile' // No drafts, no versions
  | 'has_draft' // Has unsaved draft
  | 'pending_review' // Submitted, awaiting admin approval
  | 'rejected' // Last submission was rejected
  | 'approved'; // Has approved profile

// ============================================================================
// VALIDATION & ERROR TYPES
// ============================================================================

/**
 * API Error response
 */
export interface ApiError {
  message: string;
  status?: number;
  details?: Record<string, any>;
}

/**
 * Field validation error
 */
export interface FieldError {
  field: string;
  message: string;
}
