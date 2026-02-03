'use client';

import { useState } from 'react';
import {
  MessageCircle,
  MapPin,
  Flag,
  Eye,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import type { DirectoryProfile } from '@/types/cofounder';
import UserAvatar from '@/components/ui/avatar/UserAvatar';
import React from 'react';
import { useReportModal } from '../../../hooks/useReportModal';
import ReportModal from '../reports/ReportModal';
import ProfileDetailModal from './ProfileDetailModal';

interface ProfileCardProps {
  profile: DirectoryProfile;
  matchScore?: number | null;
}

export default function ProfileCard({ profile, matchScore }: ProfileCardProps) {
  const reportModal = useReportModal();
  const [showReportTooltip, setShowReportTooltip] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);

  const handleMessageClick = (e: React.MouseEvent) => {
    e.stopPropagation();

    if (profile.can_message === false) {
      toast.error('You can only message one cofounder at a time. Please wait 48 hours before messaging another person.');
      return;
    }

    if (!profile.user_id) {
      toast.error('Unable to message this user.');
      return;
    }

    const event = new CustomEvent('openChat', {
      detail: {
        participantId: profile.user_id,
        participantName:
          profile.full_name ||
          `${profile.first_name} ${profile.last_name}`,
        participantAvatar: profile.profile_picture_url,
      },
    });

    window.dispatchEvent(event);
  };

  const handleReportClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    reportModal.openReportModal({
      type: 'profile',
      id: profile.profile_id,
      name:
        profile.full_name ||
        `${profile.first_name} ${profile.last_name}`,
    });
  };

  return (
    <>
      <div
        className="
          relative flex flex-col h-full max-w-sm mx-auto
          rounded-lg border border-gray-200/70 dark:border-gray-700/60
          bg-white dark:bg-gray-900
          p-4
          transition-shadow hover:shadow-md
        "
      >
        {/* Report Button */}
        <div className="absolute top-2 right-2 z-10">
          <div className="relative">
            <button
              onClick={handleReportClick}
              onMouseEnter={() => setShowReportTooltip(true)}
              onMouseLeave={() => setShowReportTooltip(false)}
              className="
                p-1.5 rounded-md
                bg-red-50 hover:bg-red-100
                dark:bg-red-900/20 dark:hover:bg-red-900/30
                text-red-600 dark:text-red-400
                transition-colors
              "
              title="Report"
            >
              <Flag className="w-4 h-4" />
            </button>

            {showReportTooltip && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded">
                Report
              </div>
            )}
          </div>
        </div>

        {/* Avatar + Country */}
        <div className="flex flex-col items-center pt-6 mb-4">
          <div className="relative mb-6">
            <UserAvatar
              src={profile.profile_picture_url}
              name={
                profile.full_name ||
                `${profile.first_name || ''} ${profile.last_name || ''}`
              }
              size="xxlarge"
              className="
                w-28 h-28 sm:w-32 sm:h-32
                border-2 border-gray-100 dark:border-gray-700
                shadow-md
              "
            />

            {profile.country && (
              <div
                className="
                  absolute -bottom-3 left-1/2 -translate-x-1/2
                  flex items-center gap-1
                  px-2.5 py-1
                  bg-blue-50 dark:bg-blue-900/20
                  text-blue-700 dark:text-blue-300
                  rounded-full text-xs
                  border border-blue-200/60 dark:border-blue-800/50
                  shadow-sm
                  whitespace-nowrap
                "
              >
                <MapPin className="w-3.5 h-3.5" />
                <span className="font-medium">{profile.country}</span>
              </div>
            )}
          </div>

          {/* Name */}
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white text-center mb-1">
            {profile.full_name ||
              `${profile.first_name || ''} ${profile.last_name || ''}`}
          </h3>

          {/* Professional Background */}
          {profile.professional_background && (
            <p className="text-sm text-gray-600 dark:text-gray-400 text-center line-clamp-2 px-2">
              {profile.professional_background}
            </p>
          )}
        </div>

        <div className="flex-1" />

        {/* Actions */}
        <div className="mt-4 pt-3 border-t border-gray-200/60 dark:border-gray-700/50 flex gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowProfileModal(true);
            }}
            className="
              flex-1 inline-flex items-center justify-center gap-2
              rounded-md
              bg-gray-100 hover:bg-gray-200
              dark:bg-gray-800 dark:hover:bg-gray-700
              text-gray-700 dark:text-gray-200
              text-xs sm:text-sm
              px-3 py-2
              transition-colors
            "
          >
            <Eye className="w-4 h-4" />
            View Profile
          </button>

          <button
            onClick={handleMessageClick}
            disabled={profile.can_message === false}
            className={`
              flex-1 inline-flex items-center justify-center gap-2
              rounded-md
              text-xs sm:text-sm
              px-3 py-2
              shadow-sm
              transition-colors
              ${
                profile.can_message === false
                  ? 'bg-gray-300 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed opacity-60'
                  : 'bg-brand-600 hover:bg-brand-700 text-white'
              }
            `}
          >
            <MessageCircle className="w-4 h-4" />
            Message
          </button>
        </div>
      </div>

      {/* Modals */}
      {reportModal.isOpen && reportModal.targetId && reportModal.reportType && (
        <ReportModal
          isOpen={reportModal.isOpen}
          onClose={reportModal.closeReportModal}
          reportType={reportModal.reportType}
          targetId={reportModal.targetId}
          targetName={reportModal.targetName || undefined}
        />
      )}

      {showProfileModal && (
        <ProfileDetailModal
          versionId={profile.version_id || ''}
          userId={profile.user_id || ''}
          onClose={() => setShowProfileModal(false)}
        />
      )}
    </>
  );
}
