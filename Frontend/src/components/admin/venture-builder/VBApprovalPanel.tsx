'use client';

import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Clock, User, Mail, DollarSign, Calendar, Loader2, Users } from 'lucide-react';
import { VBProfile } from '@/types/ventureBuilder';
import { fetchAllVBsAdmin } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';

interface VBApprovalPanelProps {
  onViewEdit: (vbId: string) => void;
  onViewAll: () => void;
}

export default function VBApprovalPanel({ onViewEdit, onViewAll }: VBApprovalPanelProps) {
  const [pendingVBs, setPendingVBs] = useState<VBProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadPendingVBs = async () => {
    try {
      setIsLoading(true);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const allVBs = await fetchAllVBsAdmin(token);
      const pending = allVBs.filter(vb => vb.status === 'pending_admin_review');
      setPendingVBs(pending);
    } catch (error: any) {
      console.error('Error fetching pending VBs:', error);
      toast.error(error.message || 'Failed to load pending VBs');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPendingVBs();
  }, []);

  const handleApprove = async (vbId: string, creditPrice: number, calendarUrl: string) => {
    try {
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(`${API_BASE_URL}/venture-builder/admin/vb/${vbId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          credit_price_per_hour: creditPrice,
          calendar_booking_url: calendarUrl || undefined,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to approve VB');
      }

      toast.success('Venture Builder approved successfully!');
      loadPendingVBs();
    } catch (error: any) {
      console.error('Error approving VB:', error);
      toast.error(error.message || 'Failed to approve VB');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading pending approvals...</p>
        </div>
      </div>
    );
  }

  if (pendingVBs.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-8 sm:p-12 text-center shadow-theme-xs">
        <div className="w-16 h-16 bg-success-100 dark:bg-success-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <CheckCircle className="w-8 h-8 text-success-600 dark:text-success-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          All Caught Up!
        </h3>
        <p className="text-gray-600 dark:text-gray-400 max-w-sm mx-auto">
          No venture builders pending approval at the moment.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            Pending Approvals
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Review and approve venture builder applications
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-warning-100 dark:bg-warning-900/30 border border-warning-200 dark:border-warning-700 rounded-lg">
            <Clock className="w-4 h-4 sm:w-5 sm:h-5 text-warning-600 dark:text-warning-400" />
            <span className="text-xs sm:text-sm font-semibold text-warning-700 dark:text-warning-300">
              {pendingVBs.length} Pending
            </span>
          </div>
          <button
            onClick={onViewAll}
            className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-medium transition-all shadow-theme-sm hover:shadow-theme-md"
          >
            <Users className="w-4 h-4" />
            <span className="hidden sm:inline">All Venture Builders</span>
            <span className="sm:hidden">View All</span>
          </button>
        </div>
      </div>

      {/* Pending VB Cards */}
      <div className="grid gap-4 sm:gap-6">
        {pendingVBs.map((vb) => (
          <VBApprovalCard
            key={vb.id}
            vb={vb}
            onApprove={handleApprove}
            onViewEdit={onViewEdit}
          />
        ))}
      </div>
    </div>
  );
}

function VBApprovalCard({
  vb,
  onApprove,
  onViewEdit
}: {
  vb: VBProfile;
  onApprove: (vbId: string, creditPrice: number, calendarUrl: string) => void;
  onViewEdit: (vbId: string) => void;
}) {
  const [creditPrice, setCreditPrice] = useState(100);
  const [calendarUrl, setCalendarUrl] = useState('');
  const [showApprovalForm, setShowApprovalForm] = useState(false);

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-theme-xs overflow-hidden">
      <div className="p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-start gap-4 sm:gap-6">
          <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-xl overflow-hidden border-4 border-gray-200 dark:border-gray-700 flex-shrink-0">
            <img
              src={vb.profile_picture_url}
              alt={vb.full_name || 'VB'}
              className="w-full h-full object-cover"
            />
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white mb-2">
              {vb.full_name || 'Unnamed Venture Builder'}
            </h3>

            <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2 sm:gap-3 mb-4">
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <Mail className="w-4 h-4 flex-shrink-0" />
                <span className="truncate">{vb.contact_email}</span>
              </div>
              {vb.expertise_areas && vb.expertise_areas.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {vb.expertise_areas.map((area) => (
                    <span
                      key={area.id}
                      className="px-2 sm:px-3 py-1 text-xs font-medium bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-300 border border-brand-200 dark:border-brand-700 rounded-lg"
                    >
                      {area.name}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-3">
              {vb.biography}
            </p>

            {!showApprovalForm ? (
              <div className="flex flex-wrap gap-2 sm:gap-3">
                <button
                  onClick={() => onViewEdit(vb.id)}
                  className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium transition-colors"
                >
                  <User className="w-4 h-4" />
                  <span className="hidden sm:inline">View Details</span>
                  <span className="sm:hidden">Details</span>
                </button>
                <button
                  onClick={() => setShowApprovalForm(true)}
                  className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-medium transition-all shadow-theme-sm"
                >
                  <CheckCircle className="w-4 h-4" />
                  <span className="hidden sm:inline">Review & Approve</span>
                  <span className="sm:hidden">Approve</span>
                </button>
              </div>
            ) : (
              <div className="space-y-4 p-3 sm:p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      <div className="flex items-center gap-2">
                        <DollarSign className="w-4 h-4 text-gray-400" />
                        Credit Price Per Hour
                      </div>
                    </label>
                    <input
                      type="number"
                      value={creditPrice}
                      onChange={(e) => setCreditPrice(Number(e.target.value))}
                      min="0"
                      className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        Calendar URL (Optional)
                      </div>
                    </label>
                    <input
                      type="url"
                      value={calendarUrl}
                      onChange={(e) => setCalendarUrl(e.target.value)}
                      placeholder="https://calendly.com/username"
                      className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                    />
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                  <button
                    onClick={() => onApprove(vb.id, creditPrice, calendarUrl)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-success-500 hover:bg-success-600 text-white rounded-lg text-sm font-medium transition-all shadow-theme-sm"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Approve
                  </button>
                  <button
                    onClick={() => setShowApprovalForm(false)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium transition-colors"
                  >
                    <XCircle className="w-4 h-4" />
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
