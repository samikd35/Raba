"use client";

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Hypothesis, HypothesisText, isStructuredHypothesisText } from '@/types/organization';
import { Lightbulb, Calendar } from 'lucide-react';
import { motion } from 'framer-motion';

export interface HypothesisCardProps {
  hypothesis: Hypothesis;
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

export function HypothesisCard({ 
  hypothesis, 
  index, 
  readOnly = false,
  animationDelay = 0 
}: HypothesisCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ 
        duration: 0.4,
        delay: animationDelay 
      }}
      className="p-6 bg-white dark:bg-gray-900 border border-purple-200 dark:border-purple-800 rounded-xl shadow-sm hover:shadow-lg hover:border-purple-300 dark:hover:border-purple-700 group transition-all duration-200"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <Badge 
          variant="secondary"
          className="w-fit bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300"
        >
          {hypothesis.persona_name || 'Unknown Persona'}
        </Badge>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <Lightbulb className="w-3 h-3" />
          <span>Hypothesis #{index + 1}</span>
        </div>
      </div>
      
      {/* Hypothesis Statement */}
      <div className="mb-4">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Hypothesis Statement
        </h4>
        {isStructuredHypothesisText(hypothesis.text) ? (
          <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg border border-purple-100 dark:border-purple-800 space-y-2">
            <p className="text-gray-800 dark:text-gray-200 leading-relaxed">
              <span className="font-bold text-purple-700 dark:text-purple-300 text-base">We believe that </span>
              {hypothesis.text.we_believe_that}
            </p>
            <p className="text-gray-800 dark:text-gray-200 leading-relaxed">
              <span className="font-bold text-purple-700 dark:text-purple-300 text-base">Are struggling with </span>
              {hypothesis.text.are_struggling_with}
            </p>
            <p className="text-gray-800 dark:text-gray-200 leading-relaxed">
              <span className="font-bold text-purple-700 dark:text-purple-300 text-base">Thus </span>
              {hypothesis.text.thus}
            </p>
            <p className="text-gray-800 dark:text-gray-200 leading-relaxed">
              <span className="font-bold text-purple-700 dark:text-purple-300 text-base">That guarantees </span>
              {hypothesis.text.that_guarantees}
            </p>
          </div>
        ) : (
          <p className="text-gray-800 dark:text-gray-200 leading-relaxed bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg border border-purple-100 dark:border-purple-800">
            {hypothesis.text as string}
          </p>
        )}
      </div>
      
      {/* Supporting Evidence */}
      {hypothesis.evidence && hypothesis.evidence.length > 0 && (
        <div className="mb-4">
          <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Supporting Evidence ({hypothesis.evidence.length})
          </h5>
          <div className="space-y-2">
            {hypothesis.evidence.map((evidence, evidenceIndex) => (
              <div
                key={`hypothesis-evidence-${hypothesis.id}-${evidenceIndex}`}
                className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg group-hover:bg-purple-50 dark:group-hover:bg-purple-900/10 transition-colors"
              >
                <div 
                  className="flex-shrink-0 w-5 h-5 bg-purple-500 text-white rounded-full flex items-center justify-center text-xs font-bold"
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
          Generated on {formatDate(hypothesis.generated_at)}
        </p>
      </div>
    </motion.div>
  );
}

export default HypothesisCard;
