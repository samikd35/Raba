'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  AlertCircle,
  Ban,
  Clock,
  UserX,
  Shield,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import type {
  MessagingError,
  MessagingErrorType,
} from '@/types/messagingErrors';
import {
  MESSAGING_ERROR_TITLES,
  MESSAGING_ERROR_ACTIONS,
  shouldShowRetry,
} from '@/types/messagingErrors';

interface MessageErrorModalProps {
  error: MessagingError | null;
  isOpen: boolean;
  onClose: () => void;
  onRetry?: () => void;
}

/**
 * Get icon component for error type
 */
function getErrorIcon(errorType: MessagingErrorType) {
  const iconMap: Record<MessagingErrorType, React.ReactNode> = {
    user_blocked: <Ban className="w-12 h-12 text-red-500" />,
    user_blocked_by_you: <UserX className="w-12 h-12 text-orange-500" />,
    rate_limit_exceeded: <Clock className="w-12 h-12 text-yellow-500" />,
    self_message: <AlertCircle className="w-12 h-12 text-blue-500" />,
    user_not_found: <UserX className="w-12 h-12 text-gray-500" />,
    thread_not_found: <AlertTriangle className="w-12 h-12 text-gray-500" />,
    unauthorized: <Shield className="w-12 h-12 text-red-500" />,
    encryption_failed: <AlertTriangle className="w-12 h-12 text-orange-500" />,
    decryption_failed: <AlertTriangle className="w-12 h-12 text-orange-500" />,
    websocket_auth_failed: <AlertCircle className="w-12 h-12 text-red-500" />,
    websocket_timeout: <Clock className="w-12 h-12 text-orange-500" />,
    unknown: <AlertCircle className="w-12 h-12 text-gray-500" />,
  };

  return iconMap[errorType] || iconMap.unknown;
}

/**
 * Get background color for error type
 */
function getErrorBgColor(errorType: MessagingErrorType): string {
  const colorMap: Record<MessagingErrorType, string> = {
    user_blocked: 'bg-red-50 dark:bg-red-900/20',
    user_blocked_by_you: 'bg-orange-50 dark:bg-orange-900/20',
    rate_limit_exceeded: 'bg-yellow-50 dark:bg-yellow-900/20',
    self_message: 'bg-blue-50 dark:bg-blue-900/20',
    user_not_found: 'bg-gray-50 dark:bg-gray-700/50',
    thread_not_found: 'bg-gray-50 dark:bg-gray-700/50',
    unauthorized: 'bg-red-50 dark:bg-red-900/20',
    encryption_failed: 'bg-orange-50 dark:bg-orange-900/20',
    decryption_failed: 'bg-orange-50 dark:bg-orange-900/20',
    websocket_auth_failed: 'bg-red-50 dark:bg-red-900/20',
    websocket_timeout: 'bg-orange-50 dark:bg-orange-900/20',
    unknown: 'bg-gray-50 dark:bg-gray-700/50',
  };

  return colorMap[errorType] || colorMap.unknown;
}

export default function MessageErrorModal({
  error,
  isOpen,
  onClose,
  onRetry,
}: MessageErrorModalProps) {
  if (!isOpen || !error) return null;

  const title = MESSAGING_ERROR_TITLES[error.type];
  const actions = MESSAGING_ERROR_ACTIONS[error.type];
  const showRetry = shouldShowRetry(error.type) && onRetry;
  const bgColor = getErrorBgColor(error.type);

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-md w-full overflow-hidden"
        >
          {/* Header with Icon */}
          <div className={`p-6 ${bgColor} border-b border-gray-200 dark:border-gray-700`}>
            <div className="flex flex-col items-center text-center">
              <div className="mb-4">
                {getErrorIcon(error.type)}
              </div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                {title}
              </h2>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {error.message}
              </p>
            </div>
          </div>

          {/* Body with Actions/Suggestions */}
          <div className="p-6">
            <div className="space-y-3">
              {actions.map((action, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 text-sm text-gray-600 dark:text-gray-400"
                >
                  <div className="mt-0.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500" />
                  </div>
                  <p>{action}</p>
                </div>
              ))}
            </div>

            {/* Additional Details */}
            {error.details && error.details !== error.message && (
              <div className="mt-4 p-3 bg-gray-100 dark:bg-gray-700/50 rounded-lg">
                <p className="text-xs text-gray-600 dark:text-gray-400 font-mono">
                  {error.details}
                </p>
              </div>
            )}

            {/* Status Code */}
            {error.statusCode && (
              <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 text-center">
                Error Code: {error.statusCode}
              </div>
            )}
          </div>

          {/* Footer with Actions */}
          <div className="flex items-center gap-3 p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30">
            {showRetry && (
              <button
                onClick={() => {
                  onRetry();
                  onClose();
                }}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-600 dark:bg-brand-500 text-white rounded-lg hover:bg-brand-700 dark:hover:bg-brand-600 transition-colors font-medium"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
            )}
            <button
              onClick={onClose}
              className={`${showRetry ? 'flex-1' : 'w-full'} px-4 py-2.5 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors font-medium`}
            >
              {showRetry ? 'Cancel' : 'Close'}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
