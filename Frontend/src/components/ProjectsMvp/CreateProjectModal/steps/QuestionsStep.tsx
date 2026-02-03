'use client';

import React from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import type { Question } from '../types';

interface QuestionsStepProps {
  questions: Question[];
  answers: Record<string, string>;
  answerErrors: Record<string, string>;
  isSubmitting: boolean;
  onAnswerChange: (questionId: string, value: string) => void;
  getPriorityColor: (priority: string) => string;
  getCategoryDisplay: (category: string) => string;
}

export const QuestionsStep: React.FC<QuestionsStepProps> = ({
  questions,
  answers,
  answerErrors,
  isSubmitting,
  onAnswerChange,
  getPriorityColor,
  getCategoryDisplay,
}) => {
  return (
    <div className="py-2 space-y-4">
      <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
        <CheckCircle2 className="h-5 w-5 text-green-500" />
        <p className="text-sm text-green-700 dark:text-green-300">
          Successfully generated {questions.length} clarifying questions for your project!
        </p>
      </div>

      <div className="space-y-4">
        {questions.map((question, index) => (
          <div
            key={question.id}
            className="space-y-3"
          >
            {/* Question Header */}
            <div className="flex items-start gap-3">
              <span className="text-sm font-semibold text-brand-500 dark:text-brand-400 mt-1">
                Q{index + 1}.
              </span>
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge className={`${getPriorityColor(question.priority)} border`}>
                    {question.priority}
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    {getCategoryDisplay(question.category)}
                  </Badge>
                  {question.required && (
                    <Badge className="bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300 border-purple-200 dark:border-purple-800 border">
                      Required
                    </Badge>
                  )}
                </div>
                <Label htmlFor={`answer-${question.id}`} className="text-sm font-medium text-brand-500 dark:text-gray-300">
                  {question.question}
                  {question.required && <span className="text-red-500 ml-1">*</span>}
                </Label>
                {question.context && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 italic">
                    Context: {question.context}
                  </p>
                )}
              </div>
            </div>

            {/* Answer Input */}
            <div className="ml-8 space-y-2">
              <Textarea
                id={`answer-${question.id}`}
                placeholder={`Enter your answer for this ${question.required ? 'required' : 'optional'} question...`}
                value={answers[question.id] || ''}
                onChange={(e) => onAnswerChange(question.id, e.target.value)}
                className={`w-full min-h-[100px] resize-y ${
                  answerErrors[question.id] 
                    ? 'border-red-500 dark:border-red-500 focus-visible:ring-red-500' 
                    : ''
                }`}
                disabled={isSubmitting}
              />
              {answerErrors[question.id] && (
                <div className="flex items-center gap-1 text-red-500 text-xs">
                  <AlertCircle className="h-3 w-3" />
                  <span>{answerErrors[question.id]}</span>
                </div>
              )}
              {answers[question.id] && !answerErrors[question.id] && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {answers[question.id].length} characters
                </p>
              )}
            </div>

            {/* Divider */}
            {index < questions.length - 1 && (
              <div className="border-t border-gray-200 dark:border-gray-700 mt-4" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
