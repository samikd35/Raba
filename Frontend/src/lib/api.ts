export const API_BASE_URL = 'http://localhost:8000/api/v1';

export class ApiError extends Error {
    constructor(public status: number, public message: string) {
        super(message);
        this.name = 'ApiError';
    }
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
            errorMessage = errorData.detail || errorData.message || errorMessage;
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
            errorMessage = errorData.detail || errorData.message || errorMessage;
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
