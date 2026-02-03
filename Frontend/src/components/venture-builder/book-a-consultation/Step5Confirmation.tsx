'use client';

import React, { useState } from 'react';
import { Check, Calendar, CreditCard, FileText, User, Clock, Loader2, Users } from 'lucide-react';
import { createBooking } from '@/lib/api/venture-builder';
import { VBProfile } from '@/types/ventureBuilder';
import { BookingFormData } from './BookingWizard';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import { useRouter } from 'next/navigation';

interface Step5ConfirmationProps {
  formData: BookingFormData;
  ventureBuilder: VBProfile;
  onSuccess: () => void;
}

export default function Step5Confirmation({ formData, ventureBuilder, onSuccess }: Step5ConfirmationProps) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [bookingComplete, setBookingComplete] = useState(false);
  const vbName = ventureBuilder.full_name || ventureBuilder.name || 'Venture Builder';

  const handleConfirmBooking = async () => {
    try {
      setIsSubmitting(true);

      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required. Please sign in again.');
      }

      const bookingPayload = {
        venture_builder_id: ventureBuilder.id,
        project_id: formData.projectId,
        tenant_id: formData.tenantId,
        session_datetime: formData.sessionDatetime,
        session_duration_minutes: formData.sessionDuration,
        agenda: formData.agenda,
        accepted_terms_version: formData.termsVersion || 'v1.0',
      };

      await createBooking(bookingPayload, token);

      setBookingComplete(true);
      toast.success('Session booked successfully!');

      setTimeout(() => {
        onSuccess();
      }, 2000);
    } catch (error: any) {
      console.error('Error creating booking:', error);
      toast.error(error.message || 'Failed to book session');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (bookingComplete) {
    return (
      <div className="space-y-6 py-8">
        <div className="flex flex-col items-center justify-center text-center">
          <div className="w-20 h-20 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center mb-4">
            <Check className="w-10 h-10 text-green-600 dark:text-green-400" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Booking Confirmed!
          </h3>
          <p className="text-gray-600 dark:text-gray-400 max-w-md mb-6">
            Your session with {vbName} has been successfully booked.
          </p>
        </div>

        {/* Email Reminder Info */}
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
          <p className="text-sm text-blue-800 dark:text-blue-300">
            <strong>📧 Email Confirmation Sent</strong>
          </p>
          <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
            You'll receive a confirmation email with:
          </p>
          <ul className="text-sm text-blue-700 dark:text-blue-400 mt-2 ml-4 space-y-1">
            <li>• Calendar invitation (.ics file)</li>
            <li>• Google Meet link for the session</li>
            <li>• Session details and agenda</li>
            <li>• Reminder 24 hours before the session</li>
          </ul>
        </div>

        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg">
          <p className="text-sm text-yellow-800 dark:text-yellow-300">
            <strong>💡 Tip:</strong> Review the agenda you submitted before the session to make the most of your time with the Venture Builder.
          </p>
        </div>

        {/* Action CTAs */}
        <div className="flex flex-col sm:flex-row gap-3 pt-4">
          <button
            onClick={() => router.push('/vb-sessions')}
            className="flex-1 flex items-center justify-center gap-2 px-6 py-4 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-semibold transition-all shadow-md hover:shadow-lg"
          >
            <Calendar className="w-5 h-5" />
            View My Coaching Sessions
          </button>
          <button
            onClick={() => router.push('/venture-builders')}
            className="flex-1 flex items-center justify-center gap-2 px-6 py-4 bg-white dark:bg-gray-800 border-2 border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-semibold hover:bg-gray-50 dark:hover:bg-gray-700 transition-all"
          >
            <Users className="w-5 h-5" />
            Back to Venture Builders
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Review & Confirm
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Please review your booking details before confirming.
        </p>
      </div>

      {/* Booking Summary */}
      <div className="space-y-4">
        <div className="p-5 bg-gradient-to-br from-brand-50 to-white dark:from-gray-900 dark:to-gray-800 border border-brand-100 dark:border-gray-700 rounded-xl">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full overflow-hidden border-2 border-brand-200 dark:border-brand-600 flex-shrink-0">
              <img
                src={ventureBuilder.profile_picture_url}
                alt={vbName}
                className="w-full h-full object-cover"
              />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <User className="w-4 h-4 text-brand-500 dark:text-brand-400" />
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Venture Builder</p>
              </div>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {vbName}
              </p>
              {ventureBuilder.expertise_areas && ventureBuilder.expertise_areas.length > 0 && (
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {ventureBuilder.expertise_areas[0].name}
                </p>
              )}
            </div>
            <div className="hidden sm:flex items-center gap-2 px-3 py-2 bg-white/70 dark:bg-gray-900/60 border border-brand-100 dark:border-gray-700 rounded-lg text-xs text-gray-600 dark:text-gray-300">
              <Clock className="w-3.5 h-3.5" />
              60 min session
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Date & Time */}
          <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Calendar className="w-4 h-4 text-brand-500 dark:text-brand-400" />
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Session Date & Time</p>
            </div>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {new Date(formData.sessionDatetime).toLocaleString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <Clock className="w-4 h-4 text-gray-500 dark:text-gray-400" />
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {new Date(formData.sessionDatetime).toLocaleString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                  timeZoneName: 'short',
                })} • 60 minutes
              </p>
            </div>
          </div>

          {/* Project */}
          <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-brand-500 dark:text-brand-400" />
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Project</p>
            </div>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {formData.projectName}
            </p>
          </div>

          {/* Credits */}
          <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <CreditCard className="w-4 h-4 text-brand-500 dark:text-brand-400" />
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Payment</p>
            </div>
            <div className="flex items-baseline gap-2">
              <p className="text-2xl font-bold text-brand-600 dark:text-brand-400">
                {formData.creditDetails?.requiredCredits || 0}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">credits</p>
            </div>
            {formData.creditDetails && (
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                Remaining: {formData.creditDetails.currentBalance - formData.creditDetails.requiredCredits} credits
              </p>
            )}
          </div>

          {/* Agenda Preview */}
          <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-brand-500 dark:text-brand-400" />
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Session Agenda</p>
            </div>
            <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg max-h-40 overflow-y-auto">
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {formData.agenda}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Terms Reminder */}
      <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg">
        <p className="text-sm text-yellow-800 dark:text-yellow-300">
          <strong>Important:</strong> By confirming this booking, you agree to the terms and conditions.
          Cancellations must be made at least 24 hours in advance for a full refund.
        </p>
      </div>

      {/* Confirm Button */}
      <button
        onClick={handleConfirmBooking}
        disabled={isSubmitting}
        className={`w-full py-4 px-6 rounded-lg text-base font-semibold transition-all duration-200 flex items-center justify-center gap-2 ${
          isSubmitting
            ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 cursor-not-allowed'
            : 'bg-brand-500 hover:bg-brand-600 text-white shadow-md hover:shadow-lg'
        }`}
      >
        {isSubmitting ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Confirming Booking...
          </>
        ) : (
          <>
            <Check className="w-5 h-5" />
            Confirm Booking
          </>
        )}
      </button>

      <p className="text-xs text-center text-gray-500 dark:text-gray-400">
        You'll receive a confirmation email with the Google Meet link after booking
      </p>
    </div>
  );
}
