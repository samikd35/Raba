import { WorkflowResponse, AnswerPayload, ReportResponse } from '@/types/validation';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

// Configuration constants
export const API_CONFIG = {
  DEFAULT_TIMEOUT: 30000, // 30 seconds
  POLLING_MAX_ATTEMPTS: 60,
  POLLING_INITIAL_DELAY: 5000, // Start with 5 seconds to reduce server load
  POLLING_MAX_DELAY: 30000, // Increase max delay to 30 seconds
  POLLING_BACKOFF_MULTIPLIER: 1.5, // More aggressive backoff to slow down faster
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
  RETRY_STATUS_CODES: [408, 429, 500, 502, 503, 504], // Retryable HTTP status codes
} as const;

// Enhanced error class with more context
export class WorkflowAPIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code: string = 'UNKNOWN_ERROR',
    public retryable: boolean = false,
    public details?: unknown
  ) {
    super(message);
    this.name = 'WorkflowAPIError';
    
    // Maintain proper stack trace for where error was thrown
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, WorkflowAPIError);
    }
  }
}

// Request cache for deduplication
const requestCache = new Map<string, Promise<any>>();

// Helper function to create cache key
function getCacheKey(url: string, options: RequestInit): string {
  return `${options.method || 'GET'}:${url}:${options.body || ''}`;
}

// Helper function for delay
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Conditional logging based on environment
function logDebug(...args: any[]): void {
  if (process.env.NODE_ENV === 'development') {
    console.log('[WorkflowAPI]', ...args);
  }
}

function logError(...args: any[]): void {
  console.error('[WorkflowAPI]', ...args);
}

/**
 * Robust API request wrapper with timeout, retry, and abort support.
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
  authToken?: string,
  config: {
    timeout?: number;
    retryAttempts?: number;
    signal?: AbortSignal;
    skipCache?: boolean;
  } = {}
): Promise<T> {
  // Input validation
  if (!endpoint) {
    throw new WorkflowAPIError('Endpoint is required', undefined, 'INVALID_INPUT');
  }

  if (!authToken) {
    throw new WorkflowAPIError('Authentication token is required', 401, 'AUTH_REQUIRED');
  }

  // Safe URL construction
  const url = endpoint.startsWith('http') 
    ? endpoint 
    : `${API_BASE_URL.replace(/\/$/, '')}/${endpoint.replace(/^\//, '')}`;

  const timeout = config.timeout || API_CONFIG.DEFAULT_TIMEOUT;
  const maxRetries = config.retryAttempts ?? API_CONFIG.RETRY_ATTEMPTS;
  
  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
    'Authorization': `Bearer ${authToken}`
  };

  const cacheKey = getCacheKey(url, options);

  // Check cache for GET requests
  if (options.method === 'GET' && !config.skipCache && requestCache.has(cacheKey)) {
    logDebug(`Returning cached response for: ${url}`);
    return requestCache.get(cacheKey)!;
  }

  const executeRequest = async (attempt: number = 0): Promise<T> => {
    // Create a timeout controller for this specific attempt
    const timeoutController = new AbortController();
    const timeoutId = setTimeout(() => timeoutController.abort(), timeout);

    // If an external signal exists, we need to respect it too
    const combinedSignal = config.signal || timeoutController.signal;
    
    // If the external signal aborts, we should abort our internal controller to be safe
    if (config.signal) {
      const abortHandler = () => {
        clearTimeout(timeoutId);
        if (!timeoutController.signal.aborted) {
          timeoutController.abort();
        }
      };
      
      if (!config.signal.aborted) {
        config.signal.addEventListener('abort', abortHandler, { once: true });
      } else {
        // Signal is already aborted, handle immediately
        abortHandler();
      }
    }

    try {
      logDebug(`Making API request to: ${url} (Attempt ${attempt + 1})`);
      
      const response = await fetch(url, {
        ...options,
        headers: defaultHeaders,
        signal: combinedSignal,
      });

      console.log(`Rrrrrrrrrrrrrrrresponse: ${JSON.stringify(response)}`);

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorData: any = {};
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

        try {
          const contentType = response.headers.get('content-type');
          if (contentType?.includes('application/json')) {
            errorData = await response.json();
            errorMessage = errorData.message || errorData.error || errorMessage;
          } else {
            errorMessage = await response.text() || errorMessage;
          }
        } catch (e) { /* Ignore parse error */ }

        // Check retry eligibility
        const isRetryable = API_CONFIG.RETRY_STATUS_CODES.includes(response.status);
        
        if (isRetryable && attempt < maxRetries) {
          const backoff = API_CONFIG.RETRY_DELAY * Math.pow(2, attempt); // Exponential backoff
          logDebug(`Retrying ${url} in ${backoff}ms...`);
          await delay(backoff);
          return executeRequest(attempt + 1);
        }

        throw new WorkflowAPIError(
          errorMessage,
          response.status,
          errorData.code || `HTTP_${response.status}`,
          isRetryable,
          errorData
        );
      }

      const result = await response.json();

      // Cache GET requests
      if (options.method === 'GET' && !config.skipCache) {
        // Clear cache after 5 minutes
        setTimeout(() => requestCache.delete(cacheKey), 300000);
      }

      return result;

    } catch (error: any) {
      clearTimeout(timeoutId);

      // Handle AbortError specifically
      if (error.name === 'AbortError' || config.signal?.aborted) {
        throw new WorkflowAPIError(
          'Request was cancelled',
          undefined,
          'REQUEST_CANCELLED',
          false
        );
      }

      // If it's already our custom error, rethrow
      if (error instanceof WorkflowAPIError) throw error;

      // Handle Network Errors (TypeError in fetch usually means network failure)
      if (error instanceof TypeError && error.message.includes('fetch')) {
         if (attempt < maxRetries) {
            const backoff = API_CONFIG.RETRY_DELAY * Math.pow(2, attempt);
            await delay(backoff);
            return executeRequest(attempt + 1);
         }
         throw new WorkflowAPIError(
            'Network error: Unable to connect to server.',
            undefined,
            'NETWORK_ERROR',
            true
         );
      }

      throw new WorkflowAPIError(
        error.message || 'An unexpected error occurred',
        undefined,
        'UNKNOWN_ERROR',
        false,
        error
      );
    }
  };

  const requestPromise = executeRequest();
  
  if (options.method === 'GET' && !config.skipCache) {
    requestCache.set(cacheKey, requestPromise);
  }

  return requestPromise;
}

// Validate workflow parameters
function validateWorkflowParams(query: string, userId: string): void {
  if (!query || query.trim().length === 0) {
    throw new WorkflowAPIError('Query cannot be empty', undefined, 'INVALID_QUERY');
  }

  if (query.trim().length > 5000) {
    throw new WorkflowAPIError('Query is too long (max 5000 characters)', undefined, 'QUERY_TOO_LONG');
  }

  if (!userId || userId.trim().length === 0) {
    throw new WorkflowAPIError('User ID is required', undefined, 'INVALID_USER_ID');
  }
}

// --- API METHODS ---

export async function startWorkflow(
  query: string,
  userId: string,
  authToken: string,
  signal?: AbortSignal
): Promise<WorkflowResponse> {
  validateWorkflowParams(query, userId);

  return apiRequest<WorkflowResponse>(
    '/api/workflow/jobs',
    {
      method: 'POST',
      body: JSON.stringify({
        query: query.trim(),
        user_id: userId,
        interactive: true,
      }),
    },
    authToken,
    { signal, skipCache: true }
  );
}

export async function checkWorkflowStatus(
  sessionId: string,
  authToken: string,
  signal?: AbortSignal
): Promise<WorkflowResponse> {
  if (!sessionId) throw new WorkflowAPIError('Session ID is required', undefined, 'INVALID_SESSION_ID');

  return apiRequest<WorkflowResponse>(
    `/api/workflow/status/${sessionId}`,
    { method: 'GET' },
    authToken,
    { signal, skipCache: true }
  );
}

export async function submitAnswers(
  sessionId: string,
  answers: Record<string, string>,
  authToken: string,
  signal?: AbortSignal
): Promise<WorkflowResponse> {
  if (!sessionId) throw new WorkflowAPIError('Session ID is required', undefined, 'INVALID_SESSION_ID');
  if (!answers || Object.keys(answers).length === 0) {
    throw new WorkflowAPIError('Answers cannot be empty', undefined, 'INVALID_ANSWERS');
  }

  return apiRequest<WorkflowResponse>(
    `/api/workflow/answers/${sessionId}`,
    {
      method: 'POST',
      body: JSON.stringify({ answers } as AnswerPayload),
    },
    authToken,
    { signal, skipCache: true }
  );
}

export async function getReport(
  sessionId: string,
  authToken: string,
  signal?: AbortSignal
): Promise<ReportResponse> {
  if (!sessionId) throw new WorkflowAPIError('Session ID is required', undefined, 'INVALID_SESSION_ID');

  return apiRequest<ReportResponse>(
    `/api/workflow/report/${sessionId}`,
    { method: 'GET' },
    authToken,
    { signal, skipCache: true }
  );
}

// --- POLLING LOGIC ---

/**
 * Enhanced iterative polling with exponential backoff and cancellation support.
 * Replaces recursion to prevent stack overflow and improve memory management.
 */
export async function pollWorkflowStatus(
  sessionId: string,
  authToken: string,
  onProgress?: (response: WorkflowResponse) => void,
  maxAttempts: number = API_CONFIG.POLLING_MAX_ATTEMPTS,
  initialDelay: number = API_CONFIG.POLLING_INITIAL_DELAY,
  signal?: AbortSignal
): Promise<WorkflowResponse> {
  if (!sessionId) throw new WorkflowAPIError('Session ID is required', undefined, 'INVALID_SESSION_ID');

  let attempts = 0;
  let currentDelay = initialDelay;

  while (attempts < maxAttempts) {
    // 1. Check Cancellation
    if (signal?.aborted) {
      throw new WorkflowAPIError('Polling was cancelled', undefined, 'POLLING_CANCELLED');
    }

    try {
      // 2. Fetch Status
      const response = await checkWorkflowStatus(sessionId, authToken, signal);
      console.log(`status check Response: ${JSON.stringify(response)}`);
      // 3. Report Progress
      if (onProgress) {
        try {
          onProgress(response);
        } catch (e) {
          logError('Progress callback failed', e);
        }
      }

      // 4. Check Success Conditions
      // We complete if status is 'completed' OR 'waiting_for_clarification' (caller handles interaction)
      if (response.status === 'completed' || response.progress >= 100) {
        logDebug(`Workflow completed after ${attempts + 1} attempts`);
        return response;
      }
      
      // If the API asks for clarification, we stop polling and return the current state
      // so the UI can present questions to the user.
      if (response.status === 'waiting_for_clarification') {
        logDebug(`Workflow paused for clarification after ${attempts + 1} attempts`);
        return response;
      }

      // 5. Check Error Conditions
      if (response.status === 'error') {
        throw new WorkflowAPIError(
          response.error || 'Workflow failed',
          undefined,
          'WORKFLOW_ERROR',
          false,
          response
        );
      }

    } catch (error: any) {
      // Propagate critical errors immediately
      if (error instanceof WorkflowAPIError) {
        if (error.code === 'POLLING_CANCELLED' || error.code === 'WORKFLOW_ERROR' || error.code === 'AUTH_REQUIRED') {
          throw error;
        }
      }
      
      logError(`Polling attempt ${attempts + 1} warning:`, error);
      // For network glitches, we continue polling up to maxAttempts
    }

    attempts++;
    
    // 6. Wait with Cancellation Support
    // This allows us to cancel *during* the sleep period
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => resolve(), currentDelay);
      
      if (signal) {
        const abortHandler = () => {
          clearTimeout(timer);
          reject(new WorkflowAPIError('Polling was cancelled', undefined, 'POLLING_CANCELLED'));
        };
        
        if (!signal.aborted) {
          signal.addEventListener('abort', abortHandler, { once: true });
        } else {
          // Signal is already aborted, handle immediately
          clearTimeout(timer);
          reject(new WorkflowAPIError('Polling was cancelled', undefined, 'POLLING_CANCELLED'));
          return;
        }
      }
    });

    // 7. Calculate Next Delay (Exponential Backoff)
    currentDelay = Math.min(
      currentDelay * API_CONFIG.POLLING_BACKOFF_MULTIPLIER, 
      API_CONFIG.POLLING_MAX_DELAY
    );
  }

  throw new WorkflowAPIError(
    'Polling timeout: Workflow did not complete in time',
    undefined,
    'POLLING_TIMEOUT',
    false,
    { attempts, maxAttempts }
  );
}

// --- DIAGNOSTICS & UTILS ---

export async function diagnoseWorkflowIssue(
  sessionId: string,
  authToken: string,
  signal?: AbortSignal
): Promise<{
  diagnosis: string;
  recommendations: string[];
  debugInfo: any;
  canRecover: boolean;
}> {
  // Try to fetch status one last time to see what the server says
  let debugInfo: any = {};
  let errorResponse: any = null;

  try {
    debugInfo = await checkWorkflowStatus(sessionId, authToken, signal);
  } catch (err) {
    errorResponse = err;
    debugInfo = { error: err instanceof Error ? err.message : String(err) };
  }
  
  let diagnosis = '';
  let recommendations: string[] = [];
  let canRecover = false;

  if (errorResponse) {
    if (debugInfo.error?.includes('404')) {
      diagnosis = 'Session Not Found';
      recommendations = ['Start a new workflow', 'Verify session ID'];
      canRecover = true;
    } else if (debugInfo.error?.includes('401')) {
      diagnosis = 'Authentication Failed';
      recommendations = ['Refresh page', 'Sign in again'];
      canRecover = true;
    } else {
      diagnosis = 'Connection Error';
      recommendations = ['Check internet', 'Retry operation'];
      canRecover = true;
    }
  } else {
    diagnosis = 'Session Exists';
    recommendations = ['The session is valid, retry polling'];
    canRecover = true;
  }

  return { diagnosis, recommendations, debugInfo, canRecover };
}

export function createDetailedErrorReport(
  error: unknown,
  context: { operation: string; sessionId?: string; }
) {
  const timestamp = new Date().toISOString();
  
  if (error instanceof WorkflowAPIError) {
    return {
      summary: `${error.code}: ${error.message}`,
      details: { ...error, context, timestamp },
      userMessage: error.code === 'POLLING_TIMEOUT' 
        ? 'The operation is taking longer than expected.' 
        : error.message,
      canRetry: error.retryable
    };
  }

  return {
    summary: 'Unexpected Error',
    details: { error, context, timestamp },
    userMessage: 'An unexpected error occurred.',
    canRetry: true
  };
}

export function clearRequestCache(): void {
  requestCache.clear();
  logDebug('Request cache cleared');
}

// --- INTERFACES & HISTORY ---

export interface ProblemValidationReport {
  id: string;
  session_id: string;
  title: string;
  executive_summary: string;
  report_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  completion_percentage: number;
  created_at: string;
  // ... (keeping simplified for brevity, add specific fields as needed)
  [key: string]: any; 
}

export interface ProblemValidationHistoryResponse {
  success: boolean;
  data: {
    reports: ProblemValidationReport[];
  };
  total?: number;
}

export async function getProblemValidationReports(
  authToken: string,
  signal?: AbortSignal
): Promise<ProblemValidationHistoryResponse> {
  return apiRequest<ProblemValidationHistoryResponse>(
    '/api/v1/problem-validation/reports',
    { method: 'GET' },
    authToken,
    { signal }
  );
}