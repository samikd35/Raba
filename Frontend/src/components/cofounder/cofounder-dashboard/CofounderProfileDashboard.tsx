'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  Edit,
  Calendar,
  Briefcase,
  MapPin,
  Languages,
  Target,
  AlertCircle,
  Loader2,
  ChevronLeft,
} from 'lucide-react';
import { cofounderAPI } from '@/lib/api/cofounderService';
import type { ProfileSummary, ProfileVersion, ProfileStatus } from '@/types/cofounder';
import Link from 'next/link';
import UserAvatar from '@/components/ui/avatar/UserAvatar';
import EmptyStateBanner from '../EmptyStateBanner';

export default function CofounderProfileDashboard() {
  const [profileSummary, setProfileSummary] = useState<ProfileSummary | null>(null);
  const [versions, setVersions] = useState<ProfileVersion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<ProfileVersion | null>(null);
  const [statusFilter, setStatusFilter] = useState<ProfileStatus | 'all'>('all');
  const [versionCounts, setVersionCounts] = useState<Record<string, number>>({
    all: 0,
    draft: 0,
    submitted: 0,
    approved: 0,
    rejected: 0,
  });

  useEffect(() => {
    loadProfileData();
  }, []);

  useEffect(() => {
    loadVersions();
  }, [statusFilter]);

  const loadProfileData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      try {
        const summary = await cofounderAPI.profiles.getMyProfileSummary();
        setProfileSummary(summary);
      } catch (summaryError: any) {
        // If 404, user has no profile yet - this is okay
        if (summaryError.message?.includes('404') || summaryError.message?.includes('not found')) {
          console.log('No profile summary found - user may not have created profile yet');
          setProfileSummary(null);
        } else {
          throw summaryError;
        }
      }

      // Load counts for all statuses
      await loadVersionCounts();
    } catch (err: any) {
      console.error('Failed to load profile:', err);
      setError(err.message || 'Failed to load profile data');
    } finally {
      setIsLoading(false);
    }
  };

  const loadVersionCounts = async () => {
    try {
      const allVersions = await cofounderAPI.profiles.listMyVersions('all', 100);

      const counts = {
        all: allVersions.length,
        draft: allVersions.filter(v => v.status === 'draft').length,
        submitted: allVersions.filter(v => v.status === 'submitted').length,
        approved: allVersions.filter(v => v.status === 'approved').length,
        rejected: allVersions.filter(v => v.status === 'rejected').length,
      };

      setVersionCounts(counts);
    } catch (err: any) {
      if (err.message?.includes('404') || err.message?.includes('not found')) {
        console.log('No versions found for counts');
      } else {
        console.error('Failed to load version counts:', err);
      }
    }
  };

  const loadVersions = async () => {
    try {
      const filteredVersions = await cofounderAPI.profiles.listMyVersions(statusFilter, 20);
      setVersions(filteredVersions);
    } catch (err: any) {
      if (err.message?.includes('404') || err.message?.includes('not found')) {
        console.log('No versions found for filter:', statusFilter);
        setVersions([]);
      } else {
        console.error('Failed to load versions:', err);
      }
    }
  };

  const getStatusConfig = (status: ProfileStatus) => {
    switch (status) {
      case 'approved':
        return {
          icon: CheckCircle,
          color: 'text-green-600 dark:text-green-400',
          bgColor: 'bg-green-50 dark:bg-green-900/20',
          borderColor: 'border-green-200 dark:border-green-800',
          label: 'Approved',
          description: 'Your profile is live and visible to potential cofounders',
        };
      case 'submitted':
        return {
          icon: Clock,
          color: 'text-blue-600 dark:text-blue-400',
          bgColor: 'bg-blue-50 dark:bg-blue-900/20',
          borderColor: 'border-blue-200 dark:border-blue-800',
          label: 'Under Review',
          description: 'Your profile is being reviewed by our team',
        };
      case 'rejected':
        return {
          icon: XCircle,
          color: 'text-red-600 dark:text-red-400',
          bgColor: 'bg-red-50 dark:bg-red-900/20',
          borderColor: 'border-red-200 dark:border-red-800',
          label: 'Needs Revision',
          description: 'Your profile needs some updates before approval',
        };
      case 'draft':
      default:
        return {
          icon: FileText,
          color: 'text-gray-600 dark:text-gray-400',
          bgColor: 'bg-gray-50 dark:bg-gray-700/50',
          borderColor: 'border-gray-200 dark:border-gray-700',
          label: 'Draft',
          description: 'Complete and submit your profile for review',
        };
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading your profile...</p>
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
                Error Loading Profile
              </h3>
              <p className="text-red-700 dark:text-red-300 mb-4">{error}</p>
              <button
                onClick={loadProfileData}
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

  const currentStatus = profileSummary?.profile?.status || 'draft';
  const statusConfig = getStatusConfig(currentStatus);
  const StatusIcon = statusConfig.icon;
  const latestVersion = profileSummary?.latest_version;
  const approvedVersion = profileSummary?.last_approved;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Cofounder Profile
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Manage your cofounder matching profile and view your status
            </p>
          </div>
          {!profileSummary && (
            <Link
              href="/workspace/cofounder-matching"
              className="flex items-center gap-2 px-6 py-3 bg-brand-500 dark:bg-brand-400 text-white rounded-lg hover:bg-brand-600 dark:hover:bg-brand-500 transition-all font-medium"
            >
              <Edit className="w-4 h-4" />
              Create New Profile
            </Link>
          )}
        </div>

        {/* Status Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mb-8 p-6 rounded-lg border ${statusConfig.bgColor} ${statusConfig.borderColor}`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <StatusIcon className={`w-8 h-8 ${statusConfig.color} flex-shrink-0`} />
              <div>
                <h2 className={`text-xl font-semibold mb-1 ${statusConfig.color}`}>
                  {statusConfig.label}
                </h2>
                <p className="text-gray-700 dark:text-gray-300 mb-4">
                  {statusConfig.description}
                </p>

                {currentStatus === 'rejected' && latestVersion?.review_reason && (
                  <div className="mt-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-red-200 dark:border-red-800">
                    <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Feedback from reviewer:
                    </p>
                    <p className="text-sm text-gray-700 dark:text-gray-300">
                      {latestVersion.review_reason}
                    </p>
                  </div>
                )}

                {latestVersion && (
                  <div className="flex items-center gap-4 mt-4 text-sm text-gray-600 dark:text-gray-400">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      Last updated: {formatDate(latestVersion.created_at)}
                    </span>
                    {latestVersion.submitted_at && (
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        Submitted: {formatDate(latestVersion.submitted_at)}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-2">
              {currentStatus === 'draft' && (
                <Link
                  href="/workspace/cofounder-matching"
                  className="flex items-center gap-2 px-4 py-2 bg-brand-500 dark:bg-brand-400 text-white rounded-lg hover:bg-brand-600 dark:hover:bg-brand-500 transition-all"
                >
                  <Edit className="w-4 h-4" />
                  Complete Profile
                </Link>
              )}
              {currentStatus === 'rejected' && (
                <Link
                  href="/workspace/cofounder-matching"
                  className="flex items-center gap-2 px-4 py-2 bg-brand-500 dark:bg-brand-400 text-white rounded-lg hover:bg-brand-600 dark:hover:bg-brand-500 transition-all"
                >
                  <Edit className="w-4 h-4" />
                  Edit & Resubmit
                </Link>
              )}
            </div>
          </div>
        </motion.div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Profile Preview */}
          <div className="lg:col-span-2 space-y-6">
            {approvedVersion ? (
              <ProfilePreview version={approvedVersion} title="Your Approved Profile" />
            ) : latestVersion ? (
              <ProfilePreview version={latestVersion} title="Your Latest Profile" />
            ) : (
              <EmptyStateBanner
                type="no-profile"
                actionText="Create Profile"
                actionLink="/workspace/cofounder-matching"
              />
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Version History */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Clock className="w-5 h-5" />
                Version History
              </h3>

              {/* Status Filters */}
              <div className="flex flex-wrap gap-2 mb-4">
                {(['all', 'draft', 'submitted', 'approved', 'rejected'] as const).map((status) => {
                  const isActive = statusFilter === status;
                  const count = versionCounts[status];

                  // Get button styling based on status
                  let buttonStyle = '';
                  if (isActive) {
                    if (status === 'submitted') {
                      buttonStyle = 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300';
                    } else if (status === 'approved') {
                      buttonStyle = 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300';
                    } else if (status === 'rejected') {
                      buttonStyle = 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300';
                    } else if (status === 'draft') {
                      buttonStyle = 'bg-gray-50 dark:bg-gray-700/50 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300';
                    } else {
                      buttonStyle = 'bg-brand-50 dark:bg-brand-900/20 border-brand-200 dark:border-brand-800 text-brand-700 dark:text-brand-300';
                    }
                  } else {
                    buttonStyle = 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600';
                  }

                  const label = status === 'all' ? 'All' : status.charAt(0).toUpperCase() + status.slice(1);

                  return (
                    <button
                      key={status}
                      onClick={() => setStatusFilter(status)}
                      className={`px-3 py-1.5 text-sm font-medium border rounded-lg transition-all flex items-center gap-2 ${buttonStyle}`}
                    >
                      {label}
                      {isActive && count > 0 && (
                        <span className="px-2 py-0.5 bg-white/50 dark:bg-black/20 text-xs rounded-full font-semibold">
                          {count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              <div className="space-y-3">
                {versions.length === 0 ? (
                  <p className="text-sm text-gray-600 dark:text-gray-400">No versions yet</p>
                ) : (
                  versions.slice(0, 5).map((version) => {
                    const versionStatus = getStatusConfig(version.status);
                    const VersionIcon = versionStatus.icon;
                    return (
                      <button
                        key={version.id}
                        onClick={() => setSelectedVersion(version)}
                        className="w-full text-left p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-all"
                      >
                        <div className="flex items-start gap-3">
                          <VersionIcon className={`w-4 h-4 ${versionStatus.color} flex-shrink-0 mt-0.5`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-1">
                              <span className={`text-xs font-medium ${versionStatus.color}`}>
                                {versionStatus.label}
                              </span>
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {formatDate(version.created_at)}
                              </span>
                            </div>
                            {version.review_reason && (
                              <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
                                {version.review_reason}
                              </p>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Quick Stats */}
            {latestVersion && (
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Profile Stats
                </h3>
                <div className="space-y-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Industries</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {latestVersion.industries_of_interest?.length || 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Responsibilities</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {latestVersion.responsibilities_offered?.length || 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Skills Needed</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {latestVersion.skills_needed?.length || 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Languages</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {latestVersion.preferred_languages?.length || 0}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Version Detail Modal */}
      {selectedVersion && (
        <VersionDetailModal
          version={selectedVersion}
          onClose={() => setSelectedVersion(null)}
        />
      )}
    </div>
  );
}


interface ProfilePreviewProps {
  version: ProfileVersion;
  title: string;
}

function ProfilePreview({ version, title }: ProfilePreviewProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{title}</h2>
        <Link
          href="/workspace/cofounder-matching"
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-brand-500 dark:bg-brand-400 hover:bg-brand-600 dark:hover:bg-brand-500 rounded-lg transition-colors"
        >
          <Edit className="w-4 h-4" />
          Edit Profile
        </Link>
      </div>

      {/* Basic Info - Always Visible */}
      <div className="flex items-start gap-6 mb-6 pb-6 border-b border-gray-200 dark:border-gray-700">
        <UserAvatar
          src={version.profile_picture_url}
          name={version.first_name}
          size="xxlarge"
        />
        <div className="flex-1">
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            {version.first_name} {version.last_name}
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-2">
            {version.professional_background}
          </p>
          <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
            <span className="flex items-center gap-1">
              <MapPin className="w-4 h-4" />
              {version.country}
            </span>
            <span className="flex items-center gap-1">
              <Briefcase className="w-4 h-4" />
              {version.expected_commitment}
            </span>
          </div>
        </div>
      </div>

      {/* Default Visible Fields */}
      {/* About */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">About</h4>
        <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
          {version.personal_statement}
        </p>
      </div>

      {/* Email */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Email</h4>
        <p className="text-sm text-gray-700 dark:text-gray-300">{version.email}</p>
      </div>

      {/* Industries - Default Visible */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
          Industries of Interest
        </h4>
        <div className="flex flex-wrap gap-2">
          {version.industries_of_interest?.map((industry, index) => (
            <span
              key={index}
              className="px-3 py-1 bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300 rounded-full text-xs font-medium border border-brand-200 dark:border-brand-800"
            >
              {industry}
            </span>
          ))}
        </div>
      </div>

      {/* Venture Stages - Default Visible */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
          <Target className="w-4 h-4" />
          Venture Stages
        </h4>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-600 dark:text-gray-400 mb-2">Current Stage:</p>
            <div className="flex flex-wrap gap-2">
              {version.venture_stage?.map((stage, index) => (
                <span
                  key={index}
                  className="px-2 py-1 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 rounded text-xs border border-orange-200 dark:border-orange-800"
                >
                  {stage}
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-gray-600 dark:text-gray-400 mb-2">Preferred Stages:</p>
            <div className="flex flex-wrap gap-2">
              {version.preferred_venture_stage?.map((stage, index) => (
                <span
                  key={index}
                  className="px-2 py-1 bg-teal-50 dark:bg-teal-900/20 text-teal-700 dark:text-teal-300 rounded text-xs border border-teal-200 dark:border-teal-800"
                >
                  {stage}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Looking For - Default Visible */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
          Looking For
        </h4>
        <div className="flex flex-wrap gap-2">
          {version.skills_needed?.map((skill, index) => (
            <span
              key={index}
              className="px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-xs font-medium border border-blue-200 dark:border-blue-800"
            >
              {skill}
            </span>
          ))}
        </div>
      </div>

      {isExpanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3 }}
          className="border-t border-gray-200 dark:border-gray-700 pt-6"
        >
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Complete Profile Details</h3>

          {/* Contact Information */}
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Contact Information</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              {version.linkedin_url && (
                <div>
                  <p className="text-gray-600 dark:text-gray-400 mb-1">LinkedIn</p>
                  <a href={version.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-brand-600 dark:text-brand-400 hover:underline break-all">
                    {version.linkedin_url}
                  </a>
                </div>
              )}
              {version.website_url && (
                <div>
                  <p className="text-gray-600 dark:text-gray-400 mb-1">Website</p>
                  <a href={version.website_url} target="_blank" rel="noopener noreferrer" className="text-brand-600 dark:text-brand-400 hover:underline break-all">
                    {version.website_url}
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Education */}
          {version.education && version.education.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Education</h4>
              <div className="space-y-2">
                {version.education.map((edu, index) => (
                  <div key={index} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                    <p className="text-sm text-gray-900 dark:text-white">{edu}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Achievement */}
          {version.achievement && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Notable Achievement</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                {version.achievement}
              </p>
            </div>
          )}

          {/* Responsibilities Offered */}
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
              What I Can Offer
            </h4>
            <div className="flex flex-wrap gap-2">
              {version.responsibilities_offered?.map((resp, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-full text-xs font-medium border border-green-200 dark:border-green-800"
                >
                  {resp}
                </span>
              ))}
            </div>
          </div>

          {/* Employment History */}
          {version.employment_history && Array.isArray(version.employment_history) && version.employment_history.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                Employment History
              </h4>
              <div className="space-y-3">
                {version.employment_history.map((job: any, index: number) => (
                  <div key={index} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                    <p className="font-medium text-gray-900 dark:text-white text-sm">{job.role_title}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{job.organization}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                      {job.start_date} - {job.is_current ? 'Present' : job.end_date}
                    </p>
                    {job.responsibilities_description && (
                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">{job.responsibilities_description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Languages */}
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
              <Languages className="w-4 h-4" />
              Preferred Languages
            </h4>
            <div className="flex flex-wrap gap-2">
              {version.preferred_languages?.map((lang, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 rounded-full text-xs font-medium border border-purple-200 dark:border-purple-800"
                >
                  {lang.code || lang.language}
                  {lang.importance === 'non_negotiable' && ' (Must Have)'}
                  {lang.importance === 'important' && ' (Nice to Have)'}
                </span>
              ))}
            </div>
          </div>

          {/* Location Preferences */}
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Location Preferences
            </h4>
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-gray-600 dark:text-gray-400">Current Location: </span>
                <span className="text-gray-900 dark:text-white font-medium">{version.country}</span>
              </div>
              {version.preferred_country && (
                <div>
                  <span className="text-gray-600 dark:text-gray-400">Preferred Cofounder Location: </span>
                  <span className="text-gray-900 dark:text-white font-medium">{version.preferred_country}</span>
                  {version.preferred_country_importance === 'non_negotiable' && (
                    <span className="ml-2 text-xs text-red-600 dark:text-red-400">(Must Have)</span>
                  )}
                  {version.preferred_country_importance === 'important' && (
                    <span className="ml-2 text-xs text-yellow-600 dark:text-yellow-400">(Nice to Have)</span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Commitment Preferences */}
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
              <Briefcase className="w-4 h-4" />
              Commitment
            </h4>
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-gray-600 dark:text-gray-400">My Commitment: </span>
                <span className="text-gray-900 dark:text-white font-medium">{version.expected_commitment}</span>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">Expected from Cofounder: </span>
                <span className="text-gray-900 dark:text-white font-medium">{version.preferred_commitment}</span>
                {version.commitment_importance === 'non_negotiable' && (
                  <span className="ml-2 text-xs text-red-600 dark:text-red-400">(Must Have)</span>
                )}
                {version.commitment_importance === 'important' && (
                  <span className="ml-2 text-xs text-yellow-600 dark:text-yellow-400">(Nice to Have)</span>
                )}
              </div>
            </div>
          </div>

          {/* Age Preferences */}
          {version.age_enabled && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Age Preference</h4>
              <div className="text-sm">
                <span className="text-gray-600 dark:text-gray-400">Preferred Age Range: </span>
                <span className="text-gray-900 dark:text-white font-medium">
                  {version.age_min || 'Any'} - {version.age_max || 'Any'} years
                </span>
                {version.age_importance === 'non_negotiable' && (
                  <span className="ml-2 text-xs text-red-600 dark:text-red-400">(Must Have)</span>
                )}
                {version.age_importance === 'important' && (
                  <span className="ml-2 text-xs text-yellow-600 dark:text-yellow-400">(Nice to Have)</span>
                )}
              </div>
            </div>
          )}

          {/* Social Links */}
          {version.social_links && Object.keys(version.social_links).length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Social Media</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(version.social_links).map(([platform, url]) => (
                  <div key={platform}>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-1 capitalize">{platform}</p>
                    <a href={url as string} target="_blank" rel="noopener noreferrer" className="text-sm text-brand-600 dark:text-brand-400 hover:underline break-all">
                      {url as string}
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Ideal Cofounder */}
          {(version as any).ideal_cofounder_description && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                Ideal Cofounder
              </h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                {(version as any).ideal_cofounder_description}
              </p>
            </div>
          )}
        </motion.div>
      )}

      {/* Show All / Show Less Button at Bottom */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-center">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 px-6 py-2 text-sm font-medium text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded-lg transition-colors"
        >
          {isExpanded ? 'Show Less' : 'Show All Details'}
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronLeft className="w-4 h-4 -rotate-90" />
          </motion.div>
        </button>
      </div>
    </div>
  );
}


interface VersionDetailModalProps {
  version: ProfileVersion;
  onClose: () => void;
}

function VersionDetailModal({ version, onClose }: VersionDetailModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
      >
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Profile Version Details
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-all"
          >
            <XCircle className="w-6 h-6" />
          </button>
        </div>
        <div className="p-6">
          <ProfilePreview version={version} title={`Version from ${new Date(version.created_at).toLocaleDateString()}`} />
        </div>
      </motion.div>
    </div>
  );
}
