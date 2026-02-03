'use client';

import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, AlertTriangle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { reportAPI } from '@/lib/api/reportService';
import {
  ReportReason,
  REPORT_REASON_LABELS,
  REPORT_REASON_DESCRIPTIONS,
} from '@/types/reports';

interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportType: 'profile' | 'message';
  targetId: string; // profile_id or message_id
  targetName?: string; // Name of profile or preview of message for display
}

export default function ReportModal({
  isOpen,
  onClose,
  reportType,
  targetId,
  targetName,
}: ReportModalProps) {
  const [selectedReason, setSelectedReason] = useState<ReportReason | ''>('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const reasons: ReportReason[] = [
    'SPAM_OR_SCAM',
    'HARASSMENT_OR_HATE',
    'MISREPRESENTATION',
    'OFF_PLATFORM_SOLICITATION',
    'ADULT_CONTENT',
    'DUPLICATE_ACCOUNT',
    'UNDERAGE_OR_NOT_FOUNDER',
    'OTHER',
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedReason) {
      toast.error('Please select a reason for reporting');
      return;
    }

    if (selectedReason === 'OTHER' && !description.trim()) {
      toast.error('Please provide a description when selecting "Other"');
      return;
    }

    try {
      setIsSubmitting(true);

      if (reportType === 'profile') {
        await reportAPI.user.reportProfile({
          reported_profile_id: targetId,
          reason: selectedReason as ReportReason,
          description: description.trim() || undefined,
        });
        toast.success('Profile reported successfully. Our team will review it.');
      } else {
        await reportAPI.user.reportMessage({
          message_id: targetId,
          reason: selectedReason as ReportReason,
          description: description.trim() || undefined,
        });
        toast.success('Message reported successfully. Our team will review it.');
      }

      // Reset form and close modal
      setSelectedReason('');
      setDescription('');
      onClose();
    } catch (error: any) {
      console.error('Failed to submit report:', error);
      toast.error(error.message || 'Failed to submit report. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setSelectedReason('');
      setDescription('');
      onClose();
    }
  };

  if (!isOpen || !mounted) return null;

  const modalContent = (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-red-500" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              Report {reportType === 'profile' ? 'Profile' : 'Message'}
            </h2>
          </div>
          <button
            onClick={handleClose}
            disabled={isSubmitting}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors disabled:opacity-50"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Target Info */}
          {targetName && (
            <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Reporting:
              </p>
              <p className="text-gray-900 dark:text-white font-medium">
                {targetName}
              </p>
            </div>
          )}

          {/* Reason Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Why are you reporting this {reportType}? *
            </label>
            <div className="space-y-2">
              {reasons.map((reason) => (
                <label
                  key={reason}
                  className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-all ${
                    selectedReason === reason
                      ? 'border-red-500 bg-red-50 dark:bg-red-900/20'
                      : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                  }`}
                >
                  <input
                    type="radio"
                    name="reason"
                    value={reason}
                    checked={selectedReason === reason}
                    onChange={(e) => setSelectedReason(e.target.value as ReportReason)}
                    disabled={isSubmitting}
                    className="mt-1 w-4 h-4 text-red-500 focus:ring-red-500"
                  />
                  <div className="ml-3 flex-1">
                    <p className="font-medium text-gray-900 dark:text-white">
                      {REPORT_REASON_LABELS[reason]}
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {REPORT_REASON_DESCRIPTIONS[reason]}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Additional Details {selectedReason === 'OTHER' && '*'}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isSubmitting}
              rows={4}
              className="w-full px-4 py-3 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 dark:focus:ring-red-400 focus:border-transparent resize-none"
              placeholder="Please provide any additional details that will help us review this report..."
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              {selectedReason === 'OTHER'
                ? 'Description is required when "Other" is selected'
                : 'Optional: Provide additional context to help our team'}
            </p>
          </div>

          {/* Info Message */}
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-sm text-blue-900 dark:text-blue-200">
              <strong>What happens next:</strong> Our moderation team will review your
              report within 24-48 hours. We take all reports seriously and will take
              appropriate action if we find a violation of our community guidelines.
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-6 py-2.5 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !selectedReason}
              className="px-6 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isSubmitting ? 'Submitting...' : 'Submit Report'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
