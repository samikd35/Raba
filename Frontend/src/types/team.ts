// Team Types

export interface Team {
  id: string;
  name: string;
  organization_id: string;
  organization_name: string;
  team_leader_id: string;
  team_leader_name: string;
  team_leader_email: string;
  member_count: number;
  // Optional descriptive fields
  description?: string | null;
  website?: string | null;
  industry?: string | null;
  size?: string | null;
  country?: string | null;
  credit_pool_total: number;
  credit_pool_used: number;
  credit_pool_remaining: number;
  pool_reset_date: string;
  status: 'active' | 'suspended' | 'frozen';
  created_at: string;
  // Optional: role of the CURRENT user within this team (as provided by backend team details endpoint)
  user_role?: 'member' | 'team_leader' | 'admin' | 'owner';
}

export interface TeamMember {
  id: string;
  user_id: string;
  name: string;
  email: string;
  role: 'member' | 'team_leader' | 'admin';
  team_id: string;
  team_name: string;
  credits_allocated: number;
  credits_used: number;
  status: 'active' | 'frozen' | 'suspended';
  joined_date: string;
}

export interface TeamInviteRequest {
  emails: string[];
  is_admin: boolean;
}

export interface TeamInviteResponse {
  success: boolean;
  message: string;
  invitations: string[];
}

export interface TeamJoinRequest {
  invite_token: string;
}

export interface TeamJoinResponse {
  team_id: string;
  organization_id: string;
  role: 'member' | 'admin';
  permissions: {
    can_manage_team: boolean;
    can_invite: boolean;
    can_edit: boolean;
    can_delete: boolean;
  };
  joined_at: string;
}

export interface TeamMetrics {
  invitations: {
    sent: number;
    accepted: number;
  };
  membership: {
    total: number;
  };
}

export interface TeamCreateRequest {
  name: string;
  description: string;
  website: string;
  industry: string;
  size: string;
  country: string;
  settings: { additionalProp1: Record<string, any> };
}

export interface TeamCreateResponse {
  id: string;
  organization_id?: string;
  name: string;
  created_at: string;
}

export interface TeamResponse {
  id: string;
  name: string;
  organization_id: string;
  organization_name?: string;
  team_leader_id?: string;
  team_leader_name?: string;
  team_leader_email?: string;
  member_count?: number;
  description?: string | null;
  website?: string | null;
  industry?: string | null;
  size?: string | null;
  country?: string | null;
  credit_pool_total?: number;
  credit_pool_used?: number;
  credit_pool_remaining?: number;
  pool_reset_date?: string;
  status?: 'active' | 'suspended' | 'frozen';
  created_at?: string;
}

// Credit Request Types

export interface CreditRequest {
  request_id: string;
  team_id: string;
  team_name?: string;
  organization_id: string;
  requester_id: string;
  requester_name: string;
  requester_email: string;
  requested_credits: number;
  reason?: string;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  reviewed_by?: string;
  reviewed_by_name?: string;
  reviewed_at?: string;
  review_notes?: string;
  credits_allocated?: number;
  created_at: string;
  updated_at: string;
}

export interface CreditRequestCreate {
  requested_credits: number;
  reason?: string;
}

export interface CreditRequestReview {
  action: 'approve' | 'reject';
  credits_allocated?: number;
  review_notes?: string;
}