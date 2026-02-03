"use client";

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Questionnaire } from '@/types/organization';
import { 
  MessageSquare, 
  Calendar, 
  Activity, 
  Heart, 
  MapPin,
  Link2
} from 'lucide-react';
import { motion } from 'framer-motion';

export interface QuestionnaireCardProps {
  questionnaire: Questionnaire;
  index: number;
  readOnly?: boolean;
  animationDelay?: number;
}

// Get icon based on question type
const getQuestionTypeIcon = (type: string) => {
  switch (type) {
    case 'behavioral':
      return Activity;
    case 'attitudinal':
      return Heart;
    case 'contextual':
      return MapPin;
    default:
      return MessageSquare;
  }
};

// Get color classes based on question type
const getTypeColorClasses = (type: string): string => {
  switch (type) {
    case 'behavioral':
      return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
    case 'attitudinal':
      return 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400';
    case 'contextual':
      return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
    default:
      return 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400';
  }
};

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

export function QuestionnaireCard({ 
  questionnaire, 
  index, 
  readOnly = false,
  animationDelay = 0 
}: QuestionnaireCardProps) {
  const TypeIcon = getQuestionTypeIcon(questionnaire.type);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ 
        duration: 0.4,
        delay: animationDelay 
      }}
      className="p-6 bg-white dark:bg-gray-900 border border-orange-200 dark:border-orange-800 rounded-xl shadow-sm hover:shadow-lg hover:border-orange-300 dark:hover:border-orange-700 group transition-all duration-200"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge 
            variant="secondary"
            className="bg-orange-100 dark:bg-orange-900/50 text-orange-700 dark:text-orange-300"
          >
            {questionnaire.persona_name || 'Unknown Persona'}
          </Badge>
          <Badge 
            variant="outline"
            className={`flex items-center gap-1 ${getTypeColorClasses(questionnaire.type)}`}
          >
            <TypeIcon className="w-3 h-3" />
            {questionnaire.type}
          </Badge>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <MessageSquare className="w-3 h-3" />
          <span>Question #{index + 1}</span>
        </div>
      </div>
      
      {/* Question Text */}
      <div className="mb-4">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Interview Question
        </h4>
        <p className="text-gray-800 dark:text-gray-200 leading-relaxed bg-orange-50 dark:bg-orange-900/20 p-4 rounded-lg border border-orange-100 dark:border-orange-800">
          {questionnaire.text}
        </p>
      </div>
      
      {/* Linked References */}
      <div className="mb-4 flex flex-wrap gap-3 text-xs">
        {questionnaire.assumption_id && (
          <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
            <Link2 className="w-3 h-3" />
            <span>Assumption: {questionnaire.assumption_id}</span>
          </div>
        )}
        {questionnaire.hypothesis_id && (
          <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
            <Link2 className="w-3 h-3" />
            <span>Hypothesis: {questionnaire.hypothesis_id}</span>
          </div>
        )}
      </div>

      {/* Generated timestamp */}
      <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          Generated on {formatDate(questionnaire.generated_at)}
        </p>
      </div>
    </motion.div>
  );
}

export default QuestionnaireCard;
