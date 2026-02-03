import { Cohort } from './types';
import { CohortProjectsResponse } from '@/types/organization';

export async function fetchCohorts(tenantId: string, token: string, signal?: AbortSignal): Promise<Cohort[]> {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, '') || '';
    const url = `${baseUrl}/api/cohorts/${tenantId}?include_inactive=false`;

    console.log(`[fetchCohorts] Fetching from: ${url}`);
    const start = Date.now();

    // Create a timeout signal (15 seconds)
    const timeoutController = new AbortController();
    const timeoutId = setTimeout(() => timeoutController.abort(), 15000);

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            // Combine the provided signal with our timeout signal
            signal: signal ? AbortSignal.any([signal, timeoutController.signal]) : timeoutController.signal,
        });

        clearTimeout(timeoutId);
        const duration = Date.now() - start;
        console.log(`[fetchCohorts] Response received in ${duration}ms, status: ${response.status}`);

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Session expired. Please sign in again.');
            }
            if (response.status === 403) {
                throw new Error('Access forbidden. Please check your permissions.');
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `Failed to fetch cohorts: ${response.statusText}`);
        }

        const data = await response.json();

        let cohortsList: Cohort[] = [];
        if (Array.isArray(data)) {
            cohortsList = data;
        } else if (data && typeof data === 'object' && Array.isArray(data.cohorts)) {
            cohortsList = data.cohorts;
        } else if (data && typeof data === 'object' && Array.isArray(data.data)) {
            cohortsList = data.data;
        }

        console.log(`[fetchCohorts] Successfully parsed ${cohortsList.length} cohorts`);
        return cohortsList;
    } catch (error: any) {
        if (error.name === 'AbortError') {
            console.log('[fetchCohorts] Request aborted');
        } else {
            console.error('[fetchCohorts] Error:', error);
        }
        throw error;
    }
}

/**
 * Fetch projects for a specific cohort
 * GET /api/cohorts/{tenant_id}/{cohort_id}/projects
 * 
 * @param tenantId - Organization tenant ID
 * @param cohortId - Cohort ID
 * @param token - Authentication token
 * @param params - Optional query parameters for pagination
 * @param signal - Optional abort signal
 * @returns CohortProjectsResponse with paginated project list
 */
export async function fetchCohortProjects(
    tenantId: string,
    cohortId: string,
    token: string,
    params?: {
        page?: number;
        page_size?: number;
    },
    signal?: AbortSignal
): Promise<CohortProjectsResponse> {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, '') || '';

    const queryParams = new URLSearchParams();
    queryParams.append('page', (params?.page || 1).toString());
    queryParams.append('page_size', (params?.page_size || 20).toString());

    const url = `${baseUrl}/api/cohorts/${tenantId}/${cohortId}/projects?${queryParams.toString()}`;

    console.log(`[fetchCohortProjects] Fetching from: ${url}`);
    const start = Date.now();

    // Create a timeout signal (20 seconds)
    const timeoutController = new AbortController();
    const timeoutId = setTimeout(() => timeoutController.abort(), 20000);

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            signal: signal ? AbortSignal.any([signal, timeoutController.signal]) : timeoutController.signal,
        });

        clearTimeout(timeoutId);
        const duration = Date.now() - start;
        console.log(`[fetchCohortProjects] Response received in ${duration}ms, status: ${response.status}`);

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Session expired. Please sign in again.');
            }
            if (response.status === 403) {
                throw new Error('Access forbidden. Please check your permissions.');
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || errorData.detail || `Failed to fetch cohort projects: ${response.statusText}`);
        }

        const data: CohortProjectsResponse = await response.json();

        console.log(`[fetchCohortProjects] Successfully fetched ${data.projects?.length || 0} projects for cohort ${data.cohort_name}`);
        return data;
    } catch (error: any) {
        if (error.name === 'AbortError') {
            console.log('[fetchCohortProjects] Request aborted');
        } else {
            console.error('[fetchCohortProjects] Error:', error);
        }
        throw error;
    }
}
