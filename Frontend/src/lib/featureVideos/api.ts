/**
 * Feature Videos API Client
 * Handles GET/POST for seen feature videos
 */

import { authService } from '@/services/authService';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export type SeenSource = 'autoplay' | 'icon_click';

export interface SeenFeaturesResponse {
  seen: string[];
}

export interface MarkSeenRequest {
  featureId: string;
  source: SeenSource;
}

/**
 * Get all seen feature video IDs for the current user
 * Should be called once on app load
 */
export async function getSeenFeatureVideos(): Promise<string[]> {
  const token = authService.getCurrentToken();
  
  if (!token) {
    if (process.env.NODE_ENV === 'development') {
      console.log('[FeatureVideos] No auth token available, returning empty seen list');
    }
    return [];
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/feature-videos/seen`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        if (process.env.NODE_ENV === 'development') {
          console.warn('[FeatureVideos] Unauthorized - token may be expired');
        }
        return [];
      }
      throw new Error(`Failed to fetch seen features: ${response.status}`);
    }

    const data: SeenFeaturesResponse = await response.json();
    return data.seen || [];
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[FeatureVideos] Error fetching seen features:', error);
    }
    return [];
  }
}

/**
 * Mark a feature as seen (fire-and-forget)
 * Should be called when video starts playing for first time
 */
export async function postSeenFeatureVideo(
  featureId: string,
  source: SeenSource
): Promise<void> {
  const token = authService.getCurrentToken();
  
  if (!token) {
    if (process.env.NODE_ENV === 'development') {
      console.log('[FeatureVideos] No auth token available, skipping mark seen');
    }
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/feature-videos/seen`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        featureId,
        source,
      }),
    });

    if (!response.ok && process.env.NODE_ENV === 'development') {
      console.warn(`[FeatureVideos] Failed to mark feature as seen: ${response.status}`);
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[FeatureVideos] Error marking feature as seen:', error);
    }
  }
}
