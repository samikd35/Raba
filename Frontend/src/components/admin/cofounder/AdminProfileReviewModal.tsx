
'use client';

import React from 'react';
import { createPortal } from 'react-dom';
import { motion } from 'framer-motion';
import {
  X,
  MapPin,
  Briefcase,
  CheckCircle,
  XCircle,
  Loader2,
  Globe,
  Target,
  Languages,
  Calendar,
  GraduationCap,
  Mail,
  User,
  Cake,
  Filter,
  Users,
  Award,
  Lightbulb,
} from 'lucide-react';
import type { ProfileVersion } from '@/types/cofounder';
import UserAvatar from '@/components/ui/avatar/UserAvatar';

const MotionDiv = motion.div;

interface AdminProfileReviewModalProps {
  profile: ProfileVersion;
  onClose: () => void;
  onApprove: () => void;
  onReject: () => void;
  actionLoading: boolean;
}

export default function AdminProfileReviewModal({
  profile,
  onClose,
  onApprove,
  onReject,
  actionLoading,
}: AdminProfileReviewModalProps) {
  const employmentHistoryEntries = Array.isArray(profile.employment_history)
    ? profile.employment_history
    : (profile.employment_history as any)?.entries || [];

  const modalContent = (
    <MotionDiv
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <MotionDiv
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        onClick={(e) => e.stopPropagation()}
        className="
          bg-white dark:bg-gray-900/80
          border border-brand-200 dark:border-brand-700/50
          rounded-2xl shadow-2xl
          max-w-5xl w-full
          max-h-[90vh]
          overflow-hidden
          backdrop-blur
          flex flex-col
        "
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-4 p-4 sm:p-6 border-b border-brand-200 dark:border-brand-700/50 bg-brand-50 dark:bg-brand-800/40">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-2 h-2 bg-brand-500 dark:bg-brand-400 rounded-full flex-shrink-0" />
            <h2 className="text-lg sm:text-xl font-semibold text-brand-700 dark:text-brand-200 truncate">
              Admin Review - Cofounder Profile
            </h2>
          </div>

          <button
            onClick={onClose}
            className="w-10 h-10 flex-shrink-0 rounded-xl bg-brand-100 dark:bg-brand-700/60 text-brand-600 dark:text-brand-200 flex items-center justify-center transition hover:rotate-90 hover:scale-105"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body (scrollable) */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {/* Profile header */}
          <div className="p-4 sm:p-6 bg-brand-25 dark:bg-brand-900/20 border-b border-brand-200 dark:border-brand-800/60">
            <div className="flex flex-col md:flex-row gap-6">
              <div className="flex flex-col items-center gap-4 flex-shrink-0">
                <UserAvatar
                  src={profile.profile_picture_url}
                  name={`${profile.first_name} ${profile.last_name}`}
                  size="xxlarge"
                />
              </div>

              <div className="flex-1 space-y-4 min-w-0">
                <div className="flex flex-col lg:flex-row lg:items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-2xl sm:text-3xl font-bold text-brand-700 dark:text-brand-100 break-words">
                      {profile.first_name} {profile.last_name}
                    </h3>
                    <p className="text-sm text-brand-600 dark:text-brand-200 mt-1">
                      {profile.professional_background || 'Entrepreneur'}
                    </p>

                    <div className="flex flex-wrap items-center gap-3 mt-4 text-sm text-gray-600 dark:text-gray-300">
                      {profile.country && (
                        <span className="inline-flex items-center gap-2 px-3 py-1 bg-white/70 dark:bg-gray-800/50 rounded-full border border-brand-100 dark:border-brand-800">
                          <MapPin className="w-4 h-4 text-brand-500" />
                          {profile.country}
                        </span>
                      )}

                      {profile.expected_commitment && (
                        <span className="inline-flex items-center gap-2 px-3 py-1 bg-white/70 dark:bg-gray-800/50 rounded-full border border-brand-100 dark:border-brand-800">
                          <Briefcase className="w-4 h-4 text-brand-500" />
                          {profile.expected_commitment}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {profile.personal_statement && (
                  <p className="text-sm text-brand-700/80 dark:text-brand-100/80 leading-relaxed break-words">
                    {profile.personal_statement}
                  </p>
                )}

                {(profile.linkedin_url ||
                  profile.website_url ||
                  (profile.social_links && Object.keys(profile.social_links).length > 0)) && (
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
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Details */}
          <div className="px-4 sm:px-6 py-6 sm:py-8 space-y-8 bg-white dark:bg-gray-900/40">
            {/* Personal Information */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl border border-brand-100 dark:border-brand-800/60 bg-white/70 dark:bg-gray-800/30">
                <div className="flex items-center gap-2 text-brand-600 dark:text-brand-300 mb-2">
                  <Mail className="w-4 h-4" />
                  <h4 className="text-sm font-semibold">Email</h4>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300 break-all">{profile.email}</p>
              </div>
              <div className="p-4 rounded-xl border border-brand-100 dark:border-brand-800/60 bg-white/70 dark:bg-gray-800/30">
                <div className="flex items-center gap-2 text-brand-600 dark:text-brand-300 mb-2">
                  <User className="w-4 h-4" />
                  <h4 className="text-sm font-semibold">Gender</h4>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">{profile.gender}</p>
              </div>
              <div className="p-4 rounded-xl border border-brand-100 dark:border-brand-800/60 bg-white/70 dark:bg-gray-800/30">
                <div className="flex items-center gap-2 text-brand-600 dark:text-brand-300 mb-2">
                  <Cake className="w-4 h-4" />
                  <h4 className="text-sm font-semibold">Date of Birth</h4>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">{profile.date_of_birth}</p>
              </div>
            </div>

            {profile.achievement && (
              <div className="rounded-2xl border border-brand-100 dark:border-brand-800/60 bg-brand-25 dark:bg-brand-900/10 p-4 sm:p-6 shadow-sm">
                <h4 className="text-base font-semibold text-brand-700 dark:text-brand-200 mb-2">
                  Notable Achievement
                </h4>
                <p className="text-sm text-brand-700/90 dark:text-brand-100/90 leading-relaxed break-words">
                  {profile.achievement}
                </p>
              </div>
            )}

            {/* Education */}
            {profile.education && profile.education.length > 0 && (
              <div>
                <h4 className="text-base font-semibold text-brand-700 dark:text-brand-200 mb-4 flex items-center gap-2">
                  <GraduationCap className="w-5 h-5" />
                  Education
                </h4>
                <div className="space-y-2">
                  {profile.education.map((edu, index) => (
                    <div
                      key={index}
                      className="p-4 rounded-xl border border-brand-100 dark:border-brand-800/60 bg-white/70 dark:bg-gray-800/30"
                    >
                      <p className="text-sm text-gray-700 dark:text-gray-300 break-words">{edu}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Industries of Interest */}
            {profile.industries_of_interest && profile.industries_of_interest.length > 0 && (
              <div>
                <h4 className="text-base font-semibold text-brand-700 dark:text-brand-200 mb-4 flex items-center gap-2">
                  <Target className="w-5 h-5" />
                  Industries of Interest
                </h4>
                <div className="flex flex-wrap gap-2">
                  {profile.industries_of_interest.map((industry, index) => (
                    <span
                      key={index}
                      className="px-4 py-2 bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300 rounded-full text-sm border border-brand-200 dark:border-brand-800"
                    >
                      {industry}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Responsibilities Offered */}
            {profile.responsibilities_offered && profile.responsibilities_offered.length > 0 && (
              <div>
                <h4 className="text-base font-semibold text-brand-700 dark:text-brand-200 mb-4 flex items-center gap-2">
                  <Award className="w-5 h-5" />
                  Responsibilities Offered
                </h4>
                <div className="flex flex-wrap gap-2">
                  {profile.responsibilities_offered.map((resp, index) => (
                    <span
                      key={index}
                      className="px-4 py-2 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-full text-sm border border-green-200 dark:border-green-800"
                    >
                      {resp}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Skills Needed */}
            {profile.skills_needed && profile.skills_needed.length > 0 && (
              <div>
                <h4 className="text-base font-semibold text-brand-700 dark:text-brand-200 mb-4 flex items-center gap-2">
                  <Lightbulb className="w-5 h-5" />
                  Skills Needed in Cofounder
                </h4>
                <div className="flex flex-wrap gap-2">
                  {profile.skills_needed.map((skill, index) => (
                    <span
                      key={index}
                      className="px-4 py-2 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 rounded-full text-sm border border-orange-200 dark:border-orange-800"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Employment History */}
            {employmentHistoryEntries.length > 0 && (
              <div>
                <h4 className="text-base font-semibold text-brand-700 dark:text-brand-200 mb-4 flex items-center gap-2">
                  <Briefcase className="w-5 h-5" />
                  Employment History
                </h4>
                <div className="space-y-4">
                  {employmentHistoryEntries.map((job: any, index: number) => (
                    <div
                      key={index}
                      className="p-4 sm:p-5 rounded-xl border border-brand-100 dark:border-brand-800/60 bg-white/70 dark:bg-gray-800/30"
                    >
                      <div className="font-semibold text-brand-700 dark:text-brand-200 break-words">
                        {job.role} at {job.organization}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400 mt-1 flex items-center gap-1 flex-wrap">
                        <Calendar className="w-3.5 h-3.5" />
                        <span className="break-words">
                          {job.start_date} - {job.is_current ? 'Present' : job.end_date}
                        </span>
                      </div>
                      {job.responsibilities && (
                        <p className="text-sm text-gray-700 dark:text-gray-300 mt-3 break-words">
                          {job.responsibilities}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Preferred Languages */}
            {profile.preferred_languages && profile.preferred_languages.length > 0 && (
              <div>
                <h4 className="text-base font-semibold text-brand-700 dark:text-brand-200 mb-4 flex items-center gap-2">
                  <Languages className="w-5 h-5" />
                  Preferred Cofounder Languages
                </h4>
                <div className="flex flex-wrap gap-2">
                  {profile.preferred_languages.map((lang, index) => (
                    <span
                      key={index}
                      className="px-4 py-2 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 rounded-full text-sm border border-purple-200 dark:border-purple-800"
                    >
                      {lang.code || lang.language}
                      {lang.importance === 'non_negotiable' && ' (Must Have)'}
                      {lang.importance === 'important' && ' (Nice to Have)'}
                    </span>
                  ))}
                </div>
                {profile.language_importance && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                    Overall Importance: {profile.language_importance === 'non_negotiable' ? 'Must Have' : 'Nice to Have'}
                  </p>
                )}
              </div>
            )}

            {/* Location Preferences */}
            {profile.preferred_country && (
              <div>
                <h4 className="text-base font-semibold text-brand-700 dark:text-brand-200 mb-4 flex items-center gap-2">
                  <MapPin className="w-5 h-5" />
                  Preferred Cofounder Location
                </h4>
                <div className="p-4 rounded-xl border border-brand-100 dark:border-brand-800/60 bg-white/70 dark:bg-gray-800/30">
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    {profile.preferred_country}
                  </p>
                  {profile.preferred_country_importance && (
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                      Importance: {profile.preferred_country_importance === 'non_negotiable' ? 'Must Have' : 'Nice to Have'}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Commitment & Stage */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-4 rounded-xl border border-brand-100 dark:border-brand-800/60 bg-white/70 dark:bg-gray-800/30">
                <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-200 mb-2">
                  Expected Commitment
                </h4>
                <p className="text-sm text-gray-700 dark:text-gray-300 break-words">
                  {profile.expected_commitment}
                </p>
              </div>
              <div className="p-4 rounded-xl border border-brand-100 dark:border-brand-800/60 bg-white/70 dark:bg-gray-800/30">
                <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-200 mb-2">
                  Preferred Cofounder Commitment
                </h4>
                <p className="text-sm text-gray-700 dark:text-gray-300 break-words">
                  {profile.preferred_commitment}
                </p>
                {profile.commitment_importance && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    Importance: {profile.commitment_importance === 'non_negotiable' ? 'Must Have' : 'Nice to Have'}
                  </p>
                )}
              </div>
            </div>

            {/* Venture Stage */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {profile.venture_stage && profile.venture_stage.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-200 mb-2">
                    Current Venture Stage
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {profile.venture_stage.map((stage, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-sm border border-blue-200 dark:border-blue-800"
                      >
                        {stage}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {profile.preferred_venture_stage && profile.preferred_venture_stage.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-200 mb-2">
                    Preferred Cofounder Venture Stage
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {profile.preferred_venture_stage.map((stage, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 rounded-full text-sm border border-indigo-200 dark:border-indigo-800"
                      >
                        {stage}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Age Preferences */}
            {profile.age_enabled && (
              <div>
                <h4 className="text-base font-semibold text-brand-700 dark:text-brand-200 mb-4 flex items-center gap-2">
                  <Filter className="w-5 h-5" />
                  Age Preferences for Cofounder
                </h4>
                <div className="p-4 rounded-xl border border-brand-100 dark:border-brand-800/60 bg-white/70 dark:bg-gray-800/30">
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    {profile.age_min && profile.age_max
                      ? `${profile.age_min} - ${profile.age_max} years`
                      : profile.age_min
                      ? `${profile.age_min}+ years`
                      : profile.age_max
                      ? `Up to ${profile.age_max} years`
                      : 'No specific range'}
                  </p>
                  {profile.age_importance && (
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                      Importance: {profile.age_importance === 'non_negotiable' ? 'Must Have' : 'Nice to Have'}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Ideal Cofounder Description */}
            {profile.ideal_cofounder_description && (
              <div>
                <h4 className="text-base font-semibold text-brand-700 dark:text-brand-200 mb-4 flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  Ideal Cofounder Description
                </h4>
                <div className="p-4 sm:p-5 rounded-xl border border-brand-100 dark:border-brand-800/60 bg-brand-25 dark:bg-brand-900/10">
                  <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed break-words">
                    {profile.ideal_cofounder_description}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Spacer so last content isn't hidden behind sticky footer */}
          <div className="h-24" />
        </div>

        {/* Footer (sticky bottom-right actions) */}
        {profile.status === 'submitted' && (
          <div
            className="
              sticky bottom-0
              border-t border-brand-200 dark:border-brand-700/50
              bg-white/95 dark:bg-gray-900/90
              backdrop-blur
              p-4 sm:p-6
            "
          >
            <div className="flex flex-col sm:flex-row sm:justify-end gap-3">
              <button
                onClick={onReject}
                disabled={actionLoading}
                className="
                  inline-flex items-center justify-center gap-2
                  px-5 py-3
                  bg-red-600 dark:bg-red-500 text-white
                  rounded-lg
                  hover:bg-red-700 dark:hover:bg-red-600
                  transition-all
                  disabled:opacity-50 disabled:cursor-not-allowed
                  font-medium shadow-lg
                  w-full sm:w-auto
                "
              >
                <XCircle className="w-5 h-5" />
                Reject
              </button>

              <button
                onClick={onApprove}
                disabled={actionLoading}
                className="
                  inline-flex items-center justify-center gap-2
                  px-5 py-3
                  bg-green-600 dark:bg-green-500 text-white
                  rounded-lg
                  hover:bg-green-700 dark:hover:bg-green-600
                  transition-all
                  disabled:opacity-50 disabled:cursor-not-allowed
                  font-medium shadow-lg
                  w-full sm:w-auto
                "
              >
                {actionLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <CheckCircle className="w-5 h-5" />
                )}
                Approve
              </button>
            </div>
          </div>
        )}
      </MotionDiv>
    </MotionDiv>
  );

  return createPortal(modalContent, document.body);
}


