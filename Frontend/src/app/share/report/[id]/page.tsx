"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  AlertTriangle,
  FileText,
  RefreshCw,
  ExternalLink,
  Lock,
  Share2
} from "lucide-react";
import { fetchSharedReport } from "@/lib/api/reportService";

// Interfaces
interface SourceItem {
  number?: number;
  source_url: string;
  source_title?: string;
  credibility_score?: number;
  publication_date?: string;
}

interface SharedReportData {
  success: boolean;
  share: {
    id: string;
    share_token: string;
    session_id: string;
    is_public: boolean;
    password_protected: boolean;
    expires_at: string | null;
    view_count: number;
    created_at: string;
    share_url: string;
  };
  report: {
    id: string;
    title: string;
    summary: string;
    report_type: string;
    created_at: string;
    updated_at: string;
    content: {
      title: string;
      executive_summary: string;
      industry_analysis: string;
      challenges_analysis: string;
      recommendations: string;
      sources: SourceItem[];
      tenant_id?: string;
    };
  };
  message: string;
}

// Optimized Markdown Renderer Component
const MarkdownRenderer = React.memo(({ 
  content, 
  className = "" 
}: { 
  content: string;
  className?: string;
}) => {
  const processedContent = useMemo(() => content, [content]);

  return (
    <div className={`prose dark:prose-invert max-w-none text-gray-700 dark:text-gray-300 ${className}`}>
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]} 
        rehypePlugins={[rehypeRaw]}
        components={{
          h1: ({node, ...props}) => <h2 className="text-2xl font-bold mt-6 mb-4 text-gray-900 dark:text-white" {...props} />,
          h2: ({node, ...props}) => <h3 className="text-xl font-semibold mt-5 mb-3 text-gray-900 dark:text-white" {...props} />,
          h3: ({node, ...props}) => <h4 className="text-lg font-medium mt-4 mb-2 text-gray-900 dark:text-white" {...props} />,
          p: ({node, ...props}) => <p className="mb-4 leading-relaxed" {...props} />,
          ul: ({node, ...props}) => <ul className="list-disc list-outside pl-16 mb-4 space-y-2" style={{listStyleType: 'disc'}} {...props} />,
          ol: ({node, ...props}) => <ol className="list-decimal list-outside pl-16 mb-4 space-y-2" style={{listStyleType: 'decimal'}} {...props} />,
          li: ({node, ...props}) => <li className="mb-1" style={{display: 'list-item'}} {...props} />,
          a: ({node, href, ...props}) => {
            const isInternal = href?.startsWith('#') ?? false;
            const isSourceHref = href?.startsWith('#source-') ?? false;
            const hasDataSource = (node?.properties as any)?.['data-source'];
            const isCitation = isSourceHref || hasDataSource;
            
            const handleCitationClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
              if (!isCitation) return;

              e.preventDefault();

              let targetId: string | null = null;
              if (hasDataSource) {
                const sourceNumber = (node?.properties as any)?.['data-source'];
                targetId = `source-${sourceNumber}`;
              } else if (isSourceHref && href) {
                targetId = href.replace('#', '');
              }

              if (!targetId) return;

              const targetElement = document.getElementById(targetId) as HTMLElement | null;

              if (targetElement) {
                const sourceUrl = targetElement.dataset?.sourceUrl;

                if (sourceUrl && sourceUrl !== '#') {
                  window.open(sourceUrl, '_blank', 'noopener,noreferrer');
                  return;
                }

                targetElement.scrollIntoView({ behavior: 'smooth' });
              }
            };
          
            return (
              <a 
                href={href}
                className={`${isCitation ? 'text-blue-600 dark:text-blue-400' : 'text-brand-500 dark:text-brand-400'} font-bold hover:underline flex items-center gap-1`} 
                {...(isInternal ? {} : { target: "_blank", rel: "noopener noreferrer" })}
                onClick={isCitation ? handleCitationClick : undefined}
                {...props}
              >
                {props.children}
                {!isInternal && !isCitation && <ExternalLink className="h-3 w-3" />}
              </a>
            );
          },
          strong: ({node, ...props}) => <strong className="font-semibold text-gray-900 dark:text-white" {...props} />,
          code: ({node, inline, ...props}) => 
            inline ? (
              <code className="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
            ) : (
              <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto my-4">
                <code className="text-sm font-mono" {...props} />
              </pre>
            ),
          blockquote: ({node, ...props}) => (
            <blockquote className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic my-4 text-gray-600 dark:text-gray-300" {...props} />
          ),
          table: ({node, ...props}) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700" {...props} />
            </div>
          ),
          thead: ({node, ...props}) => <thead className="bg-gray-50 dark:bg-gray-800" {...props} />,
          tbody: ({node, ...props}) => <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700" {...props} />,
          th: ({node, ...props}) => <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider" {...props} />,
          td: ({node, ...props}) => <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300" {...props} />,
          hr: ({node, ...props}) => <hr className="my-6 border-gray-200 dark:border-gray-700" {...props} />,
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
});

MarkdownRenderer.displayName = 'MarkdownRenderer';

// Loading Component
const LoadingSpinner = React.memo(({ message = "Loading shared report..." }: { message?: string }) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
    <div className="text-center">
      <div className="rounded-full h-12 w-12 border-2 border-t-brand-500 border-r-brand-500 border-b-brand-100 border-l-brand-100 mx-auto mb-4 animate-spin" />
      <p className="text-gray-600 dark:text-gray-400">{message}</p>
    </div>
  </div>
));

LoadingSpinner.displayName = 'LoadingSpinner';

// Error Display Component
const ErrorDisplay = React.memo(({ 
  error, 
  onRetry 
}: { 
  error: string; 
  onRetry?: () => void;
}) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
    <div className="text-center max-w-md px-4">
      <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        Unable to Load Report
      </h2>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        {error}
      </p>
      <div className="flex gap-3 justify-center">
        {onRetry && (
          <Button onClick={onRetry} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        )}
        <Button onClick={() => window.location.href = '/'}>
          Go Home
        </Button>
      </div>
    </div>
  </div>
));

ErrorDisplay.displayName = 'ErrorDisplay';

// Source Item Component
const SourceItem = React.memo(({ 
  source, 
  index 
}: { 
  source: SourceItem; 
  index: number;
}) => {
  const [isValidUrl, setIsValidUrl] = useState(true);
  
  const handleLinkError = useCallback(() => {
    setIsValidUrl(false);
  }, []);

  const formatUrl = useCallback((url: string) => {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname.replace('www.', '');
    } catch {
      return url.length > 30 ? url.substring(0, 30) + '...' : url;
    }
  }, []);

  const getCredibilityColor = useCallback((score?: number) => {
    if (!score) return 'text-brand-500';
    if (score >= 8) return 'text-green-500';
    if (score >= 6) return 'text-yellow-500';
    return 'text-red-500';
  }, []);

  return (
    <div
      id={`source-${index + 1}`}
      data-source-url={source.source_url}
      className="flex gap-3 p-3 bg-brand-50 dark:bg-brand-900/10 rounded-lg hover:bg-brand-100 dark:hover:bg-brand-900/20 transition-colors"
    >
      <div className="shrink-0 w-6 h-6 bg-brand-100 dark:bg-brand-900/20 rounded-full flex items-center justify-center text-xs font-medium text-brand-700 dark:text-brand-300">
        {source.number ?? index + 1}
      </div>
      <div className="flex-1 min-w-0">
        <a
          href={isValidUrl ? source.source_url : '#'}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 hover:underline block truncate"
          onError={handleLinkError}
          onClick={(e) => !isValidUrl && e.preventDefault()}
        >
          {source.source_title || 'Untitled Source'}
        </a>
        <div className="flex items-center justify-between mt-1">
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate flex-1">
            {formatUrl(source.source_url)}
          </p>
          {source.credibility_score && (
            <span className={`text-xs font-medium ${getCredibilityColor(source.credibility_score)}`}>
              Score: {source.credibility_score}/10
            </span>
          )}
        </div>
        {source.publication_date && (
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            Published: {new Date(source.publication_date).toLocaleDateString()}
          </p>
        )}
      </div>
    </div>
  );
});

SourceItem.displayName = 'SourceItem';

// Main Public Report Page Component
export default function PublicReportPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = React.use(params);
  
  const [reportData, setReportData] = useState<SharedReportData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requiresPassword, setRequiresPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [isSubmittingPassword, setIsSubmittingPassword] = useState(false);
  
  const router = useRouter();

  // Fetch shared report data using share token
  const fetchReport = useCallback(async (passwordAttempt?: string) => {
    if (!resolvedParams?.id) {
      setError('Share token is required');
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const data = await fetchSharedReport(resolvedParams.id, passwordAttempt);
      
      setReportData(data);
      setRequiresPassword(false);
    } catch (err: any) {
      console.error('Error fetching shared report:', err);
      
      // Check if password is required
      if (err.message?.includes('password') || err.message?.includes('Password required')) {
        setRequiresPassword(true);
        setError(null);
      } else {
        setError(err.message || 'An unexpected error occurred');
      }
    } finally {
      setIsLoading(false);
      setIsSubmittingPassword(false);
    }
  }, [resolvedParams?.id]);

  // Handle password submission
  const handlePasswordSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) return;
    
    setIsSubmittingPassword(true);
    await fetchReport(password);
  }, [password, fetchReport]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // Process content to add inline citation links
  const processContentWithCitations = useCallback((content: string) => {
    if (!content) return '';
    
    let processedContent = content.replace(
      /\[(\d+)\]/g, 
      '<a href="#source-$1" data-source="$1" class="citation-link text-blue-600 dark:text-blue-400 font-semibold">[$1]</a>'
    );
    
    processedContent = processedContent.replace(/^\s*•\s+(.+)$/gm, '* $1');
    
    return processedContent;
  }, []);

  // Memoized computed values - updated for new response structure
  const report = useMemo(() => reportData?.report, [reportData]);
  const content = useMemo(() => report?.content, [report]);
  const sources = useMemo(() => (content?.sources || []) as SourceItem[], [content?.sources]);

  // Memoized source items
  const sourceItems = useMemo(() => 
    sources.map((source, index) => (
      <SourceItem key={`source-${index}-${source.source_url}`} source={source} index={index} />
    )), [sources]
  );

  // Copy share link
  const copyShareLink = useCallback(() => {
    const shareUrl = window.location.href;
    navigator.clipboard.writeText(shareUrl);
    // Could add toast notification here
  }, []);

  // Loading state
  if (isLoading) {
    return <LoadingSpinner />;
  }

  // Password required state
  if (requiresPassword) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <Card className="max-w-md w-full p-8 shadow-lg bg-white dark:bg-gray-800">
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <Lock className="h-8 w-8 text-brand-500" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Password Protected
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              This report requires a password to view.
            </p>
          </div>
          
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div>
              <Input
                type="password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full"
                disabled={isSubmittingPassword}
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-brand-500 hover:bg-brand-600"
              disabled={isSubmittingPassword || !password.trim()}
            >
              {isSubmittingPassword ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Verifying...
                </>
              ) : (
                'View Report'
              )}
            </Button>
          </form>
        </Card>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <ErrorDisplay 
        error={error} 
        onRetry={() => fetchReport()}
      />
    );
  }

  // No data state
  if (!reportData || !content) {
    return (
      <ErrorDisplay 
        error="Report data is not available."
        onRetry={() => fetchReport()}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Public Report Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-brand-500 rounded-lg flex items-center justify-center">
                <FileText className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Shared Report
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Generated on {report?.created_at ? new Date(report.created_at).toLocaleDateString() : 'Unknown'}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={copyShareLink}
                className="hidden sm:flex"
              >
                <Share2 className="h-4 w-4 mr-2" />
                Copy Link
              </Button>
              <Button
                size="sm"
                onClick={() => router.push('/signin')}
                className="bg-brand-500 hover:bg-brand-600"
              >
                <Lock className="h-4 w-4 mr-2" />
                Sign In for More
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Report Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        <Card className="p-8 shadow-md bg-white dark:bg-gray-800">
          <h1 className="text-4xl font-bold text-brand-500 dark:text-brand-400 mb-6 leading-tight">
            {content?.title || 'Market Validation Report'}
          </h1>

          {/* Executive Summary */}
          {content?.executive_summary && (
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                1. Executive Summary
              </h2>
              <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                <MarkdownRenderer 
                  content={processContentWithCitations(content.executive_summary)} 
                />
              </div>
            </section>
          )}

          {/* Industry Analysis Section */}
          {content?.industry_analysis && (
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                2. Industry Analysis
              </h2>
              <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                <MarkdownRenderer 
                  content={processContentWithCitations(content.industry_analysis)} 
                />
              </div>
            </section>
          )}

          {/* PESTLE Analysis & Challenges */}
          {content?.challenges_analysis && (
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                3. PESTLE Analysis & Market Challenges
              </h2>
              <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                <MarkdownRenderer 
                  content={processContentWithCitations(content.challenges_analysis)} 
                />
              </div>
            </section>
          )}

          {/* Strategic Recommendations */}
          {content?.recommendations && (
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                4. Strategic Recommendations
              </h2>
              <div className="space-y-4">
                <MarkdownRenderer 
                  content={processContentWithCitations(content.recommendations)} 
                />
              </div>
            </section>
          )}

          {/* References Section */}
          {sources.length > 0 && (
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                5. References
              </h2>
              <div className="space-y-4">
                {sourceItems}
              </div>
            </section>
          )}
        </Card>

        {/* CTA Section */}
        <div className="mt-8 text-center">
          <Card className="p-8 bg-gradient-to-r from-brand-50 to-brand-100 dark:from-brand-900/20 dark:to-brand-800/20 border-brand-200 dark:border-brand-700">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Want to create your own validation reports?
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Sign up for free and start validating your business ideas with AI-powered market research.
            </p>
            <div className="flex gap-3 justify-center">
              <Button
                variant="outline"
                onClick={() => router.push('/signin')}
              >
                Sign In
              </Button>
              <Button
                onClick={() => router.push('/signup')}
                className="bg-brand-500 hover:bg-brand-600"
              >
                Get Started Free
              </Button>
            </div>
          </Card>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-12">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Powered by Yuba - AI-Powered Market Validation
            </p>
            <div className="flex gap-4">
              <a href="/" className="text-sm text-brand-500 hover:text-brand-600">
                Learn More
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
