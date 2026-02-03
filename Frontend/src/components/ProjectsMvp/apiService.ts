import { authService } from '@/services/authService';
import { ProjectsResponse } from './types';

/**
 * Fetch completed value maps from the API
 * @param signal - AbortController signal
 * @param skipCache - If true, bypasses backend Redis cache
 */
export async function fetchCompletedValueMaps(signal?: AbortSignal, skipCache = false): Promise<ProjectsResponse> {
  const token = authService.getCurrentToken();

  if (!token) {
    throw new Error('Authentication required. Please sign in again.');
  }

  const headers: Record<string, string> = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Add cache bypass header when refreshing
  if (skipCache) {
    headers['X-Skip-Cache'] = 'true';
  }

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/completed/value-maps`, {
    method: 'GET',
    headers,
    signal,
  });

  if (!response.ok) {
    if (response.status === 401) {
      await authService.logout();
      throw new Error('Session expired. Please sign in again.');
    }
    if (response.status === 403) {
      throw new Error('Access forbidden. Please check your permissions.');
    }
    if (response.status === 404) {
      throw new Error('No completed value maps found.');
    }
    throw new Error(`Failed to fetch projects: ${response.statusText}`);
  }

  return response.json();
}
