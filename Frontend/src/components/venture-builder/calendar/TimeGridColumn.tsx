'use client';

import { useState, useRef } from 'react';
import AvailabilityBlock from './AvailabilityBlock';
import type { DayOfWeek } from '@/types/ventureBuilder';

interface WindowData {
  day_of_week: DayOfWeek;
  start_time: string;
  end_time: string;
  originalIndex: number;
}

interface TimeGridColumnProps {
  day: DayOfWeek;
  dayLabel: string;
  windows: WindowData[];
  onAddWindow: (startTime: string, endTime: string) => void;
  onUpdateWindow: (originalIndex: number, startTime: string, endTime: string) => void;
  onDeleteWindow: (originalIndex: number) => void;
  startHour: number;
  endHour: number;
  hourHeight: number;
  selectedIndex: number | null;
  onSelectWindow: (index: number | null) => void;
}

export default function TimeGridColumn({
  day,
  dayLabel,
  windows,
  onAddWindow,
  onUpdateWindow,
  onDeleteWindow,
  startHour,
  endHour,
  hourHeight,
  selectedIndex,
  onSelectWindow,
}: TimeGridColumnProps) {
  const columnRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);

  const totalHours = endHour - startHour;

  // Convert Y position to time
  const yToTime = (y: number): string => {
    const minutes = Math.round((y / hourHeight) * 60 / 30) * 30; // Snap to 30 min
    const totalMinutes = startHour * 60 + minutes;
    const hours = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
  };

  // Handle mouse down to start creating a new block
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.availability-block')) return;

    const rect = columnRef.current?.getBoundingClientRect();
    if (!rect) return;

    const y = e.clientY - rect.top;
    setIsDragging(true);
    setDragStart(y);
    setDragEnd(y);
    onSelectWindow(null);
  };

  // Handle mouse move while dragging
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || dragStart === null) return;

    const rect = columnRef.current?.getBoundingClientRect();
    if (!rect) return;

    const y = Math.max(0, Math.min(e.clientY - rect.top, totalHours * hourHeight));
    setDragEnd(y);
  };

  // Handle mouse up to finish creating a block
  const handleMouseUp = () => {
    if (!isDragging || dragStart === null || dragEnd === null) {
      setIsDragging(false);
      setDragStart(null);
      setDragEnd(null);
      return;
    }

    const startY = Math.min(dragStart, dragEnd);
    const endY = Math.max(dragStart, dragEnd);

    // Minimum height for a block (30 minutes)
    if (endY - startY >= (hourHeight / 2)) {
      const startTime = yToTime(startY);
      const endTime = yToTime(endY);
      onAddWindow(startTime, endTime);
    }

    setIsDragging(false);
    setDragStart(null);
    setDragEnd(null);
  };

  // Calculate drag preview position
  const getDragPreviewStyle = () => {
    if (!isDragging || dragStart === null || dragEnd === null) return null;

    const top = Math.min(dragStart, dragEnd);
    const height = Math.abs(dragEnd - dragStart);

    return {
      top: `${top}px`,
      height: `${Math.max(height, hourHeight / 2)}px`,
    };
  };

  const dragPreviewStyle = getDragPreviewStyle();

  return (
    <div className="flex flex-col">
      {/* Day header */}
      <div className="h-12 flex items-center justify-center border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 sticky top-0 z-10">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {dayLabel}
        </span>
      </div>

      {/* Time slots */}
      <div
        ref={columnRef}
        className="relative flex-1 border-r border-gray-200 dark:border-gray-700 cursor-crosshair"
        style={{ height: `${totalHours * hourHeight}px` }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Hour grid lines */}
        {Array.from({ length: totalHours }, (_, i) => (
          <div
            key={i}
            className="absolute left-0 right-0 border-t border-gray-100 dark:border-gray-800"
            style={{ top: `${i * hourHeight}px` }}
          />
        ))}

        {/* Half-hour grid lines */}
        {Array.from({ length: totalHours }, (_, i) => (
          <div
            key={`half-${i}`}
            className="absolute left-0 right-0 border-t border-gray-50 dark:border-gray-800/50 border-dashed"
            style={{ top: `${i * hourHeight + hourHeight / 2}px` }}
          />
        ))}

        {/* Availability blocks */}
        {windows.map((window) => (
          <div key={window.originalIndex} className="availability-block">
            <AvailabilityBlock
              startTime={window.start_time}
              endTime={window.end_time}
              onUpdate={(startTime, endTime) =>
                onUpdateWindow(window.originalIndex, startTime, endTime)
              }
              onDelete={() => onDeleteWindow(window.originalIndex)}
              hourHeight={hourHeight}
              startHour={startHour}
              isSelected={selectedIndex === window.originalIndex}
              onSelect={() => onSelectWindow(window.originalIndex)}
            />
          </div>
        ))}

        {/* Drag preview */}
        {dragPreviewStyle && (
          <div
            className="absolute left-1 right-1 bg-brand-400/50 dark:bg-brand-500/50 rounded-md border-2 border-dashed border-brand-500 dark:border-brand-400 pointer-events-none"
            style={dragPreviewStyle}
          />
        )}
      </div>
    </div>
  );
}
