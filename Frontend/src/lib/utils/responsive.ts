/**
 * Responsive design utilities
 * 
 * These utilities help create responsive layouts that work across all device sizes
 */

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Combine class names with Tailwind merge
 * Useful for responsive classes
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Get responsive grid columns class
 * 
 * @param mobile - Columns on mobile (< 640px)
 * @param tablet - Columns on tablet (640px - 1024px)
 * @param desktop - Columns on desktop (>= 1024px)
 * @returns Tailwind grid columns class
 */
export function getResponsiveGridCols(
  mobile: number = 1,
  tablet: number = 2,
  desktop: number = 3
): string {
  return cn(
    `grid-cols-${mobile}`,
    `sm:grid-cols-${tablet}`,
    `lg:grid-cols-${desktop}`
  );
}

/**
 * Get responsive gap class
 * 
 * @param mobile - Gap on mobile
 * @param tablet - Gap on tablet
 * @param desktop - Gap on desktop
 * @returns Tailwind gap class
 */
export function getResponsiveGap(
  mobile: number = 2,
  tablet: number = 4,
  desktop: number = 6
): string {
  return cn(
    `gap-${mobile}`,
    `sm:gap-${tablet}`,
    `lg:gap-${desktop}`
  );
}

/**
 * Get responsive padding class
 * 
 * @param mobile - Padding on mobile
 * @param tablet - Padding on tablet
 * @param desktop - Padding on desktop
 * @returns Tailwind padding class
 */
export function getResponsivePadding(
  mobile: number = 4,
  tablet: number = 6,
  desktop: number = 8
): string {
  return cn(
    `p-${mobile}`,
    `sm:p-${tablet}`,
    `lg:p-${desktop}`
  );
}

/**
 * Get responsive text size class
 * 
 * @param mobile - Text size on mobile
 * @param tablet - Text size on tablet
 * @param desktop - Text size on desktop
 * @returns Tailwind text size class
 */
export function getResponsiveTextSize(
  mobile: 'xs' | 'sm' | 'base' | 'lg' | 'xl' = 'sm',
  tablet: 'xs' | 'sm' | 'base' | 'lg' | 'xl' = 'base',
  desktop: 'xs' | 'sm' | 'base' | 'lg' | 'xl' = 'lg'
): string {
  return cn(
    `text-${mobile}`,
    `sm:text-${tablet}`,
    `lg:text-${desktop}`
  );
}

/**
 * Get responsive flex direction class
 * 
 * @param mobile - Flex direction on mobile
 * @param desktop - Flex direction on desktop
 * @returns Tailwind flex direction class
 */
export function getResponsiveFlexDirection(
  mobile: 'row' | 'col' = 'col',
  desktop: 'row' | 'col' = 'row'
): string {
  return cn(
    `flex-${mobile}`,
    `lg:flex-${desktop}`
  );
}

/**
 * Check if touch target meets minimum size (44x44px)
 * 
 * @param element - Element to check
 * @returns Whether element meets minimum touch target size
 */
export function meetsTouchTargetSize(element: HTMLElement): boolean {
  const rect = element.getBoundingClientRect();
  return rect.width >= 44 && rect.height >= 44;
}

/**
 * Get responsive container class
 * Provides proper padding and max-width for different screen sizes
 * 
 * @returns Tailwind container class
 */
export function getResponsiveContainer(): string {
  return cn(
    'w-full',
    'px-4 sm:px-6 lg:px-8',
    'mx-auto',
    'max-w-7xl'
  );
}

/**
 * Get responsive card class
 * 
 * @returns Tailwind card class with responsive padding
 */
export function getResponsiveCard(): string {
  return cn(
    'bg-white dark:bg-gray-800',
    'rounded-lg',
    'shadow-sm',
    'p-4 sm:p-6 lg:p-8',
    'border border-gray-200 dark:border-gray-700'
  );
}

/**
 * Get responsive modal class
 * 
 * @returns Tailwind modal class with responsive sizing
 */
export function getResponsiveModal(): string {
  return cn(
    'w-full',
    'max-w-full sm:max-w-lg lg:max-w-2xl',
    'mx-4 sm:mx-auto',
    'p-4 sm:p-6 lg:p-8'
  );
}

/**
 * Get responsive button class
 * Ensures touch targets are large enough on mobile
 * 
 * @returns Tailwind button class with responsive sizing
 */
export function getResponsiveButton(): string {
  return cn(
    'px-4 py-2',
    'sm:px-6 sm:py-3',
    'min-h-[44px]', // Minimum touch target size
    'text-sm sm:text-base'
  );
}

/**
 * Get responsive table class
 * Makes tables scrollable on mobile
 * 
 * @returns Tailwind table wrapper class
 */
export function getResponsiveTable(): string {
  return cn(
    'w-full',
    'overflow-x-auto',
    '-mx-4 sm:mx-0',
    'px-4 sm:px-0'
  );
}

/**
 * Get responsive sidebar class
 * 
 * @param isOpen - Whether sidebar is open on mobile
 * @returns Tailwind sidebar class
 */
export function getResponsiveSidebar(isOpen: boolean = false): string {
  return cn(
    'fixed lg:static',
    'inset-y-0 left-0',
    'z-50 lg:z-auto',
    'w-64',
    'transform lg:transform-none',
    'transition-transform duration-300',
    isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
    'bg-white dark:bg-gray-800',
    'border-r border-gray-200 dark:border-gray-700'
  );
}

/**
 * Get responsive navigation class
 * 
 * @returns Tailwind navigation class
 */
export function getResponsiveNavigation(): string {
  return cn(
    'flex',
    'flex-col lg:flex-row',
    'gap-2 lg:gap-4',
    'p-4 lg:p-0'
  );
}

/**
 * Get responsive metric card grid class
 * 
 * @returns Tailwind grid class for metric cards
 */
export function getResponsiveMetricGrid(): string {
  return cn(
    'grid',
    'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
    'gap-4 sm:gap-6'
  );
}

/**
 * Get responsive form class
 * 
 * @returns Tailwind form class with responsive spacing
 */
export function getResponsiveForm(): string {
  return cn(
    'space-y-4 sm:space-y-6',
    'w-full'
  );
}

/**
 * Get responsive input class
 * 
 * @returns Tailwind input class with responsive sizing
 */
export function getResponsiveInput(): string {
  return cn(
    'w-full',
    'px-3 py-2',
    'sm:px-4 sm:py-3',
    'text-sm sm:text-base',
    'min-h-[44px]' // Minimum touch target size
  );
}

/**
 * Hide element on specific breakpoints
 * 
 * @param hideOn - Breakpoints to hide on
 * @returns Tailwind class to hide element
 */
export function hideOn(...breakpoints: ('mobile' | 'tablet' | 'desktop')[]): string {
  const classes: string[] = [];
  
  if (breakpoints.includes('mobile')) {
    classes.push('hidden sm:block');
  }
  if (breakpoints.includes('tablet')) {
    classes.push('sm:hidden lg:block');
  }
  if (breakpoints.includes('desktop')) {
    classes.push('lg:hidden');
  }
  
  return cn(...classes);
}

/**
 * Show element only on specific breakpoints
 * 
 * @param showOn - Breakpoints to show on
 * @returns Tailwind class to show element
 */
export function showOn(...breakpoints: ('mobile' | 'tablet' | 'desktop')[]): string {
  const classes: string[] = ['hidden'];
  
  if (breakpoints.includes('mobile')) {
    classes.push('block sm:hidden');
  }
  if (breakpoints.includes('tablet')) {
    classes.push('sm:block lg:hidden');
  }
  if (breakpoints.includes('desktop')) {
    classes.push('lg:block');
  }
  
  return cn(...classes);
}
