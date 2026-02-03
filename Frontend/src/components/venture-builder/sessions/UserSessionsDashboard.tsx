'use client';

import React, { useEffect, useState } from 'react';
import { Calendar, Clock, User, Filter, Loader2, AlertCircle, FileText, AlertTriangle } from 'lucide-react';
import { getUserSessions } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import Link from 'next/link';
import type { VBSession, SessionStatus, Dispute } from '@/types/ventureBuilder';
import UserSessionNoteModal from './UserSessionNoteModal';
import CreateDisputeModal from '../disputes/CreateDisputeModal';

export default function UserSessionsDashboard() {
  const [sessions, setSessions] = useState<VBSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<SessionStatus | 'all'>('all');
  const [selectedSessionForNotes, setSelectedSessionForNotes] = useState<string | null>(null);
  const [selectedSessionForDispute, setSelectedSessionForDispute] = useState<string | null>(null);

  const loadSessions = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const token = authService.getCurrentToken();
      if (!token) throw new Error('Authentication required');

      const data = await getUserSessions(token, {
        status_filter: statusFilter !== 'all' ? statusFilter : undefined,
      });
      setSessions(data);
    } catch (error: any) {
      console.error('Error fetching sessions:', error);
      setError(error.message || 'Failed to load sessions');
      toast.error(error.message || 'Failed to load sessions');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [statusFilter]);

  const getStatusBadge = (status: SessionStatus) => {
    const config: Record<SessionStatus, { label: string; className: string }> = {
      pending: { label: 'Pending', className: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300' },
      confirmed: { label: 'Confirmed', className: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' },
      completed: { label: 'Completed', className: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' },
      settled: { label: 'Settled', className: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300' },
      canceled: { label: 'Canceled', className: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400' },
    };
    return (
      <span className={`px-3 py-1 text-xs font-medium rounded-full ${config[status].className}`}>
        {config[status].label}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
        <p className="text-red-700 dark:text-red-300 mt-2">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">My Sessions</h1>
          <p className="text-gray-600 dark:text-gray-400">View your coaching sessions</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as SessionStatus | 'all')}
            className="px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="all">All Status</option>
            <option value="confirmed">Confirmed</option>
            <option value="completed">Completed</option>
            <option value="settled">Settled</option>
            <option value="canceled">Canceled</option>
          </select>
          <Link
            href="/workspace/vb-browse"
            className="px-6 py-3 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium transition-colors"
          >
            Book New Session
          </Link>
        </div>
      </div>

      <div className="space-y-4">
        {sessions.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
            <Calendar className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">No Sessions Found</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {statusFilter !== 'all' ? `No sessions with status "${statusFilter}"` : 'No sessions booked yet'}
            </p>
            <Link
              href="/workspace/vb-browse"
              className="inline-block px-6 py-3 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium transition-colors"
            >
              Browse Venture Builders
            </Link>
          </div>
        ) : (
          sessions.map((session) => {
            const sessionDate = new Date(session.session_datetime);
            return (
              <div key={session.id} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      {getStatusBadge(session.status)}
                      <span className="text-sm text-gray-500 dark:text-gray-400">{session.credits_charged} credits</span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-900 dark:text-white mb-2">
                      <Calendar className="w-4 h-4" />
                      <span className="font-semibold">
                        {sessionDate.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                      <Clock className="w-4 h-4" />
                      <span>{sessionDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })} • {session.session_duration_minutes} minutes</span>
                    </div>
                  </div>
                </div>
                {session.agenda && (
                  <div className="mb-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                    <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Session Agenda</h4>
                    <p className="text-sm text-gray-900 dark:text-white">{session.agenda}</p>
                  </div>
                )}
                {/* Action buttons for completed/settled sessions */}
                {(session.status === 'completed' || session.status === 'settled') && (
                  <div className="flex flex-wrap items-center gap-4">
                    {session.has_notes && (
                      <button
                        onClick={() => setSelectedSessionForNotes(session.id)}
                        className="flex items-center gap-2 text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 hover:underline transition-colors"
                      >
                        <FileText className="w-4 h-4" />
                        <span>View session notes</span>
                      </button>
                    )}
                    <button
                      onClick={() => setSelectedSessionForDispute(session.id)}
                      className="flex items-center gap-2 text-sm text-warning-600 dark:text-warning-400 hover:text-warning-700 dark:hover:text-warning-300 hover:underline transition-colors"
                    >
                      <AlertTriangle className="w-4 h-4" />
                      <span>Report Issue</span>
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Session Notes Modal */}
      <UserSessionNoteModal
        sessionId={selectedSessionForNotes || ''}
        isOpen={!!selectedSessionForNotes}
        onClose={() => setSelectedSessionForNotes(null)}
      />

      {/* Create Dispute Modal */}
      <CreateDisputeModal
        sessionId={selectedSessionForDispute || ''}
        isOpen={!!selectedSessionForDispute}
        onClose={() => setSelectedSessionForDispute(null)}
        onSuccess={() => {
          setSelectedSessionForDispute(null);
          // Optionally refresh sessions or show a success message
        }}
      />
    </div>
  );
}
