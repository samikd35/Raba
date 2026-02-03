import { useState, useMemo, useCallback } from 'react';

export interface PaginationOptions {
  initialPage?: number;
  initialPageSize?: number;
  pageSizeOptions?: number[];
}

export interface PaginationResult<T> {
  // Current page data
  currentPageData: T[];
  
  // Pagination state
  currentPage: number;
  pageSize: number;
  totalPages: number;
  totalItems: number;
  
  // Navigation
  goToPage: (page: number) => void;
  nextPage: () => void;
  previousPage: () => void;
  goToFirstPage: () => void;
  goToLastPage: () => void;
  
  // Page size
  setPageSize: (size: number) => void;
  
  // State checks
  canGoNext: boolean;
  canGoPrevious: boolean;
  
  // Page range info
  startIndex: number;
  endIndex: number;
}

/**
 * Custom hook for client-side pagination
 * 
 * @param data - Array of items to paginate
 * @param options - Pagination configuration
 * @returns Pagination state and controls
 */
export function usePagination<T>(
  data: T[],
  options: PaginationOptions = {}
): PaginationResult<T> {
  const {
    initialPage = 1,
    initialPageSize = 10,
  } = options;

  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);

  // Calculate pagination values
  const totalItems = data.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalItems);

  // Get current page data
  const currentPageData = useMemo(() => {
    return data.slice(startIndex, endIndex);
  }, [data, startIndex, endIndex]);

  // Navigation functions
  const goToPage = useCallback((page: number) => {
    const validPage = Math.max(1, Math.min(page, totalPages));
    setCurrentPage(validPage);
  }, [totalPages]);

  const nextPage = useCallback(() => {
    goToPage(currentPage + 1);
  }, [currentPage, goToPage]);

  const previousPage = useCallback(() => {
    goToPage(currentPage - 1);
  }, [currentPage, goToPage]);

  const goToFirstPage = useCallback(() => {
    setCurrentPage(1);
  }, []);

  const goToLastPage = useCallback(() => {
    setCurrentPage(totalPages);
  }, [totalPages]);

  // Update page size and reset to first page
  const handleSetPageSize = useCallback((size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  }, []);

  // State checks
  const canGoNext = currentPage < totalPages;
  const canGoPrevious = currentPage > 1;

  // Reset to first page if current page exceeds total pages
  if (currentPage > totalPages && totalPages > 0) {
    setCurrentPage(1);
  }

  return {
    currentPageData,
    currentPage,
    pageSize,
    totalPages,
    totalItems,
    goToPage,
    nextPage,
    previousPage,
    goToFirstPage,
    goToLastPage,
    setPageSize: handleSetPageSize,
    canGoNext,
    canGoPrevious,
    startIndex,
    endIndex,
  };
}

/**
 * Hook for server-side pagination
 * Manages pagination state without slicing data
 */
export function useServerPagination(
  totalItems: number,
  options: PaginationOptions = {}
) {
  const {
    initialPage = 1,
    initialPageSize = 10,
  } = options;

  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalItems);

  const goToPage = useCallback((page: number) => {
    const validPage = Math.max(1, Math.min(page, totalPages));
    setCurrentPage(validPage);
  }, [totalPages]);

  const nextPage = useCallback(() => {
    goToPage(currentPage + 1);
  }, [currentPage, goToPage]);

  const previousPage = useCallback(() => {
    goToPage(currentPage - 1);
  }, [currentPage, goToPage]);

  const goToFirstPage = useCallback(() => {
    setCurrentPage(1);
  }, []);

  const goToLastPage = useCallback(() => {
    setCurrentPage(totalPages);
  }, [totalPages]);

  const handleSetPageSize = useCallback((size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  }, []);

  const canGoNext = currentPage < totalPages;
  const canGoPrevious = currentPage > 1;

  return {
    currentPage,
    pageSize,
    totalPages,
    totalItems,
    goToPage,
    nextPage,
    previousPage,
    goToFirstPage,
    goToLastPage,
    setPageSize: handleSetPageSize,
    canGoNext,
    canGoPrevious,
    startIndex,
    endIndex,
    // Offset and limit for API calls
    offset: startIndex,
    limit: pageSize,
  };
}
