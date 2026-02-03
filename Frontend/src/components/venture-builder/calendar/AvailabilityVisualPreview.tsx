'use client';

import { useState, useEffect } from 'react';
import { Clock, Loader2, AlertCircle } from 'lucide-react';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';
import type { AvailabilitySlot } from '@/types/ventureBuilder';

// Day names for display (0 = Sunday)
const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

// Format hour for display
const formatHour = (hour: number): string => {
  const period = hour >= 12 ? 'PM' : 'AM';
  const displayHour = hour % 12 || 12;
  return `${displayHour}${period}`;
};

// Parse time string (HH:MM:SS) to hour
const parseHour = (time: string): number => {
  const [hours] = time.split(':').map(Number);
  return hours;
};

// Format time for display (HH:MM:SS -> h:mm AM/PM)
const formatTime = (time: string): string => {
  const [hours] = time.split(':').map(Number);
  if (hours === 0) return '12 AM';
  if (hours === 12) return '12 PM';
  if (hours < 12) return `${hours} AM`;
  return `${hours - 12} PM`;
};

interface AvailabilityVisualPreviewProps {
  startHour?: number;
  endHour?: number;
  hourHeight?: number;
}

export default function AvailabilityVisualPreview({
  startHour = 6,
  endHour = 22,
  hourHeight = 40,
}: AvailabilityVisualPreviewProps) {
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [timezone, setTimezone] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAvailability();
  }, []);

  const loadAvailability = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Get VB profile to get the ID
      const vbProfile = await ventureBuilderAPI.profile.getMyProfile();

      // Get timezone from calendar status
      try {
        const calendarStatus = await ventureBuilderAPI.calendar.getStatus();
        if (calendarStatus.time_zone) {
          setTimezone(calendarStatus.time_zone);
        }
      } catch (e) {
        // Calendar may not be connected
      }

      // Get availability slots using new API
      const data = await ventureBuilderAPI.availability.listSlots(vbProfile.id);
      setSlots(data || []);
    } catch (err: any) {
      console.error('Failed to load availability:', err);
      if (err.message?.includes('404') || err.message?.includes('not found')) {
        setSlots([]);
      } else {
        setError('Failed to load availability');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Group slots by day (0-6, Sunday-Saturday)
  const slotsByDay: Record<number, AvailabilitySlot[]> = {};
  for (let i = 0; i < 7; i++) {
    slotsByDay[i] = slots
      .filter((s) => s.day_of_week === i)
      .sort((a, b) => a.session_start.localeCompare(b.session_start));
  }

  const totalHours = endHour - startHour;
  const hasAvailability = slots.length > 0;

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 text-error-600 dark:text-error-400">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-light-100 dark:bg-blue-light-900/30 rounded-lg">
            <Clock className="w-5 h-5 text-blue-light-600 dark:text-blue-light-400" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              Weekly Availability
            </h3>
            {timezone && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Timezone: {timezone}
              </p>
            )}
          </div>
        </div>
      </div>

      {!hasAvailability ? (
        <div className="p-6">
          <div className="p-4 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-warning-600 dark:text-warning-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-warning-800 dark:text-warning-300">
                  No availability set
                </p>
                <p className="text-sm text-warning-700 dark:text-warning-400 mt-1">
                  Go back to set your available time slots.
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-4">
          {/* Calendar Grid */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <div className="flex">
              {/* Time axis */}
              <div className="w-14 flex-shrink-0 border-r border-gray-200 dark:border-gray-700">
                {/* Empty header cell */}
                <div className="h-10 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800" />

                {/* Hour labels */}
                <div className="relative" style={{ height: `${totalHours * hourHeight}px` }}>
                  {Array.from({ length: totalHours }, (_, i) => (
                    <div
                      key={i}
                      className="absolute left-0 right-0 flex items-start justify-end pr-2 -translate-y-2"
                      style={{ top: `${i * hourHeight}px` }}
                    >
                      <span className="text-[10px] text-gray-500 dark:text-gray-400">
                        {formatHour(startHour + i)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Day columns */}
              <div className="flex-1 grid grid-cols-7">
                {DAY_NAMES.map((dayName, dayIndex) => {
                  const daySlots = slotsByDay[dayIndex] || [];

                  return (
                    <div key={dayIndex} className="border-r border-gray-200 dark:border-gray-700 last:border-r-0">
                      {/* Day header */}
                      <div className="h-10 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex items-center justify-center">
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                          {dayName}
                        </span>
                      </div>

                      {/* Time slots */}
                      <div
                        className="relative bg-gray-50 dark:bg-gray-900"
                        style={{ height: `${totalHours * hourHeight}px` }}
                      >
                        {/* Hour grid lines */}
                        {Array.from({ length: totalHours }, (_, i) => (
                          <div
                            key={i}
                            className="absolute left-0 right-0 border-t border-gray-100 dark:border-gray-800"
                            style={{ top: `${i * hourHeight}px` }}
                          />
                        ))}

                        {/* Availability blocks (1-hour slots) */}
                        {daySlots.map((slot, idx) => {
                          const slotHour = parseHour(slot.session_start);

                          // Skip if outside visible range
                          if (slotHour < startHour || slotHour >= endHour) {
                            return null;
                          }

                          const top = (slotHour - startHour) * hourHeight;
                          const height = hourHeight; // 1 hour slot

                          return (
                            <div
                              key={idx}
                              className="absolute left-1 right-1 bg-brand-500/80 dark:bg-brand-600/80 rounded-md border border-brand-600 dark:border-brand-500"
                              style={{ top: `${top}px`, height: `${height}px` }}
                            >
                              <div className="px-1 py-0.5 text-[9px] text-white font-medium truncate">
                                {formatTime(slot.session_start)}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Session info */}
          <div className="mt-3 text-center">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              All sessions are 60 minutes
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
