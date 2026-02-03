"use client";

import React, { useMemo } from 'react';
import {
  AlertTriangle,
  AlertCircle,
  Sparkles,
  FileText,
  ExternalLink,
} from 'lucide-react';
import { SolutionCritiqueData } from '@/types/organization';
import { CritiqueCard, ResearchSources } from '@/features/solution-critic/components';

interface SolutionCritiqueSectionProps {
  critiqueData: SolutionCritiqueData | null;
  readOnly?: boolean;
  embedded?: boolean;
}

export const SolutionCritiqueSection: React.FC<SolutionCritiqueSectionProps> = ({
  critiqueData,
  readOnly = true,
  embedded = true,
}) => {
  // Memoize data derived from the response (same logic as workspace page)
  const allCritiques = useMemo(() => {
    if (!critiqueData?.critique_report?.all_critiques) return [];
    
    let critiques = [...critiqueData.critique_report.all_critiques];

    // Reorder "Business Model Defensibility Critique" to be at number 5 (index 4)
    const businessModelIdx = critiques.findIndex((c: any) =>
      c.section_name && c.section_name.toLowerCase().includes("business model defensibility")
    );

    if (businessModelIdx !== -1) {
      const [item] = critiques.splice(businessModelIdx, 1);
      const insertIdx = Math.min(4, critiques.length);
      critiques.splice(insertIdx, 0, item);
    }

    return critiques;
  }, [critiqueData]);

  const allSources = useMemo(() => 
    critiqueData?.critique_report?.sources || [], 
    [critiqueData]
  );

  const critiquesByDimension = useMemo(() => 
    critiqueData?.critique_report?.critiques_by_dimension || {}, 
    [critiqueData]
  );

  // Create map of critique_id to dimension summary for quick lookup
  const critiqueSummaryMap = useMemo(() => {
    const summaryMap: Record<string, string> = {};
    Object.values(critiquesByDimension).forEach((dimension: any) => {
      if (dimension) {
        dimension.critiques?.forEach((critique: any) => {
          summaryMap[critique.critique_id] = dimension.summary;
        });
      }
    });
    return summaryMap;
  }, [critiquesByDimension]);

  // Handle empty/null state
  if (!critiqueData) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Sparkles className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">No Critique Data Available</p>
        <p className="text-sm">Solution Critique will appear here once generated.</p>
      </div>
    );
  }

  // Handle processing state
  if (critiqueData.status === 'processing') {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <div className="animate-spin w-12 h-12 mx-auto mb-4 border-4 border-purple-200 border-t-purple-600 rounded-full" />
        <p className="text-lg font-medium">Critique In Progress</p>
        <p className="text-sm">AI is analyzing your solution. This may take a minute...</p>
      </div>
    );
  }

  // Handle failed state
  if (critiqueData.status === 'failed') {
    return (
      <div className="text-center py-8 text-red-500 dark:text-red-400">
        <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
        <p className="text-lg font-medium">Critique Failed</p>
        <p className="text-sm">{critiqueData.error || 'An error occurred during analysis.'}</p>
      </div>
    );
  }

  // Handle missing report
  const report = critiqueData.critique_report;
  if (!report) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-lg font-medium">Report Not Available</p>
        <p className="text-sm">Critique completed but report data is missing.</p>
      </div>
    );
  }

  // Main content - same layout as workspace page
  return (
    <div className="space-y-2">
      {/* Critiques List - using the same CritiqueCard component */}
      <div className="space-y-2">
        {allCritiques.map((critique: any, index: number) => (
          <CritiqueCard
            key={critique.critique_id}
            critique={critique}
            index={index}
            allSources={allSources}
            dimensionSummary={critiqueSummaryMap[critique.critique_id]}
          />
        ))}
      </div>

      {/* Research Sources Section */}
      <ResearchSources sources={allSources} />

      {/* Metadata */}
      {report.generated_at && (
        <div className="flex items-center justify-center gap-4 text-xs text-gray-500 dark:text-gray-400 mt-4">
          <div className="flex items-center gap-1">
            <FileText className="w-3 h-3" />
            Generated on {new Date(report.generated_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </div>
          {report.metadata?.total_sources && (
            <div className="flex items-center gap-1">
              <ExternalLink className="w-3 h-3" />
              {report.metadata.total_sources} sources analyzed
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SolutionCritiqueSection;
