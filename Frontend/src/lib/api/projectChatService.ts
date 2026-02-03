import { authService } from '../../services/authService';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

// Custom error class for project chat API errors
export class ProjectChatAPIError extends Error {
    status: number;
    constructor(message: string, status: number = 500) {
        super(message);
        this.name = 'ProjectChatAPIError';
        this.status = status;
    }
}

const getAuthHeaders = (): HeadersInit => {
    const token = authService.getCurrentToken();
    if (!token) {
        throw new ProjectChatAPIError('No authentication token available', 401);
    }
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
    };
};

const handleApiError = async (response: Response): Promise<void> => {
    if (!response.ok) {
        let errorMessage = `API Error: ${response.status} ${response.statusText}`;
        try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
            // If JSON parsing fails, use default error message
        }
        throw new ProjectChatAPIError(errorMessage, response.status);
    }
};

// Helper to generate default thread title
export const generateDefaultThreadTitle = (): string => {
    return `Chat ${new Date().toLocaleString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        hour: 'numeric', 
        minute: '2-digit' 
    })}`; 
};

export const projectChatService = {
    createThread: async (organizationId: string, projectId: string, title?: string) => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/api/organization/${organizationId}/member-projects/${projectId}/chat/threads`,
                {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({
                        title: title || `New Thread ${new Date().toLocaleTimeString()}`,
                        metadata: {},
                    }),
                }
            );
            await handleApiError(response);
            return await response.json();
        } catch (error) {
            console.error('Failed to create thread:', error);
            throw error;
        }
    },

    getThreads: async (
        organizationId: string,
        projectId: string,
        params?: { limit?: number; offset?: number }
    ) => {
        try {
            const queryParams = new URLSearchParams();
            if (params?.limit) queryParams.append('limit', params.limit.toString());
            if (params?.offset) queryParams.append('offset', params.offset.toString());

            const response = await fetch(
                `${API_BASE_URL}/api/organization/${organizationId}/member-projects/${projectId}/chat/threads?${queryParams.toString()}`,
                {
                    method: 'GET',
                    headers: getAuthHeaders(),
                }
            );
            await handleApiError(response);
            return await response.json();
        } catch (error) {
            console.error('Failed to get threads:', error);
            throw error;
        }
    },

    getThreadDetails: async (organizationId: string, threadId: string) => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/api/organization/${organizationId}/chat/threads/${threadId}`,
                {
                    method: 'GET',
                    headers: getAuthHeaders(),
                }
            );
            await handleApiError(response);
            return await response.json();
        } catch (error) {
            console.error('Failed to get thread details:', error);
            throw error;
        }
    },

    postMessage: async (organizationId: string, threadId: string, content: string) => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/api/organization/${organizationId}/chat/threads/${threadId}/messages`,
                {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ content }),
                }
            );
            await handleApiError(response);
            return await response.json();
        } catch (error) {
            console.error('Failed to post message:', error);
            throw error;
        }
    },

    getMessages: async (
        organizationId: string,
        threadId: string,
        params?: { limit?: number; cursor?: string; order?: 'asc' | 'desc' }
    ) => {
        try {
            const queryParams = new URLSearchParams();
            if (params?.limit) queryParams.append('limit', params.limit.toString());
            if (params?.cursor) queryParams.append('cursor', params.cursor);
            if (params?.order) queryParams.append('order', params.order);

            const response = await fetch(
                `${API_BASE_URL}/api/organization/${organizationId}/chat/threads/${threadId}/messages?${queryParams.toString()}`,
                {
                    method: 'GET',
                    headers: getAuthHeaders(),
                }
            );
            await handleApiError(response);
            return await response.json();
        } catch (error) {
            console.error('Failed to get messages:', error);
            throw error;
        }
    },
};

// Named exports for direct imports
export const createThread = projectChatService.createThread;
export const listThreads = projectChatService.getThreads;
export const postMessage = projectChatService.postMessage;
export const getMessages = projectChatService.getMessages;
