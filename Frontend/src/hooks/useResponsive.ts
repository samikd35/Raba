import { useState, useEffect } from 'react';

/**
 * Breakpoint definitions matching Tailwind CSS defaults
 */
export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

export type Breakpoint = keyof typeof BREAKPOINTS;

/**
 * Hook to detect current breakpoint
 * 
 * @returns Current breakpoint name
 */
export function useBreakpoint(): Breakpoint {
  const [breakpoint, setBreakpoint] = useState<Breakpoint>('2xl');

  useEffect(() => {
    const updateBreakpoint = () => {
      const width = window.innerWidth;
      
      if (width < BREAKPOINTS.sm) {
        setBreakpoint('sm');
      } else if (width < BREAKPOINTS.md) {
        setBreakpoint('md');
      } else if (width < BREAKPOINTS.lg) {
        setBreakpoint('lg');
      } else if (width < BREAKPOINTS.xl) {
        setBreakpoint('xl');
      } else {
        setBreakpoint('2xl');
      }
    };

    updateBreakpoint();
    window.addEventListener('resize', updateBreakpoint);
    
    return () => window.removeEventListener('resize', updateBreakpoint);
  }, []);

  return breakpoint;
}

/**
 * Hook to check if viewport is at or above a breakpoint
 * 
 * @param breakpoint - Breakpoint to check
 * @returns Whether viewport is at or above the breakpoint
 */
export function useMediaQuery(breakpoint: Breakpoint): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const query = `(min-width: ${BREAKPOINTS[breakpoint]}px)`;
    const media = window.matchMedia(query);
    
    setMatches(media.matches);
    
    const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
    media.addEventListener('change', listener);
    
    return () => media.removeEventListener('change', listener);
  }, [breakpoint]);

  return matches;
}

/**
 * Hook to get viewport dimensions
 * 
 * @returns Object with width and height
 */
export function useViewport() {
  const [viewport, setViewport] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  });

  useEffect(() => {
    const handleResize = () => {
      setViewport({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return viewport;
}

/**
 * Hook to check if device is mobile
 * 
 * @returns Whether device is mobile (< 640px)
 */
export function useIsMobile(): boolean {
  return !useMediaQuery('sm');
}

/**
 * Hook to check if device is tablet
 * 
 * @returns Whether device is tablet (640px - 1024px)
 */
export function useIsTablet(): boolean {
  const isAboveSm = useMediaQuery('sm');
  const isBelowLg = !useMediaQuery('lg');
  return isAboveSm && isBelowLg;
}

/**
 * Hook to check if device is desktop
 * 
 * @returns Whether device is desktop (>= 1024px)
 */
export function useIsDesktop(): boolean {
  return useMediaQuery('lg');
}

/**
 * Hook to get device type
 * 
 * @returns Device type: 'mobile', 'tablet', or 'desktop'
 */
export function useDeviceType(): 'mobile' | 'tablet' | 'desktop' {
  const isMobile = useIsMobile();
  const isTablet = useIsTablet();
  
  if (isMobile) return 'mobile';
  if (isTablet) return 'tablet';
  return 'desktop';
}

/**
 * Hook to check if device is touch-enabled
 * 
 * @returns Whether device supports touch
 */
export function useIsTouchDevice(): boolean {
  const [isTouch, setIsTouch] = useState(false);

  useEffect(() => {
    setIsTouch(
      'ontouchstart' in window ||
      navigator.maxTouchPoints > 0 ||
      (navigator as any).msMaxTouchPoints > 0
    );
  }, []);

  return isTouch;
}

/**
 * Hook to get responsive value based on breakpoint
 * 
 * @param values - Object with values for each breakpoint
 * @returns Value for current breakpoint
 */
export function useResponsiveValue<T>(values: {
  mobile?: T;
  tablet?: T;
  desktop: T;
}): T {
  const deviceType = useDeviceType();
  
  if (deviceType === 'mobile' && values.mobile !== undefined) {
    return values.mobile;
  }
  if (deviceType === 'tablet' && values.tablet !== undefined) {
    return values.tablet;
  }
  return values.desktop;
}

/**
 * Hook to get responsive columns for grid layouts
 * 
 * @param options - Column counts for each device type
 * @returns Number of columns for current device
 */
export function useResponsiveColumns(options: {
  mobile?: number;
  tablet?: number;
  desktop: number;
}): number {
  return useResponsiveValue({
    mobile: options.mobile || 1,
    tablet: options.tablet || 2,
    desktop: options.desktop,
  });
}
