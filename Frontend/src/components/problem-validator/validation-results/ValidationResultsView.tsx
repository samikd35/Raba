"use client";

import React, { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
    useUser,
    useIsAuthenticated,
    useIsLoading,
    useToken,
    useIsInitialized,
    useInitializeAuth
} from "@/stores/authStore";
import { useSidebar } from "@/context/SidebarContext";
import { fetchReport, downloadReportPdf, type BackendReportData } from "@/lib/api/reportService";
import toast from "react-hot-toast";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
    ArrowLeft,
    Lightbulb,
    FileText,
    RefreshCw,
    MessageCircle,
    ArrowRight,
    Share2,
    ArrowUp,
    Download
} from "lucide-react";

import {
    EnhancedValidationResultsData,
    ValidationResultsViewProps,
    ReportContent,
    SourceItem as SourceItemType
} from "./types";
import { LoadingSpinner } from "./LoadingSpinner";
import { ErrorDisplay } from "./ErrorDisplay";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { SourceItem } from "./SourceItem";
import { ChatbotDrawer } from "./ChatbotDrawer";
import { ShareReportModal } from "./ShareReportModal";
import { usePDFExport } from "./usePDFExport";
import FeatureVideoOverlay from "@/components/feature-videos/FeatureVideoOverlay";
import { FEATURE_IDS, getFeatureVideoConfig } from "@/lib/featureVideos";

export const ValidationResultsView = ({
    params,
    workspaceType,
    basePath,
    ActionableInsightsComponent
}: ValidationResultsViewProps) => {
    const resolvedParams = React.use(params);
    const { isExpanded } = useSidebar();
    const featureConfig = getFeatureVideoConfig(FEATURE_IDS.PROBLEM_VALIDATOR);

    const [validationData, setValidationData] = useState<EnhancedValidationResultsData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'report' | 'insights'>('report');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [projectName, setProjectName] = useState('');
    const [isCreatingProject, setIsCreatingProject] = useState(false);
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [showFloatingButtons, setShowFloatingButtons] = useState(false);
    const [showTopButton, setShowTopButton] = useState(true);
    const [showBackToTop, setShowBackToTop] = useState(false);
    const [isShareModalOpen, setIsShareModalOpen] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);
    const reportRef = useRef<HTMLDivElement>(null);
    const footerRef = useRef<HTMLDivElement>(null);
    const lastScrollY = useRef(0);
    const scrollTimeout = useRef<NodeJS.Timeout | null>(null);

    const router = useRouter();
    const { exportState, exportToPdf } = usePDFExport();
    const abortControllerRef = useRef<AbortController | null>(null);

    const user = useUser();
    const isAuthenticated = useIsAuthenticated();
    const authLoading = useIsLoading();
    const isInitialized = useIsInitialized();
    const token = useToken();
    const initializeAuth = useInitializeAuth();

    // Compute navigation paths based on workspaceType
    const problemValidatorPath = `${basePath}/problem-validator`;
    const projectsPath = `${basePath}/projects`;

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

    useEffect(() => {
        console.log('ValidationResults Auth State:', {
            isInitialized,
            authLoading,
            isAuthenticated,
            hasUser: !!user,
            hasToken: !!token
        });
    }, [isInitialized, authLoading, isAuthenticated, user, token]);

    useEffect(() => {
        if (isInitialized && !authLoading && !isAuthenticated) {
            console.log('ValidationResults: User not authenticated, redirecting to signin');
            router.push('/signin');
        }
    }, [isInitialized, authLoading, isAuthenticated, router]);

    useEffect(() => {
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    const initializeData = useCallback(async () => {
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

            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }

            abortControllerRef.current = new AbortController();

            console.log('ValidationResults: Fetching report data from backend', {
                reportId: resolvedParams.id,
                hasToken: !!token
            });

            const backendData: BackendReportData = await fetchReport(resolvedParams.id, token);

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

        } catch (err: unknown) {
            if (err instanceof Error && err.name === 'AbortError') return;

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

    useEffect(() => {
        const handleScroll = () => {
            const currentScrollY = window.scrollY;
            const scrollingDown = currentScrollY > lastScrollY.current;
            const scrollingUp = currentScrollY < lastScrollY.current;

            if (scrollTimeout.current) {
                clearTimeout(scrollTimeout.current);
            }

            if (scrollingDown && currentScrollY > 200) {
                setShowFloatingButtons(true);
                setShowTopButton(false);
            } else if (scrollingUp) {
                setShowFloatingButtons(false);
                setShowTopButton(true);
            }

            if (currentScrollY < 100) {
                setShowTopButton(true);
            }

            setShowBackToTop(currentScrollY > 300);

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

    const getReportId = useCallback((data?: EnhancedValidationResultsData) => {
        const targetData = data || validationData;
        if (!targetData) {
            console.log('ValidationResults: No validation data available for report ID');
            return null;
        }

        const reportId = targetData.reportId ||
            targetData.report?.report_id ||
            null;

        return reportId;
    }, [validationData]);

    const createNewProject = useCallback(async () => {
        if (!projectName.trim()) {
            toast.error('Project name is required');
            return;
        }

        if (!isAuthenticated || !token) {
            toast.error('Authentication required. Please sign in again.');
            router.push('/signin');
            return;
        }

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
            const requestPayload = {
                name: projectName.trim(),
                pv_report_id: reportId
            };

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json',
                },
                body: JSON.stringify(requestPayload),
            });

            const responseText = await response.text();

            let responseData;
            try {
                responseData = responseText ? JSON.parse(responseText) : {};
            } catch {
                console.error('JSON Parse Error');
                throw new Error(`Invalid JSON response from server: ${responseText.substring(0, 100)}...`);
            }

            if (!response.ok) {
                console.error('HTTP Error Response:', {
                    status: response.status,
                    statusText: response.statusText,
                    body: responseData
                });

                if (response.status === 400) {
                    if (responseData.detail && typeof responseData.detail === 'string') {
                        if (responseData.detail.includes('duplicate key value violates unique constraint') ||
                            responseData.detail.includes('unique_tenant_project_name')) {
                            throw new Error('A project with this name already exists in your workspace. Please choose a different name.');
                        }
                    }
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

                const errorMsg = responseData.message || responseData.detail || `Request failed with status ${response.status}`;
                throw new Error(errorMsg);
            }

            if (!responseData.success) {
                throw new Error(responseData.message || 'Project creation failed - server returned unsuccessful response');
            }

            if (!responseData.data?.project?.id) {
                throw new Error('Invalid response format - missing project information');
            }

            const project = responseData.data.project;
            const projectId = project.id;

            console.log('=== PROJECT CREATION SUCCESS ===');
            toast.success('Project created successfully!');

            setProjectName('');
            setIsModalOpen(false);

            setTimeout(() => {
                router.push(`${projectsPath}/${projectId}`);
            }, 500);

        } catch (error: unknown) {
            console.error('=== PROJECT CREATION ERROR ===');

            let userMessage = 'Failed to create project';

            if (error instanceof Error) {
                if (error.name === 'TypeError' && error.message.includes('fetch')) {
                    userMessage = 'Network error. Please check your internet connection and try again.';
                } else if (error.message.includes('JSON')) {
                    userMessage = 'Server response error. Please try again or contact support if the issue persists.';
                } else if (error.message.includes('duplicate') || error.message.includes('already exists')) {
                    userMessage = error.message;
                } else if (error.message.includes('session has expired') || error.message.includes('Authentication')) {
                    userMessage = error.message;
                    setTimeout(() => {
                        router.push('/signin');
                    }, 2000);
                } else if (error.message) {
                    userMessage = error.message;
                }
            }

            toast.error(userMessage);
        } finally {
            setIsCreatingProject(false);
            console.log('=== PROJECT CREATION END ===');
        }
    }, [projectName, isAuthenticated, token, getReportId, router, projectsPath]);

    const processContentWithCitations = useCallback((content: string) => {
        if (!content) return '';

        let processedContent = content.replace(
            /\[(\d+)\]/g,
            '<a href="#source-$1" data-source="$1" class="citation-link text-blue-600 dark:text-blue-400 font-semibold">[$1]</a>'
        );

        processedContent = processedContent.replace(/^\s*•\s+(.+)$/gm, '* $1');

        return processedContent;
    }, []);

    const handleDownloadReport = async () => {
        const reportId = getReportId();
        if (!reportId || !token) {
            toast.error("Unable to download: Missing report information");
            return;
        }

        setIsDownloading(true);
        try {
            console.log("Starting PDF download for report:", reportId);
            const blob = await downloadReportPdf(reportId, token);

            // Create object URL and download
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Yuba_Report_${(reportData?.title || 'Validation').replace(/[^a-z0-9]/gi, '_').substring(0, 50)}.pdf`;
            document.body.appendChild(a);
            a.click();

            // Cleanup
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            toast.success("Report downloaded successfully!");
        } catch (error) {
            console.error("Download error:", error);
            toast.error(error instanceof Error ? error.message : "Failed to download report");
        } finally {
            setIsDownloading(false);
        }
    };

    const reportData = useMemo(() => {
        const reportContent: ReportContent | null = validationData?.report?.report as ReportContent | null;
        return reportContent || null;
    }, [validationData]);

    const sources = useMemo(() =>
        (reportData?.sources as SourceItemType[]) || [],
        [reportData?.sources]
    );

    const sourceItems = useMemo(() =>
        sources.map((source, index) => (
            <SourceItem key={`source-${index}-${source.source_url}`} source={source} index={index} />
        )), [sources]
    );

    const handleBackToValidator = useCallback(() => {
        router.push(problemValidatorPath);
    }, [router, problemValidatorPath]);

    const scrollToTop = useCallback(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }, []);

    const openChatbot = useCallback(() => {
        setIsChatOpen(true);
    }, []);

    const closeChatbot = useCallback(() => {
        setIsChatOpen(false);
    }, []);

    const openCreateProjectModal = useCallback(() => {
        setIsModalOpen(true);
    }, []);

    const closeModal = useCallback(() => {
        setIsModalOpen(false);
        setProjectName('');
    }, []);

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
                onRetry={() => router.push(problemValidatorPath)}
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
                buttonClassName="bottom-28 right-8"
            /> */}
            {/* Back to Top Button */}
            <div
                className={`fixed right-8 top-1/2 -translate-y-1/2 z-40 transition-all duration-300 ease-in-out ${showBackToTop ? 'translate-x-0 opacity-100' : 'translate-x-20 opacity-0 pointer-events-none'}`}
            >
                <Button
                    variant="default"
                    size="icon"
                    onClick={scrollToTop}
                    className="rounded-full shadow-lg w-10 h-10"
                    aria-label="Back to top"
                >
                    <ArrowUp className="h-5 w-5 text-white" />
                </Button>
            </div>

            {/* Floating Top CTA Button */}
            <div
                className={`fixed top-18 right-8 z-40 transition-all duration-300 ease-in-out ${showTopButton ? 'translate-y-0 opacity-100' : '-translate-y-[200%] opacity-0'}`}
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
            <div className="sticky top-0 z-50 -mt-4 max-w-xl mx-auto">
                <div className="max-w-xl mx-auto px-4 py-2">
                    <div className="flex flex-col md:flex-row items-center justify-between">
                        <div className="flex-1 flex justify-center">
                            <div className="flex items-center border border-gray-200 dark:border-gray-700 rounded-lg p-1 bg-gray-50 dark:bg-gray-800 shadow-sm">
                                <Button
                                    variant={activeTab === 'report' ? 'default' : 'ghost'}
                                    onClick={() => setActiveTab('report')}
                                    className={`w-46 relative flex items-center justify-center gap-3 px-16 py-3 text-base rounded-md transition-all duration-200 ${activeTab === 'report'
                                        ? 'bg-brand-500 dark:bg-gray-900 shadow-sm text-white dark:text-brand-400'
                                        : 'text-brand-500 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                                        }`}
                                >
                                    <FileText className={`h-5 w-5 transition-transform ${activeTab === 'report' ? 'scale-110' : 'scale-100'}`} />
                                    <span className="font-semibold">Report</span>
                                    {activeTab === 'report' && (
                                        <span className="absolute -bottom-1 left-1/2 w-5 h-0.5 bg-brand-500 -translate-x-1/2 rounded-full"></span>
                                    )}
                                </Button>

                                <Button
                                    variant={activeTab === 'insights' ? 'default' : 'ghost'}
                                    onClick={() => setActiveTab('insights')}
                                    className={`w-46 relative flex items-center justify-center gap-3 px-16 py-3 text-base rounded-md transition-all duration-200 ${activeTab === 'insights'
                                        ? 'bg-brand-500 dark:bg-gray-900 shadow-sm text-white dark:text-brand-400'
                                        : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                                        }`}
                                >
                                    <Lightbulb className={`h-5 w-5 transition-transform ${activeTab === 'insights' ? 'scale-110' : 'scale-100'}`} />
                                    <span className="font-semibold">Insights</span>
                                    {activeTab === 'insights' && (
                                        <span className="absolute -bottom-1 left-1/2 w-5 h-0.5 bg-brand-500 -translate-x-1/2 rounded-full"></span>
                                    )}
                                </Button>
                            </div>
                        </div>

                        <div className="w-24"></div>
                    </div>
                </div>
            </div>

            {/* Main Report Content */}
            {activeTab === 'report' ? (
                <div key="report-tab" className="max-w-6xl mx-auto bg-white dark:bg-gray-900 min-h-screen">
                    <Card className="p-8 shadow-md">
                        <div ref={reportRef} id="report-content">
                            {/* Report Header with Share Button */}
                            <div className="flex items-start justify-between gap-4 mb-6">
                                <h1 className="text-4xl font-bold text-brand-500 dark:text-brand-200 leading-tight flex-1">
                                    {reportData?.title || 'Market Validation Report'}
                                </h1>
                                <TooltipProvider>
                                    <div className="flex items-center gap-2">
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={handleDownloadReport}
                                                    disabled={isDownloading}
                                                    className="shrink-0 flex items-center gap-2 text-brand-500 dark:text-brand-400 hover:text-brand-500 dark:hover:text-brand-400 hover:border-brand-500 dark:hover:border-brand-400 transition-colors border-brand-500 dark:border-brand-400"
                                                >
                                                    {isDownloading ? (
                                                        <RefreshCw className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <Download className="h-4 w-4" />
                                                    )}
                                                    <span>{isDownloading ? 'Downloading...' : 'Download PDF'}</span>
                                                </Button>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                                <p>Download this report as a PDF</p>
                                            </TooltipContent>
                                        </Tooltip>

                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => setIsShareModalOpen(true)}
                                                    className="shrink-0 flex items-center gap-2 text-brand-500 dark:text-brand-400 hover:text-brand-500 dark:hover:text-brand-400 hover:border-brand-500 dark:hover:border-brand-400 transition-colors border-brand-500 dark:border-brand-400"
                                                >
                                                    <Share2 className="h-4 w-4" />
                                                    <span>Share</span>
                                                </Button>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                                <p>Share this report with others</p>
                                            </TooltipContent>
                                        </Tooltip>
                                    </div>
                                </TooltipProvider>
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
                <div key="insights-tab" className="max-w-6xl mx-auto bg-white dark:bg-gray-900 min-h-screen">
                    <ActionableInsightsComponent reportId={getReportId() ?? undefined} />
                </div>
            )}

            {/* Floating Footer Buttons */}
            <div
                className={`fixed bottom-0 ${isExpanded ? 'left-64' : 'left-16'} right-0 z-30 transition-all duration-300 ease-in-out ${showFloatingButtons ? 'translate-y-0' : 'translate-y-full'}`}
            >
                <div className="flex items-center justify-center py-4 bg-transparent">
                    <div className="flex gap-4">
                        <Button variant="outline" onClick={handleBackToValidator} className="bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-900">
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

            <ShareReportModal
                isOpen={isShareModalOpen}
                onClose={() => setIsShareModalOpen(false)}
                sessionId={getReportId()}
                token={token}
                reportTitle={reportData?.title || 'Market Validation Report'}
            />

            {/* Downloading Modal */}
            <Dialog open={isDownloading} onOpenChange={() => { }}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader className="bg-brand-25 dark:bg-gray-800 -mx-6 -mt-6 px-6 pt-6 pb-4 rounded-t-lg border-b border-brand-200 dark:border-brand-700">
                        <DialogTitle className="text-brand-500">Downloading Report</DialogTitle>
                    </DialogHeader>
                    <div className="flex flex-col items-center justify-center py-8 space-y-4">
                        <div className="relative">
                            <div className="h-16 w-16 rounded-full border-4 border-brand-100 border-t-brand-600 animate-spin"></div>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <FileText className="h-6 w-6 text-brand-600 opacity-50" />
                            </div>
                        </div>
                        <p className="text-center text-brand-500 dark:text-gray-300">
                            Generating your branded PDF report...
                        </p>
                        <p className="text-center text-xs text-gray-400">
                            This may take a few moments
                        </p>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Create Project Modal */}
            <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle><span className="text-brand-500">Create a Project </span></DialogTitle>
                        <p className="text-gray-500 text-sm">Create a project to explore this report further in the next module</p>
                    </DialogHeader>
                    <div className="grid gap-4">
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
        </div>
    );
};

ValidationResultsView.displayName = 'ValidationResultsView';
