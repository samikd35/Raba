'use client';

import React from 'react';
import { motion } from 'framer-motion';
import type { ProfileFormData } from '@/types/cofounder';
import { Slider } from '@/components/ui/slider';

const ageImportanceOptions = [
  { value: 'important', title: 'Nice to Have', description: 'Weighted in matching' },
  { value: 'non_negotiable', title: 'Must Have', description: 'Hard filter' },
];

interface StepProps {
  formData: ProfileFormData;
  updateField: <K extends keyof ProfileFormData>(
    field: K,
    value: ProfileFormData[K]
  ) => void;
}

export default function Step6Review({ formData, updateField }: StepProps) {
  const MIN_AGE = 20;
  const MAX_AGE = 50;

  const toggleAgePreference = (enabled: boolean) => {
    updateField('age_preference', {
      ...formData.age_preference,
      enabled,
      min: enabled ? formData.age_preference.min || MIN_AGE : null,
      max: enabled ? formData.age_preference.max || MAX_AGE : null,
      importance: enabled ? formData.age_preference.importance || 'important' : null,
    });
  };

  const normalizeAgeValue = (value: number | null | undefined, fallback: number) => {
    if (typeof value === 'number' && !Number.isNaN(value)) {
      return Math.min(MAX_AGE, Math.max(MIN_AGE, value));
    }
    return fallback;
  };

  const ageMin = normalizeAgeValue(formData.age_preference.min, MIN_AGE);
  const ageMax = normalizeAgeValue(formData.age_preference.max, MAX_AGE);
  const sliderValue: number[] = [
    Math.min(ageMin, ageMax),
    Math.max(ageMin, ageMax),
  ];

  const handleAgeRangeChange = (value: number[]) => {
    if (!value || value.length < 2) return;
    const [min, max] = value;
    updateField('age_preference', {
      ...formData.age_preference,
      min,
      max,
    });
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Age Preference & Review
      </h2>

      {/* Age Preference Toggle */}
      <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={formData.age_preference.enabled}
            onChange={(e) => toggleAgePreference(e.target.checked)}
            className="w-5 h-5 text-brand-500 focus:ring-brand-500 rounded"
          />
          <div>
            <div className="font-medium text-gray-900 dark:text-white">
              Enable Age Preference (Optional)
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Filter cofounders by age range (20-50)
            </div>
          </div>
        </label>
      </div>

      {/* Age Range Settings */}
      {formData.age_preference.enabled && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="space-y-4 pl-4 border-l-4 border-brand-500 dark:border-brand-400"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Select Age Range (20-50)
            </label>
            <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <Slider
                value={sliderValue}
                min={MIN_AGE}
                max={MAX_AGE}
                step={1}
                onValueChange={handleAgeRangeChange}
                className="py-2"
              />
              <div className="flex items-center justify-between text-sm">
                <div className="flex flex-col">
                  <span className="text-xs uppercase text-gray-500 dark:text-gray-400">Minimum</span>
                  <span className="text-lg font-semibold text-gray-900 dark:text-white">{sliderValue[0]}</span>
                </div>
                <div className="h-6 w-px bg-gray-200 dark:bg-gray-700" />
                <div className="flex flex-col text-right">
                  <span className="text-xs uppercase text-gray-500 dark:text-gray-400">Maximum</span>
                  <span className="text-lg font-semibold text-gray-900 dark:text-white">{sliderValue[1]}</span>
                </div>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Age Match Importance
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {ageImportanceOptions.map((option) => (
                <label
                  key={option.value}
                  className="flex items-start gap-3 text-sm text-gray-700 dark:text-gray-300 cursor-pointer"
                >
                  <input
                    type="radio"
                    name="age-importance"
                    value={option.value}
                    checked={formData.age_preference.importance === option.value}
                    onChange={() =>
                      updateField('age_preference', {
                        ...formData.age_preference,
                        importance: option.value as 'important' | 'non_negotiable',
                      })
                    }
                    className="mt-1 h-4 w-4 text-brand-600 focus:ring-brand-500"
                  />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {option.title}
                    </div>
                    <div className="text-xs mt-1 text-gray-500 dark:text-gray-400">
                      {option.description}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* Profile Summary */}
      <div className="mt-8 p-6 bg-gradient-to-br from-brand-50 to-blue-50 dark:from-brand-900/20 dark:to-blue-900/20 border border-brand-200 dark:border-brand-800 rounded-lg">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Profile Summary
        </h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400">Name:</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {formData.first_name} {formData.last_name}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400">Background:</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {formData.professional_background || 'Not specified'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400">Industries:</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {formData.industries_of_interest.length} selected
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400">Commitment:</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {formData.expected_commitment}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400">Preferred Location:</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {formData.preferred_country}
            </span>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-brand-200 dark:border-brand-700">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Review your information above and click "Submit for Review" when ready. Our team will
            review your profile and notify you once it's approved.
          </p>
        </div>
      </div>
    </div>
  );
}
