'use client';

import { useState, useEffect, useCallback } from 'react';
import { Loader2, Save, Undo2, AlertCircle, Clock, Plus, Trash2 } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';
import type { AvailabilitySlot } from '@/types/ventureBuilder';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';

// Day names for display
const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const DAY_NAMES_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

// Available time slots (1-hour sessions from 6 AM to 10 PM)
const TIME_OPTIONS = Array.from({ length: 17 }, (_, i) => {
  const hour = i + 6; // 6 AM to 10 PM
  const time = `${String(hour).padStart(2, '0')}:00:00`;
  const displayTime = hour <= 12 ? `${hour}:00 AM` : `${hour - 12}:00 PM`;
  return { value: time, label: hour === 12 ? '12:00 PM' : displayTime };
});

// Local slot type for UI state
interface LocalSlot {
  day_of_week: number;
  session_start: string;
  isNew?: boolean; // Track if this is a newly added slot
}

export default function AvailabilitySection() {
  const [vbId, setVbId] = useState<string | null>(null);
  const [savedSlots, setSavedSlots] = useState<AvailabilitySlot[]>([]);
  const [localSlots, setLocalSlots] = useState<LocalSlot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [timezone, setTimezone] = useState<string>('');

  // Load VB profile and availability slots
  useEffect(() => {
    loadData();
  }, []);

  // Track changes
  useEffect(() => {
    const savedSet = new Set(savedSlots.map(s => `${s.day_of_week}-${s.session_start}`));
    const localSet = new Set(localSlots.map(s => `${s.day_of_week}-${s.session_start}`));

    // Check if sets are different
    const hasAdded = localSlots.some(s => !savedSet.has(`${s.day_of_week}-${s.session_start}`));
    const hasRemoved = savedSlots.some(s => !localSet.has(`${s.day_of_week}-${s.session_start}`));

    setHasChanges(hasAdded || hasRemoved);
  }, [localSlots, savedSlots]);

  const loadData = async () => {
    try {
      setIsLoading(true);

      // Get VB profile
      const vbProfile = await ventureBuilderAPI.profile.getMyProfile();
      setVbId(vbProfile.id);

      // Get calendar status for timezone
      try {
        const calendarStatus = await ventureBuilderAPI.calendar.getStatus();
        if (calendarStatus.time_zone) {
          setTimezone(calendarStatus.time_zone);
        }
      } catch (e) {
        // Calendar may not be connected
      }

      // Get availability slots
      const slots = await ventureBuilderAPI.availability.listSlots(vbProfile.id);
      setSavedSlots(slots);
      setLocalSlots(slots.map(s => ({
        day_of_week: s.day_of_week,
        session_start: s.session_start,
      })));
    } catch (error: any) {
      console.error('Failed to load availability:', error);
      if (!error.message?.includes('404')) {
        toast.error('Failed to load availability');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Get slots for a specific day
  const getSlotsForDay = useCallback((dayOfWeek: number): LocalSlot[] => {
    return localSlots
      .filter(s => s.day_of_week === dayOfWeek)
      .sort((a, b) => a.session_start.localeCompare(b.session_start));
  }, [localSlots]);

  // Add a new slot
  const handleAddSlot = (dayOfWeek: number, sessionStart: string) => {
    // Check if slot already exists
    const exists = localSlots.some(
      s => s.day_of_week === dayOfWeek && s.session_start === sessionStart
    );

    if (exists) {
      toast.error('This time slot already exists');
      return;
    }

    setLocalSlots([...localSlots, { day_of_week: dayOfWeek, session_start: sessionStart, isNew: true }]);
  };

  // Remove a slot
  const handleRemoveSlot = (dayOfWeek: number, sessionStart: string) => {
    setLocalSlots(localSlots.filter(
      s => !(s.day_of_week === dayOfWeek && s.session_start === sessionStart)
    ));
  };

  // Reset to saved state
  const handleReset = () => {
    setLocalSlots(savedSlots.map(s => ({
      day_of_week: s.day_of_week,
      session_start: s.session_start,
    })));
  };

  // Save changes
  const handleSave = async () => {
    if (!vbId) {
      toast.error('VB profile not found');
      return;
    }

    try {
      setIsSaving(true);

      // Find slots to add (in local but not in saved)
      const savedSet = new Set(savedSlots.map(s => `${s.day_of_week}-${s.session_start}`));
      const slotsToAdd = localSlots.filter(s => !savedSet.has(`${s.day_of_week}-${s.session_start}`));

      // Find slots to delete (in saved but not in local)
      const localSet = new Set(localSlots.map(s => `${s.day_of_week}-${s.session_start}`));
      const slotsToDelete = savedSlots.filter(s => !localSet.has(`${s.day_of_week}-${s.session_start}`));

      // Delete removed slots
      if (slotsToDelete.length > 0) {
        await ventureBuilderAPI.availability.deleteSlots(vbId, {
          slots: slotsToDelete.map(s => ({
            day_of_week: s.day_of_week,
            session_start: s.session_start,
          })),
        });
      }

      // Add new slots
      if (slotsToAdd.length > 0) {
        await ventureBuilderAPI.availability.createSlots(vbId, {
          slots: slotsToAdd.map(s => ({
            day_of_week: s.day_of_week,
            session_start: s.session_start,
          })),
        });
      }

      // Reload to get fresh data
      const freshSlots = await ventureBuilderAPI.availability.listSlots(vbId);
      setSavedSlots(freshSlots);
      setLocalSlots(freshSlots.map(s => ({
        day_of_week: s.day_of_week,
        session_start: s.session_start,
      })));

      toast.success('Availability saved successfully!');
    } catch (error: any) {
      console.error('Failed to save availability:', error);
      toast.error(error.message || 'Failed to save availability');
    } finally {
      setIsSaving(false);
    }
  };

  // Format time for display (HH:MM:SS -> h:mm AM/PM)
  const formatTime = (time: string): string => {
    const [hours] = time.split(':').map(Number);
    if (hours === 0) return '12:00 AM';
    if (hours === 12) return '12:00 PM';
    if (hours < 12) return `${hours}:00 AM`;
    return `${hours - 12}:00 PM`;
  };

  // Get available time options for a day (excluding already selected times)
  const getAvailableTimeOptions = (dayOfWeek: number) => {
    const usedTimes = new Set(
      localSlots.filter(s => s.day_of_week === dayOfWeek).map(s => s.session_start)
    );
    return TIME_OPTIONS.filter(opt => !usedTimes.has(opt.value));
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
          <div className="flex items-start gap-3 sm:gap-4">
            <div className="p-2.5 sm:p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
              <Clock className="w-5 h-5 sm:w-6 sm:h-6 text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-1">
                Weekly Availability
              </h3>
              <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
                Set your available 1-hour session times.
                {timezone && (
                  <span className="font-medium"> Timezone: {timezone}</span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {hasChanges && (
              <button
                onClick={handleReset}
                disabled={isSaving}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <Undo2 className="w-4 h-4" />
                <span className="hidden sm:inline">Reset</span>
              </button>
            )}

            <button
              onClick={handleSave}
              disabled={!hasChanges || isSaving}
              className="inline-flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save
                </>
              )}
            </button>
          </div>
        </div>

        {/* Empty state warning */}
        {localSlots.length === 0 && (
          <div className="p-4 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-warning-600 dark:text-warning-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-warning-800 dark:text-warning-300">
                  No availability set
                </p>
                <p className="text-sm text-warning-700 dark:text-warning-400 mt-1">
                  Add at least one time slot to start receiving bookings.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Day Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {DAY_NAMES.map((dayName, dayIndex) => {
          const daySlots = getSlotsForDay(dayIndex);
          const availableOptions = getAvailableTimeOptions(dayIndex);

          return (
            <div
              key={dayIndex}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
            >
              {/* Day Header */}
              <div className="px-4 py-3 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-gray-900 dark:text-white">
                    {dayName}
                  </h4>
                  <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                    {daySlots.length} slot{daySlots.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>

              {/* Slots */}
              <div className="p-3 space-y-2">
                {daySlots.map((slot) => (
                  <div
                    key={`${slot.day_of_week}-${slot.session_start}`}
                    className={`flex items-center justify-between px-3 py-2 rounded-lg border ${
                      slot.isNew
                        ? 'bg-success-50 dark:bg-success-900/20 border-success-200 dark:border-success-700'
                        : 'bg-gray-50 dark:bg-gray-700/50 border-gray-200 dark:border-gray-600'
                    }`}
                  >
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatTime(slot.session_start)}
                    </span>
                    <button
                      onClick={() => handleRemoveSlot(slot.day_of_week, slot.session_start)}
                      className="p-1 text-gray-400 hover:text-error-500 dark:hover:text-error-400 transition-colors"
                      title="Remove slot"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}

                {/* Add Slot Dropdown */}
                {availableOptions.length > 0 && (
                  <div className="pt-2">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button className="w-full px-3 py-2 text-sm border border-dashed border-gray-300 dark:border-gray-600 rounded-lg bg-transparent text-gray-600 dark:text-gray-400 hover:border-brand-400 dark:hover:border-brand-500 hover:bg-gray-50 dark:hover:bg-gray-700/50 focus:outline-none focus:ring-2 focus:ring-brand-500 transition-colors flex items-center justify-center gap-2">
                          <Plus className="w-4 h-4" />
                          Add time slot
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="center" className="w-48 max-h-64 overflow-y-auto">
                        <DropdownMenuLabel className="text-xs text-gray-500 dark:text-gray-400">
                          Select a time
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        {availableOptions.map((opt) => (
                          <DropdownMenuItem
                            key={opt.value}
                            onClick={() => handleAddSlot(dayIndex, opt.value)}
                            className="cursor-pointer flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:bg-brand-50 dark:hover:bg-brand-900/20"
                          >
                            <Clock className="w-3.5 h-3.5 text-gray-400" />
                            {opt.label}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                )}

                {/* No more slots available */}
                {availableOptions.length === 0 && daySlots.length > 0 && (
                  <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-2">
                    All time slots added
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Info note */}
      <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-600 dark:text-gray-400">
          <strong>Note:</strong> All sessions are 60 minutes long. Founders will see available time
          slots based on your schedule and your Google Calendar availability (if connected).
        </p>
      </div>
    </div>
  );
}
