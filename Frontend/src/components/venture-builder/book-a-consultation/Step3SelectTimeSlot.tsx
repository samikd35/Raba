'use client';

import React, { useEffect, useState } from 'react';
import { Calendar, Edit2 } from 'lucide-react';
import AvailabilitySlotPicker from '../booking/AvailabilitySlotPicker';
import type { BookableSlot } from '@/types/ventureBuilder';

interface Step3SelectTimeSlotProps {
  vbId: string;
  selectedDatetime: string;
  onSelectTime: (datetime: string) => void;
  ventureBuilderName?: string;
}

export default function Step3SelectTimeSlot({
  vbId,
  selectedDatetime,
  onSelectTime,
  ventureBuilderName = 'Venture Builder',
}: Step3SelectTimeSlotProps) {
  const [selectedSlot, setSelectedSlot] = useState<BookableSlot | null>(null);
  const [showPicker, setShowPicker] = useState(!selectedDatetime);

  useEffect(() => {
    if (selectedDatetime) {
      setShowPicker(false);
    }
  }, [selectedDatetime]);

  const handleSlotSelect = (slot: BookableSlot) => {
    setSelectedSlot(slot);
    onSelectTime(slot.start);
    setShowPicker(false);
  };

  // If time is already selected, show recap with "Change time" button
  if (selectedDatetime) {
    return (
      <>
        <div className="space-y-6">
          <div>
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Selected Time Slot
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Review your selected time or choose a different slot.
            </p>
          </div>

          {/* Time Recap Card */}
          <div className="p-6 bg-gradient-to-br from-brand-50 to-brand-100 dark:from-brand-900/20 dark:to-brand-800/20 rounded-xl border border-brand-200 dark:border-brand-700">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-lg bg-brand-500 dark:bg-brand-600 flex items-center justify-center flex-shrink-0">
                <Calendar className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-brand-600 dark:text-brand-400 mb-2">
                  Your Session Time
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
                  {new Date(selectedDatetime).toLocaleString('en-US', {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </p>
                <p className="text-lg font-semibold text-brand-600 dark:text-brand-400">
                  {new Date(selectedDatetime).toLocaleString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZoneName: 'short',
                  })}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                  60 minute session with {ventureBuilderName}
                </p>
              </div>
            </div>
          </div>

          {/* Change Time Button */}
          <button
            onClick={() => setShowPicker(true)}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <Edit2 className="w-5 h-5" />
            Change Time
          </button>
        </div>

        {showPicker && (
          <AvailabilitySlotPicker
            vbId={vbId}
            vbName={ventureBuilderName}
            onSlotSelect={handleSlotSelect}
            selectedSlot={selectedSlot}
          />
        )}
      </>
    );
  }

  // Initial state: show slot picker
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Select Time Slot
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Choose an available time slot for your session.
        </p>
      </div>

      <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg flex items-start gap-3">
        <Calendar className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-blue-800 dark:text-blue-300">
            Available time slots
          </p>
          <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
            Select a date and time that works for you. All times are displayed in your local timezone.
          </p>
        </div>
      </div>

      <AvailabilitySlotPicker
        vbId={vbId}
        vbName={ventureBuilderName}
        onSlotSelect={handleSlotSelect}
        selectedSlot={selectedSlot}
      />
    </div>
  );
}
