"use client";

import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';

interface NavigationLoadingContextType {
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  startLoading: () => void;
  stopLoading: () => void;
}

const NavigationLoadingContext = createContext<NavigationLoadingContextType | undefined>(undefined);

export function NavigationLoadingProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(false);
  const pathname = usePathname();

  // Timings to improve perceived performance
  const showDelayMs = 150; // don't show overlay for ultra-fast transitions
  const minVisibleMs = 300; // keep visible briefly to avoid flicker once shown
  const hardTimeoutMs = 10000; // absolute safety stop

  const showTimerRef = useRef<NodeJS.Timeout | null>(null);
  const hideTimerRef = useRef<NodeJS.Timeout | null>(null);
  const hardTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shownAtRef = useRef<number | null>(null);

  const clearTimers = () => {
    if (showTimerRef.current) {
      clearTimeout(showTimerRef.current);
      showTimerRef.current = null;
    }
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    if (hardTimeoutRef.current) {
      clearTimeout(hardTimeoutRef.current);
      hardTimeoutRef.current = null;
    }
  };

  const reallyStart = () => {
    setIsLoading(true);
    shownAtRef.current = Date.now();
    // Hard stop safety
    hardTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
      shownAtRef.current = null;
    }, hardTimeoutMs);
  };

  const startLoading = () => {
    // If already scheduled or visible, do nothing
    if (isLoading || showTimerRef.current) return;

    // Delay showing to avoid flash on fast navigations
    showTimerRef.current = setTimeout(() => {
      showTimerRef.current = null;
      // Only show if still relevant
      reallyStart();
    }, showDelayMs);
  };

  const stopLoading = () => {
    // If it never showed yet, just cancel the show timer
    if (showTimerRef.current) {
      clearTimeout(showTimerRef.current);
      showTimerRef.current = null;
      return;
    }

    const now = Date.now();
    const shownAt = shownAtRef.current;

    if (isLoading && shownAt) {
      const elapsed = now - shownAt;
      const remaining = Math.max(minVisibleMs - elapsed, 0);
      if (remaining > 0) {
        // Keep visible a bit longer to prevent flicker
        if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
        hideTimerRef.current = setTimeout(() => {
          setIsLoading(false);
          shownAtRef.current = null;
          if (hardTimeoutRef.current) {
            clearTimeout(hardTimeoutRef.current);
            hardTimeoutRef.current = null;
          }
        }, remaining);
      } else {
        setIsLoading(false);
        shownAtRef.current = null;
        if (hardTimeoutRef.current) {
          clearTimeout(hardTimeoutRef.current);
          hardTimeoutRef.current = null;
        }
      }
    } else {
      // Not loading; ensure timers cleared
      clearTimers();
      shownAtRef.current = null;
      setIsLoading(false);
    }
  };

  // Stop loading when pathname changes (route completed)
  useEffect(() => {
    stopLoading();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, []);

  const value = {
    isLoading,
    setIsLoading,
    startLoading,
    stopLoading,
  };

  return (
    <NavigationLoadingContext.Provider value={value}>
      {children}
    </NavigationLoadingContext.Provider>
  );
}

export function useNavigationLoading() {
  const context = useContext(NavigationLoadingContext);
  if (context === undefined) {
    throw new Error('useNavigationLoading must be used within a NavigationLoadingProvider');
  }
  return context;
}
