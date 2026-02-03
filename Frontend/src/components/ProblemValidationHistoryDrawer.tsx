"use client";

import React, { useState, useEffect, useCallback } from "react";
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
import { Separator } from "@/components/ui/separator";
import { 
  History, 
  FileText, 
  Calendar, 
  Eye, 
  Loader2, 
  AlertCircle,
  CheckCircle,
  RefreshCw
} from "lucide-react";

// Updated interfaces to match new backend structure
interface ValidationReport {
  id: string;
  tenant_id: string;
  project_id: string | null;
  source_type: string;
  title: string;
  storage_path: string | null;
  sha256: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  has_chat: boolean;
  is_recent: boolean;
  is_pinned: boolean;
  is_archived: boolean;
  view_count: number;
  tags: string[];
  metadata: {
    session_id: string;
    workflow_status: string;
  };
  content: null;
  actionable_insights: any[];
}

interface ValidationHistoryResponse {
  success: boolean;
  data: {
    reports: ValidationReport[];
    pagination: {
      current_page: number;
      page_size: number;
      total_count: number;
      total_pages: number;
      has_next: boolean;
      has_prev: boolean;
    };
    filters_applied: Record<string, any>;
    sort: {
      field: string;
      order: string;
    };
  };
  message: string;
  error: string | null;
}

interface ProblemValidationHistoryDrawerProps {
  trigger?: React.ReactNode;
  workspacePath?: string;
}

export default function ProblemValidationHistoryDrawer({ 
  trigger,
  workspacePath
}: ProblemValidationHistoryDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [reports, setReports] = useState<ValidationReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [navigating, setNavigating] = useState(false);
  
  const { token } = useAuthStore();
  const router = useRouter();

  // Cache utilities
  const getCachedReports = useCallback((): ValidationReport[] | null => {
    if (typeof window === 'undefined') return null;
    
    try {
      const cached = localStorage.getItem('validationHistoryReports');
      const timestamp = localStorage.getItem('validationHistoryReportsTimestamp');
      
      if (!cached || !timestamp) return null;
      
      // Check if cache is fresh (5 minutes)
      const isCacheFresh = Date.now() - parseInt(timestamp) < 5 * 60 * 1000;
      if (!isCacheFresh) {
        localStorage.removeItem('validationHistoryReports');
        localStorage.removeItem('validationHistoryReportsTimestamp');
        return null;
      }
      
      return JSON.parse(cached);
    } catch {
      // Clear corrupted cache
      localStorage.removeItem('validationHistoryReports');
      localStorage.removeItem('validationHistoryReportsTimestamp');
      return null;
    }
  }, []);

  const setCachedReports = useCallback((reports: ValidationReport[]) => {
    if (typeof window === 'undefined') return;
    
    try {
      localStorage.setItem('validationHistoryReports', JSON.stringify(reports));
      localStorage.setItem('validationHistoryReportsTimestamp', Date.now().toString());
    } catch (error) {
      console.error('Failed to cache reports:', error);
    }
  }, []);

  // Simplified fetch function with caching
  const fetchReports = useCallback(async (forceRefresh = false) => {
    if (!token) return;
    
    // Try to use cache first unless forcing refresh
    if (!forceRefresh) {
      const cachedReports = getCachedReports();
      if (cachedReports) {
        setReports(cachedReports);
        return;
      }
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(`${API_BASE_URL}/api/reports/history`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch reports: ${response.status}`);
      }

      const data: ValidationHistoryResponse = await response.json();
      const reports = data.data.reports || [];
      setReports(reports);
      setCachedReports(reports);
    } catch (err) {
      console.error('Error fetching validation history:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch reports');
    } finally {
      setLoading(false);
    }
  }, [token, getCachedReports, setCachedReports]);

  // Fetch reports when drawer opens
  useEffect(() => {
    if (isOpen && token) {
      fetchReports();
    }
  }, [isOpen, token, fetchReports]);

  // Handle report click navigation
  const handleReportClick = useCallback((reportId: string) => {
    // Close drawer immediately for snappier UX
    setIsOpen(false);
   
    const navigatingPath = `${workspacePath || '/team-workspace'}/problem-validator/${reportId}/results`;
    
    setNavigating(true);
    router.push(navigatingPath);
  }, [router, workspacePath]);

  // Format date helper
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
      
      if (diffInHours < 24) {
        const hours = Math.floor(diffInHours);
        return hours < 1 ? 'Just now' : `${hours}h ago`;
      } else {
        const days = Math.floor(diffInHours / 24);
        return days < 7 ? `${days}d ago` : date.toLocaleDateString();
      }
    } catch {
      return 'Unknown date';
    }
  };

  // Truncate text helper
  const truncateText = (text: string, maxLength: number = 80): string => {
    if (!text) return 'No summary available';
    return text.length <= maxLength ? text : `${text.substring(0, maxLength)}...`;
  };

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />;
      case 'processing':
        return <Loader2 className="h-4 w-4 text-blue-600 dark:text-blue-400 animate-spin" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />;
      default:
        return <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />;
    }
  };

  // Default trigger button
  const defaultTrigger = (
    <Button variant="outline" size="sm" className="gap-2 h-9 px-3 font-medium border-brand-200 dark:border-brand-700 hover:bg-brand-50 dark:hover:bg-brand-900/20">
      <History className="h-4 w-4 text-brand-500 dark:text-brand-400" />
      <span className="hidden sm:inline text-brand-500 dark:text-brand-400">History</span>
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
                onClick={() => fetchReports(true)} 
                className="gap-2 text-brand-500 dark:text-brand-400 hover:text-brand-600 dark:hover:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-800/30"
                disabled={loading}
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              Validation History
            </SheetTitle>
          </SheetHeader>

          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {/* Main Content Area - This is where scrolling should happen */}
            <div className="flex-1 overflow-hidden p-2 bg-background dark:bg-gray-900/30">
              {loading && reports.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="flex flex-col items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-900/50 border border-brand-200 dark:border-brand-700">
                      <Loader2 className="h-5 w-5 animate-spin text-brand-500 dark:text-brand-400" />
                    </div>
                    <div className="space-y-1 text-center">
                      <p className="text-sm font-medium text-brand-600 dark:text-brand-300">Loading reports</p>
                      <p className="text-xs text-muted-foreground dark:text-brand-400">Please wait while we fetch your validation history</p>
                    </div>
                  </div>
                </div>
              ) : error ? (
                <div className="flex flex-col items-center justify-center h-full space-y-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800">
                    <AlertCircle className="h-6 w-6 text-red-500 dark:text-red-400" />
                  </div>
                  <div className="space-y-2 text-center">
                    <p className="text-sm font-medium text-brand-600 dark:text-brand-300">Failed to load reports</p>
                    <p className="text-xs text-muted-foreground dark:text-brand-400 max-w-[280px]">{error}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => fetchReports(true)} className="gap-2 border-brand-200 dark:border-brand-700 hover:bg-brand-50 dark:hover:bg-brand-900/20">
                    <RefreshCw className="h-3.5 w-3.5" />
                    Try Again
                  </Button>
                </div>
              ) : reports.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full space-y-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted dark:bg-gray-800/50 border border-border dark:border-brand-700">
                    <FileText className="h-6 w-6 text-muted-foreground dark:text-brand-400" />
                  </div>
                  <div className="space-y-2 text-center">
                    <p className="text-sm font-medium text-brand-600 dark:text-brand-300">No reports yet</p>
                    <p className="text-xs text-muted-foreground dark:text-brand-400 max-w-[280px]">
                      Start your first problem validation to see reports appear here
                    </p>
                  </div>
                </div>
              ) : (
                <ScrollArea className="h-full pr-2">
                  <div className="space-y-3 pr-2">
                    {reports.map((report) => (
                      <div key={report.id}>
                        <div
                          className="group relative rounded-lg border bg-card dark:bg-gray-800/50 p-4 transition-all duration-200 hover:bg-brand-50 dark:hover:bg-brand-900/20 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-sm cursor-pointer border-border dark:border-brand-700/50"
                          onClick={() => handleReportClick(report.id)}
                        >
                          <div className="space-y-2">
                            {/* Header with title and badges */}
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <h4 className="font-semibold text-sm line-clamp-2 text-brand-600 dark:text-brand-200 group-hover:text-brand-700 dark:group-hover:text-brand-100 transition-colors">
                                  {report.title || 'Untitled Report'}
                                </h4>
                                
                              </div>
                              <div className="shrink-0">
                                {getStatusIcon(report.metadata?.workflow_status)}
                              </div>
                            </div>

                            {/* Footer - Metadata */}
                            <div className="flex items-center justify-between pt-2 border-t border-border dark:border-brand-700/50">
                              <div className="flex items-center gap-3 text-xs text-muted-foreground dark:text-brand-400">
                                <div className="flex items-center gap-1">
                                  <Calendar className="h-3 w-3" />
                                  <span>{formatDate(report.created_at)}</span>
                                </div>
                                {report.view_count > 0 && (
                                  <div className="flex items-center gap-1">
                                    <Eye className="h-3 w-3" />
                                    <span>{report.view_count}</span>
                                  </div>
                                )}
                              </div>
                              <div className="text-xs text-muted-foreground dark:text-brand-400">
                                {report.metadata?.workflow_status ? 
                                  report.metadata.workflow_status.charAt(0).toUpperCase() + 
                                  report.metadata.workflow_status.slice(1) : 
                                  'Completed'}
                              </div>
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