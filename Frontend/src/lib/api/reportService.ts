/**
 * Report Service
 * Handles user reports (profile/message reports) and problem validation reports
 */

import { authService } from '@/services/authService';
import type {
  ReportStatistics,
  ReportListResponse,
  ReportResponse,
  ReportFilters,
  ResolveReportRequest,
} from '@/types/reports';

interface BackendReportData {
  success: boolean;
  data: {
    id: string;
    title: string;
    summary: string;
    report_type: string;
    created_at: string;
    updated_at: string;
    content: {
      title: string;
      executive_summary: string;
      industry_analysis: string;
      challenges_analysis: string;
      recommendations: string;
      sources: SourceItem[];
      tenant_id: string;
    };
  };
  report_id: string;
  job_id: string;
  actionable_insights?: {
    insights: any[];
    total_insights: number;
    status: string;
  };
  message: string;
  error: string | null;
}

interface SourceItem {
  number?: number;
  source_url: string;
  source_title?: string;
  credibility_score?: number;
  publication_date?: string;
}

// Share-related interfaces
export interface CreateShareRequest {
  session_id: string;
  access_type?: 'view' | 'download';
  password?: string;
  is_public?: boolean;
  allowed_emails?: string[];
  max_views?: number;
  expires_in_days?: number;
  share_message?: string;
}

export interface ShareData {
  id: string;
  share_token: string;
  share_url: string;
  session_id: string;
  report_id: string;
  report_title: string;
  access_type: string;
  is_public: boolean;
  has_password: boolean;
  allowed_emails: string[];
  max_views: number;
  view_count: number;
  expires_at: string;
  is_active: boolean;
  is_expired: boolean;
  is_view_limit_reached: boolean;
  share_message: string;
  created_at: string;
  last_accessed_at: string | null;
  revoked_at: string | null;
}

export interface CreateShareResponse {
  success: boolean;
  message: string;
  share: ShareData;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

/**
 * Get authentication token
 * @throws Error if no token available
 */
const getAuthToken = (): string => {
  if (typeof window === 'undefined') {
    throw new Error('Authentication required. Cannot access token on server side.');
  }

  const token = authService.getCurrentToken();
  if (!token) {
    throw new Error('Authentication required. Please sign in to continue.');
  }
  return token;
};

/**
 * Get auth headers for API requests
 */
const getAuthHeaders = (): HeadersInit => {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getAuthToken()}`,
  };
};

/**
 * Handle API errors consistently
 */
const handleApiError = async (response: Response): Promise<never> => {
  let errorMessage = `Request failed with status ${response.status}`;

  try {
    const errorData = await response.json();
    console.error('API Error Response:', errorData);

    // Handle FastAPI validation errors
    if (errorData.detail && Array.isArray(errorData.detail)) {
      const validationErrors = errorData.detail.map((err: any) => {
        const location = err.loc ? err.loc.join(' -> ') : 'unknown';
        return `${location}: ${err.msg}`;
      }).join('\n');
      errorMessage = `Validation Error:\n${validationErrors}`;
    } else if (errorData.detail) {
      errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
    } else if (errorData.message) {
      errorMessage = errorData.message;
    }
  } catch {
    // If response is not JSON, use status text
    errorMessage = response.statusText || errorMessage;
  }

  throw new Error(errorMessage);
};

/**
 * Fetches a problem validation report by ID from the backend API
 * @param reportId - The ID of the report to fetch
 * @param token - Authentication token
 * @returns Promise<BackendReportData>
 * @throws Error if the request fails or user doesn't have permission
 */
export async function fetchReport(reportId: string, token: string): Promise<BackendReportData> {
  console.log(`reportId`, reportId)
  console.log(`token`, token)
  if (!reportId) {
    throw new Error('Report ID is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  try {
    const response = await fetch(`${apiUrl}/api/reports/${reportId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    console.log(`responseeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee`, response)

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      // Handle specific error cases
      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 403) {
        throw new Error('Access denied. You may not have permission to view this report or it may not exist.');
      }

      if (response.status === 404) {
        throw new Error('Report not found. The report may have been deleted or the ID is incorrect.');
      }

      throw new Error(`Failed to fetch report: ${response.status} ${response.statusText}`);
    }

    const data: BackendReportData = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to fetch report data');
    }

    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching the report');
  }
}

/**
 * Fetches a public problem validation report by ID (no authentication required)
 * This is used for shared report links that anyone can view
 * @param reportId - The ID of the report to fetch
 * @returns Promise<BackendReportData>
 * @throws Error if the request fails or report doesn't exist
 */
export async function fetchPublicReport(reportId: string): Promise<BackendReportData> {
  if (!reportId) {
    throw new Error('Report ID is required');
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  try {
    const response = await fetch(`${apiUrl}/api/reports/${reportId}/public`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Public API error: ${response.status} - ${errorText}`);

      if (response.status === 404) {
        throw new Error('Report not found. The report may have been deleted or the link is invalid.');
      }

      if (response.status === 403) {
        throw new Error('This report is not available for public viewing.');
      }

      throw new Error(`Failed to fetch report: ${response.status} ${response.statusText}`);
    }

    const data: BackendReportData = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to fetch report data');
    }

    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching the report');
  }
}

/**
 * Creates a shareable link for a problem validation report
 * @param request - Share creation request with session_id and options
 * @param token - Authentication token
 * @returns Promise<CreateShareResponse>
 */
export async function createReportShare(
  request: CreateShareRequest,
  token: string
): Promise<CreateShareResponse> {
  if (!request.session_id) {
    throw new Error('Session ID is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  try {
    const response = await fetch(`${apiUrl}/api/workflow/share`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: request.session_id,
        access_type: request.access_type || 'view',
        is_public: request.is_public ?? true,
        password: request.password,
        allowed_emails: request.allowed_emails,
        max_views: request.max_views,
        expires_in_days: request.expires_in_days,
        share_message: request.share_message,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Share API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 404) {
        throw new Error('Report not found.');
      }

      throw new Error(`Failed to create share link: ${response.status}`);
    }

    const data: CreateShareResponse = await response.json();

    if (!data.success) {
      throw new Error(data.message || 'Failed to create share link');
    }

    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while creating share link');
  }
}

/**
 * Fetches a shared report using a share token (no authentication required)
 * @param shareToken - The share token from the share URL
 * @param password - Optional password if the share is password-protected
 * @returns Promise<BackendReportData>
 */
export async function fetchSharedReport(
  shareToken: string,
  password?: string
): Promise<BackendReportData> {
  if (!shareToken) {
    throw new Error('Share token is required');
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  try {
    const url = new URL(`${apiUrl}/api/workflow/share/${shareToken}`);
    if (password) {
      url.searchParams.append('password', password);
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Shared report API error: ${response.status} - ${errorText}`);

      if (response.status === 404) {
        throw new Error('This shared link is invalid or has expired.');
      }

      if (response.status === 403) {
        throw new Error('Access denied. This link may require a password or you may not have permission.');
      }

      if (response.status === 410) {
        throw new Error('This shared link has expired or reached its view limit.');
      }

      throw new Error(`Failed to fetch shared report: ${response.status}`);
    }

    const data: BackendReportData = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to fetch shared report');
    }

    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching the shared report');
  }
}

/**
 * Downloads the problem validation report as a PDF
 * @param sessionId - The workflow session ID
 * @param token - Authentication token
 * @returns Promise<Blob>
 */
export async function downloadReportPdf(sessionId: string, token: string): Promise<Blob> {
  if (!sessionId) {
    throw new Error('Session ID is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  try {
    const response = await fetch(`${apiUrl}/api/workflow/report/${sessionId}/download`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/pdf',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Download API error: ${response.status} - ${errorText}`);

      if (response.status === 403) {
        throw new Error("This is a Premium feature. Please upgrade to download PDF reports.");
      }
      if (response.status === 404) {
        throw new Error("Report not found or workflow not completed.");
      }
      throw new Error(`Download failed: ${response.status} - ${errorText}`);
    }

    return await response.blob();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while downloading the report');
  }
}

// ============================================================================
// REPORTS USER API - User report submission
// ============================================================================

export class ReportsUserAPI {
  /**
   * POST /profiles/reports/profile - Report a profile
   */
  static async reportProfile(request: {
    reported_profile_id: string;
    reason: string;
    description?: string;
  }): Promise<ReportResponse> {
    const response = await fetch(`${API_BASE_URL}/profiles/reports/profile`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * POST /profiles/reports/message - Report a message
   */
  static async reportMessage(request: {
    message_id: string;
    reason: string;
    description?: string;
  }): Promise<ReportResponse> {
    const response = await fetch(`${API_BASE_URL}/profiles/reports/message`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }
}

// ============================================================================
// REPORTS ADMIN API - Admin report management (requires admin role)
// ============================================================================

export class ReportsAdminAPI {
  /**
   * GET /profiles/reports/stats - Get report statistics
   */
  static async getStatistics(): Promise<ReportStatistics> {
    const response = await fetch(`${API_BASE_URL}/profiles/reports/stats`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * GET /profiles/reports/ - List reports with filters
   */
  static async listReports(filters?: ReportFilters): Promise<ReportListResponse> {
    const params = new URLSearchParams();

    if (filters?.status) params.append('status', filters.status);
    if (filters?.report_type) params.append('report_type', filters.report_type);
    if (filters?.page) params.append('page', String(filters.page));
    if (filters?.page_size) params.append('page_size', String(filters.page_size));

    const queryString = params.toString();
    const url = `${API_BASE_URL}/profiles/reports/${queryString ? `?${queryString}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * POST /profiles/reports/{report_id}/resolve - Resolve a report
   */
  static async resolveReport(
    reportId: string,
    resolveRequest: ResolveReportRequest
  ): Promise<ReportResponse> {
    const response = await fetch(`${API_BASE_URL}/profiles/reports/${reportId}/resolve`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(resolveRequest),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }
}

// ============================================================================
// CONVENIENCE EXPORTS
// ============================================================================

/**
 * Combined API client for Reports
 */
export const reportAPI = {
  user: ReportsUserAPI,
  admin: ReportsAdminAPI,
};

export default reportAPI;

/**
 * Type exports for use in other parts of the application
 */
export type { BackendReportData, SourceItem };