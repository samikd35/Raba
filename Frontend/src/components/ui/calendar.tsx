"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { DayPicker } from "react-day-picker";

import { cn } from "@/lib/utils";

export type CalendarProps = React.ComponentProps<typeof DayPicker>;

export function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  ...props
}: CalendarProps) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn("p-3", className)}
      classNames={{
        months: "flex flex-col sm:flex-row space-y-4 sm:space-x-4 sm:space-y-0",
        month: "space-y-4",
        month_caption: "flex justify-center pt-1 relative items-center mb-2",
        caption_label: "text-sm font-medium text-gray-900 dark:text-gray-100 hidden",
        dropdowns: "flex justify-center gap-2",
        dropdown: "px-2 py-1 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded text-gray-900 dark:text-gray-100",
        dropdown_root: "relative inline-block",
        chevron: "fill-gray-700 dark:fill-gray-200",
        month_grid: "w-full border-collapse space-y-1",
        weekdays: "flex",
        weekday: "text-muted-foreground rounded-md w-9 font-normal text-[0.8rem] text-gray-500 dark:text-gray-400",
        week: "flex w-full mt-2",
        day_button: cn(
          "h-9 w-9 p-0 font-normal hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded-md transition-colors",
          "text-gray-900 dark:text-gray-100"
        ),
        selected:
          "bg-brand-500 text-white hover:bg-brand-500 hover:text-white focus:bg-brand-500 focus:text-white",
        today:
          "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100",
        outside: "text-gray-400 dark:text-gray-500 opacity-50",
        disabled: "text-gray-300 dark:text-gray-600 opacity-50",
        range_middle:
          "aria-selected:bg-brand-100 aria-selected:text-brand-900",
        hidden: "invisible",
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation }) => {
          const Icon = orientation === "left" ? ChevronLeft : ChevronRight;
          return <Icon className="h-4 w-4" />;
        },
      }}
      {...props}
    />
  );
}
