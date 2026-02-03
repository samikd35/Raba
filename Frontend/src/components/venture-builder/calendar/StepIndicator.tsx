'use client';

import { Check } from 'lucide-react';

interface Step {
  number: number;
  title: string;
  path: string;
}

const STEPS: Step[] = [
  { number: 1, title: 'Connect Calendar', path: '/venture-builder/calendar' },
  { number: 2, title: 'Set Availability', path: '/venture-builder/settings' },
  { number: 3, title: 'Review & Finish', path: '/venture-builder/review' },
];

interface StepIndicatorProps {
  currentStep: 1 | 2 | 3;
}

export default function StepIndicator({ currentStep }: StepIndicatorProps) {
  return (
    <div className="w-full">
      <div className="flex items-center justify-center">
        {STEPS.map((step, index) => (
          <div key={step.number} className="flex items-center">
            {/* Step circle */}
            <div className="flex flex-col items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                  step.number < currentStep
                    ? 'bg-green-500 text-white'
                    : step.number === currentStep
                    ? 'bg-brand-600 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                }`}
              >
                {step.number < currentStep ? (
                  <Check className="w-5 h-5" />
                ) : (
                  step.number
                )}
              </div>
              <span
                className={`mt-2 text-xs font-medium ${
                  step.number === currentStep
                    ? 'text-brand-600 dark:text-brand-400'
                    : step.number < currentStep
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-gray-500 dark:text-gray-400'
                }`}
              >
                {step.title}
              </span>
            </div>

            {/* Connector line */}
            {index < STEPS.length - 1 && (
              <div
                className={`w-16 sm:w-24 h-0.5 mx-2 ${
                  step.number < currentStep
                    ? 'bg-green-500'
                    : 'bg-gray-200 dark:bg-gray-700'
                }`}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
