export interface Cohort {
    id: string;
    tenant_id: string;
    name: string;
    description: string;
    color: string;
    is_active: boolean;
    settings: Record<string, any>;
    created_by: string;
    created_at: string;
    updated_at: string;
}

export interface CohortMember {
    id: string;
    cohort_id: string;
    member_tenant_id: string;
    tenant_type: 'individual' | 'team';
    tenant_name: string;
    user_id: string | null;
    user_email: string | null;
    user_full_name: string | null;
    user_name: string | null;
    user_role: string | null;
    created_at: string;
}
