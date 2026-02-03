'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Calendar, List, AlertCircle } from 'lucide-react';
import { getVBSessions } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import VBSessionsCalendarView from '@/components/venture-builder/dashboard/VBSessionsCalendarView';
import VBPastSessionsTable from './VBPastSessionsTable';
import type { VBSession } from '@/types/ventureBuilder';

type ViewMode = 'upcoming' | 'past';

export default function VBSessionsList() {
  const router = useRouter();
  const [viewMode, setViewMode] = useState<ViewMode>('upcoming');
  const [pastSessions, setPastSessions] = useState<VBSession[]>([]);
  const [pastError, setPastError] = useState<string | null>(null);
  const [hasFetchedPast, setHasFetchedPast] = useState(false);

  // Load past sessions when switching to past view (lazy load)
  useEffect(() => {
    if (viewMode === 'past' && !hasFetchedPast) {
      loadPastSessions();
    }
  }, [viewMode, hasFetchedPast]);

  const loadPastSessions = async () => {
    try {
      setPastError(null);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const data = await getVBSessions(token, {});

      // Filter to only past sessions (completed, settled, canceled or past date)
      const now = new Date();
      const past = data.filter((session) => {
        const sessionDate = new Date(session.session_datetime);
        return (
          sessionDate < now ||
          ['completed', 'settled', 'canceled'].includes(session.status)
        );
      });

      // Sort by date descending (most recent first)
      past.sort(
        (a, b) =>
          new Date(b.session_datetime).getTime() -
          new Date(a.session_datetime).getTime()
      );

      setPastSessions(past);
      setHasFetchedPast(true);
    } catch (error: any) {
      console.error('Error fetching past sessions:', error);
      setPastError(error.message || 'Failed to load past sessions');
      toast.error(error.message || 'Failed to load past sessions');
    }
  };

  const handleViewSession = (sessionId: string) => {
    router.push(`/workspace/vb-portal/sessions/${sessionId}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Sessions
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            View and manage your coaching sessions with founders.
          </p>
        </div>

        {/* View Toggle */}
        <div className="mb-6">
          <div className="inline-flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode('upcoming')}
              className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                viewMode === 'upcoming'
                  ? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              <Calendar className="w-4 h-4" />
              Upcoming
            </button>
            <button
              onClick={() => setViewMode('past')}
              className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                viewMode === 'past'
                  ? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              <List className="w-4 h-4" />
              Past
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          {viewMode === 'upcoming' ? (
            <VBSessionsCalendarView />
          ) : pastError ? (
            <div className="p-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-6 h-6 text-error-600 dark:text-error-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-lg font-semibold text-error-900 dark:text-error-200 mb-2">
                    Error Loading Sessions
                  </h3>
                  <p className="text-error-700 dark:text-error-300">{pastError}</p>
                  <button
                    onClick={() => {
                      setHasFetchedPast(false);
                      loadPastSessions();
                    }}
                    className="mt-4 px-4 py-2 bg-error-600 hover:bg-error-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <VBPastSessionsTable
              sessions={pastSessions}
              onViewSession={handleViewSession}
            />
          )}
        </div>
      </div>
    </div>
  );
}
