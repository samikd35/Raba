'use client';

import React, { useState, useEffect } from 'react';
import { X, Calendar, AlertCircle, Check } from 'lucide-react';

interface CalendarModalProps {
  isOpen: boolean;
  onClose: () => void;
  calendarUrl: string;
  onConfirmTime: (datetime: string) => void;
  ventureBuilderName: string;
}

export default function CalendarModal({
  isOpen,
  onClose,
  calendarUrl,
  onConfirmTime,
  ventureBuilderName,
}: CalendarModalProps) {
  const [manualDatetime, setManualDatetime] = useState('');
  const [iframeError, setIframeError] = useState(false);
  const [iframeLoaded, setIframeLoaded] = useState(false);

  useEffect(() => {
    // Check for iframe loading errors (X-Frame-Options)
    const checkIframeLoad = setTimeout(() => {
      if (!iframeLoaded && isOpen) {
        setIframeError(true);
      }
    }, 5000); // 5 second timeout

    return () => clearTimeout(checkIframeLoad);
  }, [iframeLoaded, isOpen]);

  const handleConfirm = () => {
    if (manualDatetime) {
      onConfirmTime(manualDatetime);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
      <div className="w-full h-full max-w-7xl max-h-[90vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Choose a Time
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Select an available time slot with {ventureBuilderName}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-gray-600 dark:text-gray-400" />
          </button>
        </div>

        {/* Content - Split Layout */}
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
          {/* Left Side - Calendar Iframe */}
          <div className="flex-1 relative bg-gray-50 dark:bg-gray-800 overflow-auto">
            {!iframeError ? (
              <>
                {!iframeLoaded && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 dark:border-brand-400"></div>
                  </div>
                )}
                <iframe
                  src={calendarUrl}
                  width="100%"
                  height="100%"
                  frameBorder="0"
                  title="Booking Calendar"
                  onLoad={() => setIframeLoaded(true)}
                  onError={() => setIframeError(true)}
                  className={iframeLoaded ? 'opacity-100' : 'opacity-0'}
                  sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                />
              </>
            ) : (
              /* X-Frame-Options Fallback */
              <div className="flex flex-col items-center justify-center h-full p-8 text-center">
                <div className="w-20 h-20 bg-yellow-100 dark:bg-yellow-900/30 rounded-full flex items-center justify-center mb-4">
                  <AlertCircle className="w-10 h-10 text-yellow-600 dark:text-yellow-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  Calendar Embedding Blocked
                </h3>
                <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md">
                  The calendar cannot be embedded due to security restrictions (X-Frame-Options).
                  Please use the manual date/time selector on the right, or open the calendar in a new window.
                </p>
                <a
                  href={calendarUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-6 py-3 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium transition-colors inline-flex items-center gap-2"
                >
                  <Calendar className="w-5 h-5" />
                  Open Calendar in New Window
                </a>
              </div>
            )}
          </div>

          {/* Right Side - Session Summary & Manual Input */}
          <div className="w-full lg:w-96 bg-white dark:bg-gray-900 border-t lg:border-t-0 lg:border-l border-gray-200 dark:border-gray-700 p-6 flex flex-col">
            <div className="flex-1 space-y-6">
              {/* Session Summary */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Session Details
                </h3>
                <div className="space-y-3">
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Venture Builder</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{ventureBuilderName}</p>
                  </div>
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Duration</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">60 minutes</p>
                  </div>
                </div>
              </div>

              {/* Manual Time Selection */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                  Manual Time Selection
                </h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
                  Can't find a suitable time? Enter your preferred date and time manually.
                </p>
                <input
                  type="datetime-local"
                  value={manualDatetime}
                  onChange={(e) => setManualDatetime(e.target.value)}
                  className="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
                />
              </div>

              {/* Info Notice */}
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
                <p className="text-xs text-blue-800 dark:text-blue-300">
                  <strong>Note:</strong> All times are displayed in your local timezone. You'll receive a calendar invitation after confirming.
                </p>
              </div>
            </div>

            {/* Confirm Button */}
            <button
              onClick={handleConfirm}
              disabled={!manualDatetime}
              className={`mt-6 w-full py-4 px-6 rounded-lg text-base font-semibold transition-all duration-200 flex items-center justify-center gap-2 ${
                manualDatetime
                  ? 'bg-brand-500 hover:bg-brand-600 text-white shadow-md hover:shadow-lg'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 cursor-not-allowed'
              }`}
            >
              <Check className="w-5 h-5" />
              Confirm Time Selection
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
