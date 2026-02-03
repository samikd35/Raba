"use client"

import { useState, useRef, useEffect, useCallback } from 'react';

export const useAutoSave = <T>(
  data: T,
  storageKey: string,
  debounceMs: number = 2000
) => {
  const [isAutoSaving, setIsAutoSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const autoSave = useCallback(() => {
    if (typeof window === 'undefined') return;

    setIsAutoSaving(true);
    try {
      localStorage.setItem(storageKey, JSON.stringify(data));
      setLastSaved(new Date());
    } catch (error) {
      console.error('Auto-save failed:', error);
    } finally {
      setTimeout(() => setIsAutoSaving(false), 1000);
    }
  }, [data, storageKey]);

  useEffect(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(autoSave, debounceMs);

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [autoSave, debounceMs]);

  return { isAutoSaving, lastSaved };
};
