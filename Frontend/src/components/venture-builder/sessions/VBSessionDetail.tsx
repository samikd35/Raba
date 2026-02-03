'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  AlertCircle,
  Calendar,
  Clock,
  User,
  Building2,
  Briefcase,
  ExternalLink,
  Save,
  CheckCircle,
  Loader2,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';
import { getVBSessions } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import type { VBSession, SessionNote, SessionStatus } from '@/types/ventureBuilder';

const STATUS_BADGES: Record<SessionStatus, { bg: string; text: string }> = {
  confirmed: {
    bg: 'bg-blue-light-100 dark:bg-blue-light-900/40',
    text: 'text-blue-light-700 dark:text-blue-light-300',
  },
  completed: {
    bg: 'bg-success-100 dark:bg-success-900/40',
    text: 'text-success-700 dark:text-success-300',
  },
  settled: {
    bg: 'bg-brand-100 dark:bg-brand-900/40',
    text: 'text-brand-700 dark:text-brand-300',
  },
  canceled: {
    bg: 'bg-gray-100 dark:bg-gray-800',
    text: 'text-gray-500 dark:text-gray-400',
  },
  pending: {
    bg: 'bg-warning-100 dark:bg-warning-900/40',
    text: 'text-warning-700 dark:text-warning-300',
  },
};

interface VBSessionDetailProps {
  sessionId: string;
  onBack?: () => void;
}

export default function VBSessionDetail({ sessionId, onBack }: VBSessionDetailProps) {
  const router = useRouter();

  const [session, setSession] = useState<VBSession | null>(null);
  const [note, setNote] = useState<SessionNote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasFetched, setHasFetched] = useState(false);

  // Form state
  const [mainOutcomes, setMainOutcomes] = useState('');
  const [keyTakeaways, setKeyTakeaways] = useState('');
  const [nextSteps, setNextSteps] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);

  useEffect(() => {
    loadSessionData();
  }, [sessionId]);

  const loadSessionData = async () => {
    try {
      setError(null);

      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      // Load session details
      const sessions = await getVBSessions(token, {});
      const foundSession = sessions.find((s) => s.id === sessionId);

      if (!foundSession) {
        throw new Error('Session not found');
      }

      setSession(foundSession);

      // Try to load existing note
      try {
        const existingNote = await ventureBuilderAPI.notes.getSessionNoteVB(sessionId);
        setNote(existingNote);
        setMainOutcomes(existingNote.main_outcomes || '');
        setKeyTakeaways(existingNote.key_takeaways || '');
        setNextSteps(existingNote.next_steps || '');
      } catch (noteError: any) {
        // Note doesn't exist yet, which is fine
        if (!noteError.message?.includes('404') && !noteError.message?.includes('not found')) {
          console.error('Error loading note:', noteError);
        }
      }

      setHasFetched(true);
    } catch (error: any) {
      console.error('Error loading session:', error);
      setError(error.message || 'Failed to load session details');
      setHasFetched(true);
    }
  };

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      router.push('/workspace/vb-portal/sessions');
    }
  };

  const handleSaveNotes = async () => {
    if (mainOutcomes.length < 10) {
      toast.error('Main outcomes must be at least 10 characters');
      return;
    }
    if (keyTakeaways.length < 10) {
      toast.error('Key takeaways must be at least 10 characters');
      return;
    }

    try {
      setIsSaving(true);

      if (note) {
        await ventureBuilderAPI.notes.update(note.id, {
          main_outcomes: mainOutcomes,
          key_takeaways: keyTakeaways,
          next_steps: nextSteps || undefined,
          visible_to_user: true,
        });
      } else {
        const newNote = await ventureBuilderAPI.notes.create({
          vb_session_id: sessionId,
          main_outcomes: mainOutcomes,
          key_takeaways: keyTakeaways,
          next_steps: nextSteps || undefined,
          visible_to_user: true,
        });
        setNote(newNote);
      }

      toast.success('Notes saved successfully!');
    } catch (error: any) {
      console.error('Error saving notes:', error);
      toast.error(error.message || 'Failed to save notes');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveAndComplete = async () => {
    if (mainOutcomes.length < 10) {
      toast.error('Main outcomes must be at least 10 characters');
      return;
    }
    if (keyTakeaways.length < 10) {
      toast.error('Key takeaways must be at least 10 characters');
      return;
    }

    try {
      setIsCompleting(true);

      if (note) {
        await ventureBuilderAPI.notes.update(note.id, {
          main_outcomes: mainOutcomes,
          key_takeaways: keyTakeaways,
          next_steps: nextSteps || undefined,
          visible_to_user: true,
        });
      } else {
        await ventureBuilderAPI.notes.create({
          vb_session_id: sessionId,
          main_outcomes: mainOutcomes,
          key_takeaways: keyTakeaways,
          next_steps: nextSteps || undefined,
          visible_to_user: true,
        });
      }

      await ventureBuilderAPI.sessions.updateStatus(sessionId, 'completed');

      toast.success('Session completed with notes!');
      handleBack();
    } catch (error: any) {
      console.error('Error completing session:', error);
      toast.error(error.message || 'Failed to complete session');
    } finally {
      setIsCompleting(false);
    }
  };

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return {
      date: date.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      }),
      time: date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
      }),
    };
  };

  if (error || (!session && hasFetched)) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <div className="p-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-6 h-6 text-error-600 dark:text-error-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-lg font-semibold text-error-900 dark:text-error-200 mb-2">
                  Error Loading Session
                </h3>
                <p className="text-error-700 dark:text-error-300">
                  {error || 'Session not found'}
                </p>
                <button
                  onClick={handleBack}
                  className="mt-4 px-4 py-2 bg-error-600 hover:bg-error-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Back to Sessions
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  const { date, time } = formatDateTime(session.session_datetime);
  const statusBadge = STATUS_BADGES[session.status] || STATUS_BADGES.pending;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Back Button */}
        <button
          onClick={handleBack}
          className="inline-flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Sessions
        </button>

        {/* Header */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-brand-100 dark:bg-brand-900/20 rounded-lg">
                <Calendar className="w-6 h-6 text-brand-600 dark:text-brand-400" />
              </div>
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                    Session Details
                  </h1>
                  <span
                    className={`inline-flex px-2.5 py-1 text-xs font-semibold rounded-full ${statusBadge.bg} ${statusBadge.text}`}
                  >
                    {session.status}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4" />
                    {date} at {time}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <User className="w-4 h-4" />
                    {session.user_name || 'Unknown Founder'}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Building2 className="w-4 h-4" />
                    {session.tenant_name || session.tenant_id}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Two-Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left Column - Project Snapshot (40%) */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 sticky top-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Briefcase className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Project Snapshot
                  </h2>
                </div>
                {session.project_id && (
                  <a
                    href={`/projects/${session.project_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded-lg transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Open Project
                  </a>
                )}
              </div>

              {session.project_id ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Project Name
                    </label>
                    <p className="text-gray-900 dark:text-white font-medium">
                      {session.project_name || 'Untitled Project'}
                    </p>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Organization
                    </label>
                    <p className="text-gray-900 dark:text-white">
                      {session.tenant_name || session.tenant_id}
                    </p>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Founder
                    </label>
                    <p className="text-gray-900 dark:text-white">
                      {session.user_name || 'Unknown'}
                    </p>
                  </div>

                  <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Click "Open Project" to view the full project details in a new tab.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Briefcase className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-600 dark:text-gray-400">
                    No project associated with this session.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Right Column - Coaching Notes Form (60%) */}
          <div className="lg:col-span-3">
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
                Coaching Notes
              </h2>

              <div className="space-y-6">
                {/* Main Outcomes */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Main Session Outcomes <span className="text-error-500">*</span>
                  </label>
                  <textarea
                    value={mainOutcomes}
                    onChange={(e) => setMainOutcomes(e.target.value)}
                    placeholder="What were the main outcomes of this session? What was accomplished?"
                    rows={5}
                    className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-800 focus:border-brand-300 focus:outline-none focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800 resize-none"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {mainOutcomes.length}/5000 characters (minimum 10)
                  </p>
                </div>

                {/* Key Takeaways */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Key Takeaways <span className="text-error-500">*</span>
                  </label>
                  <textarea
                    value={keyTakeaways}
                    onChange={(e) => setKeyTakeaways(e.target.value)}
                    placeholder="What are the key insights or learnings from this session?"
                    rows={5}
                    className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-800 focus:border-brand-300 focus:outline-none focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800 resize-none"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {keyTakeaways.length}/5000 characters (minimum 10)
                  </p>
                </div>

                {/* Next Steps */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Next Steps / Recommendations
                  </label>
                  <textarea
                    value={nextSteps}
                    onChange={(e) => setNextSteps(e.target.value)}
                    placeholder="What should the founder work on next? Any recommendations?"
                    rows={4}
                    className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-800 focus:border-brand-300 focus:outline-none focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800 resize-none"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {nextSteps.length}/2000 characters (optional)
                  </p>
                </div>

                {/* Note about visibility */}
                <div className="p-3 bg-blue-light-50 dark:bg-blue-light-900/20 border border-blue-light-200 dark:border-blue-light-800 rounded-lg">
                  <p className="text-xs text-blue-light-700 dark:text-blue-light-300">
                    <strong>Note:</strong> These notes will be visible to the founder after you save them.
                  </p>
                </div>

                {/* Last updated */}
                {note && (
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    Last updated: {new Date(note.updated_at).toLocaleString()}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <button
                    onClick={handleSaveNotes}
                    disabled={isSaving || isCompleting}
                    className="inline-flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isSaving ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4" />
                        Save Notes
                      </>
                    )}
                  </button>

                  {session.status !== 'completed' && session.status !== 'settled' && (
                    <button
                      onClick={handleSaveAndComplete}
                      disabled={isSaving || isCompleting}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-success-600 text-white hover:bg-success-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {isCompleting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Completing...
                        </>
                      ) : (
                        <>
                          <CheckCircle className="w-4 h-4" />
                          Save & Complete
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
