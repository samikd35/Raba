'use client';

import React from 'react';
import { AlertTriangle, ArrowRight, FileWarning, Info } from 'lucide-react';
import type { MissingArtifactsStepProps } from '../types';

/**
 * Get artifact display name and icon color
 */
const getArtifactStyle = (artifactName: string): { color: string; bgColor: string } => {
  const lowerName = artifactName.toLowerCase();
  if (lowerName.includes('vps') || lowerName.includes('value')) {
    return { 
      color: 'text-purple-600 dark:text-purple-400', 
      bgColor: 'bg-purple-100 dark:bg-purple-900/40' 
    };
  }
  if (lowerName.includes('bmc') || lowerName.includes('business')) {
    return { 
      color: 'text-blue-600 dark:text-blue-400', 
      bgColor: 'bg-blue-100 dark:bg-blue-900/40' 
    };
  }
  if (lowerName.includes('critique') || lowerName.includes('solution')) {
    return { 
      color: 'text-amber-600 dark:text-amber-400', 
      bgColor: 'bg-amber-100 dark:bg-amber-900/40' 
    };
  }
  return { 
    color: 'text-gray-600 dark:text-gray-400', 
    bgColor: 'bg-gray-100 dark:bg-gray-800' 
  };
};

/**
 * Format artifact name for display
 */
const formatArtifactName = (name: string): string => {
  return name
    .replace(/_/g, ' ')
    .replace(/\b(v\d+)\b/gi, (match) => match.toUpperCase())
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

export const MissingArtifactsStep: React.FC<MissingArtifactsStepProps> = ({
  artifactDetails,
  onClose,
}) => {
  return (
    <div className="py-4 space-y-6">
      {/* Warning Banner */}
      <div className="flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
        <AlertTriangle className="h-6 w-6 text-amber-500 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h3 className="font-semibold text-amber-800 dark:text-amber-300">
            Missing Required Artifacts
          </h3>
          <p className="text-sm text-amber-700 dark:text-amber-400">
            Your project is missing some required artifacts needed for PRD generation. 
            Please complete the following steps first.
          </p>
        </div>
      </div>

      {/* Missing Artifacts List */}
      <div className="space-y-3">
        <h4 className="font-medium text-gray-900 dark:text-gray-100">
          Required Steps ({artifactDetails.length})
        </h4>
        
        <div className="space-y-3">
          {artifactDetails.map((artifact, index) => {
            const style = getArtifactStyle(artifact.artifact_name);
            return (
              <div
                key={artifact.artifact_name}
                className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <div className="flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-lg ${style.bgColor} flex items-center justify-center shrink-0`}>
                    <FileWarning className={`h-4 w-4 ${style.color}`} />
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-gray-400 dark:text-gray-500">
                        Step {index + 1}
                      </span>
                      <h5 className="font-semibold text-gray-900 dark:text-gray-100">
                        {formatArtifactName(artifact.artifact_name)}
                      </h5>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {artifact.description}
                    </p>
                    <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                      <ArrowRight className="h-3.5 w-3.5 text-brand-500" />
                      <p className="text-xs text-brand-600 dark:text-brand-400 font-medium">
                        {artifact.how_to_generate}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Info Box */}
      <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <Info className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
        <p className="text-xs text-blue-700 dark:text-blue-300">
          Complete the missing steps in order. Each artifact builds on the previous one to ensure 
          your PRD is comprehensive and well-informed.
        </p>
      </div>
    </div>
  );
};
