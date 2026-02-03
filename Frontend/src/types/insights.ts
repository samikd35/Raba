// Types for Actionable Insights functionality based on actual API response

export interface InsightStatus {
  status: "processing" | "completed" | "failed";
  insights_count: number;
  progress: number | null;
  estimated_time_remaining: number | null;
  error_message: string | null;
}

export interface InsightContent {
  important_questions_industry_geography: {
    desirability_analysis: string[];
    recommended_research_areas: string[];
    key_stakeholders_institutions: string[];
  };
  emerging_key_insights: {
    customer_segments: string;
    existing_solutions: string;
    distribution_channels: string;
    regulations_policies: string;
    government_policies: string;
    barriers_consumption: string;
  };
  leverage_points: string[];
  key_questions_for_founders: string[];
}

export interface GenerationMetadata {
  model_used: string;
  json_direct: boolean;
  generated_at: string;
  sources_count: number;
  prompt_template: string;
  structured_format: boolean;
}

export interface InsightData {
  id: string;
  insight_type: string;
  title: string;
  content: InsightContent;
  supporting_chunks: string[];
  confidence_score: number;
  generation_metadata: GenerationMetadata;
  created_at: string;
}

export interface InsightsApiResponse {
  success: boolean;
  insights: InsightData[];
  report_id: string;
  total_insights: number;
  generation_time: null;
  metadata: {
    generated_at: string;
  };
}

export interface InsightError {
  code: string;
  message: string;
  details?: any;
}
