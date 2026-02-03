'use client';

import WeeklyTimeGrid from './WeeklyTimeGrid';
import type { CreateAvailabilityWindowPayload, DayOfWeek } from '@/types/ventureBuilder';

interface VisualAvailabilityEditorProps {
  windows: CreateAvailabilityWindowPayload[];
  onAddWindow: (day: DayOfWeek, startTime: string, endTime: string) => void;
  onUpdateWindow: (index: number, startTime: string, endTime: string) => void;
  onDeleteWindow: (index: number) => void;
}

export default function VisualAvailabilityEditor({
  windows,
  onAddWindow,
  onUpdateWindow,
  onDeleteWindow,
}: VisualAvailabilityEditorProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      {/* Weekly grid */}
      <WeeklyTimeGrid
        windows={windows}
        onAddWindow={onAddWindow}
        onUpdateWindow={onUpdateWindow}
        onDeleteWindow={onDeleteWindow}
      />
    </div>
  );
}
