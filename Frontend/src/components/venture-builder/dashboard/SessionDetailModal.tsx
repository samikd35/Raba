'use client';

import { useState } from 'react';
import {
  X,
  Calendar,
  Clock,
  User,
  Mail,
  CheckCircle,
  XCircle,
  Loader2,
  FileText,
} from 'lucide-react';
import { completeSession, cancelSession } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import type { VBSession, SessionStatus } from '@/types/ventureBuilder';

interface SessionDetailModalProps {
  session: VBSession;
  onClose: () => void;
  onSessionUpdated: () => void;
}

export default function SessionDetailModal({
  session,
  onClose,
  onSessionUpdated,
}: SessionDetailModalProps) {
  const [showCancelForm, setShowCancelForm] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const sessionDate = new Date(session.session_datetime);
  const isPast = sessionDate < new Date();
  const canComplete = session.status === 'confirmed' && isPast;
  const canCancel = session.status === 'confirmed' && !isPast;

  const getStatusConfig = (status: SessionStatus) => {
    const config: Record<SessionStatus, { label: string; className: string }> = {
      confirmed: {
        label: 'Confirmed',
        className: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
      },
      completed: {
        label: 'Completed',
        className: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
      },
      settled: {
        label: 'Settled',
        className: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
      },
      canceled: {
        label: 'Canceled',
        className: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400',
      },
      pending: {
        label: 'Pending',
        className: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
      },
    };
    return config[status] || config.pending;
  };

  const handleComplete = async () => {
    if (!confirm('Are you sure you want to mark this session as completed?')) return;

    try {
      setIsSubmitting(true);
      const token = authService.getCurrentToken();
      if (!token) throw new Error('Authentication required');

      await completeSession(session.id, token);
      toast.success('Session marked as completed!');
      onSessionUpdated();
      onClose();
    } catch (error: any) {
      console.error('Error completing session:', error);
      toast.error(error.message || 'Failed to complete session');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!cancelReason.trim() || cancelReason.length < 10) {
      toast.error('Cancellation reason must be at least 10 characters');
      return;
    }

    try {
      setIsSubmitting(true);
      const token = authService.getCurrentToken();
      if (!token) throw new Error('Authentication required');

      await cancelSession(session.id, cancelReason, token);
      toast.success('Session canceled successfully. User has been notified and credits refunded.');
      onSessionUpdated();
      onClose();
    } catch (error: any) {
      console.error('Error canceling session:', error);
      toast.error(error.message || 'Failed to cancel session');
    } finally {
      setIsSubmitting(false);
    }
  };

  const statusConfig = getStatusConfig(session.status);

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-900 rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Session Details
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Status Badge */}
          <div className="flex items-center justify-between">
            <span className={`px-4 py-1.5 text-sm font-medium rounded-full ${statusConfig.className}`}>
              {statusConfig.label}
            </span>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {session.credits_charged} credits
            </span>
          </div>

          {/* Date & Time */}
          <div className="space-y-3">
            <div className="flex items-center gap-3 text-gray-900 dark:text-white">
              <Calendar className="w-5 h-5 text-gray-400" />
              <span className="font-medium">
                {sessionDate.toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </span>
            </div>
            <div className="flex items-center gap-3 text-gray-600 dark:text-gray-400">
              <Clock className="w-5 h-5 text-gray-400" />
              <span>
                {sessionDate.toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                })} • {session.session_duration_minutes} minutes
              </span>
            </div>
          </div>

          {/* Client Info */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              Client Information
            </h4>
            <div className="flex items-center gap-3">
              {session.vb_picture ? (
                <img
                  src={session.vb_picture}
                  alt="Client"
                  className="w-12 h-12 rounded-full object-cover"
                />
              ) : (
                <div className="w-12 h-12 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
                  <User className="w-6 h-6 text-gray-400" />
                </div>
              )}
              <div>
                <div className="flex items-center gap-2 text-gray-900 dark:text-white">
                  <User className="w-4 h-4 text-gray-400" />
                  <span className="font-medium">
                    {session.user_name || session.booked_by_user_id.substring(0, 8) + '...'}
                  </span>
                </div>
                {session.vb_email && (
                  <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 mt-1">
                    <Mail className="w-4 h-4" />
                    <span>{session.vb_email}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Agenda */}
          {session.agenda && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-gray-400" />
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Session Agenda
                </h4>
              </div>
              <p className="text-sm text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                {session.agenda}
              </p>
            </div>
          )}

          {/* Cancel Form */}
          {showCancelForm && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <h4 className="text-sm font-semibold text-red-900 dark:text-red-200 mb-2">
                Cancel Session
              </h4>
              <p className="text-xs text-red-700 dark:text-red-300 mb-3">
                Please provide a reason for canceling. The user will be notified and credits refunded.
              </p>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                className="w-full px-3 py-2 border border-red-200 dark:border-red-800 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500 text-sm"
                rows={3}
                placeholder="Reason for cancellation (minimum 10 characters)..."
              />
              <div className="flex gap-2 mt-3">
                <button
                  onClick={handleCancel}
                  disabled={isSubmitting || cancelReason.length < 10}
                  className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Canceling...
                    </span>
                  ) : (
                    'Confirm Cancellation'
                  )}
                </button>
                <button
                  onClick={() => {
                    setShowCancelForm(false);
                    setCancelReason('');
                  }}
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        {(canComplete || canCancel) && !showCancelForm && (
          <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex gap-3">
            {canComplete && (
              <button
                onClick={handleComplete}
                disabled={isSubmitting}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {isSubmitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle className="w-4 h-4" />
                )}
                Mark as Completed
              </button>
            )}
            {canCancel && (
              <button
                onClick={() => setShowCancelForm(true)}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <XCircle className="w-4 h-4" />
                Cancel Session
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
