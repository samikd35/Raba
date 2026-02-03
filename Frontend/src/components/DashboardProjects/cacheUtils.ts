import { DashboardProject } from './types';

// Cache configuration
// CRITICAL: Cache keys MUST be tenant-specific to prevent cross-tenant data leakage
const CACHE_KEY_PREFIX = 'dashboard_projects_cache';
const CACHE_TIMESTAMP_PREFIX = 'dashboard_projects_cache_timestamp';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

/**
 * Get the current tenant_id from auth store or localStorage
 * This ensures cache keys are tenant-specific
 */
const getCurrentTenantId = (): string | null => {
  if (typeof window === 'undefined') return null;
  
  try {
    // Try to get from auth-storage (Zustand persisted store)
    const authStorage = localStorage.getItem('auth-storage');
    if (authStorage) {
      const parsed = JSON.parse(authStorage);
      const tenantId = parsed?.state?.user?.tenant_id;
      if (tenantId) return tenantId;
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to get tenant_id from auth storage:', error);
    }
  }
  
  return null;
};

/**
 * Build tenant-specific cache key
 */
const buildCacheKey = (prefix: string): string => {
  const tenantId = getCurrentTenantId();
  // CRITICAL: If no tenant_id, use a placeholder that will never match
  // This prevents cross-tenant cache hits
  return tenantId ? `${prefix}_${tenantId}` : `${prefix}_no_tenant`;
};

/**
 * Get cached projects data if available and not expired
 * CRITICAL: Cache is tenant-specific to prevent cross-tenant data leakage
 */
export const getCachedProjects = (): DashboardProject[] | null => {
  if (typeof window === 'undefined') return null;
  
  try {
    const cacheKey = buildCacheKey(CACHE_KEY_PREFIX);
    const timestampKey = buildCacheKey(CACHE_TIMESTAMP_PREFIX);
    
    const cached = localStorage.getItem(cacheKey);
    const timestamp = localStorage.getItem(timestampKey);
    
    if (!cached || !timestamp) return null;
    
    const age = Date.now() - parseInt(timestamp, 10);
    if (age > CACHE_DURATION) {
      // Cache expired
      localStorage.removeItem(cacheKey);
      localStorage.removeItem(timestampKey);
      return null;
    }
    
    if (process.env.NODE_ENV === 'development') {
      console.log(`📦 Using cached projects for tenant: ${getCurrentTenantId()}`);
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
 * CRITICAL: Cache is tenant-specific to prevent cross-tenant data leakage
 */
export const setCachedProjects = (data: DashboardProject[]): void => {
  if (typeof window === 'undefined') return;
  
  try {
    const cacheKey = buildCacheKey(CACHE_KEY_PREFIX);
    const timestampKey = buildCacheKey(CACHE_TIMESTAMP_PREFIX);
    
    localStorage.setItem(cacheKey, JSON.stringify(data));
    localStorage.setItem(timestampKey, Date.now().toString());
    
    if (process.env.NODE_ENV === 'development') {
      console.log(`📦 Cached dashboard projects for tenant: ${getCurrentTenantId()}`);
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to cache data:', error);
    }
  }
};

/**
 * Clear cached projects data for current tenant
 * CRITICAL: Only clears the current tenant's cache
 */
export const clearProjectsCache = (): void => {
  if (typeof window === 'undefined') return;
  
  try {
    const cacheKey = buildCacheKey(CACHE_KEY_PREFIX);
    const timestampKey = buildCacheKey(CACHE_TIMESTAMP_PREFIX);
    
    localStorage.removeItem(cacheKey);
    localStorage.removeItem(timestampKey);
    
    if (process.env.NODE_ENV === 'development') {
      console.log(`📦 Cleared dashboard projects cache for tenant: ${getCurrentTenantId()}`);
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to clear cache:', error);
    }
  }
};

/**
 * Clear ALL dashboard project caches (all tenants)
 * Use this when logging out or for complete cache reset
 */
export const clearAllProjectsCaches = (): void => {
  if (typeof window === 'undefined') return;
  
  try {
    // Find and remove all dashboard project cache keys (including legacy keys)
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith(CACHE_KEY_PREFIX) || key.startsWith(CACHE_TIMESTAMP_PREFIX))) {
        keysToRemove.push(key);
      }
    }
    
    // Also remove legacy global cache keys (from before tenant-specific fix)
    const legacyKeys = ['dashboard_projects_cache', 'dashboard_projects_cache_timestamp'];
    legacyKeys.forEach(key => {
      if (localStorage.getItem(key)) {
        keysToRemove.push(key);
      }
    });
    
    keysToRemove.forEach(key => localStorage.removeItem(key));
    
    if (process.env.NODE_ENV === 'development') {
      console.log(`📦 Cleared ALL dashboard projects caches (${keysToRemove.length} keys)`);
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to clear all caches:', error);
    }
  }
};
