// Organization Management Types

export interface Organization {
  id: string;
  name: string;
  description?: string;
  website?: string;
  industry?: string;
  size?: string;
  country: string;
  city: string;
  contact_email: string;
  phone_number: string;
  type?: 'prepay_org' | 'grant_org' | 'postpay_org';
  monthly_credit_limit?: number;
  created_at: string;
  updated_at: string;
  status: 'active' | 'suspended' | 'frozen';
  // Backend API fields (from /admin/list endpoint)
  total_credits?: number;
  used_credits?: number;
  total_members?: number;
  total_teams?: number;
  // Legacy fields for backward compatibility
  current_monthly_usage?: number;
}

export interface OrganizationTypeResponse {
  success: boolean;
  organization_type: 'grant_org' | 'prepay_org' | 'postpay_org';
}

export interface OrganizationInvite {
  id: string;
  email: string;
  organization_type: 'prepay_org' | 'grant_org' | 'postpay_org';
  monthly_credit_limit?: number;
  status: 'pending' | 'accepted' | 'expired';
  created_at: string;
  expires_at: string;
}

export interface Team {
  id: string;
  name: string;
  organization_id: string;
  team_leader_id: string;
  team_leader_name: string;
  team_leader_email: string;
  member_count: number;
  credit_pool_total: number;
  credit_pool_used: number;
  credit_pool_remaining: number;
  pool_reset_date: string;
  status: 'active' | 'suspended' | 'frozen';
  created_at: string;
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'member' | 'team_leader' | 'admin';
  team_id?: string;
  team_name?: string;
  credits_allocated: number;
  credits_used: number;
  status: 'active' | 'frozen' | 'suspended';
  joined_date: string;
}

export interface OrganizationAdmin {
  id: string;
  name: string;
  email: string;
  organization_id: string;
  organization_name: string;
  role: 'admin';
  status: 'active' | 'suspended';
  created_at: string;
}

export interface CreditSummary {
  total_credits: number;
  used_credits: number;
  remaining_credits: number;
  monthly_limit: number;
  reset_date: string;
}

export interface InvitationAnalytics {
  total_invitations_sent: number;
  invitations_accepted: number;
  acceptance_rate: number;
  pending_invitations: number;
}

export interface OrganizationStats {
  total_organizations: number;
  total_members: number;
  total_teams: number;
  total_credits_utilized: number;
  total_credits_remaining: number;
  average_team_size: number;
}

// Form Types
export interface InviteOrganizationForm {
  email: string;
  organization_type: 'prepay_org' | 'grant_org' | 'postpay_org';
  monthly_credit_limit?: number;
}

export interface CreateOrganizationForm {
  name: string;
  country: string;
  city: string;
  contact_email: string;
  phone_number: string;
  description?: string;
  website?: string;
  industry?: string;
  size?: string;
  settings?: Record<string, any>;
  invite_token?: string;
}

// Member Invitation Types
export interface InviteMember {
  email: string;
  credits: number;
  is_admin?: boolean;
  cohort_id?: string;
  can_skip_modules?: boolean;
}

export interface InviteMembersForm {
  individual_members: InviteMember[];
  team_leaders: InviteMember[];
}

export interface InviteTeamMembersForm {
  emails: string[];
  credits_per_member?: number;
}

// New Organization Types for invite functionality
export interface OrganizationInviteRequest {
  email: string;
  organization_type: 'prepay_org' | 'grant_org' | 'postpay_org';
  monthly_credit_limit?: number;
}

export interface OrganizationInviteResponse {
  id: string;
  email: string;
  organization_type: 'prepay_org' | 'grant_org' | 'postpay_org';
  monthly_credit_limit?: number;
  status: 'pending' | 'accepted' | 'expired';
  created_at: string;
  expires_at: string;
  invite_url: string;
}

export interface OrganizationInviteToken {
  token: string;
}

// Credit allocation validation
export interface CreditAllocationValidation {
  number_of_invitees: number;
  assigned_credits: number;
  organization_monthly_limit: number;
  current_usage: number;
  is_valid: boolean;
  error_message?: string;
}

// Credit Management Types

export interface CreditAllocation {
  user_id: string;
  credit_amount: number;
  reason?: string;
  validity_period?: string;
}

export interface CreditAllocationRequest {
  user_id: string;
  credit_amount: number;
  reason?: string;
  validity_period?: string;
}

export interface CreditAllocationResponse {
  success: boolean;
  message: string;
  lot_id: string;
  user_id: string;
  credits_allocated: number;
  allocated_at: string;
}

export interface CreditLot {
  lot_id: string;
  user_id: string;
  user_name?: string;
  user_email?: string;
  organization_id: string;
  team_id?: string;
  team_name?: string;
  credits_allocated: number;
  credits_used: number;
  credits_remaining: number;
  status: 'active' | 'frozen' | 'suspended' | 'expired';
  reason?: string;
  validity_period?: string;
  allocated_at: string;
  expires_at?: string;
  frozen_at?: string;
  suspended_at?: string;
}

export interface CreditLotActionResponse {
  success: boolean;
  message: string;
  lot_id: string;
  status: 'active' | 'frozen' | 'suspended';
  action_timestamp: string;
}

// Member Projects Types

export interface ProjectSummary {
  id: string;
  name: string;
  description: string;
  current_step: string;
  created_at: string;
  updated_at: string;
}

export interface MemberWithProjects {
  user_id: string;
  user_email: string;
  user_name: string;
  member_type: 'individual' | 'team';
  tenant_id: string;
  project_count: number;
  pv_report_count: number;
  projects: ProjectSummary[];
  // Team-specific fields
  team_name?: string;
  team_contact_email?: string;
  team_admin_emails?: string[];
}

export interface MemberProjectsResponse {
  members: MemberWithProjects[];
  total_count: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface TenantInfo {
  // Backend may return 'id' or 'tenant_id'
  id?: string;
  tenant_id?: string;
  tenant_type: 'individual' | 'team';
  name: string;
  contact_email?: string;
}

export interface TenantProjectsResponse {
  tenant: TenantInfo;
  projects: ProjectSummary[];
  total_count: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface OwnerInfo {
  user_id: string;
  user_email: string;
  user_name: string;
  member_type: 'individual' | 'team';
  tenant_id: string;
  team_name?: string;
}

export interface PVReport {
  id: string;
  title: string;
  content: Record<string, any> | null;
}

export interface AccessLog {
  accessed_by: string;
  accessed_at: string;
}

export interface Evidence {
  quote: string;
  source: string;
}

export interface CustomerProfileItem {
  id: string;
  type: 'gain' | 'pain' | 'jtbd';
  label: string;
  maps_to: any;
  evidence: Evidence[];
  confidence: number;
  persona_id: string;
  description: string;
}

export interface CustomerProfile {
  gains: CustomerProfileItem[];
  pains: CustomerProfileItem[];
  jobs_to_be_done: CustomerProfileItem[];
}

export interface VPCPersona {
  status: string;
  value_map: any;
  created_at: string;
  persona_id: string;
  canvas_data: any;
  persona_name: string;
  customer_profile: CustomerProfile | null;
}

export interface VPCData {
  vpcs: {
    [key: string]: VPCPersona;
  } | null;
  vpc_status: string;
  primary_persona_id: string;
  // Customer profile selections stored at root level
  customer_profile?: CustomerProfile;
}

export interface HypothesisText {
  we_believe_that: string;
  are_struggling_with: string;
  thus: string;
  that_guarantees: string;
}

export interface Hypothesis {
  id: string;
  text: HypothesisText | string;
  evidence: string[];
  persona_id: string;
  generated_at: string;
  persona_name: string;
}

// Helper functions for hypothesis text handling
export function isStructuredHypothesisText(text: HypothesisText | string): text is HypothesisText {
  return typeof text === 'object' && 
         text !== null && 
         'we_believe_that' in text;
}

export function formatHypothesisText(text: HypothesisText | string): string {
  if (isStructuredHypothesisText(text)) {
    return `We believe that ${text.we_believe_that} are struggling with ${text.are_struggling_with}, thus ${text.thus}, that guarantees ${text.that_guarantees}`;
  }
  return text;
}

export interface Assumption {
  id: string;
  text: string;
  evidence: string[];
  generated_at: string;
  persona_name: string;
  hypothesis_id: string;
}

export interface Questionnaire {
  id: string;
  text: string;
  type: 'behavioral' | 'attitudinal' | 'contextual';
  generated_at: string;
  persona_name: string;
  assumption_id: string;
  hypothesis_id: string;
}

export interface FieldPrepData {
  stage: string;
  hypotheses: Hypothesis[];
  assumptions: Assumption[];
  questionnaires: Questionnaire[];
  hypotheses_generated_at?: string;
  assumptions_generated_at?: string;
  questionnaires_generated_at?: string;
}

// Market Research Analysis Types
export interface AnalysisEvidence {
  text: string;
  citations: string[];
  confidence: number | null;
}

export interface DimensionAnalysis {
  title: string;
  accuracy_level: string;
  dimension_type: string;
  primary_insight: string;
  confidence_score: number;
  counter_evidence: AnalysisEvidence[];
  data_limitations: string | null;
  statistical_summary: any | null;
  supporting_evidence: AnalysisEvidence[];
  quantitative_findings: any | null;
}

export interface AssumptionAnalysis {
  analyses: DimensionAnalysis[];
  key_findings: string[];
  persona_name: string;
  assumption_id: string;
  recommendation: string;
  assumption_text: string;
  confidence_label: string;
  validation_status: string;
  overall_confidence: number;
}

export interface ExecutiveSummary {
  content: string;
  statistics: {
    validated: number;
    invalidated: number;
    total_assumptions: number;
    average_confidence: number;
    partially_validated: number;
  };
  key_insights: string[];
}

export interface StructuredReport {
  metadata: {
    user_id: string | null;
    tenant_id: string;
    project_id: string;
    report_type: string;
    generated_at: string;
    project_name: string;
    report_version: string;
  };
  assumptions: AssumptionAnalysis[];
  executive_summary: ExecutiveSummary;
  research_data_summary?: {
    csv_files: any[];
    data_type: string;
    pdf_files: any[];
    total_data_fields: number;
    total_respondents: number;
    total_files_processed: number;
  };
}

export interface PersonaAnalysisData {
  structured_report: StructuredReport;
  persona_name?: string;
  stage?: string;
  assumption_analyses?: any[];
  final_report?: string;
  session_id?: string;
}

export interface AnalysisData {
  personas?: {
    [key: string]: PersonaAnalysisData;
  };
  stage?: string;
  structured_report?: StructuredReport;
  assumption_analyses?: any[];
  session_id?: string;
}

// Customer Profile v2 Types
export interface EnhancementRationale {
  original?: string;
  evidence?: string;
  reason?: string;
}

export interface CustomerProfileV2Item {
  id: string;
  label: string;
  description: string;
  text?: string;
  type?: 'gain' | 'pain' | 'jtbd';
  persona_id: string;
  persona_name?: string;
  evidence?: Array<{ quote: string; source: string }>;
  enhancement_rationale?: EnhancementRationale;
  confidence?: number;
  maps_to?: any;
}

export interface CustomerProfileV2 {
  jobs_to_be_done: CustomerProfileV2Item[];
  pains: CustomerProfileV2Item[];
  gains: CustomerProfileV2Item[];
}

// Value Map V2 Item Types
export interface ValueMapItem {
  id: string;
  label: string;
  text: string;
  impact?: string;
  value?: string;
  evidence?: string;
  priority?: 'critical' | 'high' | 'medium' | 'low';
  addresses_jtbd?: string[];
  addresses_pain?: string[];
  creates_gain?: string[];
}

export interface ValueMapSelections {
  persona_name?: string;
  products_services: ValueMapItem[];
  pain_relievers: ValueMapItem[];
  gain_creators: ValueMapItem[];
}

export interface VPCV2PersonaData {
  customer_profile: CustomerProfileV2;
  value_map_candidates?: any;
  value_map_selections?: ValueMapSelections | null;
  status?: string;
  persona_id?: string;
  persona_name?: string;
  version?: string;
  validation_metadata?: {
    validation_status?: string;
    confidence?: number;
    change_summary?: any;
    generated_at?: string;
  };
  selections_made_at?: string;
}

export interface VPCV2Data {
  [personaId: string]: VPCV2PersonaData;
}

// VPS (Value Proposition Statement) Types
export interface VPSPrimaryStatement {
  our: string;  // Products and Services
  help: string;  // Customer Segment
  who_want_to: string;  // Jobs to be done
  by: string;  // Customer pain
  and: string;  // Customer gain
  unlike: string;  // Competing value proposition
}

export interface VPSKeyDifferentiator {
  title: string;
  description: string;
  evidence?: string;
}

export interface VPSItem {
  persona_id?: string;
  persona_name?: string;
  primary_statement: VPSPrimaryStatement | string;
  key_differentiators?: VPSKeyDifferentiator[];
  more_context?: string;
  generation_metadata?: {
    confidence_score?: number;
    generated_at?: string;
    generated_by?: string;
    context_mode?: string;
  };
  refinement_metadata?: {
    refinement_decision?: string;
    rationale?: string;
    changes_summary?: string;
  };
}

// BMC (Business Model Canvas) Types
export interface BMCBlockItem {
  title: string;
  description: string;
  evidence?: string;
  priority?: 'high' | 'medium' | 'low';
}

export interface BMCBlock {
  items?: BMCBlockItem[];
  summary?: string;
  changed?: boolean;
  change_reason?: string;
  vps_v2_aligned?: boolean;
}

export interface BMCData {
  customer_segments?: BMCBlock;
  value_propositions?: BMCBlock;
  channels?: BMCBlock;
  customer_relationships?: BMCBlock;
  revenue_streams?: BMCBlock;
  key_resources?: BMCBlock;
  key_activities?: BMCBlock;
  key_partnerships?: BMCBlock;
  cost_structure?: BMCBlock;
  generation_metadata?: {
    generated_at?: string;
    version?: string;
    model_used?: string;
    blocks_generated?: number;
  };
  refinement_metadata?: {
    refinement_decision?: string;
    blocks_changed?: number;
    critique_sources_used?: string[];
  };
}

// Solution Critique Types
export interface CritiqueSource {
  id: number;
  type: 'web' | 'bmc' | 'vpc' | 'vps';
  title?: string;
  url?: string;
  field?: string;
  snippet?: string;
}

export interface CritiqueItem {
  critique_id: string;
  dimension: string;
  section_name: string;
  problem: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  recommendation: string;
  sources?: CritiqueSource[];
  citation_count?: number;
  unique_sources_used?: number;
}

export interface PrioritizedActions {
  immediate?: string[];
  short_term?: string[];
  long_term?: string[];
}

export interface CritiqueReport {
  project_id?: string;
  session_id?: string;
  generated_at?: string;
  executive_summary?: {
    overall_viability?: string;
    key_strengths?: string[];
    critical_concerns?: string[];
    recommendation?: string;
  };
  critiques_by_dimension?: {
    [dimension: string]: CritiqueItem[];
  };
  all_critiques?: CritiqueItem[];
  sources?: CritiqueSource[];
  prioritized_actions?: PrioritizedActions;
  metadata?: {
    total_critiques?: number;
    severity_distribution?: {
      critical?: number;
      high?: number;
      medium?: number;
      low?: number;
    };
    dimensions_analyzed?: number;
    total_sources?: number;
    total_citations?: number;
    ai_model?: string;
    geography?: string;
    industry?: string;
  };
}

export interface SolutionCritiqueData {
  session_id?: string;
  status?: 'processing' | 'completed' | 'failed';
  generated_at?: string;
  completed_at?: string;
  critique_report?: CritiqueReport;
  error?: string;
}

export interface MVPData {
  vps_v1?: VPSItem[];
  vps_v2?: VPSItem[];
  bmc?: BMCData;
  bmc_v2?: BMCData;
  solution_critique?: any;
  current_version?: {
    vps?: string;
    vps_updated_at?: string;
    vps_count?: number;
    bmc?: string;
    bmc_updated_at?: string;
  };
}

// Persona from the personas column (separate from VPC)
export interface ProjectPersona {
  id: string;
  name: string;
  description: string;
  problem_relationship?: string;
  evidence?: Array<{ quote: string; source: string }>;
  is_primary_payer?: boolean;
}

export interface MemberProject {
  id: string;
  tenant_id: string;
  user_id: string;
  name: string;
  description: string;
  pv_report_id: string;
  status: string;
  current_step: string;
  vpc_data: VPCData | null;
  field_prep_data: FieldPrepData | null;
  personas: ProjectPersona[] | null;  // Separate personas column
  analysis_data: AnalysisData | null;  // Market research analysis data
  analysis_status?: string;  // Analysis status (processing, completed, etc.)
  vpc_v2_data: VPCV2Data | null;  // Customer Profile v2 data
  mvp_data: MVPData | null;  // MVP data including VPS v1/v2, BMC, etc.
  soln_critique_data: SolutionCritiqueData | null;  // Solution Critique data
  prd_data: PRDData | null;  // Product Requirement Document data
  settings: any;
  created_at: string;
  updated_at: string;
  documents?: {
    title: string;
  };
}

// PRD (Product Requirement Document) Types
export interface PRDData {
  prd_json: PRDJson | null;
  prd_metadata?: PRDMetadata;
  validation_status?: string;
  version?: number;
}

export interface PRDMetadata {
  template_code: string;
  template_name: string;
  template_version: string;
  schema_version: string;
  generated_at: string;
  research_used: boolean;
  research_sources_count: number | null;
}

export interface PRDJson {
  purpose?: {
    statement?: string;
    purpose_statement?: string;
    target_persona?: string;
    validated_problem?: string;
  };
  primary_persona?: {
    name?: string;
    persona_name?: string;
    description?: string;
    segment?: string;
    primary_job?: {
      job_type?: string;
      job_statement?: string;
    };
    primary_jtbd?: string;
    key_pains?: string[];
    desired_gains?: string[];
  };
  scope?: {
    in_scope?: {
      geography?: string;
      additional?: string[];
      core_flows?: string[];
      user_segments?: string[];
    };
    out_of_scope?: string[];
  };
  objective?: {
    primary_objective?: string;
    key_results?: Array<{ result: string; target: string }>;
    learning_goals?: string[];
    success_criteria?: string[];
  };
  mvp_features?: {
    must_haves?: Array<{
      feature_name: string;
      job_type?: string;
      description?: string;
      job_supported?: string;
      vpc_reference?: string;
      bmc_reference?: string;
    }>;
    nice_to_haves?: Array<{
      feature_name: string;
      description?: string;
      job_supported?: string;
      rationale_for_deferral?: string;
    }>;
  };
  critical_workflows?: Array<{
    workflow_name: string;
    description?: string;
    is_must_have?: boolean;
    value_delivered?: string;
    steps?: string[];
  }>;
  success_signals?: {
    qualitative?: Array<{
      signal_name: string;
      description?: string;
      collection_method?: string;
    }>;
    quantitative?: Array<{
      metric_name: string;
      description?: string;
      measurement_method?: string;
      target?: string;
    }>;
  };
}

export interface MemberProjectDetailResponse {
  project: MemberProject;
  owner: OwnerInfo;
  pv_report: PVReport | null;
  access_log: AccessLog;
}

// Cohort Projects Types (for GET /api/cohorts/{tenant_id}/{cohort_id}/projects)
export interface CohortProject {
  id: string;
  name: string;
  description: string | null;
  current_step: string;
  status: string;
  created_at: string;
  updated_at: string;
  tenant_id: string;
  tenant_name: string;
  tenant_type: 'individual' | 'team';
  owner_email: string | null;
  owner_name: string | null;
}

export interface CohortProjectsResponse {
  projects: CohortProject[];
  total_count: number;
  page: number;
  page_size: number;
  has_next: boolean;
  cohort_id: string;
  cohort_name: string;
}