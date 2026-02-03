"use client";

import React from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import '@/styles/datepicker-custom.css';
import { Calendar } from 'lucide-react';

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
}

const presets = [
  { label: 'Today', days: 0 },
  { label: '1 Week', days: 7 },
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
];

export function DateRangePicker({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
}: DateRangePickerProps) {
  const handlePreset = (days: number) => {
    const end = new Date();
    const start = new Date();
    
    if (days === 0) {
      // Today: start and end are the same (today)
      onStartDateChange(end.toISOString().split('T')[0]);
      onEndDateChange(end.toISOString().split('T')[0]);
    } else {
      // Last X days: start is X days ago, end is today
      start.setDate(start.getDate() - days);
      onStartDateChange(start.toISOString().split('T')[0]);
      onEndDateChange(end.toISOString().split('T')[0]);
    }
  };

  // Convert string dates to Date objects for DatePicker
  const startDateObj = startDate ? new Date(startDate + 'T00:00:00') : null;
  const endDateObj = endDate ? new Date(endDate + 'T00:00:00') : null;

  const handleStartDateChange = (date: Date | null) => {
    if (date) {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      onStartDateChange(`${year}-${month}-${day}`);
    }
  };

  const handleEndDateChange = (date: Date | null) => {
    if (date) {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      onEndDateChange(`${year}-${month}-${day}`);
    }
  };

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
      <div className="flex items-center gap-2">
        <Calendar className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        <div className="relative">
          <DatePicker
            selected={startDateObj}
            onChange={handleStartDateChange}
            maxDate={endDateObj || undefined}
            dateFormat="dd/MM/yyyy"
            className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 cursor-pointer hover:border-brand-500 dark:hover:border-brand-400 transition-colors w-[140px]"
            placeholderText="Start Date"
            showPopperArrow={false}
          />
        </div>
        <span className="text-gray-500 dark:text-gray-400 text-sm font-medium">to</span>
        <div className="relative">
          <DatePicker
            selected={endDateObj}
            onChange={handleEndDateChange}
            minDate={startDateObj || undefined}
            dateFormat="dd/MM/yyyy"
            className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 cursor-pointer hover:border-brand-500 dark:hover:border-brand-400 transition-colors w-[140px]"
            placeholderText="End Date"
            showPopperArrow={false}
          />
        </div>
      </div>
      
      <div className="flex flex-wrap gap-2">
        {presets.map((preset) => (
          <button
            key={preset.label}
            onClick={() => handlePreset(preset.days)}
            className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-brand-500 dark:hover:border-brand-400 transition-colors"
          >
            {preset.label}
          </button>
        ))}
      </div>
    </div>
  );
}
