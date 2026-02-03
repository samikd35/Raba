"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw, Sparkles, FileText, CheckCircle2, Zap, Clock } from "lucide-react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";

interface PRDErrorStateProps {
  error: string;
  onRetry: () => void;
  pageTitle?: string;
  showGenerateOption?: boolean;
  onGenerateClick?: () => void;
}

/**
 * Check if the error indicates no PRD exists (404)
 */
const isNoPRDError = (error: string): boolean => {
  const lowerError = error.toLowerCase();
  return (
    lowerError.includes('no prd found') ||
    lowerError.includes('prd not found') ||
    lowerError.includes('404') ||
    lowerError.includes('not found for this project')
  );
};

export function PRDErrorState({ 
  error, 
  onRetry, 
  pageTitle = "Your Product Requirement Detail",
  showGenerateOption = false,
  onGenerateClick,
}: PRDErrorStateProps) {
  const canGenerate = showGenerateOption || isNoPRDError(error);

  return (
    <div className="container mx-auto space-y-4">
      <PageBreadcrumb pageTitle={pageTitle} />
      
      {canGenerate ? (
        <div className="space-y-4">
          {/* Hero Section */}
          <Card className="border-brand-200 dark:border-brand-800 bg-gradient-to-br from-brand-50 to-white dark:from-brand-900/20 dark:to-gray-900">
            <CardContent className="pt-8 pb-8">
              <div className="text-center space-y-6 max-w-2xl mx-auto">
                {/* Icon with animated glow */}
                <div className="relative inline-flex">
                  <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center shadow-lg">
                    <FileText className="w-10 h-10 text-white" />
                  </div>
                  <div className="absolute inset-0 rounded-2xl bg-brand-400 opacity-20 blur-xl animate-pulse" />
                </div>

                {/* Title and Description */}
                <div className="space-y-3">
                  <h2 className="text-2xl font-bold text-brand-600 dark:text-brand-400">
                    No Product Requirements Found
                  </h2>
                  <p className="text-base text-gray-600 dark:text-gray-400 leading-relaxed">
                    Let&apos;s create a comprehensive Product Requirement Document for your project.
                    Our AI will analyze your project and generate detailed requirements.
                  </p>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-center gap-3 pt-2">
                  <Button 
                    variant="outline" 
                    onClick={onRetry}
                    className="border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Refresh
                  </Button>
                  <Button 
                    onClick={onGenerateClick}
                    className="bg-gradient-to-r from-brand-500 to-brand-600 hover:from-brand-600 hover:to-brand-700 text-white shadow-lg hover:shadow-xl transition-all"
                  >
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate PR
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* What to Expect Section */}
          <Card className="border-gray-200 dark:border-gray-800">
            <CardContent className="pt-6 pb-6">
              <div className="space-y-4">
                <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100">
                  What to Expect
                </h3>
                <div className="grid gap-4 md:grid-cols-3">
                  {/* Step 1 */}
                  <div className="flex items-start gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                    <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900/40 flex items-center justify-center shrink-0">
                      <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-medium text-sm text-green-900 dark:text-green-300">
                        Answer Questions
                      </h4>
                      <p className="text-xs text-green-700 dark:text-green-400">
                        We&apos;ll ask a few clarifying questions about your project
                      </p>
                    </div>
                  </div>

                  {/* Step 2 */}
                  <div className="flex items-start gap-3 p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                    <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center shrink-0">
                      <Zap className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-medium text-sm text-blue-900 dark:text-blue-300">
                        AI Analysis
                      </h4>
                      <p className="text-xs text-blue-700 dark:text-blue-400">
                        Our AI analyzes your project and generates requirements
                      </p>
                    </div>
                  </div>

                  {/* Step 3 */}
                  <div className="flex items-start gap-3 p-4 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
                    <div className="w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/40 flex items-center justify-center shrink-0">
                      <Clock className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-medium text-sm text-purple-900 dark:text-purple-300">
                        Ready in Minutes
                      </h4>
                      <p className="text-xs text-purple-700 dark:text-purple-400">
                        Get your comprehensive PRD in just a few minutes
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card className="border-red-200 dark:border-red-800">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <div className="w-16 h-16 mx-auto rounded-full bg-red-100 dark:bg-red-900/40 flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-red-600 dark:text-red-400">
                  Error Loading PRD
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 max-w-md mx-auto">
                  {error || "Failed to load Product Requirements Document"}
                </p>
              </div>
              <Button 
                onClick={onRetry}
                variant="outline"
                className="border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
