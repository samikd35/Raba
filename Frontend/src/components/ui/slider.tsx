"use client";

import * as React from "react";
import * as SliderPrimitive from "@radix-ui/react-slider";

import { cn } from "@/lib/utils";

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>
>(({ className, ...props }, ref) => {
  const thumbCount = Array.isArray(props.value ?? props.defaultValue)
    ? (props.value ?? props.defaultValue)?.length ?? 1
    : 1;

  return (
    <SliderPrimitive.Root
      ref={ref}
      className={cn(
        "relative flex w-full touch-none select-none items-center",
        className
      )}
      {...props}
    >
      <SliderPrimitive.Track className="relative h-2 w-full grow overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800">
        <SliderPrimitive.Range className="absolute h-full bg-brand-500 dark:bg-brand-400" />
      </SliderPrimitive.Track>
      {Array.from({ length: thumbCount }).map((_, index) => (
        <SliderThumb key={index} />
      ))}
    </SliderPrimitive.Root>
  );
});
Slider.displayName = SliderPrimitive.Root.displayName;

const SliderThumb = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Thumb>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Thumb>
>((props, ref) => (
  <SliderPrimitive.Thumb
    ref={ref}
    className="block h-4 w-4 rounded-full border border-brand-500 bg-white shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 dark:border-brand-400 dark:bg-gray-900 dark:focus-visible:ring-offset-gray-950"
    {...props}
  />
));
SliderThumb.displayName = SliderPrimitive.Thumb.displayName;

export { Slider };
