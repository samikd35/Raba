// Types for ProjectsMvp component and sub-components

export interface Persona {
  id: string;
  name: string;
  description: string;
  is_primary_payer: boolean;
  problem_relationship: string;
  evidence: Array<{
    quote: string;
    source: string;
    relevance_score: number;
  }>;
}

export interface Hypothesis {
  id: string;
  text: string;
  evidence: string[];
  persona_id: string;
  persona_name: string;
  generated_at: string;
}

export interface Assumption {
  id: string;
  text: string;
  evidence: string[];
  persona_id: string;
  persona_name: string;
  hypothesis_id: string;
  component_type: string;
  generated_at: string;
  quality_validation: {
    is_valid: boolean;
    warnings: string[];
    has_current_state_language: boolean;
  };
}

export interface Questionnaire {
  id: string;
  text: string;
  type: string;
  persona_name: string;
  assumption_id: string;
  hypothesis_id: string;
  component_type: string;
  generated_at: string;
}

export interface Project {
  id: string;
  tenant_id: string;
  user_id: string;
  name: string;
  problem_statement: string;
  status: string;
  created_at: string;
  updated_at: string;
  personas_count: number;
  customer_profile_completed: boolean;
  value_map_completed: boolean;
  value_map_completed_at: string | null;
  personas: Array<{
    id: string;
    name: string;
    value_map_completed: boolean;
  }>;
  module_3_ready: boolean;
  vps_v1_generated: boolean;
  context_mode: string;
  context_status: string;
}

export interface ProjectsResponse {
  success: boolean;
  data: {
    projects: Project[];
    total_count: number;
    page: number;
    page_size: number;
    has_next: boolean;
    filter_applied: string;
  };
  message: string;
}

export type SortField = 'name' | 'created_at' | 'updated_at' | 'personas_count';
export type SortOrder = 'asc' | 'desc';
export type StatusFilter = 'all' | 'active' | 'completed' | 'archived';
