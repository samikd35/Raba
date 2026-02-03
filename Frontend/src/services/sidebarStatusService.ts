/**
 * Sidebar Status Service
 * 
 * Fetches unified workflow completion status from the backend
 * to determine which sidebar menu items should be unlocked.
 */

import { authService } from './authService';

export interface SidebarStatus {
  has_projects: boolean;
  project_created: boolean;
  persona_created: boolean;
  customer_profile_v1_completed: boolean;
  hypothesis_completed: boolean;
  assumptions_completed: boolean;
  questionnaires_completed: boolean;
  market_research_completed: boolean;
  customer_profile_v2_completed: boolean;
  value_map_completed: boolean;
  vps_v1_completed: boolean;
  bmc_v1_completed: boolean;
  solution_critique_completed: boolean;
  vps_v2_completed: boolean;
  bmc_v2_completed: boolean;
  mvp_requirements_completed: boolean;
  max_level: number;
}

export interface SidebarStatusResponse {
  success: boolean;
  data: SidebarStatus;
}

const DEFAULT_SIDEBAR_STATUS: SidebarStatus = {
  has_projects: false,
  project_created: false,
  persona_created: false,
  customer_profile_v1_completed: false,
  hypothesis_completed: false,
  assumptions_completed: false,
  questionnaires_completed: false,
  market_research_completed: false,
  customer_profile_v2_completed: false,
  value_map_completed: false,
  vps_v1_completed: false,
  bmc_v1_completed: false,
  solution_critique_completed: false,
  vps_v2_completed: false,
  bmc_v2_completed: false,
  mvp_requirements_completed: false,
  max_level: 0,
};

class SidebarStatusService {
  private cachedStatus: SidebarStatus | null = null;
  private lastFetchTime: number = 0;
  private readonly CACHE_TTL_MS = 60000; // 1 minute client-side cache

  /**
   * Fetch sidebar unlock status from the backend.
   * Uses client-side caching to reduce API calls.
   */
  async getSidebarStatus(token?: string, forceRefresh = false): Promise<SidebarStatus> {
    // Check client-side cache first
    const now = Date.now();
    if (!forceRefresh && this.cachedStatus && (now - this.lastFetchTime) < this.CACHE_TTL_MS) {
      if (process.env.NODE_ENV === 'development') {
        console.log('[SidebarStatusService] Returning cached status');
      }
      return this.cachedStatus;
    }

    const authToken = token || authService.getCurrentToken();
    if (!authToken) {
      console.warn('[SidebarStatusService] No auth token available');
      return DEFAULT_SIDEBAR_STATUS;
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/sidebar-status`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          console.warn('[SidebarStatusService] Unauthorized - token may be expired');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: SidebarStatusResponse = await response.json();
      
      if (data.success && data.data) {
        this.cachedStatus = data.data;
        this.lastFetchTime = now;
        
        if (process.env.NODE_ENV === 'development') {
          console.log('[SidebarStatusService] Status fetched:', {
            max_level: data.data.max_level,
            has_projects: data.data.has_projects,
          });
        }
        
        return data.data;
      }

      return DEFAULT_SIDEBAR_STATUS;
    } catch (error) {
      console.error('[SidebarStatusService] Failed to fetch sidebar status:', error);
      return this.cachedStatus || DEFAULT_SIDEBAR_STATUS;
    }
  }

  /**
   * Invalidate the client-side cache.
   * Call this after project updates to ensure fresh data.
   */
  invalidateCache(): void {
    this.cachedStatus = null;
    this.lastFetchTime = 0;
    if (process.env.NODE_ENV === 'development') {
      console.log('[SidebarStatusService] Cache invalidated');
    }
  }

  /**
   * Get sidebar unlock flags for menu items.
   * Maps backend status to specific menu unlock conditions.
   */
  getUnlockFlags(status: SidebarStatus): {
    customerUnderstanding: boolean;
    marketFindingsAnalysis: boolean;
    businessModelInnovation: boolean;
    productRequirement: boolean;
    askYubaAIExpert: boolean;
  } {
    return {
      // Customer Understanding: Unlocked when project is created
      customerUnderstanding: status.project_created,
      // Market Findings Analysis: Unlocked when questionnaires completed
      marketFindingsAnalysis: status.questionnaires_completed,
      // Business Model Innovation: Unlocked when value map completed
      businessModelInnovation: status.value_map_completed,
      // Product Requirement: Unlocked when BMC v2 completed
      productRequirement: status.bmc_v2_completed,
      // Ask Yuba AI Expert: Unlocked when MVP requirements (Product Requirement) completed
      askYubaAIExpert: status.mvp_requirements_completed,
    };
  }
}

export const sidebarStatusService = new SidebarStatusService();
export default sidebarStatusService;
