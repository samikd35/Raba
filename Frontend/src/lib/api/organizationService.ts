import {
  Organization,
  OrganizationInviteRequest,
  OrganizationInviteResponse,
  MemberProjectsResponse,
  TenantProjectsResponse,
  MemberProjectDetailResponse
} from '../../types/organization';
import { authService } from '../../services/authService';
import { FormValidator } from '../../lib/validation';

/**
 * Organization Service - Real API Integration
 * 
 * This service handles all organization-related API calls including:
 * - Fetching organizations
 * - Inviting organizations (super admin)
 * - Creating organizations
 * - Managing organization metrics
 * - Inviting users to organizations
 * - Joining organizations
 * - Deleting organizations
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

/**
 * Get authentication headers for API requests
 */
const getAuthHeaders = (): HeadersInit => {
  const token = authService.getCurrentToken();
  if (!token) {
    throw new Error('No authentication token available');
  }
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
};

/**
 * Handle API errors with proper error messages
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
    } catch {
      // If JSON parsing fails, use default error message
    }

    // Ensure we throw a string message to avoid [object Object]
    const finalMessage = typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage);
    throw new Error(finalMessage);
  }
};

/**
 * Log errors only in development environment
 */
const logError = (context: string, error: unknown): void => {
  if (process.env.NODE_ENV === 'development') {
    console.error(`[OrganizationService] ${context}:`, error);
  }
};

// Resilient fetch with timeout + retries for transient errors
const RETRYABLE_STATUS = new Set([502, 503, 504, 524]); // include Cloudflare 524
const isRetryableMessage = (msg: string) => {
  const m = msg.toLowerCase();
  return (
    m.includes('connectionterminated') ||
    m.includes('network') ||
    m.includes('fetch') ||
    m.includes('err_http2') ||
    m.includes('stream')
  );
};

async function fetchJson<T = any>(
  url: string,
  options: RequestInit = {},
  opts: { retries?: number; timeoutMs?: number; retryDelayBaseMs?: number } = {}
): Promise<T> {
  const retries = opts.retries ?? 2;
  const timeoutMs = opts.timeoutMs ?? 15000;
  const retryDelayBaseMs = opts.retryDelayBaseMs ?? 500;

  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    let timeoutId: NodeJS.Timeout | null = null;
    let isTimeoutAbort = false;

    try {
      // Set up timeout that marks the abort as timeout-related
      timeoutId = setTimeout(() => {
        isTimeoutAbort = true;
        controller.abort();
      }, timeoutMs);

      const response = await fetch(url, {
        cache: 'no-store',
        ...options,
        headers: {
          ...getAuthHeaders(),
          ...(options.headers || {}),
        },
        signal: controller.signal,
      });

      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }

      if (!response.ok) {
        if (RETRYABLE_STATUS.has(response.status) && attempt < retries) {
          const delay = retryDelayBaseMs * Math.pow(2, attempt);
          await new Promise((r) => setTimeout(r, delay));
          continue;
        }
        await handleApiError(response); // throws
      }

      // Try JSON; if none, return null as any
      const text = await response.text();
      return (text ? JSON.parse(text) : (null as any)) as T;
    } catch (err: any) {
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }

      lastError = err;
      const message = typeof err?.message === 'string' ? err.message : '';

      // Handle AbortError more carefully
      if (err?.name === 'AbortError') {
        // If it's a timeout abort, we can retry
        if (isTimeoutAbort && attempt < retries) {
          if (process.env.NODE_ENV === 'development') {
            console.warn(`[OrganizationService] Request timeout, retrying attempt ${attempt + 1}/${retries + 1}`);
          }
          const delay = retryDelayBaseMs * Math.pow(2, attempt);
          await new Promise((r) => setTimeout(r, delay));
          continue;
        }
        // If it's not a timeout abort, don't retry - throw immediately
        break;
      }

      // Handle other retryable errors
      if (attempt < retries && isRetryableMessage(message)) {
        const delay = retryDelayBaseMs * Math.pow(2, attempt);
        await new Promise((r) => setTimeout(r, delay));
        continue;
      }

      break;
    }
  }
  throw lastError instanceof Error ? lastError : new Error('Request failed');
}

/**
 * Normalize and validate organization invite payload
 */
function normalizeInvitePayload(input: OrganizationInviteRequest): {
  email: string;
  credit: number;
  meta: {
    organization_type: 'prepay_org' | 'grant_org' | 'postpay_org';
    monthly_credit_limit?: number
  }
} {
  const email = (input.email || '').trim();
  if (!FormValidator.validateEmail(email)) {
    throw new Error('Invalid email format');
  }

  let credit: number;
  if (input.organization_type === 'grant_org') {
    if (typeof input.monthly_credit_limit !== 'number' || input.monthly_credit_limit <= 0) {
      throw new Error('Monthly credit limit is required for grant organizations');
    }
    credit = input.monthly_credit_limit;
  } else {
    // prepay_org and postpay_org don't need initial credits/mandatory limits here
    credit = 0;
  }

  return {
    email,
    credit,
    meta: {
      organization_type: input.organization_type,
      monthly_credit_limit: input.monthly_credit_limit,
    },
  };
}

/**
 * Organization API Service
 * Handles all organization-related API operations
 */
export class OrganizationService {
  /**
   * Fetch all organizations (Super Admin dashboard)
   * GET /api/organization/admin/list
   * 
   * Query Parameters:
   * - page: Page number (default: 1)
   * - page_size: Items per page (default: 20)
   * - search: Search term for organization name
   * - industry: Filter by industry
   * - country: Filter by country
   * - size: Filter by organization size
   * - is_active: Filter by active status
   */
  static async fetchOrganizations(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    industry?: string;
    country?: string;
    size?: string;
    is_active?: boolean;
  }): Promise<Organization[]> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
      if (params?.search) queryParams.append('search', params.search);
      if (params?.industry) queryParams.append('industry', params.industry);
      if (params?.country) queryParams.append('country', params.country);
      if (params?.size) queryParams.append('size', params.size);
      if (params?.is_active !== undefined) queryParams.append('is_active', params.is_active.toString());

      const url = `${API_BASE_URL}/api/organization/admin/list${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      const data = await response.json();

      // Handle response format from documentation
      if (data.success && data.data && Array.isArray(data.data)) {
        return data.data;
      }
      if (Array.isArray(data)) {
        return data;
      }

      return [];
    } catch (error) {
      logError('fetchOrganizations', error);
      throw error;
    }
  }

  /**
   * Get organization summary statistics (Super Admin)
   * GET /api/organization/admin/summary
   * 
   * Returns aggregated statistics about all organizations including:
   * - Total/active/inactive counts
   * - Member and team counts
   * - Credit allocation and usage
   * - Breakdowns by industry, size, and country
   */
  static async getOrganizationSummary(): Promise<{
    total_organizations: number;
    active_organizations: number;
    inactive_organizations: number;
    total_members: number;
    total_teams: number;
    total_credits_allocated: number;
    total_credits_used: number;
    organizations_by_industry: Record<string, number>;
    organizations_by_size: Record<string, number>;
    organizations_by_country: Record<string, number>;
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/organization/admin/summary`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      const result = await response.json();

      // Handle response format from documentation
      if (result.success && result.data) {
        return result.data;
      }

      throw new Error('Invalid response format from organization summary endpoint');
    } catch (error) {
      logError('getOrganizationSummary', error);
      throw error;
    }
  }

  /**
   * Invite organization (platform-level, super admin)
   * POST /api/organization/invite
   */
  static async inviteOrganization(data: OrganizationInviteRequest): Promise<OrganizationInviteResponse> {
    try {
      // Normalize & validate
      const wire = normalizeInvitePayload(data);

      const response = await fetch(`${API_BASE_URL}/api/organization/invite`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          email: wire.email,
          credit: wire.credit,
          organization_type: data.organization_type
        }),
      });
      await handleApiError(response);
      const result = await response.json();

      // Transform the response to match our expected format
      const inviteResponse: OrganizationInviteResponse = {
        id: result.id,
        email: result.email,
        organization_type: data.organization_type,
        monthly_credit_limit: data.organization_type === 'grant_org' ? data.monthly_credit_limit : undefined,
        status: result.status,
        created_at: result.created_at,
        expires_at: result.expires_at || new Date(new Date(result.created_at).getTime() + 48 * 60 * 60 * 1000).toISOString(),
        invite_url: result.invite_url || `${process.env.NEXT_PUBLIC_FRONTEND_URL || window.location.origin}/admin/onboarding?token=${result.id}&type=${data.organization_type}`,
      };

      return inviteResponse;
    } catch (error) {
      logError('inviteOrganization', error);
      throw error;
    }
  }

  /**
   * Note: Token validation happens automatically during organization creation.
   * The backend's create_organization_tenant() calls verify_invitation() inline,
   * so there's no need for a separate accept/validate endpoint.
   */

  /**
   * Create organization using invite token
   * POST /api/organization/create
   */
  static async createOrganization(data: {
    name: string;
    country: string;
    city: string;
    contact_email: string;
    phone_number: string;
    description?: string;
    website?: string;
    industry?: string;
    size?: string;
    settings?: Record<string, any>;
    invite_token?: string;
  }): Promise<Organization> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/organization/create`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      await handleApiError(response);
      const result = await response.json();

      // Extract organization data from wrapped response
      if (result.success && result.data) {
        return result.data;
      }

      throw new Error('Invalid response format from organization creation endpoint');
    } catch (error) {
      logError('createOrganization', error);
      throw error;
    }
  }

  /**
   * Organization admin invites users (individuals & team leaders)
   * POST /api/organization/admin/{id}/invite
   */
  static async inviteUsersToOrganization(
    organizationId: string,
    data: {
      individual_members: Array<{
        email: string;
        credits: number;
        is_admin?: boolean;
        cohort_id?: string;
        can_skip_modules?: boolean
      }>;
      team_leaders: Array<{
        email: string;
        credits: number;
        is_admin?: boolean;
        cohort_id?: string;
        can_skip_modules?: boolean
      }>;
      organization_admins?: Array<{
        email: string;
        credits: number;
        is_admin?: boolean;
        cohort_id?: string | null;
        can_skip_modules?: boolean
      }>;
    }
  ): Promise<{
    success: boolean;
    message: string;
    invites: { email: string; is_admin: boolean; is_team_leader: boolean; credits: number }[];
    invitation_ids: string[]
  }> {
    try {
      // Transform to backend format
      const invites = [
        ...data.individual_members.map(m => {
          const item: any = {
            email: m.email,
            is_admin: m.is_admin || false,
            is_team_leader: false,
            credit_allocated: m.credits,
            cohort_id: m.cohort_id,
            can_skip_modules: m.can_skip_modules ?? false,
          };
          return item;
        }),
        ...data.team_leaders.map(l => {
          const item: any = {
            email: l.email,
            is_admin: l.is_admin || false,
            is_team_leader: true,
            credit_allocated: l.credits,
            cohort_id: l.cohort_id,
            can_skip_modules: l.can_skip_modules ?? false,
          };
          return item;
        }),
        ...(data.organization_admins || []).map(a => {
          const item: any = {
            email: a.email,
            is_admin: true,
            is_team_leader: false,
            credit_allocated: a.credits || 0,
            cohort_id: a.cohort_id || null,
            can_skip_modules: a.can_skip_modules ?? false,
          };
          return item;
        }),
      ];

      console.log('Invitessssssssssssssssssssssssssssss:', invites);

      const response = await fetch(`${API_BASE_URL}/api/organization/admin/${organizationId}/invite`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Accept': 'application/json',
        },
        body: JSON.stringify({ invites }),
      });
      await handleApiError(response);

      const responseText = await response.text();
      let result: any;
      try {
        result = responseText ? JSON.parse(responseText) : {};
      } catch (e) {
        result = { message: responseText };
      }

      // Transform response to match expected format
      const message = typeof result === 'string' ? result : (result.message || `Successfully invited ${invites.length} users`);

      const returnedInvites = (result && result.invites && result.invites.length > 0)
        ? result.invites.map((i: any) => ({
          email: i.email,
          is_admin: i.is_admin,
          is_team_leader: i.is_team_leader,
          credits: i.credits !== undefined ? i.credits : (i.credit_allocated !== undefined ? i.credit_allocated : 0),
        }))
        : invites.map((i: any) => ({
          email: i.email,
          is_admin: i.is_admin,
          is_team_leader: i.is_team_leader,
          credits: i.credit_allocated,
        }));

      return {
        success: true,
        message,
        invites: returnedInvites,
        invitation_ids: (result && (result.invitation_ids || result.ids)) || [],
      };
    } catch (error) {
      logError('inviteUsersToOrganization', error);
      throw error;
    }
  }

  /**
   * Join organization using invite token
   * POST /api/organization/{id}/join
   */
  static async joinOrganization(organizationId: string, inviteToken: string): Promise<{
    success: boolean;
    message: string;
    data: {
      tenant_id: string;
      user_id: string;
      role: string;
      is_active: boolean;
    };
  }> {
    try {
      // First, join the organization
      const response = await fetch(`${API_BASE_URL}/api/organization/${organizationId}/join`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ invite_token: inviteToken }),
      });
      await handleApiError(response);
      const result = await response.json();

      // Update the auth token with the new organization-scoped token
      if (result.auth?.access_token) {
        authService.setToken(result.auth.access_token);
        if (process.env.NODE_ENV === 'development') {
          console.log('✅ Updated auth token after joining organization');
        }
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('joinOrganization result:', result);
      }

      return result;
    } catch (error) {
      logError('joinOrganization', error);
      throw error;
    }
  }

  /**
   * Get current user's membership details in an organization
   * GET /api/organization/{id}/membership
   */
  static async getUserMembershipDetails(organizationId: string): Promise<{
    membership: {
      id: string;
      tenant_id: string;
      user_id: string;
      role: string;
      joined_at: string;
      is_active: boolean;
      permissions: Record<string, any>;
    };
    organization: {
      id: string;
      name: string;
      description: string | null;
      industry: string | null;
      size: string | null;
      country: string | null;
    };
    invitation: {
      credits_allocated: number;
      invited_by_email: string | null;
      accepted_at: string;
      is_team_leader: boolean;
      is_admin: boolean;
    };
  }> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/organization/${organizationId}/membership`,
        {
          method: 'GET',
          headers: getAuthHeaders(),
        }
      );
      await handleApiError(response);
      const result = await response.json();
      return result.data;
    } catch (error) {
      logError('getUserMembershipDetails', error);
      throw error;
    }
  }

  /**
   * Get organization details by ID (for organization owners and system admins)
   */
  static async getOrganizationById(organizationId: string): Promise<Organization> {
    try {
      const url = `${API_BASE_URL}/api/organization/${organizationId}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      const data = await response.json();

      if (data.success && data.data) {
        return data.data;
      } else {
        throw new Error('Invalid response format from organization details endpoint');
      }
    } catch (error) {
      logError('getOrganizationById', error);
      throw error;
    }
  }

  /**
   * Get the organization type for the currently authenticated org owner/admin.
   * GET /api/organization/my/type
   */
  static async getMyOrganizationType(): Promise<{
    success: boolean;
    organization_type: 'grant_org' | 'prepay_org' | 'postpay_org';
  }> {
    try {
      const url = `${API_BASE_URL}/api/organization/my/type`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      const data = await response.json();

      if (data.success && data.organization_type) {
        return data as { success: boolean; organization_type: 'grant_org' | 'prepay_org' | 'postpay_org' };
      } else {
        throw new Error('Invalid response format from organization type endpoint');
      }
    } catch (error) {
      logError('getMyOrganizationType', error);
      throw error;
    }
  }

  /**
   * Get organization metrics
   * GET /api/organization/{id}/metrics
   */
  static async getOrganizationMetrics(organizationId: string): Promise<{
    invitations: { sent: number; accepted: number };
    membership: { total: number; team_members: number; individual_members: number };
    credits?: { total: number; used: number; remaining: number; monthly_limit: number };
  }> {
    try {
      const url = `${API_BASE_URL}/api/organization/${organizationId}/metrics`;
      return await fetchJson(url, { method: 'GET' });
    } catch (error) {
      logError('getOrganizationMetrics', error);
      throw error;
    }
  }

  /**
   * Get organization teams overview
   * GET /api/organization/{id}/teams/overview
   */
  static async getOrganizationTeams(organizationId: string): Promise<{
    teams: Array<{
      team_id: string;
      team_name: string;
      team_leader: {
        user_id: string;
        full_name: string;
        email: string;
      } | null;
      members_count: number;
      credit_pool: {
        total: number;
        used: number;
        remaining: number;
        monthly_limit: number | null;
      };
    }>;
  }> {
    try {
      const url = `${API_BASE_URL}/api/organization/${organizationId}/teams/overview`;
      return await fetchJson(url, { method: 'GET' });
    } catch (error) {
      logError('getOrganizationTeams', error);
      throw error;
    }
  }

  /**
   * Get individual members (organization members who are NOT in any team)
   * GET /api/organization/{organizationId}/individual-members
   */
  static async getIndividualMembers(organizationId: string): Promise<{
    members: Array<{
      user_id: string;
      name: string;
      email: string;
      role: string;
      credits_allocated: number;
      credits_used: number;
      status: string;
      joined_at: string;
    }>;
  }> {
    try {
      const url = `${API_BASE_URL}/api/organization/${organizationId}/individual-members`;
      return await fetchJson(url, { method: 'GET' });
    } catch (error) {
      logError('getIndividualMembers', error);
      throw error;
    }
  }

  /**
   * Update organization details
   * PUT /api/organization/{id}
   */
  static async updateOrganization(
    organizationId: string,
    updateData: {
      name?: string;
      description?: string;
      website?: string;
      industry?: string;
      size?: string;
      country?: string;
      city?: string;
      contact_email?: string;
      phone_number?: string;
    }
  ): Promise<{ success: boolean; message: string; data: Organization }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/organization/${organizationId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(updateData),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('updateOrganization', error);
      throw error;
    }
  }

  /**
   * Delete organization
   * DELETE /api/organization/{id}
   */
  static async deleteOrganization(organizationId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/organization/${organizationId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('deleteOrganization', error);
      throw error;
    }
  }

  /**
   * Get organization members (team members only)
   * GET /api/organization/{organizationId}/teams/members
   */
  static async getOrganizationMembers(organizationId: string): Promise<{
    members: Array<{
      user_id: string;
      name: string;
      role: string;
      credits_allocated: number;
      credits_used: number;
      status: string;
      team_id: string;
      team_name: string;
    }>;
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/organization/${organizationId}/teams/members`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getOrganizationMembers', error);
      throw error;
    }
  }

  /**
   * Delete a member from the organization
   * DELETE /api/organization/{organizationId}/members/{userId}
   */
  static async deleteOrganizationMember(
    organizationId: string,
    userId: string
  ): Promise<{
    success: boolean;
    message: string;
    credits_returned: number;
    user_id: string;
    organization_id: string;
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/organization/${organizationId}/members/${userId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('deleteOrganizationMember', error);
      throw error;
    }
  }

  /**
   * Resend an invitation email for a pending or expired invitation
   * POST /api/organization/{organizationId}/invitations/{invitationId}/resend
   */
  static async resendInvitation(
    organizationId: string,
    invitationId: string
  ): Promise<{
    success: boolean;
    message: string;
    email: string;
    invitation_id: string;
  }> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/organization/${organizationId}/invitations/${invitationId}/resend`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
        }
      );
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('resendInvitation', error);
      throw error;
    }
  }

  /**
   * Check if user is a team leader in an organization
   * This checks if the user has pending team credits, which indicates they were invited as a team leader
   * 
   * Note: This is a workaround until the backend returns is_team_leader in the join response
   */
  static async isTeamLeader(organizationId: string): Promise<boolean> {
    try {
      // Check if user has pending team credits
      // This endpoint may not exist yet, so we'll handle the error gracefully
      const response = await fetch(`${API_BASE_URL}/api/organization/${organizationId}/pending-team-credits`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      if (response.status === 404) {
        // Endpoint doesn't exist, return false
        return false;
      }

      await handleApiError(response);
      const result = await response.json();

      // If there are pending team credits, user is a team leader
      return result.has_pending_credits === true || (result.data && result.data.length > 0);
    } catch (error) {
      logError('isTeamLeader', error);
      // If there's an error, assume not a team leader
      return false;
    }
  }

  /**
   * Grant additional credits to an organization (Super Admin only)
   * POST /credits/admin/grant
   * 
   * This creates NEW credits for the organization (not a transfer)
   * Note: This endpoint does NOT have /api prefix in the backend
   */
  static async grantCreditsToOrganization(
    organizationId: string,
    creditAmount: number
  ): Promise<{
    success: boolean;
    message?: string;
    organization_id: string;
    organization_name: string;
    credit_amount: number;
    expires_at: string;
    granted_by: string;
    granted_at: string;
    lot_id?: string;
    email_sent: boolean;
    email_recipient: string | null;
  }> {
    try {
      // Note: Credit endpoints don't have /api prefix in backend
      const url = `${API_BASE_URL}/credits/admin/grant`;
      console.log('[OrganizationService] Granting credits:', { url, organizationId, creditAmount });

      const response = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          organization_id: organizationId,
          credit_amount: creditAmount,
        }),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('grantCreditsToOrganization', error);
      throw error;
    }
  }

  /**
   * Allocate credits from organization to a member (individual or team)
   * POST /credits/orgs/{organization_id}/allocate
   * 
   * This transfers credits from the organization's pool to a member
   * Note: This endpoint does NOT have /api prefix in the backend
   */
  static async allocateCreditsToMember(
    organizationId: string,
    tenantId: string,
    tenantType: 'individual' | 'team',
    creditAmount: number
  ): Promise<{
    success: boolean;
    message: string;
    organization_id: string;
    organization_name?: string;
    tenant_id: string;
    tenant_name?: string;
    tenant_type: string;
    credit_amount: number;
    expires_at: string;
    allocated_by: string;
    allocated_at: string;
    remaining_org_credits: number;
    email_sent: boolean;
    email_recipient: string | null;
  }> {
    try {
      // Note: Credit endpoints don't have /api prefix in backend
      const url = `${API_BASE_URL}/credits/orgs/${organizationId}/allocate`;
      console.log('[OrganizationService] Allocating credits:', { url, organizationId, tenantId, tenantType, creditAmount });

      const response = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          tenant_id: tenantId,
          tenant_type: tenantType,
          credit_amount: creditAmount,
        }),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('allocateCreditsToMember', error);
      throw error;
    }
  }

  /**
   * Get all organization members with their projects
   * GET /api/organization/{organization_id}/member-projects
   * 
   * This endpoint retrieves all members (individual and team) along with
   * their project summaries. Results are paginated and can be filtered by member type.
   * 
   * @param organizationId - The organization ID
   * @param params - Optional query parameters
   * @param params.page - Page number (default: 1)
   * @param params.page_size - Items per page (default: 20, max: 50)
   * @param params.member_type - Filter by member type: 'individual', 'team', or 'all' (default: 'all')
   * 
   * @returns MemberProjectsResponse with paginated member list and their projects
   * 
   * @example
   * const response = await OrganizationService.getMemberProjects(orgId, {
   *   page: 1,
   *   page_size: 20,
   *   member_type: 'individual'
   * });
   */
  static async getMemberProjects(
    organizationId: string,
    params?: {
      page?: number;
      page_size?: number;
      member_type?: 'individual' | 'team' | 'all';
    }
  ): Promise<MemberProjectsResponse> {
    try {
      const queryParams = new URLSearchParams();

      // Add pagination parameters with defaults
      queryParams.append('page', (params?.page || 1).toString());
      queryParams.append('page_size', (params?.page_size || 20).toString());

      // Add member type filter if specified
      if (params?.member_type && params.member_type !== 'all') {
        queryParams.append('member_type', params.member_type);
      }

      const url = `${API_BASE_URL}/api/organization/${organizationId}/member-projects?${queryParams.toString()}`;

      if (process.env.NODE_ENV === 'development') {
        console.log('[OrganizationService] Fetching member projects:', { url, organizationId, params });
      }

      // Use resilient fetchJson with retries
      const response = await fetchJson<MemberProjectsResponse>(
        url,
        { method: 'GET' },
        { retries: 2, timeoutMs: 20000 }
      );

      if (process.env.NODE_ENV === 'development') {
        console.log('[OrganizationService] Member projects fetched:', {
          totalCount: response?.total_count,
          membersCount: response?.members?.length,
          page: response?.page,
          hasNext: response?.has_next
        });
      }

      return response;
    } catch (error) {
      logError('getMemberProjects', error);
      throw error;
    }
  }

  /**
   * Get projects for a specific tenant (individual or team)
   * GET /api/organization/{organization_id}/tenants/{tenant_id}/projects
   * 
   * This endpoint retrieves all projects belonging to a specific tenant within
   * the organization. Results are paginated.
   * 
   * @param organizationId - The organization ID
   * @param tenantId - The tenant ID (individual_tenant_id or team_id)
   * @param params - Optional query parameters
   * @param params.page - Page number (default: 1)
   * @param params.page_size - Items per page (default: 20, max: 50)
   * 
   * @returns TenantProjectsResponse with tenant info and paginated projects
   * 
   * @example
   * const response = await OrganizationService.getTenantProjects(orgId, tenantId, {
   *   page: 1,
   *   page_size: 20
   * });
   */
  static async getTenantProjects(
    organizationId: string,
    tenantId: string,
    params?: {
      page?: number;
      page_size?: number;
      search?: string;
    }
  ): Promise<TenantProjectsResponse> {
    try {
      const queryParams = new URLSearchParams();

      // Add pagination parameters with defaults
      queryParams.append('page', (params?.page || 1).toString());
      queryParams.append('page_size', (params?.page_size || 20).toString());

      // Add search parameter if specified
      if (params?.search) {
        queryParams.append('search', params.search);
      }

      const url = `${API_BASE_URL}/api/organization/${organizationId}/tenants/${tenantId}/projects?${queryParams.toString()}`;

      if (process.env.NODE_ENV === 'development') {
        console.log('[OrganizationService] Fetching tenant projects:', { url, organizationId, tenantId, params });
      }

      // Use resilient fetchJson with retries
      const response = await fetchJson<TenantProjectsResponse>(
        url,
        { method: 'GET' },
        { retries: 2, timeoutMs: 20000 }
      );

      if (process.env.NODE_ENV === 'development') {
        console.log('[OrganizationService] RAW API Response:', JSON.stringify(response, null, 2));
        console.log('[OrganizationService] Tenant projects fetched:', {
          tenantId: response?.tenant?.tenant_id || response?.tenant?.id,
          tenantType: response?.tenant?.tenant_type,
          totalCount: response?.total_count,
          projectsCount: response?.projects?.length,
          page: response?.page,
          hasNext: response?.has_next
        });
      }

      // Normalize the response to ensure tenant_id exists
      if (response?.tenant && !response.tenant.tenant_id && response.tenant.id) {
        response.tenant.tenant_id = response.tenant.id;
      }

      return response;
    } catch (error) {
      logError('getTenantProjects', error);
      throw error;
    }
  }

  /**
   * Get detailed information for a specific member's project
   * GET /api/organization/{organization_id}/member-projects/{project_id}
   * 
   * This endpoint retrieves complete project data including:
   * - Full project details (VPC data, field prep data, etc.)
   * - Owner information
   * - PV Report (if available)
   * - Access log (audit trail)
   * 
   * Note: This endpoint logs the access for audit purposes on the backend.
   * 
   * @param organizationId - The organization ID
   * @param projectId - The project ID
   * 
   * @returns MemberProjectDetailResponse with complete project data
   * 
   * @example
   * const response = await OrganizationService.getMemberProjectDetail(orgId, projectId);
   * console.log(response.project.vpc_data); // Access VPC data
   * console.log(response.pv_report); // Access PV report
   */
  static async getMemberProjectDetail(
    organizationId: string,
    projectId: string
  ): Promise<MemberProjectDetailResponse> {
    try {
      const url = `${API_BASE_URL}/api/organization/${organizationId}/member-projects/${projectId}`;

      if (process.env.NODE_ENV === 'development') {
        console.log('[OrganizationService] Fetching member project detail:', { url, organizationId, projectId });
      }

      // Use resilient fetchJson with retries and longer timeout for large project data
      const response = await fetchJson<MemberProjectDetailResponse>(
        url,
        { method: 'GET' },
        { retries: 2, timeoutMs: 30000 } // Longer timeout for large datasets
      );

      if (process.env.NODE_ENV === 'development') {
        console.log('[OrganizationService] Member project detail fetched:', {
          projectId: response?.project?.id,
          projectName: response?.project?.name,
          ownerType: response?.owner?.member_type,
          hasPvReport: !!response?.pv_report,
          // Personas from personas column
          projectPersonasCount: response?.project?.personas?.length || 0,
          // Personas from vpc_data.vpcs
          vpcPersonasCount: response?.project?.vpc_data?.vpcs ? Object.keys(response.project.vpc_data.vpcs).length : 0,
          hypothesesCount: response?.project?.field_prep_data?.hypotheses?.length || 0,
          assumptionsCount: response?.project?.field_prep_data?.assumptions?.length || 0,
          questionnairesCount: response?.project?.field_prep_data?.questionnaires?.length || 0
        });
        // Log raw personas data for debugging
        console.log('[OrganizationService] Personas data:', {
          personas: response?.project?.personas,
          vpc_data: response?.project?.vpc_data,
          // Check for customer profile at root level
          hasRootCustomerProfile: !!response?.project?.vpc_data?.customer_profile,
          rootCustomerProfile: response?.project?.vpc_data?.customer_profile
        });
      }

      return response;
    } catch (error) {
      logError('getMemberProjectDetail', error);
      throw error;
    }
  }

  /**
   * Soft delete a team from the organization
   * DELETE /api/organization/{organizationId}/teams/{teamId}
   * 
   * This performs a soft delete:
   * - Sets team is_active = false
   * - Deactivates all team memberships
   * - Returns remaining credits to the organization
   * 
   * @param organizationId - The organization ID
   * @param teamId - The team ID to delete
   * @param returnCredits - Whether to return remaining credits to org (default: true)
   * 
   * @returns DeleteTeamResponse with deletion details
   */
  static async deleteTeam(
    organizationId: string,
    teamId: string,
    returnCredits: boolean = true
  ): Promise<{
    success: boolean;
    message: string;
    team_id: string;
    team_name: string;
    organization_id: string;
    members_deactivated: number;
    credits_returned_to_org: number;
    credit_lots_deactivated: number;
    deleted_at: string;
    deleted_by: string;
  }> {
    try {
      const url = `${API_BASE_URL}/api/organization/${organizationId}/teams/${teamId}?return_credits=${returnCredits}`;

      if (process.env.NODE_ENV === 'development') {
        console.log('[OrganizationService] Deleting team:', { organizationId, teamId, returnCredits });
      }

      const response = await fetchJson(url, { method: 'DELETE' });

      if (process.env.NODE_ENV === 'development') {
        console.log('[OrganizationService] Team deleted:', response);
      }

      return response;
    } catch (error) {
      logError('deleteTeam', error);
      throw error;
    }
  }
}

// Export singleton instance
export const organizationService = OrganizationService;
