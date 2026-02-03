'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, UserPlus, FileText, Clock, CheckCircle, XCircle } from 'lucide-react';
import Link from 'next/link';

type BannerType = 'no-profile' | 'draft' | 'pending-review' | 'rejected' | 'no-matches';

interface EmptyStateBannerProps {
  type: BannerType;
  message?: string;
  actionText?: string;
  actionLink?: string;
}

export default function EmptyStateBanner({
  type,
  message,
  actionText,
  actionLink,
}: EmptyStateBannerProps) {
  const getBannerConfig = () => {
    switch (type) {
      case 'no-profile':
        return {
          icon: <UserPlus className="w-12 h-12" />,
          title: 'Create Your Cofounder Profile',
          description:
            message ||
            'Start your journey to finding the perfect cofounder by creating your profile. Tell us about your background, skills, and what you\'re looking for.',
          bgColor: 'bg-blue-50 dark:bg-blue-900/20',
          borderColor: 'border-blue-200 dark:border-blue-800',
          iconColor: 'text-blue-600 dark:text-blue-400',
          textColor: 'text-blue-900 dark:text-blue-100',
          defaultAction: 'Create Profile',
          defaultLink: '/workspace/cofounder-matching',
        };
      case 'draft':
        return {
          icon: <FileText className="w-12 h-12" />,
          title: 'Complete Your Profile',
          description:
            message ||
            'You have a draft profile saved. Complete and submit it for review to start browsing potential cofounders.',
          bgColor: 'bg-yellow-50 dark:bg-yellow-900/20',
          borderColor: 'border-yellow-200 dark:border-yellow-800',
          iconColor: 'text-yellow-600 dark:text-yellow-400',
          textColor: 'text-yellow-900 dark:text-yellow-100',
          defaultAction: 'Continue Editing',
          defaultLink: '/workspace/cofounder-matching',
        };
      case 'pending-review':
        return {
          icon: <Clock className="w-12 h-12" />,
          title: 'Profile Under Review',
          description:
            message ||
            'Your profile is currently being reviewed by our team. You\'ll be notified once it\'s approved and you can start browsing the directory.',
          bgColor: 'bg-purple-50 dark:bg-purple-900/20',
          borderColor: 'border-purple-200 dark:border-purple-800',
          iconColor: 'text-purple-600 dark:text-purple-400',
          textColor: 'text-purple-900 dark:text-purple-100',
          defaultAction: 'View Dashboard',
          defaultLink: '/workspace/cofounder-matching/dashboard',
        };
      case 'rejected':
        return {
          icon: <XCircle className="w-12 h-12" />,
          title: 'Profile Needs Updates',
          description:
            message ||
            'Your profile was not approved. Please review the feedback and make necessary updates before resubmitting.',
          bgColor: 'bg-red-50 dark:bg-red-900/20',
          borderColor: 'border-red-200 dark:border-red-800',
          iconColor: 'text-red-600 dark:text-red-400',
          textColor: 'text-red-900 dark:text-red-100',
          defaultAction: 'View Feedback',
          defaultLink: '/workspace/cofounder-matching/dashboard',
        };
      case 'no-matches':
        return {
          icon: <AlertCircle className="w-12 h-12" />,
          title: 'No Matches Found',
          description:
            message ||
            'We couldn\'t find any cofounders matching your current filters. Try adjusting your search criteria or check back later.',
          bgColor: 'bg-gray-50 dark:bg-gray-800',
          borderColor: 'border-gray-200 dark:border-gray-700',
          iconColor: 'text-gray-600 dark:text-gray-400',
          textColor: 'text-gray-900 dark:text-gray-100',
          defaultAction: 'Clear Filters',
          defaultLink: '',
        };
      default:
        return {
          icon: <AlertCircle className="w-12 h-12" />,
          title: 'No Data',
          description: message || 'No information available at this time.',
          bgColor: 'bg-gray-50 dark:bg-gray-800',
          borderColor: 'border-gray-200 dark:border-gray-700',
          iconColor: 'text-gray-600 dark:text-gray-400',
          textColor: 'text-gray-900 dark:text-gray-100',
          defaultAction: 'Go Back',
          defaultLink: '/workspace',
        };
    }
  };

  const config = getBannerConfig();
  const finalActionText = actionText || config.defaultAction;
  const finalActionLink = actionLink || config.defaultLink;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`${config.bgColor} ${config.borderColor} border rounded-lg p-8 text-center`}
    >
      <div className={`${config.iconColor} flex justify-center mb-4`}>{config.icon}</div>
      <h3 className={`text-xl font-bold ${config.textColor} mb-2`}>{config.title}</h3>
      <p className={`${config.textColor} opacity-80 mb-6 max-w-2xl mx-auto`}>
        {config.description}
      </p>
      {finalActionLink && (
        <Link
          href={finalActionLink}
          className={`inline-block px-6 py-3 ${
            type === 'no-profile' || type === 'draft'
              ? 'bg-brand-500 hover:bg-brand-600 dark:bg-brand-400 dark:hover:bg-brand-500'
              : 'bg-gray-700 hover:bg-gray-800 dark:bg-gray-600 dark:hover:bg-gray-500'
          } text-white rounded-lg font-medium transition-colors`}
        >
          {finalActionText}
        </Link>
      )}
    </motion.div>
  );
}
