'use client';

import React, { useState } from 'react';
import { X, AlertTriangle, User, MessageSquare, Calendar, CheckCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { reportAPI } from '@/lib/api/reportService';
import type { Report } from '@/types/reports';
import { REPORT_REASON_LABELS } from '@/types/reports';
import { cn } from '@/lib/utils';

interface ReportDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: Report;
  onResolved: () => void;
}

export default function ReportDetailModal({
  isOpen,
  onClose,
  report,
  onResolved,
}: ReportDetailModalProps) {
  const [resolutionStatus, setResolutionStatus] = useState<'REVIEWED' | 'ACTIONED' | 'NO_ACTION'>('REVIEWED');
  const [adminNotes, setAdminNotes] = useState('');
  const [actionTaken, setActionTaken] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleResolve = async () => {
    try {
      setIsSubmitting(true);

      await reportAPI.admin.resolveReport(report.id, {
        status: resolutionStatus,
        admin_notes: adminNotes.trim() || undefined,
        action_taken: actionTaken.trim() || undefined,
      });

      toast.success('Report resolved successfully');
      onResolved();
    } catch (error: any) {
      console.error('Failed to resolve report:', error);
      toast.error(error.message || 'Failed to resolve report');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isResolved = report.status !== 'PENDING';

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-5xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-red-500" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              Report Details
            </h2>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors disabled:opacity-50"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-6 space-y-6 lg:space-y-0 lg:grid lg:grid-cols-[1.4fr_1fr] lg:gap-6">
            <div className="space-y-6">
              {/* Report Info */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <DetailCard
                  label="Report Type"
                  value={
                    <span className="flex items-center gap-2">
                      {report.report_type === 'PROFILE' ? (
                        <>
                          <User className="w-4 h-4" />
                          Profile
                        </>
                      ) : (
                        <>
                          <MessageSquare className="w-4 h-4" />
                          Message
                        </>
                      )}
                    </span>
                  }
                />
                <DetailCard label="Status" value={report.status.replace('_', ' ')} />
                <DetailCard label="Reason" value={REPORT_REASON_LABELS[report.reason]} />
                <DetailCard
                  label={
                    <span className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      Reported At
                    </span>
                  }
                  value={new Date(report.created_at).toLocaleDateString('en-US', {
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                />
              </div>

              {/* IDs */}
              <div className="space-y-3">
                <DetailCode label="Report ID" value={report.id} />
                <DetailCode label="Reporter User ID" value={report.reporter_user_id} />
                {report.reported_profile_id && (
                  <DetailCode label="Reported Profile ID" value={report.reported_profile_id} />
                )}
                {report.reported_message_id && (
                  <DetailCode label="Reported Message ID" value={report.reported_message_id} />
                )}
              </div>

              {/* Description */}
              {report.description && (
                <div>
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Reporter's Description
                  </p>
                  <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-sm leading-relaxed text-gray-900 dark:text-white whitespace-pre-wrap">
                    {report.description}
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-4">
              {isResolved ? (
                <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl space-y-3">
                  <div className="flex items-center gap-2 text-green-900 dark:text-green-200">
                    <CheckCircle className="w-5 h-5" />
                    <p className="font-semibold">This report has been resolved</p>
                  </div>

                  {report.resolved_by && (
                    <DetailCode label="Resolved By" value={report.resolved_by} tone="success" />
                  )}

                  {report.resolved_at && (
                    <DetailCard
                      label="Resolved At"
                      value={new Date(report.resolved_at).toLocaleDateString('en-US', {
                        month: 'long',
                        day: 'numeric',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                      tone="success"
                    />
                  )}

                  {report.admin_notes && (
                    <p className="text-sm text-green-900 dark:text-green-200">
                      <span className="font-medium">Admin Notes:</span> {report.admin_notes}
                    </p>
                  )}

                  {report.action_taken && (
                    <p className="text-sm text-green-900 dark:text-green-200">
                      <span className="font-medium">Action Taken:</span> {report.action_taken}
                    </p>
                  )}
                </div>
              ) : (
                <div className="p-4 bg-gray-50 dark:bg-gray-800/60 rounded-xl border border-gray-200 dark:border-gray-700 space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Resolve Report
                  </h3>

                  <div className="space-y-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Resolution Status *
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <ResolutionOption
                        title="Reviewed"
                        description="Reviewed but no action yet"
                        active={resolutionStatus === 'REVIEWED'}
                        onClick={() => setResolutionStatus('REVIEWED')}
                        color="blue"
                      />
                      <ResolutionOption
                        title="Actioned"
                        description="Action has been taken"
                        active={resolutionStatus === 'ACTIONED'}
                        onClick={() => setResolutionStatus('ACTIONED')}
                        color="green"
                      />
                      <ResolutionOption
                        title="No Action"
                        description="No violation found"
                        active={resolutionStatus === 'NO_ACTION'}
                        onClick={() => setResolutionStatus('NO_ACTION')}
                        color="gray"
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Admin Notes (Internal)
                    </label>
                    <textarea
                      value={adminNotes}
                      onChange={(e) => setAdminNotes(e.target.value)}
                      disabled={isSubmitting}
                      rows={3}
                      className="w-full px-3 py-2 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 resize-none"
                      placeholder="Internal notes about this report..."
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Action Taken (Optional)
                    </label>
                    <textarea
                      value={actionTaken}
                      onChange={(e) => setActionTaken(e.target.value)}
                      disabled={isSubmitting}
                      rows={3}
                      className="w-full px-3 py-2 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 resize-none"
                      placeholder="Describe what action was taken..."
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="px-6 py-2.5 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
          >
            {isResolved ? 'Close' : 'Cancel'}
          </button>

          {!isResolved && (
            <button
              onClick={handleResolve}
              disabled={isSubmitting}
              className="px-6 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isSubmitting ? 'Resolving...' : 'Resolve Report'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

interface DetailCardProps {
  label: React.ReactNode;
  value: React.ReactNode;
  tone?: 'default' | 'success';
}

function DetailCard({ label, value, tone = 'default' }: DetailCardProps) {
  const toneClasses =
    tone === 'success'
      ? 'bg-green-100 dark:bg-green-900/30 text-green-900 dark:text-green-200'
      : 'bg-gray-50 dark:bg-gray-700/50 text-gray-900 dark:text-white';

  return (
    <div className={cn('p-4 rounded-lg', toneClasses)}>
      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
        {label}
      </p>
      <p className="font-medium">{value}</p>
    </div>
  );
}

interface DetailCodeProps {
  label: string;
  value: string;
  tone?: 'default' | 'success';
}

function DetailCode({ label, value, tone = 'default' }: DetailCodeProps) {
  const color =
    tone === 'success'
      ? 'bg-green-100 dark:bg-green-900/40 text-green-900 dark:text-green-200'
      : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white';

  return (
    <div>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{label}</p>
      <code className={`text-xs px-2 py-1 rounded font-mono inline-block ${color}`}>
        {value}
      </code>
    </div>
  );
}

interface ResolutionOptionProps {
  title: string;
  description: string;
  active: boolean;
  color: 'blue' | 'green' | 'gray';
  onClick: () => void;
}

const OPTION_STYLES: Record<
  ResolutionOptionProps['color'],
  { active: string; inactive: string }
> = {
  blue: {
    active: 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-200',
    inactive:
      'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-400',
  },
  green: {
    active: 'border-green-500 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-200',
    inactive:
      'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-400',
  },
  gray: {
    active: 'border-gray-500 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200',
    inactive:
      'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-400',
  },
};

function ResolutionOption({ title, description, active, color, onClick }: ResolutionOptionProps) {
  const styles = OPTION_STYLES[color];
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-left px-3 py-2 border-2 rounded-lg transition-all text-sm ${
        active ? styles.active : styles.inactive
      }`}
    >
      <p className="font-semibold">{title}</p>
      <p className="text-xs mt-1">{description}</p>
    </button>
  );
}
