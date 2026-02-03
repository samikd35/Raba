'use client';

import { useState, useEffect } from 'react';
import { Clock, Loader2, AlertCircle } from 'lucide-react';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';
import type { DayOfWeek } from '@/types/ventureBuilder';

interface AvailabilityWindow {
  day_of_week: DayOfWeek | number;
  start_time: string;
  end_time: string;
}

interface AvailabilityData {
  windows: AvailabilityWindow[];
  timezone: string;
}

const DAY_NAMES: Record<DayOfWeek, string> = {
  sunday: 'Sunday',
  monday: 'Monday',
  tuesday: 'Tuesday',
  wednesday: 'Wednesday',
  thursday: 'Thursday',
  friday: 'Friday',
  saturday: 'Saturday',
};

const DAY_ORDER: DayOfWeek[] = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
];

// Helper to convert day number to name
const getDayName = (dayNumber: number): DayOfWeek => {
  const dayNames: DayOfWeek[] = [
    'sunday',
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday',
  ];
  return dayNames[dayNumber];
};

// Format time for display (e.g., "09:00" -> "9:00 AM")
const formatTime = (time: string): string => {
  const [hours, minutes] = time.split(':').map(Number);
  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;
  return `${displayHours}:${minutes.toString().padStart(2, '0')} ${period}`;
};

export default function AvailabilitySummary() {
  const [availability, setAvailability] = useState<AvailabilityData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAvailability();
  }, []);

  const loadAvailability = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Get VB profile to get vb_id
      const vbProfile = await ventureBuilderAPI.profile.getMyProfile();

      // Get availability profile
      const data = await ventureBuilderAPI.availability.getProfile(vbProfile.id);

      // Handle response - could be array or single object
      const profileData = Array.isArray(data) ? data[0] : data;

      if (profileData) {
        setAvailability({
          windows: (profileData as any).windows || [],
          timezone: (profileData as any).timezone || 'Not set',
        });
      } else {
        setAvailability({ windows: [], timezone: 'Not set' });
      }
    } catch (err: any) {
      console.error('Failed to load availability:', err);
      if (err.message?.includes('404') || err.message?.includes('not found')) {
        setAvailability({ windows: [], timezone: 'Not set' });
      } else {
        setError('Failed to load availability');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Group windows by day
  const getWindowsByDay = (): Map<DayOfWeek, AvailabilityWindow[]> => {
    const grouped = new Map<DayOfWeek, AvailabilityWindow[]>();

    if (!availability?.windows) return grouped;

    availability.windows.forEach((window) => {
      const day =
        typeof window.day_of_week === 'number'
          ? getDayName(window.day_of_week)
          : window.day_of_week;

      if (!grouped.has(day)) {
        grouped.set(day, []);
      }
      grouped.get(day)!.push(window);
    });

    // Sort windows within each day
    grouped.forEach((windows, day) => {
      windows.sort((a, b) => a.start_time.localeCompare(b.start_time));
    });

    return grouped;
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

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  const windowsByDay = getWindowsByDay();
  const hasAvailability = windowsByDay.size > 0;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
          <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white">
            Availability Schedule
          </h3>
          {availability?.timezone && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Timezone: {availability.timezone}
            </p>
          )}
        </div>
      </div>

      {!hasAvailability ? (
        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                No availability set
              </p>
              <p className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">
                You haven't configured any available time slots yet.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {DAY_ORDER.map((day) => {
            const windows = windowsByDay.get(day);
            if (!windows || windows.length === 0) return null;

            return (
              <div
                key={day}
                className="flex items-start gap-4 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0"
              >
                <span className="text-sm font-medium text-gray-900 dark:text-white w-24 flex-shrink-0">
                  {DAY_NAMES[day]}
                </span>
                <div className="flex flex-wrap gap-2">
                  {windows.map((window, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-1 bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300 text-sm rounded-full"
                    >
                      {formatTime(window.start_time)} - {formatTime(window.end_time)}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
