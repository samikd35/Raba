/**
 * Custom hook for managing loading states in async operations
 */

import { useState, useCallback } from 'react';
import { ErrorHandler } from '@/lib/errors/errorHandler';

interface UseLoadingStateOptions {
  onSuccess?: () => void;
  onError?: (error: any) => void;
  context?: string;
}

/**
 * Hook for managing loading state with error handling
 */
export function useLoadingState(initialState = false) {
  const [isLoading, setIsLoading] = useState(initialState);
  const [error, setError] = useState<string | null>(null);

  const startLoading = useCallback(() => {
    setIsLoading(true);
    setError(null);
  }, []);

  const stopLoading = useCallback(() => {
    setIsLoading(false);
  }, []);

  const setLoadingError = useCallback((errorMessage: string) => {
    setError(errorMessage);
    setIsLoading(false);
  }, []);

  const reset = useCallback(() => {
    setIsLoading(false);
    setError(null);
  }, []);

  return {
    isLoading,
    error,
    startLoading,
    stopLoading,
    setLoadingError,
    reset,
  };
}

/**
 * Hook for wrapping async operations with loading state and error handling
 */
export function useAsyncOperation<T = any>(
  operation: (...args: any[]) => Promise<T>,
  options?: UseLoadingStateOptions
) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<T | null>(null);

  const execute = useCallback(
    async (...args: any[]) => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await operation(...args);
        setData(result);
        options?.onSuccess?.();
        return result;
      } catch (err) {
        const errorInfo = ErrorHandler.handle(
          err,
          options?.context || 'AsyncOperation',
          { silent: true }
        );
        setError(errorInfo.message);
        options?.onError?.(err);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [operation, options]
  );

  const reset = useCallback(() => {
    setIsLoading(false);
    setError(null);
    setData(null);
  }, []);

  return {
    execute,
    isLoading,
    error,
    data,
    reset,
  };
}

/**
 * Hook for managing multiple loading states
 */
export function useMultipleLoadingStates<T extends string>(
  keys: T[]
): {
  loadingStates: Record<T, boolean>;
  startLoading: (key: T) => void;
  stopLoading: (key: T) => void;
  isAnyLoading: boolean;
} {
  const [loadingStates, setLoadingStates] = useState<Record<T, boolean>>(
    keys.reduce((acc, key) => ({ ...acc, [key]: false }), {} as Record<T, boolean>)
  );

  const startLoading = useCallback((key: T) => {
    setLoadingStates(prev => ({ ...prev, [key]: true }));
  }, []);

  const stopLoading = useCallback((key: T) => {
    setLoadingStates(prev => ({ ...prev, [key]: false }));
  }, []);

  const isAnyLoading = Object.values(loadingStates).some(Boolean);

  return {
    loadingStates,
    startLoading,
    stopLoading,
    isAnyLoading,
  };
}

/**
 * Hook for debounced loading state (useful for search/filter operations)
 */
export function useDebouncedLoading(delay = 300) {
  const [isLoading, setIsLoading] = useState(false);
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null);

  const startLoading = useCallback(() => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    setIsLoading(true);
  }, [timeoutId]);

  const stopLoading = useCallback(() => {
    const id = setTimeout(() => {
      setIsLoading(false);
    }, delay);
    setTimeoutId(id);
  }, [delay]);

  return {
    isLoading,
    startLoading,
    stopLoading,
  };
}
