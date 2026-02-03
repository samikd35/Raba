'use client';

import { useState } from 'react';
import TimeGridColumn from './TimeGridColumn';
import type { DayOfWeek, CreateAvailabilityWindowPayload } from '@/types/ventureBuilder';

const DAYS_OF_WEEK: DayOfWeek[] = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
];

const DAY_LABELS: Record<DayOfWeek, string> = {
  monday: 'Mon',
  tuesday: 'Tue',
  wednesday: 'Wed',
  thursday: 'Thu',
  friday: 'Fri',
  saturday: 'Sat',
  sunday: 'Sun',
};

interface WeeklyTimeGridProps {
  windows: CreateAvailabilityWindowPayload[];
  onAddWindow: (day: DayOfWeek, startTime: string, endTime: string) => void;
  onUpdateWindow: (index: number, startTime: string, endTime: string) => void;
  onDeleteWindow: (index: number) => void;
  startHour?: number;
  endHour?: number;
  hourHeight?: number;
}

export default function WeeklyTimeGrid({
  windows,
  onAddWindow,
  onUpdateWindow,
  onDeleteWindow,
  startHour = 6,
  endHour = 22,
  hourHeight = 48,
}: WeeklyTimeGridProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  const totalHours = endHour - startHour;

  // Format hour for display
  const formatHour = (hour: number): string => {
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour} ${period}`;
  };

  // Group windows by day with their original indices
  const windowsByDay = DAYS_OF_WEEK.reduce((acc, day) => {
    acc[day] = windows
      .map((w, idx) => ({ ...w, originalIndex: idx }))
      .filter((w) => w.day_of_week === day);
    return acc;
  }, {} as Record<DayOfWeek, Array<CreateAvailabilityWindowPayload & { originalIndex: number }>>);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-900">
      <div className="flex">
        {/* Time axis */}
        <div className="w-16 flex-shrink-0 border-r border-gray-200 dark:border-gray-700">
          {/* Empty header cell */}
          <div className="h-12 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50" />

          {/* Hour labels */}
          <div className="relative" style={{ height: `${totalHours * hourHeight}px` }}>
            {Array.from({ length: totalHours }, (_, i) => (
              <div
                key={i}
                className="absolute left-0 right-0 flex items-start justify-end pr-2 -translate-y-2"
                style={{ top: `${i * hourHeight}px` }}
              >
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {formatHour(startHour + i)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Day columns */}
        <div className="flex-1 grid grid-cols-7">
          {DAYS_OF_WEEK.map((day) => (
            <TimeGridColumn
              key={day}
              day={day}
              dayLabel={DAY_LABELS[day]}
              windows={windowsByDay[day]}
              onAddWindow={(startTime, endTime) => onAddWindow(day, startTime, endTime)}
              onUpdateWindow={onUpdateWindow}
              onDeleteWindow={onDeleteWindow}
              startHour={startHour}
              endHour={endHour}
              hourHeight={hourHeight}
              selectedIndex={selectedIndex}
              onSelectWindow={setSelectedIndex}
            />
          ))}
        </div>
      </div>

      {/* Instructions */}
      <div className="p-3 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
          Click and drag on a day to add availability. Drag blocks to move them. Drag edges to resize.
        </p>
      </div>
    </div>
  );
}
