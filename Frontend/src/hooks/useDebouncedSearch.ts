import { useState, useEffect, useCallback, useRef } from 'react';
import { debounceAsync } from '@/lib/utils/debounce';

/**
 * Custom hook for debounced search functionality
 * 
 * @param searchFn - Async function to execute the search
 * @param delay - Debounce delay in milliseconds (default: 300ms)
 * @returns Search state and control functions
 */
export function useDebouncedSearch<T>(
  searchFn: (query: string) => Promise<T>,
  delay: number = 300
) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<T | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Create debounced search function
  const debouncedSearchRef = useRef(
    debounceAsync(async (searchQuery: string) => {
      if (!searchQuery.trim()) {
        setResults(null);
        setIsSearching(false);
        return;
      }

      try {
        setIsSearching(true);
        setError(null);
        const data = await searchFn(searchQuery);
        setResults(data);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Search failed';
        setError(errorMessage);
        console.error('Search error:', err);
      } finally {
        setIsSearching(false);
      }
    }, delay)
  );

  // Update query and trigger debounced search
  const search = useCallback((newQuery: string) => {
    setQuery(newQuery);
    if (newQuery.trim()) {
      setIsSearching(true);
      debouncedSearchRef.current(newQuery);
    } else {
      setResults(null);
      setIsSearching(false);
      setError(null);
    }
  }, []);

  // Clear search results
  const clear = useCallback(() => {
    setQuery('');
    setResults(null);
    setIsSearching(false);
    setError(null);
  }, []);

  return {
    query,
    results,
    isSearching,
    error,
    search,
    clear,
  };
}

/**
 * Custom hook for debounced value
 * Useful for form inputs that trigger API calls
 * 
 * @param value - Value to debounce
 * @param delay - Debounce delay in milliseconds (default: 300ms)
 * @returns Debounced value
 */
export function useDebouncedValue<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}
