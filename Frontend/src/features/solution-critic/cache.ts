import { SolutionCritiqueData } from './types';

// ============================================
// Cache Configuration
// ============================================

const CACHE_KEY_PREFIX = 'solution_critic_';
const CACHE_TIMESTAMP_KEY_PREFIX = 'solution_critic_timestamp_';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

/**
 * Get cached solution critic data for a project
 */
export const getCachedData = (projectId: string): SolutionCritiqueData | null => {
  if (typeof window === 'undefined') return null;
  
  try {
    const cacheKey = `${CACHE_KEY_PREFIX}${projectId}`;
    const timestampKey = `${CACHE_TIMESTAMP_KEY_PREFIX}${projectId}`;
    
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
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to read cache:', error);
    }
    return null;
  }
};

/**
 * Set cached solution critic data for a project
 */
export const setCachedData = (projectId: string, data: SolutionCritiqueData): void => {
  if (typeof window === 'undefined') return;
  
  try {
    const cacheKey = `${CACHE_KEY_PREFIX}${projectId}`;
    const timestampKey = `${CACHE_TIMESTAMP_KEY_PREFIX}${projectId}`;
    
    localStorage.setItem(cacheKey, JSON.stringify(data));
    localStorage.setItem(timestampKey, Date.now().toString());
    
    if (process.env.NODE_ENV === 'development') {
      console.log('Cached solution critique data for project:', projectId);
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to cache data:', error);
    }
  }
};

/**
 * Clear cached solution critic data for a project
 */
export const clearCache = (projectId: string): void => {
  if (typeof window === 'undefined') return;
  
  try {
    const cacheKey = `${CACHE_KEY_PREFIX}${projectId}`;
    const timestampKey = `${CACHE_TIMESTAMP_KEY_PREFIX}${projectId}`;
    
    localStorage.removeItem(cacheKey);
    localStorage.removeItem(timestampKey);
    
    if (process.env.NODE_ENV === 'development') {
      console.log('Cleared solution critique cache for project:', projectId);
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to clear cache:', error);
    }
  }
};
