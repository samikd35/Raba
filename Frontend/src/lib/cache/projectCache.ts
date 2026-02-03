import { MemberProjectDetailResponse } from '@/types/organization';

const CACHE_PREFIX = 'project_detail_cache_';
const CACHE_TIMESTAMP_PREFIX = 'project_detail_cache_timestamp_';
const CACHE_DURATION = 10 * 60 * 1000; // 10 minutes

export const getCachedProjectDetail = (projectId: string): MemberProjectDetailResponse | null => {
    if (typeof window === 'undefined') return null;

    try {
        const cacheKey = `${CACHE_PREFIX}${projectId}`;
        const timestampKey = `${CACHE_TIMESTAMP_PREFIX}${projectId}`;

        const cached = localStorage.getItem(cacheKey);
        const timestamp = localStorage.getItem(timestampKey);

        if (!cached || !timestamp) return null;

        const age = Date.now() - parseInt(timestamp, 10);
        if (age > CACHE_DURATION) {
            localStorage.removeItem(cacheKey);
            localStorage.removeItem(timestampKey);
            return null;
        }

        return JSON.parse(cached);
    } catch (error) {
        console.error('Failed to read project cache:', error);
        return null;
    }
};

export const setCachedProjectDetail = (projectId: string, data: MemberProjectDetailResponse): void => {
    if (typeof window === 'undefined') return;

    try {
        const cacheKey = `${CACHE_PREFIX}${projectId}`;
        const timestampKey = `${CACHE_TIMESTAMP_PREFIX}${projectId}`;

        const serializedData = JSON.stringify(data);

        // Skip if data is ridiculously large for localStorage (e.g. > 4MB)
        // Average limit is 5MB, keeping a buffer
        if (serializedData.length > 4 * 1024 * 1024) {
            console.warn(`Project ${projectId} data is too large for cache (${(serializedData.length / 1024 / 1024).toFixed(2)}MB)`);
            return;
        }

        localStorage.setItem(cacheKey, serializedData);
        localStorage.setItem(timestampKey, Date.now().toString());

        // Cleanup old caches
        cleanupOldCaches();
    } catch (error) {
        // Handle QuotaExceededError gracefully
        const isQuotaError = error instanceof Error && (
            error.name === 'QuotaExceededError' ||
            error.name === 'NS_ERROR_DOM_QUOTA_REACHED' ||
            error.name === 'QuotaExceededError' || // Chrome/Safari/Edge 
            (error as any).code === 22 || // Legacy
            (error as any).code === 1014 // Firefox legacy
        );

        if (isQuotaError) {
            console.warn('LocalStorage quota exceeded, clearing project caches...');
            clearAllProjectCaches();
            // Try one more time after clearing (if it still fails, it's just too big)
            try {
                const cacheKey = `${CACHE_PREFIX}${projectId}`;
                const timestampKey = `${CACHE_TIMESTAMP_PREFIX}${projectId}`;
                localStorage.setItem(cacheKey, JSON.stringify(data));
                localStorage.setItem(timestampKey, Date.now().toString());
            } catch (retryError) {
                console.warn('Project data still too large even after clearing cache. Caching disabled for this project.');
            }
        } else {
            console.error('Failed to cache project data:', error);
        }
    }
};

export const clearProjectCache = (projectId: string): void => {
    if (typeof window === 'undefined') return;
    try {
        localStorage.removeItem(`${CACHE_PREFIX}${projectId}`);
        localStorage.removeItem(`${CACHE_TIMESTAMP_PREFIX}${projectId}`);
    } catch (error) {
        console.error('Failed to clear project cache:', error);
    }
};

export const clearAllProjectCaches = (): void => {
    if (typeof window === 'undefined') return;
    try {
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith(CACHE_PREFIX) || key.startsWith(CACHE_TIMESTAMP_PREFIX)) {
                localStorage.removeItem(key);
            }
        });
    } catch (error) {
        console.error('Failed to clear all project caches:', error);
    }
};

const cleanupOldCaches = (): void => {
    try {
        const now = Date.now();
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith(CACHE_TIMESTAMP_PREFIX)) {
                const timestamp = localStorage.getItem(key);
                if (timestamp) {
                    const age = now - parseInt(timestamp, 10);
                    if (age > CACHE_DURATION) {
                        const projectId = key.replace(CACHE_TIMESTAMP_PREFIX, '');
                        localStorage.removeItem(`${CACHE_PREFIX}${projectId}`);
                        localStorage.removeItem(key);
                    }
                }
            }
        });
    } catch (error) {
        // Silent fail for cleanup
    }
};
