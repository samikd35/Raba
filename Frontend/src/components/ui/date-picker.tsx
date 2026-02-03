'use client';

import * as React from 'react';
import { Calendar as CalendarIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar } from '@/components/ui/calendar';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

const MONTHS = [
  { label: 'January', value: 0 },
  { label: 'February', value: 1 },
  { label: 'March', value: 2 },
  { label: 'April', value: 3 },
  { label: 'May', value: 4 },
  { label: 'June', value: 5 },
  { label: 'July', value: 6 },
  { label: 'August', value: 7 },
  { label: 'September', value: 8 },
  { label: 'October', value: 9 },
  { label: 'November', value: 10 },
  { label: 'December', value: 11 },
];

export interface DatePickerProps {
  label?: React.ReactNode;
  value: string | null | undefined;
  onChange: (value: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
  mode?: 'date' | 'month';
  fromYear?: number;
  toYear?: number;
  defaultMonth?: Date;
  disabledDate?: (date: Date) => boolean;
  helperText?: React.ReactNode;
  className?: string;
  allowClear?: boolean;
  minDate?: Date;
  maxDate?: Date;
}

export function DatePicker({
  label,
  value,
  onChange,
  placeholder = 'Select date',
  disabled,
  mode = 'month',
  fromYear,
  toYear,
  defaultMonth,
  disabledDate,
  helperText,
  className,
  allowClear = true,
  minDate,
  maxDate,
}: DatePickerProps) {
  const normalizedValue = value && value.trim() !== '' ? value : null;
  const parsedDate = React.useMemo(() => parseValue(normalizedValue, mode), [normalizedValue, mode]);
  const initialMonth = React.useMemo(() => {
    const target = parsedDate ?? defaultMonth ?? new Date();
    return clampToRange(target, fromYear, toYear, minDate, maxDate);
  }, [parsedDate, defaultMonth, fromYear, toYear, minDate, maxDate]);

  const [open, setOpen] = React.useState(false);
  const [currentMonth, setCurrentMonth] = React.useState<Date>(initialMonth);

  React.useEffect(() => {
    setCurrentMonth(clampToRange(initialMonth, fromYear, toYear, minDate, maxDate));
  }, [initialMonth, fromYear, toYear, minDate, maxDate]);

  const years = React.useMemo(() => {
    const range = buildYearRange(fromYear, toYear, minDate, maxDate, mode);
    return range;
  }, [fromYear, toYear, minDate, maxDate, mode]);

  const handleSelect = (date?: Date) => {
    if (!date) return;
    const formatted = mode === 'date' ? formatDateValue(date) : formatMonthValue(date);
    onChange(formatted);
    setOpen(false);
  };

  const handleClear = () => {
    onChange(null);
    setOpen(false);
  };

  const buttonLabel = normalizedValue
    ? mode === 'date'
      ? formatDateLabel(normalizedValue)
      : formatMonthLabel(normalizedValue)
    : placeholder;

  const isDateDisabled = (date: Date) => {
    if (disabledDate && disabledDate(date)) return true;
    if (minDate && startOfDay(date) < startOfDay(minDate)) return true;
    if (maxDate && startOfDay(date) > startOfDay(maxDate)) return true;
    if (fromYear && date.getFullYear() < fromYear) return true;
    if (toYear && date.getFullYear() > toYear) return true;
    return false;
  };

  const handleMonthChange = (monthIndex: string) => {
    const index = Number(monthIndex);
    if (Number.isNaN(index)) return;
    setCurrentMonth(new Date(currentMonth.getFullYear(), index, 1));
  };

  const handleYearChange = (yearValue: string) => {
    const year = Number(yearValue);
    if (Number.isNaN(year)) return;
    setCurrentMonth(new Date(year, currentMonth.getMonth(), 1));
  };

  return (
    <div className={cn('space-y-1.5', className)}>
      {label && (
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
      )}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            disabled={disabled}
            className={cn(
              'w-full justify-start text-left font-normal h-11 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg',
              disabled && 'opacity-60 cursor-not-allowed'
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4 text-gray-500 dark:text-gray-400" />
            <span className={normalizedValue ? 'text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400'}>
              {buttonLabel}
            </span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-3 pt-3">
              <Select
                value={String(currentMonth.getMonth())}
                onValueChange={handleMonthChange}
              >
                <SelectTrigger className="h-9 w-32 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                  <SelectValue placeholder="Month" />
                </SelectTrigger>
                <SelectContent>
                  {MONTHS.map((month) => (
                    <SelectItem key={month.value} value={String(month.value)}>
                      {month.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={String(currentMonth.getFullYear())}
                onValueChange={handleYearChange}
              >
                <SelectTrigger className="h-9 w-28 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                  <SelectValue placeholder="Year" />
                </SelectTrigger>
                <SelectContent className="max-h-64">
                  {years.map((year) => (
                    <SelectItem key={year} value={String(year)}>
                      {year}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Calendar
              mode="single"
              selected={parsedDate}
              onSelect={handleSelect}
              month={currentMonth}
              onMonthChange={setCurrentMonth}
              disabled={isDateDisabled}
              numberOfMonths={1}
              initialFocus
            />
          </div>
          {allowClear && (
            <div className="flex items-center justify-between border-t border-gray-200 dark:border-gray-700 px-3 py-2 bg-gray-50 dark:bg-gray-800">
              <button
                type="button"
                onClick={handleClear}
                disabled={!normalizedValue}
                className="text-sm text-brand-600 dark:text-brand-400 disabled:opacity-50"
              >
                Clear
              </button>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {mode === 'date' ? 'Select day' : 'Select month & year'}
              </span>
            </div>
          )}
        </PopoverContent>
      </Popover>
      {helperText && (
        <p className="text-xs text-gray-500 dark:text-gray-400">{helperText}</p>
      )}
    </div>
  );
}

function parseValue(value: string | null | undefined, mode: 'date' | 'month'): Date | undefined {
  if (!value) return undefined;
  if (mode === 'month') {
    const [year, month] = value.split('-').map(Number);
    if (!year || Number.isNaN(year) || Number.isNaN(month)) return undefined;
    return new Date(year, (month ?? 1) - 1, 1);
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return undefined;
  return parsed;
}

function formatMonthValue(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  return `${year}-${month}`;
}

function formatDateValue(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function formatMonthLabel(value: string): string {
  const date = parseValue(value, 'month');
  if (!date) return '';
  return date.toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  });
}

function formatDateLabel(value: string): string {
  const date = parseValue(value, 'date');
  if (!date) return '';
  return date.toLocaleDateString(undefined, {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

function buildYearRange(
  fromYear?: number,
  toYear?: number,
  minDate?: Date,
  maxDate?: Date,
  mode: 'date' | 'month' = 'month'
): number[] {
  const today = new Date();
  let start = fromYear ?? (minDate ? minDate.getFullYear() : today.getFullYear() - (mode === 'date' ? 70 : 10));
  let end = toYear ?? (maxDate ? maxDate.getFullYear() : today.getFullYear() + (mode === 'date' ? 0 : 5));

  if (minDate) {
    start = Math.max(start, minDate.getFullYear());
  }
  if (maxDate) {
    end = Math.min(end, maxDate.getFullYear());
  }
  if (start > end) {
    const swap = start;
    start = end;
    end = swap;
  }
  const years: number[] = [];
  for (let year = start; year <= end; year += 1) {
    years.push(year);
  }
  return years;
}

function clampToRange(
  date: Date,
  fromYear?: number,
  toYear?: number,
  minDate?: Date,
  maxDate?: Date
): Date {
  const clamped = new Date(date);
  if (fromYear && clamped.getFullYear() < fromYear) {
    clamped.setFullYear(fromYear);
  }
  if (toYear && clamped.getFullYear() > toYear) {
    clamped.setFullYear(toYear);
  }
  if (minDate && clamped < minDate) {
    return new Date(minDate);
  }
  if (maxDate && clamped > maxDate) {
    return new Date(maxDate);
  }
  return clamped;
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}
