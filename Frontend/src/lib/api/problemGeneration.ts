// lib/api/problemGeneration.ts
import { authService } from '@/services/authService';

// Request management for deduplication and cancellation
const activeRequests = new Map<string, AbortController>();
const requestCache = new Map<string, { data: any; timestamp: number }>();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
const REQUEST_TIMEOUT = 120000; // 2 minutes for generation, 30s for status
const STATUS_REQUEST_TIMEOUT = 30000;

export interface ProblemGenerationParameters {
  industry: string[];
  geography: string[];
  background: string[];
  product_type: string[];
  target_customer: string[];
  impact_focus?: string[];  // Made optional to match default handling
  custom_constraints?: string;
  num_problems?: number;
  creativity_level?: number;
}

export interface ProblemGenerationJobResponse {
  job_id: string;
  status: string;
  user_id: string;
  created_at: string;
  message: string;
  problems: null;
  problems_count: number;
  processing_time_ms: null;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  user_id: string;
  created_at: string;
  message: string;
  problems: Problem[] | null;
  problems_count: number;
  processing_time_ms: number | null;
}

export interface Problem {
  id: string;
  user_id: string;
  title: string;
  description: string;
  category: string;
  severity_level: string;
  target_geography: string[];
  impact_focus: string[];
  affected_population_size: number | null;
  problem_type: string;
  time_horizon: string;
  complexity_level: string;
  root_causes: string[];
  potential_effects: string[];
  stakeholders: string[];
  success_metrics: string[];
  supporting_sources: string[];
  generation_parameters: Record<string, any>;
  generation_model: string;
  generation_timestamp: string;
  quality_score: number;
  validation_status: string;
  validation_feedback: string | null;
  view_count: number;
  like_count: number;
  bookmark_count: number;
  created_at: string;
  updated_at: string;
  session_id: string;
  session_rank: number | null;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

// API base URL - adjust this to match your backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

/**
 * Create a cache key for request deduplication
 */
function createCacheKey(endpoint: string, params?: any): string {
  return `${endpoint}:${params ? JSON.stringify(params) : ''}`;
}

/**
 * Check if cached data is still valid
 */
function isCacheValid(timestamp: number): boolean {
  return Date.now() - timestamp < CACHE_DURATION;
}

/**
 * Clean up expired cache entries
 */
function cleanupCache(): void {
  const now = Date.now();
  const entries = Array.from(requestCache.entries());
  for (const [key, { timestamp }] of entries) {
    if (now - timestamp > CACHE_DURATION) {
      requestCache.delete(key);
    }
  }
}

/**
 * Create AbortController with timeout
 */
function createAbortController(timeoutMs: number): AbortController {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort(new Error(`Request timeout after ${timeoutMs}ms`));
  }, timeoutMs);
  
  // Clear timeout if request completes normally
  controller.signal.addEventListener('abort', () => {
    clearTimeout(timeoutId);
  });
  
  return controller;
}

/**
 * Sleep utility for retry delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Calculate exponential backoff delay
 */
function calculateBackoffDelay(attempt: number, baseDelay: number = 1000): number {
  return Math.min(baseDelay * Math.pow(2, attempt) + Math.random() * 1000, 30000);
}

/**
 * Generate a short debug ID to correlate logs across calls
 */
function createDebugId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Get authentication token for API requests
 * @returns Authentication token
 * @throws Error if no token is available
 */
const getAuthToken = (): string => {
  if (typeof window === 'undefined') {
    throw new Error('Authentication required. Please log in to generate problems.');
  }
  
  const token = authService.getCurrentToken();
  if (!token) {
    throw new Error('Authentication required. Please log in to generate problems.');
  }
  return token;
};

/**
 * Validate problem generation parameters before submitting to API
 */
export function validateProblemGenerationParameters(
  parameters: ProblemGenerationParameters
): ValidationResult {
  const errors: string[] = [];

  if (process.env.NODE_ENV === 'development') {
    console.log('[pgen][validate] Raw parameters received:', parameters);
  }

  // Check required fields
  if (!parameters.industry || parameters.industry.length === 0) {
    errors.push('Please select at least one industry');
  }

  if (!parameters.geography || parameters.geography.length === 0) {
    errors.push('Please select a country');
  }

  if (!parameters.background || parameters.background.length === 0) {
    errors.push('Please select your professional background');
  }

  if (!parameters.product_type || parameters.product_type.length === 0) {
    errors.push('Please select a product type');
  }

  if (!parameters.target_customer || parameters.target_customer.length === 0) {
    errors.push('Please select your target customer');
  }

  // Optional but if provided, check minimum
  if (parameters.impact_focus && parameters.impact_focus.length === 0) {
    errors.push('If providing impact focus, select at least one');
  }

  // Check selection limits
  if (parameters.industry && parameters.industry.length > 2) {
    errors.push('Please select no more than 2 industries');
  }

  if (parameters.geography && parameters.geography.length > 1) {
    errors.push('Please select only one country');
  }

  // Additional validations for optional numeric fields
  if (parameters.num_problems !== undefined) {
    if (!Number.isInteger(parameters.num_problems) || parameters.num_problems < 1 || parameters.num_problems > 10) {
      errors.push('Number of problems must be an integer between 1 and 10');
    }
  }

  if (parameters.creativity_level !== undefined) {
    if (typeof parameters.creativity_level !== 'number' || parameters.creativity_level < 0 || parameters.creativity_level > 1) {
      errors.push('Creativity level must be a number between 0 and 1');
    }
  }

  if (process.env.NODE_ENV === 'development') {
    if (errors.length > 0) {
      console.warn('[pgen][validate] Validation failed with errors:', errors);
    } else {
      console.log('[pgen][validate] Validation passed');
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Extract error message from various error response formats
 */
function extractErrorMessage(error: unknown): string {
  if (!error) {
    return 'Unknown error occurred';
  }

  // If it's already a string
  if (typeof error === 'string') {
    return error;
  }

  // If it's an Error object
  if (error instanceof Error) {
    return error.message;
  }

  // If it's an object with a message property
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return String((error as { message: unknown }).message);
  }

  // If it's an object with a detail property
  if (typeof error === 'object' && error !== null && 'detail' in error) {
    return String((error as { detail: unknown }).detail);
  }

  // If it's an object with errors array
  if (typeof error === 'object' && error !== null && 'errors' in error && Array.isArray((error as { errors: unknown }).errors)) {
    return ((error as { errors: string[] }).errors).join(', ');
  }

  // Last resort: stringify the object
  try {
    const stringified = JSON.stringify(error);
    if (process.env.NODE_ENV === 'development') {
      console.warn('[pgen][error] Using stringified unknown error object:', stringified);
    }
    return stringified;
  } catch {
    return 'Unknown error format';
  }
}

/**
 * Generate problems by submitting parameters to the API with optimizations
 */
export async function generateProblems(
  parameters: ProblemGenerationParameters,
  signal?: AbortSignal,
  forceRefresh: boolean = false
): Promise<ProblemGenerationJobResponse> {
  // Validate parameters first
  const validation = validateProblemGenerationParameters(parameters);
  if (!validation.isValid) {
    throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
  }

  const debugId = createDebugId('pgen');

  const authToken = getAuthToken();
  const endpoint = '/api/v1/pgen/generate';
  const cacheKey = createCacheKey(endpoint, parameters);
  
  // Check cache first (for identical requests) unless forceRefresh is true
  if (!forceRefresh) {
    const cached = requestCache.get(cacheKey);
    if (cached && isCacheValid(cached.timestamp)) {
      if (process.env.NODE_ENV === 'development') {
        console.log('[pgen][generate][%s] Returning cached problem generation result', debugId, {
          cacheAgeMs: Date.now() - cached.timestamp
        });
      }
      return cached.data;
    }
  } else if (process.env.NODE_ENV === 'development') {
    console.log('[pgen][generate][%s] Bypassing cache due to forceRefresh flag', debugId);
  }

  // Check for duplicate in-flight requests
  if (activeRequests.has(cacheKey)) {
    if (process.env.NODE_ENV === 'development') {
      console.warn('[pgen][generate][%s] Duplicate request detected, aborting previous request for same cacheKey', debugId);
    }
    activeRequests.get(cacheKey)?.abort();
  }

  // Create AbortController with timeout
  const controller = signal ? new AbortController() : createAbortController(REQUEST_TIMEOUT);
  activeRequests.set(cacheKey, controller);

  // Combine external signal with internal controller
  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  const requestBody = {
    parameters: {
      industry: parameters.industry,
      geography: parameters.geography,
      background: parameters.background,
      product_type: parameters.product_type,
      target_customer: parameters.target_customer,
      impact_focus: parameters.impact_focus ?? ['social venture'],
      num_problems: parameters.num_problems ?? 3,
      creativity_level: parameters.creativity_level ?? 0.7,
      custom_constraints: parameters.custom_constraints ?? "",
    }
  };

  if (process.env.NODE_ENV === 'development') {
    console.log('[pgen][generate][%s] Problem Generation API Call', debugId, {
      url: `${API_BASE_URL}${endpoint}`,
      hasAuth: !!authToken,
      parametersCount: Object.keys(parameters).length,
      parameters,
      requestBody,
      cacheKey
    });
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    });

    if (process.env.NODE_ENV === 'development') {
      console.log('[pgen][generate][%s] Response received', debugId, {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        redirected: response.redirected,
        url: response.url
      });
    }

    if (!response.ok) {
      await handleApiError(response);
    }

    const data = await response.json();
    
    // Cache successful response (unless this was a forced refresh)
    if (!forceRefresh) {
      requestCache.set(cacheKey, {
        data,
        timestamp: Date.now()
      });
    } else if (process.env.NODE_ENV === 'development') {
      console.log('[pgen][generate][%s] Skipping cache storage due to forceRefresh', debugId);
    }
    
    // Clean up old cache entries
    cleanupCache();
    
    if (process.env.NODE_ENV === 'development') {
      console.log('[pgen][generate][%s] Problem generation successful', debugId, {
        jobId: (data as any)?.job_id,
        status: (data as any)?.status,
        problemsCount: (data as any)?.problems_count
      });
    }
    
    return data;
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[pgen][generate][%s] Error during problem generation', debugId, {
        error,
        message: error instanceof Error ? error.message : String(error)
      });
    }

    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request was cancelled or timed out');
    }
    
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Network error: Unable to connect to the server. Please check your internet connection.');
    }
    
    throw new Error(`Problem generation failed: ${extractErrorMessage(error)}`);
  } finally {
    // Clean up active request tracking
    activeRequests.delete(cacheKey);
  }
}

/**
 * Poll job status to get progress updates and final results with optimizations
 */
export async function pollJobStatus(
  jobId: string,
  signal?: AbortSignal
): Promise<JobStatusResponse> {
  const authToken = getAuthToken();
  const endpoint = `/api/v1/pgen/status/${jobId}`;
  const cacheKey = createCacheKey(endpoint);
  const debugId = createDebugId('pgen-status');
  
  // Check cache for recent status (shorter cache for status)
  const cached = requestCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < 10000) { // 10 second cache for status
    if (process.env.NODE_ENV === 'development') {
      console.log('[pgen][status][%s] Returning cached status result', debugId, {
        jobId,
        cacheAgeMs: Date.now() - cached.timestamp,
        status: (cached.data as any)?.status
      });
    }
    return cached.data;
  }

  // Create AbortController with shorter timeout for status requests
  const controller = signal ? new AbortController() : createAbortController(STATUS_REQUEST_TIMEOUT);
  
  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${authToken}`,
      },
      signal: controller.signal,
    });

    if (process.env.NODE_ENV === 'development') {
      console.log('[pgen][status][%s] Response received', debugId, {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        redirected: response.redirected,
        url: response.url
      });
    }

    if (!response.ok) {
      await handleApiError(response);
    }

    const data = await response.json();
    
    // Cache status response briefly
    requestCache.set(cacheKey, {
      data,
      timestamp: Date.now()
    });
    
    return data;
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[pgen][status][%s] Error while polling job status', debugId, {
        jobId,
        error,
        message: error instanceof Error ? error.message : String(error)
      });
    }

    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Status request was cancelled or timed out');
    }
    
    throw new Error(`Failed to poll job status: ${extractErrorMessage(error)}`);
  }
}

/**
 * Centralized API error handling
 */
async function handleApiError(response: Response): Promise<never> {
  let errorData: unknown = {};
  let errorText = '';
  
  try {
    errorText = await response.text();
    if (errorText) {
      try {
        errorData = JSON.parse(errorText);
      } catch {
        errorData = { message: errorText };
      }
    }
  } catch {
    errorData = { message: 'Failed to read error response' };
  }

  if (process.env.NODE_ENV === 'development') {
    console.error('[pgen][api-error] 🚨 API Error', {
      status: response.status,
      statusText: response.statusText,
      url: response.url,
      errorData,
      timestamp: new Date().toISOString()
    });
  }

  let errorMessage: string;
  
  switch (response.status) {
    case 401:
      errorMessage = 'Authentication failed. Please log in again.';
      break;
    case 402:
      errorMessage = 'INSUFFICIENT_CREDITS_ERROR';
      break;
    case 403:
      errorMessage = 'Access forbidden. You may not have permission to perform this action.';
      break;
    case 404:
      errorMessage = 'Resource not found. It may have expired or been deleted.';
      break;
    case 429:
      errorMessage = 'Too many requests. Please wait a moment before trying again.';
      break;
    case 400:
      const extractedMessage = extractErrorMessage(errorData);
      errorMessage = extractedMessage && extractedMessage !== '{}'
        ? `Invalid request: ${extractedMessage}`
        : 'Invalid request parameters.';
      break;
    case 500:
      errorMessage = 'Server error occurred. Please try again in a few moments.';
      break;
    default:
      if (response.status >= 500) {
        errorMessage = 'Server error. Please try again later.';
      } else {
        const extracted = extractErrorMessage(errorData);
        errorMessage = extracted && extracted !== '{}' && extracted !== 'Unknown error format'
          ? extracted
          : `Request failed (HTTP ${response.status})`;
      }
  }

  throw new Error(errorMessage);
}

/**
 * Poll job status with automatic retries, exponential backoff, and progress callbacks
 */
export async function pollJobStatusWithRetries(
  jobId: string,
  maxRetries: number = 60,
  baseIntervalMs: number = 5000, // Start with 5 seconds
  onProgress?: (progress: number, status: string, message: string) => void,
  signal?: AbortSignal
): Promise<JobStatusResponse> {
  let consecutiveErrors = 0;
  const maxConsecutiveErrors = 3;
  const debugId = createDebugId('pgen-poll');
  
  for (let retry = 0; retry < maxRetries; retry++) {
    // Check if cancelled
    if (signal?.aborted) {
      if (process.env.NODE_ENV === 'development') {
        console.warn('[pgen][poll][%s] Polling aborted by external signal', debugId, {
          jobId,
          retry
        });
      }
      throw new Error('Polling was cancelled');
    }
    
    try {
      const statusResponse = await pollJobStatus(jobId, signal);
      
      // Reset error counter on successful request
      consecutiveErrors = 0;
      
      // Calculate progress based on status and retry count
      let progress = 0;
      switch (statusResponse.status) {
        case 'pending':
          progress = Math.min(10 + (retry * 2), 25); // 10-25%
          break;
        case 'processing':
          progress = Math.min(30 + (retry * 3), 90); // 30-90%
          break;
        case 'completed':
          progress = 100;
          break;
        case 'failed':
          progress = 0;
          break;
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[pgen][poll][%s] Poll iteration result', debugId, {
          jobId,
          retry,
          status: statusResponse.status,
          message: statusResponse.message,
          progress
        });
      }

      // Call progress callback if provided
      if (onProgress) {
        onProgress(progress, statusResponse.status, statusResponse.message);
      }
      
      // If job is completed or failed, return the result
      if (statusResponse.status === 'completed' || statusResponse.status === 'failed') {
        if (process.env.NODE_ENV === 'development') {
          console.log('[pgen][poll][%s] Job finished', debugId, {
            jobId,
            finalStatus: statusResponse.status,
            problemsCount: statusResponse.problems_count
          });
        }
        return statusResponse;
      }
      
      // Calculate next interval with exponential backoff (max 30 seconds)
      const nextInterval = Math.min(
        baseIntervalMs * Math.pow(1.5, Math.floor(retry / 3)),
        30000
      );
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[pgen][poll][%s] Next poll scheduled', debugId, {
          jobId,
          attempt: retry + 1,
          maxRetries,
          nextIntervalMs: nextInterval
        });
      }
      
      // Wait before next poll
      await sleep(nextInterval);
      
    } catch (error) {
      consecutiveErrors++;
      
      if (process.env.NODE_ENV === 'development') {
        console.error('[pgen][poll][%s] Polling error', debugId, {
          jobId,
          attempt: retry + 1,
          consecutiveErrors,
          maxConsecutiveErrors,
          error,
          message: error instanceof Error ? error.message : String(error)
        });
      }
      
      // If too many consecutive errors, fail fast
      if (consecutiveErrors >= maxConsecutiveErrors) {
        throw new Error(`Job polling failed after ${consecutiveErrors} consecutive errors: ${extractErrorMessage(error)}`);
      }
      
      // If this is the last retry, throw the error
      if (retry === maxRetries - 1) {
        throw new Error(`Job polling failed after ${maxRetries} retries: ${extractErrorMessage(error)}`);
      }
      
      // Wait before retry with exponential backoff
      const retryDelay = calculateBackoffDelay(consecutiveErrors - 1, 2000);
      if (process.env.NODE_ENV === 'development') {
        console.log('[pgen][poll][%s] Waiting before retry', debugId, {
          jobId,
          retry,
          retryDelayMs: retryDelay
        });
      }
      await sleep(retryDelay);
    }
  }
  
  throw new Error('Job polling timeout - maximum retries exceeded');
}

/**
 * Complete problem generation workflow with optimizations
 */
export async function generateProblemsComplete(
  parameters: ProblemGenerationParameters,
  onProgress?: (progress: number, status: string, message: string) => void,
  signal?: AbortSignal,
  forceRefresh: boolean = false
): Promise<JobStatusResponse> {
  // Initial progress
  if (onProgress) {
    onProgress(0, 'initializing', 'Validating parameters...');
  }
  
  // Submit job with cancellation support
  if (onProgress) {
    onProgress(5, 'submitting', 'Submitting problem generation request...');
  }
  
  const jobResponse = await generateProblems(parameters, signal, forceRefresh);
  
  if (onProgress) {
    onProgress(10, 'polling', 'Starting to monitor job progress...');
  }
  
  // Start polling for results with optimized settings
  return pollJobStatusWithRetries(
    jobResponse.job_id,
    60, // max retries (5 minutes with exponential backoff)
    5000, // start with 5 seconds
    onProgress,
    signal
  );
}

/**
 * Cancel all active requests (useful for cleanup)
 */
export function cancelAllRequests(): void {
  const entries = Array.from(activeRequests.entries());
  for (const [key, controller] of entries) {
    controller.abort();
    activeRequests.delete(key);
  }
  
  if (process.env.NODE_ENV === 'development') {
    console.log('🛑 Cancelled all active requests');
  }
}

/**
 * Clear request cache (useful for testing or forced refresh)
 */
export function clearRequestCache(): void {
  requestCache.clear();
  
  if (process.env.NODE_ENV === 'development') {
    console.log('🗑️ Cleared request cache');
  }
}

/**
 * Get cache statistics (useful for debugging)
 */
export function getCacheStats(): { size: number; activeRequests: number } {
  cleanupCache();
  return {
    size: requestCache.size,
    activeRequests: activeRequests.size
  };
}

/**
 * Utility function to log problem generation parameters (for debugging)
 */
export function debugProblemGenerationParameters(
  parameters: ProblemGenerationParameters
): void {
  if (process.env.NODE_ENV === 'development') {
    console.log('Problem Generation Parameters:', {
      industry: parameters.industry,
      geography: parameters.geography,
      background: parameters.background,
      product_type: parameters.product_type,
      target_customer: parameters.target_customer,
      impact_focus: parameters.impact_focus,
      custom_constraints: parameters.custom_constraints,
      num_problems: parameters.num_problems,
      creativity_level: parameters.creativity_level,
    });
  }
}