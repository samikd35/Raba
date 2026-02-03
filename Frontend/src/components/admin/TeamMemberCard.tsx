"use client";

import React, { useState } from 'react';
import { TeamMember } from '@/types/team';
import { RotateCcw, Trash2, UserX } from 'lucide-react';
import { toast } from "react-hot-toast";

interface TeamMemberCardProps {
  member: TeamMember;
  onSuspend?: (memberId: string) => Promise<void>;
  onRemove?: (memberId: string) => Promise<void>;
  isTeamLeader?: boolean;
}

/**
 * TeamMemberCard Component
 * 
 * Displays a team member with their details and management actions.
 * Styled consistently with organization admin pages.
 * 
 * Features:
 * - Avatar with initials
 * - Name, email, role display
 * - Credits used tracking
 * - Status badge (active/frozen/suspended)
 * - Suspend and remove actions (for non-leaders)
 * - Confirmation dialogs for destructive actions
 */
export default function TeamMemberCard({ 
  member, 
  onSuspend, 
  onRemove,
  isTeamLeader = false 
}: TeamMemberCardProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState<'suspend' | 'remove' | null>(null);

  // Generate initials from name
  const getInitials = (name: string): string => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  // Format number with locale
  const formatNumber = (num: number): string => {
    return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
  };

  // Handle suspend action
  const handleSuspend = async () => {
    if (!onSuspend) return;
    
    setIsProcessing(true);
    try {
      await onSuspend(member.id);
      toast.success(`${member.name} has been suspended`);
      setShowConfirmDialog(null);
    } catch (error: any) {
      console.error('Failed to suspend member:', error);
      toast.error(error?.message || 'Failed to suspend member');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle remove action
  const handleRemove = async () => {
    if (!onRemove) return;
    
    setIsProcessing(true);
    try {
      await onRemove(member.id);
      toast.success(`${member.name} has been removed from the team`);
      setShowConfirmDialog(null);
    } catch (error: any) {
      console.error('Failed to remove member:', error);
      toast.error(error?.message || 'Failed to remove member');
    } finally {
      setIsProcessing(false);
    }
  };

  // Get status badge color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'frozen':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'suspended':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  return (
    <>
      <div className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
        {/* Left side: Avatar and info */}
        <div className="flex items-center space-x-3 flex-1 min-w-0">
          {/* Avatar */}
          <div className="w-10 h-10 rounded-full bg-brand-500 flex items-center justify-center flex-shrink-0">
            <span className="text-white text-sm font-medium">
              {getInitials(member.name)}
            </span>
          </div>
          
          {/* Member info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2">
              <p className="font-medium text-gray-900 dark:text-white truncate">
                {member.name}
              </p>
              {member.role === 'team_leader' && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 flex-shrink-0">
                  Leader
                </span>
              )}
              {member.role === 'admin' && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 flex-shrink-0">
                  Admin
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
              {member.email}
            </p>
          </div>
        </div>

        {/* Right side: Credits and actions */}
        <div className="flex items-center space-x-4 ml-4">
          {/* Credits used */}
          <div className="text-right">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {formatNumber(member.credits_used)} credits
            </p>
            <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(member.status)}`}>
              {member.status}
            </span>
          </div>

          {/* Action buttons - only show for non-leaders */}
          {!isTeamLeader && member.role !== 'team_leader' && (
            <div className="flex items-center space-x-2">
              {member.status === 'active' && onSuspend && (
                <button
                  onClick={() => setShowConfirmDialog('suspend')}
                  disabled={isProcessing}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                  title="Suspend member"
                  aria-label="Suspend member"
                >
                  <UserX className="w-4 h-4 text-orange-600" />
                </button>
              )}
              {onRemove && (
                <button
                  onClick={() => setShowConfirmDialog('remove')}
                  disabled={isProcessing}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                  title="Remove member"
                  aria-label="Remove member"
                >
                  <Trash2 className="w-4 h-4 text-red-600" />
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              {showConfirmDialog === 'suspend' ? 'Suspend Member' : 'Remove Member'}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {showConfirmDialog === 'suspend' 
                ? `Are you sure you want to suspend ${member.name}? They will not be able to use their credits until reactivated.`
                : `Are you sure you want to remove ${member.name} from the team? This action cannot be undone.`
              }
            </p>
            <div className="flex space-x-3 justify-end">
              <button
                onClick={() => setShowConfirmDialog(null)}
                disabled={isProcessing}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={showConfirmDialog === 'suspend' ? handleSuspend : handleRemove}
                disabled={isProcessing}
                className={`px-4 py-2 rounded-lg text-white disabled:opacity-50 ${
                  showConfirmDialog === 'suspend'
                    ? 'bg-orange-600 hover:bg-orange-700'
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {isProcessing ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Processing...</span>
                  </div>
                ) : (
                  showConfirmDialog === 'suspend' ? 'Suspend' : 'Remove'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
