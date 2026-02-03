'use client';

import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { COMMUNITY_DECLARATION_ITEMS } from '@/constants/communityDeclaration';

interface DeclarationProps {
  declarationChecks: boolean[];
  onToggle: (index: number) => void;
}

export default function Declaration({
  declarationChecks,
  onToggle,
}: DeclarationProps) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-brand-100 dark:bg-brand-900/30 mb-4">
          <ShieldCheck className="w-8 h-8 text-brand-600 dark:text-brand-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Community Member Declaration
        </h2>
        <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          Before creating your profile, please read and agree to the following community guidelines.
          These help us maintain a respectful and productive environment for everyone.
        </p>
      </div>

      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-6 border border-gray-200 dark:border-gray-600">
        <div className="space-y-4">
          {COMMUNITY_DECLARATION_ITEMS.map((item, index) => (
            <label
              key={index}
              className="flex items-start gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 cursor-pointer hover:border-brand-300 dark:hover:border-brand-600 transition-all group"
            >
              <input
                type="checkbox"
                checked={declarationChecks[index]}
                onChange={() => onToggle(index)}
                className="mt-0.5 w-5 h-5 text-brand-600 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-brand-500 dark:focus:ring-brand-400 focus:ring-2 cursor-pointer"
              />
              <span className="flex-1 text-sm text-gray-700 dark:text-gray-300 leading-relaxed group-hover:text-gray-900 dark:group-hover:text-white transition-colors">
                {item}
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <strong>Note:</strong> You must agree to all statements above to continue creating your cofounder profile.
          These guidelines help us build a trusted community focused on finding the right cofounders.
        </p>
      </div>
    </div>
  );
}
