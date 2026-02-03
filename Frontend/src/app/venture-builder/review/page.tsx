'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  ArrowLeft,
  CheckCircle,
  Calendar,
  Globe,
  PartyPopper,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import StepIndicator from '@/components/venture-builder/calendar/StepIndicator';
import AvailabilityVisualPreview from '@/components/venture-builder/calendar/AvailabilityVisualPreview';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';

interface CalendarStatus {
  connected: boolean;
  calendar_id: string | null;
  calendar_name: string | null;
  time_zone: string | null;
  is_valid: boolean | null;
}

export default function VBReviewPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [isFinishing, setIsFinishing] = useState(false);
  const [calendarStatus, setCalendarStatus] = useState<CalendarStatus | null>(null);

  useEffect(() => {
    checkSetup();
  }, []);

  const checkSetup = async () => {
    try {
      setIsLoading(true);
      const status = await ventureBuilderAPI.calendar.getStatus();

      if (!status.connected) {
        // Not connected - redirect to calendar connection page
        router.push('/venture-builder/calendar');
        return;
      }

      setCalendarStatus(status);
    } catch (error: any) {
      console.error('Failed to check calendar status:', error);
      toast.error('Failed to load setup status');
      router.push('/venture-builder/calendar');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBack = () => {
    router.push('/venture-builder/settings');
  };

  const handleFinish = async () => {
    try {
      setIsFinishing(true);
      toast.success('Calendar setup complete!');
      // Redirect to VB Portal
      router.push('/workspace/vb-portal');
    } catch (error: any) {
      console.error('Failed to finish setup:', error);
      toast.error('Something went wrong');
    } finally {
      setIsFinishing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading review...</p>
        </div>
      </div>
    );
  }

  if (!calendarStatus) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        {/* Step Indicator */}
        <div className="mb-8">
          <StepIndicator currentStep={3} />
        </div>

        {/* Page Header */}
        <div className="mb-8 text-center">
          <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <PartyPopper className="w-8 h-8 text-green-600 dark:text-green-400" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Review Your Setup
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            You're almost done! Review your calendar settings below.
          </p>
        </div>

        {/* Summary Cards */}
        <div className="space-y-6">
          {/* Calendar Connection Card */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                <Calendar className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  Google Calendar
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Connection status
                </p>
              </div>
              <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                <CheckCircle className="w-5 h-5" />
                <span className="text-sm font-medium">Connected</span>
              </div>
            </div>

            <div className="space-y-3 pl-12">
              {calendarStatus.calendar_name && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500 dark:text-gray-400 w-20">Calendar:</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {calendarStatus.calendar_name}
                  </span>
                </div>
              )}

              {calendarStatus.time_zone && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500 dark:text-gray-400 w-20">Timezone:</span>
                  <div className="flex items-center gap-2">
                    <Globe className="w-4 h-4 text-gray-400" />
                    <span className="font-medium text-gray-900 dark:text-white">
                      {calendarStatus.time_zone}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Availability Visual Preview */}
          <AvailabilityVisualPreview />
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex items-center justify-between">
          <button
            onClick={handleBack}
            className="inline-flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Settings
          </button>

          <button
            onClick={handleFinish}
            disabled={isFinishing}
            className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium shadow-sm"
          >
            {isFinishing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Finishing...
              </>
            ) : (
              <>
                <CheckCircle className="w-5 h-5" />
                Finish Setup
              </>
            )}
          </button>
        </div>

        {/* Help note */}
        <p className="text-center text-xs text-gray-500 dark:text-gray-400 mt-6">
          You can update your availability anytime from your VB Portal settings.
        </p>
      </div>
    </div>
  );
}
