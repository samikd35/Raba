'use client';

import { useState, useRef } from 'react';
import { Trash2, GripVertical } from 'lucide-react';

interface AvailabilityBlockProps {
  startTime: string; // HH:MM
  endTime: string; // HH:MM
  onUpdate: (startTime: string, endTime: string) => void;
  onDelete: () => void;
  hourHeight: number;
  startHour: number;
  isSelected?: boolean;
  onSelect?: () => void;
}

export default function AvailabilityBlock({
  startTime,
  endTime,
  onUpdate,
  onDelete,
  hourHeight,
  startHour,
  isSelected = false,
  onSelect,
}: AvailabilityBlockProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isResizingTop, setIsResizingTop] = useState(false);
  const [isResizingBottom, setIsResizingBottom] = useState(false);
  const blockRef = useRef<HTMLDivElement>(null);

  // Convert time string to minutes from midnight
  const timeToMinutes = (time: string): number => {
    const [hours, minutes] = time.split(':').map(Number);
    return hours * 60 + minutes;
  };

  // Convert minutes to time string
  const minutesToTime = (minutes: number): string => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
  };

  // Calculate position and height based on time
  const startMinutes = timeToMinutes(startTime);
  const endMinutes = timeToMinutes(endTime);
  const startOffset = ((startMinutes / 60) - startHour) * hourHeight;
  const blockHeight = ((endMinutes - startMinutes) / 60) * hourHeight;

  // Format time for display
  const formatTimeDisplay = (time: string): string => {
    const [hours, minutes] = time.split(':').map(Number);
    const period = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;
    return `${displayHours}:${minutes.toString().padStart(2, '0')} ${period}`;
  };

  // Handle drag to move
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.resize-handle')) return;
    e.preventDefault();
    e.stopPropagation();
    onSelect?.();

    const startY = e.clientY;
    const initialStartMinutes = timeToMinutes(startTime);
    const duration = timeToMinutes(endTime) - initialStartMinutes;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      setIsDragging(true);
      const deltaY = moveEvent.clientY - startY;
      const deltaMinutes = Math.round((deltaY / hourHeight) * 60 / 30) * 30; // Snap to 30 min

      let newStartMinutes = initialStartMinutes + deltaMinutes;
      // Clamp to valid range
      newStartMinutes = Math.max(startHour * 60, Math.min(22 * 60 - duration, newStartMinutes));

      const newEndMinutes = newStartMinutes + duration;
      onUpdate(minutesToTime(newStartMinutes), minutesToTime(newEndMinutes));
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  // Handle resize from top
  const handleResizeTop = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onSelect?.();

    const startY = e.clientY;
    const initialStartMinutes = timeToMinutes(startTime);
    const endMinutesValue = timeToMinutes(endTime);

    const handleMouseMove = (moveEvent: MouseEvent) => {
      setIsResizingTop(true);
      const deltaY = moveEvent.clientY - startY;
      const deltaMinutes = Math.round((deltaY / hourHeight) * 60 / 30) * 30;

      let newStartMinutes = initialStartMinutes + deltaMinutes;
      // Minimum 30 minutes duration, clamp to valid range
      newStartMinutes = Math.max(startHour * 60, Math.min(endMinutesValue - 30, newStartMinutes));

      onUpdate(minutesToTime(newStartMinutes), endTime);
    };

    const handleMouseUp = () => {
      setIsResizingTop(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  // Handle resize from bottom
  const handleResizeBottom = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onSelect?.();

    const startY = e.clientY;
    const initialEndMinutes = timeToMinutes(endTime);
    const startMinutesValue = timeToMinutes(startTime);

    const handleMouseMove = (moveEvent: MouseEvent) => {
      setIsResizingBottom(true);
      const deltaY = moveEvent.clientY - startY;
      const deltaMinutes = Math.round((deltaY / hourHeight) * 60 / 30) * 30;

      let newEndMinutes = initialEndMinutes + deltaMinutes;
      // Minimum 30 minutes duration, clamp to valid range
      newEndMinutes = Math.max(startMinutesValue + 30, Math.min(22 * 60, newEndMinutes));

      onUpdate(startTime, minutesToTime(newEndMinutes));
    };

    const handleMouseUp = () => {
      setIsResizingBottom(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  return (
    <div
      ref={blockRef}
      className={`absolute left-1 right-1 rounded-md cursor-move transition-shadow ${
        isSelected
          ? 'bg-brand-600 dark:bg-brand-500 ring-2 ring-brand-400 shadow-lg z-10'
          : 'bg-brand-500 dark:bg-brand-600 hover:bg-brand-600 dark:hover:bg-brand-500'
      } ${isDragging || isResizingTop || isResizingBottom ? 'opacity-80' : ''}`}
      style={{
        top: `${startOffset}px`,
        height: `${Math.max(blockHeight, 30)}px`,
      }}
      onMouseDown={handleMouseDown}
      onClick={(e) => {
        e.stopPropagation();
        onSelect?.();
      }}
    >
      {/* Top resize handle */}
      <div
        className="resize-handle absolute top-0 left-0 right-0 h-2 cursor-ns-resize hover:bg-white/20 rounded-t-md"
        onMouseDown={handleResizeTop}
      />

      {/* Content */}
      <div className="px-2 py-1 text-xs text-white overflow-hidden h-full flex flex-col justify-between">
        <div className="flex items-center gap-1">
          <GripVertical className="w-3 h-3 opacity-60 flex-shrink-0" />
          <span className="font-medium truncate">
            {formatTimeDisplay(startTime)}
          </span>
        </div>
        {blockHeight > 40 && (
          <span className="opacity-80 truncate">
            {formatTimeDisplay(endTime)}
          </span>
        )}
      </div>

      {/* Delete button - only show when selected */}
      {isSelected && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="absolute -top-2 -right-2 p-1 bg-red-500 hover:bg-red-600 text-white rounded-full shadow-md transition-colors"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      )}

      {/* Bottom resize handle */}
      <div
        className="resize-handle absolute bottom-0 left-0 right-0 h-2 cursor-ns-resize hover:bg-white/20 rounded-b-md"
        onMouseDown={handleResizeBottom}
      />
    </div>
  );
}
