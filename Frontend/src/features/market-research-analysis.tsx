"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "react-hot-toast";
import { 
  FileText, 
  CheckCircle2, 
  AlertCircle,
  Loader2,
  Users,
  Target,
  TrendingUp,
  Award,
  ArrowLeft,
  BarChart3,
  Lightbulb,
  AlertTriangle,
  Info,
  Download,
  Share2,
  MessageCircle,
  X,
  Send,
  RefreshCw,
  UserCircle2
} from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { ChatDrawer } from "@/components/chat";

interface MarketResearchData {
  project_id: string;
  status: string;
  report_available: boolean;
  format: string;
  personas: {
    [key: string]: {
      structured_report: {
        metadata: {
          user_id: string | null;
          tenant_id: string;
          project_id: string;
          report_type: string;
          generated_at: string;
          project_name: string;
          report_version: string;
        };
        assumptions: {
          analyses: {
            title: string;
            accuracy_level: string;
            dimension_type: string;
            primary_insight: string;
            confidence_score: number;
            counter_evidence: {
              text: string;
              citations: string[];
              confidence: number | null;
            }[];
            data_limitations: string | null;
            statistical_summary: any | null;
            supporting_evidence: {
              text: string;
              citations: string[];
              confidence: number | null;
            }[];
            quantitative_findings: any | null;
          }[];
          key_findings: string[];
          persona_name: string;
          assumption_id: string;
          recommendation: string;
          assumption_text: string;
          confidence_label: string;
          validation_status: string;
          overall_confidence: number;
        }[];
        executive_summary: {
          content: string;
          statistics: {
            validated: number;
            invalidated: number;
            total_assumptions: number;
            average_confidence: number;
            partially_validated: number;
          };
          key_insights: string[];
        };
        research_data_summary: {
          csv_files: any[];
          data_type: string;
          pdf_files: {
            pages: number;
            chunks: number;
            filename: string;
            source_type: string;
          }[];
          total_data_fields: number;
          total_respondents: number;
          total_files_processed: number;
          total_interview_files: number;
          interview_participants: any[];
        };
      };
      final_report: string;
      session_id: string;
      stage: string;
      assumption_analyses: any[];
    };
  };
  root_stage: string;
}

interface MarketResearchAnalysisProps {
  projectId: string;
}

// Type aliases for nested structures
type Evidence = {
  text: string;
  citations: string[];
  confidence: number | null;
};

type Analysis = {
  title: string;
  accuracy_level: string;
  dimension_type: string;
  primary_insight: string;
  confidence_score: number;
  counter_evidence: Evidence[];
  data_limitations: string | null;
  statistical_summary: any | null;
  supporting_evidence: Evidence[];
  quantitative_findings: any | null;
};

type Assumption = {
  analyses: Analysis[];
  key_findings: string[];
  assumption_id: string;
  recommendation: string;
  assumption_text: string;
  confidence_label: string;
  validation_status: string;
  overall_confidence: number;
  persona_name: string;
};

// Chat Message Interface
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

// Chat Response Interface
interface ChatResponse {
  id: string;
  content: string;
  success: boolean;
  error?: string;
  chat_session_id: string;
  metadata?: any;
}

// Cache configuration
const CACHE_KEY_PREFIX = 'market_research_analysis_';
const CACHE_TIMESTAMP_KEY_PREFIX = 'market_research_analysis_timestamp_';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Cache utilities
const getCachedData = (projectId: string): MarketResearchData | null => {
  if (typeof window === 'undefined') return null;
  
  try {
    const cacheKey = `${CACHE_KEY_PREFIX}${projectId}`;
    const timestampKey = `${CACHE_TIMESTAMP_KEY_PREFIX}${projectId}`;
    
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
    
    return JSON.parse(cached);
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to read cache:', error);
    }
    return null;
  }
};

const setCachedData = (projectId: string, data: MarketResearchData): void => {
  if (typeof window === 'undefined') return;
  
  try {
    const cacheKey = `${CACHE_KEY_PREFIX}${projectId}`;
    const timestampKey = `${CACHE_TIMESTAMP_KEY_PREFIX}${projectId}`;
    
    localStorage.setItem(cacheKey, JSON.stringify(data));
    localStorage.setItem(timestampKey, Date.now().toString());
    
    if (process.env.NODE_ENV === 'development') {
      console.log('Cached market research data for project:', projectId);
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to cache data:', error);
    }
  }
};

const clearCache = (projectId: string): void => {
  if (typeof window === 'undefined') return;
  
  try {
    const cacheKey = `${CACHE_KEY_PREFIX}${projectId}`;
    const timestampKey = `${CACHE_TIMESTAMP_KEY_PREFIX}${projectId}`;
    
    localStorage.removeItem(cacheKey);
    localStorage.removeItem(timestampKey);
    
    if (process.env.NODE_ENV === 'development') {
      console.log('Cleared market research cache for project:', projectId);
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to clear cache:', error);
    }
  }
};

const MarketResearchAnalysis: React.FC<MarketResearchAnalysisProps> = ({ projectId }) => {
  const router = useRouter();
  const pathname = usePathname();
  const basePath = pathname?.startsWith('/workspace') ? '/workspace' : '/team-workspace';
  const { isAuthenticated, token } = useAuthStore();
  
  // Initialize state with cached data
  const [data, setData] = useState<MarketResearchData | null>(() => {
    const cached = getCachedData(projectId);
    if (cached) {
      if (process.env.NODE_ENV === 'development') {
        console.log('Loaded market research data from cache for project:', projectId);
      }
      return cached;
    }
    return null;
  });
  
  const [loading, setLoading] = useState(() => {
    // Don't show loading if we have cached data
    const cached = getCachedData(projectId);
    return !cached;
  });
  
  const [error, setError] = useState<string | null>(null);
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [expandedAssumptions, setExpandedAssumptions] = useState<Set<string>>(new Set());
  const [showAllEvidence, setShowAllEvidence] = useState<Record<string, boolean>>({});
  const [showError, setShowError] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  
  const isMountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const isFetchingRef = useRef(false);

  // Chat handlers - MUST be at the top level to avoid hooks violation
  const openChatbot = useCallback(() => setIsChatOpen(true), []);
  const closeChatbot = useCallback(() => setIsChatOpen(false), []);

  const fetchMarketResearchData = useCallback(async (forceRefresh: boolean = false) => {
    if (!isAuthenticated || !projectId) {
      const errorMsg = !isAuthenticated ? 'Authentication required' : 'Invalid project ID';
      if (isMountedRef.current) {
        setError(errorMsg);
        setLoading(false);
      }
      return;
    }

    // Prevent duplicate requests
    if (isFetchingRef.current) {
      if (process.env.NODE_ENV === 'development') {
        console.log('Request already in progress, skipping...');
      }
      return;
    }

    // Check cache first unless force refresh
    if (!forceRefresh) {
      const cached = getCachedData(projectId);
      if (cached) {
        if (process.env.NODE_ENV === 'development') {
          console.log('Using cached data, skipping API call');
        }
        setData(cached);
        setLoading(false);
        setError(null);
        setShowError(false);
        
        if (cached.personas && Object.keys(cached.personas).length > 0) {
          setSelectedPersona(Object.keys(cached.personas)[0]);
        }
        return;
      }
    } else {
      clearCache(projectId);
    }

    // Abort previous request if exists
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    isFetchingRef.current = true;

    try {
      if (isMountedRef.current) {
        setLoading(true);
        setError(null);
      }
      
      const authToken = token;
      if (!authToken) {
        throw new Error('Authentication token not found');
      }

      const API_URL = process.env.NEXT_PUBLIC_API_URL;
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Fetching market research data from API for project:', projectId);
      }

      const response = await fetch(
        `${API_URL}/api/v1/market-research/analysis/projects/${projectId}/results`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`,
          },
          signal: abortControllerRef.current.signal,
        }
      );

      if (!response.ok) {
        if (process.env.NODE_ENV === 'development') {
          console.log('Response error:', response);
        }
        setShowError(true);
        if (response.status === 401) {
          throw new Error('Authentication required. Please sign in again.');
        } else if (response.status == 404) {
          if (isMountedRef.current) {
            setData(null);
            setLoading(false);
            setShowError(true);
          }
          return;
        }
        throw new Error(`Failed to fetch results: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (isMountedRef.current) {
        setData(result.data);
        setCachedData(projectId, result.data);
        setShowError(false);
        
        if (result.data.personas && Object.keys(result.data.personas).length > 0) {
          setSelectedPersona(Object.keys(result.data.personas)[0]);
        }
        
        if (process.env.NODE_ENV === 'development') {
          console.log('Loaded and cached market research data');
        }
      }
    } catch (err) {
      if (!isMountedRef.current) return;
      
      if (err instanceof Error && err.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Request aborted');
        }
        return;
      }
      
      const errorMessage = err instanceof Error ? err.message : 'Failed to load data';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
      isFetchingRef.current = false;
    }
  }, [isAuthenticated, projectId, token]);

  useEffect(() => {
    if ((error || showError) && projectId) {
      router.push(`${basePath}/market-research-upload/${projectId}`);
    }
  }, [error, showError, projectId, router, basePath]);

  const handleRetry = () => {
    clearCache(projectId);
    router.push(`${basePath}/market-research-upload/${projectId}`);
  };

  const handleGoBack = () => {
    router.push(`${basePath}/projects-questionnaire-completed`);
  };

  const toggleAssumption = useCallback((assumptionId: string) => {
    setExpandedAssumptions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(assumptionId)) {
        newSet.delete(assumptionId);
      } else {
        newSet.add(assumptionId);
      }
      return newSet;
    });
  }, []);

  const toggleEvidence = useCallback((key: string) => {
    setShowAllEvidence(prev => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const getConfidenceBadgeColor = (confidence: number) => {
    if (confidence >= 0.8) return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300";
    if (confidence >= 0.6) return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300";
    return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
  };

  const getValidationStatusBadge = (status: string) => {
    const statusConfig = {
      validated: { icon: CheckCircle2, color: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300", label: "Validated" },
      invalidated: { icon: AlertCircle, color: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300", label: "Invalidated" },
      partially_validated: { icon: AlertTriangle, color: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300", label: "Partially Validated" },
    };
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.validated;
    const Icon = config.icon;
    
    return (
      <Badge className={`${config.color} flex items-center gap-1`}>
        <Icon className="w-3 h-3" />
        {config.label}
      </Badge>
    );
  };

  const currentPersonaData = useMemo(() => {
    if (!data || !selectedPersona) return null;
    return data.personas[selectedPersona];
  }, [data, selectedPersona]);

  const [isGoingBack, setIsGoingBack] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isProceeding, setIsProceeding] = useState(false);

  const microDelay = useCallback((ms: number = 600) => new Promise((res) => setTimeout(res, ms)), []);

  const handleGoBackClick = useCallback(async () => {
    try {
      setIsGoingBack(true);
      await microDelay(400);
      if (typeof handleGoBack === 'function') {
        await Promise.resolve(handleGoBack());
      }
    } finally {
      setIsGoingBack(false);
    }
  }, [handleGoBack, microDelay]);

  const handleRegenerateClick = useCallback(async () => {
    try {
      setIsRegenerating(true);
      await microDelay(800);
    } finally {
      setIsRegenerating(false);
    }
  }, [microDelay]);

  const handleNextStepClick = useCallback(async () => {
    try {
      setIsProceeding(true);
      router.push(`${basePath}/customer-profile-v2/${projectId}`);
    } finally {
      setIsProceeding(false);
    }
  }, [projectId, router, basePath]);

  // Fetch data immediately when component mounts
  useEffect(() => {
    isMountedRef.current = true;
    fetchMarketResearchData();

    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      isFetchingRef.current = false;
    };
  }, [fetchMarketResearchData]);

  // Show loading state while fetching data
  if (loading) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-8 dark:border-gray-700 dark:bg-transparent">
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <Loader2 className="w-12 h-12 text-gray-600 dark:text-gray-400 animate-spin" />
          <div className="text-center">
            <p className="text-lg font-medium text-brand-500 dark:text-gray-100">Loading Market Findings Results...</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Please wait while we fetch your findings data</p>
          </div>
        </div>
      </div>
    );
  }

  // Show error state if there was an error fetching data
  if (error || showError) {
    return null;
  }

  // Only show "No Results Available" when we have successfully fetched data but no results are available
  if (!data || !data.report_available || !currentPersonaData) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-8 dark:border-gray-700 dark:bg-transparent">
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <Loader2 className="w-12 h-12 text-gray-600 dark:text-gray-400 animate-spin" />
          <div className="text-center">
            <p className="text-lg font-medium text-brand-500 dark:text-gray-100">Loading Market Findings ...</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Please wait while we fetch your findings data</p>
          </div>
        </div>
      </div>
    );
  }

  const { structured_report } = currentPersonaData;

  // Add null check before destructuring
  if (!structured_report) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-8 dark:border-gray-700 dark:bg-transparent">
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <AlertCircle className="w-12 h-12 text-red-500 dark:text-red-400" />
          <div className="text-center">
            <p className="text-lg font-medium text-red-600 dark:text-red-400">No Analysis Data Available</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">The structured report is not available for this persona</p>
          </div>
          <Button onClick={handleRetry} className="bg-brand-500 hover:bg-gray-700 dark:bg-transparent dark:hover:bg-gray-700">
            <Loader2 className="w-4 h-4 mr-2" />
            Retry Analysis
          </Button>
        </div>
      </div>
    );
  }

  const { executive_summary, assumptions, metadata, research_data_summary } = structured_report;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-transparent space-y-4">
      {/* Header Section */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-brand-500 dark:text-gray-300 flex items-center gap-2 px-4 bg-brand-25 dark:bg-transparent border-gray-200 dark:border-gray-600 py-2 border rounded-lg">
            Generated on {new Date(metadata.generated_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button
            onClick={handleGoBackClick}
            variant="outline"
            size="sm"
            disabled={isGoingBack}
            aria-busy={isGoingBack}
            aria-live="polite"
            className={`min-w-[160px] transition-all duration-300 ease-in-out active:scale-95 focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed text-brand-500 dark:text-gray-300 ${
              isGoingBack
                ? 'opacity-70 scale-[0.98] bg-gradient-to-r from-gray-50 to-gray-100 dark:from-brand-600 dark:to-gray-700 border-gray-300 dark:border-gray-600'
                : 'hover:scale-[1.02] hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600'
            }`}
          >
            {isGoingBack ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin text-gray-600 dark:text-gray-400" />
                <span className="animate-pulse">Going back...</span>
              </>
            ) : (
              <>
                <ArrowLeft className="w-4 h-4 mr-2 transition-transform group-hover:-translate-x-1" />
                Back to Projects
              </>
            )}
          </Button>

          <Button
            variant="default"
            size="sm"
            onClick={handleRetry}
            disabled={isRegenerating}
            aria-busy={isRegenerating}
            aria-live="polite"
            className={`min-w-[140px] bg-green-500 hover:bg-green-600 transition-all duration-300 ease-in-out active:scale-95 focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed relative overflow-hidden ${
              isRegenerating
                ? 'opacity-80 scale-[0.98] shadow-lg shadow-green-500/30'
                : 'hover:scale-[1.02] hover:shadow-lg hover:shadow-green-500/40'
            }`}
          >
            {isRegenerating && (
              <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"
                    style={{ backgroundSize: '200% 100%' }} />
            )}
            {isRegenerating ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                <span className="animate-pulse">Regenerating...</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4 mr-2 transition-transform group-hover:translate-y-0.5" />
                Regenerate
              </>
            )}
          </Button>

          <Button
            variant="default"
            size="sm"
            onClick={handleNextStepClick}
            disabled={isProceeding}
            aria-busy={isProceeding}
            aria-live="polite"
            className={`min-w-[120px] transition-all duration-300 ease-in-out active:scale-95 focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed relative overflow-hidden ${
              isProceeding
                ? 'opacity-80 scale-[0.98] shadow-lg shadow-gray-500/30'
                : 'hover:scale-[1.02] hover:shadow-lg hover:shadow-gray-500/40'
            }`}
          >
            {isProceeding && (
              <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"
                    style={{ backgroundSize: '200% 100%' }} />
            )}
            {isProceeding ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                <span className="animate-pulse">Processing...</span>
              </>
            ) : (
              <>
                <Share2 className="w-4 h-4 mr-2 transition-transform group-hover:translate-x-0.5" />
                Next Step
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Sticky Chat Button */}
      <div className="fixed bottom-6 right-6 z-40">
        <Button
          onClick={openChatbot}
          className="bg-brand-500 text-white hover:bg-gray-700 dark:bg-brand-500 dark:hover:bg-brand-700 shadow-lg transition-all duration-300 hover:scale-105 flex items-center justify-center p-4 rounded-full h-14 w-14"
          aria-label="Chat with AI"
        >
          <MessageCircle className="h-6 w-6" />
          <span className="sr-only">Chat with AI</span>
        </Button>
      </div>

      {/* Chatbot Drawer */}
      <ChatDrawer
        isOpen={isChatOpen}
        onClose={closeChatbot}
        projectId={projectId}
        title="Chat with Market Findings"
        placeholder="Type your message..."
        emptyStateTitle="Start a conversation"
        emptyStateDescription="Ask questions about your market research findings and get AI-powered insights."
        suggestedQuestions={[
          "Summarize the key findings",
          "What are the main recommendations?",
          "Explain the validation results"
        ]}
      />

      {/* Persona Toggle */}
      {Object.keys(data.personas).length > 1 && (
        <div className="flex justify-center mb-2">
          <div className="bg-white dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm ">
            <Tabs
              value={selectedPersona || Object.keys(data.personas)[0]}
              onValueChange={(value) => setSelectedPersona(value)}
              className="w-full"
            >
              <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${Object.keys(data.personas).length}, 1fr)` }}>
                {Object.keys(data.personas).map((personaKey) => (
                  <TabsTrigger
                    key={personaKey}
                    value={personaKey}
                    className="flex items-center gap-2 text-brand-500 dark:text-gray-300"
                  >
                    <UserCircle2 className="w-4 h-4" />
                    {data.personas[personaKey]?.structured_report?.assumptions?.[0]?.persona_name || personaKey}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>
        </div>
      )}

      {/* Executive Summary */}
      <Card className="shadow-md border-gray-200 dark:border-gray-700">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Award className="w-6 h-6 text-brand-500 dark:text-gray-400" />
            <CardTitle className="text-xl text-brand-500 dark:text-gray-100">Executive Summary</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 -mt-4">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line text-sm">
              {executive_summary.content.replace(/^Executive Summary:\s*/i, '')}
            </p>
          </div>

          {executive_summary.key_insights.length > 0 && (
            <div className="space-y-4 pt-6 border-t border-gray-200 dark:border-gray-700">
              <h4 className="font-semibold text-lg flex items-center gap-2 text-brand-500 dark:text-gray-100">
                <Lightbulb className="w-5 h-5 text-brand-500 dark:text-gray-400" />
                Key Insights
              </h4>
              <div className="grid gap-3">
                {executive_summary.key_insights.map((insight: string, idx: number) => (
                  <div key={idx} className="flex items-start gap-3 p-4 rounded-lg bg-gray-50 dark:bg-transparent border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500 text-white flex items-center justify-center text-xs font-bold mt-0.5">
                      {idx + 1}
                    </div>
                    <p className="text-sm text-gray-700 dark:text-gray-300 flex-1">{insight}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Assumption Analyses - All Expanded */}
      <div className="space-y-4 mt-8">
        <div className="flex items-center gap-3 px-2">
          <BarChart3 className="w-6 h-6 text-gray-600 dark:text-gray-400" />
          <h3 className="text-xl font-semibold text-brand-500 dark:text-gray-100">Assumption Analyses</h3>
          <Badge variant="outline" className="px-2 text-sm border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300">{assumptions.length} Total</Badge>
        </div>

        {assumptions.map((assumption: Assumption, index: number) => (
          <Card key={assumption.assumption_id} className="shadow-md border-gray-200 dark:border-gray-700 overflow-hidden">
            {/* Assumption Header */}
            <div className="bg-gray-50 dark:bg-transparent p-4">
              <div className="space-y-4">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge className="bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 text-sm px-3 py-1">
                    Assumption #{index + 1}
                  </Badge>
                  {getValidationStatusBadge(assumption.validation_status)}
                </div>
                <h3 className="text-md font-semibold text-brand-500 dark:text-gray-100 leading-tight">
                  {assumption.assumption_text}
                </h3>
              </div>
            </div>

            <CardContent className="p-4 space-y-4 -mt-6">
              {/* Recommendation */}
              <div className="p-4 bg-gray-50 dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-start gap-3">
                  <Info className="w-5 h-5 text-gray-600 dark:text-gray-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h4 className="font-semibold text-brand-500 dark:text-gray-100 mb-2">Recommendation</h4>
                    <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{assumption.recommendation}</p>
                  </div>
                </div>
              </div>

              {/* Dimension Analyses */}
              <div className="space-y-4">
                {assumption.analyses.map((analysis: Analysis, analysisIdx: number) => (
                  <div key={analysis.dimension_type} className="space-y-4 p-5 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-transparent">
                    {/* Dimension Header */}
                    <div className="flex items-center justify-between pb-3 border-b border-gray-200 dark:border-gray-700">
                      <h5 className="font-semibold text-base text-brand-500 dark:text-gray-100 capitalize flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-gray-700 dark:text-gray-300 font-bold text-sm">
                          {analysisIdx + 1}
                        </div>
                        {analysis.dimension_type.replace(/_/g, ' ')}
                      </h5>
                      <div className="flex items-center gap-2">
                        <Badge className={getConfidenceBadgeColor(analysis.confidence_score)}>
                          {Math.round(analysis.confidence_score * 100)}% Confidence
                        </Badge>
                        <Badge variant="outline" className="capitalize">
                          {analysis.accuracy_level} Accuracy
                        </Badge>
                      </div>
                    </div>

                    {/* Primary Insight */}
                    <div className="p-4 bg-white dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700">
                      <h6 className="font-medium text-brand-500 dark:text-gray-100 mb-2 flex items-center gap-2">
                        <Target className="w-4 h-4 text-brand-500 dark:text-gray-400" />
                        Primary Insight
                      </h6>
                      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{analysis.primary_insight}</p>
                    </div>

                    {/* Supporting Evidence */}
                    {analysis.supporting_evidence.length > 0 && (
                      <div className="space-y-3">
                        <h6 className="font-medium text-brand-500 dark:text-gray-100 flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400" />
                          Supporting Evidence ({analysis.supporting_evidence.length})
                        </h6>
                        <div className="grid gap-2">
                          {analysis.supporting_evidence.map((evidence: Evidence, idx: number) => (
                            <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                              <div className="flex-shrink-0 w-5 h-5 rounded-full bg-brand-500 text-white flex items-center justify-center text-xs font-bold mt-0.5">
                                {idx + 1}
                              </div>
                              <p className="text-sm text-gray-700 dark:text-gray-300 flex-1">{evidence.text}</p>
                              {evidence.confidence && (
                                <Badge className="bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300 text-xs">
                                  {Math.round(evidence.confidence * 100)}%
                                </Badge>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Counter Evidence */}
                    {analysis.counter_evidence.length > 0 && (
                      <div className="space-y-3">
                        <h6 className="font-medium text-red-700 dark:text-red-400 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4" />
                          Counter Evidence ({analysis.counter_evidence.length})
                        </h6>
                        <div className="grid gap-2">
                          {analysis.counter_evidence.map((evidence: Evidence, idx: number) => (
                            <div key={idx} className="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors">
                              <div className="flex-shrink-0 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center text-xs font-bold mt-0.5">
                                {idx + 1}
                              </div>
                              <p className="text-sm text-gray-700 dark:text-gray-300 flex-1">{evidence.text}</p>
                              {evidence.confidence && (
                                <Badge className="bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300 text-xs">
                                  {Math.round(evidence.confidence * 100)}%
                                </Badge>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Data Limitations */}
                    {analysis.data_limitations && (
                      <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
                        <div className="flex items-start gap-2">
                          <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <h6 className="font-medium text-yellow-800 dark:text-yellow-300 text-sm mb-1">Data Limitations</h6>
                            <p className="text-xs text-yellow-700 dark:text-yellow-400">{analysis.data_limitations}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Key Findings */}
              {assumption.key_findings.length > 0 && (
                <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <h5 className="font-semibold text-lg flex items-center gap-2 text-brand-500 dark:text-gray-100">
                    <Lightbulb className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                    Key Findings for This Assumption ({assumption.key_findings.length})
                  </h5>
                  <div className="grid gap-2">
                    {assumption.key_findings.map((finding: string, idx: number) => (
                      <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                        <div className="flex-shrink-0 w-5 h-5 rounded-full bg-brand-500 text-white flex items-center justify-center text-xs font-bold mt-0.5">
                          {idx + 1}
                        </div>
                        <p className="text-sm text-gray-700 dark:text-gray-300 flex-1">{finding}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default MarketResearchAnalysis;