"use client";

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { useNavigationLoading } from '@/context/NavigationLoadingContext';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  History, 
  FileText, 
  Calendar, 
  Eye, 
  Loader2, 
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Clock,
  TrendingUp,
  Lightbulb
} from "lucide-react";

interface RefinementHistoryItem {
  id: string;
  tenant_id: string;
  user_id: string;
  session_title: string;
  original_idea: string;
  status: string;
  researched: boolean;
  research_notes: any;
  processing_time_seconds: number;
  metadata: {
    idea_length: number;
    average_score: number;
    problems_generated: number;
  };
  created_at: string;
  updated_at: string;
  completed_at: string;
}

interface RefinementHistoryResponse {
  success: boolean;
  history: RefinementHistoryItem[];
  total_count: number;
  user_id: string;
  pagination: {
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

interface RefinementHistoryDrawerProps {
  trigger?: React.ReactNode;
  workspacePath?: string;
}

export default function RefinementHistoryDrawer({ 
  trigger,
  workspacePath
}: RefinementHistoryDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [notifying, setNotifying] = useState(false);
  const [history, setHistory] = useState<RefinementHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clickingItemId, setClickingItemId] = useState<string | null>(null);
  const [navigating, setNavigating] = useState(false);
  
  // Use Zustand store instead of old useAuth hook
  const { user, token, isAuthenticated } = useAuthStore();
  const router = useRouter();
  const { startLoading } = useNavigationLoading();
  
  // Refs for cleanup and state tracking
  const abortControllerRef = useRef<AbortController | null>(null);
  const hasFetchedRef = useRef(false);
  const isMountedRef = useRef(true);

  // Constants for maintainability
  const constants = useMemo(() => ({
    CACHE_DURATION: 5 * 60 * 1000, // 5 minutes
    API_TIMEOUT: 10000, // 10 seconds
    STORAGE_KEYS: {
      HISTORY: (userId: string) => `refinementHistory_${userId}`,
      TIMESTAMP: (userId: string) => `refinementHistoryTimestamp_${userId}`,
      RESULTS: 'ideaRefinementResults',
      ORIGINAL_IDEA: 'originalIdea'
    }
  }), []);

  // Get the correct user ID - User interface only has 'id' property
  const userId = useMemo(() => {
    return user?.id || '';
  }, [user?.id]);

  // Get auth token safely using Zustand store
  const getAuthToken = useCallback(() => {
    return token || null;
  }, [token]);

  // Debug user changes - only in development
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log("🔍 RefinementHistoryDrawer - User state:", { 
        user, 
        isAuthenticated,
        hasUserId: !!userId 
      });
    }
  }, [user, isAuthenticated, userId]);

  // Reset fetch flag when user changes
  useEffect(() => {
    hasFetchedRef.current = false;
  }, [userId]);

  // Cache utilities
  const getCachedHistory = useCallback((): RefinementHistoryItem[] | null => {
    if (typeof window === 'undefined' || !userId) return null;
    
    try {
      const cached = localStorage.getItem(constants.STORAGE_KEYS.HISTORY(userId));
      const timestamp = localStorage.getItem(constants.STORAGE_KEYS.TIMESTAMP(userId));
      
      if (!cached || !timestamp) return null;
      
      // Check if cache is fresh (5 minutes)
      const isCacheFresh = Date.now() - parseInt(timestamp) < constants.CACHE_DURATION;
      if (!isCacheFresh) {
        localStorage.removeItem(constants.STORAGE_KEYS.HISTORY(userId));
        localStorage.removeItem(constants.STORAGE_KEYS.TIMESTAMP(userId));
        return null;
      }
      
      return JSON.parse(cached);
    } catch {
      // Clear corrupted cache
      localStorage.removeItem(constants.STORAGE_KEYS.HISTORY(userId));
      localStorage.removeItem(constants.STORAGE_KEYS.TIMESTAMP(userId));
      return null;
    }
  }, [userId, constants]);

  const setCachedHistory = useCallback((history: RefinementHistoryItem[]) => {
    if (typeof window === 'undefined' || !userId) return;
    
    try {
      localStorage.setItem(constants.STORAGE_KEYS.HISTORY(userId), JSON.stringify(history));
      localStorage.setItem(constants.STORAGE_KEYS.TIMESTAMP(userId), Date.now().toString());
    } catch (error) {
      console.error('Failed to cache history:', error);
    }
  }, [userId, constants]);

  // Optimized fetchHistory with proper error handling and race condition prevention
  const fetchHistory = useCallback(async (forceRefresh = false) => {
    // Prevent multiple calls and check mount status
    if (hasFetchedRef.current && !forceRefresh || loading || !isMountedRef.current) {
      console.log("⏩ Skipping fetch - already fetched, loading, or unmounted");
      return;
    }

    // Check if we have required data
    const token = getAuthToken();
    if (!token || !userId) {
      console.log("❌ Missing auth data:", { token: !!token, userId: !!userId });
      if (isMountedRef.current) {
        setError(!token ? "Authentication required" : "User not available");
        setLoading(false);
      }
      return;
    }

    // Try to use cache first unless forcing refresh
    if (!forceRefresh) {
      const cachedHistory = getCachedHistory();
      if (cachedHistory) {
        setHistory(cachedHistory);
        setNotifying(cachedHistory.length > 0);
        hasFetchedRef.current = true;
        return;
      }
    }

    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller
    abortControllerRef.current = new AbortController();
    hasFetchedRef.current = true;

    try {
      if (isMountedRef.current) {
        setLoading(true);
        setError(null);
      }

      console.log("🚀 Fetching history for user:", userId);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      
      // Add timeout to fetch
      const timeoutPromise = new Promise<never>((_, reject) => 
        setTimeout(() => reject(new Error('Request timeout')), constants.API_TIMEOUT)
      );

      const fetchPromise = fetch(
        `${apiUrl}/api/v1/idea-refinement/history`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          signal: abortControllerRef.current?.signal,
        }
      );

      const response = await Promise.race([fetchPromise, timeoutPromise]);
      console.log("📡 History response status:", response.status);

      if (!response.ok) {
        let errorText = '';
        try {
          errorText = await response.text();
        } catch {
          errorText = 'No error details available';
        }
        
        console.error("❌ Server error response:", errorText);
        
        if (response.status === 401) {
          throw new Error('Authentication failed. Please log in again.');
        } else if (response.status === 403) {
          throw new Error('Access denied.');
        } else if (response.status === 404) {
          throw new Error('History endpoint not found.');
        } else {
          throw new Error(`Server error: ${response.status}`);
        }
      }

      const data: RefinementHistoryResponse = await response.json();
      console.log("✅ History data received:", data);
      
      if (data.success && Array.isArray(data.history)) {
        if (isMountedRef.current) {
          setHistory(data.history);
          setNotifying(data.history.length > 0);
        }
        
        // Cache the data
        setCachedHistory(data.history);
      } else {
        throw new Error(data.success === false ? 'Server returned error' : 'Invalid response format');
      }
    } catch (err) {
      if (!isMountedRef.current) return;
      
      if (err instanceof Error && err.name === 'AbortError') {
        console.log("⏹️ Request cancelled");
        return;
      }
      
      console.error('❌ Fetch history error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [userId, loading, getAuthToken, constants, getCachedHistory, setCachedHistory]);

  // Fetch when drawer opens and we have user data
  useEffect(() => {
    if (isOpen && userId && !hasFetchedRef.current && !loading && isMountedRef.current) {
      console.log("🎯 Triggering history fetch");
      fetchHistory();
    }
  }, [isOpen, userId, fetchHistory, loading]);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Handle item click navigation
  const handleItemClick = useCallback(async (item: RefinementHistoryItem) => {
    // Prevent multiple clicks
    if (clickingItemId) return;
    
    // Close drawer immediately for snappier UX
    setIsOpen(false);
    
    try {
      setClickingItemId(item.id);
      setNavigating(true);
      startLoading(); // Start global navigation loading
      
      const token = getAuthToken();
      if (!token || !userId) {
        console.error("❌ Missing auth for item click");
        router.push('/signin');
        return;
      }

      console.log("🔗 Navigating to results for item:", item.id);

      // Transform the history item data to match the IdeaRefinementResponse interface
      const resultsData = {
        success: true,
        session_id: item.id,
        problem_statements: [], // Empty array since field is no longer available
        parsed_context: {
          persona: '',
          industry: '',
          geography: '',
          delivery_mode: ''
        },
        processing_time: item.processing_time_seconds || 0
      };

      // Store the data in sessionStorage
      try {
        sessionStorage.setItem(constants.STORAGE_KEYS.RESULTS, JSON.stringify(resultsData));
        sessionStorage.setItem(constants.STORAGE_KEYS.ORIGINAL_IDEA, item.original_idea || '');
        
        console.log("📦 Stored results data:", resultsData);
        
        // Dispatch custom event to notify results page of new data
        window.dispatchEvent(new CustomEvent('refinementDataUpdated'));
        
        // Navigate to the results page
        router.push(`${workspacePath}/idea-refiner/history/${item.id}`);
      } catch (storageError) {
        console.error('Storage error:', storageError);
        throw new Error('Failed to store session data');
      }
      
    } catch (error) {
      console.error('❌ Navigation error:', error);
      // Fallback with minimal valid data
      const fallbackData = {
        success: true,
        session_id: item.id,
        problem_statements: [], // Empty array since field is no longer available
        parsed_context: {
          persona: '',
          industry: '',
          geography: '',
          delivery_mode: ''
        },
        processing_time: 0
      };
      
      try {
        sessionStorage.setItem(constants.STORAGE_KEYS.RESULTS, JSON.stringify(fallbackData));
        sessionStorage.setItem(constants.STORAGE_KEYS.ORIGINAL_IDEA, item.original_idea || '');
        router.push(`${workspacePath}/idea-refiner/results`);
      } catch (fallbackError) {
        console.error('Fallback navigation failed:', fallbackError);
        setError('Failed to navigate to results page');
      }
    } finally {
      setClickingItemId(null);
      setNavigating(false);
    }
  }, [clickingItemId, userId, router, getAuthToken, constants, startLoading]);

  // Memoized utility functions
  const formatTimeAgo = useCallback((dateString: string) => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
      
      if (diffInSeconds < 60) return 'Just now';
      if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
      if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
      if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
      return date.toLocaleDateString();
    } catch {
      return 'Unknown';
    }
  }, []);

  const truncateText = useCallback((text: string, maxLength: number = 80) => {
    if (!text) return 'Untitled';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }, []);

  // Memoized status functions
  const getStatusIcon = useCallback((status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />;
      case 'processing':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-600 dark:text-blue-400" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />;
      default:
        return <Clock className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />;
    }
  }, []);

  const getStatusColor = useCallback((status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case 'processing':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
    }
  }, []);

  // Default trigger button
  const defaultTrigger = (
    <Button variant="outline" size="sm" className="gap-2 h-9 px-3 font-medium border-brand-200 dark:border-brand-700 hover:bg-brand-50 dark:hover:bg-brand-900/20 relative">
      <Lightbulb className="h-4 w-4 text-brand-500 dark:text-brand-400" />
      <span className="hidden sm:inline text-brand-500 dark:text-brand-400">History</span>
      {notifying && history.length > 0 && (
        <span className="absolute -top-1 -right-1 flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
        </span>
      )}
    </Button>
  );

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        {trigger || defaultTrigger}
      </SheetTrigger>
      
      <SheetContent side="right" className="w-[420px] sm:w-[580px] h-full flex flex-col p-0 bg-background dark:bg-gray-900/95 backdrop-blur-sm border-border dark:border-brand-800/50">
        <div className="flex flex-col h-full">
          <SheetHeader className="p-4 border-b shrink-0 border-border dark:border-brand-800/50 bg-background/50 dark:bg-gray-900/50 backdrop-blur-sm">
            <SheetTitle className="flex items-center gap-2 text-xl font-semibold text-brand-600 dark:text-brand-300">
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => fetchHistory(true)} 
                className="gap-2 text-brand-500 dark:text-brand-400 hover:text-brand-600 dark:hover:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-800/30"
                disabled={loading}
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              Refinement History
              {loading && (
                <Loader2 className="w-4 h-4 animate-spin text-brand-500 dark:text-brand-400" />
              )}
            </SheetTitle>
          </SheetHeader>

          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {/* Main Content Area - This is where scrolling should happen */}
            <div className="flex-1 overflow-hidden p-2 bg-background dark:bg-gray-900/30">
              {loading && history.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="flex flex-col items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-900/50 border border-brand-200 dark:border-brand-700">
                      <Loader2 className="h-5 w-5 animate-spin text-brand-500 dark:text-brand-400" />
                    </div>
                    <div className="space-y-1 text-center">
                      <p className="text-sm font-medium text-brand-600 dark:text-brand-300">Loading refinement history</p>
                      <p className="text-xs text-muted-foreground dark:text-brand-400">Please wait while we fetch your refinement sessions</p>
                    </div>
                  </div>
                </div>
              ) : error ? (
                <div className="flex flex-col items-center justify-center h-full space-y-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800">
                    <AlertCircle className="h-6 w-6 text-red-500 dark:text-red-400" />
                  </div>
                  <div className="space-y-2 text-center">
                    <p className="text-sm font-medium text-brand-600 dark:text-brand-300">Failed to load history</p>
                    <p className="text-xs text-muted-foreground dark:text-brand-400 max-w-[280px]">{error}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => fetchHistory(true)} className="gap-2 border-brand-200 dark:border-brand-700 hover:bg-brand-50 dark:hover:bg-brand-900/20">
                    <RefreshCw className="h-3.5 w-3.5" />
                    Try Again
                  </Button>
                </div>
              ) : history.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full space-y-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted dark:bg-gray-800/50 border border-border dark:border-brand-700">
                    <FileText className="h-6 w-6 text-muted-foreground dark:text-brand-400" />
                  </div>
                  <div className="space-y-2 text-center">
                    <p className="text-sm font-medium text-brand-600 dark:text-brand-300">No refinement history yet</p>
                    <p className="text-xs text-muted-foreground dark:text-brand-400 max-w-[280px]">
                      Start refining ideas to see your history appear here
                    </p>
                  </div>
                </div>
              ) : (
                <ScrollArea className="h-full pr-2">
                  <div className="space-y-3 pr-2">
                    {history.map((item) => (
                      <div key={item.id}>
                        <div
                          className={`group relative rounded-lg border bg-card dark:bg-gray-800/50 p-4 transition-all duration-200 hover:bg-brand-50 dark:hover:bg-brand-900/20 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-sm cursor-pointer border-border dark:border-brand-700/50 ${
                            clickingItemId === item.id ? 'opacity-75 cursor-wait' : ''
                          }`}
                          onClick={() => handleItemClick(item)}
                        >
                          <div className="space-y-2">
                            {/* Header with title and badges */}
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <h4 className="font-semibold text-sm line-clamp-2 text-brand-600 dark:text-brand-200 group-hover:text-brand-700 dark:group-hover:text-brand-100 transition-colors">
                                  {truncateText(item.session_title, 50)}
                                </h4>
                              </div>
                              <div className="shrink-0">
                                {clickingItemId === item.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin text-brand-500 dark:text-brand-400" />
                                ) : (
                                  getStatusIcon(item.status)
                                )}
                              </div>
                            </div>

                            {/* Original idea preview */}
                            {item.original_idea && (
                              <p className="text-xs text-muted-foreground dark:text-brand-400 line-clamp-2">
                                {truncateText(item.original_idea, 100)}
                              </p>
                            )}

                            {/* Footer - Metadata */}
                            <div className="flex items-center justify-between pt-2 border-t border-border dark:border-brand-700/50">
                              <div className="flex items-center gap-3 text-xs text-muted-foreground dark:text-brand-400">
                                <div className="flex items-center gap-1">
                                  <Calendar className="h-3 w-3" />
                                  <span>{formatTimeAgo(item.updated_at)}</span>
                                </div>
                                <div className="flex items-center gap-1">
                                  <FileText className="h-3 w-3" />
                                  <span>{item.metadata?.problems_generated || 0} problems</span>
                                </div>
                                {item.metadata?.average_score && (
                                  <div className="flex items-center gap-1">
                                    <TrendingUp className="h-3 w-3" />
                                    <span>{item.metadata.average_score.toFixed(1)} avg</span>
                                  </div>
                                )}
                              </div>
                              <span 
                                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${getStatusColor(item.status)}`}
                              >
                                {clickingItemId === item.id ? 'Loading...' : item.status}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
