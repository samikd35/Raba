// ============================================
// TypeScript Interfaces for Solution Critic Data
// ============================================

export interface Source {
  id: number;
  url?: string;
  type: "web" | "vpc" | "vps" | "bmc";
  title?: string;
  field?: string;
  content?: string;
  context?: string;
  priority?: number;
  issue?: string;
}

export interface Suggestion {
  type: "validation" | "optimization" | "alternative" | "compliance";
  action: string;
  effort: "low" | "medium" | "high";
  impact: "low" | "medium" | "high";
  priority: "immediate" | "short_term" | "long_term";
  rationale: string;
  supporting_sources: number[];
}

export interface Critique {
  title: string;
  impact: string;
  problem: string;
  sources: Source[];
  summary: string[];
  severity: "low" | "medium" | "high";
  dimension: string;
  confidence: number;
  critique_id: string;
  suggestions: Suggestion[];
  section_name: string;
  citation_count: number;
  unique_sources_used: number;
}

export interface DimensionAnalysis {
  summary: string;
  critiques: Critique[];
  citation_count: number;
  dimension_severity: "low" | "medium" | "high";
}

export interface ExecutiveSummary {
  top_3_risks: string[];
  key_insights: string[];
  recommendation: string;
  total_critiques: number;
  overall_viability: string;
  overall_confidence: number;
  severity_distribution: SeverityDistribution;
}

export interface SeverityDistribution {
  low: number;
  medium: number;
  high: number;
}

export interface Metadata {
  ai_model: string;
  industry: string;
  geography: string;
  total_sources: number;
  total_citations: number;
  total_critiques: number;
  dimensions_analyzed: number;
  severity_distribution: SeverityDistribution;
}

export interface CritiqueDimensions {
  market_viability?: DimensionAnalysis;
  technical_scalability?: DimensionAnalysis;
  dominant_business_logic?: DimensionAnalysis;
  operational_feasibility?: DimensionAnalysis;
  competitive_differentiation?: DimensionAnalysis;
  [key: string]: DimensionAnalysis | undefined;
}

export interface SolutionCritiqueData {
  sources: Source[];
  metadata: Metadata;
  project_id: string;
  session_id: string;
  generated_at: string;
  all_critiques: Critique[];
  critiques_by_dimension: CritiqueDimensions;
  executive_summary?: ExecutiveSummary;
}

export interface SolutionCriticResponse {
  success: boolean;
  data: SolutionCritiqueData;
  metadata: {
    generated_at: string;
    total_sources: number;
    total_citations: number;
    ai_model: string;
    processing_time_seconds: number | null;
  };
}

export interface SolutionCriticProps {
  projectId: string;
}
