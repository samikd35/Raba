'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FolderOpen, 
  Loader2, 
  AlertCircle,
  RefreshCw,
  Target,
  Eye,
  Search,
  Filter,
  X,
  SortAsc,
  SortDesc,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from '@/components/ui/badge';
import { authService } from '@/services/authService';
import toast from "react-hot-toast";

import { AllProjectCard } from './AllProjectCard';
import { AllProject, AllProjectsResponse, SortField, SortOrder, StatusFilter } from './types';

/**
 * Fetch all projects from API
 * @param signal - AbortController signal
 * @param skipCache - If true, bypasses backend Redis cache
 */
async function fetchAllProjects(signal?: AbortSignal, skipCache = false): Promise<AllProjectsResponse> {
  const token = authService.getCurrentToken();

  if (!token) {
    throw new Error('Authentication required');
  }

  const headers: Record<string, string> = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Add cache bypass header when refreshing
  if (skipCache) {
    headers['X-Skip-Cache'] = 'true';
  }

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects`, {
    method: 'GET',
    headers,
    signal,
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Session expired. Please sign in again.');
    }
    throw new Error(`Failed to fetch projects: ${response.status}`);
  }

  return response.json();
}

/**
 * Loading skeleton component
 */
const ProjectsLoading = React.memo(() => (
  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
    {[...Array(6)].map((_, i) => (
      <motion.div
        key={i}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: i * 0.1 }}
      >
        <Card className="h-full p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700">
          <div className="space-y-4">
            <div className="flex items-start justify-between">
              <div className="space-y-2 flex-1">
                <div className="h-5 bg-gray-100 dark:bg-gray-700 rounded-lg w-3/4 animate-pulse"></div>
                <div className="h-3 bg-gray-50 dark:bg-gray-800 rounded w-full animate-pulse"></div>
              </div>
              <div className="h-6 w-16 bg-gray-100 dark:bg-gray-700 rounded-full animate-pulse ml-2"></div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
              <div className="h-4 bg-gray-100 dark:bg-gray-700 rounded w-1/2 animate-pulse"></div>
            </div>
            <div className="h-9 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse"></div>
          </div>
        </Card>
      </motion.div>
    ))}
  </div>
));

ProjectsLoading.displayName = 'ProjectsLoading';

/**
 * Error component
 */
const ProjectsError = React.memo(({ error, onRetry }: { error: string; onRetry: () => void }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    className="flex flex-col items-center justify-center py-16 text-center"
  >
    <div className="p-4 rounded-full bg-red-100 dark:bg-red-900/30 mb-6">
      <AlertCircle className="w-12 h-12 text-red-600 dark:text-red-400" />
    </div>
    <h3 className="text-xl font-semibold text-brand-500 dark:text-gray-100 mb-3">Failed to Load Projects</h3>
    <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md">{error}</p>
    <Button onClick={onRetry} variant="outline" className="border-gray-200 dark:border-gray-600">
      <RefreshCw className="w-4 h-4 mr-2" />
      Try Again
    </Button>
  </motion.div>
));

ProjectsError.displayName = 'ProjectsError';

/**
 * Empty state component
 */
const EmptyProjects = React.memo(({ basePath = '/workspace' }: { basePath?: string }) => {
  const router = useRouter();
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      <div className="p-6 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 border dark:border-gray-600 mb-8">
        <FolderOpen className="w-16 h-16 text-brand-600 dark:text-gray-400" />
      </div>
      <h3 className="text-xl font-bold text-brand-500 dark:text-gray-100 mb-3">No Projects Yet</h3>
      <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md">
        Discover more about the reality surrounding the problems you want to solve.
      </p>
      <div className="flex flex-col sm:flex-row gap-4">
        <Button 
          onClick={() => router.push(`${basePath}/problem-validator`)}
          className="bg-brand-600 hover:bg-brand-700 text-white"
        >
          <Target className="w-4 h-4 mr-2" />
          Validate Problems
        </Button>
        <Button 
          onClick={() => router.push(`${basePath}/problem-explorer`)}
          variant="outline"
          className="border-gray-200 dark:border-gray-600"
        >
          <Eye className="w-4 h-4 mr-2" />
          Explore Problems
        </Button>
      </div>
    </motion.div>
  );
});

EmptyProjects.displayName = 'EmptyProjects';

interface FilterState {
  search: string;
  status: StatusFilter;
  sortBy: SortField;
  sortOrder: SortOrder;
}

interface AllProjectsProps {
  basePath?: string;
}

/**
 * Main All Projects component
 * Uses GET /api/v2/vmp/projects endpoint
 */
// Status states: 'loading' | 'success' | 'error' | 'empty'
type LoadStatus = 'loading' | 'success' | 'error' | 'empty';

export function AllProjects({ basePath = '/workspace' }: AllProjectsProps) {
  const [projects, setProjects] = useState<AllProject[]>([]);
  // BULLETPROOF: Single status state - starts as 'loading', NEVER shows empty until API confirms
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    search: '',
    status: 'all',
    sortBy: 'updated_at',
    sortOrder: 'desc',
  });
  const [showFilters, setShowFilters] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const router = useRouter();

  /**
   * Load projects from API
   * @param forceRefresh - If true, bypasses backend cache
   */
  const loadProjects = useCallback(async (forceRefresh = false) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      setStatus('loading');
      setError(null);

      const response = await fetchAllProjects(abortControllerRef.current.signal, forceRefresh);

      if (response.success && response.data?.projects) {
        setProjects(response.data.projects);
        // Only set success/empty AFTER we have the API response
        setStatus(response.data.projects.length > 0 ? 'success' : 'empty');
      } else {
        throw new Error(response.message || 'Failed to fetch projects');
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to load projects';
      setError(errorMessage);
      setStatus('error');
      toast.error(errorMessage);
    }
  }, []);

  useEffect(() => {
    loadProjects();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadProjects]);

  const handleRetry = useCallback(() => {
    loadProjects(true);
  }, [loadProjects]);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await loadProjects(true);
    setIsRefreshing(false);
    toast.success('Projects refreshed');
  }, [loadProjects]);

  const handleNavigateToProject = useCallback((projectId: string) => {
    router.push(`${basePath}/projects/${projectId}`);
  }, [router, basePath]);

  // Filter and sort projects
  const filteredAndSortedProjects = useMemo(() => {
    let filtered = [...projects];

    // Search filter
    if (filters.search.trim()) {
      const searchTerm = filters.search.toLowerCase().trim();
      filtered = filtered.filter(project => 
        project.name.toLowerCase().includes(searchTerm) ||
        project.description?.toLowerCase().includes(searchTerm) ||
        project.problem_statement?.toLowerCase().includes(searchTerm)
      );
    }

    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(project => 
        project.status.toLowerCase() === filters.status
      );
    }

    // Sort projects
    filtered.sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (filters.sortBy) {
        case 'name':
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
          break;
        case 'created_at':
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case 'updated_at':
          aValue = new Date(a.updated_at).getTime();
          bValue = new Date(b.updated_at).getTime();
          break;
        case 'status':
          aValue = a.status.toLowerCase();
          bValue = b.status.toLowerCase();
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return filters.sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return filters.sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [projects, filters]);

  const handleFilterChange = useCallback((key: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({
      search: '',
      status: 'all',
      sortBy: 'updated_at',
      sortOrder: 'desc',
    });
  }, []);

  const hasActiveFilters = useMemo(() => {
    return filters.search.trim() !== '' || 
           filters.status !== 'all' || 
           filters.sortBy !== 'updated_at' ||
           filters.sortOrder !== 'desc';
  }, [filters]);

  // BULLETPROOF: Use single status state to determine what to render
  // Loading state - ALWAYS show first until API responds
  if (status === 'loading') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100">All Projects</h2>
        </div>
        <ProjectsLoading />
      </div>
    );
  }

  // Error state
  if (status === 'error') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100">All Projects</h2>
        </div>
        <ProjectsError error={error || 'An error occurred'} onRetry={handleRetry} />
      </div>
    );
  }

  // Empty state - ONLY when API confirms zero projects
  if (status === 'empty') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100">All Projects</h2>
        </div>
        <EmptyProjects basePath={basePath} />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      <Card className="px-4 py-4 bg-white dark:bg-gray-900 border-gray-100 dark:border-gray-700">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100">
                All Projects
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {filteredAndSortedProjects.length} of {projects.length} project{projects.length !== 1 ? 's' : ''}
                {hasActiveFilters && ' (filtered)'}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              {/* Refresh */}
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>

              {/* Search */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Search projects..."
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  className="pl-10 pr-4 h-9 text-sm border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900"
                />
              </div>

              {/* Filter Toggle */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
                className={`border-gray-200 dark:border-gray-600 ${showFilters ? 'bg-gray-50 dark:bg-gray-800' : ''}`}
              >
                <Filter className="w-4 h-4 mr-2" />
                Filters
                {hasActiveFilters && (
                  <Badge variant="secondary" className="ml-2 bg-gray-100 dark:bg-gray-800">
                    {[filters.status !== 'all', filters.sortBy !== 'updated_at', filters.sortOrder !== 'desc'].filter(Boolean).length}
                  </Badge>
                )}
              </Button>
            </div>
          </div>

          {/* Active Filters */}
          {hasActiveFilters && (
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="h-8 px-2.5 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400"
              >
                <X className="w-3.5 h-3.5 mr-1.5" />
                Clear all
              </Button>
              {filters.status !== 'all' && (
                <Badge variant="outline" className="text-xs border-gray-200 dark:border-gray-600">
                  {filters.status}
                </Badge>
              )}
            </div>
          )}

          {/* Advanced Filters */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700">
                  {/* Status */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Status</label>
                    <Select value={filters.status} onValueChange={(value: StatusFilter) => handleFilterChange('status', value)}>
                      <SelectTrigger className="h-9 text-sm border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900">
                        <SelectValue placeholder="Status" />
                      </SelectTrigger>
                      <SelectContent className="bg-white dark:bg-gray-900 border-gray-100 dark:border-gray-600">
                        <SelectItem value="all">All Status</SelectItem>
                        <SelectItem value="active">Active</SelectItem>
                        <SelectItem value="completed">Completed</SelectItem>
                        <SelectItem value="paused">Paused</SelectItem>
                        <SelectItem value="archived">Archived</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Sort By */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Sort By</label>
                    <Select value={filters.sortBy} onValueChange={(value: SortField) => handleFilterChange('sortBy', value)}>
                      <SelectTrigger className="h-9 text-sm border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900">
                        <SelectValue placeholder="Sort by" />
                      </SelectTrigger>
                      <SelectContent className="bg-white dark:bg-gray-900 border-gray-100 dark:border-gray-600">
                        <SelectItem value="updated_at">Last Updated</SelectItem>
                        <SelectItem value="created_at">Created Date</SelectItem>
                        <SelectItem value="name">Name</SelectItem>
                        <SelectItem value="status">Status</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Sort Order */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Order</label>
                    <Button
                      variant="outline"
                      onClick={() => handleFilterChange('sortOrder', filters.sortOrder === 'asc' ? 'desc' : 'asc')}
                      className="w-full h-9 justify-start text-sm border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900"
                    >
                      {filters.sortOrder === 'asc' ? (
                        <>
                          <SortAsc className="w-4 h-4 mr-2" />
                          Ascending
                        </>
                      ) : (
                        <>
                          <SortDesc className="w-4 h-4 mr-2" />
                          Descending
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Projects Grid */}
          {filteredAndSortedProjects.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-16 text-center"
            >
              <div className="p-4 rounded-full bg-gray-100 dark:bg-gray-800/50 mb-6">
                <Search className="w-12 h-12 text-gray-400 dark:text-gray-500" />
              </div>
              <h3 className="text-xl font-semibold text-brand-500 dark:text-gray-100 mb-3">No Projects Found</h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md">
                No projects match your current search and filter criteria.
              </p>
              <Button onClick={clearFilters} variant="outline" className="border-gray-200 dark:border-gray-600">
                Clear All Filters
              </Button>
            </motion.div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              <AnimatePresence>
                {filteredAndSortedProjects.map((project, index) => (
                  <AllProjectCard
                    key={project.id}
                    project={project}
                    index={index}
                    onNavigate={handleNavigateToProject}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
