import { Cohort } from './types';

// Cache configuration
const CACHE_KEY = 'cohorts_cache';
const CACHE_TIMESTAMP_KEY = 'cohorts_cache_timestamp';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

export const getCachedData = (): Cohort[] | null => {
    if (typeof window === 'undefined') return null;

    try {
        const cached = localStorage.getItem(CACHE_KEY);
        const timestamp = localStorage.getItem(CACHE_TIMESTAMP_KEY);

        if (!cached || !timestamp) return null;

        const age = Date.now() - parseInt(timestamp, 10);
        if (age > CACHE_DURATION) {
            localStorage.removeItem(CACHE_KEY);
            localStorage.removeItem(CACHE_TIMESTAMP_KEY);
            return null;
        }

        return JSON.parse(cached);
    } catch (error) {
        console.error('Failed to read cache:', error);
        return null;
    }
};

export const setCachedData = (data: Cohort[]): void => {
    if (typeof window === 'undefined') return;

    if (!data || data.length === 0) return;

    try {
        localStorage.setItem(CACHE_KEY, JSON.stringify(data));
        localStorage.setItem(CACHE_TIMESTAMP_KEY, Date.now().toString());
    } catch (error) {
        console.error('Failed to cache data:', error);
    }
};

export const clearCache = (): void => {
    if (typeof window === 'undefined') return;
    try {
        localStorage.removeItem(CACHE_KEY);
        localStorage.removeItem(CACHE_TIMESTAMP_KEY);
    } catch (error) {
        console.error('Failed to clear cache:', error);
    }
};
