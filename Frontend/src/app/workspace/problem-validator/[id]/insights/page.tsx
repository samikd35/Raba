  "use client";

import React, { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { 
  ArrowLeft, 
  RefreshCw, 
  AlertTriangle,
  Brain,
  Globe,
  Users,
  Factory,
  MapPin,
  Scale,
  Shield,
  MessageCircle,
  User,
  Bot
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import toast from "react-hot-toast";
import { useAuthStore } from "@/stores/authStore";
import { 
  fetchInsights, 
  filterActionableInsights,
  extractChatMessages,
  InsightsApiResponse, 
  BackendInsight 
} from "@/lib/api/insights";

// Updated types based on actual API response - FURTHER OPTIMIZED
interface StructuredInsightContent {
  important_questions_industry_geography: {
    desirability_analysis: string[];
    recommended_research_areas: string[];
    key_stakeholders_institutions: string[];
  };
  emerging_key_insights: {
    customer_segments: string;
    existing_solutions: string;
    distribution_channels: string;
    regulations_policies: string;
    government_policies: string;
    barriers_consumption: string;
  };
  leverage_points: string[];
  key_questions_for_founders: string[];
}

interface ChatMessageContent {
  role: 'user' | 'assistant';
  content: string;
  user_id: string;
  metadata: {
    chunks?: string[];
    tracking: {
      timestamp: string;
      client_info: {
        service: string;
      };
    };
    chat_session_id?: string;
    web_search_enabled?: boolean;
  };
  report_id: string;
  chat_session_id: string | null;
}

// Memoized helper functions to identify insight types - FURTHER OPTIMIZED
const isStructuredInsight = (insight: BackendInsight): insight is BackendInsight & { content: StructuredInsightContent } => {
  const content = insight.content;
  return insight.insight_type === 'comprehensive_actionable_insights' && 
        content && 
        typeof content === 'object' &&
        'important_questions_industry_geography' in content;
};

const isChatMessage = (insight: BackendInsight): insight is BackendInsight & { content: ChatMessageContent } => {
  const content = insight.content;
  return insight.title.includes('Chat Message') && 
        content && 
        typeof content === 'object' &&
        'role' in content;
};

// Enhanced custom hook for insights data fetching with additional optimizations
const useInsights = (reportId: string | null) => {
  const [insights, setInsights] = useState<InsightsApiResponse | null>(null);
  const [actionableInsights, setActionableInsights] = useState<BackendInsight[]>([]);
  const [chatMessages, setChatMessages] = useState<BackendInsight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated, token } = useAuthStore();
  const abortControllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  // Cleanup function for aborting requests
  const cleanup = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const fetchData = useCallback(async () => {
    console.log('fetchData called with:', { reportId, isAuthenticated, hasToken: !!token });
    
    if (!reportId?.trim()) {
      console.log('No report ID provided');
      setError('No report ID provided');
      setLoading(false);
      return;
    }

    if (!isAuthenticated) {
      console.log('Not authenticated');
      setError('Authentication required');
      setLoading(false);
      return;
    }

    // Prevent state updates if component unmounted
    if (!mountedRef.current) return;

    try {
      setLoading(true);
      setError(null);
      cleanup(); // Cleanup any previous requests

      if (!token?.trim()) {
        throw new Error('Authentication token not found');
      }

      console.log('Making API call to fetch insights for report:', reportId);

      // Create new abort controller for this request
      abortControllerRef.current = new AbortController();

      const data = await fetchInsights(reportId, token, abortControllerRef.current.signal);
      
      console.log('Insights API response:', data);
      
      // Check if component is still mounted before updating state
      if (!mountedRef.current) return;

      setInsights(data);

      // Use useMemo-like filtering for better performance
      if (data?.insights?.length) {
        const actionable = filterActionableInsights(data.insights);
        const chats = extractChatMessages(data.insights);
        
        console.log('Filtered insights:', { actionable: actionable.length, chats: chats.length });
        
        setActionableInsights(actionable);
        setChatMessages(chats);
      } else {
        console.log('No insights found in response');
        setActionableInsights([]);
        setChatMessages([]);
      }
    } catch (err: any) {
      // Ignore abort errors and check if component is mounted
      if (err.name === 'AbortError' || !mountedRef.current) return;
      
      console.error('Error fetching insights:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch insights';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [reportId, isAuthenticated, token, cleanup]);

  useEffect(() => {
    mountedRef.current = true;
    
    if (reportId && isAuthenticated) {
      fetchData();
    } else {
      setLoading(false);
    }

    // Cleanup on unmount
    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, [reportId, isAuthenticated]);

  return {
    insights,
    actionableInsights,
    chatMessages,
    loading,
    error,
    refetch: fetchData
  };
};

// Optimized Loading Component with performance improvements
const InsightsLoading = React.memo(() => (
  <div className="flex items-center justify-center min-h-[calc(100vh-10rem)]">
    <div className="text-center max-w-lg mx-auto p-8">
      {/* Spinner */}
      <div
        className="mx-auto mb-2 h-8 w-8 rounded-full border-2 border-brand-500/30 border-t-brand-600 animate-spin"
        role="status"
        aria-label="Loading insights"
        aria-live="polite"
      />

      <h2 className="text-xl font-semibold text-brand-500 dark:text-white">
      Extracting Actionable Insights      </h2>
    </div>
  </div>
));

InsightsLoading.displayName = 'InsightsLoading';

// Optimized Error Component
const InsightsError = React.memo(({ 
  error, 
  onRetry,
  onBack
}: { 
  error: string; 
  onRetry: () => void;
  onBack: () => void;
}) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
    <div className="text-center max-w-md mx-auto p-8">
      <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Analysis Failed</h2>
      <p className="text-gray-600 dark:text-gray-400 mb-6">{error}</p>
      <div className="flex gap-3 justify-center">
        <Button onClick={onRetry} className="bg-brand-600 hover:bg-brand-700">
          <RefreshCw className="h-4 w-4 mr-2" />
          Try Again
        </Button>
        <Button onClick={onBack} variant="outline">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Results
        </Button>
      </div>
    </div>
  </div>
));

InsightsError.displayName = 'InsightsError';

// Optimized Chat Message Component
const ChatMessageDisplay = React.memo(({ insight }: { insight: BackendInsight & { content: ChatMessageContent } }) => {
  const isUser = insight.content.role === 'user';
  
  // Memoize the processed content
  const processedContent = useMemo(() => 
    insight.content.content.split('\n').map((line, index) => (
      <p key={index} className="mb-2 last:mb-0">{line}</p>
    )),
    [insight.content.content]
  );

  const timestamp = useMemo(() => 
    new Date(insight.content.metadata.tracking.timestamp).toLocaleString(),
    [insight.content.metadata.tracking.timestamp]
  );

  const messageClass = isUser 
    ? 'bg-brand-500 text-white' 
    : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white';

  const iconClass = isUser ? 'bg-brand-500' : 'bg-gray-500';

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex gap-3 max-w-4xl ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${iconClass}`}>
          {isUser ? <User className="h-4 w-4 text-white" /> : <Bot className="h-4 w-4 text-white" />}
        </div>
        <div className={`p-4 rounded-lg ${messageClass}`}>
          <div className="prose prose-sm max-w-none dark:prose-invert">
            {processedContent}
          </div>
          <div className="text-xs opacity-70 mt-2">
            {timestamp}
          </div>
        </div>
      </div>
    </div>
  );
});

ChatMessageDisplay.displayName = 'ChatMessageDisplay';

// Optimized Insight Card Component
const InsightCard = React.memo(({ 
  icon: Icon, 
  title, 
  color, 
  content 
}: { 
  icon: React.ComponentType<any>;
  title: string;
  color: string;
  content: string;
}) => (
  <div className="p-6 bg-gray-50 dark:bg-gray-800 rounded-lg">
    <h4 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
      <Icon className={`h-5 w-5 ${color}`} />
      {title}
    </h4>
    <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
      {content}
    </p>
  </div>
));

InsightCard.displayName = 'InsightCard';

// Optimized Market Insights Section
const MarketInsightsSection = React.memo(({ insight }: { insight: BackendInsight & { content: StructuredInsightContent } }) => {
  const insightsData = useMemo(() => [
    {
      icon: Users,
      title: "Customer Segments",
      color: "text-green-600",
      content: insight.content.emerging_key_insights.customer_segments
    },
    {
      icon: Factory,
      title: "Existing Solutions",
      color: "text-red-600",
      content: insight.content.emerging_key_insights.existing_solutions
    },
    {
      icon: MapPin,
      title: "Distribution Channels",
      color: "text-orange-600",
      content: insight.content.emerging_key_insights.distribution_channels
    },
    {
      icon: Scale,
      title: "Regulations & Compliance",
      color: "text-brand-500",
      content: insight.content.emerging_key_insights.regulations_policies
    },
    {
      icon: Scale,
      title: "Government Policies",
      color: "text-brand-500",
      content: insight.content.emerging_key_insights.government_policies
    },
    {
      icon: Scale,
      title: "Barriers to Consumption",
      color: "text-brand-500",
      content: insight.content.emerging_key_insights.barriers_consumption
    }
  ], [insight.content.emerging_key_insights]);


  return (
    <section className="mb-8">
      <div className="mb-4">

      <h2 className="text-xl font-bold text-brand-500 dark:text-brand-400  ">
       Emerging Key Insights
      </h2>

       <p className="text-sm text-brand-600 dark:text-gray-400 leading-relaxed italic">
        These are critical detais that resulted from this discovery, and are potential key pointers to your next steps
      </p>
      </div>

      <div className="space-y-6">
        <div className="grid md:grid-cols-2 gap-6">
          {insightsData.map((item, index) => (
            <InsightCard
              key={index}
              icon={item.icon}
              title={item.title}
              color={item.color}
              content={item.content}
            />
          ))}
        </div>
      </div>
    </section>
  );
});

MarketInsightsSection.displayName = 'MarketInsightsSection';

// Optimized List Item Component for repeated patterns
const ListItem = React.memo(({ 
  index, 
  content,
  bgColor = "bg-brand-500",
  textColor = "text-white",
  size = "xs"
}: { 
  index: number;
  content: string;
  bgColor?: string;
  textColor?: string;
  size?: "sm" | "xs";
}) => (
  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
    <div className="flex gap-3">
          <div className={`flex-shrink-0 w-6 h-6  bg-brand-100 dark:bg-brand-900/20 text-brand-500 dark:text-brand-400 rounded-full text-xs font-bold flex items-center justify-center mt-1`}>
        {index + 1}
      </div>
      <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">{content.replace(/^\d+\.\s+/, "")}</p>
    </div>
  </div>
));

ListItem.displayName = 'ListItem';

// Optimized Strategic Leverage Points Section
const StrategicLeverageSection = React.memo(({ insight }: { insight: BackendInsight & { content: StructuredInsightContent } }) => (
  <section className="mb-8">



    <div className="mb-4">

      <h2 className="text-xl font-bold text-brand-500 dark:text-brand-400  ">
      Leverage Points
      </h2>

       <p className="text-sm text-brand-600 dark:text-gray-400 leading-relaxed italic">
This refers to potential areas of intervention for your consideration, should you decide to solve for this problem      </p>
      </div>
    
    <div className="space-y-4">
      {insight.content.leverage_points.map((point, index) => (
        <ListItem
          key={index}
          index={index}
          content={point}
        />
      ))}
    </div>
  </section>
));

StrategicLeverageSection.displayName = 'StrategicLeverageSection';

// Optimized Critical Questions Section
const CriticalQuestionsSection = React.memo(({ insight }: { insight: BackendInsight & { content: StructuredInsightContent } }) => (
  <section className="mb-8">
    <div className="mb-4">

      <h2 className="text-xl font-bold text-brand-500 dark:text-brand-400  ">
      Key Questions for Founders
      </h2>

       <p className="text-sm text-brand-600 dark:text-gray-400 leading-relaxed italic">
Some key questions that may prove as a helpful guide going into the Value Proposition Design Module      </p>
      </div>
   
    <div className="space-y-3">
      {insight.content.key_questions_for_founders.map((question, index) => (
        <ListItem
          key={index}
          index={index}
          content={question}
        />
      ))}
    </div>
  </section>
));

CriticalQuestionsSection.displayName = 'CriticalQuestionsSection';

// Optimized Analysis Section Component
const AnalysisSection = React.memo(({ 
  section 
}: { 
  section: {
    icon: React.ComponentType<any>;
    title: string;
    description?: string;
    color: string;
    bgColor: string;
    textColor: string;
    items: string[];
  };
}) => (
  <div className="p-6 bg-gray-50 rounded-lg dark:bg-[#101828]  ">
    <h4 className="font-bold text-brand-500 dark:text-brand-400  flex items-center gap-2 text-xl">
      {/* <section.icon className={`h-4 w-4 ${section.color}`} /> */}
      {section.title}
    </h4>
    {section.description && (
      <p className="text-sm text-brand-600 dark:text-gray-400 mb-4 leading-relaxed italic">
        {section.description}
      </p>
    )}
    <div className="space-y-3">
      {section.items.map((item: string, index: number) => (
        <div key={index} className="flex gap-3">
          <div className={`flex-shrink-0 w-6 h-6  bg-brand-100 dark:bg-brand-900/20 text-brand-500 dark:text-brand-400 rounded-full text-xs font-bold flex items-center justify-center mt-1`}>
            {index + 1}
          </div>
          <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">{item.replace(/^\d+\.\s+/, "")}</p>
        </div>
      ))}
    </div>
  </div>
));

AnalysisSection.displayName = 'AnalysisSection';

// Optimized Industry & Geographic Analysis Section
const IndustryAnalysisSection = React.memo(({ insight }: { insight: BackendInsight & { content: StructuredInsightContent } }) => {
  const analysisSections = useMemo(() => [
    {
      icon: Shield,
      title: "Desirability Analysis",
      description: "Factual indicators that there indeed is need for the problem to de addressed",
      color: "text-brand-500",
      bgColor: "bg-brand-100 dark:bg-brand-900/20",
      textColor: "text-brand-500 dark:text-brand-400",
      items: insight.content.important_questions_industry_geography.desirability_analysis
    },
    {
      icon: Globe,
      title: "Recommended Areas for Further Research",
      description: "Some key aspects into which we strongly suggest you consider digging deeper for the next stages of your research",
      color: "text-green-600",
      bgColor: "bg-green-100 dark:bg-green-900/20",
      textColor: "text-green-600 dark:text-green-400",
      items: insight.content.important_questions_industry_geography.recommended_research_areas
    },
    {
      icon: Users,
      title: "Key Stakeholders & Institutions",
      description: "This highlights key stakeholders and institutions we recommend you engage early on as they are greatly relevant to this problem",
      color: "text-brand-500",
      bgColor: "bg-brand-100 dark:bg-brand-900/20",
      textColor: "text-brand-500 dark:text-brand-400",
      items: insight.content.important_questions_industry_geography.key_stakeholders_institutions
    }
  ], [insight.content.important_questions_industry_geography]);

  return (
    <section className="mb-8 dark:bg-[#101828]">
      {/* <h2 className="text-xl font-bold text-brand-500 dark:text-brand-400 mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
        1. Industry & Geographic Analysis
      </h2> */}
      <div className="space-y-6">
        {analysisSections.map((section, sectionIndex) => (
          <AnalysisSection key={sectionIndex} section={section} />
        ))}
      </div>
    </section>
  );
});

IndustryAnalysisSection.displayName = 'IndustryAnalysisSection';

// Optimized Structured Insight Component
const StructuredInsightDisplay = React.memo(({ insight }: { insight: BackendInsight & { content: StructuredInsightContent } }) => (
  <div className="space-y-8 dark:bg-[#101828]">
        <IndustryAnalysisSection insight={insight} />

    <MarketInsightsSection insight={insight} />
    <StrategicLeverageSection insight={insight} />
    <CriticalQuestionsSection insight={insight} />
  </div>
));

StructuredInsightDisplay.displayName = 'StructuredInsightDisplay';

// Optimized Empty State Component
const NoInsightsState = React.memo(({ onBack }: { onBack: () => void }) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
    <div className="text-center">
      <AlertTriangle className="h-16 w-16 text-yellow-500 mx-auto mb-4" />
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">No Insights Generated</h2>
      <p className="text-gray-600 dark:text-gray-400 mb-6">Unable to generate insights for this report.</p>
      <Button onClick={onBack} variant="outline">
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Results
      </Button>
    </div>
  </div>
));

NoInsightsState.displayName = 'NoInsightsState';





// Warning Message Component
const NoStructuredInsightsWarning = React.memo(() => (
  <div className="mb-8 p-6 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
    <div className="flex items-center gap-2 mb-2">
      <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
      <h3 className="font-semibold text-yellow-800 dark:text-yellow-200">No Structured Insights Available</h3>
    </div>
    <p className="text-yellow-700 dark:text-yellow-300 text-sm">
      Only chat messages are available for this report. Structured actionable insights may still be generating.
    </p>
  </div>
));

NoStructuredInsightsWarning.displayName = 'NoStructuredInsightsWarning';

// MAIN COMPONENT - FINAL OPTIMIZED VERSION
const ActionableInsights = React.memo(function ActionableInsights({ reportId: propReportId }: { reportId?: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Use prop reportId if provided, otherwise fall back to URL parameter
  const reportId = propReportId || searchParams.get('report_id');
  const { insights, actionableInsights, chatMessages, loading, error, refetch } = useInsights(reportId);

  console.log('ActionableInsights render:', { 
    reportId, 
    loading, 
    error, 
    hasInsights: !!insights,
    actionableCount: actionableInsights.length,
    chatCount: chatMessages.length 
  });

  const handleBackToReport = useCallback(() => {
    router.push(`/workspace/problem-validator/${reportId}/results`);
  }, [router, reportId]);

  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  // Memoized structured insights
  const structuredInsights = useMemo(() => 
    actionableInsights.filter(isStructuredInsight),
    [actionableInsights]
  );

  // Early returns for different states
  if (loading) {
    return (
      <div key="insights-loading" >
        <div className="container mx-auto px-4 py-8">
          <InsightsLoading />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div key="insights-error" >
        <div className="container mx-auto px-4 py-8">
          <InsightsError error={error} onRetry={handleRetry} onBack={handleBackToReport} />
        </div>
      </div>
    );
  }

  if (!insights || insights.insights.length === 0) {
    return (
      <div key="insights-empty" >
        <div className="container mx-auto px-4 py-8">
          <NoInsightsState onBack={handleBackToReport} />
        </div>
      </div>
    );
  }

  return (
    <div key="insights-content" >
      {/* Main Content */}
      <div className="max-w-6xl mx-auto dark:bg-[#101828]">
        <Card className="p-6 shadow-sm bg-white dark:bg-[#101828]">
          <div id="insights-content">
            {/* Show warning if no structured insights */}
            {structuredInsights.length === 0 && chatMessages.length > 0 && (
              <NoStructuredInsightsWarning />
            )}

            {/* Render structured insights first */}
            {structuredInsights.length > 0 && (
              <div className="mb-8 dark:bg-[#101828]">
                {structuredInsights.map((insight) => (
                  <StructuredInsightDisplay key={`insight-${insight.id}`} insight={insight} />
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
});

export default ActionableInsights;
