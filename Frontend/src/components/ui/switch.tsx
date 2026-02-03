"use client"

import * as React from "react"
import * as SwitchPrimitive from "@radix-ui/react-switch"

import { cn } from "@/lib/utils"

function Switch({
  className,
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
      data-slot="switch"
      className={cn(
        "peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        "data-[state=checked]:bg-brand-500 data-[state=checked]:border-brand-500",
        "data-[state=unchecked]:bg-transparent data-[state=unchecked]:border-gray-200 dark:data-[state=unchecked]:border-gray-800",
        className
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb
        data-slot="switch-thumb"
        className={cn(
          "pointer-events-none block h-5 w-5 rounded-full shadow-lg ring-0 transition-transform",
          "data-[state=checked]:bg-white data-[state=checked]:translate-x-5",
          "data-[state=unchecked]:bg-gray-200 dark:data-[state=unchecked]:bg-gray-700 data-[state=unchecked]:translate-x-0"
        )}
      />
    </SwitchPrimitive.Root>
  )
}

export { Switch }
