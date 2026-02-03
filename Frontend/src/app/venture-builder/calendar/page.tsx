'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Calendar, Loader2, CheckCircle, Clock, Shield } from 'lucide-react';
import { toast } from 'react-hot-toast';
import StepIndicator from '@/components/venture-builder/calendar/StepIndicator';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';
import type { GoogleCalendarList } from '@/types/ventureBuilder';

export default function VBCalendarPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [needsCalendarSelection, setNeedsCalendarSelection] = useState(false);
  const [calendars, setCalendars] = useState<GoogleCalendarList[]>([]);
  const [isLoadingCalendars, setIsLoadingCalendars] = useState(false);
  const [isSelecting, setIsSelecting] = useState(false);

  useEffect(() => {
    checkConnectionStatus();
  }, []);

  const checkConnectionStatus = async () => {
    try {
      setIsLoading(true);
      const status = await ventureBuilderAPI.calendar.getStatus();

      if (status.connected && status.calendar_id) {
        setIsConnected(true);
        // Auto-redirect to settings if fully connected with calendar selected
        router.push('/venture-builder/settings');
      } else if (status.connected && !status.calendar_id) {
        // Connected but no calendar selected - show calendar selection
        setIsConnected(true);
        setNeedsCalendarSelection(true);
        await loadCalendars();
      }
    } catch (error: any) {
      console.error('Failed to check calendar status:', error);
      // Not connected or error - stay on this page
    } finally {
      setIsLoading(false);
    }
  };

  const loadCalendars = async () => {
    try {
      setIsLoadingCalendars(true);
      const calendarList = await ventureBuilderAPI.calendar.listCalendars();
      setCalendars(calendarList);
    } catch (error: any) {
      console.error('Failed to load calendars:', error);
      toast.error('Failed to load your calendars');
    } finally {
      setIsLoadingCalendars(false);
    }
  };

  const handleSelectCalendar = async (calendarId: string, timezone?: string) => {
    try {
      setIsSelecting(true);
      await ventureBuilderAPI.calendar.selectCalendar({
        calendar_id: calendarId,
        time_zone: timezone,
      });
      toast.success('Calendar selected successfully!');
      router.push('/venture-builder/settings');
    } catch (error: any) {
      console.error('Failed to select calendar:', error);
      toast.error(error.message || 'Failed to select calendar');
    } finally {
      setIsSelecting(false);
    }
  };

  const handleConnect = async () => {
    try {
      setIsConnecting(true);
      const response = await ventureBuilderAPI.calendar.getAuthUrl();
      // Redirect to Google OAuth
      window.location.href = response.auth_url;
    } catch (error: any) {
      console.error('Failed to initiate connection:', error);
      toast.error(error.message || 'Failed to connect to Google Calendar');
      setIsConnecting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Checking calendar status...</p>
        </div>
      </div>
    );
  }

  // If connected but needs calendar selection, show calendar list
  if (isConnected && needsCalendarSelection) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          {/* Step Indicator */}
          <div className="mb-12">
            <StepIndicator currentStep={1} />
          </div>

          {/* Calendar Selection */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8">
            {/* Icon */}
            <div className="w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-10 h-10 text-green-600 dark:text-green-400" />
            </div>

            {/* Title */}
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-3 text-center">
              Google Calendar Connected
            </h1>

            {/* Description */}
            <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md mx-auto text-center">
              Select which calendar you want to use for session bookings.
            </p>

            {/* Calendar List */}
            {isLoadingCalendars ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : calendars.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <p>No calendars found in your Google account.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {calendars.map((calendar) => (
                  <button
                    key={calendar.id}
                    onClick={() => handleSelectCalendar(calendar.id, calendar.timezone)}
                    disabled={isSelecting}
                    className="w-full p-4 text-left border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-brand-500 dark:hover:border-brand-500 transition-colors disabled:opacity-50"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-gray-900 dark:text-white">
                          {calendar.summary}
                          {calendar.primary && (
                            <span className="ml-2 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
                              Primary
                            </span>
                          )}
                        </div>
                        {calendar.description && (
                          <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            {calendar.description}
                          </div>
                        )}
                        {calendar.timezone && (
                          <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                            Timezone: {calendar.timezone}
                          </div>
                        )}
                      </div>
                      <CheckCircle className="w-5 h-5 text-gray-400" />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // If connected with calendar selected, show redirecting message
  if (isConnected && !needsCalendarSelection) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Calendar connected! Redirecting...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        {/* Step Indicator */}
        <div className="mb-12">
          <StepIndicator currentStep={1} />
        </div>

        {/* Main Content */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8 text-center">
          {/* Icon */}
          <div className="w-20 h-20 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
            <Calendar className="w-10 h-10 text-brand-600 dark:text-brand-400" />
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
            Connect Your Google Calendar
          </h1>

          {/* Description */}
          <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md mx-auto">
            Link your Google Calendar to enable real-time session booking with founders.
            We'll sync your availability automatically.
          </p>

          {/* Connect Button */}
          <button
            onClick={handleConnect}
            disabled={isConnecting}
            className="inline-flex items-center gap-3 px-8 py-4 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-lg font-medium shadow-sm"
          >
            {isConnecting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Connecting...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                Connect Google Calendar
              </>
            )}
          </button>

          {/* Benefits */}
          <div className="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-6 text-left">
            <div className="flex items-start gap-3 p-4 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
              <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white text-sm">
                  Real-time Sync
                </h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Your availability updates instantly
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-4 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white text-sm">
                  Auto Event Creation
                </h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Sessions added to your calendar
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-4 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
              <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                <Shield className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white text-sm">
                  Conflict Detection
                </h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Prevent double bookings
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Privacy note */}
        <p className="text-center text-xs text-gray-500 dark:text-gray-400 mt-6">
          We only access your calendar to check availability and create session events.
          You can disconnect at any time.
        </p>
      </div>
    </div>
  );
}
