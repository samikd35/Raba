'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  AlertCircle,
  FileText,
  Filter,
} from 'lucide-react';
import { cofounderAPI } from '@/lib/api/cofounderService';
import type { ProfileVersion, ProfileStatus } from '@/types/cofounder';
import CofounderFilter, {
  DirectoryFilters,
  defaultDirectoryFilters,
} from '@/components/cofounder/cofounder-directory/CofounderFilter';
import ProfileListItem from './ProfileListItem';
import AdminProfileReviewModal from './AdminProfileReviewModal';
import RejectReasonModal from './RejectReasonModal';
import { getStatusConfig } from './utils';

export default function CofounderAdminModeration() {
  const router = useRouter();
  const [profiles, setProfiles] = useState<ProfileVersion[]>([]);
  const [filteredProfiles, setFilteredProfiles] = useState<ProfileVersion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<ProfileVersion | null>(null);
  const [statusFilter, setStatusFilter] = useState<ProfileStatus>('submitted');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  // Additional filter states
  const [directoryFilters, setDirectoryFilters] = useState<DirectoryFilters>(defaultDirectoryFilters);

  useEffect(() => {
    loadProfiles();
    setCurrentPage(1); // Reset to first page when filter changes
  }, [statusFilter]);

  // Apply additional filters when they change
  useEffect(() => {
    applyFilters();
  }, [directoryFilters, profiles]);

  const loadProfiles = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await cofounderAPI.admin.listProfileVersions(statusFilter, 100);
      setProfiles(data);
      setFilteredProfiles(data);
    } catch (err: any) {
      console.error('Failed to load profiles:', err);
      setError(err.message || 'Failed to load profiles');
    } finally {
      setIsLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...profiles];

    if (directoryFilters.languages.length > 0) {
      filtered = filtered.filter((profile) =>
        profile.preferred_languages?.some((lang: any) =>
          directoryFilters.languages.includes(lang.language_id) ||
          directoryFilters.languages.includes(lang.code)
        )
      );
    }

    if (directoryFilters.preferred_commitment) {
      filtered = filtered.filter((profile) =>
        profile.expected_commitment === directoryFilters.preferred_commitment ||
        profile.preferred_commitment === directoryFilters.preferred_commitment
      );
    }

    if (directoryFilters.preferred_venture_stage.length > 0) {
      const selectedStage = directoryFilters.preferred_venture_stage[0];
      filtered = filtered.filter((profile) =>
        profile.venture_stage?.includes(selectedStage) ||
        profile.preferred_venture_stage?.includes(selectedStage)
      );
    }

    if (directoryFilters.country) {
      const countryTarget = directoryFilters.country.toLowerCase();
      filtered = filtered.filter((profile) => {
        const normalize = (value?: string | null) =>
          typeof value === 'string' ? value.toLowerCase() : '';
        const currentCountry = normalize(profile.country);
        const preferredCountry = normalize((profile as any).preferred_country);
        return currentCountry === countryTarget || preferredCountry === countryTarget;
      });
    }

    setFilteredProfiles(filtered);
    setCurrentPage(1); // Reset to first page when filters change
  };

  const clearAdditionalFilters = () => {
    setDirectoryFilters({ ...defaultDirectoryFilters });
  };

  const handleApprove = async (versionId: string) => {
    if (!confirm('Are you sure you want to approve this profile?')) return;

    try {
      setActionLoading(true);
      await cofounderAPI.admin.approveVersion(versionId);
      alert('Profile approved successfully!');
      setSelectedProfile(null);
      await loadProfiles();
    } catch (err: any) {
      console.error('Failed to approve profile:', err);
      alert(`Failed to approve profile: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedProfile) return;
    if (!rejectReason.trim()) {
      alert('Please provide a reason for rejection');
      return;
    }

    try {
      setActionLoading(true);
      await cofounderAPI.admin.rejectVersion(selectedProfile.id, rejectReason);
      alert('Profile rejected successfully!');
      setShowRejectModal(false);
      setRejectReason('');
      setSelectedProfile(null);
      await loadProfiles();
    } catch (err: any) {
      console.error('Failed to reject profile:', err);
      alert(`Failed to reject profile: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };


  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading profiles...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="max-w-2xl mx-auto p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-lg font-semibold text-red-900 dark:text-red-200 mb-2">
                Error Loading Profiles
              </h3>
              <p className="text-red-700 dark:text-red-300 mb-4">{error}</p>
              <button
                onClick={loadProfiles}
                className="px-4 py-2 bg-red-600 dark:bg-red-500 text-white rounded-lg hover:bg-red-700 dark:hover:bg-red-600 transition-all"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50 dark:bg-gray-900">
      <div className="flex-none p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Header with Toggle */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Cofounder Management
            </h1>

            {/* Toggle Switch */}
            <div className="flex items-center gap-2 bg-white dark:bg-gray-800 p-1 rounded-lg border border-gray-200 dark:border-gray-700">
              <button
                className="px-4 py-2 rounded border border-blue-light-200 text-sm font-medium bg-brand-500 text-white"
              >
                Moderation
              </button>
              <button
                onClick={() => router.push('/admin/enums')}
                className="px-4 py-2 rounded border border-brand-400 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Enums
              </button>

              <button
                onClick={() => router.push('/admin/reports-monitoring')}
                className="px-4 py-2 rounded border border-brand-400 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Reports Monitoring
              </button>
            </div>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            Review and moderate cofounder profile submissions
          </p>
        </div>

        {/* Additional Filters */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <Filter className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter Profiles</span>
          </div>
          <CofounderFilter
            filters={directoryFilters}
            onChange={setDirectoryFilters}
            onClear={clearAdditionalFilters}
            className="gap-2"
          />
        </div>

        {/* Status Filter Tabs */}
        <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
          {(['submitted', 'approved', 'rejected', 'draft'] as ProfileStatus[]).map(
            (status) => {
              const config = getStatusConfig(status);
              const StatusIcon = config.icon;
              const count = profiles.filter((p) => p.status === status).length;
              const isActive = statusFilter === status;

              // Get button styling based on status
              let buttonStyle = '';
              if (isActive) {
                if (status === 'submitted') {
                  buttonStyle = 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300';
                } else if (status === 'approved') {
                  buttonStyle = 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300';
                } else if (status === 'rejected') {
                  buttonStyle = 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300';
                } else {
                  buttonStyle = 'bg-gray-50 dark:bg-gray-700/50 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300';
                }
              } else {
                buttonStyle = 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700';
              }

              return (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all whitespace-nowrap ${buttonStyle}`}
                >
                  <StatusIcon className="w-4 h-4" />
                  <span className="font-medium">{config.label}</span>
                  {isActive && count > 0 && (
                    <span className="px-2 py-0.5 bg-white/50 dark:bg-black/20 text-xs rounded-full font-semibold">
                      {count}
                    </span>
                  )}
                </button>
              );
            }
          )}
        </div>
      </div>

      {/* Scrollable Profiles List */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto pb-6">
          {filteredProfiles.length === 0 ? (
            <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <FileText className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                No Profiles Found
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                No profiles with status "{statusFilter}"
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-4">
                {filteredProfiles
                  .slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)
                  .map((profile) => (
                    <ProfileListItem
                      key={profile.id}
                      profile={profile}
                      onView={() => setSelectedProfile(profile)}
                    />
                  ))}
              </div>

              {/* Pagination */}
              {filteredProfiles.length > itemsPerPage && (
                <div className="mt-6 flex items-center justify-between bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 px-6 py-4">
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Showing {(currentPage - 1) * itemsPerPage + 1} to{' '}
                    {Math.min(currentPage * itemsPerPage, filteredProfiles.length)} of{' '}
                    {filteredProfiles.length} profiles
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                      disabled={currentPage === 1}
                      className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      Previous
                    </button>
                    <div className="flex items-center gap-2">
                      {Array.from(
                        { length: Math.ceil(filteredProfiles.length / itemsPerPage) },
                        (_, i) => i + 1
                      ).map((page) => (
                        <button
                          key={page}
                          onClick={() => setCurrentPage(page)}
                          className={`px-3 py-2 text-sm font-medium rounded-lg transition-all ${
                            currentPage === page
                              ? 'bg-brand-500 dark:bg-brand-400 text-white'
                              : 'text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                          }`}
                        >
                          {page}
                        </button>
                      ))}
                    </div>
                    <button
                      onClick={() =>
                        setCurrentPage((prev) =>
                          Math.min(Math.ceil(filteredProfiles.length / itemsPerPage), prev + 1)
                        )
                      }
                      disabled={currentPage === Math.ceil(filteredProfiles.length / itemsPerPage)}
                      className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Admin Profile Review Modal */}
      {selectedProfile && !showRejectModal && (
        <AdminProfileReviewModal
          profile={selectedProfile}
          onClose={() => setSelectedProfile(null)}
          onApprove={() => handleApprove(selectedProfile.id)}
          onReject={() => setShowRejectModal(true)}
          actionLoading={actionLoading}
        />
      )}

      {/* Reject Reason Modal */}
      {selectedProfile && showRejectModal && (
        <RejectReasonModal
          profile={selectedProfile}
          reason={rejectReason}
          onReasonChange={setRejectReason}
          onConfirm={handleReject}
          onCancel={() => {
            setShowRejectModal(false);
            setRejectReason('');
          }}
          actionLoading={actionLoading}
        />
      )}
    </div>
  );
}
