'use client';

import { useState, useEffect } from 'react';
import { Calendar, Loader2, AlertCircle, ChevronLeft, ChevronRight, Clock } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';
import type { BookableSlot, GetAvailabilityResponse } from '@/types/ventureBuilder';

interface AvailabilitySlotPickerProps {
  vbId: string;
  vbName: string;
  onSlotSelect: (slot: BookableSlot) => void;
  selectedSlot?: BookableSlot | null;
}

export default function AvailabilitySlotPicker({
  vbId,
  vbName,
  onSlotSelect,
  selectedSlot,
}: AvailabilitySlotPickerProps) {
  const [availability, setAvailability] = useState<GetAvailabilityResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentWeekStart, setCurrentWeekStart] = useState<Date>(getStartOfWeek(new Date()));

  useEffect(() => {
    loadAvailability();
  }, [vbId, currentWeekStart]);

  const loadAvailability = async () => {
    try {
      setIsLoading(true);
      const weekEnd = new Date(currentWeekStart);
      weekEnd.setDate(weekEnd.getDate() + 13); // Load 2 weeks

      const data = await ventureBuilderAPI.availability.getBookableSlots({
        vb_id: vbId,
        start_date: formatDate(currentWeekStart),
        end_date: formatDate(weekEnd),
      });

      setAvailability(data);
    } catch (error: any) {
      console.error('Failed to load availability:', error);
      toast.error('Failed to load available time slots');
    } finally {
      setIsLoading(false);
    }
  };

  const groupSlotsByDate = () => {
    if (!availability) return [];

    // Filter to only available slots
    const availableSlots = availability.slots.filter(slot => slot.available);

    const grouped = new Map<string, BookableSlot[]>();

    availableSlots.forEach((slot) => {
      const date = new Date(slot.start).toDateString();
      if (!grouped.has(date)) {
        grouped.set(date, []);
      }
      grouped.get(date)!.push(slot);
    });

    // Convert to array and sort by date
    return Array.from(grouped.entries())
      .map(([dateStr, slots]) => ({
        date: new Date(dateStr),
        dateStr,
        slots: slots.sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime()),
      }))
      .sort((a, b) => a.date.getTime() - b.date.getTime());
  };

  const goToPreviousWeek = () => {
    const newDate = new Date(currentWeekStart);
    newDate.setDate(newDate.getDate() - 7);

    // Don't allow going to past weeks
    if (newDate < getStartOfWeek(new Date())) {
      return;
    }

    setCurrentWeekStart(newDate);
  };

  const goToNextWeek = () => {
    const newDate = new Date(currentWeekStart);
    newDate.setDate(newDate.getDate() + 7);
    setCurrentWeekStart(newDate);
  };

  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const formatDateHeader = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    });
  };

  const isSlotSelected = (slot: BookableSlot) => {
    return selectedSlot?.start === slot.start;
  };

  const groupedSlots = groupSlotsByDate();
  const isCurrentWeek = currentWeekStart.getTime() === getStartOfWeek(new Date()).getTime();

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
            <Calendar className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Select a Time Slot
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Book a 60-minute session with {vbName}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={goToPreviousWeek}
            disabled={isCurrentWeek}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Previous week"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="text-sm font-medium text-gray-900 dark:text-white min-w-[120px] text-center">
            {currentWeekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} -{' '}
            {new Date(currentWeekStart.getTime() + 6 * 24 * 60 * 60 * 1000).toLocaleDateString(
              'en-US',
              { month: 'short', day: 'numeric' }
            )}
          </span>
          <button
            onClick={goToNextWeek}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Next week"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {availability && availability.time_zone && (
        <div className="mb-4 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <Clock className="w-4 h-4" />
          <span>Times shown in {availability.time_zone}</span>
        </div>
      )}

      {groupedSlots.length === 0 ? (
        <div className="py-12 text-center">
          <div className="mb-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg inline-block">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
              <div className="text-left">
                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                  No available slots
                </p>
                <p className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">
                  {vbName} has no available time slots in the next two weeks. Try checking again
                  later.
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-6 max-h-[600px] overflow-y-auto">
          {groupedSlots.map(({ date, dateStr, slots }) => (
            <div key={dateStr}>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 sticky top-0 bg-white dark:bg-gray-800 py-2 z-10">
                {formatDateHeader(date)}
              </h4>

              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
                {slots.map((slot, index) => {
                  const selected = isSlotSelected(slot);
                  return (
                    <button
                      key={`${slot.start}-${index}`}
                      onClick={() => onSlotSelect(slot)}
                      className={`
                        px-4 py-2 rounded-lg text-sm font-medium transition-all
                        ${
                          selected
                            ? 'bg-brand-600 text-white ring-2 ring-brand-600 ring-offset-2 dark:ring-offset-gray-800'
                            : 'bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-brand-50 dark:hover:bg-brand-900/20 hover:text-brand-700 dark:hover:text-brand-300 border border-gray-200 dark:border-gray-600'
                        }
                      `}
                    >
                      {formatTime(slot.start)}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedSlot && (
        <div className="mt-6 p-4 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-lg">
          <div className="flex items-start gap-2">
            <Clock className="w-5 h-5 text-brand-600 dark:text-brand-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-brand-900 dark:text-brand-300">
                Selected Time Slot
              </p>
              <p className="text-sm text-brand-700 dark:text-brand-400 mt-1">
                {new Date(selectedSlot.start).toLocaleString('en-US', {
                  weekday: 'long',
                  month: 'long',
                  day: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit',
                  hour12: true,
                })}{' '}
                - {formatTime(selectedSlot.end)}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper functions
function getStartOfWeek(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
  d.setDate(diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
