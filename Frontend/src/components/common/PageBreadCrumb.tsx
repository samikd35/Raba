"use client";

import Link from "next/link";
import React from "react";
import { usePathname } from "next/navigation";
import ProblemGenerationHistoryDropdown from "../ProblemGenerationHistoryDropdown";
import RefineDropdown from "../RefineDropdown";
import ProblemValidationHistoryDropdown from "../ProblemValidationHistoryDropdown";

interface BreadcrumbProps {
  pageTitle: string;
  titleSuffix?: React.ReactNode;
}

const PageBreadcrumb: React.FC<BreadcrumbProps> = ({ pageTitle, titleSuffix }) => {
  const pathname = usePathname();

  // Determine home path based on current route
  // Note: workspace dashboard is at /workspace, team-workspace dashboard is at /team-workspace/dashboard
  const homePath = pathname?.startsWith("/team-workspace")
    ? "/team-workspace/dashboard"
    : "/workspace";
  return (
    <div className="flex gap-2 z-25 px-2 py-2 min-w-0 justify-between items-center">
      {/* Page Title Section */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="hidden sm:block w-1 h-6 bg-brand-500 rounded-full flex-shrink-0"></div>
        <h2 className="text-lg sm:text-xl font-semibold text-brand-500 dark:text-white/95 tracking-tight truncate">
          {pageTitle}
        </h2>
        {titleSuffix}
      </div>

      {/* Bottom Section - Breadcrumb & Dropdowns */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end gap-2 min-w-0">
        {/* Breadcrumb */}
        <nav className="flex items-center min-w-0">
          <ol className="flex items-center gap-2 text-sm min-w-0">
            <li className="flex-shrink-0">
              <Link
                className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 transition-colors duration-200 whitespace-nowrap"
                href={homePath}
              >
                <svg
                  className="w-4 h-4 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                  />
                </svg>
                <span className="hidden sm:inline">Home</span>
                <span className="sm:hidden">Home</span>
              </Link>
            </li>
            <li className="flex items-center gap-2 min-w-0">
              <svg
                className="w-4 h-4 text-gray-400 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
              <span className="text-gray-800 dark:text-white/90 font-medium truncate">
                {pageTitle}
              </span>
            </li>
          </ol>
        </nav>

        {/* Action Items Container */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Dropdowns */}
          <div className="flex items-center gap-2">
            {pageTitle === "Problem Explorer" && <ProblemGenerationHistoryDropdown />}
            {(pageTitle === "Problem Predictor" ||
              pageTitle === "Refinement Problem Detail" ||
              pageTitle === "Idea Refinement Results" ||
              pageTitle === "Refinement History Details") && <RefineDropdown />}
            {pageTitle === "Problem Validator" && (
              <ProblemValidationHistoryDropdown />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PageBreadcrumb;