'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Save, ArrowLeft, Loader2, User, Mail, Linkedin, FileText, DollarSign, Calendar, AlertCircle, CheckCircle, Check, X, Briefcase } from 'lucide-react';
import { VBProfile, WorkExperience } from '@/types/ventureBuilder';
import { fetchVBByIdAdmin, updateVBProfile, updateVBPricing, updateVBPublishStatus, approveVBProfile, rejectVBProfile } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import VBReconciliationActions from './VBReconciliationActions';

interface VBDetailEditProps {
  vbId: string;
  onBack: () => void;
}

export default function VBDetailEdit({ vbId, onBack }: VBDetailEditProps) {
  const [vb, setVb] = useState<VBProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  const [contactEmail, setContactEmail] = useState('');
  const [biography, setBiography] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [creditPricePerHour, setCreditPricePerHour] = useState<number>(0);
  const [calendarBookingUrl, setCalendarBookingUrl] = useState('');
  const [isActive, setIsActive] = useState(false);
  const [status, setStatus] = useState<string>('pending_profile');

  const loadVB = useCallback(async () => {
    try {
      setIsLoading(true);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const data = await fetchVBByIdAdmin(vbId, token);
      setVb(data);

      setContactEmail(data.contact_email);
      setBiography(data.biography);
      setLinkedinUrl(data.linkedin_url || '');
      setCreditPricePerHour(data.credit_price_per_hour || (data.status === 'pending_admin_review' ? 100 : 0));
      setCalendarBookingUrl(data.calendar_booking_url || '');
      setIsActive(data.is_active);
      setStatus(data.status);
    } catch (error: any) {
      console.error('Error fetching VB:', error);
      toast.error(error.message || 'Failed to load venture builder');
    } finally {
      setIsLoading(false);
    }
  }, [vbId]);

  useEffect(() => {
    loadVB();
  }, [loadVB]);

  const handleSave = async () => {
    try {
      setIsSaving(true);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const profileUpdatePayload = {
        contact_email: contactEmail,
        biography: biography,
        linkedin_url: linkedinUrl || undefined,
        calendar_booking_url: calendarBookingUrl || undefined,
        status: status,
      };

      await updateVBProfile(vbId, profileUpdatePayload, token);

      if (creditPricePerHour && creditPricePerHour !== vb?.credit_price_per_hour) {
        await updateVBPricing(vbId, creditPricePerHour, token);
      }

      if (isActive !== vb?.is_active) {
        await updateVBPublishStatus(vbId, isActive, token);
      }

      toast.success('Venture Builder updated successfully');
      loadVB();
    } catch (error: any) {
      console.error('Error updating VB:', error);
      toast.error(error.message || 'Failed to update venture builder');
    } finally {
      setIsSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!creditPricePerHour || creditPricePerHour <= 0) {
      toast.error('Please set a valid credit price per hour before approving');
      return;
    }

    try {
      setIsApproving(true);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      await approveVBProfile(vbId, creditPricePerHour, token);
      toast.success('Venture Builder approved successfully!');
      loadVB();
    } catch (error: any) {
      console.error('Error approving VB:', error);
      toast.error(error.message || 'Failed to approve venture builder');
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }

    try {
      setIsRejecting(true);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      await rejectVBProfile(vbId, rejectionReason, token);
      toast.success('Venture Builder rejected');
      setShowRejectModal(false);
      setRejectionReason('');
      loadVB();
    } catch (error: any) {
      console.error('Error rejecting VB:', error);
      toast.error(error.message || 'Failed to reject venture builder');
    } finally {
      setIsRejecting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; className: string; icon: React.ReactNode }> = {
      pending_profile: {
        label: 'Pending Profile',
        className: 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300 border-warning-200 dark:border-warning-700',
        icon: <AlertCircle className="w-4 h-4" />,
      },
      pending_admin_review: {
        label: 'Pending Review',
        className: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 border-orange-200 dark:border-orange-700',
        icon: <AlertCircle className="w-4 h-4" />,
      },
      active: {
        label: 'Active',
        className: 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300 border-success-200 dark:border-success-700',
        icon: <CheckCircle className="w-4 h-4" />,
      },
      inactive: {
        label: 'Inactive',
        className: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-600',
        icon: <AlertCircle className="w-4 h-4" />,
      },
    };

    const config = statusConfig[status] || statusConfig.inactive;

    return (
      <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm ${config.className}`}>
        {config.icon}
        <span className="font-medium">{config.label}</span>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 dark:border-brand-400 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading venture builder...</p>
        </div>
      </div>
    );
  }

  if (!vb) {
    return (
      <div className="text-center py-16">
        <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <User className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          Venture builder not found
        </h3>
        <button
          onClick={onBack}
          className="mt-4 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg transition-colors"
        >
          Go Back
        </button>
      </div>
    );
  }

  const isPendingReview = status === 'pending_admin_review';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors w-fit"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="font-medium">Back to List</span>
        </button>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {isPendingReview ? (
            <>
              <button
                onClick={() => setShowRejectModal(true)}
                disabled={isRejecting || isApproving}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all bg-error-500 hover:bg-error-600 text-white shadow-theme-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isRejecting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="hidden sm:inline">Rejecting...</span>
                  </>
                ) : (
                  <>
                    <X className="w-4 h-4" />
                    <span className="hidden sm:inline">Reject</span>
                  </>
                )}
              </button>
              <button
                onClick={handleApprove}
                disabled={isApproving || isRejecting || !creditPricePerHour || creditPricePerHour <= 0}
                title={(!creditPricePerHour || creditPricePerHour <= 0) ? 'Please set a valid credit price per hour first' : 'Approve this venture builder'}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all bg-success-500 hover:bg-success-600 text-white shadow-theme-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isApproving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="hidden sm:inline">Approving...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    <span className="hidden sm:inline">Approve</span>
                  </>
                )}
              </button>
            </>
          ) : (
            <button
              onClick={handleSave}
              disabled={isSaving}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-theme-sm ${
                isSaving
                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 cursor-not-allowed'
                  : 'bg-brand-500 hover:bg-brand-600 text-white hover:shadow-theme-md'
              }`}
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save Changes
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Profile Card */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-theme-xs overflow-hidden">
        {/* Profile Header */}
        <div className="p-4 sm:p-6 border-b border-gray-100 dark:border-gray-700">
          <div className="flex flex-col sm:flex-row items-start gap-4 sm:gap-6">
            <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-xl overflow-hidden border-4 border-gray-200 dark:border-gray-600 flex-shrink-0 bg-gray-100 dark:bg-gray-700">
              <img
                src={vb.profile_picture_url}
                alt={vb.full_name || 'VB'}
                className="w-full h-full object-cover"
              />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {vb.full_name || 'Unnamed Venture Builder'}
              </h2>
              <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-3">
                {getStatusBadge(status)}
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Published:</span>
                  <span className={`font-semibold ${isActive ? 'text-success-600 dark:text-success-400' : 'text-gray-500'}`}>
                    {isActive ? 'Yes' : 'No'}
                  </span>
                </div>
              </div>
              {vb.expertise_areas && vb.expertise_areas.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {vb.expertise_areas.map((area) => (
                    <span
                      key={area.id}
                      className="px-3 py-1 text-xs font-medium bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 border border-brand-200 dark:border-brand-700 rounded-lg"
                    >
                      {area.name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Form Sections */}
        <div className="p-4 sm:p-6 space-y-8">
          {/* Profile Information */}
          <section>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                <User className="w-4 h-4 text-brand-600 dark:text-brand-400" />
              </div>
              Profile Information
            </h3>
            <div className="grid gap-4 sm:gap-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <span className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-gray-400" />
                      Contact Email
                    </span>
                  </label>
                  <input
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <span className="flex items-center gap-2">
                      <Linkedin className="w-4 h-4 text-gray-400" />
                      LinkedIn URL
                    </span>
                  </label>
                  <input
                    type="url"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                    placeholder="https://linkedin.com/in/username"
                    className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  <span className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-gray-400" />
                    Biography
                  </span>
                </label>
                <textarea
                  value={biography}
                  onChange={(e) => setBiography(e.target.value)}
                  rows={5}
                  className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all resize-none"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
                  {biography.length} / 2000 characters
                </p>
              </div>
            </div>
          </section>

          {/* Work Experience */}
          {vb.work_experience && vb.work_experience.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                  <Briefcase className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                </div>
                Work Experience
              </h3>
              <div className="grid gap-3">
                {vb.work_experience.map((exp, index) => (
                  <div
                    key={index}
                    className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <h4 className="font-semibold text-gray-900 dark:text-white">{exp.position}</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{exp.organization}</p>
                    <p className="text-xs text-gray-500 mt-1">{exp.years}</p>
                    {exp.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 line-clamp-2">{exp.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Pricing & Calendar */}
          <section>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                <DollarSign className="w-4 h-4 text-brand-600 dark:text-brand-400" />
              </div>
              Pricing & Calendar
            </h3>
            {isPendingReview && (
              <div className="mb-4 p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-700 rounded-lg">
                <p className="text-sm text-orange-800 dark:text-orange-300">
                  <strong>Required:</strong> Set a valid credit price per hour before approving this profile.
                </p>
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Credit Price Per Hour {isPendingReview && <span className="text-error-500">*</span>}
                </label>
                <input
                  type="number"
                  value={creditPricePerHour}
                  onChange={(e) => setCreditPricePerHour(Number(e.target.value))}
                  min="1"
                  className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  <span className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-gray-400" />
                    Calendar Booking URL
                  </span>
                </label>
                <input
                  type="url"
                  value={calendarBookingUrl}
                  onChange={(e) => setCalendarBookingUrl(e.target.value)}
                  placeholder="https://calendly.com/username"
                  className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                />
              </div>
            </div>
          </section>

          {/* Status & Controls */}
          <section>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Status & Controls
            </h3>
            <div className="space-y-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Admin Status
                </label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full sm:w-auto px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                >
                  <option value="pending_profile">Pending Profile</option>
                  <option value="pending_admin_review">Pending Admin Review</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  Controls the VB's workflow status in the system
                </p>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">Publish Status</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Controls if this VB is visible to users
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 dark:bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-brand-300 dark:peer-focus:ring-brand-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-brand-500"></div>
                  <span className="ml-3 text-sm font-medium text-gray-900 dark:text-white">
                    {isActive ? 'Published' : 'Unpublished'}
                  </span>
                </label>
              </div>

              <div className="p-4 bg-blue-light-50 dark:bg-blue-light-900/20 border border-blue-light-200 dark:border-blue-light-700 rounded-lg">
                <p className="text-sm text-blue-light-800 dark:text-blue-light-300">
                  <strong>Note:</strong> Changes to the profile will be saved when you click "Save Changes".
                </p>
              </div>
            </div>
          </section>

          {/* Reconciliation Section - Only for active VBs */}
          {status === 'active' && vb && (
            <section>
              <VBReconciliationActions vbId={vbId} vbName={vb.full_name || 'Venture Builder'} />
            </section>
          )}
        </div>
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Reject Venture Builder Profile
              </h3>
            </div>
            <div className="p-6">
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Please provide a reason for rejecting this profile. This will be sent to the venture builder.
              </p>
              <textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Enter rejection reason..."
                rows={4}
                className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-error-500 dark:focus:ring-error-400 focus:border-transparent transition-all resize-none"
              />
            </div>
            <div className="flex items-center justify-end gap-3 px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => {
                  setShowRejectModal(false);
                  setRejectionReason('');
                }}
                disabled={isRejecting}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={isRejecting || !rejectionReason.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-error-500 hover:bg-error-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isRejecting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Rejecting...
                  </>
                ) : (
                  <>
                    <X className="w-4 h-4" />
                    Reject Profile
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
