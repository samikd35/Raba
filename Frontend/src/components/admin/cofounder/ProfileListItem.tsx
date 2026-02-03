import { motion } from 'framer-motion';
import { Eye, MapPin, Briefcase, Calendar } from 'lucide-react';
import type { ProfileVersion } from '@/types/cofounder';
import UserAvatar from '@/components/ui/avatar/UserAvatar';
import { getStatusConfig } from './utils';

interface ProfileListItemProps {
  profile: ProfileVersion;
  onView: () => void;
}

export default function ProfileListItem({ profile, onView }: ProfileListItemProps) {
  const statusConfig = getStatusConfig(profile.status);
  const StatusIcon = statusConfig.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-all"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4 flex-1">
          <UserAvatar
            src={profile.profile_picture_url}
            name={profile.first_name}
            size="large"
          />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {profile.first_name} {profile.last_name}
              </h3>
              <span
                className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.bgColor} ${statusConfig.color}`}
              >
                <StatusIcon className="w-3 h-3" />
                {statusConfig.label}
              </span>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              {profile.professional_background}
            </p>

            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {profile.country}
              </span>
              <span className="flex items-center gap-1">
                <Briefcase className="w-4 h-4" />
                {profile.expected_commitment}
              </span>
              {profile.submitted_at && (
                <span className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  Submitted: {new Date(profile.submitted_at).toLocaleDateString()}
                </span>
              )}
            </div>

            <div className="mt-3 flex flex-wrap gap-1">
              {profile.industries_of_interest?.slice(0, 3).map((industry, index) => (
                <span
                  key={index}
                  className="px-2 py-0.5 bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300 rounded text-xs border border-brand-200 dark:border-brand-800"
                >
                  {industry}
                </span>
              ))}
              {profile.industries_of_interest &&
                profile.industries_of_interest.length > 3 && (
                  <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-xs">
                    +{profile.industries_of_interest.length - 3} more
                  </span>
                )}
            </div>

            {profile.status === 'rejected' && profile.review_reason && (
              <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-sm font-medium text-red-900 dark:text-red-200 mb-1">
                  Rejection Reason:
                </p>
                <p className="text-sm text-red-700 dark:text-red-300">
                  {profile.review_reason}
                </p>
              </div>
            )}
          </div>
        </div>

        <button
          onClick={onView}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 dark:bg-brand-400 text-white rounded-lg hover:bg-brand-600 dark:hover:bg-brand-500 transition-all whitespace-nowrap"
        >
          <Eye className="w-4 h-4" />
          Review
        </button>
      </div>
    </motion.div>
  );
}
