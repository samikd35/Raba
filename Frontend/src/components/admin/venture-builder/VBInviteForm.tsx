'use client';

import React, { useState } from 'react';
import { Mail, Send, Loader2, CheckCircle, Info } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';

export default function VBInviteForm() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [invitationSent, setInvitationSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email || !email.includes('@')) {
      toast.error('Please enter a valid email address');
      return;
    }

    setIsLoading(true);

    try {
      const data = await ventureBuilderAPI.invitations.sendInvitation({ email });
      toast.success('Invitation sent successfully!');
      setInvitationSent(true);
      setEmail('');

      // Reset success state after 3 seconds
      setTimeout(() => setInvitationSent(false), 3000);
    } catch (error: any) {
      console.error('Error sending invitation:', error);
      toast.error(error.message || 'Failed to send invitation');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-theme-xs overflow-hidden">
      <div className="px-4 sm:px-6 py-4 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 sm:w-12 sm:h-12 bg-brand-100 dark:bg-brand-900/30 rounded-xl flex items-center justify-center">
            <Mail className="w-5 h-5 sm:w-6 sm:h-6 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
              Invite Venture Builder
            </h2>
            <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
              Send an invitation email to a new Venture Builder
            </p>
          </div>
        </div>
      </div>

      <div className="p-4 sm:p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="vb@example.com"
                disabled={isLoading}
                className="w-full pl-10 pr-4 py-2.5 sm:py-3 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              The invitation link will be valid for 48 hours
            </p>
          </div>

          <button
            type="submit"
            disabled={isLoading || !email}
            className={`w-full flex items-center justify-center gap-2 px-6 py-2.5 sm:py-3 rounded-lg text-sm font-semibold transition-all ${
              isLoading || !email
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                : invitationSent
                ? 'bg-success-500 hover:bg-success-600 text-white'
                : 'bg-brand-500 hover:bg-brand-600 text-white shadow-theme-sm hover:shadow-theme-md'
            }`}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Sending Invitation...
              </>
            ) : invitationSent ? (
              <>
                <CheckCircle className="w-5 h-5" />
                Invitation Sent!
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                Send Invitation
              </>
            )}
          </button>
        </form>

        <div className="mt-6 p-3 sm:p-4 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-lg">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-brand-600 dark:text-brand-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs sm:text-sm text-brand-800 dark:text-brand-300">
              <strong>Note:</strong> The invitee will receive an email with a registration link. They must complete their profile within 48 hours before the invitation expires.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
