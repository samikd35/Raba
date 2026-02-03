'use client';

import { useState } from 'react';
import { Calendar, CheckCircle, Globe, Loader2, XCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';

interface CalendarStatus {
  connected: boolean;
  calendar_id: string | null;
  calendar_name: string | null;
  time_zone: string | null;
  is_valid: boolean | null;
}

interface CalendarSidebarProps {
  status: CalendarStatus;
  onDisconnect?: () => void;
}

export default function CalendarSidebar({ status, onDisconnect }: CalendarSidebarProps) {
  const [isDisconnecting, setIsDisconnecting] = useState(false);

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect your Google Calendar?')) {
      return;
    }

    try {
      setIsDisconnecting(true);
      await ventureBuilderAPI.calendar.disconnect();
      toast.success('Calendar disconnected successfully');
      onDisconnect?.();
    } catch (error: any) {
      console.error('Failed to disconnect:', error);
      toast.error(error.message || 'Failed to disconnect calendar');
    } finally {
      setIsDisconnecting(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
          <Calendar className="w-5 h-5 text-green-600 dark:text-green-400" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white">
            Calendar Connected
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Google Calendar
          </p>
        </div>
      </div>

      {/* Status indicator */}
      <div className="flex items-center gap-2 mb-4 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
        <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
        <span className="text-sm font-medium text-green-700 dark:text-green-300">
          Active & Syncing
        </span>
      </div>

      {/* Calendar details */}
      <div className="space-y-4">
        {status.calendar_name && (
          <div>
            <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Calendar
            </label>
            <p className="text-sm font-medium text-gray-900 dark:text-white mt-1">
              {status.calendar_name}
            </p>
          </div>
        )}

        {status.time_zone && (
          <div>
            <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Timezone
            </label>
            <div className="flex items-center gap-2 mt-1">
              <Globe className="w-4 h-4 text-gray-400" />
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {status.time_zone}
              </p>
            </div>
          </div>
        )}

        {status.is_valid === false && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
            <div className="flex items-start gap-2">
              <XCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-700 dark:text-red-300">
                  Connection Issue
                </p>
                <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                  Please reconnect your calendar
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Disconnect button */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={handleDisconnect}
          disabled={isDisconnecting}
          className="w-full text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-medium disabled:opacity-50"
        >
          {isDisconnecting ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Disconnecting...
            </span>
          ) : (
            'Disconnect Calendar'
          )}
        </button>
      </div>
    </div>
  );
}
