"use client";

import React from "react";
import { Loader2 } from "lucide-react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";

interface PRDLoadingStateProps {
  pageTitle?: string;
}

export function PRDLoadingState({ pageTitle = "Your Product Requirement Detail" }: PRDLoadingStateProps) {
  return (
    <div className="container mx-auto">
      <PageBreadcrumb pageTitle={pageTitle} />
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-brand-600" />
          <p className="text-gray-600 dark:text-gray-400">Loading Product Requirements...</p>
        </div>
      </div>
    </div>
  );
}
