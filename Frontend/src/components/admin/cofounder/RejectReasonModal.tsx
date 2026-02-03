import { motion } from 'framer-motion';
import { X, Loader2, Send } from 'lucide-react';
import type { ProfileVersion } from '@/types/cofounder';
import UserAvatar from '@/components/ui/avatar/UserAvatar';

interface RejectReasonModalProps {
  profile: ProfileVersion;
  reason: string;
  onReasonChange: (reason: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
  actionLoading: boolean;
}

export default function RejectReasonModal({
  profile,
  reason,
  onReasonChange,
  onConfirm,
  onCancel,
  actionLoading,
}: RejectReasonModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={onCancel}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full"
      >
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Reject Profile
          </h2>
          <button
            onClick={onCancel}
            disabled={actionLoading}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-all disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <UserAvatar
              src={profile.profile_picture_url}
              name={profile.first_name}
              size="medium"
            />
            <div>
              <p className="font-medium text-gray-900 dark:text-white">
                {profile.first_name} {profile.last_name}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {profile.professional_background}
              </p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Rejection Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => onReasonChange(e.target.value)}
              disabled={actionLoading}
              rows={4}
              placeholder="Please provide a clear reason for rejection. This will be sent to the user."
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white bg-white dark:bg-gray-700 focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent resize-none disabled:opacity-50"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Be constructive and specific to help the user improve their profile.
            </p>
          </div>
        </div>

        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={actionLoading}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-all disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={actionLoading || !reason.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 dark:bg-red-500 text-white rounded-lg hover:bg-red-700 dark:hover:bg-red-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {actionLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Rejecting...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Reject Profile
              </>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
