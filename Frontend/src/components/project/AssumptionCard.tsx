"use client";

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Assumption } from '@/types/organization';
import { Target, Calendar } from 'lucide-react';
import { motion } from 'framer-motion';

export interface AssumptionCardProps {
  assumption: Assumption;
  index: number;
  readOnly?: boolean;
  animationDelay?: number;
}

// Format date helper
const formatDate = (dateString: string): string => {
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return 'N/A';
  }
};

export function AssumptionCard({ 
  assumption, 
  index, 
  readOnly = false,
  animationDelay = 0 
}: AssumptionCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ 
        duration: 0.4,
        delay: animationDelay 
      }}
      className="p-6 bg-white dark:bg-gray-900 border border-green-200 dark:border-green-800 rounded-xl shadow-sm hover:shadow-lg hover:border-green-300 dark:hover:border-green-700 group transition-all duration-200"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <Badge 
          variant="secondary"
          className="w-fit bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300"
        >
          {assumption.persona_name || 'Unknown Persona'}
        </Badge>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <Target className="w-3 h-3" />
          <span>Assumption #{index + 1}</span>
        </div>
      </div>
      
      {/* Assumption Statement */}
      <div className="mb-4">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Testable Assumption
        </h4>
        <p className="text-gray-800 dark:text-gray-200 leading-relaxed bg-green-50 dark:bg-green-900/20 p-4 rounded-lg border border-green-100 dark:border-green-800">
          {assumption.text}
        </p>
      </div>
      
      {/* Supporting Evidence */}
      {assumption.evidence && assumption.evidence.length > 0 && (
        <div className="mb-4">
          <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Supporting Evidence ({assumption.evidence.length})
          </h5>
          <div className="space-y-2">
            {assumption.evidence.map((evidence, evidenceIndex) => (
              <div
                key={`assumption-evidence-${assumption.id}-${evidenceIndex}`}
                className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg group-hover:bg-green-50 dark:group-hover:bg-green-900/10 transition-colors"
              >
                <div 
                  className="flex-shrink-0 w-5 h-5 bg-green-500 text-white rounded-full flex items-center justify-center text-xs font-bold"
                >
                  {evidenceIndex + 1}
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                  {evidence}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generated timestamp */}
      <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          Generated on {formatDate(assumption.generated_at)}
        </p>
      </div>
    </motion.div>
  );
}

export default AssumptionCard;
