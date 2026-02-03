"use client";

import React from "react";
import { Loader2 } from "lucide-react";
import PageBreadcrumb from "@/components/common/module 3/sub-module-1/PageBreadCrumb";

export const BMCLoadingState: React.FC = () => {
  return (
    <div className="min-h-screen">
      <PageBreadcrumb pageTitle="Business Model Canvas" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">Loading Business Model Canvas...</p>
          </div>
        </div>
      </div>
    </div>
  );
};
