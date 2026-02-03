'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, Circle } from 'lucide-react';
import type { ProfileFormData } from '@/types/cofounder';

interface ProfileCompletionProgressProps {
  formData: ProfileFormData;
  className?: string;
}

export default function ProfileCompletionProgress({
  formData,
  className = '',
}: ProfileCompletionProgressProps) {
  // Calculate completion percentage based on required fields
  const calculateCompletion = (): { percentage: number; completed: number; total: number; sections: any[] } => {
    const sections = [
      {
        name: 'Basic Info',
        fields: [
          { name: 'First Name', value: formData.first_name },
          { name: 'Last Name', value: formData.last_name },
          { name: 'Email', value: formData.email },
          { name: 'Country', value: formData.country },
        ],
      },
      {
        name: 'Professional',
        fields: [
          { name: 'Professional Background', value: formData.professional_background },
          {
            name: 'Industries (min 2)',
            value: formData.industries_of_interest?.length >= 2 ? 'yes' : '',
          },
        ],
      },
      {
        name: 'Capabilities',
        fields: [
          {
            name: 'Responsibilities (min 1)',
            value: formData.responsibilities_offered?.length > 0 ? 'yes' : '',
          },
          { name: 'Skills Needed (min 1)', value: formData.skills_needed?.length > 0 ? 'yes' : '' },
        ],
      },
      {
        name: 'Personal',
        fields: [
          { name: 'Personal Statement', value: formData.personal_statement },
        ],
      },
      {
        name: 'Commitment',
        fields: [
          { name: 'Your Commitment', value: formData.expected_commitment },
          { name: 'Preferred Commitment', value: formData.preferred_commitment },
          { name: 'Venture Stage (min 1)', value: formData.venture_stage?.length > 0 ? 'yes' : '' },
          {
            name: 'Preferred Venture Stage (min 1)',
            value: formData.preferred_venture_stage?.length > 0 ? 'yes' : '',
          },
        ],
      },
    ];

    let totalFields = 0;
    let completedFields = 0;

    const sectionsWithCompletion = sections.map((section) => {
      let sectionCompleted = 0;
      section.fields.forEach((field) => {
        totalFields++;
        if (field.value && field.value.toString().trim() !== '') {
          completedFields++;
          sectionCompleted++;
        }
      });
      return {
        ...section,
        completed: sectionCompleted,
        total: section.fields.length,
        percentage: Math.round((sectionCompleted / section.fields.length) * 100),
      };
    });

    const percentage = Math.round((completedFields / totalFields) * 100);

    return {
      percentage,
      completed: completedFields,
      total: totalFields,
      sections: sectionsWithCompletion,
    };
  };

  const completion = calculateCompletion();

  return (
    <div className={`bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 ${className}`}>
      {/* Overall Progress */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            Profile Completion
          </h3>
          <span className="text-sm font-bold text-brand-600 dark:text-brand-400">
            {completion.percentage}%
          </span>
        </div>
        <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${completion.percentage}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className={`h-full rounded-full ${
              completion.percentage === 100
                ? 'bg-green-500'
                : completion.percentage >= 75
                ? 'bg-brand-500'
                : completion.percentage >= 50
                ? 'bg-yellow-500'
                : 'bg-orange-500'
            }`}
          />
        </div>
        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
          {completion.completed} of {completion.total} required fields completed
        </p>
      </div>

      {/* Section Breakdown */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Sections
        </h4>
        {completion.sections.map((section, index) => (
          <div key={index} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              {section.percentage === 100 ? (
                <CheckCircle className="w-4 h-4 text-green-500" />
              ) : (
                <Circle className="w-4 h-4 text-gray-400" />
              )}
              <span className="text-gray-700 dark:text-gray-300">{section.name}</span>
            </div>
            <span
              className={`font-medium ${
                section.percentage === 100
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
            >
              {section.completed}/{section.total}
            </span>
          </div>
        ))}
      </div>

      {/* Completion Message */}
      {completion.percentage === 100 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg"
        >
          <p className="text-xs text-green-700 dark:text-green-300 font-medium text-center">
            🎉 Profile complete! Ready to submit for review.
          </p>
        </motion.div>
      )}
    </div>
  );
}
