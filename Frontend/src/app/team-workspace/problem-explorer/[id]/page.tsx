"use client";
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import PageBreadcrumb from "@/components/common/PageBreadCrumb";

import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/authStore';
import { toast } from 'react-hot-toast';
import { 
  Target, 
  Users, 
  Lightbulb, 
  ArrowLeft, 
  Loader2, 
  AlertCircle,
  ArrowRight,
} from 'lucide-react';

// Interfaces for the problem generation data
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

interface SupportingSource {
  url: string;
  title: string;
  author: string | null;
  domain: string;
  source_uuid: string;
  content_type: string;
  citation_number: number;
  publication_date: string | null;
  credibility_score: number;
}

interface ProblemStatement {
  id: string;
  user_id: string;
  tenant_id: string | null;
  session_id: string;
  title: string;
  description: string;
  category: string;
  severity_level: string;
  target_geography: string[];
  target_demographics: string[];
  affected_population_size: number | null;
  problem_type: string;
  time_horizon: string;
  complexity_level: string;
  root_causes: string[];
  potential_effects: string[];
  stakeholders: string[];
  success_metrics: string[];
  supporting_sources: SupportingSource[];
  embedding: any | null;
  generation_parameters: GenerationParameters;
  generation_model: string;
  generation_timestamp: string;
  quality_score: number;
  validation_status: string;
  validated_by: string | null;
  validated_at: string | null;
  is_bookmarked: boolean;
  is_liked: boolean;
  like_count: number;
  view_count: number;
  created_at: string;
  updated_at: string;
  impact_focus: string[];
}

interface ProblemResult {
  result_id: string | null;
  rank: number;
  selected: boolean;
  quality_score: number;
  viewed: boolean;
  bookmarked: boolean;
  liked: boolean;
  problem_statements: ProblemStatement;
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
  results: ProblemResult[];
}

interface WorkflowAPIError extends Error {
  status?: number;
}

// Constants for maintainability
const constants = {
  API_TIMEOUT: 10000, // 10 seconds
  RETRY_DELAY: 2000, // 2 seconds
  MAX_RETRIES: 3
} as const;

// API function to fetch session details with proper error handling
const getSessionDetails = async (sessionId: string, authToken: string, signal?: AbortSignal): Promise<GenerationSession> => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ;
  
  if (process.env.NODE_ENV === 'development') {
    console.log('🔄 Fetching session details for:', sessionId);
  }

  // Add timeout to fetch
  const timeoutPromise = new Promise<never>((_, reject) => 
    setTimeout(() => reject(new Error('Request timeout')), constants.API_TIMEOUT)
  );

  const fetchPromise = fetch(`${apiUrl}/api/v1/pgen/history/${sessionId}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    },
    signal,
  });

  const response = await Promise.race([fetchPromise, timeoutPromise]);

  if (!response.ok) {
    let errorMessage = `HTTP error! status: ${response.status}`;
    
    // Handle specific status codes
    if (response.status === 401) {
      errorMessage = 'Authentication failed. Please log in again.';
    } else if (response.status === 403) {
      errorMessage = 'Access denied. You do not have permission to view this session.';
    } else if (response.status === 404) {
      errorMessage = 'Session not found. It may have been deleted or does not exist.';
    } else if (response.status >= 500) {
      errorMessage = 'Server error. Please try again later.';
    }

    const error = new Error(errorMessage) as WorkflowAPIError;
    error.status = response.status;
    throw error;
  }

  const data = await response.json();
  
  if (process.env.NODE_ENV === 'development') {
    console.log('✅ Session data received:', data);
  }
  
  return data;
};


const ProblemExplorerPage = () => {
  const params = useParams();
  const router = useRouter();
  
  // Use Zustand store for authentication
  const { isAuthenticated, token } = useAuthStore();
  
  const [session, setSession] = useState<GenerationSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  
  // Refs for cleanup and state tracking
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);
  const retryTimeoutRef = useRef<NodeJS.Timeout>();

  const sessionId = params.id as string;

  // Safe token retrieval using Zustand store
  const getAuthToken = useCallback(() => {
    return token || null;
  }, [token]);

  const fetchSessionData = useCallback(async () => {
    // Prevent multiple calls and check mount status
    if (!isMountedRef.current) return;

    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller
    abortControllerRef.current = new AbortController();

    if (!isAuthenticated || !sessionId) {
      const errorMsg = !isAuthenticated ? 'Authentication required' : 'Invalid session ID';
      if (isMountedRef.current) {
        setError(errorMsg);
        setLoading(false);
      }
      return;
    }

    try {
      if (isMountedRef.current) {
        setLoading(true);
        setError(null);
      }
      
      const token = getAuthToken();
      if (!token) {
        throw new Error('Authentication token not found');
      }

      const sessionData = await getSessionDetails(sessionId, token, abortControllerRef.current.signal);
      
      if (isMountedRef.current) {
        setSession(sessionData);
        setRetryCount(0); // Reset retry count on success
        
        if (sessionData.status === 'failed') {
          toast.error("This problem generation session failed to complete.");
        }
      }
    } catch (err) {
      if (!isMountedRef.current) return;
      
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('⏹️ Session fetch request cancelled');
        return;
      }
      
      console.error('❌ Error fetching session data:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load session data';
      
      setError(errorMessage);
      
      // Auto-retry for network errors (up to MAX_RETRIES times)
      if (retryCount < constants.MAX_RETRIES && 
          (errorMessage.includes('network') || errorMessage.includes('timeout') || errorMessage.includes('Server error'))) {
        const nextRetryCount = retryCount + 1;
        setRetryCount(nextRetryCount);
        
        if (process.env.NODE_ENV === 'development') {
          console.log(`🔄 Auto-retrying session fetch (attempt ${nextRetryCount})`);
        }
        
        retryTimeoutRef.current = setTimeout(() => {
          fetchSessionData();
        }, constants.RETRY_DELAY * Math.pow(2, retryCount)); // Exponential backoff
      } else {
        toast.error(errorMessage);
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [isAuthenticated, sessionId, getAuthToken, retryCount]);

  useEffect(() => {
    isMountedRef.current = true;
    fetchSessionData();

    return () => {
      isMountedRef.current = false;
      // Cleanup all pending requests and timeouts
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, [fetchSessionData]);

  const handleGoBack = useCallback(() => {
    router.push('/team-workspace/problem-explorer');
  }, [router]);

  const handleRetry = useCallback(() => {
    setRetryCount(0);
    setError(null);
    fetchSessionData();
  }, [fetchSessionData]);

  const handleValidateProblem = useCallback(
    (problem: ProblemStatement, index: number) => {
      if (typeof window === 'undefined') return;

      try {
        const statementText = problem.title;
        const selectedProblemStatement = {
          statement: statementText,
          assumptions: [] as string[],
        };

        const firstIndustry = problem.generation_parameters?.industry?.[0] ?? '';
        const firstGeography = problem.generation_parameters?.geography?.[0] ?? '';
        const firstDeliveryMode = problem.generation_parameters?.product_type?.[0] ?? '';
        const firstPersona = problem.target_demographics?.[0] ?? '';

        const validationData = {
          selectedProblemStatement,
          problemIndex: index,
          // originalIdea: problem.title,
          // contextAnalysis: undefined,
          // persona: firstPersona,
          // industry: firstIndustry,
          // geography: firstGeography,
          // delivery_mode: firstDeliveryMode,
          sessionId: session?.session_id,
          allProblemStatements: undefined,
        };

        window.sessionStorage.setItem('marketValidationData', JSON.stringify(validationData));
        router.push('/team-workspace/problem-validator');
      } catch (storageError) {
        if (process.env.NODE_ENV === 'development') {
          // eslint-disable-next-line no-console
          console.error('Failed to store validation data from Problem Explorer:', storageError);
        }
        toast.error('Failed to prepare validation data. Please try again.');
      }
    },
    [router, session?.session_id]
  );

  // Function to convert inline citations to clickable links
  const convertCitationsToLinks = useCallback((text: string, sources: SupportingSource[]) => {
    if (!text || !sources || sources.length === 0) return text;
    
    // Regex to match citation patterns like [1], [2], etc.
    const citationRegex = /\[(\d+)\]/g;
    
    return text.replace(citationRegex, (match, citationNumber) => {
      const num = parseInt(citationNumber, 10);
      const source = sources.find(s => s.citation_number === num);
      
      if (source && source.url) {
        return `<a href="${source.url}" target="_blank" rel="noopener noreferrer" class="text-brand-600 hover:text-brand-800 underline cursor-pointer font-medium">${match}</a>`;
      }
      
      return match; // Return original if no matching source found
    });
  }, []);

  // Memoized problem card component
  const ProblemCard = useCallback(
    ({
      problem,
      index,
      onValidate,
    }: {
      problem: ProblemStatement;
      index: number;
      onValidate: (problem: ProblemStatement, index: number) => void;
    }) => (
      <Card key={problem.id} className="border border-brand-100">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="bg-brand-100 text-brand-700 dark:bg-brand-500/20 dark:text-brand-300 px-3 py-1 rounded-full text-xs font-medium">
                  Problem #{index + 1}
                </span>
              </div>
              <CardTitle className="text-lg leading-tight text-brand-600 dark:text-white">
                {problem.title}
              </CardTitle>
            </div>

            <Button
              className="mt-1 flex items-center gap-2 bg-brand-500 text-white dark:bg-brand-500/60 dark:text-brand-50 border border-brand-200 dark:border-brand-700 px-4 py-2 rounded-lg text-sm font-medium shadow-sm transition-all ease-in-out hover:bg-brand-700 dark:hover:bg-brand-800 focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
              onClick={(e) => {
                e.stopPropagation();
                onValidate(problem, index);
              }}
              aria-label={`Validate problem ${index + 1}`}
            >
              <span>Validate this problem</span>
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          <div 
            className="text-muted-foreground leading-relaxed text-sm -mt-4"
            dangerouslySetInnerHTML={{ 
              __html: convertCitationsToLinks(problem.description, problem.supporting_sources) 
            }}
          />

          <div className="grid md:grid-cols-2 gap-4">

           <div className="space-y-4 p-4 bg-brand-25 rounded-lg dark:bg-brand-500/20 md:col-span-2">
              <div className="flex items-center gap-2 text-md font-medium text-brand-600 dark:text-brand-200">
                <AlertCircle className="w-4 h-4" aria-hidden="true" />
                Supporting Sources
              </div>
              <div className="flex flex-col gap-2">
                {(problem.supporting_sources ?? []).slice(0, 4).map((source, idx) => (
                  <a
                    key={idx}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-300 px-3 py-2 rounded-lg text-sm hover:bg-brand-100 dark:hover:bg-brand-500/20 transition-colors"
                  >
                    <span className="font-medium">
                      {source.title || source.domain || 'View source'}
                    </span>
                    {source.domain && (
                      <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                        ({source.domain})
                      </span>
                    )}
                  </a>
                ))}
                {(!problem.supporting_sources || problem.supporting_sources.length === 0) && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 italic">
                    No supporting sources provided for this problem.
                  </div>
                )}
              </div>
            </div>
            <div className="space-y-4 p-4 bg-brand-25 rounded-lg dark:bg-brand-500/20">
              <div className="flex items-center gap-2 text-md font-medium text-brand-600 dark:text-brand-200">
                <Target className="w-4 h-4" aria-hidden="true" />
                Root Causes
              </div>
              <div className="flex flex-col gap-2">
                {(problem.root_causes ?? []).slice(0, 3).map((cause, idx) => (
                  <div
                    key={idx}
                    className="bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-300 px-3 py-2 rounded-lg text-sm"
                  >
                    {cause}
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-4 p-4 bg-brand-25 rounded-lg dark:bg-brand-500/20">
              <div className="flex items-center gap-2 text-md font-medium text-brand-600 dark:text-brand-200">
                <AlertCircle className="w-4 h-4" aria-hidden="true" />
                Potential Effects
              </div>
              <div className="flex flex-col gap-2">
                {(problem.potential_effects ?? []).slice(0, 4).map((effect, idx) => (
                  <div
                    key={idx}
                    className="bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-300 px-3 py-2 rounded-lg text-sm"
                  >
                    {effect}
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-4 p-4 bg-brand-25 rounded-lg dark:bg-brand-500/20">
              <div className="flex items-center gap-2 text-md font-medium text-brand-600 dark:text-brand-200">
                <Users className="w-4 h-4" aria-hidden="true" />
                Key Stakeholders
              </div>
              <div className="flex flex-col gap-2">
                {(problem.stakeholders ?? []).slice(0, 3).map((stakeholder, idx) => (
                  <div
                    key={idx}
                    className="bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-300 px-3 py-2 rounded-lg text-sm"
                  >
                    {stakeholder}
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-4 p-4 bg-brand-25 rounded-lg dark:bg-brand-500/20">
              <div className="flex items-center gap-2 text-md font-medium text-brand-600 dark:text-brand-200">
                <Lightbulb className="w-4 h-4" aria-hidden="true" />
                Success Metrics
              </div>
              <div className="flex flex-col gap-2">
                {(problem.success_metrics ?? []).slice(0, 4).map((metric, idx) => (
                  <div
                    key={idx}
                    className="bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-300 px-3 py-2 rounded-lg text-sm"
                  >
                    {metric}
                  </div>
                ))}
              </div>
            </div>

           

          </div>
        </CardContent>
      </Card>
    ),
    []
  );

  const problemsList = useMemo(() => {
    if (!session?.results) return null;

    const problems = session.results.map(result => result.problem_statements);

    return (
      <div className="grid gap-4">
        {problems.map((problem, index) => (
          <ProblemCard
            key={problem.id}
            problem={problem}
            index={index}
            onValidate={handleValidateProblem}
          />
        ))}
      </div>
    );
  }, [session?.results, ProblemCard, handleValidateProblem]);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen p-6" role="status" aria-live="polite">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-20">
            <div className="text-center space-y-4">
              <Loader2 className="w-8 h-8 animate-spin text-brand-500 mx-auto" aria-hidden="true" />
              <p className="text-gray-600 dark:text-gray-400">
                {retryCount > 0 ? `Loading (retry ${retryCount}/${constants.MAX_RETRIES})...` : 'Loading problem generation session...'}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen p-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-20">
            <div className="text-center space-y-4" role="alert" aria-live="polite">
              <AlertCircle className="w-12 h-12 text-red-500 mx-auto" aria-hidden="true" />
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Failed to Load Session
              </h2>
              <p className="text-gray-600 dark:text-gray-400 max-w-md">
                {error || 'Session not found or you do not have permission to view it.'}
              </p>
              <div className="flex gap-3 justify-center">
                <Button 
                  onClick={handleGoBack} 
                  variant="outline"
                  aria-label="Go back to problem explorer"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" aria-hidden="true" />
                  Go Back
                </Button>
                <Button 
                  onClick={handleRetry}
                  disabled={retryCount >= constants.MAX_RETRIES}
                  aria-label="Retry loading session"
                >
                  {retryCount >= constants.MAX_RETRIES ? 'Max Retries Reached' : 'Retry'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // No session data state - only show if not loading and no error
  if (!loading && !error && !session) {
    return (
      <div className="min-h-screen p-6">
        <div className="max-w-6xl mx-auto ">
          <div className="flex items-center justify-center py-20">
            <div className="text-center space-y-4 ">
              <Loader2 className="w-8 h-8 animate-spin text-brand-500 mx-auto mb-4" aria-hidden="true" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Loading Session Data
              </h3>
              
             
            </div>
          </div>
        </div>
      </div>
    );
  }

  const problems = session.results?.map(result => result.problem_statements) || [];

  return (
    <div className="relative flex flex-col overflow-x-hidden ">
          <PageBreadcrumb pageTitle="Problem Explorer" />
          <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-white/[0.03] ">
       
        {/* Problems Results */}
        {session.status === 'completed' && problems.length > 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-4"
          >
            <div className="flex items-center justify-between">
            <div className="flex items-center justify-between">
          <Button 
            onClick={handleGoBack} 
            variant="outline" 
            className="flex items-center gap-2"
            aria-label="Go back to problem explorer"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Back 
          </Button>
        </div>
        <div className="flex flex-col items-center justify-between">

          
              <h2 className="text-xl font-semibold text-brand-600 dark:text-white">
                Potential Problems You Could Explore
              </h2>

<p className="text-sm text-gray-500 dark:text-gray-400">Let's now help you explore potential problems you could solve for</p>
              </div>

              <span className="text-sm text-gray-500 dark:text-gray-400">
                {problems.length} results
              </span>
            </div>

            {problemsList}
          </motion.div>
        ) : session.status === 'running' ? (
          <div className="text-center py-12" role="status" aria-live="polite">
            <Loader2 className="w-8 h-8 animate-spin text-brand-500 mx-auto mb-4" aria-hidden="true" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Generation In Progress
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Your problems are being generated. This may take a few minutes.
            </p>
          </div>
        ) : (
          <div className="text-center py-12">
            <AlertCircle className="w-8 h-8 text-gray-400 mx-auto mb-4" aria-hidden="true" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              No Problems Available
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              This session doesn't have any generated problems yet.
            </p>
          </div>
        )}
      </div>
      </div>
  );
};

export default ProblemExplorerPage;