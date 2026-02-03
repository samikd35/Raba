// Types for Dashboard Projects component

export interface DashboardProject {
  id: string;
  name: string;
  description?: string;
  problem_statement?: string;
  status: string;
  current_step?: string;
  created_at: string;
  updated_at: string;
  progress_percentage?: number;
  artifact_count?: number;
  pv_report_title?: string;
  personas_count?: number;
}

export interface LatestProjectsResponse {
  success: boolean;
  data: {
    projects: DashboardProject[];
  };
  message: string;
}

