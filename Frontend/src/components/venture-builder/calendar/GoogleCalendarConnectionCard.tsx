'use client';

import { useState, useEffect } from 'react';
import { Calendar, CheckCircle, AlertCircle, XCircle, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';
import type { GoogleCalendarConnection, GoogleCalendarList } from '@/types/ventureBuilder';

export default function GoogleCalendarConnectionCard() {
  const [connection, setConnection] = useState<GoogleCalendarConnection | null>(null);
  const [calendars, setCalendars] = useState<GoogleCalendarList[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSelecting, setIsSelecting] = useState(false);
  const [showCalendarList, setShowCalendarList] = useState(false);

  useEffect(() => {
    loadConnection();
  }, []);

  const loadConnection = async () => {
    try {
      setIsLoading(true);
      const data = await ventureBuilderAPI.calendar.getStatus();

      // Map API response to component state
      setConnection({
        connected: data.connected,
        selected_calendar_id: data.calendar_id || undefined,
        calendar_name: data.calendar_name || undefined,
        timezone: data.time_zone || undefined,
      });

      // If connected but no calendar selected, load calendar list
      if (data.connected && !data.calendar_id) {
        await loadCalendars();
        setShowCalendarList(true);
      }
    } catch (error: any) {
      console.error('Failed to load calendar connection:', error);
      setConnection({
        connected: false,
        error: error.message,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadCalendars = async () => {
    try {
      const calendarList = await ventureBuilderAPI.calendar.listCalendars();
      setCalendars(calendarList);
    } catch (error: any) {
      console.error('Failed to load calendars:', error);
      toast.error('Failed to load your calendars');
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

  const handleSelectCalendar = async (calendarId: string) => {
    try {
      setIsSelecting(true);
      await ventureBuilderAPI.calendar.selectCalendar({
        calendar_id: calendarId,
      });

      // Reload connection status after selection
      await loadConnection();
      setShowCalendarList(false);
      toast.success('Calendar selected successfully!');
    } catch (error: any) {
      console.error('Failed to select calendar:', error);
      toast.error(error.message || 'Failed to select calendar');
    } finally {
      setIsSelecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect your Google Calendar?')) {
      return;
    }

    try {
      await ventureBuilderAPI.calendar.disconnect();
      setConnection({ connected: false });
      setCalendars([]);
      setShowCalendarList(false);
      toast.success('Calendar disconnected successfully');
    } catch (error: any) {
      console.error('Failed to disconnect:', error);
      toast.error(error.message || 'Failed to disconnect calendar');
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  // Not Connected State
  if (!connection?.connected) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
            <Calendar className="w-6 h-6 text-gray-600 dark:text-gray-400" />
          </div>

          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Google Calendar Not Connected
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Connect your Google Calendar to enable real-time session booking.
              Your calendar will be used to check availability and automatically
              create events when sessions are booked.
            </p>

            {connection?.error && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700 dark:text-red-300">
                    {connection.error}
                  </p>
                </div>
              </div>
            )}

            <button
              onClick={handleConnect}
              disabled={isConnecting}
              className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isConnecting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <Calendar className="w-4 h-4" />
                  Connect Google Calendar
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Connected but no calendar selected
  if (!connection.selected_calendar_id && showCalendarList) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-start gap-4 mb-6">
          <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
            <Calendar className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>

          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Select a Calendar
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Choose which calendar to use for session bookings
            </p>
          </div>
        </div>

        <div className="space-y-2">
          {calendars.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <p>No calendars found in your Google account.</p>
            </div>
          ) : (
            calendars.map((calendar) => (
              <button
                key={calendar.id}
                onClick={() => handleSelectCalendar(calendar.id)}
                disabled={isSelecting}
                className="w-full p-4 text-left border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
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
                    <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                      Timezone: {calendar.timezone}
                    </div>
                  </div>
                  <CheckCircle className="w-5 h-5 text-gray-400" />
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    );
  }

  // Fully Connected State
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-green-200 dark:border-green-800 p-6">
      <div className="flex items-start gap-4">
        <div className="p-3 bg-green-100 dark:bg-green-900/20 rounded-lg">
          <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
        </div>

        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Google Calendar Connected
          </h3>

          <div className="space-y-2 mb-4">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-600 dark:text-gray-400">Account:</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {connection.email}
              </span>
            </div>

            {connection.calendar_name && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-600 dark:text-gray-400">Calendar:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {connection.calendar_name}
                </span>
              </div>
            )}

            {connection.timezone && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-600 dark:text-gray-400">Timezone:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {connection.timezone}
                </span>
              </div>
            )}

            {connection.last_sync && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-600 dark:text-gray-400">Last synced:</span>
                <span className="text-gray-900 dark:text-white">
                  {new Date(connection.last_sync).toLocaleString()}
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setShowCalendarList(true);
                loadCalendars();
              }}
              className="text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 font-medium"
            >
              Change Calendar
            </button>

            <span className="text-gray-300 dark:text-gray-600">|</span>

            <button
              onClick={handleDisconnect}
              className="text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-medium"
            >
              Disconnect
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
