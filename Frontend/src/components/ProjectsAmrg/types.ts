export interface Project {
    id: string;
    tenant_id: string;
    user_id: string;
    name: string;
    problem_statement: string;
    status: string;
    created_at: string;
    updated_at: string;
    amrg_completed: boolean;
    amrg_completed_at: string | null;
    context_mode: string;
    // Optional fields that might be useful if the API adds them later or for compatibility/extension
    personas_count?: number;
    personas?: Array<{
        id: string;
        name: string;
    }>;
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

export type SortField = 'name' | 'created_at' | 'updated_at';
export type SortOrder = 'asc' | 'desc';
export type StatusFilter = 'all' | 'active' | 'completed' | 'archived';
