'use client';

import { Plus, Trash2, Clock } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type {
  CreateAvailabilityWindowPayload,
  DayOfWeek,
} from '@/types/ventureBuilder';

// Order: Sunday first to match PRD (Sun-Sat)
const DAYS_OF_WEEK: DayOfWeek[] = [
  'sunday',
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
];

const DAY_LABELS: Record<DayOfWeek, string> = {
  sunday: 'Sunday',
  monday: 'Monday',
  tuesday: 'Tuesday',
  wednesday: 'Wednesday',
  thursday: 'Thursday',
  friday: 'Friday',
  saturday: 'Saturday',
};

// Helper to add 60 minutes to a time string (24-hour format)
const addHourToTime = (time: string): string => {
  if (!time || time === '--:--') return '--:--';
  const [hours, minutes] = time.split(':').map(Number);
  const totalMinutes = hours * 60 + minutes + 60;
  const newHours = Math.floor(totalMinutes / 60) % 24;
  const newMinutes = totalMinutes % 60;
  return `${String(newHours).padStart(2, '0')}:${String(newMinutes).padStart(2, '0')}`;
};

// Convert 24-hour time to 12-hour format
const to12HourFormat = (time24: string): { time12: string; period: 'AM' | 'PM' } => {
  if (!time24 || time24 === '--:--') {
    return { time12: '9:00', period: 'AM' };
  }
  const [hours, minutes] = time24.split(':').map(Number);
  const period: 'AM' | 'PM' = hours >= 12 ? 'PM' : 'AM';
  let hour = hours % 12;
  if (hour === 0) hour = 12;
  return { time12: `${hour}:${String(minutes).padStart(2, '0')}`, period };
};

// Convert 12-hour format to 24-hour time string
const to24HourFormat = (time12: string, period: 'AM' | 'PM'): string => {
  const match = time12.match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return '09:00';

  let hour = parseInt(match[1], 10);
  const minute = match[2];

  if (period === 'AM') {
    if (hour === 12) hour = 0;
  } else {
    if (hour !== 12) hour = hour + 12;
  }
  return `${String(hour).padStart(2, '0')}:${minute}`;
};

// Format time for display (12-hour with AM/PM)
const formatTimeDisplay = (time24: string): string => {
  if (!time24 || time24 === '--:--') return '--:--';
  const { time12, period } = to12HourFormat(time24);
  return `${time12} ${period}`;
};

// Check if two time slots overlap
const doSlotsOverlap = (
  slot1Start: string,
  slot1End: string,
  slot2Start: string,
  slot2End: string
): boolean => {
  if (slot1Start === '--:--' || slot2Start === '--:--') return false;
  return (
    (slot1Start >= slot2Start && slot1Start < slot2End) ||
    (slot1End > slot2Start && slot1End <= slot2End) ||
    (slot1Start <= slot2Start && slot1End >= slot2End)
  );
};

interface AvailabilityProfileEditorProps {
  windows: CreateAvailabilityWindowPayload[];
  onAddSlot: (day: DayOfWeek) => void;
  onUpdateStartTime: (index: number, startTime: string) => void;
  onDeleteSlot: (index: number) => void;
}

export default function AvailabilityProfileEditor({
  windows,
  onAddSlot,
  onUpdateStartTime,
  onDeleteSlot,
}: AvailabilityProfileEditorProps) {
  // Group windows by day
  const windowsByDay = DAYS_OF_WEEK.reduce((acc, day) => {
    acc[day] = windows
      .map((w, originalIndex) => ({ ...w, originalIndex }))
      .filter((w) => w.day_of_week === day);
    return acc;
  }, {} as Record<DayOfWeek, (CreateAvailabilityWindowPayload & { originalIndex: number })[]>);

  // Check for overlaps within a day
  const getOverlapError = (day: DayOfWeek, currentIndex: number): string | null => {
    const daySlots = windowsByDay[day];
    const currentSlot = daySlots.find((s) => s.originalIndex === currentIndex);
    if (!currentSlot || currentSlot.start_time === '--:--') return null;

    const currentEnd = addHourToTime(currentSlot.start_time);

    for (const otherSlot of daySlots) {
      if (otherSlot.originalIndex === currentIndex) continue;
      if (otherSlot.start_time === '--:--') continue;

      const otherEnd = addHourToTime(otherSlot.start_time);

      if (doSlotsOverlap(currentSlot.start_time, currentEnd, otherSlot.start_time, otherEnd)) {
        return 'Overlaps with another slot';
      }
    }
    return null;
  };

  const handleTimeInputChange = (
    originalIndex: number,
    currentTime: string,
    newTime12: string
  ) => {
    const { period } = to12HourFormat(currentTime);
    const newTime24 = to24HourFormat(newTime12, period);
    onUpdateStartTime(originalIndex, newTime24);
  };

  const handlePeriodChange = (
    originalIndex: number,
    currentTime: string,
    newPeriod: 'AM' | 'PM'
  ) => {
    const { time12 } = to12HourFormat(currentTime);
    const newTime24 = to24HourFormat(time12, newPeriod);
    onUpdateStartTime(originalIndex, newTime24);
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Day sections */}
      {DAYS_OF_WEEK.map((day) => {
        const daySlots = windowsByDay[day];

        return (
          <div
            key={day}
            className="border-b border-gray-200 dark:border-gray-700 last:border-b-0"
          >
            {/* Day header */}
            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                {DAY_LABELS[day]}
              </h4>
            </div>

            {/* Slots for this day */}
            <div className="px-6 py-4 space-y-3">
              {daySlots.map((slot, slotIndex) => {
                const endTime = addHourToTime(slot.start_time);
                const overlapError = getOverlapError(day, slot.originalIndex);
                const isLastSlot = slotIndex === daySlots.length - 1;
                const { time12, period } = to12HourFormat(slot.start_time);

                return (
                  <div
                    key={slot.originalIndex}
                    className={`p-4 rounded-lg border transition-colors ${
                      overlapError
                        ? 'bg-error-50 dark:bg-error-900/10 border-error-200 dark:border-error-800'
                        : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700'
                    }`}
                  >
                    <div className="flex flex-wrap items-end gap-6">
                      {/* Start Time - Input + AM/PM Selector */}
                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Start Time
                        </label>
                        <div className="flex items-center gap-1">
                          {/* Time input */}
                          <input
                            type="text"
                            value={time12}
                            onChange={(e) =>
                              handleTimeInputChange(slot.originalIndex, slot.start_time, e.target.value)
                            }
                            placeholder="9:00"
                            className="h-9 w-16 rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-center text-gray-800 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
                          />
                          {/* AM/PM Selector */}
                          <Select
                            value={period}
                            onValueChange={(value) =>
                              handlePeriodChange(slot.originalIndex, slot.start_time, value as 'AM' | 'PM')
                            }
                          >
                            <SelectTrigger className="h-9 w-[72px] text-sm" size="sm">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="AM">AM</SelectItem>
                              <SelectItem value="PM">PM</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      {/* End Time (Auto-calculated, locked) with AM/PM display */}
                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          End Time
                        </label>
                        <div className="h-9 w-24 rounded-md border border-gray-300 bg-gray-100 px-2 py-1.5 text-sm text-gray-500 cursor-not-allowed dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 flex items-center justify-center">
                          {formatTimeDisplay(endTime)}
                        </div>
                      </div>

                      {/* Session Length (Fixed 60 minutes - Read-only) */}
                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Duration
                        </label>
                        <div className="h-9 w-20 rounded-md border border-gray-300 bg-gray-100 px-2 py-1.5 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 flex items-center justify-center gap-1">
                          <Clock className="w-3 h-3" />
                          60 min
                        </div>
                      </div>

                      {/* Actions - Add Slot and Delete buttons */}
                      <div className="ml-auto flex items-center gap-2">
                        {/* Add Slot button - only show on last slot */}
                        {isLastSlot && (
                          <button
                            onClick={() => onAddSlot(day)}
                            className="p-2 text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded-lg transition-colors"
                            title="Add another slot"
                          >
                            <Plus className="w-4 h-4" />
                          </button>
                        )}

                        {/* Delete button */}
                        <button
                          onClick={() => onDeleteSlot(slot.originalIndex)}
                          className="p-2 text-error-600 dark:text-error-400 hover:bg-error-50 dark:hover:bg-error-900/20 rounded-lg transition-colors"
                          title="Delete slot"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Overlap error */}
                    {overlapError && (
                      <div className="mt-2 text-xs text-error-600 dark:text-error-400">
                        {overlapError}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
