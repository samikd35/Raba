"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { toast } from "react-hot-toast";
import { useAuthStore } from "@/stores/authStore";
import { SolutionCritiqueData, SolutionCriticResponse } from '../types';
import { getCachedData, setCachedData, clearCache } from '../cache';

// --- Helpers ---

const debugLog = (message: string, ...args: any[]) => {
  if (process.env.NODE_ENV === 'development') {
    console.log(`[SolutionCritic] ${message}`, ...args);
  }
};

interface UseSolutionCriticReturn {
  data: SolutionCritiqueData | null;
  loading: boolean;
  error: string | null;
  isGoingBack: boolean;
  isRefreshing: boolean;
  isGenerating: boolean;
  isContinueLoading: boolean;
  generationProgress: string | null;
  fetchSolutionCriticData: (forceRefresh?: boolean) => Promise<void>;
  handleGoBack: () => Promise<void>;
  handleRefresh: () => Promise<void>;
  generateSolutionCritique: () => Promise<void>;
  stopPolling: (resetState?: boolean) => void;
  handleContinue: () => void;
}

export const useSolutionCritic = (projectId: string): UseSolutionCriticReturn => {
  const router = useRouter();
  const pathname = usePathname();
  const basePath = pathname?.startsWith('/workspace') ? '/workspace' : '/team-workspace';
  const { isAuthenticated, token } = useAuthStore();
  const API_URL = process.env.NEXT_PUBLIC_API_URL;

  // --- State ---

  const [data, setData] = useState<SolutionCritiqueData | null>(() => {
    const cached = getCachedData(projectId);
    if (cached) debugLog('Loaded initial data from cache', projectId);
    return cached;
  });

  const [loading, setLoading] = useState(() => !getCachedData(projectId));
  const [error, setError] = useState<string | null>(null);

  // Action States
  const [isGoingBack, setIsGoingBack] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isContinueLoading, setIsContinueLoading] = useState<boolean>(false);
  const isGeneratingRef = useRef(false); // Ref to track generation state for async callbacks
  const [generationProgress, setGenerationProgress] = useState<string | null>(null);

  // --- Refs ---

  const isMountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);

  // --- Utils ---

  const cleanupAbortController = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const safeSetState = <T>(setter: React.Dispatch<React.SetStateAction<T>>, value: T) => {
    if (isMountedRef.current) setter(value);
  };

  // --- Data Fetching ---

  const fetchSolutionCriticData = useCallback(async (forceRefresh: boolean = false) => {
    if (!isAuthenticated || !projectId) {
      safeSetState(setError, !isAuthenticated ? 'Authentication required' : 'Invalid project ID');
      safeSetState(setLoading, false);
      return;
    }

    // 1. Check Cache
    if (!forceRefresh) {
      const cached = getCachedData(projectId);
      if (cached) {
        debugLog('Using cached data');
        safeSetState(setData, cached);
        safeSetState(setLoading, false);
        safeSetState(setError, null);
        return;
      }
    } else {
      clearCache(projectId);
    }

    // 2. Setup Request
    cleanupAbortController();
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    safeSetState(setLoading, true);
    safeSetState(setError, null);

    try {
      debugLog('Fetching from API');
      const response = await fetch(
        `${API_URL}/api/v2/mvp/projects/${projectId}/solution-critique/results`,
        {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          signal,
        }
      );

      // 3. Handle 404 - Set error state, don't auto-generate to avoid infinite loops
      if (response.status === 404) {
        debugLog('404 detected - no solution critique exists');
        safeSetState(setLoading, false);
        safeSetState<string | null>(setError, 'NO_DATA'); // Special error code for empty state
        return;
      }

      if (response.status === 401) throw new Error('Authentication required. Please sign in again.');
      if (!response.ok) throw new Error(`Failed to fetch results: ${response.statusText}`);

      const result: SolutionCriticResponse = await response.json();

      if (result.success && result.data) {
        safeSetState(setData, result.data);
        setCachedData(projectId, result.data);
        debugLog('Data fetched and cached');
      }
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      
      const msg = err.message || 'Failed to load data';
      debugLog('Fetch error', msg);
      safeSetState(setError, msg);
      toast.error(msg);
    } finally {
      safeSetState(setLoading, false);
    }
  }, [isAuthenticated, projectId, token, API_URL]);

  // --- Generation & Polling ---

  const stopPolling = useCallback((resetState: boolean = false) => {
    if (pollingTimerRef.current) {
      clearTimeout(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
    // Note: We don't abort generation requests here to allow backend to finish
    // even if UI stops polling, unless strictly necessary.
    
    if (resetState) {
      isGeneratingRef.current = false;
      safeSetState(setIsGenerating, false);
      safeSetState(setGenerationProgress, null);
    }
  }, []);

  const checkStatus = async () => {
    if (!isMountedRef.current || !token) return 'stopped';

    try {
      const response = await fetch(
        `${API_URL}/api/v2/mvp/projects/${projectId}/solution-critique/status`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      if (!response.ok) return 'error';

      const result = await response.json();
      
      if (result.success && result.status === 'completed') return 'completed';
      if (result.status === 'failed' || result.error) throw new Error(result.error || 'Generation failed');
      
      if (result.progress) safeSetState(setGenerationProgress, result.progress);
      
      return 'pending';
    } catch (err) {
      throw err;
    }
  };

  const pollForCompletion = useCallback(async () => {
    const startTime = Date.now();
    const MAX_TIME = 180000; // 3 mins

    const runPoll = async () => {
      if (!isMountedRef.current) return;

      if (Date.now() - startTime > MAX_TIME) {
        stopPolling(true);
        safeSetState(setError, 'Generation timed out');
        toast.error('Generation timeout');
        return;
      }

      try {
        const status = await checkStatus();

        if (status === 'completed') {
          debugLog('Generation completed');
          safeSetState(setGenerationProgress, 'Fetching results...');
          toast.success('Solution critique generated!');
          
          // Stop polling and reset state FIRST to prevent re-triggering
          stopPolling(true);
          
          // Clear cache and fetch fresh
          clearCache(projectId);
          await fetchSolutionCriticData(true);
        } else if (status === 'pending') {
          // Schedule next poll safely
          pollingTimerRef.current = setTimeout(runPoll, 3000);
        } else {
          // Stopped or unknown state
          stopPolling();
        }
      } catch (err: any) {
        stopPolling(true);
        const msg = err.message || 'Generation failed';
        safeSetState(setError, msg);
        toast.error(msg);
      }
    };

    runPoll();
  }, [fetchSolutionCriticData, projectId, stopPolling, API_URL, token]);

  const generateSolutionCritique = useCallback(async () => {
    if (!isAuthenticated || !token) {
      toast.error('Authentication required');
      return;
    }
    
    // Use ref to prevent race conditions with async state updates
    if (isGeneratingRef.current) {
      debugLog('Generation already in progress, skipping');
      return;
    }

    // Reset previous states
    stopPolling(false); 
    cleanupAbortController(); // Abort any pending fetches
    abortControllerRef.current = new AbortController();

    try {
      isGeneratingRef.current = true;
      safeSetState(setIsGenerating, true);
      safeSetState(setGenerationProgress, 'Starting generation...');
      safeSetState(setError, null);

      debugLog('Triggering generation');

      const response = await fetch(
        `${API_URL}/api/v2/mvp/projects/${projectId}/solution-critique/generate`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ force_regenerate: true }),
          signal: abortControllerRef.current.signal,
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Generation failed: ${response.statusText}`);
      }

      const result = await response.json();
      if (!result.success) throw new Error(result.message || 'Failed to start generation');

      toast.success('Solution critique generation started');
      safeSetState(setGenerationProgress, 'Analyzing your solution...');

      // Start the recursive polling
      pollForCompletion();

    } catch (err: any) {
      if (err.name === 'AbortError') {
        isGeneratingRef.current = false;
        return;
      }
      
      const msg = err.message || 'Failed to generate critique';
      stopPolling(true);
      isGeneratingRef.current = false;
      safeSetState(setError, msg);
      toast.error(msg);
    }
  }, [isAuthenticated, token, projectId, isGenerating, stopPolling, pollForCompletion, API_URL]);

  // Fix circular dependency manually by assigning the function to the ref-based flow if needed,
  // but simpler here: fetchSolutionCriticData calls generateSolutionCritique.
  // To avoid `generateSolutionCritique` changing and triggering `fetchSolutionCriticData` re-creation:
  // We rely on stable deps (token, projectId) and `useCallback`.

  // --- Navigation & UI Handlers ---

  const handleGoBack = useCallback(async () => {
    safeSetState(setIsGoingBack, true);
    // Artificial delay for UX smoothness
    await new Promise(resolve => setTimeout(resolve, 400));
    if (isMountedRef.current) {
      router.push(`${basePath}/bmc/${projectId}`);
      setIsGoingBack(false);
    }
  }, [router, basePath, projectId]);

  const handleRefresh = useCallback(async () => {
    safeSetState(setIsRefreshing, true);
    await fetchSolutionCriticData(true);
    safeSetState(setIsRefreshing, false);
  }, [fetchSolutionCriticData]);

  const handleContinue = useCallback(async () => {
    safeSetState(setIsContinueLoading, true);
    router.push(`${basePath}/vps-v2/${projectId}`);
  }, [router, basePath, projectId]);

  // --- Lifecycle ---

  useEffect(() => {
    isMountedRef.current = true;
    fetchSolutionCriticData();

    return () => {
      isMountedRef.current = false;
      cleanupAbortController();
      if (pollingTimerRef.current) {
        clearTimeout(pollingTimerRef.current);
      }
    };
  }, [fetchSolutionCriticData]);

  return {
    data,
    loading,
    error,
    isGoingBack,
    isRefreshing,
    isGenerating,
    isContinueLoading,
    generationProgress,
    fetchSolutionCriticData,
    handleGoBack,
    handleRefresh,
    generateSolutionCritique,
    stopPolling,
    handleContinue,
  };
};

export default useSolutionCritic;