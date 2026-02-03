"use client";

import React from "react";
import { AlertCircle, RefreshCw, Play, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import PageBreadcrumb from "@/components/common/module 3/sub-module-1/PageBreadCrumb";

interface BMCErrorStateProps {
  error: string;
  onRetry: () => void;
  onGenerate: () => void;
  isGenerating: boolean;
  isAccessError?: boolean;
}

export const BMCErrorState: React.FC<BMCErrorStateProps> = ({
  error,
  onRetry,
  onGenerate,
  isGenerating,
  isAccessError = false
}) => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageBreadcrumb pageTitle="Business Model Canvas" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center max-w-md">
            <AlertCircle className={`w-12 h-12 mx-auto mb-4 ${isAccessError ? 'text-orange-500' : 'text-red-500'}`} />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              {isAccessError ? 'Access Restricted' : 'Unable to Load BMC'}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">{error}</p>
            
            {isAccessError ? (
              <div className="space-y-3">
                <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4 text-sm text-orange-800 dark:text-orange-200">
                  <strong>What you can do:</strong>
                  <ul className="mt-2 text-left space-y-1">
                    <li>• Contact your team administrator for access</li>
                    <li>• Check if you're a member of the correct team</li>
                    <li>• Return to your project dashboard</li>
                  </ul>
                </div>
                <Button onClick={() => window.history.back()} variant="outline">
                  Go Back
                </Button>
              </div>
            ) : (
              <div className="flex gap-3 justify-center">
                <Button onClick={onRetry} variant="outline">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Retry
                </Button>
                <Button onClick={onGenerate} disabled={isGenerating}>
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Generate BMC
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
