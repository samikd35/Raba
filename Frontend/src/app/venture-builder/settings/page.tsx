'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, ArrowRight } from 'lucide-react';
import { toast } from 'react-hot-toast';
import StepIndicator from '@/components/venture-builder/calendar/StepIndicator';
import CalendarSidebar from '@/components/venture-builder/calendar/CalendarSidebar';
import AvailabilitySection from '@/components/venture-builder/calendar/AvailabilitySection';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';

interface CalendarStatus {
  connected: boolean;
  calendar_id: string | null;
  calendar_name: string | null;
  time_zone: string | null;
  is_valid: boolean | null;
}

export default function VBSettingsPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [calendarStatus, setCalendarStatus] = useState<CalendarStatus | null>(null);

  useEffect(() => {
    checkConnectionStatus();
  }, []);

  const checkConnectionStatus = async () => {
    try {
      setIsLoading(true);
      const status = await ventureBuilderAPI.calendar.getStatus();

      if (!status.connected || !status.calendar_id) {
        // Not connected or no calendar selected - redirect to calendar connection page
        router.push('/venture-builder/calendar');
        return;
      }

      setCalendarStatus(status);
    } catch (error: any) {
      console.error('Failed to check calendar status:', error);
      toast.error('Failed to load calendar status');
      // Redirect to connection page on error
      router.push('/venture-builder/calendar');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = () => {
    // Redirect to calendar connection page after disconnect
    router.push('/venture-builder/calendar');
  };

  const handleNext = () => {
    router.push('/venture-builder/review');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading settings...</p>
        </div>
      </div>
    );
  }

  if (!calendarStatus) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Step Indicator */}
        <div className="mb-8">
          <StepIndicator currentStep={2} />
        </div>

        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Set Your Availability
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Configure your weekly schedule for founder sessions.
          </p>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar - Calendar Details */}
          <div className="lg:col-span-1">
            <CalendarSidebar
              status={calendarStatus}
              onDisconnect={handleDisconnect}
            />
          </div>

          {/* Main Content - Availability Editor */}
          <div className="lg:col-span-3">
            <AvailabilitySection />

            {/* Next button */}
            <div className="mt-6 flex justify-end">
              <button
                onClick={handleNext}
                className="inline-flex items-center gap-2 px-6 py-3 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors font-medium"
              >
                Next: Review
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
