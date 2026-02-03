import Link from "next/link";
import React from "react";
import ProblemGenerationHistoryDropdown from "../workspace/ProblemGenerationHistoryDropdown";
import RefineDropdown from "../workspace/RefineDropdown";
import ProblemValidationHistoryDropdown from "../workspace/ProblemValidationHistoryDropdown";

interface BreadcrumbProps {
  pageTitle: string;
  titleSuffix?: React.ReactNode;
}

const PageBreadcrumb2: React.FC<BreadcrumbProps> = ({ pageTitle, titleSuffix }) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 z-25 mb-4 px-2 mt-1">
      {/* Page Title Section */}
      <div className="flex items-center gap-3">
        <div className="hidden sm:block w-1 h-6 bg-brand-500 rounded-full"></div>
        <h2 className="text-lg sm:text-xl font-semibold text-brand-500 dark:text-white/95 tracking-tight">
          {pageTitle}
        </h2>
        {titleSuffix}
      </div>

      {/* Right Section - Credits, Breadcrumb & Dropdowns */}
      <div className="flex flex-col-reverse sm:flex-row items-start sm:items-center gap-4">
        {/* Breadcrumb */}
        <nav className="flex items-center">
          <ol className="flex items-center gap-2 text-sm">
            <li>
              <Link
                className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 transition-colors duration-200"
                href="/workspace"
              >
                <svg
                  className="w-4 h-4"
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
                Home
              </Link>
            </li>
            <li className="flex items-center gap-2">
              <svg
                className="w-4 h-4 text-gray-400"
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
              <span className="text-gray-800 dark:text-white/90 font-medium">
                {pageTitle}
              </span>
            </li>
          </ol>
        </nav>

        {/* Action Items Container */}
        <div className="flex items-center gap-3 flex-wrap">


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

export default PageBreadcrumb2;