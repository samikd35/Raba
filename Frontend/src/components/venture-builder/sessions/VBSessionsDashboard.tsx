'use client';

import React, { useEffect, useState } from 'react';
import { Calendar, Clock, User, Mail, CheckCircle, XCircle, Filter, Loader2, AlertCircle } from 'lucide-react';
import { getVBSessions, completeSession, cancelSession } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import type { VBSession, SessionStatus } from '@/types/ventureBuilder';

export default function VBSessionsDashboard() {
  const [sessions, setSessions] = useState<VBSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<SessionStatus | 'all'>('all');
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [selectedSession, setSelectedSession] = useState<VBSession | null>(null);
  const [cancelReason, setCancelReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadSessions = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const data = await getVBSessions(token, {
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

  const handleCompleteSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to mark this session as completed?')) return;

    try {
      const token = authService.getCurrentToken();
      if (!token) throw new Error('Authentication required');

      await completeSession(sessionId, token);
      toast.success('Session marked as completed!');
      loadSessions();
    } catch (error: any) {
      console.error('Error completing session:', error);
      toast.error(error.message || 'Failed to complete session');
    }
  };

  const handleCancelSession = async () => {
    if (!selectedSession) return;
    if (!cancelReason.trim() || cancelReason.length < 10) {
      toast.error('Cancellation reason must be at least 10 characters');
      return;
    }

    try {
      setIsSubmitting(true);
      const token = authService.getCurrentToken();
      if (!token) throw new Error('Authentication required');

      await cancelSession(selectedSession.id, cancelReason, token);
      toast.success('Session canceled successfully. User has been notified and credits refunded.');
      setShowCancelModal(false);
      setSelectedSession(null);
      setCancelReason('');
      loadSessions();
    } catch (error: any) {
      console.error('Error canceling session:', error);
      toast.error(error.message || 'Failed to cancel session');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (status: SessionStatus) => {
    const config: Record<SessionStatus, { label: string; className: string }> = {
      confirmed: {
        label: 'Confirmed',
        className: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700',
      },
      completed: {
        label: 'Completed',
        className: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-700',
      },
      settled: {
        label: 'Settled',
        className: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-700',
      },
      canceled: {
        label: 'Canceled',
        className: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-600',
      },
    };

    const statusConfig = config[status];
    return (
      <span className={`px-3 py-1 text-xs font-medium rounded-full border ${statusConfig.className}`}>
        {statusConfig.label}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading sessions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-lg font-semibold text-red-900 dark:text-red-200 mb-2">
              Error Loading Sessions
            </h3>
            <p className="text-red-700 dark:text-red-300">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            My Sessions
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage your coaching sessions
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
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
          </div>
          <div className="px-4 py-2 bg-brand-100 dark:bg-brand-900/30 border border-brand-200 dark:border-brand-700 rounded-lg">
            <span className="text-sm font-semibold text-brand-700 dark:text-brand-300">
              {sessions.length} Sessions
            </span>
          </div>
        </div>
      </div>

      {/* Sessions List */}
      <div className="space-y-4">
        {sessions.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
            <Calendar className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              No Sessions Found
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {statusFilter !== 'all'
                ? `No sessions with status "${statusFilter}"`
                : 'No sessions scheduled yet'}
            </p>
          </div>
        ) : (
          sessions.map((session) => {
            const sessionDate = new Date(session.session_datetime);
            const isPast = sessionDate < new Date();
            const canComplete = session.status === 'confirmed' && isPast;
            const canCancel = session.status === 'confirmed' && !isPast;

            return (
              <div
                key={session.id}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      {getStatusBadge(session.status)}
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {session.credits_charged} credits
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-900 dark:text-white mb-2">
                      <Calendar className="w-4 h-4" />
                      <span className="font-semibold">
                        {sessionDate.toLocaleDateString('en-US', {
                          weekday: 'long',
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                      <Clock className="w-4 h-4" />
                      <span>
                        {sessionDate.toLocaleTimeString('en-US', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })} • {session.session_duration_minutes} minutes
                      </span>
                    </div>
                  </div>
                </div>

                {/* Client Info */}
                <div className="mb-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                  <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Client Information
                  </h4>
                  <div className="flex items-center gap-3">
                    {session.vb_picture && (
                      <img
                        src={session.vb_picture}
                        alt="Client"
                        className="w-10 h-10 rounded-full"
                      />
                    )}
                    <div>
                      <div className="flex items-center gap-2 text-gray-900 dark:text-white">
                        <User className="w-4 h-4" />
                        <span>{session.booked_by_user_id.substring(0, 8)}...</span>
                      </div>
                      {session.vb_email && (
                        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                          <Mail className="w-4 h-4" />
                          <span>{session.vb_email}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Agenda */}
                {session.agenda && (
                  <div className="mb-4">
                    <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                      Session Agenda
                    </h4>
                    <p className="text-sm text-gray-900 dark:text-white">{session.agenda}</p>
                  </div>
                )}

                {/* Actions */}
                {(canComplete || canCancel) && (
                  <div className="flex gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                    {canComplete && (
                      <button
                        onClick={() => handleCompleteSession(session.id)}
                        className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition-colors"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Mark as Completed
                      </button>
                    )}
                    {canCancel && (
                      <button
                        onClick={() => {
                          setSelectedSession(session);
                          setShowCancelModal(true);
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-colors"
                      >
                        <XCircle className="w-4 h-4" />
                        Cancel Session
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Cancel Modal */}
      {showCancelModal && selectedSession && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl max-w-md w-full p-6">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
              Cancel Session
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Please provide a reason for canceling this session. The user will be notified and credits will be refunded.
            </p>
            <textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 mb-4"
              rows={4}
              placeholder="Reason for cancellation (minimum 10 characters)..."
            />
            <div className="flex gap-3">
              <button
                onClick={handleCancelSession}
                disabled={isSubmitting || cancelReason.length < 10}
                className="flex-1 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Canceling...' : 'Confirm Cancellation'}
              </button>
              <button
                onClick={() => {
                  setShowCancelModal(false);
                  setSelectedSession(null);
                  setCancelReason('');
                }}
                disabled={isSubmitting}
                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
