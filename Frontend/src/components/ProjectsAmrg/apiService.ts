import { authService } from '@/services/authService';
import { ProjectsResponse } from './types';

/**
 * Fetch projects with completed MVP Requirements (AMRG)
 */
export async function fetchCompletedAmrgProjects(signal?: AbortSignal): Promise<ProjectsResponse> {
    const token = authService.getCurrentToken();

    if (!token) {
        throw new Error('Authentication required. Please sign in again.');
    }

    // Using page=1&page_size=20&include_metadata=true as default akin to user request
    // Ideally this could be parameterized but sticking to the simple pattern for now as the component doesn't implement pagination yet
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/mav/projects/completed/mvp-requirements?page=1&page_size=20&include_metadata=true`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
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
            throw new Error('No completed projects found.');
        }
        throw new Error(`Failed to fetch projects: ${response.statusText}`);
    }

    return response.json();
}
