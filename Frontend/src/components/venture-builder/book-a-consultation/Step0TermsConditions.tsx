'use client';

import React, { useState } from 'react';
import { Check, ExternalLink } from 'lucide-react';

interface Step0TermsConditionsProps {
  termsAccepted: boolean;
  onToggle: (accepted: boolean, version: string) => void;
}

const TERMS_VERSION = 'v1.0.2024-12-31';

const BOOKING_TERMS = [
  'I understand that booking a session will deduct credits from my account balance.',
  'I commit to attending the scheduled session at the agreed time.',
  'I understand that cancellations must be made at least 24 hours in advance for a refund.',
  'I agree to come prepared with specific questions and topics to discuss.',
  'I understand that the Venture Builder may take notes during our session.',
  'I agree to the Venture Builder\'s session policies and guidelines.',
];

export default function Step0TermsConditions({ termsAccepted, onToggle }: Step0TermsConditionsProps) {
  const [viewedFullTerms, setViewedFullTerms] = useState(false);

  const handleToggle = (checked: boolean) => {
    onToggle(checked, TERMS_VERSION);

    // Log T&C acceptance metadata
    if (checked) {
      console.log('Terms accepted:', {
        version: TERMS_VERSION,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
      });
    }
  };

  const handleViewFullTerms = () => {
    setViewedFullTerms(true);
    // TODO: Open full terms modal or navigate to full terms page
    window.open('/terms-and-conditions', '_blank');
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Booking Terms & Conditions
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Please review and accept the following terms before proceeding with your booking.
        </p>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">Version: {TERMS_VERSION}</span>
          <span className="text-gray-300 dark:text-gray-600">•</span>
          <button
            onClick={handleViewFullTerms}
            className="text-xs text-brand-600 dark:text-brand-400 hover:underline flex items-center gap-1"
          >
            View full Terms & Conditions
            <ExternalLink className="w-3 h-3" />
          </button>
        </div>
      </div>

      <div className="space-y-4 p-6 bg-brand-50 dark:bg-brand-900/20 rounded-xl border border-brand-200 dark:border-brand-700">
        {BOOKING_TERMS.map((term, index) => (
          <div key={index} className="flex items-start gap-3">
            <div className="w-5 h-5 rounded-full bg-brand-500 dark:bg-brand-400 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Check className="w-3 h-3 text-white" />
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              {term}
            </p>
          </div>
        ))}
      </div>

      <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg">
        <p className="text-sm text-yellow-800 dark:text-yellow-300">
          <strong>Note:</strong> Sessions are 60 minutes long. Please ensure you have a stable internet connection and a quiet environment for the call.
        </p>
      </div>

      {/* Credit Deduction Banner */}
      <div className="p-4 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700 rounded-lg">
        <p className="text-sm text-brand-800 dark:text-brand-300">
          <strong>💳 Credit Deduction:</strong> Booking this session will deduct credits from your workspace balance. The exact amount will be shown in the credit check step.
        </p>
      </div>

      <label className="flex items-start gap-3 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
        <input
          type="checkbox"
          checked={termsAccepted}
          onChange={(e) => handleToggle(e.target.checked)}
          className="w-5 h-5 text-brand-500 dark:text-brand-400 rounded border-gray-300 dark:border-gray-600 focus:ring-brand-500 dark:focus:ring-brand-400 mt-0.5"
        />
        <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">
          I have read and accept all the terms and conditions listed above (Version {TERMS_VERSION})
        </span>
      </label>
    </div>
  );
}
