'use client';

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  MapPin,
  Briefcase,
  Languages,
  Target,
  MessageCircle,
  AlertCircle,
  Clock,
  Ban,
  UserX,
  Flag,
  Star,
  Award,
  Globe,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import type { ProfileVersion } from '@/types/cofounder';
import UserAvatar from '@/components/ui/avatar/UserAvatar';
import { cofounderAPI } from '@/lib/api/cofounderService';
import { messagingAPI } from '@/lib/api/messagingService';
import { useReportModal } from '../../../hooks/useReportModal';
import ReportModal from '../reports/ReportModal';
import { LoadingSpinner } from '@/components/ui/loading-states';

const MotionDiv = motion.div;

interface ProfileDetailModalProps {
  versionId: string;
  userId?: string; // Pass user_id directly for messaging
  onClose: () => void;
}

export default function ProfileDetailModal({
  versionId,
  userId,
  onClose,
}: ProfileDetailModalProps) {
  const [profile, setProfile] = useState<ProfileVersion | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [messagingRestriction, setMessagingRestriction] = useState<{
    canContact: boolean;
    reason?: string;
    rateLimitExpiresAt?: string;
    isMatched?: boolean;
  } | null>(null);
  const [showRestrictionModal, setShowRestrictionModal] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [isCheckingMessaging, setIsCheckingMessaging] = useState(false);
  const reportModal = useReportModal();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setIsLoading(true);
        const data = await cofounderAPI.profiles.getDirectoryProfileByVersion(versionId);
        console.log('=== COFOUNDER FULL PROFILE ===', data);
        setProfile(data);
      } catch (err: any) {
        console.error('Failed to fetch profile:', err);
        setError(err.message || 'Failed to load profile');
      } finally {
        setIsLoading(false);
      }
    };

    fetchProfile();
  }, [versionId]);

  // Check messaging restrictions when profile loads
  useEffect(() => {
    const checkMessagingRestrictions = async () => {
      const targetUserId = userId || (profile as any)?.user_id;

      if (!targetUserId || !profile) {
        return;
      }

      try {
        setIsCheckingMessaging(true);
        const canContactResponse = await messagingAPI.canContact(targetUserId);

        if (!canContactResponse.can_contact) {
          setMessagingRestriction({
            canContact: false,
            reason: canContactResponse.reason,
            rateLimitExpiresAt: canContactResponse.rate_limit_expires_at,
            isMatched: canContactResponse.is_matched,
          });
        } else {
          setMessagingRestriction({
            canContact: true,
          });
        }
      } catch (error: any) {
        console.error('[ProfileDetailModal] Failed to check messaging restrictions:', error);
        // On error, assume messaging is allowed but will be checked again on click
        setMessagingRestriction({
          canContact: true,
        });
      } finally {
        setIsCheckingMessaging(false);
      }
    };

    checkMessagingRestrictions();
  }, [profile, userId]);

  const handleMessageClick = async () => {
    // Use userId prop if available, otherwise try to get from profile
    const targetUserId = userId || (profile as any)?.user_id;

    if (!targetUserId) {
      console.error('[ProfileDetailModal] Cannot message user: user_id not available', {
        userId,
        profileUserId: (profile as any)?.user_id,
        profile,
      });
      toast.error('Unable to message this user. User information not available.');
      return;
    }

    // If we already have restriction info and can't contact, show modal
    if (messagingRestriction && !messagingRestriction.canContact) {
      setShowRestrictionModal(true);
      return;
    }

    console.log('[ProfileDetailModal] Attempting to message user:', targetUserId);

    try {
      // Double-check if user can be contacted (in case state is stale)
      const canContactResponse = await messagingAPI.canContact(targetUserId);

      if (!canContactResponse.can_contact) {
        // Show restriction modal with detailed information
        setMessagingRestriction({
          canContact: false,
          reason: canContactResponse.reason,
          rateLimitExpiresAt: canContactResponse.rate_limit_expires_at,
          isMatched: canContactResponse.is_matched,
        });
        setShowRestrictionModal(true);
        return;
      }

      // Dispatch custom event to open chat
      const event = new CustomEvent('openChat', {
        detail: {
          participantId: targetUserId,
          participantName:
            (profile as any).full_name ||
            `${profile?.first_name} ${profile?.last_name}`,
          participantAvatar: profile?.profile_picture_url,
        },
      });

      console.log('[ProfileDetailModal] Dispatching openChat event:', event.detail);
      window.dispatchEvent(event);
      onClose(); // Close modal after opening chat
    } catch (error: any) {
      console.error('[ProfileDetailModal] Failed to check contact status:', error);
      toast.error(error.message || 'Unable to check messaging status');
    }
  };

  if (!mounted) return null;

  if (isLoading) {
    const loadingContent = (
      <div
        className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      >
        <MotionDiv
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 flex items-center justify-center"
        >
          <LoadingSpinner size="lg" className="text-brand-500 dark:text-brand-400" />
        </MotionDiv>
      </div>
    );
    return createPortal(loadingContent, document.body);
  }

  if (error || !profile) {
    const errorContent = (
      <div
        className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      >
        <MotionDiv
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 max-w-md text-center"
        >
          <p className="text-red-600 dark:text-red-400 mb-4">
            {error || 'Profile not found'}
          </p>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            Close
          </button>
        </MotionDiv>
      </div>
    );
    return createPortal(errorContent, document.body);
  }

  const employmentHistoryEntries = Array.isArray(profile.employment_history)
    ? profile.employment_history
    : (profile.employment_history as any)?.entries || [];

  const modalContent = (
    <>
      <MotionDiv
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            onClose();
          }
        }}
      >
      <MotionDiv
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white dark:bg-gray-900/80 border border-brand-200 dark:border-brand-700/50 rounded-2xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden backdrop-blur"
      >
        {/* Header */}
        <div className="p-6 border-b border-brand-200 dark:border-brand-700/50 bg-brand-50 dark:bg-brand-800/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-brand-500 dark:bg-brand-400 rounded-full" />
              <h2 className="text-xl font-semibold text-brand-700 dark:text-brand-200">
                Cofounder Profile
              </h2>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() =>
                  reportModal.openReportModal({
                    type: 'profile',
                    id: profile.profile_id,
                    name:
                      (profile as any).full_name ||
                      `${profile.first_name} ${profile.last_name}`,
                  })
                }
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-300 bg-red-50 dark:bg-red-900/30 rounded-full border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/40 transition"
              >
                <Flag className="w-4 h-4" />
                Report
              </button>
              <button
                onClick={onClose}
                className="w-10 h-10 rounded-xl bg-brand-100 dark:bg-brand-700/60 text-brand-600 dark:text-brand-200 flex items-center justify-center transition hover:rotate-90 hover:scale-105"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="flex flex-col max-h-[calc(90vh-80px)] overflow-y-auto">
          {/* Profile header */}
          <div className="p-6 bg-brand-25 dark:bg-brand-900/20 border-b border-brand-200 dark:border-brand-800/60">
            <div className="flex flex-col md:flex-row gap-6">
              <div className="flex flex-col items-center gap-4 flex-shrink-0">
                <div className="relative">
                  <div className="w-32 h-32 rounded-2xl overflow-hidden border-4 border-brand-200 dark:border-brand-600/40 shadow-lg ring-2 ring-brand-100 dark:ring-brand-700/30">
                    {profile.profile_picture_url ? (
                      <img
                        src={profile.profile_picture_url}
                        alt={
                          (profile as any).full_name ||
                          `${profile.first_name} ${profile.last_name}`
                        }
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-brand-100 dark:bg-brand-800 flex items-center justify-center text-brand-600 dark:text-brand-300 text-3xl font-semibold">
                        {((profile as any).full_name ||
                          `${profile.first_name} ${profile.last_name}`)
                          .split(' ')
                          .map((n: string) => n[0])
                          .join('')
                          .toUpperCase()
                          .slice(0, 2)}
                      </div>
                    )}
                  </div>
                </div>
                <button
                  onClick={handleMessageClick}
                  disabled={isCheckingMessaging || (messagingRestriction !== null && !messagingRestriction.canContact)}
                  title={
                    messagingRestriction && !messagingRestriction.canContact
                      ? messagingRestriction.reason || 'Cannot send message'
                      : undefined
                  }
                  className={`inline-flex items-center gap-2 px-5 py-2 rounded-full text-sm font-semibold shadow transition ${
                    isCheckingMessaging || (messagingRestriction !== null && !messagingRestriction.canContact)
                      ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                      : 'bg-brand-500 text-white hover:bg-brand-600'
                  }`}
                >
                  <MessageCircle className="w-4 h-4" />
                  {isCheckingMessaging ? 'Checking...' : 'Message'}
                </button>
              </div>

              <div className="flex-1 space-y-4">
                <div className="flex flex-col lg:flex-row lg:items-start gap-4">
                  <div className="flex-1">
                    <h3 className="text-3xl font-bold text-brand-700 dark:text-brand-100">
                      {(profile as any).full_name ||
                        `${profile.first_name} ${profile.last_name}`}
                    </h3>
                    <p className="text-sm text-brand-600 dark:text-brand-200 mt-1">
                      {profile.professional_background || 'Entrepreneur'}
                    </p>
                    <div className="flex flex-wrap items-center gap-3 mt-4 text-sm text-gray-600 dark:text-gray-300">
                      <span className="inline-flex items-center gap-2 px-3 py-1 bg-white/70 dark:bg-gray-800/50 rounded-full border border-brand-100 dark:border-brand-800">
                        <MapPin className="w-4 h-4 text-brand-500" />
                        {profile.country}
                      </span>
                      <span className="inline-flex items-center gap-2 px-3 py-1 bg-white/70 dark:bg-gray-800/50 rounded-full border border-brand-100 dark:border-brand-800">
                        <Briefcase className="w-4 h-4 text-brand-500" />
                        {(profile as any).preferred_commitment ||
                          profile.expected_commitment}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-wrap">
                    <div className="flex items-center gap-2 px-3 py-1 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-full border border-green-200 dark:border-green-800 text-sm font-medium">
                      <Star className="w-4 h-4" />
                      Ready to build
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-200 rounded-full border border-blue-200 dark:border-blue-800 text-sm font-medium">
                      <Award className="w-4 h-4" />
                      Verified
                    </div>
                  </div>
                </div>

                {profile.personal_statement && (
                  <p className="text-sm text-brand-700/80 dark:text-brand-100/80 leading-relaxed">
                    {profile.personal_statement}
                  </p>
                )}

                {(profile.linkedin_url ||
                  profile.website_url ||
                  (profile.social_links &&
                    Object.keys(profile.social_links).length > 0)) && (
                  <div className="flex flex-wrap gap-3 text-sm">
                    {profile.linkedin_url && (
                      <a
                        href={profile.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-brand-100 dark:border-brand-800 text-brand-600 dark:text-brand-300 bg-white/80 dark:bg-gray-800/60 hover:bg-brand-50 transition"
                      >
                        <Globe className="w-4 h-4" />
                        LinkedIn
                      </a>
                    )}
                    {profile.website_url && (
                      <a
                        href={profile.website_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-brand-100 dark:border-brand-800 text-brand-600 dark:text-brand-300 bg-white/80 dark:bg-gray-800/60 hover:bg-brand-50 transition"
                      >
                        <Globe className="w-4 h-4" />
                        Website
                      </a>
                    )}
                    {profile.social_links &&
                      Object.entries(profile.social_links).map(
                        ([platform, url]) => (
                          <a
                            key={platform}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-brand-100 dark:border-brand-800 text-brand-600 dark:text-brand-300 bg-white/80 dark:bg-gray-800/60 capitalize hover:bg-brand-50 transition"
                          >
                            <Globe className="w-4 h-4" />
                            {platform}
                          </a>
                        ),
                      )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Details */}
          <div className="px-6 py-8 space-y-8 bg-white dark:bg-gray-900/40">
            {profile.achievement && (
              <div className="rounded-2xl border border-brand-100 dark:border-brand-800/60 bg-brand-25 dark:bg-brand-900/10 p-6 shadow-sm">
                <h4 className="text-base font-semibold text-brand-700 dark:text-brand-200 mb-2">
                  Notable Achievement
                </h4>
                <p className="text-sm text-brand-700/90 dark:text-brand-100/90 leading-relaxed">
                  {profile.achievement}
                </p>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {profile.responsibilities_offered &&
                profile.responsibilities_offered.length > 0 && (
                  <div className="rounded-2xl border border-green-100 dark:border-green-900/40 bg-green-50/40 dark:bg-green-900/10 p-5">
                    <h4 className="flex items-center gap-2 text-sm font-semibold text-green-800 dark:text-green-200 mb-3">
                      <Briefcase className="w-4 h-4" />
                      What I Can Offer
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {profile.responsibilities_offered.map((item, index) => (
                        <span
                          key={index}
                          className="px-3 py-1 text-xs font-medium bg-white/80 dark:bg-green-900/30 rounded-full text-green-700 dark:text-green-200 border border-green-100 dark:border-green-800"
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              {profile.skills_needed && profile.skills_needed.length > 0 && (
                <div className="rounded-2xl border border-blue-100 dark:border-blue-900/40 bg-blue-50/40 dark:bg-blue-900/10 p-5">
                  <h4 className="flex items-center gap-2 text-sm font-semibold text-blue-800 dark:text-blue-200 mb-3">
                    <Target className="w-4 h-4" />
                    Looking For
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {profile.skills_needed.map((item, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 text-xs font-medium bg-white/80 dark:bg-blue-900/30 rounded-full text-blue-700 dark:text-blue-200 border border-blue-100 dark:border-blue-800"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {profile.industries_of_interest &&
              profile.industries_of_interest.length > 0 && (
                <div className="rounded-2xl border border-purple-100 dark:border-purple-900/40 bg-purple-50/40 dark:bg-purple-900/10 p-5">
                  <h4 className="text-sm font-semibold text-purple-800 dark:text-purple-200 mb-3">
                    Industries of Interest
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {profile.industries_of_interest.map((item, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 text-xs font-medium bg-white/80 dark:bg-purple-900/30 rounded-full text-purple-700 dark:text-purple-200 border border-purple-100 dark:border-purple-800"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}

            {profile.preferred_languages &&
              profile.preferred_languages.length > 0 && (
                <div className="rounded-2xl border border-brand-100 dark:border-brand-900/30 p-5">
                  <h4 className="flex items-center gap-2 text-sm font-semibold text-brand-800 dark:text-brand-100 mb-3">
                    <Languages className="w-4 h-4" />
                    Preferred Languages
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {profile.preferred_languages.map((lang: any, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 text-xs font-medium bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-200 rounded-full border border-brand-100 dark:border-brand-800"
                      >
                        {lang.code || (lang as any).language}
                        {lang.importance === 'non_negotiable' && ' · Must have'}
                        {lang.importance === 'important' && ' · Nice to have'}
                      </span>
                    ))}
                  </div>
                </div>
              )}

            {(profile.education && profile.education.length > 0) ||
            employmentHistoryEntries.length > 0 ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {profile.education && profile.education.length > 0 && (
                  <div className="rounded-2xl border border-gray-100 dark:border-gray-800/60 p-5 bg-white/80 dark:bg-gray-900/40">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
                      Education
                    </h4>
                    <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
                      {profile.education.map((edu, index) => (
                        <div
                          key={index}
                          className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-700/60"
                        >
                          {edu}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {employmentHistoryEntries.length > 0 && (
                  <div className="rounded-2xl border border-gray-100 dark:border-gray-800/60 p-5 bg-white/80 dark:bg-gray-900/40">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
                      Experience
                    </h4>
                    <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
                      {employmentHistoryEntries.map((job: any, index: number) => (
                        <div
                          key={index}
                          className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-700/60"
                        >
                          <div className="font-medium text-gray-900 dark:text-white">
                            {job.role_title} · {job.organization}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {job.start_date} -{' '}
                            {job.is_current ? 'Present' : job.end_date}
                          </div>
                          {job.responsibilities_description && (
                            <p className="mt-2 text-xs leading-relaxed">
                              {job.responsibilities_description}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : null}

            {profile.venture_stage && profile.venture_stage.length > 0 && (
              <div className="rounded-2xl border border-indigo-100 dark:border-indigo-900/30 p-5 bg-indigo-50/40 dark:bg-indigo-900/10">
                <h4 className="flex items-center gap-2 text-sm font-semibold text-indigo-800 dark:text-indigo-200 mb-3">
                  <Target className="w-4 h-4" />
                  Current Venture Stage
                </h4>
                <div className="flex flex-wrap gap-2">
                  {profile.venture_stage.map((stage: string, index: number) => (
                    <span
                      key={index}
                      className="px-3 py-1 text-xs font-medium bg-white/80 dark:bg-indigo-900/30 rounded-full text-indigo-700 dark:text-indigo-200 border border-indigo-100 dark:border-indigo-800"
                    >
                      {stage}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(profile as any).preferred_venture_stage &&
              (profile as any).preferred_venture_stage.length > 0 && (
                <div className="rounded-2xl border border-teal-100 dark:border-teal-900/30 p-5 bg-teal-50/40 dark:bg-teal-900/10">
                  <h4 className="flex items-center gap-2 text-sm font-semibold text-teal-800 dark:text-teal-200 mb-3">
                    <Target className="w-4 h-4" />
                    Preferred Venture Stages
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {(profile as any).preferred_venture_stage.map(
                      (stage: string, index: number) => (
                        <span
                          key={index}
                          className="px-3 py-1 text-xs font-medium bg-white/80 dark:bg-teal-900/30 rounded-full text-teal-700 dark:text-teal-200 border border-teal-100 dark:border-teal-800"
                        >
                          {stage}
                        </span>
                      ),
                    )}
                  </div>
                </div>
              )}

            {(profile as any).ideal_cofounder_description && (
              <div className="rounded-2xl border border-orange-100 dark:border-orange-900/30 p-5 bg-orange-50/40 dark:bg-orange-900/10">
                <h4 className="text-sm font-semibold text-orange-800 dark:text-orange-200 mb-3">
                  Ideal Cofounder
                </h4>
                <p className="text-sm text-orange-900/80 dark:text-orange-100 leading-relaxed">
                  {(profile as any).ideal_cofounder_description}
                </p>
              </div>
            )}
          </div>
        </div>
      </MotionDiv>

      {/* Messaging Restriction Modal */}
      <AnimatePresence>
        {showRestrictionModal &&
          messagingRestriction &&
          !messagingRestriction.canContact && (
            <div
              className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50"
              onClick={() => setShowRestrictionModal(false)}
            >
              <MotionDiv
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6"
              >
                <div className="flex items-start gap-4 mb-4">
                  {/* Icon based on error type */}
                  {messagingRestriction.rateLimitExpiresAt && (
                    <div className="p-3 bg-orange-100 dark:bg-orange-900/20 rounded-full">
                      <Clock className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                    </div>
                  )}
                  {(messagingRestriction.reason === 'You cannot send messages to this user because you have been blocked.' ||
                    messagingRestriction.reason === 'You have blocked this user. Unblock them to send messages.') && (
                    <div className="p-3 bg-red-100 dark:bg-red-900/20 rounded-full">
                      <Ban className="w-6 h-6 text-red-600 dark:text-red-400" />
                    </div>
                  )}
                  {messagingRestriction.isMatched === false && (
                    <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-full">
                      <UserX className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                    </div>
                  )}
                  {!messagingRestriction.rateLimitExpiresAt &&
                    messagingRestriction.reason !== 'You cannot send messages to this user because you have been blocked.' &&
                    messagingRestriction.reason !== 'You have blocked this user. Unblock them to send messages.' &&
                    messagingRestriction.isMatched !== false && (
                      <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-full">
                        <AlertCircle className="w-6 h-6 text-gray-600 dark:text-gray-400" />
                      </div>
                    )}

                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                      Cannot Send Message
                    </h3>

                    {/* Rate Limit Exceeded */}
                    {messagingRestriction.rateLimitExpiresAt && (
                      <div className="space-y-2">
                        <div className="p-3 bg-orange-50 dark:bg-orange-900/10 border border-orange-200 dark:border-orange-800 rounded-lg">
                          <p className="text-sm text-orange-800 dark:text-orange-200 font-medium">
                            You can only message one cofounder at a time. Please wait 48 hours before messaging another person.
                          </p>
                          <p className="text-xs text-orange-600 dark:text-orange-300 mt-2">
                            Next available: {new Date(messagingRestriction.rateLimitExpiresAt).toLocaleString()}
                          </p>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                          You can message users you've matched with at any time. Rate limits only apply to new conversations.
                        </p>
                      </div>
                    )}

                    {/* User Blocked (by them) */}
                    {messagingRestriction.reason === 'You cannot send messages to this user because you have been blocked.' && (
                      <div className="space-y-2">
                        <div className="p-3 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg">
                          <p className="text-sm text-red-800 dark:text-red-200">
                            You cannot send messages to this user because you have been blocked.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* User Blocked By You */}
                    {messagingRestriction.reason === 'You have blocked this user. Unblock them to send messages.' && (
                      <div className="space-y-2">
                        <div className="p-3 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg">
                          <p className="text-sm text-red-800 dark:text-red-200 font-medium">
                            You have blocked this user
                          </p>
                          <p className="text-xs text-red-600 dark:text-red-300 mt-1">
                            Unblock them from your settings to send messages.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Self Message */}
                    {messagingRestriction.reason === 'You cannot send messages to yourself.' && (
                      <div className="space-y-2">
                        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg">
                          <p className="text-sm text-gray-800 dark:text-gray-200">
                            You cannot send messages to yourself.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* User Not Found */}
                    {messagingRestriction.reason === 'The recipient user was not found.' && (
                      <div className="space-y-2">
                        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                          <p className="text-sm text-yellow-800 dark:text-yellow-200">
                            The recipient user was not found. They may have deleted their account.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Not Matched */}
                    {messagingRestriction.isMatched === false && (
                      <div className="space-y-2">
                        <div className="p-3 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg">
                          <p className="text-sm text-blue-800 dark:text-blue-200 font-medium">
                            Complete your profile to start messaging
                          </p>
                          <p className="text-xs text-blue-600 dark:text-blue-300 mt-1">
                            Both users must have approved cofounder profiles to message each other.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Encryption/Decryption Failed */}
                    {(messagingRestriction.reason === 'Failed to encrypt the message.' ||
                      messagingRestriction.reason === 'Failed to decrypt the message.') && (
                      <div className="space-y-2">
                        <div className="p-3 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg">
                          <p className="text-sm text-red-800 dark:text-red-200 font-medium">
                            Security Error
                          </p>
                          <p className="text-xs text-red-600 dark:text-red-300 mt-1">
                            {messagingRestriction.reason} Please try again or contact support.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Thread Not Found / Unauthorized */}
                    {(messagingRestriction.reason === 'The message thread was not found.' ||
                      messagingRestriction.reason === 'You are not authorized to access this thread.') && (
                      <div className="space-y-2">
                        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg">
                          <p className="text-sm text-gray-800 dark:text-gray-200">
                            {messagingRestriction.reason}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Generic/Unknown Reason */}
                    {messagingRestriction.reason &&
                      !messagingRestriction.rateLimitExpiresAt &&
                      messagingRestriction.isMatched !== false &&
                      messagingRestriction.reason !== 'You cannot send messages to this user because you have been blocked.' &&
                      messagingRestriction.reason !== 'You have blocked this user. Unblock them to send messages.' &&
                      messagingRestriction.reason !== 'You cannot send messages to yourself.' &&
                      messagingRestriction.reason !== 'The recipient user was not found.' &&
                      messagingRestriction.reason !== 'Failed to encrypt the message.' &&
                      messagingRestriction.reason !== 'Failed to decrypt the message.' &&
                      messagingRestriction.reason !== 'The message thread was not found.' &&
                      messagingRestriction.reason !== 'You are not authorized to access this thread.' && (
                        <div className="space-y-2">
                          <div className="p-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg">
                            <p className="text-sm text-gray-800 dark:text-gray-200">
                              {messagingRestriction.reason}
                            </p>
                          </div>
                        </div>
                      )}
                  </div>
                </div>

                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => setShowRestrictionModal(false)}
                    className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-all font-medium"
                  >
                    Close
                  </button>
                  {messagingRestriction.isMatched === false && (
                    <a
                      href="/workspace/cofounder-matching"
                      className="flex-1 px-4 py-2 bg-brand-500 dark:bg-brand-400 text-white rounded-lg hover:bg-brand-600 dark:hover:bg-brand-500 transition-all font-medium text-center"
                    >
                      Create Profile
                    </a>
                  )}
                </div>
              </MotionDiv>
            </div>
          )}
      </AnimatePresence>
    </MotionDiv>

      {/* Report Modal - Outside main modal for proper overlay */}
      {reportModal.isOpen &&
        reportModal.targetId &&
        reportModal.reportType && (
          <ReportModal
            isOpen={reportModal.isOpen}
            onClose={reportModal.closeReportModal}
            reportType={reportModal.reportType}
            targetId={reportModal.targetId}
            targetName={reportModal.targetName || undefined}
          />
        )}
    </>
  );

  return createPortal(modalContent, document.body);
}
