import { Project } from './types';

// Cache configuration
const CACHE_KEY = 'completed_value_maps_cache';
const CACHE_TIMESTAMP_KEY = 'completed_value_maps_cache_timestamp';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

/**
 * Get cached projects data if available and not expired
 */
export const getCachedData = (): Project[] | null => {
  if (typeof window === 'undefined') return null;
  
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    const timestamp = localStorage.getItem(CACHE_TIMESTAMP_KEY);
    
    if (!cached || !timestamp) return null;
    
    const age = Date.now() - parseInt(timestamp, 10);
    if (age > CACHE_DURATION) {
      // Cache expired
      localStorage.removeItem(CACHE_KEY);
      localStorage.removeItem(CACHE_TIMESTAMP_KEY);
      return null;
    }
    
    return JSON.parse(cached);
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to read cache:', error);
    }
    return null;
  }
};

/**
 * Cache projects data with timestamp
 * NOTE: Empty arrays are NOT cached to prevent empty state flash on next load
 */
export const setCachedData = (data: Project[]): void => {
  if (typeof window === 'undefined') return;
  
  // Don't cache empty arrays - they cause empty state flash on next load
  if (!data || data.length === 0) {
    if (process.env.NODE_ENV === 'development') {
      console.log('Skipping cache - no projects to cache');
    }
    return;
  }
  
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(data));
    localStorage.setItem(CACHE_TIMESTAMP_KEY, Date.now().toString());
    
    if (process.env.NODE_ENV === 'development') {
      console.log('Cached value maps data:', data.length);
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to cache data:', error);
    }
  }
};

/**
 * Clear cached projects data
 */
export const clearCache = (): void => {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.removeItem(CACHE_KEY);
    localStorage.removeItem(CACHE_TIMESTAMP_KEY);
    
    if (process.env.NODE_ENV === 'development') {
      console.log('Cleared value maps cache');
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to clear cache:', error);
    }
  }
};
