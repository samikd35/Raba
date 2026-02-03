// TypeScript interfaces for Business Model Canvas

export interface BMCChannel {
  id: string;
  name: string;
  type: string;
  phases: string[];
  description: string;
  segment_ids: string[];
  cost_structure: string;
  evidence_source: string;
  reach_potential: string;
}

export interface BMCResource {
  id: string;
  name: string;
  type: string;
  criticality: string;
  description: string;
  required_for: string[];
  evidence_source: string;
  acquisition_strategy: string;
}

export interface BMCActivity {
  id: string;
  name: string;
  type: string;
  criticality: string;
  description: string;
  required_for: string[];
  evidence_source: string;
  resources_needed: string[];
}

export interface BMCPartnership {
  id: string;
  name: string;
  motivation: string;
  partner_type: string;
  evidence_source: string;
  resources_provided: string[];
  value_contribution: string;
  partner_description: string;
  activities_supported: string[];
}

export interface BMCValueProposition {
  id: string;
  name: string;
  vpc_fit: {
    gains_created: string[];
    jobs_addressed: string[];
    pains_relieved: string[];
  };
  segment_ids: string[];
  key_benefits: string[];
  differentiation: string;
  evidence_source: string;
  value_statement: string;
}

export interface BMCCustomerRelationship {
  id: string;
  name: string;
  type: string;
  description: string;
  segment_ids: string[];
  evidence_source: string;
  growth_strategy: string;
  retention_strategy: string;
  acquisition_strategy: string;
}

export interface BMCCustomerSegment {
  id: string;
  name: string;
  priority: string;
  description: string;
  size_estimate: string;
  characteristics: string[];
  evidence_source: string;
  persona_mapping: string[];
}

export interface BMCRevenueStream {
  id: string;
  name: string;
  type: string;
  segment_ids: string[];
  evidence_source: string;
  pricing_strategy: string;
  pricing_mechanism: string;
  revenue_potential: string;
}

export interface BMCCostCategory {
  id: string;
  name: string;
  type: string;
  description: string;
  cost_estimate: string;
  evidence_source: string;
  related_resources: string[];
  related_activities: string[];
  related_partnerships: string[];
  optimization_potential: string;
}

export interface BMCCostStructure {
  model_type: string;
  cost_categories: BMCCostCategory[];
  economies_of_scale: string;
  economies_of_scope: string;
}

export interface GenerationMetadata {
  model_used: string;
  generated_at: string;
  generation_time: number;
}

export interface BMCData {
  channels?: {
    channels?: BMCChannel[];
    items?: BMCChannel[];  // Alternative field name from API
    generation_metadata?: GenerationMetadata;
  };
  key_resources?: {
    resources?: BMCResource[];
    items?: BMCResource[];  // Alternative field name from API
    generation_metadata?: GenerationMetadata;
  };
  key_activities?: {
    activities?: BMCActivity[];
    items?: BMCActivity[];  // Alternative field name from API
    generation_metadata?: GenerationMetadata;
  };
  key_partnerships?: {
    partnerships?: BMCPartnership[];
    items?: BMCPartnership[];  // Alternative field name from API
    generation_metadata?: GenerationMetadata;
  };
  value_propositions?: {
    propositions?: BMCValueProposition[];
    items?: BMCValueProposition[];  // Alternative field name from API
    generation_metadata?: GenerationMetadata;
  };
  customer_relationships?: {
    relationships?: BMCCustomerRelationship[];
    items?: BMCCustomerRelationship[];  // Alternative field name from API
    generation_metadata?: GenerationMetadata;
  };
  customer_segments?: {
    segments?: BMCCustomerSegment[];
    items?: BMCCustomerSegment[];  // Alternative field name from API
    generation_metadata?: GenerationMetadata;
  };
  revenue_streams?: {
    revenue_streams?: BMCRevenueStream[];
    items?: BMCRevenueStream[];  // Alternative field name from API
    generation_metadata?: GenerationMetadata;
  };
  cost_structure?: {
    cost_structure?: BMCCostStructure;
    items?: BMCCostStructure;  // Alternative field name from API
    generation_metadata?: GenerationMetadata;
  };
  generation_metadata?: {
    user_id: string;
    version: string;
    model_used: string;
    generated_at: string;
    blocks_generated: number;
    context_completeness: number;
    total_generation_time: number;
    block_generation_times: Record<string, number>;
  };
}

export interface BMCResponse {
  success: boolean;
  project_id: string;
  project_name: string;
  bmc: BMCData;
  message: string;
  updated_block?: string | null;
  regenerated_block?: string | null;
}
