"use client"

import * as React from "react"
import { CheckIcon, ChevronsUpDownIcon, Globe } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { AFRICAN_COUNTRIES } from "@/lib/constants/countries"

const countries = AFRICAN_COUNTRIES.map(country => ({
  value: country,
  label: country,
}))

interface CountrySelectionProps {
  value?: string
  onValueChange?: (value: string) => void
  placeholder?: string
  className?: string
}

export function CountrySelection({ 
  value = "", 
  onValueChange, 
  placeholder = "Select country...",
  className 
}: CountrySelectionProps) {
  const [open, setOpen] = React.useState(false)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn(
            "w-full h-12 justify-between text-left transition-all duration-200",
            "bg-white dark:bg-gray-900/50 border border-gray-300 dark:border-gray-600",
            "hover:border-brand-400 dark:hover:border-brand-500 hover:shadow-sm",
            "focus:border-brand-500 dark:focus:border-brand-400 focus:ring-1 focus:ring-brand-500/20",
            "text-gray-900 dark:text-gray-100 rounded-lg",
            value && "border-brand-400 dark:border-brand-500 bg-brand-50/50 dark:bg-brand-900/10",
            className
          )}
        >
          {value ? (
            <span className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-brand-500 dark:text-brand-400" />
              {countries.find((country) => country.value === value)?.label}
            </span>
          ) : (
            <span className="text-gray-500 dark:text-gray-400 flex items-center gap-2">
              <Globe className="w-4 h-4" />
              {placeholder}
            </span>
          )}
          <ChevronsUpDownIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent 
        className={cn(
          "w-full max-h-80 border border-gray-200 dark:border-gray-700",
          "bg-white dark:bg-gray-900 shadow-lg rounded-lg overflow-hidden p-0"
        )}
        side="bottom"
        align="start"
      >
        <Command>
          <div className="sticky top-0 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 p-3">
            <CommandInput 
              placeholder="Search countries..." 
              className="h-9 border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800"
            />
          </div>
          <CommandList className="max-h-60">
            <CommandEmpty className="py-8 text-center">
              <div className="flex flex-col items-center justify-center text-center">
                <Globe className="w-6 h-6 text-gray-300 dark:text-gray-600 mb-2" />
                <p className="text-sm text-gray-500 dark:text-gray-400">No countries found</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Try a different search term</p>
              </div>
            </CommandEmpty>
            <CommandGroup className="p-1">
              {countries.map((country) => (
                <CommandItem
                  key={country.value}
                  value={country.value}
                  onSelect={(currentValue) => {
                    const selectedCountry = countries.find(c => c.value.toLowerCase() === currentValue.toLowerCase())?.value || ""
                    onValueChange?.(selectedCountry === value ? "" : selectedCountry)
                    setOpen(false)
                  }}
                  className={cn(
                    "cursor-pointer rounded-md px-3 py-2 text-sm transition-colors",
                    "text-gray-900 dark:text-gray-100",
                    "hover:bg-brand-50 dark:hover:bg-brand-900/20",
                    "focus:bg-brand-100 dark:focus:bg-brand-900/30",
                    "data-[selected=true]:bg-brand-500 data-[selected=true]:text-white",
                    "flex items-center justify-between"
                  )}
                >
                  <span>{country.label}</span>
                  {value === country.value && (
                    <CheckIcon className="w-4 h-4" />
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}