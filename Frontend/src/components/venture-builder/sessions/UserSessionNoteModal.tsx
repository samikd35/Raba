'use client';

import { useState, useEffect } from 'react';
import { X, FileText, Loader2, AlertCircle, Lightbulb, ListChecks, ArrowRight } from 'lucide-react';
import { getSessionNoteForUser } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import type { SessionNote } from '@/types/ventureBuilder';

interface UserSessionNoteModalProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function UserSessionNoteModal({ sessionId, isOpen, onClose }: UserSessionNoteModalProps) {
  const [note, setNote] = useState<SessionNote | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && sessionId) {
      loadNote();
    }
  }, [isOpen, sessionId]);

  const loadNote = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const noteData = await getSessionNoteForUser(sessionId, token);
      setNote(noteData);
    } catch (err: any) {
      console.error('Error loading session note:', err);
      setError(err.message || 'Failed to load session notes');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-2xl bg-white dark:bg-gray-900 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
                <FileText className="w-5 h-5 text-brand-600 dark:text-brand-400" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Session Notes
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mb-4" />
                <p className="text-gray-600 dark:text-gray-400">Loading session notes...</p>
              </div>
            ) : error ? (
              <div className="p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-error-600 dark:text-error-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-medium text-error-900 dark:text-error-200 mb-1">
                      Unable to load notes
                    </h3>
                    <p className="text-sm text-error-700 dark:text-error-300">{error}</p>
                  </div>
                </div>
              </div>
            ) : !note ? (
              <div className="text-center py-12">
                <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  No Notes Available
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  The session notes are not available yet.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Main Outcomes */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="p-1.5 bg-success-100 dark:bg-success-900/30 rounded">
                      <ListChecks className="w-4 h-4 text-success-600 dark:text-success-400" />
                    </div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      Main Session Outcomes
                    </h3>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {note.main_outcomes}
                    </p>
                  </div>
                </div>

                {/* Key Takeaways */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="p-1.5 bg-brand-100 dark:bg-brand-900/30 rounded">
                      <Lightbulb className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                    </div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      Key Takeaways
                    </h3>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {note.key_takeaways}
                    </p>
                  </div>
                </div>

                {/* Next Steps (if available) */}
                {note.next_steps && (
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <div className="p-1.5 bg-warning-100 dark:bg-warning-900/30 rounded">
                        <ArrowRight className="w-4 h-4 text-warning-600 dark:text-warning-400" />
                      </div>
                      <h3 className="font-semibold text-gray-900 dark:text-white">
                        Next Steps / Recommendations
                      </h3>
                    </div>
                    <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                      <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                        {note.next_steps}
                      </p>
                    </div>
                  </div>
                )}

                {/* Last updated */}
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Notes added on {new Date(note.created_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end p-6 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
