'use client';

import React from 'react';
import { CheckCircle2, AlertCircle, HelpCircle, Target } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import type { QuestionsStepProps } from '../types';

/**
 * Get category color based on question category
 */
const getCategoryColor = (category: string): string => {
  const lowerCategory = category.toLowerCase();
  if (lowerCategory.includes('user') || lowerCategory.includes('customer')) {
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border-blue-200 dark:border-blue-800';
  }
  if (lowerCategory.includes('technical') || lowerCategory.includes('feature')) {
    return 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300 border-purple-200 dark:border-purple-800';
  }
  if (lowerCategory.includes('business') || lowerCategory.includes('market')) {
    return 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300 border-green-200 dark:border-green-800';
  }
  if (lowerCategory.includes('scope') || lowerCategory.includes('constraint')) {
    return 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border-amber-200 dark:border-amber-800';
  }
  return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700';
};

export const QuestionsStep: React.FC<QuestionsStepProps> = ({
  questions,
  answers,
  answerErrors,
  isSubmitting,
  onAnswerChange,
  runId,
  coarseRouting,
}) => {
  return (
    <div className="py-2 space-y-4">
      {/* Success Banner */}
      <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
        <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
        <p className="text-sm text-green-700 dark:text-green-300">
          Successfully generated {questions.length} clarifying questions for your PRD!
        </p>
      </div>

 

      {/* Questions List */}
      <div className="space-y-5">
        {questions.map((question, index) => (
          <div
            key={`question-${question.q_index}`}
            className="space-y-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700"
          >
            {/* Question Header */}
            <div className="flex items-start gap-3">
              <span className="text-sm font-bold text-brand-500 dark:text-brand-400 mt-0.5">
                Q{index + 1}.
              </span>
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge className={`${getCategoryColor(question.category)} border text-xs`}>
                    {question.category}
                  </Badge>
                </div>
                <Label 
                  htmlFor={`answer-${question.q_index}`} 
                  className="text-sm font-medium text-gray-900 dark:text-gray-100 block"
                >
                  {question.question_text}
                  <span className="text-red-500 ml-1">*</span>
                </Label>
                {question.purpose && (
                  <div className="flex items-start gap-1.5 mt-1">
                    <HelpCircle className="h-3.5 w-3.5 text-gray-400 shrink-0 mt-0.5" />
                    <p className="text-xs text-gray-500 dark:text-gray-400 italic">
                      {question.purpose}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Answer Input */}
            <div className="ml-7 space-y-2">
              <Textarea
                id={`answer-${question.q_index}`}
                placeholder="Enter your answer here... (minimum 10 characters)"
                value={answers[question.q_index] || ''}
                onChange={(e) => onAnswerChange(question.q_index, e.target.value)}
                className={`w-full min-h-[100px] resize-y transition-colors ${
                  answerErrors[question.q_index]
                    ? 'border-red-500 dark:border-red-500 focus-visible:ring-red-500'
                    : 'focus-visible:ring-brand-500'
                }`}
                disabled={isSubmitting}
              />
              <div className="flex items-center justify-between">
                {answerErrors[question.q_index] ? (
                  <div className="flex items-center gap-1 text-red-500 text-xs">
                    <AlertCircle className="h-3 w-3" />
                    <span>{answerErrors[question.q_index]}</span>
                  </div>
                ) : (
                  <div />
                )}
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  {(answers[question.q_index] || '').length} / 10+ characters
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Info Footer */}
      <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
        <p className="text-xs text-amber-700 dark:text-amber-300">
          <strong>Tip:</strong> Provide detailed answers to get a more accurate and comprehensive PRD. 
          Each answer should be at least 10 characters long.
        </p>
      </div>
    </div>
  );
};
