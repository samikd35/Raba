"use client";

import React, { useEffect, useState, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LogIn, UserPlus, Lock, RefreshCw, Mail } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter
} from "@/components/ui/dialog";

import { ReportContent, SourceItem as SourceItemType } from "./types";
import { LoadingSpinner } from "./LoadingSpinner";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { SourceItem } from "./SourceItem";

interface SharedReportResponse {
    success: boolean;
    message: string;
    report: {
        title: string;
        executive_summary: string;
        industry_analysis: string;
        challenges_analysis: string;
        recommendations: string;
        sources: Array<{
            number?: number;
            source_url: string;
            source_title?: string;
        }>;
        report_type: string;
        share_message: string;
        shared_by: string;
        shared_at: string;
    };
    access_type: string;
    can_download: boolean;
}

interface SharedReportViewProps {
    shareToken: string;
}

export const SharedReportView = ({ shareToken }: SharedReportViewProps) => {
    const [reportData, setReportData] = useState<ReportContent | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [sharedBy, setSharedBy] = useState<string>("");
    const [isScrolled, setIsScrolled] = useState(false);

    // Auth States
    const [requiresPassword, setRequiresPassword] = useState(false);
    const [requiresEmail, setRequiresEmail] = useState(false);
    const [password, setPassword] = useState("");
    const [email, setEmail] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const reportRef = useRef<HTMLDivElement>(null);

    const fetchSharedReport = useCallback(async (passwordAttempt: string = "", emailAttempt: string = "") => {
        try {
            setIsLoading(true);
            setError(null);

            const apiUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/workflow/share/access`;

            const response = await fetch(apiUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify({
                    share_token: shareToken,
                    password: passwordAttempt,
                    accessor_email: emailAttempt,
                }),
            });

            if (!response.ok) {
                const responseText = await response.text();
                let errorData: any = {};
                try {
                    errorData = responseText ? JSON.parse(responseText) : {};
                } catch {
                    // Not JSON
                }

                // Check if password is required
                const isPasswordRequired =
                    (response.status === 403) &&
                    (
                        (errorData.code === "access_denied" && errorData.message === "Password required") ||
                        (errorData.detail?.code === "access_denied" && errorData.detail?.message === "Password required")
                    );

                if (isPasswordRequired) {
                    setRequiresPassword(true);
                    setRequiresEmail(false);
                    setIsLoading(false);
                    // If we tried a password and still got "Password required", it means it was wrong
                    if (passwordAttempt) {
                        setError("Incorrect password");
                    }
                    return;
                }

                // Check if email is required
                const isEmailRequired =
                    (response.status === 403) &&
                    (
                        (errorData.code === "access_denied" && errorData.message === "Email required for access") ||
                        (errorData.detail?.code === "access_denied" && errorData.detail?.message === "Email required for access")
                    );

                if (isEmailRequired) {
                    setRequiresEmail(true);
                    setRequiresPassword(false);
                    setIsLoading(false);
                    if (emailAttempt) {
                        setError("Access denied. Email not authorized.");
                    }
                    return;
                }

                const errorMessage =
                    (typeof errorData.message === 'string' ? errorData.message : null) ||
                    (typeof errorData.detail === 'string' ? errorData.detail : null) ||
                    (typeof errorData.detail?.message === 'string' ? errorData.detail.message : null) ||
                    "Failed to load shared report.";

                if (response.status === 404) {
                    throw new Error("This shared report was not found or has expired.");
                }
                if (response.status === 403) {
                    throw new Error(errorMessage);
                }
                throw new Error(errorMessage);
            }

            const data: SharedReportResponse = await response.json();

            if (!data.success) {
                throw new Error(data.message || "Failed to access shared report.");
            }

            const transformedReport: ReportContent = {
                title: data.report.title,
                executive_summary: data.report.executive_summary,
                industry_analysis: data.report.industry_analysis,
                challenges_analysis: data.report.challenges_analysis,
                recommendations: data.report.recommendations,
                sources: data.report.sources.map((source, index) => ({
                    number: source.number || index + 1,
                    source_url: source.source_url,
                    source_title: source.source_title || "Untitled Source",
                })),
            };

            setReportData(transformedReport);
            setSharedBy(data.report.shared_by);
            setRequiresPassword(false);
            setRequiresEmail(false);
        } catch (err) {
            console.error("Error fetching shared report:", err);
            const errorMessage =
                err instanceof Error ? err.message : "Failed to load shared report";
            setError(errorMessage);
        } finally {
            setIsLoading(false);
            setIsSubmitting(false);
        }
    }, [shareToken]);

    const handlePasswordSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        if (!password.trim()) return;
        setIsSubmitting(true);
        setError(null);
        await fetchSharedReport(password, ""); // Clear email attempt when retrying password
    }, [password, fetchSharedReport]);

    const handleEmailSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email.trim()) return;
        setIsSubmitting(true);
        setError(null);
        // Pass password as well, in case it's needed
        await fetchSharedReport(password, email);
    }, [email, password, fetchSharedReport]);

    useEffect(() => {
        fetchSharedReport();
    }, [fetchSharedReport]);

    // Scroll detection for glassmorphic header effect
    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 10);
        };

        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    const processContentWithCitations = useCallback((content: string) => {
        if (!content) return "";

        let processedContent = content.replace(
            /\[(\d+)\]/g,
            '<a href="#source-$1" data-source="$1" class="citation-link text-blue-600 dark:text-blue-400 font-semibold">[$1]</a>'
        );

        processedContent = processedContent.replace(/^\s*•\s+(.+)$/gm, "* $1");

        return processedContent;
    }, []);

    const sources = useMemo(
        () => (reportData?.sources as SourceItemType[]) || [],
        [reportData?.sources]
    );

    const sourceItems = useMemo(
        () =>
            sources.map((source, index) => (
                <SourceItem
                    key={`source-${index}-${source.source_url}`}
                    source={source}
                    index={index}
                />
            )),
        [sources]
    );

    // Initial Loading state
    if (isLoading) {
        return <LoadingSpinner />;
    }

    // Error state (excluding auth requirements)
    if (error && !requiresPassword && !requiresEmail) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-[#101828] flex items-center justify-center p-4">
                <Card className="w-full max-w-md p-8 shadow-lg bg-white dark:bg-gray-900 text-center">
                    <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Lock className="h-8 w-8 text-red-600 dark:text-red-400" />
                    </div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                        Access Denied
                    </h1>
                    <p className="text-gray-500 dark:text-gray-400 mb-6">{error}</p>
                    <Button onClick={() => fetchSharedReport()} variant="outline">
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Try Again
                    </Button>
                </Card>
            </div>
        );
    }

    // Main render: includes Header, Content (if loaded), and Auth Modals (if needed)
    return (
        <div className="min-h-screen bg-gray-50 dark:bg-[#101828]">
            {/* Sticky Glassmorphic Header */}
            <header
                className={`sticky top-0 z-50 border-b transition-all duration-300 ${isScrolled
                    ? "bg-white/70 dark:bg-gray-900/70 backdrop-blur-md border-gray-200/50 dark:border-gray-700/50 shadow-md"
                    : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 shadow-sm"
                    }`}
            >
                <div className="max-w-6xl mx-auto px-4 py-3 md:py-4">
                    <div className="flex items-center justify-between gap-2">
                        {/* Left side - Title */}
                        <div className="flex items-center gap-2 md:gap-4 flex-1 min-w-0">
                            <Link href="/" className="relative h-8 w-24 md:h-12 md:w-32 shrink-0">
                                <Image
                                    src="/images/logo/logo.svg"
                                    alt="Logo"
                                    fill
                                    className="object-contain"
                                    priority
                                />
                            </Link>

                            <div className="hidden sm:flex items-center gap-4">
                                <div className="h-6 w-px bg-gray-200 dark:bg-gray-700"></div>
                                <div className="flex flex-col min-w-0 truncate">
                                    <h1 className="text-lg md:text-xl font-bold text-brand-600 dark:text-brand-400 truncate">
                                        Shared Report
                                    </h1>
                                    {/* {sharedBy && (
                                        <p className="text-sm text-gray-500 dark:text-gray-400">
                                            Shared by {sharedBy}
                                        </p>
                                    )} */}
                                </div>
                            </div>
                        </div>

                        {/* Right side - Action Buttons */}
                        <div className="flex items-center gap-2 md:gap-3 shrink-0">
                            <Link href="/signin">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-brand-600 dark:hover:text-brand-400 hover:border-brand-500 h-10 px-3 md:px-5 text-sm"
                                >
                                    <LogIn className="h-4 w-4" />
                                    <span>Login</span>
                                </Button>
                            </Link>
                            <Link href="/signup">
                                <Button size="sm" className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white h-10 px-3 md:px-5 text-sm">
                                    <UserPlus className="h-4 w-4" />
                                    <span>Sign Up</span>
                                </Button>
                            </Link>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Report Content */}
            {reportData && (
                <main className="max-w-6xl mx-auto py-4 md:py-8 px-3 md:px-4 md:-mt-4 relative z-10">
                    <Card className="p-4 md:p-8 shadow-md bg-white dark:bg-gray-900">
                        <div ref={reportRef} id="report-content">
                            {/* Report Title */}
                            <h1 className="text-2xl md:text-4xl font-bold text-brand-500 dark:text-brand-200 leading-tight mb-4 md:mb-8 break-words">
                                {reportData.title || "Market Validation Report"}
                            </h1>

                            {/* Executive Summary */}
                            {reportData.executive_summary && (
                                <section className="mb-8 md:mb-12">
                                    <h2 className="text-xl md:text-2xl font-bold text-brand-600 dark:text-brand-400 mb-4 md:mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                                        1. Executive Summary
                                    </h2>
                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                        <MarkdownRenderer
                                            content={processContentWithCitations(
                                                reportData.executive_summary
                                            )}
                                        />
                                    </div>
                                </section>
                            )}

                            {/* Industry Analysis Section */}
                            {reportData.industry_analysis && (
                                <section className="mb-8 md:mb-12">
                                    <h2 className="text-xl md:text-2xl font-bold text-brand-600 dark:text-brand-400 mb-4 md:mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                                        2. Industry Analysis
                                    </h2>
                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                        <MarkdownRenderer
                                            content={processContentWithCitations(
                                                reportData.industry_analysis
                                            )}
                                        />
                                    </div>
                                </section>
                            )}

                            {/* PESTLE Analysis & Challenges */}
                            {reportData.challenges_analysis && (
                                <section className="mb-8 md:mb-12">
                                    <h2 className="text-xl md:text-2xl font-bold text-brand-600 dark:text-brand-400 mb-4 md:mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                                        3. PESTLE Analysis & Market Challenges
                                    </h2>
                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                        <MarkdownRenderer
                                            content={processContentWithCitations(
                                                reportData.challenges_analysis
                                            )}
                                        />
                                    </div>
                                </section>
                            )}

                            {/* Strategic Recommendations */}
                            {reportData.recommendations && (
                                <section className="mb-8 md:mb-12">
                                    <h2 className="text-xl md:text-2xl font-bold text-brand-600 dark:text-brand-400 mb-4 md:mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                                        4. Strategic Recommendations
                                    </h2>
                                    <div className="space-y-4">
                                        <MarkdownRenderer
                                            content={processContentWithCitations(
                                                reportData.recommendations
                                            )}
                                        />
                                    </div>
                                </section>
                            )}

                            {/* References Section */}
                            {sources.length > 0 && (
                                <section className="mb-8 md:mb-12">
                                    <h2 className="text-xl md:text-2xl font-bold text-brand-600 dark:text-brand-400 mb-4 md:mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                                        5. References
                                    </h2>
                                    <div className="space-y-4">{sourceItems}</div>
                                </section>
                            )}
                        </div>
                    </Card>
                </main>
            )}

            {/* Password Modal */}
            <Dialog open={requiresPassword} onOpenChange={() => { }}>
                <DialogContent className="sm:max-w-md" onInteractOutside={(e) => e.preventDefault()}>
                    <DialogHeader>
                        <div className="mx-auto bg-brand-100 dark:bg-brand-900/30 p-3 rounded-full mb-2">
                            <Lock className="h-6 w-6 text-brand-600 dark:text-brand-400" />
                        </div>
                        <DialogTitle className="text-center text-xl">Password Protected</DialogTitle>
                        <DialogDescription className="text-center">
                            This report is protected. Please enter the password to view it.
                        </DialogDescription>
                    </DialogHeader>

                    <form onSubmit={handlePasswordSubmit} className="space-y-4 py-2">
                        <div className="space-y-2">
                            <Input
                                type="password"
                                placeholder="Enter password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full"
                                autoFocus
                            />
                            {error && (
                                <p className="text-sm text-red-500 dark:text-red-400 text-center">{error}</p>
                            )}
                        </div>
                        <DialogFooter className="sm:justify-center">
                            <Button
                                type="submit"
                                disabled={isSubmitting || !password.trim()}
                                className="w-full sm:w-full bg-brand-600 hover:bg-brand-700"
                            >
                                {isSubmitting ? (
                                    <>
                                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                        Verifying...
                                    </>
                                ) : (
                                    "Access Report"
                                )}
                            </Button>
                        </DialogFooter>
                    </form>

                    <div className="mt-2 text-center text-sm text-gray-500">
                        <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t border-gray-200 dark:border-gray-700" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-background px-2 text-muted-foreground">Or</span>
                            </div>
                        </div>
                        <div className="mt-4 flex justify-center gap-4">
                            <Link href="/signin" className="text-brand-600 hover:underline">Login</Link>
                            <Link href="/signup" className="text-brand-600 hover:underline">Sign Up</Link>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Email Modal */}
            <Dialog open={requiresEmail} onOpenChange={() => { }}>
                <DialogContent className="sm:max-w-md" onInteractOutside={(e) => e.preventDefault()}>
                    <DialogHeader>
                        <div className="mx-auto bg-brand-100 dark:bg-brand-900/30 p-3 rounded-full mb-2">
                            <Mail className="h-6 w-6 text-brand-600 dark:text-brand-400" />
                        </div>
                        <DialogTitle className="text-center text-xl">Email Required</DialogTitle>
                        <DialogDescription className="text-center">
                            This report is restricted to specific users. Please enter your email to verify access.
                        </DialogDescription>
                    </DialogHeader>

                    <form onSubmit={handleEmailSubmit} className="space-y-4 py-2">
                        <div className="space-y-2">
                            <Input
                                type="email"
                                placeholder="Enter your email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full"
                                autoFocus
                            />
                            {error && (
                                <p className="text-sm text-red-500 dark:text-red-400 text-center">{error}</p>
                            )}
                        </div>
                        <DialogFooter className="sm:justify-center">
                            <Button
                                type="submit"
                                disabled={isSubmitting || !email.trim()}
                                className="w-full sm:w-full bg-brand-600 hover:bg-brand-700"
                            >
                                {isSubmitting ? (
                                    <>
                                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                        Verifying...
                                    </>
                                ) : (
                                    "Verify Email"
                                )}
                            </Button>
                        </DialogFooter>
                    </form>

                    <div className="mt-2 text-center text-sm text-gray-500">
                        <div className="mt-4 flex justify-center gap-4">
                            <Link href="/signin" className="text-brand-600 hover:underline">Login</Link>
                            <Link href="/signup" className="text-brand-600 hover:underline">Sign Up</Link>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

SharedReportView.displayName = "SharedReportView";
