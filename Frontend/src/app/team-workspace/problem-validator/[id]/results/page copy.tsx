"use client";

import React, { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { 
  Card 
} from "@/components/ui/card";
import { 
  Button 
} from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { 
  useUser, 
  useIsAuthenticated, 
  useIsLoading, 
  useToken, 
  useIsInitialized, 
  useInitializeAuth 
} from "@/stores/authStore";
import { 
  ReportResponse,
  ReportContent 
} from "@/types/validation";
import { fetchReport, createReportShare, type BackendReportData } from "@/lib/api/reportService";
import toast from "react-hot-toast";
import html2canvas from 'html2canvas';
import { 
  jsPDF 
} from 'jspdf';
import ActionableInsights from '../insights/page';
import { 
  ScrollArea 
} from "@/components/ui/scroll-area";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogFooter 
} from "@/components/ui/dialog";
import { 
  Label 
} from "@/components/ui/label";
import { 
  Input 
} from "@/components/ui/input";
import { 
  Textarea 
} from "@/components/ui/textarea";
import { 
  ArrowLeft, 
  AlertTriangle,
  Lightbulb,
  FileText,
  RefreshCw,
  ExternalLink,
  MessageCircle,
  X,
  Send,
  ArrowRight,
  Share2,
  Copy,
  Check,
  Twitter,
  Linkedin,
  Mail
} from "lucide-react";
import FeatureVideoOverlay from "@/components/feature-videos/FeatureVideoOverlay";
import { FEATURE_IDS, getFeatureVideoConfig } from "@/lib/featureVideos";

// Enhanced Interfaces
interface EnhancedValidationResultsData {
  report: ReportResponse;
  sessionId: string;
  generatedAt?: string;
  problemStatement?: string;
  reportId?: string;
}

interface PDFExportState {
  isExporting: boolean;
  progress: number;
  error: string | null;
}

interface ShareModalState {
  isOpen: boolean;
  copied: boolean;
  isCreating: boolean;
  shareUrl: string | null;
  error: string | null;
}

interface SourceItem {
  number?: number;
  source_url: string;
  source_title?: string;
  credibility_score?: number;
  publication_date?: string;
}

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

// Optimized Chat Markdown Renderer Component
const ChatMarkdownRenderer = React.memo(({ 
  content 
}: { 
  content: string;
}) => {
  // Memoize the content processing to prevent unnecessary re-renders
  const processedContent = useMemo(() => content, [content]);

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:mt-2 prose-headings:mb-2 prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5">
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({node, ...props}) => <h3 className="text-base font-semibold mt-3 mb-2 text-gray-900 dark:text-white" {...props} />,
          h2: ({node, ...props}) => <h4 className="text-sm font-medium mt-2 mb-1 text-gray-900 dark:text-white" {...props} />,
          h3: ({node, ...props}) => <h5 className="text-sm font-medium mt-2 mb-1 text-gray-900 dark:text-white" {...props} />,
          p: ({node, ...props}) => <p className="my-1 text-sm leading-relaxed" {...props} />,
          ul: ({node, ...props}) => <ul className="list-disc list-outside pl-4 my-1 space-y-0.5" {...props} />,
          ol: ({node, ...props}) => <ol className="list-decimal list-outside pl-4 my-1 space-y-0.5" {...props} />,
          li: ({node, ...props}) => <li className="my-0.5 text-sm" {...props} />,
          a: ({node, href, ...props}) => (
            <a 
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500 hover:text-blue-600 underline text-sm" 
              {...props}
            />
          ),
          strong: ({node, ...props}) => <strong className="font-semibold text-gray-900 dark:text-white" {...props} />,
          em: ({node, ...props}) => <em className="italic" {...props} />,
          code: ({node, ...props}) => {
            const isInline = !props.className?.includes('language-');
            return isInline ? (
              <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded text-xs font-mono" {...props} />
            ) : (
              <pre className="bg-gray-100 dark:bg-gray-700 p-2 rounded my-2 overflow-x-auto">
                <code className="text-xs font-mono" {...props} />
              </pre>
            );
          },
          blockquote: ({node, ...props}) => (
            <blockquote className="border-l-3 border-gray-300 dark:border-gray-600 pl-3 italic my-2 text-sm text-gray-600 dark:text-gray-300" {...props} />
          ),
          table: ({node, ...props}) => (
            <div className="overflow-x-auto my-2">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm" {...props} />
            </div>
          ),
          thead: ({node, ...props}) => <thead className="bg-gray-50 dark:bg-gray-800" {...props} />,
          tbody: ({node, ...props}) => <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700" {...props} />,
          th: ({node, ...props}) => <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider" {...props} />,
          td: ({node, ...props}) => <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300" {...props} />,
          hr: ({node, ...props}) => <hr className="my-2 border-gray-200 dark:border-gray-700" {...props} />,
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
});

ChatMarkdownRenderer.displayName = 'ChatMarkdownRenderer';

// Optimized Chatbot Drawer Component
const ChatbotDrawer = React.memo(({ 
  isOpen, 
  onClose,
  reportId 
}: { 
  isOpen: boolean;
  onClose: () => void;
  reportId: string | null;
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chatSessionId] = useState(() => `chat_session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  
  // Enhanced Zustand authentication
  const token = useToken();

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim() || !reportId || !token) return;

    // Abort previous request if exists
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      abortControllerRef.current = new AbortController();
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          report_id: reportId,
          content: inputMessage.trim(),
          web_search_enabled: false,
          chat_session_id: chatSessionId
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: ChatResponse = await response.json();

      if (data.success) {
        const assistantMessage: ChatMessage = {
          id: data.id || `assistant_${Date.now()}`,
          role: 'assistant',
          content: data.content,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        throw new Error(data.error || 'Failed to get response from AI');
      }
    } catch (error: any) {
      // Ignore abort errors
      if (error.name === 'AbortError') return;
      
      console.error('Chat API error:', error);
      const errorMessage: ChatMessage = {
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: error.message.includes('Network') 
          ? '**Network Error**: Failed to connect to AI service. Please try again.'
          : `**Error**: ${error.message || 'Failed to get response from AI'}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      toast.error(error.message || 'Failed to get AI response');
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [inputMessage, reportId, chatSessionId, token]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  // Memoized message list to prevent unnecessary re-renders
  const messageList = useMemo(() => 
    messages.map((message) => (
      <div
        key={message.id}
        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
      >
        <div
          className={`max-w-[85%] rounded-lg px-3 py-2 ${
            message.role === 'user'
              ? 'bg-brand-500 text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
          }`}
        >
          {message.role === 'user' ? (
            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
          ) : (
            <ChatMarkdownRenderer content={message.content} />
          )}
          <div
            className={`text-xs mt-1 ${
              message.role === 'user'
                ? 'text-brand-100'
                : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        </div>
      </div>
    )), [messages]
  );

  return (
    <div className={`fixed inset-0 z-50 ${isOpen ? 'block' : 'hidden'}`}>
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-brand-500/80 opacity-25"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className={`absolute right-0 top-0 h-full w-96 bg-white dark:bg-gray-800 shadow-2xl transform transition-transform duration-300 ease-in-out ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-brand-500 rounded-full flex items-center justify-center">
              <MessageCircle className="h-4 w-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">Chat with Report</h3>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={clearChat}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              disabled={messages.length === 0}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Messages Container */}
        <div className="flex-1 h-[calc(100%-8rem)] overflow-hidden">
          <ScrollArea className="h-full p-4">
            {messages.length === 0 ? (
              <div className="text-center py-8">
                <MessageCircle className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">Start a conversation</h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Ask questions about your validation report and get AI-powered insights.
                </p>
                <div className="mt-4 text-xs text-gray-400 dark:text-gray-500">
                  <p>Try asking:</p>
                  <ul className="mt-2 space-y-1">
                    <li>• "Summarize the key findings"</li>
                    <li>• "What are the main recommendations?"</li>
                    <li>• "Explain the market challenges"</li>
                  </ul>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {messageList}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="max-w-[85%] rounded-lg px-3 py-2 bg-gray-100 dark:bg-gray-700">
                      <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                        <div className="flex gap-1">
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                        thinking...
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </ScrollArea>
        </div>

        {/* Input Area */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex gap-2">
            <Input
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              disabled={isLoading || !reportId}
              className="flex-1"
            />
            <Button
              onClick={sendMessage}
              disabled={isLoading || !inputMessage.trim() || !reportId}
              size="sm"
              className="bg-brand-500 hover:bg-brand-600"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          {!reportId && (
            <p className="text-xs text-red-500 mt-2">Report ID is required for chat</p>
          )}
        </div>
      </div>
    </div>
  );
});

ChatbotDrawer.displayName = 'ChatbotDrawer';

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

              // Prefer explicit data-source if present, otherwise derive from href (#source-5)
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

                // Fallback: keep the original smooth scroll behavior
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
          code: ({node, className, ...props}) => {
            const isInline = !className;
            return isInline ? (
              <code className="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
            ) : (
              <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto my-4">
                <code className="text-sm font-mono" {...props} />
              </pre>
            );
          },
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

// Loading Component with performance optimization
const LoadingSpinner = React.memo(({ message = "Loading validation results..." }: { message?: string }) => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center">
      <div className="rounded-full h-12 w-12 border-2 border-t-brand-500 border-r-brand-500 border-b-brand-100 border-l-brand-100 mx-auto mb-4 animate-spin" />
      <p className="text-gray-600 dark:text-gray-400">{message}</p>
    </div>
  </div>
));

LoadingSpinner.displayName = 'LoadingSpinner';

// Error Display Component with memoization
const ErrorDisplay = React.memo(({ 
  error, 
  onRetry 
}: { 
  error: string; 
  onRetry?: () => void;
}) => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center max-w-md">
      <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        Unable to Load Results
      </h2>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        {error}
      </p>
      <div className="flex gap-3 justify-center">
        <Button onClick={() => window.location.reload()} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
        <Button onClick={() => window.history.back()}>
          Go Back
        </Button>
      </div>
    </div>
  </div>
));

ErrorDisplay.displayName = 'ErrorDisplay';

// Optimized Source Item Component
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

// Enhanced PDF Export Hook with better error handling and cleanup
const usePDFExport = () => {
  const [exportState, setExportState] = useState<PDFExportState>({
    isExporting: false,
    progress: 0,
    error: null
  });

  const exportToPdf = useCallback(async (element: HTMLElement, filename: string) => {
    if (!element) {
      setExportState({ isExporting: false, progress: 0, error: 'No element to export' });
      return false;
    }

    try {
      setExportState({ isExporting: true, progress: 0, error: null });

      // Hide export-exclude elements
      const elementsToHide = element.querySelectorAll('.export-exclude');
      const originalStyles: { element: Element; display: string }[] = [];
      
      elementsToHide.forEach(el => {
        originalStyles.push({ element: el, display: (el as HTMLElement).style.display });
        (el as HTMLElement).style.display = 'none';
      });

      // Update progress
      setExportState(prev => ({ ...prev, progress: 30 }));

      // Create canvas with better quality but reasonable limits
      const canvas = await html2canvas(element, {
        scale: 1.5, // Reduced from 2 to improve performance
        useCORS: true,
        logging: false,
        scrollY: -window.scrollY,
        removeContainer: true, // Clean up temporary containers
        onclone: (clonedDoc) => {
          const clonedElement = clonedDoc.getElementById(element.id);
          if (clonedElement) {
            clonedElement.style.width = '210mm';
            clonedElement.style.padding = '20mm';
          }
        }
      });

      setExportState(prev => ({ ...prev, progress: 70 }));

      // Create PDF
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4'
      });

      const imgData = canvas.toDataURL('image/png', 0.9); // Slightly reduced quality for performance
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
      
      setExportState(prev => ({ ...prev, progress: 90 }));

      // Save PDF
      pdf.save(`${filename}.pdf`);

      // Restore original styles
      elementsToHide.forEach((el, index) => {
        (el as HTMLElement).style.display = originalStyles[index]?.display || '';
      });

      // Clean up canvas
      if (canvas.parentNode) {
        canvas.parentNode.removeChild(canvas);
      }

      setExportState({ isExporting: false, progress: 100, error: null });
      
      return true;
    } catch (error) {
      console.error('PDF export error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Export failed';
      setExportState({ isExporting: false, progress: 0, error: errorMessage });
      return false;
    }
  }, []);

  return { exportState, exportToPdf };
};

// Main Component with Enhanced Authentication
export default function ValidationResults({ params }: { params: Promise<{ id: string }> }) {
  // Unwrap params Promise using React.use()
  const resolvedParams = React.use(params);
  const featureConfig = getFeatureVideoConfig(FEATURE_IDS.PROBLEM_VALIDATOR);
  
  const [validationData, setValidationData] = useState<EnhancedValidationResultsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'report' | 'insights'>('report');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isFooterHighlighted, setIsFooterHighlighted] = useState(false);
  const [showFloatingButtons, setShowFloatingButtons] = useState(false);
  const [showTopButton, setShowTopButton] = useState(true);
  const [shareModal, setShareModal] = useState<ShareModalState>({ isOpen: false, copied: false, isCreating: false, shareUrl: null, error: null });
  const reportRef = useRef<HTMLDivElement>(null);
  const footerRef = useRef<HTMLDivElement>(null);
  const lastScrollY = useRef(0);
  const scrollTimeout = useRef<NodeJS.Timeout | null>(null);
  
  const router = useRouter();
  const { exportState, exportToPdf } = usePDFExport();
  const abortControllerRef = useRef<AbortController | null>(null);
  
  // Enhanced Zustand authentication
  const user = useUser();
  const isAuthenticated = useIsAuthenticated();
  const authLoading = useIsLoading();
  const isInitialized = useIsInitialized();
  const token = useToken();
  const initializeAuth = useInitializeAuth();

  // Initialize authentication on component mount
  useEffect(() => {
    const init = async () => {
      try {
        console.log('ValidationResults: Initializing auth...');
        await initializeAuth();
        console.log('ValidationResults: Auth initialized');
      } catch (error) {
        console.error('ValidationResults: Auth initialization failed:', error);
      }
    }
    
    if (!isInitialized) {
      init();
    }
  }, [initializeAuth, isInitialized]);

  // Debug logging for authentication state
  useEffect(() => {
    console.log('ValidationResults Auth State:', {
      isInitialized,
      authLoading,
      isAuthenticated,
      hasUser: !!user,
      hasToken: !!token
    });
  }, [isInitialized, authLoading, isAuthenticated, user, token]);

  // Redirect to signin if not authenticated after initialization
  useEffect(() => {
    if (isInitialized && !authLoading && !isAuthenticated) {
      console.log('ValidationResults: User not authenticated, redirecting to signin');
      router.push('/signin');
    }
  }, [isInitialized, authLoading, isAuthenticated, router]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Enhanced data initialization with backend API fetching
  const initializeData = useCallback(async () => {
    // Wait for authentication to be ready
    if (!isInitialized || authLoading) {
      return;
    }

    if (!isAuthenticated || !token) {
      setError('Authentication required');
      return;
    }

    if (!resolvedParams?.id) {
      setError('Report ID is required');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Abort previous request if exists
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();

      console.log('ValidationResults: Fetching report data from backend', {
        reportId: resolvedParams.id,
        hasToken: !!token
      });

      // Fetch report data using the service
      const backendData: BackendReportData = await fetchReport(resolvedParams.id, token);

      // Transform backend data to match existing component structure
      const transformedData: EnhancedValidationResultsData = {
        report: {
          session_id: `session_${Date.now()}`,
          report_id: backendData.report_id || backendData.data.id,
          query: backendData.data.title,
          title: backendData.data.title,
          executive_summary: backendData.data.content.executive_summary,
          sections: [],
          report: {
            title: backendData.data.content.title,
            executive_summary: backendData.data.content.executive_summary,
            industry_analysis: backendData.data.content.industry_analysis,
            challenges_analysis: backendData.data.content.challenges_analysis,
            recommendations: backendData.data.content.recommendations,
            sources: (backendData.data.content.sources || []).map((source, index) => ({
              number: source.number || index + 1,
              source_url: source.source_url,
              source_title: source.source_title || 'Untitled Source'
            })),
            tenant_id: backendData.data.content.tenant_id || '',
          },
          status: 'completed',
          generated_at: backendData.data.created_at,
          generation_time_seconds: null,
          word_count: null,
          quality_score: null,
        },
        sessionId: `session_${Date.now()}`,
        reportId: backendData.report_id || backendData.data.id,
      };

      console.log('ValidationResults: Data transformed successfully', {
        hasReport: !!transformedData.report,
        reportId: transformedData.reportId,
        title: transformedData.report.title,
        sourcesCount: transformedData.report.report.sources?.length || 0
      });

      setValidationData(transformedData);

    } catch (err: any) {
      // Ignore abort errors
      if (err.name === 'AbortError') return;
      
      console.error('Error fetching validation results:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load validation results';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [isInitialized, authLoading, isAuthenticated, token, resolvedParams?.id]);

  useEffect(() => {
    initializeData();
  }, [initializeData]);

  // Scroll detection for floating buttons (opposite behaviors)
  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      const scrollingDown = currentScrollY > lastScrollY.current;
      const scrollingUp = currentScrollY < lastScrollY.current;
      
      // Clear existing timeout
      if (scrollTimeout.current) {
        clearTimeout(scrollTimeout.current);
      }
      
      // Bottom buttons: Show when scrolling down, hide when scrolling up
      if (scrollingDown && currentScrollY > 200) {
        setShowFloatingButtons(true);
        setShowTopButton(false); // Hide top button when scrolling down
      } else if (scrollingUp) {
        setShowFloatingButtons(false);
        setShowTopButton(true); // Show top button when scrolling up
      }
      
      // Hide top button when at the very top
      if (currentScrollY < 100) {
        setShowTopButton(true);
      }
      
      // Update last scroll position
      lastScrollY.current = currentScrollY;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    
    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (scrollTimeout.current) {
        clearTimeout(scrollTimeout.current);
      }
    };
  }, []);

  // Enhanced report ID getter with better fallback logic
  const getReportId = useCallback((data?: EnhancedValidationResultsData) => {
    const targetData = data || validationData;
    if (!targetData) {
      console.log('ValidationResults: No validation data available for report ID');
      return null;
    }

    const reportId = targetData.reportId || 
                     targetData.report?.report_id ||
                     null;

    console.log('ValidationResults: Report ID extraction:', {
      reportId,
      hasReportId: !!targetData.reportId,
      hasReportReportId: !!targetData.report?.report_id
    });

    return reportId;
  }, [validationData]);

// Enhanced project creation with proper error handling and debugging
const createNewProject = useCallback(async () => {
  // Input validation
  if (!projectName.trim()) {
    toast.error('Project name is required');
    return;
  }

  // Authentication validation
  if (!isAuthenticated || !token) {
    toast.error('Authentication required. Please sign in again.');
    router.push('/signin');
    return;
  }

  // Report ID validation
  const reportId = getReportId();
  if (!reportId) {
    toast.error('Report ID is missing. Cannot create project without validation report.');
    return;
  }

  console.log('=== PROJECT CREATION START ===');
  console.log('Project Details:', {
    name: projectName.trim(),
    reportId,
    hasToken: !!token,
    tokenLength: token?.length || 0
  });

  setIsCreatingProject(true);

  try {
    // Prepare request payload
    const requestPayload = {
      name: projectName.trim(),
      pv_report_id: reportId
    };

    console.log('Request Payload:', requestPayload);
    console.log('API Endpoint: ${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects');

    // Make API request
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
      body: JSON.stringify(requestPayload),
    });

    console.log('Response Status:', response.status);
    console.log('Response Headers:', {
      contentType: response.headers.get('content-type'),
      contentLength: response.headers.get('content-length'),
    });

    // Get response body
    const responseText = await response.text();
    console.log('Raw Response Body:', responseText);

    // Parse JSON response
    let responseData;
    try {
      responseData = responseText ? JSON.parse(responseText) : {};
      console.log('Parsed Response Data:', responseData);
    } catch (parseError) {
      console.error('JSON Parse Error:', parseError);
      throw new Error(`Invalid JSON response from server: ${responseText.substring(0, 100)}...`);
    }

    // Handle HTTP errors
    if (!response.ok) {
      console.error('HTTP Error Response:', {
        status: response.status,
        statusText: response.statusText,
        body: responseData
      });

      // Handle specific error cases
      if (response.status === 400) {
        // Handle duplicate name constraint
        if (responseData.detail && typeof responseData.detail === 'string') {
          if (responseData.detail.includes('duplicate key value violates unique constraint') ||
              responseData.detail.includes('unique_tenant_project_name')) {
            throw new Error('A project with this name already exists in your workspace. Please choose a different name.');
          }
        }
        
        // Handle other validation errors
        const errorMsg = responseData.detail || responseData.message || 'Invalid request. Please check your input.';
        throw new Error(errorMsg);
      }
      
      if (response.status === 401) {
        throw new Error('Your session has expired. Please sign in again.');
      }
      
      if (response.status === 403) {
        throw new Error('You do not have permission to create projects.');
      }
      
      if (response.status === 404) {
        throw new Error('Validation report not found. Please generate a new validation report.');
      }
      
      if (response.status === 422) {
        const errorMsg = responseData.detail || responseData.message || 'Validation failed. Please check your input.';
        throw new Error(errorMsg);
      }
      
      if (response.status >= 500) {
        throw new Error('Server error occurred. Please try again in a few moments.');
      }
      
      // Generic error for other status codes
      const errorMsg = responseData.message || responseData.detail || `Request failed with status ${response.status}`;
      throw new Error(errorMsg);
    }

    // Validate successful response structure
    console.log('Validating response structure...');
    
    if (!responseData.success) {
      console.error('Response indicates failure:', responseData);
      throw new Error(responseData.message || 'Project creation failed - server returned unsuccessful response');
    }

    if (!responseData.data) {
      console.error('Missing data field in response:', responseData);
      throw new Error('Invalid response format - missing data field');
    }

    if (!responseData.data.project) {
      console.error('Missing project field in response data:', responseData.data);
      throw new Error('Invalid response format - missing project information');
    }

    if (!responseData.data.project.id) {
      console.error('Missing project ID in response:', responseData.data.project);
      throw new Error('Invalid response format - missing project ID');
    }

    // Extract project information
    const project = responseData.data.project;
    const projectId = project.id;
    const nextStep = responseData.data.next_step;
    const message = responseData.message;

    console.log('=== PROJECT CREATION SUCCESS ===');
    console.log('Project Created:', {
      id: projectId,
      name: project.name,
      status: project.status,
      currentStep: project.current_step,
      createdAt: project.created_at,
      nextStep,
      message
    });

    // Show success message
    toast.success('Project created successfully!');
    
    // Reset form state
    setProjectName('');
    setIsModalOpen(false);
    
    // Navigate to personas
    console.log('Navigating to personas with project ID:', projectId);
    
    // Small delay to ensure UI updates complete
    setTimeout(() => {
      router.push(`/team-workspace/projects/${projectId}`);
    }, 500);

  } catch (error: any) {
    console.error('=== PROJECT CREATION ERROR ===');
    console.error('Error Details:', {
      name: error.name,
      message: error.message,
      stack: error.stack?.substring(0, 500)
    });
    
    // Determine user-friendly error message
    let userMessage = 'Failed to create project';
    
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      userMessage = 'Network error. Please check your internet connection and try again.';
    } else if (error.message.includes('JSON')) {
      userMessage = 'Server response error. Please try again or contact support if the issue persists.';
    } else if (error.message.includes('duplicate') || error.message.includes('already exists')) {
      userMessage = error.message;
    } else if (error.message.includes('session has expired') || error.message.includes('Authentication')) {
      userMessage = error.message;
      // Redirect to login after showing error
      setTimeout(() => {
        router.push('/signin');
      }, 2000);
    } else if (error.message.includes('permission')) {
      userMessage = error.message;
    } else if (error.message.includes('not found')) {
      userMessage = error.message;
    } else if (error.message) {
      userMessage = error.message;
    }
    
    toast.error(userMessage);
  } finally {
    setIsCreatingProject(false);
    console.log('=== PROJECT CREATION END ===');
  }
}, [projectName, isAuthenticated, token, getReportId, router]);

  // Process content to add inline citation links with memoization
  const processContentWithCitations = useCallback((content: string) => {
    if (!content) return '';
    
    let processedContent = content.replace(
      /\[(\d+)\]/g, 
      '<a href="#source-$1" data-source="$1" class="citation-link text-blue-600 dark:text-blue-400 font-semibold">[$1]</a>'
    );
    
    processedContent = processedContent.replace(/^\s*•\s+(.+)$/gm, '* $1');
    
    return processedContent;
  }, []);

  // Memoized computed values - extract ReportContent from the nested structure
  const reportData = useMemo<ReportContent | undefined>(() => 
    validationData?.report?.report ?? (validationData?.report as unknown as ReportContent),
    [validationData]
  );

  const sources = useMemo(() => 
    (reportData?.sources as SourceItem[]) || [],
    [reportData]
  );

  // Memoized source items to prevent unnecessary re-renders
  const sourceItems = useMemo(() => 
    sources.map((source, index) => (
      <SourceItem key={`source-${index}-${source.source_url}`} source={source} index={index} />
    )), [sources]
  );

  // Navigation handlers
  const handleBackToValidator = useCallback(() => {
    router.push('/team-workspace/problem-validator');
  }, [router]);

  const handleNewValidation = useCallback(() => {
    router.push('/team-workspace/problem-validator');
  }, [router]);

  // Chatbot handlers
  const openChatbot = useCallback(() => {
    setIsChatOpen(true);
  }, []);

  const closeChatbot = useCallback(() => {
    setIsChatOpen(false);
  }, []);

  // Modal handlers
  const openCreateProjectModal = useCallback(() => {
    setIsModalOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setIsModalOpen(false);
    setProjectName('');
  }, []);

  // Sticky Downward Arrow Button with footer highlight
  const scrollToFooter = useCallback(() => {
    // Use instant scroll for a snappier experience
    footerRef.current?.scrollIntoView({ behavior: 'auto', block: 'start' });

    // Briefly highlight the footer section for better UX
    setIsFooterHighlighted(true);
    setTimeout(() => {
      setIsFooterHighlighted(false);
    }, 1200);
  }, []);

  // Share functionality handlers
  const openShareModal = useCallback(async () => {
    const sessionId = validationData?.sessionId;
    if (!sessionId || !token) {
      toast.error('Unable to create share link');
      return;
    }

    setShareModal({ isOpen: true, copied: false, isCreating: true, shareUrl: null, error: null });

    try {
      const response = await createReportShare(
        { session_id: sessionId, is_public: true },
        token
      );
      
      setShareModal(prev => ({
        ...prev,
        isCreating: false,
        shareUrl: response.share.share_url,
      }));
    } catch (err: any) {
      console.error('Failed to create share link:', err);
      setShareModal(prev => ({
        ...prev,
        isCreating: false,
        error: err.message || 'Failed to create share link',
      }));
      toast.error(err.message || 'Failed to create share link');
    }
  }, [validationData?.sessionId, token]);

  const closeShareModal = useCallback(() => {
    setShareModal({ isOpen: false, copied: false, isCreating: false, shareUrl: null, error: null });
  }, []);

  const copyShareLink = useCallback(async () => {
    const shareUrl = shareModal.shareUrl;
    if (!shareUrl) {
      toast.error('No share link available');
      return;
    }
    try {
      await navigator.clipboard.writeText(shareUrl);
      setShareModal(prev => ({ ...prev, copied: true }));
      toast.success('Link copied to clipboard!');
      setTimeout(() => setShareModal(prev => ({ ...prev, copied: false })), 3000);
    } catch (err) {
      toast.error('Failed to copy link');
    }
  }, [shareModal.shareUrl]);

  const shareViaEmail = useCallback(() => {
    const shareUrl = shareModal.shareUrl;
    if (!shareUrl) return;
    const title = reportData?.title || 'Market Validation Report';
    const subject = encodeURIComponent(`Check out this report: ${title}`);
    const body = encodeURIComponent(`I wanted to share this market validation report with you:\n\n${title}\n\n${shareUrl}`);
    window.open(`mailto:?subject=${subject}&body=${body}`, '_blank');
  }, [shareModal.shareUrl, reportData?.title]);

  const shareViaTwitter = useCallback(() => {
    const shareUrl = shareModal.shareUrl;
    if (!shareUrl) return;
    const title = reportData?.title || 'Market Validation Report';
    const text = encodeURIComponent(`Check out this market validation report: ${title}`);
    window.open(`https://twitter.com/intent/tweet?text=${text}&url=${encodeURIComponent(shareUrl)}`, '_blank');
  }, [shareModal.shareUrl, reportData?.title]);

  const shareViaLinkedIn = useCallback(() => {
    const shareUrl = shareModal.shareUrl;
    if (!shareUrl) return;
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`, '_blank');
  }, [shareModal.shareUrl]);

  // Loading and error states
  if (!isInitialized || authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="rounded-full h-12 w-12 border-2 border-t-brand-500 border-r-brand-500 border-b-brand-100 border-l-brand-100 mx-auto mb-4 animate-spin" />
          <p className="text-gray-600 dark:text-gray-400">Initializing authentication...</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error && !validationData) {
    return (
      <ErrorDisplay 
        error={error} 
        onRetry={initializeData}
      />
    );
  }

  if (!validationData) {
    return (
      <ErrorDisplay 
        error="We couldn't find your validation results. Please try starting a new validation session."
        onRetry={() => router.push('/team-workspace/problem-validator')}
      />
    );
  }

  return (
    <div className="bg-white dark:bg-[#101828]">
      {/* <FeatureVideoOverlay
        featureId={FEATURE_IDS.PROBLEM_VALIDATOR}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      /> */}
      {/* Floating Top CTA Button - Show on scroll up, hide on scroll down */}
      <div 
        className={`fixed top-18 right-8 z-40 transition-all duration-300 ease-in-out ${
          showTopButton ? 'translate-y-0 opacity-100' : '-translate-y-[200%] opacity-0'
        }`}
      >
      <Button
        variant="default"
        onClick={openCreateProjectModal}
        className="shadow-lg bg-green-600 hover:bg-green-700 rounded-lg h-10 px-8 flex items-center justify-center gap-2 hover:scale-105 transition-transform"
        aria-label="Advance to module 2"
      >
        <span className="text-sm font-medium whitespace-nowrap">Advance to Module 2</span>
        <ArrowRight className="h-4 w-4" />
      </Button>
    </div>

    {/* Header */}
    <div 
  className="sticky top-0 z-50 -mt-4  max-w-2xl mx-auto " 
  
>
  <div className="max-w-2xl mx-auto px-4 py-2">

        <div className="flex flex-col md:flex-row items-center justify-between ">
  {/* <Button
    variant="ghost"
    size="sm"
    onClick={handleBackToValidator}
    className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 whitespace-nowrap"
  >
    <ArrowLeft className="h-4 w-4 mr-1 sm:mr-2" />
    <span className="hidden sm:inline">Back</span>
    <span className="sm:hidden">Back</span>
  </Button> */}
  
  <div className="flex-1 flex justify-center">
    <div className="flex items-center border border-gray-200 dark:border-gray-700 rounded-lg p-1 bg-gray-50 dark:bg-gray-800 shadow-sm">
    <Button 
  variant={activeTab === 'report' ? 'default' : 'ghost'}
  onClick={() => setActiveTab('report')}
  className={`w-64 relative flex items-center justify-center gap-3 px-16 py-3 text-base rounded-md transition-all duration-200 ${
    activeTab === 'report' 
      ? 'bg-brand-500 dark:bg-gray-900 shadow-sm text-white dark:text-brand-400' 
      : 'text-brand-500 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
  }`}
>
  <FileText className={`h-5 w-5 transition-transform ${
    activeTab === 'report' ? 'scale-110' : 'scale-100'
  }`} />
  <span className="font-semibold">Report</span>
  {activeTab === 'report' && (
    <span className="absolute -bottom-1 left-1/2 w-5 h-0.5 bg-brand-500 -translate-x-1/2 rounded-full"></span>
  )}
</Button>

<Button 
  variant={activeTab === 'insights' ? 'default' : 'ghost'}
  onClick={() => setActiveTab('insights')}
  className={`w-64 relative flex items-center justify-center gap-3 px-16 py-3 text-base rounded-md transition-all duration-200 ${
    activeTab === 'insights' 
      ? 'bg-brand-500 dark:bg-gray-900 shadow-sm text-white dark:text-brand-400' 
      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
  }`}
>
  <Lightbulb className={`h-5 w-5 transition-transform ${
    activeTab === 'insights' ? 'scale-110' : 'scale-100'
  }`} />
  <span className="font-semibold">Insights</span>
  {activeTab === 'insights' && (
    <span className="absolute -bottom-1 left-1/2 w-5 h-0.5 bg-brand-500 -translate-x-1/2 rounded-full"></span>
  )}
</Button>
    </div>
  </div>
  
  {/* This empty div balances the flex layout, keeping the tabs centered */}
  <div className="w-24"></div>
</div>
        </div>
      </div>

      {/* Main Report Content */}
      {activeTab === 'report' ? (
        <div key="report-tab" className="max-w-6xl mx-auto  bg-white dark:bg-gray-900 min-h-screen">
          <Card className="p-8 shadow-md">
            <div ref={reportRef} id="report-content">
              <div className="flex items-start justify-between mb-6">
                <h1 className="text-4xl font-bold text-brand-500 dark:text-brand-400 leading-tight flex-1">
                  {reportData?.title || 'Market Validation Report'}
                </h1>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={openShareModal}
                  className="ml-4 flex items-center gap-2 text-gray-600 hover:text-brand-600 dark:text-gray-400 dark:hover:text-brand-400"
                >
                  <Share2 className="h-4 w-4" />
                  Share
                </Button>
              </div>

              {/* Executive Summary */}
              {reportData?.executive_summary && (
                <section className="mb-12">
                  <h2 className="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                    1. Executive Summary
                  </h2>
                  <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                    <MarkdownRenderer 
                      content={processContentWithCitations(reportData.executive_summary)} 
                      className="pdf-content" 
                    />
                  </div>
                </section>
              )}

              {/* Industry Analysis Section */}
              {reportData?.industry_analysis && (
                <section className="mb-12 page-break">
                  <h2 className="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                    2. Industry Analysis
                  </h2>
                  <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                    <MarkdownRenderer 
                      content={processContentWithCitations(reportData.industry_analysis)} 
                      className="pdf-content" 
                    />
                  </div>
                </section>
              )}

              {/* PESTLE Analysis & Challenges */}
              {reportData?.challenges_analysis && (
                <section className="mb-12 page-break">
                  <h2 className="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                  3. PESTLE Analysis & Market Challenges
                  </h2>
                  <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                    <MarkdownRenderer 
                      content={processContentWithCitations(reportData.challenges_analysis)} 
                      className="pdf-content" 
                    />
                  </div>
                </section>
              )}

              {/* Strategic Recommendations */}
              {reportData?.recommendations && (
                <section className="mb-12 page-break avoid-break">
                  <h2 className="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                  4. Strategic Recommendations
                  </h2>
                  <div className="space-y-4">
                    <MarkdownRenderer 
                      content={processContentWithCitations(reportData.recommendations)} 
                      className="pdf-content" 
                    />
                  </div>
                </section>
              )}

              {/* References Section */}
              {sources.length > 0 && (
                <section className="mb-12 page-break">
                  <h2 className="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                  5. References
                  </h2>
                  <div className="space-y-4">
                    {sourceItems}
                  </div>
                </section>
              )}
            </div>
          </Card>
        </div>
      ) : (
        <div key="insights-tab" className="max-w-6xl mx-auto  bg-white dark:bg-gray-900 min-h-screen">
          <ActionableInsights reportId={getReportId() ?? undefined} />
        </div>
      )}

      {/* Floating Footer Buttons - Show on scroll down, hide on scroll up */}
      <div 
        className={`fixed bottom-0 left-0 right-0 z-30 transition-transform duration-300 ease-in-out ${
          showFloatingButtons ? 'translate-y-0' : 'translate-y-full'
        }`}
      >
        <div className="flex items-center justify-center py-4 bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm border-t border-brand-100 dark:border-brand-800 shadow-lg">
          <div className="flex gap-4 justify-center px-4">
            <Button variant="outline" onClick={handleBackToValidator}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Validator
            </Button>
            <Button onClick={openCreateProjectModal} className="bg-green-600 hover:bg-green-700">
              Advance to module 2
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Sticky Chat Button */}
      <div className="fixed bottom-8 right-8 z-40">
        <Button 
          onClick={openChatbot} 
          className="bg-brand-500 text-white hover:bg-brand-600 shadow-lg transition-all duration-300 hover:scale-105 flex items-center justify-center p-4 rounded-full h-14 w-14"
          aria-label="Chat with AI"
        >
          <MessageCircle className="h-6 w-6" />
          <span className="sr-only">Chat with AI</span>
        </Button>
      </div>

      {/* Chatbot Drawer */}
      <ChatbotDrawer 
        isOpen={isChatOpen}
        onClose={closeChatbot}
        reportId={getReportId()}
      />

      {/* Create Project Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle><span className="text-brand-500">Create a Project </span></DialogTitle>
            <p className="text-gray-500 text-sm">Create a project to explore this report further in the next module</p>
          </DialogHeader>
          <div className="grid gap-4 ">
            <div className="grid gap-2">
              <Label htmlFor="project-name">
                Project Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="project-name"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Enter project name"
                disabled={isCreatingProject}
                required
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeModal} disabled={isCreatingProject}>
              Cancel
            </Button>
            <Button 
              onClick={createNewProject} 
              disabled={isCreatingProject || !projectName.trim()}
              className="bg-brand-600 hover:bg-brand-700"
            >
              {isCreatingProject ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Project'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Share Modal */}
      <Dialog open={shareModal.isOpen} onOpenChange={(open) => !open && closeShareModal()}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Share2 className="h-5 w-5 text-brand-500" />
              <span>Share Report</span>
            </DialogTitle>
            <p className="text-gray-500 text-sm">Share this report with others. Anyone with the link can view it.</p>
          </DialogHeader>
          
          <div className="space-y-4">
            {shareModal.isCreating ? (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="h-6 w-6 animate-spin text-brand-500 mr-2" />
                <span className="text-gray-600">Creating share link...</span>
              </div>
            ) : shareModal.error ? (
              <div className="flex items-center justify-center py-8 text-red-500">
                <AlertTriangle className="h-5 w-5 mr-2" />
                <span>{shareModal.error}</span>
              </div>
            ) : shareModal.shareUrl ? (
              <>
                {/* Copy Link Section */}
                <div className="flex items-center gap-2">
                  <Input
                    value={shareModal.shareUrl}
                    readOnly
                    className="flex-1 bg-gray-50 dark:bg-gray-800"
                  />
                  <Button
                    onClick={copyShareLink}
                    variant={shareModal.copied ? "default" : "outline"}
                    className={shareModal.copied ? "bg-green-600 hover:bg-green-700" : ""}
                  >
                    {shareModal.copied ? (
                      <>
                        <Check className="h-4 w-4 mr-2" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4 mr-2" />
                        Copy
                      </>
                    )}
                  </Button>
                </div>

                {/* Social Share Buttons */}
                <div className="border-t pt-4">
                  <p className="text-sm text-gray-500 mb-3">Or share via</p>
                  <div className="flex gap-3">
                    <Button
                      variant="outline"
                      onClick={shareViaEmail}
                      className="flex-1 flex items-center justify-center gap-2"
                    >
                      <Mail className="h-4 w-4" />
                      Email
                    </Button>
                    <Button
                      variant="outline"
                      onClick={shareViaTwitter}
                      className="flex-1 flex items-center justify-center gap-2"
                    >
                      <Twitter className="h-4 w-4" />
                      Twitter
                    </Button>
                    <Button
                      variant="outline"
                      onClick={shareViaLinkedIn}
                      className="flex-1 flex items-center justify-center gap-2"
                    >
                      <Linkedin className="h-4 w-4" />
                      LinkedIn
                    </Button>
                  </div>
                </div>
              </>
            ) : null}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeShareModal}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}