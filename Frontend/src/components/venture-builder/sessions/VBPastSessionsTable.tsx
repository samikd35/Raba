'use client';

import { ExternalLink, FileText, ChevronRight, Clock } from 'lucide-react';
import type { VBSession, SessionStatus } from '@/types/ventureBuilder';

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

interface VBPastSessionsTableProps {
  sessions: VBSession[];
  onViewSession: (sessionId: string) => void;
}

export default function VBPastSessionsTable({
  sessions,
  onViewSession,
}: VBPastSessionsTableProps) {
  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return {
      date: date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }),
      time: date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
      }),
    };
  };

  if (sessions.length === 0) {
    return (
      <div className="text-center py-12">
        <Clock className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">
          No past sessions
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Your completed sessions will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Date & Time
            </th>
            <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Founder
            </th>
            <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Project
            </th>
            <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Status
            </th>
            <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Notes
            </th>
            <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {sessions.map((session) => {
            const { date, time } = formatDateTime(session.session_datetime);
            const statusBadge = STATUS_BADGES[session.status] || STATUS_BADGES.pending;

            return (
              <tr
                key={session.id}
                className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <td className="py-4 px-4">
                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                    {date}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {time}
                  </div>
                </td>
                <td className="py-4 px-4">
                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                    {session.user_name || 'Unknown'}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {session.tenant_name || session.tenant_id}
                  </div>
                </td>
                <td className="py-4 px-4">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {session.project_name || 'Untitled Project'}
                  </div>
                </td>
                <td className="py-4 px-4">
                  <span
                    className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${statusBadge.bg} ${statusBadge.text}`}
                  >
                    {session.status}
                  </span>
                </td>
                <td className="py-4 px-4">
                  {session.has_notes ? (
                    <span className="inline-flex items-center gap-1 text-sm text-success-600 dark:text-success-400">
                      <FileText className="w-4 h-4" />
                      Added
                    </span>
                  ) : (
                    <span className="text-sm text-gray-400 dark:text-gray-500">
                      None
                    </span>
                  )}
                </td>
                <td className="py-4 px-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {session.project_id && (
                      <a
                        href={`/projects/${session.project_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                        Project
                      </a>
                    )}
                    <button
                      onClick={() => onViewSession(session.id)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded-lg transition-colors"
                    >
                      View
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
