// Types for All Projects component

export interface AllProject {
    id: string;
    name: string;
    description: string;
    problem_statement: string;
    status: string;
    current_step: string;
    created_at: string;
    updated_at: string;
    progress_percentage: number;
    artifact_count: number;
    pv_report_title?: string;
    personas_count?: number;
  }
  
  export interface AllProjectsResponse {
    success: boolean;
    data: {
      projects: AllProject[];
      total_count: number;
      page: number;
      page_size: number;
      has_next: boolean;
    };
    message: string;
  }
  
  export type SortField = 'name' | 'created_at' | 'updated_at' | 'status';
  export type SortOrder = 'asc' | 'desc';
  export type StatusFilter = 'all' | 'active' | 'completed' | 'paused' | 'archived';
  