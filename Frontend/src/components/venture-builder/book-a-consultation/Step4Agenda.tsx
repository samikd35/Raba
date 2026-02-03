'use client';

import React from 'react';
import { FileText, Lightbulb } from 'lucide-react';

interface Step4AgendaProps {
  agenda: string;
  onAgendaChange: (agenda: string) => void;
}

const EXAMPLE_TOPICS = [
  'Product-market fit validation',
  'Go-to-market strategy',
  'Fundraising preparation',
  'Team building and hiring',
  'Scaling operations',
  'Business model refinement',
];

export default function Step4Agenda({ agenda, onAgendaChange }: Step4AgendaProps) {
  const characterCount = agenda.length;
  const minChars = 10;
  const maxChars = 2000;

  // Enhanced validation
  const validateAgenda = () => {
    if (characterCount < minChars) {
      return {
        isValid: false,
        message: `Please provide at least ${minChars} characters to help the VB prepare effectively.`,
        type: 'error' as const,
      };
    }

    // Check for meaningful content (not just whitespace or repeated characters)
    const trimmedAgenda = agenda.trim();
    const uniqueChars = new Set(trimmedAgenda.toLowerCase()).size;

    if (uniqueChars < 10) {
      return {
        isValid: false,
        message: 'Please provide more detailed information about your goals and questions.',
        type: 'warning' as const,
      };
    }

    // Check for question marks or bullet points (indicates structured thinking)
    const hasQuestions = trimmedAgenda.includes('?');
    const hasBullets = /[•\-\*]/.test(trimmedAgenda);
    const hasNewlines = trimmedAgenda.includes('\n');

    if (!hasQuestions && !hasBullets && !hasNewlines && characterCount < 100) {
      return {
        isValid: true,
        message: 'Consider structuring your agenda with bullet points or specific questions for a more productive session.',
        type: 'info' as const,
      };
    }

    return {
      isValid: true,
      message: 'Your agenda looks good! The VB will review this before your session.',
      type: 'success' as const,
    };
  };

  const validation = validateAgenda();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Session Agenda
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Tell the Venture Builder what you'd like to discuss during your session.
        </p>
      </div>

      <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg flex items-start gap-3">
        <Lightbulb className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-blue-800 dark:text-blue-300">
            Get the Most Out of Your Session
          </p>
          <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
            Be specific about your challenges, questions, and goals. The more context you provide, the more valuable the session will be.
          </p>
        </div>
      </div>

      {/* Example Topics */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Common Topics (click to add)
        </label>
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_TOPICS.map((topic, index) => (
            <button
              key={index}
              onClick={() => {
                const currentAgenda = agenda.trim();
                const newTopic = currentAgenda ? `\n• ${topic}` : `• ${topic}`;
                onAgendaChange(agenda + newTopic);
              }}
              className="px-3 py-1.5 text-xs font-medium bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-700 rounded-full hover:bg-brand-100 dark:hover:bg-brand-800/30 transition-colors"
            >
              + {topic}
            </button>
          ))}
        </div>
      </div>

      {/* Agenda Text Area */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Your Questions & Topics *
        </label>
        <div className="relative">
          <textarea
            value={agenda}
            onChange={(e) => onAgendaChange(e.target.value)}
            placeholder="Example:&#10;• I'm struggling with product-market fit and need help validating my assumptions&#10;• Need guidance on our go-to-market strategy for East African markets&#10;• Want to discuss our fundraising deck and pitch"
            rows={10}
            maxLength={maxChars}
            className="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent resize-none"
          />
          <div className="absolute bottom-3 right-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400" />
            <span className={`text-xs ${
              characterCount < minChars
                ? 'text-red-600 dark:text-red-400'
                : characterCount >= maxChars
                ? 'text-yellow-600 dark:text-yellow-400'
                : 'text-gray-500 dark:text-gray-400'
            }`}>
              {characterCount}/{maxChars}
            </span>
          </div>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          Minimum {minChars} characters required. Be as detailed as possible to help the VB prepare.
        </p>
      </div>

      {/* Tips Section */}
      <div className="p-4 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Tips for a Productive Session:
        </p>
        <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
          <li>• Share specific challenges you're facing</li>
          <li>• Include relevant context about your business/project</li>
          <li>• Mention any decisions you need help making</li>
          <li>• List concrete questions you want answered</li>
        </ul>
      </div>

      {/* Enhanced Validation Message */}
      {characterCount >= minChars && (
        <div className={`p-4 rounded-lg border ${
          validation.type === 'success'
            ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700'
            : validation.type === 'info'
            ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700'
            : validation.type === 'warning'
            ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700'
            : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700'
        }`}>
          <p className={`text-sm ${
            validation.type === 'success'
              ? 'text-green-800 dark:text-green-300'
              : validation.type === 'info'
              ? 'text-blue-800 dark:text-blue-300'
              : validation.type === 'warning'
              ? 'text-yellow-800 dark:text-yellow-300'
              : 'text-red-800 dark:text-red-300'
          }`}>
            {validation.type === 'success' ? '✓ ' : validation.type === 'warning' ? '⚠ ' : 'ℹ '}
            {validation.message}
          </p>
        </div>
      )}
    </div>
  );
}
