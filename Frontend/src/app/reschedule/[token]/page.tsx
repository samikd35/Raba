'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2, CheckCircle, XCircle, Calendar, AlertCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';
import AvailabilitySlotPicker from '@/components/venture-builder/booking/AvailabilitySlotPicker';
import type {
  ValidateRescheduleTokenResponse,
  AvailableSlot,
  RescheduleBookResponse,
} from '@/types/ventureBuilder';

export default function ReschedulePage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;

  const [status, setStatus] = useState<'loading' | 'valid' | 'invalid' | 'success' | 'error'>(
    'loading'
  );
  const [validationData, setValidationData] = useState<ValidateRescheduleTokenResponse | null>(
    null
  );
  const [selectedSlot, setSelectedSlot] = useState<AvailableSlot | null>(null);
  const [isRebooking, setIsRebooking] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    validateToken();
  }, [token]);

  const validateToken = async () => {
    try {
      setStatus('loading');
      const data = await ventureBuilderAPI.reschedule.validateToken(token);

      if (data.valid) {
        setValidationData(data);
        setStatus('valid');
      } else {
        setStatus('invalid');
        setMessage('This reschedule link is invalid or has expired.');
      }
    } catch (error: any) {
      console.error('Failed to validate token:', error);
      setStatus('invalid');
      setMessage(error.message || 'Failed to validate reschedule link.');
    }
  };

  const handleRebook = async () => {
    if (!selectedSlot) {
      toast.error('Please select a time slot');
      return;
    }

    try {
      setIsRebooking(true);

      const response: RescheduleBookResponse = await ventureBuilderAPI.reschedule.completeReschedule(
        token,
        {
          new_start: selectedSlot.start,
          new_end: selectedSlot.end,
        }
      );

      setStatus('success');
      setMessage(response.message);
      toast.success('Session rescheduled successfully!');

      // Redirect to sessions after 3 seconds
      setTimeout(() => {
        router.push('/dashboard/sessions');
      }, 3000);
    } catch (error: any) {
      console.error('Failed to complete reschedule:', error);
      setStatus('error');
      setMessage(error.message || 'Failed to reschedule session. Please try again.');
      toast.error(error.message || 'Failed to reschedule session');
    } finally {
      setIsRebooking(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {status === 'loading' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12">
            <div className="text-center">
              <Loader2 className="w-12 h-12 animate-spin text-brand-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Validating reschedule link...
              </h2>
              <p className="text-gray-600 dark:text-gray-400">Please wait a moment.</p>
            </div>
          </div>
        )}

        {status === 'invalid' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12">
            <div className="text-center">
              <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <XCircle className="w-10 h-10 text-red-600 dark:text-red-400" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Invalid Reschedule Link
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">{message}</p>
              <button
                onClick={() => router.push('/dashboard')}
                className="px-6 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
              >
                Go to Dashboard
              </button>
            </div>
          </div>
        )}

        {status === 'valid' && validationData && (
          <div className="space-y-6">
            {/* Session Info Card */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-yellow-100 dark:bg-yellow-900/20 rounded-lg">
                  <Calendar className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
                </div>
                <div className="flex-1">
                  <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                    Reschedule Your Session
                  </h1>
                  <p className="text-gray-600 dark:text-gray-400 mb-4">
                    Your session with <span className="font-medium">{validationData.vb_name}</span>{' '}
                    needs to be rescheduled.
                  </p>

                  {validationData.original_time && (
                    <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Original Time:
                      </p>
                      <p className="text-sm text-gray-900 dark:text-white">
                        {new Date(validationData.original_time).toLocaleString('en-US', {
                          weekday: 'long',
                          month: 'long',
                          day: 'numeric',
                          hour: 'numeric',
                          minute: '2-digit',
                          hour12: true,
                        })}
                      </p>
                    </div>
                  )}

                  {validationData.apology_message && (
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium text-blue-900 dark:text-blue-300 mb-1">
                            Message from {validationData.vb_name}
                          </p>
                          <p className="text-sm text-blue-800 dark:text-blue-400">
                            {validationData.apology_message}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Slot Picker */}
            {validationData.session && (
              <AvailabilitySlotPicker
                vbId={validationData.session.venture_builder_id}
                vbName={validationData.vb_name || 'Venture Builder'}
                onSlotSelect={setSelectedSlot}
                selectedSlot={selectedSlot}
              />
            )}

            {/* Rebook Button */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    Ready to confirm?
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {selectedSlot
                      ? 'Click below to confirm your new time slot'
                      : 'Select a time slot above to continue'}
                  </p>
                </div>
                <button
                  onClick={handleRebook}
                  disabled={!selectedSlot || isRebooking}
                  className="px-6 py-3 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors inline-flex items-center gap-2 font-medium"
                >
                  {isRebooking ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Rebooking...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      Confirm Reschedule
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {status === 'success' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12">
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-10 h-10 text-green-600 dark:text-green-400" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Session Rescheduled Successfully!
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">{message}</p>
              <p className="text-sm text-gray-500 dark:text-gray-500">
                Redirecting to your dashboard...
              </p>
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12">
            <div className="text-center">
              <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <XCircle className="w-10 h-10 text-red-600 dark:text-red-400" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Reschedule Failed
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">{message}</p>
              <button
                onClick={() => setStatus('valid')}
                className="px-6 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
