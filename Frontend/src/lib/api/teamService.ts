import {
  Team,
  TeamMember,
  TeamCreateRequest,
  TeamCreateResponse,
  TeamInviteRequest,
  TeamInviteResponse,
  TeamJoinRequest,
  TeamJoinResponse,
  TeamMetrics,
  TeamResponse
} from '../../types/team';
import { useAuthStore } from '../../stores/authStore';


const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

/**
 * Get authentication headers for API requests with optional tenant context
 */
const getAuthHeaders = (organizationId?: string): HeadersInit => {
  const token = useAuthStore.getState().token;

  if (!token) {
    throw new Error('No authentication token available');
  }

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  // Add tenant/organization context if provided
  if (organizationId) {
    headers['X-Organization-ID'] = organizationId;
    headers['X-Tenant-ID'] = organizationId;
  }

  return headers;
};

/**
 * Handle API errors with proper error messages and tenant mismatch detection
 */
const handleApiError = async (response: Response): Promise<void> => {
  if (!response.ok) {
    let errorMessage: any = `API Error: ${response.status} ${response.statusText}`;

    try {
      const errorData = await response.json();

      if (errorData.message) {
        errorMessage = errorData.message;
      } else if (errorData.detail) {
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          // Handle FastAPI validation error format: detail: [{msg: "...", ...}, ...]
          errorMessage = errorData.detail
            .map((d: any) => d.msg || (typeof d === 'string' ? d : JSON.stringify(d)))
            .join('; ');
        } else {
          errorMessage = JSON.stringify(errorData.detail);
        }
      }

      // Handle specific tenant mismatch errors - check various formats
      const finalErrorMessageString = typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage);
      const lowerMessage = finalErrorMessageString.toLowerCase();

      if (lowerMessage.includes('tenant mismatch') ||
        (lowerMessage.includes('tenant') && lowerMessage.includes('mismatch')) ||
        lowerMessage.includes('wrong tenant') ||
        lowerMessage.includes('invalid tenant') ||
        lowerMessage.includes('access denied') ||
        lowerMessage.includes('unauthorized access to team') ||
        lowerMessage.includes('team not found in organization')) {

        // Provide more specific error message for tenant mismatch
        if (lowerMessage.includes('tenant mismatch')) {
          throw new Error('You do not have access to this team. Please ensure you are in the correct organization workspace.');
        } else {
          throw new Error('Access denied: You may not have permission to access this team or it may belong to a different organization.');
        }
      }

    } catch (parseError) {
      // If JSON parsing fails, check response status text for tenant mismatch
      const lowerStatusText = response.statusText?.toLowerCase() || '';
      if (lowerStatusText.includes('tenant mismatch') ||
        lowerStatusText.includes('wrong tenant') ||
        lowerStatusText.includes('invalid tenant')) {
        throw new Error('You do not have access to this team. Please ensure you are in the correct organization workspace.');
      }

      // If it's not a parsing error we threw, re-throw it
      if (parseError instanceof Error && parseError.message.includes('You do not have access')) {
        throw parseError;
      }
    }

    const finalMessage = typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage);
    throw new Error(finalMessage);
  }
};

/**
 * Team API Service
 * Handles all team-related API operations
 */
export class TeamService {
  /**
   * Get team details by ID from the new backend endpoint
   * GET /api/teams/{teamId}/details
   */
  static async getTeamDetails(teamId: string): Promise<Team> {
    try {
      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 TeamService: Fetching team details', { teamId });
      }

      const response = await fetch(`${API_BASE_URL}/api/teams/${teamId}/details`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      const teamData = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ TeamService: Team details received', {
          teamId: teamData.id,
          name: teamData.name,
          userRole: teamData.user_role,
        });
      }

      // Transform backend response to Team interface
      const transformedTeam: Team = {
        id: teamData.id,
        name: teamData.name,
        description: teamData.description,
        organization_id: teamData.organization_id,
        organization_name: teamData.organization_name,
        team_leader_id: teamData.team_leader_id,
        team_leader_name: teamData.team_leader_name,
        team_leader_email: teamData.team_leader_email,
        member_count: teamData.member_count,
        credit_pool_total: teamData.credit_pool_total,
        credit_pool_used: teamData.credit_pool_used,
        credit_pool_remaining: teamData.credit_pool_remaining,
        pool_reset_date: teamData.pool_reset_date || '',
        status: teamData.status || 'active',
        created_at: teamData.created_at,
        user_role: teamData.user_role,
      };

      return transformedTeam;
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ TeamService: Error fetching team details', error);
      }
      throw error;
    }
  }

  /**
   * Fetch all teams for an organization
   * GET /api/teams/{organization_id}
   */
  static async fetchTeams(organizationId: string): Promise<TeamResponse[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/teams/${organizationId}`, {
        method: 'GET',
        headers: getAuthHeaders(organizationId),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error fetching teams:', error);
      throw error;
    }
  }

  /**
   * Create a team under an organization
   * POST /api/teams/{organization_id}/create
   */
  static async createTeam(organizationId: string, data: TeamCreateRequest): Promise<TeamCreateResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/teams/${organizationId}/create`, {
        method: 'POST',
        headers: getAuthHeaders(organizationId),
        body: JSON.stringify(data),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error creating team:', error);
      throw error;
    }
  }

  /**
   * Invite users to a team
   * POST /api/teams/{team_id}/invite
   */
  static async inviteTeamMembers(teamId: string, data: TeamInviteRequest): Promise<TeamInviteResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/teams/${teamId}/invite`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      await handleApiError(response);
      const result = await response.json();

      // Transform response to match expected format
      return {
        success: true,
        message: result.message || `Successfully invited ${data.emails.length} users`,
        invitations: result.invitations || result.invitation_ids || [],
      };
    } catch (error) {
      console.error('Error inviting team members:', error);
      throw error;
    }
  }

  /**
   * Join a team using invite token
   * POST /api/teams/{team_id}/join
   */
  static async joinTeam(teamId: string, inviteToken: string): Promise<TeamJoinResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/teams/${teamId}/join`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ invite_token: inviteToken }),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error joining team:', error);
      throw error;
    }
  }

  /**
   * Get team metrics
   * GET /api/teams/{team_id}/metrics
   */
  static async getTeamMetrics(teamId: string, organizationId?: string): Promise<TeamMetrics> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/teams/${teamId}/metrics`, {
        method: 'GET',
        headers: getAuthHeaders(organizationId),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error fetching team metrics:', error);
      throw error;
    }
  }

  /**
   * Get team members
   * GET /api/teams/{team_id}/members
   */
  static async getTeamMembers(teamId: string): Promise<TeamMember[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/teams/${teamId}/members`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      await handleApiError(response);
      const data = await response.json();
      // Return the members array, or empty array if not found
      return data.members || data || [];
    } catch (error) {
      console.error('Error fetching team members:', error);
      // Return empty array on error to prevent breaking the UI
      return [];
    }
  }

  /**
   * Delete a team
   * DELETE /api/teams/{team_id}
   */
  static async deleteTeam(teamId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/teams/${teamId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error deleting team:', error);
      throw error;
    }
  }

  /**
   * Remove a member from a team
   * DELETE /api/teams/{team_id}/members/{member_user_id}
   */
  static async removeMember(teamId: string, memberUserId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/teams/${teamId}/members/${memberUserId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error removing team member:', error);
      throw error;
    }
  }

  /**
   * Validate team invitation token server-side and get team info
   * @param token - The invitation token
   * @param teamId - Team ID for validation
   * @returns Team information from server validation
   */
  static async getTeamInfoFromToken(token: string, teamId?: string): Promise<{
    teamId: string;
    teamName?: string;
    organizationId?: string;
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/invitations/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token,
          team_id: teamId,
        }),
      });

      if (!response.ok) {
        throw new Error('Invalid or expired invitation token');
      }

      const payload = await response.json();

      return {
        teamId: payload.tenant_id || teamId || '',
        teamName: payload.team_name,
        organizationId: payload.organization_id || payload.org_id,
      };
    } catch (error) {
      console.error('Error validating token:', error);
      throw new Error('Invalid invitation token');
    }
  }

  /**
   * Validate organization invitation token server-side
   * @param token - The invitation token
   * @param orgId - Organization ID for validation
   * @param teamId - Team ID for validation (optional)
   * @returns Invitation information from server validation
   */
  static async validateInvitationToken(
    token: string,
    orgId?: string,
    teamId?: string
  ): Promise<{
    tenant_id: string;
    is_admin: boolean;
    credits: number;
    is_team_leader: boolean;
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/invitations/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token,
          org_id: orgId,
          team_id: teamId,
        }),
      });

      if (!response.ok) {
        throw new Error('Invalid or expired invitation token');
      }

      const payload = await response.json();

      return {
        tenant_id: payload.tenant_id || '',
        is_admin: payload.is_admin || false,
        credits: payload.credits || 0,
        is_team_leader: payload.is_team_leader || false,
      };
    } catch (error) {
      console.error('Error validating token:', error);
      throw new Error('Invalid invitation token');
    }
  }

  /**
   * Legacy method for backward compatibility
   * Get team details by ID
   * @deprecated Use getTeamDetails instead
   */
  static async getTeamById(teamId: string, organizationId?: string): Promise<Team | null> {
    try {
      return await this.getTeamDetails(teamId);
    } catch (error) {
      console.error('Error fetching team by ID:', error);
      return null;
    }
  }
}

// Export singleton instance
export const teamService = TeamService;
