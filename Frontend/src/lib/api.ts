export const API_BASE_URL = 'http://localhost:8000/api/v1';

export class ApiError extends Error {
    constructor(public status: number, public message: string) {
        super(message);
        this.name = 'ApiError';
    }
}

function extractErrorMessage(errorData: any, fallback: string): string {
    if (!errorData) return fallback;
    const candidate = errorData.detail ?? errorData.message ?? errorData.error ?? errorData;
    if (typeof candidate === 'string') return candidate;
    if (Array.isArray(candidate)) {
        const parts = candidate
            .map((item) => {
                if (typeof item === 'string') return item;
                if (item?.msg) return String(item.msg);
                if (item?.message) return String(item.message);
                return JSON.stringify(item);
            })
            .filter(Boolean);
        return parts.length ? parts.join('; ') : fallback;
    }
    if (typeof candidate === 'object') {
        if (typeof candidate.message === 'string') return candidate.message;
        try {
            return JSON.stringify(candidate);
        } catch {
            return fallback;
        }
    }
    return String(candidate);
}

async function fetchJson<T>(url: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${url}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });

    if (!response.ok) {
        let errorMessage = 'An error occurred';
        try {
            const errorData = await response.json();
            errorMessage = extractErrorMessage(errorData, errorMessage);
        } catch {
            errorMessage = `HTTP error ${response.status}`;
        }
        throw new ApiError(response.status, errorMessage);
    }

    // 204 No Content
    if (response.status === 204) {
        return {} as T;
    }

    return response.json();
}

async function postFormData<T>(url: string, formData: FormData): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${url}`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        let errorMessage = 'An error occurred';
        try {
            const errorData = await response.json();
            errorMessage = extractErrorMessage(errorData, errorMessage);
        } catch {
            errorMessage = `HTTP error ${response.status}`;
        }
        throw new ApiError(response.status, errorMessage);
    }

    return response.json();
}

export const api = {
    get: <T>(url: string) => fetchJson<T>(url),
    post: <T>(url: string, body: any) => fetchJson<T>(url, { method: 'POST', body: JSON.stringify(body) }),
    put:  <T>(url: string, body: any) => fetchJson<T>(url, { method: 'PUT', body: JSON.stringify(body) }),
    delete: <T>(url: string) => fetchJson<T>(url, { method: 'DELETE' }),
    postMultipart: <T>(url: string, formData: FormData) => postFormData<T>(url, formData),
};
