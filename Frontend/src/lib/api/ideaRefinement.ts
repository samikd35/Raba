// lib/api/ideaRefinement.ts

/**
 * Idea Refinement API Module
 * Handles communication with the backend API for idea refinement
 * @version 2.0.0
 */

// ============================================================================
// Constants
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL

export const VALIDATION_LIMITS = {
  MIN_LENGTH: 10,
  MAX_LENGTH: 1000,
} as const

// ============================================================================
// Type Definitions
// ============================================================================

export interface IdeaRefinementRequest {
  original_idea: string
  refinement_type: string
  context?: Record<string, unknown>
}

export interface ProblemStatement {
  stakeholder: string
  statement: string
  assumptions: string[]
  overall_score?: number
}

export interface ParsedContext {
  persona: string
  industry: string
  geography: string
  delivery_mode: string
}

export interface IdeaRefinementResponse {
  success: boolean
  session_id: string
  problem_statements: ProblemStatement[]
  parsed_context: ParsedContext
  processing_time: number
}

export interface RefinementSession {
  id: string
  tenant_id: string
  user_id: string
  session_title: string
  original_idea: string
  status: string
  parsed_context: Record<string, any>
  problem_statements: ProblemStatement[]
  problem_scores: any
  interview_questions: any
  validation_cues: any
  refined_variants: any
  researched: boolean
  research_notes: any
  processing_time_seconds: number
  metadata: {
    idea_length: number
    average_score: number
    problems_generated: number
  }
  created_at: string
  updated_at: string
  completed_at: string
}

export interface RefinementHistoryResponse {
  success: boolean
  session: RefinementSession
  session_id: string
}

export interface ValidationResult {
  isValid: boolean
  error?: string
}

export class IdeaRefinementError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
  ) {
    super(message)
    this.name = "IdeaRefinementError"
  }
}

// ============================================================================
// Validation Functions
// ============================================================================

/**
 * Validate idea input before sending to API
 * Checks for empty input, minimum and maximum length requirements
 */
export function validateIdeaInput(idea: string): ValidationResult {
  const trimmedIdea = idea.trim()

  if (!trimmedIdea) {
    return { isValid: false, error: "Please enter an idea to refine" }
  }

  if (trimmedIdea.length < VALIDATION_LIMITS.MIN_LENGTH) {
    return {
      isValid: false,
      error: `Please provide a more detailed idea (at least ${VALIDATION_LIMITS.MIN_LENGTH} characters)`,
    }
  }

  if (trimmedIdea.length > VALIDATION_LIMITS.MAX_LENGTH) {
    return {
      isValid: false,
      error: `Please keep your idea under ${VALIDATION_LIMITS.MAX_LENGTH} characters`,
    }
  }

  return { isValid: true }
}

// ============================================================================
// Error Handling Utilities
// ============================================================================

/**
 * Parse error response from API
 */
async function parseErrorResponse(response: Response): Promise<string> {
  let errorData: Record<string, unknown> = {}
  let errorText = ""

  try {
    errorText = await response.text()
    errorData = JSON.parse(errorText)
  } catch {
    errorData = { message: errorText || "Unknown error" }
  }

  // Log detailed error information for debugging
  console.error("Idea Refinement API Error:", {
    status: response.status,
    statusText: response.statusText,
    headers: Object.fromEntries(response.headers.entries()),
    errorData,
    rawErrorText: errorText,
  })

  return extractErrorMessage(errorData, response.status)
}

/**
 * Extract user-friendly error message from error data
 */
function extractErrorMessage(errorData: Record<string, unknown>, status: number): string {
  // Try to extract message from various possible fields
  if (typeof errorData.message === "string") {
    return errorData.message
  }

  if (typeof errorData.detail === "string") {
    return errorData.detail
  }

  if (typeof errorData.detail === "object" && errorData.detail !== null) {
    const detail = errorData.detail as Record<string, unknown>
    if (typeof detail.message === "string") {
      return detail.message
    }
  }

  // Fallback to status-specific messages
  return getStatusErrorMessage(status)
}

/**
 * Get user-friendly error message based on HTTP status code
 */
function getStatusErrorMessage(status: number): string {
  const statusMessages: Record<number, string> = {
    400: "Invalid request. Please check your input and try again.",
    401: "Authentication failed. Please log in again.",
    402: "You don't have enough credits for this feature.",
    403: "Access denied. You may not have permission to refine ideas.",
    404: "Service not found. Please contact support.",
    429: "Too many requests. Please wait a moment and try again.",
    500: "Server error. Please try again later.",
    502: "Service temporarily unavailable. Please try again later.",
    503: "Service temporarily unavailable. Please try again later.",
  }

  return statusMessages[status] || `Request failed with status ${status}`
}

/**
 * Check if error is a network error
 */
function isNetworkError(error: unknown): boolean {
  return (
    error instanceof TypeError &&
    (error.message.toLowerCase().includes("fetch") ||
      error.message.toLowerCase().includes("network") ||
      error.message.toLowerCase().includes("failed to fetch"))
  )
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch idea refinement history from the backend
 *
 * @param sessionId - The session ID to fetch history for
 * @param userId - The user ID for authentication
 * @param authToken - Authentication token for API access
 * @returns Promise resolving to the refinement history response
 * @throws {IdeaRefinementError} If authentication is missing or API request fails
 */
export async function getRefinementHistory(
  sessionId: string,
  authToken: string,
): Promise<RefinementHistoryResponse> {
  if (!authToken) {
    throw new IdeaRefinementError('Authentication token is required');
  }

  if (!sessionId) {
    throw new IdeaRefinementError('Session ID is required');
  }

  const endpoint = `${API_BASE_URL}/api/v1/idea-refinement/history/${sessionId}`;
  
  if (process.env.NODE_ENV === 'development') {
    console.log('🔍 Fetching refinement history from:', endpoint);
    console.log('🔍 Session ID:', sessionId);
    console.log('🔍 Token preview:', authToken.substring(0, 20) + '...');
  }

  try {
    const response = await fetch(
      endpoint,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
      }
    );

    if (process.env.NODE_ENV === 'development') {
      console.log('📡 Response status:', response.status, response.statusText);
    }

    if (!response.ok) {
      let errorMessage = `Failed to fetch refinement history (${response.status} ${response.statusText})`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorData.detail || errorMessage;
        if (process.env.NODE_ENV === 'development') {
          console.log('❌ Error response:', errorData);
        }
      } catch (parseError) {
        if (process.env.NODE_ENV === 'development') {
          console.log('❌ Failed to parse error response:', parseError);
        }
      }
      
      const error = new IdeaRefinementError(errorMessage);
      error.status = response.status;
      throw error;
    }

    const data: RefinementHistoryResponse = await response.json();
    
    if (process.env.NODE_ENV === 'development') {
      console.log('✅ Successfully fetched refinement history:', {
        sessionId: data.session_id,
        success: data.success,
        problemCount: data.session?.problem_statements?.length || 0
      });
    }
    
    return data;
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('💥 Network or fetch error:', error);
    }
    
    if (error instanceof IdeaRefinementError) {
      throw error;
    }
    
    // Handle network errors
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new IdeaRefinementError('Network error. Please check your connection and try again.');
    }
    
    throw new IdeaRefinementError(
      error instanceof Error ? error.message : 'An unexpected error occurred'
    );
  }
}

/**
 * Refine an idea by submitting it to the backend API
 *
 * @param originalIdea - The idea text to refine
 * @param authToken - Authentication token for API access
 * @param refinementType - Type of refinement to perform (default: 'problem_statement')
 * @returns Promise resolving to the refinement response
 * @throws {IdeaRefinementError} If validation fails, authentication is missing, or API request fails
 */
export async function refineIdea(
  originalIdea: string,
  authToken: string,
  refinementType = "problem_statement",
): Promise<IdeaRefinementResponse> {
  // Validate inputs
  const validation = validateIdeaInput(originalIdea)
  if (!validation.isValid) {
    throw new IdeaRefinementError(validation.error || "Invalid input", undefined, "VALIDATION_ERROR")
  }

  if (!authToken) {
    throw new IdeaRefinementError("Authentication required. Please log in to refine ideas.", 401, "AUTH_REQUIRED")
  }

  // Prepare request
  const requestPayload: IdeaRefinementRequest = {
    original_idea: originalIdea.trim(),
    refinement_type: refinementType,
    context: {},
  }

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${authToken}`,
  }

  console.log("Auth Tokennnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn:", authToken)

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/idea-refinement/refine`, {
      method: "POST",
      headers,
      body: JSON.stringify(requestPayload),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new IdeaRefinementError(errorMessage, response.status, "API_ERROR")
    }

    const data: IdeaRefinementResponse = await response.json()

    // Validate response structure
    if (!data.problem_statements || !Array.isArray(data.problem_statements)) {
      throw new IdeaRefinementError(
        "Invalid response format: missing problem statements",
        undefined,
        "INVALID_RESPONSE",
      )
    }

    if (!data.success) {
      throw new IdeaRefinementError("Idea refinement failed. Please try again.", undefined, "REFINEMENT_FAILED")
    }

    return data
  } catch (error) {
    console.error("Idea refinement error:", error)

    // Re-throw our custom errors as-is
    if (error instanceof IdeaRefinementError) {
      throw error
    }

    // Handle network errors
    if (isNetworkError(error)) {
      throw new IdeaRefinementError(
        "Network error. Please check your connection and try again.",
        undefined,
        "NETWORK_ERROR",
      )
    }

    // Handle other unexpected errors
    throw new IdeaRefinementError(
      error instanceof Error ? error.message : "An unexpected error occurred while refining your idea",
      undefined,
      "UNKNOWN_ERROR",
    )
  }
}
