"use client";

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
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
  CheckCircle, 
  Loader2, 
  AlertCircle,  
  Calendar,  
  Lightbulb, 
  Sparkles,
  RefreshCw,
  FileText,
  Users,
  MapPin
} from "lucide-react";

// Interfaces based on the API response
interface GenerationParameters {
  industry: string[];
  geography: string[];
  background: string[];
  impact_focus: string[];
  num_problems: number;
  product_type: string[];
  target_customer: string[];
  creativity_level: number;
  custom_constraints: string;
}

interface GenerationSession {
  session_id: string;
  user_id: string;
  session_name: string;
  session_description: string | null;
  parameters: GenerationParameters;
  status: "completed" | "failed" | "running";
  problems_generated: number;
  problems_selected: number;
  created_at: string;
  completed_at: string | null;
  results: unknown | null;
}

interface GenerationHistoryResponse {
  sessions: GenerationSession[];
  total_count: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

interface ProblemGenerationHistoryDrawerProps {
  trigger?: React.ReactNode;
  workspacePath?: string;
}

export default function ProblemGenerationHistoryDrawer({ 
  trigger,
  workspacePath
}: ProblemGenerationHistoryDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [notifying, setNotifying] = useState(false);
  const [sessions, setSessions] = useState<GenerationSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clickingSessionId, setClickingSessionId] = useState<string | null>(null);
  
  // Use Zustand store
  const { user, token, isAuthenticated } = useAuthStore();
  const router = useRouter();
  
  // Refs for cleanup and state tracking
  const abortControllerRef = useRef<AbortController | null>(null);
  const hasFetchedRef = useRef(false);
  const isMountedRef = useRef(true);

  // Constants for maintainability
  const constants = useMemo(() => ({
    CACHE_DURATION: 5 * 60 * 1000, // 5 minutes
    API_TIMEOUT: 10000, // 10 seconds
    STORAGE_KEYS: {
      SESSIONS: (userId: string) => `generationSessions_${userId}`,
      TIMESTAMP: (userId: string) => `generationSessionsTimestamp_${userId}`
    }
  }), []);

  // Get the correct user ID
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
      console.log("🔍 ProblemGenerationHistoryDrawer - User state:", { 
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
  const getCachedSessions = useCallback((): GenerationSession[] | null => {
    if (typeof window === 'undefined' || !userId) return null;
    
    try {
      const cached = localStorage.getItem(constants.STORAGE_KEYS.SESSIONS(userId));
      const timestamp = localStorage.getItem(constants.STORAGE_KEYS.TIMESTAMP(userId));
      
      if (!cached || !timestamp) return null;
      
      // Check if cache is fresh (5 minutes)
      const isCacheFresh = Date.now() - parseInt(timestamp) < constants.CACHE_DURATION;
      if (!isCacheFresh) {
        localStorage.removeItem(constants.STORAGE_KEYS.SESSIONS(userId));
        localStorage.removeItem(constants.STORAGE_KEYS.TIMESTAMP(userId));
        return null;
      }
      
      return JSON.parse(cached);
    } catch {
      // Clear corrupted cache
      localStorage.removeItem(constants.STORAGE_KEYS.SESSIONS(userId));
      localStorage.removeItem(constants.STORAGE_KEYS.TIMESTAMP(userId));
      return null;
    }
  }, [userId, constants]);

  const setCachedSessions = useCallback((sessions: GenerationSession[]) => {
    if (typeof window === 'undefined' || !userId) return;
    
    try {
      localStorage.setItem(constants.STORAGE_KEYS.SESSIONS(userId), JSON.stringify(sessions));
      localStorage.setItem(constants.STORAGE_KEYS.TIMESTAMP(userId), Date.now().toString());
    } catch (error) {
      console.error('Failed to cache sessions:', error);
    }
  }, [userId, constants]);

  // API function to fetch generation history
  const getGenerationHistory = useCallback(async (authToken: string, signal?: AbortSignal): Promise<GenerationHistoryResponse> => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    
    if (process.env.NODE_ENV === 'development') {
      console.log('🔄 Fetching generation history from:', `${apiUrl}/api/v1/pgen/history`);
    }
    
    const response = await fetch(`${apiUrl}/api/v1/pgen/history`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      signal,
    });

    if (process.env.NODE_ENV === 'development') {
      console.log('📊 Generation history response status:', response.status);
    }

    if (!response.ok) {
      let errorText = 'No error details available';
      try {
        errorText = await response.text();
      } catch {
        // Ignore text parsing errors
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Generation history API error:', {
          status: response.status,
          statusText: response.statusText,
          body: errorText
        });
      }
      
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

    const data = await response.json();
    
    if (process.env.NODE_ENV === 'development') {
      console.log('✅ Generation history response data:', data);
    }
    
    return data;
  }, []);

  // Optimized fetchSessions with proper error handling and race condition prevention
  const fetchSessions = useCallback(async (forceRefresh = false) => {
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
      const cachedSessions = getCachedSessions();
      if (cachedSessions) {
        setSessions(cachedSessions);
        setNotifying(cachedSessions.length > 0);
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

      console.log("🚀 Fetching sessions for user:", userId);

      // Add timeout to fetch
      const timeoutPromise = new Promise<never>((_, reject) => 
        setTimeout(() => reject(new Error('Request timeout')), constants.API_TIMEOUT)
      );

      const fetchPromise = getGenerationHistory(token, abortControllerRef.current?.signal);
      const response = await Promise.race([fetchPromise, timeoutPromise]);
      
      if (response.sessions && isMountedRef.current) {
        setSessions(response.sessions);
        setNotifying(response.sessions.length > 0);
        
        // Cache the data
        setCachedSessions(response.sessions);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (err) {
      if (!isMountedRef.current) return;
      
      if (err instanceof Error && err.name === 'AbortError') {
        console.log("⏹️ Request cancelled");
        return;
      }
      
      console.error('❌ Fetch sessions error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [userId, loading, getAuthToken, constants, getCachedSessions, setCachedSessions, getGenerationHistory]);

  // Fetch when drawer opens and we have user data
  useEffect(() => {
    if (isOpen && userId && !hasFetchedRef.current && !loading && isMountedRef.current) {
      console.log("🎯 Triggering sessions fetch");
      fetchSessions();
    }
  }, [isOpen, userId, fetchSessions, loading]);

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

  // Handle session click navigation
  const handleSessionClick = useCallback(async (session: GenerationSession) => {
    // Prevent multiple clicks
    if (clickingSessionId) return;
    
    // Close drawer immediately for snappier UX
    setIsOpen(false);
    
    try {
      setClickingSessionId(session.session_id);
      
      const token = getAuthToken();
      if (!token || !userId) {
        console.error("❌ Missing auth for session click");
        router.push('/signin');
        return;
      }

      console.log("🔗 Navigating to results for session:", session.session_id);

      // Navigate to the problem explorer with the session ID
      router.push(`${workspacePath}/problem-explorer/${session.session_id}`);
      
    } catch (error) {
      console.error('❌ Navigation error:', error);
      setError('Failed to navigate to session results');
    } finally {
      setClickingSessionId(null);
    }
  }, [clickingSessionId, userId, router, getAuthToken]);

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
    if (!text) return 'Untitled Session';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }, []);

  // Format parameter arrays for display
  const formatParameters = useCallback((params: GenerationParameters): string => {
    const industry = params.industry?.[0] || 'Unknown industry';
    const geography = params.geography?.[0] || 'Unknown region';
    return `${industry} • ${geography}`;
  }, []);

  // Memoized status functions
  const getStatusIcon = useCallback((status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />;
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-600 dark:text-blue-400" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />;
      default:
        return <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />;
    }
  }, []);

  const getStatusColor = useCallback((status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case 'running':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
    }
  }, []);

  const getStatusText = useCallback((status: string): string => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'Completed';
      case 'running':
        return 'Generating';
      case 'failed':
        return 'Failed';
      default:
        return status;
    }
  }, []);

  // Default trigger button
  const defaultTrigger = (
    <Button variant="outline" size="sm" className="gap-2 h-9 px-3 font-medium border-brand-200 dark:border-brand-700 hover:bg-brand-50 dark:hover:bg-brand-900/20 relative">
      <Sparkles className="h-4 w-4 text-brand-500 dark:text-brand-400" />
      <span className="hidden sm:inline text-brand-500 dark:text-brand-400">History</span>
      {notifying && sessions.length > 0 && (
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
                onClick={() => fetchSessions(true)} 
                className="gap-2 text-brand-500 dark:text-brand-400 hover:text-brand-600 dark:hover:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-800/30"
                disabled={loading}
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              Generation History
              {loading && (
                <Loader2 className="w-4 h-4 animate-spin text-brand-500 dark:text-brand-400" />
              )}
            </SheetTitle>
          </SheetHeader>

          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {/* Main Content Area */}
            <div className="flex-1 overflow-hidden p-2 bg-background dark:bg-gray-900/30">
              {loading && sessions.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="flex flex-col items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-900/50 border border-brand-200 dark:border-brand-700">
                      <Loader2 className="h-5 w-5 animate-spin text-brand-500 dark:text-brand-400" />
                    </div>
                    <div className="space-y-1 text-center">
                      <p className="text-sm font-medium text-brand-600 dark:text-brand-300">Loading generation history</p>
                      <p className="text-xs text-muted-foreground dark:text-brand-400">Please wait while we fetch your generation sessions</p>
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
                  <Button variant="outline" size="sm" onClick={() => fetchSessions(true)} className="gap-2 border-brand-200 dark:border-brand-700 hover:bg-brand-50 dark:hover:bg-brand-900/20">
                    <RefreshCw className="h-3.5 w-3.5" />
                    Try Again
                  </Button>
                </div>
              ) : sessions.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full space-y-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted dark:bg-gray-800/50 border border-border dark:border-brand-700">
                    <Sparkles className="h-6 w-6 text-muted-foreground dark:text-brand-400" />
                  </div>
                  <div className="space-y-2 text-center">
                    <p className="text-sm font-medium text-brand-600 dark:text-brand-300">No generation history yet</p>
                    <p className="text-xs text-muted-foreground dark:text-brand-400 max-w-[280px]">
                      Start generating problems to see your history appear here
                    </p>
                  </div>
                </div>
              ) : (
                <ScrollArea className="h-full pr-2">
                  <div className="space-y-3 pr-2">
                    {sessions.map((session) => (
                      <div key={session.session_id}>
                        <div
                          className={`group relative rounded-lg border bg-card dark:bg-gray-800/50 p-4 transition-all duration-200 hover:bg-brand-50 dark:hover:bg-brand-900/20 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-sm cursor-pointer border-border dark:border-brand-700/50 ${
                            clickingSessionId === session.session_id ? 'opacity-75 cursor-wait' : ''
                          }`}
                          onClick={() => handleSessionClick(session)}
                        >
                          <div className="space-y-2">
                            {/* Header with title and badges */}
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <h4 className="font-semibold text-sm line-clamp-2 text-brand-600 dark:text-brand-200 group-hover:text-brand-700 dark:group-hover:text-brand-100 transition-colors">
                                  {truncateText(session.session_name, 50)}
                                </h4>
                              </div>
                              <div className="shrink-0">
                                {clickingSessionId === session.session_id ? (
                                  <Loader2 className="w-4 h-4 animate-spin text-brand-500 dark:text-brand-400" />
                                ) : (
                                  getStatusIcon(session.status)
                                )}
                              </div>
                            </div>

                            {/* Parameters preview */}
                            <p className="text-xs text-muted-foreground dark:text-brand-400 line-clamp-1">
                              {formatParameters(session.parameters)}
                            </p>

                            {/* Footer - Metadata */}
                            <div className="flex items-center justify-between pt-2 border-t border-border dark:border-brand-700/50">
                              <div className="flex items-center gap-3 text-xs text-muted-foreground dark:text-brand-400">
                                <div className="flex items-center gap-1">
                                  <Calendar className="h-3 w-3" />
                                  <span>{formatTimeAgo(session.created_at)}</span>
                                </div>
                                <div className="flex items-center gap-1">
                                  <FileText className="h-3 w-3" />
                                  <span>{session.problems_generated || 0} problems</span>
                                </div>
                                {session.problems_selected > 0 && (
                                  <div className="flex items-center gap-1">
                                    <Users className="h-3 w-3" />
                                    <span>{session.problems_selected} selected</span>
                                  </div>
                                )}
                              </div>
                              <span 
                                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${getStatusColor(session.status)}`}
                              >
                                {clickingSessionId === session.session_id ? 'Loading...' : getStatusText(session.status)}
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
