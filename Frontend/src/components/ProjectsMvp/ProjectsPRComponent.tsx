'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Calendar,
  Clock,
  FileText,
  Loader2,
  AlertCircle,
  RefreshCw,
  ArrowRight,
  Target,
  BarChart3,
  Users,
  CheckCircle2,
  PlayCircle,
  PauseCircle,
  Search,
  SortAsc,
  SortDesc,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/authService';
import { toast } from "react-hot-toast";

// Types based on the VPS v2 completed API response format
interface Project {
  id: string;
  tenant_id: string;
  user_id: string;
  name: string;
  problem_statement: string;
  status: string;
  created_at: string;
  updated_at: string;
  personas_count: number;
  vps_v2_count: number;
  vps_version: string;
  vps_updated_at: string | null;
  bmc_v2_exists: boolean;
  critique_exists: boolean;
  amrg_ready: boolean;
  module_3_status: 'complete' | 'partial' | 'none';
}

interface ProjectsResponse {
  success: boolean;
  data: {
    projects: Project[];
    total_count: number;
    page: number;
    page_size: number;
    has_next: boolean;
    filter_applied: string;
  };
  message: string;
}

// Cache configuration
const CACHE_KEY = 'completed_vps_v2_cache';
const CACHE_TIMESTAMP_KEY = 'completed_vps_v2_cache_timestamp';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Cache utilities
const getCachedData = (): Project[] | null => {
  if (typeof window === 'undefined') return null;

  try {
    const cached = localStorage.getItem(CACHE_KEY);
    const timestamp = localStorage.getItem(CACHE_TIMESTAMP_KEY);

    if (!cached || !timestamp) return null;

    const age = Date.now() - parseInt(timestamp, 10);
    if (age > CACHE_DURATION) {
      // Cache expired
      localStorage.removeItem(CACHE_KEY);
      localStorage.removeItem(CACHE_TIMESTAMP_KEY);
      return null;
    }

    return JSON.parse(cached);
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to read cache:', error);
    }
    return null;
  }
};

const setCachedData = (data: Project[]): void => {
  if (typeof window === 'undefined') return;
  
  // Don't cache empty arrays - they cause empty state flash on next load
  if (!data || data.length === 0) {
    if (process.env.NODE_ENV === 'development') {
      console.log('Skipping cache - no projects to cache');
    }
    return;
  }

  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(data));
    localStorage.setItem(CACHE_TIMESTAMP_KEY, Date.now().toString());

    if (process.env.NODE_ENV === 'development') {
      console.log('Cached projects data:', data.length);
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to cache data:', error);
    }
  }
};

const clearCache = (): void => {
  if (typeof window === 'undefined') return;

  try {
    localStorage.removeItem(CACHE_KEY);
    localStorage.removeItem(CACHE_TIMESTAMP_KEY);

    if (process.env.NODE_ENV === 'development') {
      console.log('Cleared projects cache');
    }
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('Failed to clear cache:', error);
    }
  }
};

// Enhanced API function with proper error handling
async function fetchCompletedQuestionnaires(signal?: AbortSignal): Promise<ProjectsResponse> {
  const token = authService.getCurrentToken();

  if (!token) {
    throw new Error('Authentication required. Please sign in again.');
  }

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/completed/vps-v2`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    if (response.status === 401) {
      await authService.logout();
      throw new Error('Session expired. Please sign in again.');
    }
    if (response.status === 403) {
      throw new Error('Access forbidden. Please check your permissions.');
    }
    if (response.status === 404) {
      throw new Error('No completed questionnaires found.');
    }
    throw new Error(`Failed to fetch projects: ${response.statusText}`);
  }

  return response.json();
}

// Enhanced Loading Component with Skeleton
const ProjectsLoading = React.memo(() => (
  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
    {[...Array(6)].map((_, i) => (
      <Card key={i} className="h-full border-gray-200 dark:border-gray-700">
        <CardHeader className="pb-4">
          <div className="flex items-start justify-between">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Skeleton className="h-20 rounded-lg" />
            <Skeleton className="h-20 rounded-lg" />
            <Skeleton className="h-20 rounded-lg" />
            <Skeleton className="h-20 rounded-lg" />
          </div>
          <Skeleton className="h-10 w-full rounded-lg" />
        </CardContent>
      </Card>
    ))}
  </div>
));

ProjectsLoading.displayName = 'ProjectsLoading';

// Enhanced Error Component
const ProjectsError = React.memo(({ error, onRetry }: { error: string; onRetry: () => void }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    className="flex flex-col items-center justify-center py-16 px-4"
  >
    <Card className="bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-700 max-w-md w-full">
      <CardContent className="pt-6 text-center">
        <AlertCircle className="h-16 w-16 text-red-500 dark:text-red-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-red-900 dark:text-red-100 mb-2">
          Unable to Load Projects
        </h3>
        <p className="text-red-700 dark:text-red-300 mb-6">
          {error}
        </p>
        <Button
          onClick={onRetry}
          variant="destructive"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Try Again
        </Button>
      </CardContent>
    </Card>
  </motion.div>
));

ProjectsError.displayName = 'ProjectsError';

// Enhanced Empty State Component
const ProjectsEmpty = React.memo(({
  onGoToCustomerUnderstanding,
  onStartValidationProject,
}: {
  onGoToCustomerUnderstanding: () => void;
  onStartValidationProject: () => void;
}) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="flex flex-col items-center justify-center"
  >
    <Card className="max-w-xl w-full border-none">
      <CardContent className="py-10 text-center space-y-4">
        <div className="bg-gray-100 dark:bg-gray-800 rounded-full p-6 w-24 h-24 mx-auto mb-4 flex items-center justify-center">
          <BarChart3 className="h-12 w-12 text-gray-600 dark:text-gray-400" />
        </div>
        <h3 className="text-2xl font-bold text-brand-500 dark:text-gray-100">
          Ready to Delve in your market research findings?
        </h3>
        <p className="text-base text-gray-600 dark:text-gray-400 max-w-lg mx-auto">
          You currently have no project that completed the Customer understanding Sub-module.
        </p>
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            variant="outline"
            className="min-w-[220px] dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
            onClick={onGoToCustomerUnderstanding}
          >
            <Target className="h-4 w-4 mr-2" />
            Complete Customer understanding
          </Button>
          <Button
            className="min-w-[220px] bg-brand-500 hover:bg-brand-600 text-white dark:bg-gray-600 dark:hover:bg-gray-700"
            onClick={onStartValidationProject}
          >
            <BarChart3 className="h-4 w-4 mr-2" />
            Validate Problems
          </Button>
        </div>
      </CardContent>
    </Card>
  </motion.div>
));

ProjectsEmpty.displayName = 'ProjectsEmpty';

// Project Card Component
const ProjectCard = React.memo(({ project, index, onSelect }: { project: Project; index: number; onSelect: (project: Project) => void }) => {
  const [isNavigating, setIsNavigating] = useState(false);

  const getStatusConfig = useCallback((status: string) => {
    const configs = {
      active: {
        color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
        icon: PlayCircle,
        label: 'Active',
        gradient: 'from-green-500/10 to-emerald-500/10'
      },
      completed: {
        color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
        icon: CheckCircle2,
        label: 'Completed',
        gradient: 'from-blue-500/10 to-cyan-500/10'
      },
      paused: {
        color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
        icon: PauseCircle,
        label: 'Paused',
        gradient: 'from-yellow-500/10 to-amber-500/10'
      },
      archived: {
        color: 'bg-gray-100 text-gray-700 dark:bg-gray-800/30 dark:text-gray-400',
        icon: FileText,
        label: 'Archived',
        gradient: 'from-gray-500/10 to-slate-500/10'
      }
    };
    return configs[status.toLowerCase() as keyof typeof configs] || configs.active;
  }, []);

  const statusConfig = useMemo(() => getStatusConfig(project.status), [project.status, getStatusConfig]);
  const StatusIcon = statusConfig.icon;

  const handleProjectClick = useCallback(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('Navigating to project:', project.id);
    }
    setIsNavigating(true);
    onSelect(project);
  }, [project, onSelect]);

  // Calculate statistics based on VPS v2 backend response
  const totalVpsV2 = project.vps_v2_count ?? 0;
  const totalPersonas = project.personas_count ?? 0;
  const hasBmcV2 = project.bmc_v2_exists ?? false;
  const hasCritique = project.critique_exists ?? false;
  const isAmrgReady = project.amrg_ready ?? false;
  const module3Status = project.module_3_status ?? 'none';

  // Format dates
  const formatDate = useCallback((dateString: string) => {
    try {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      }).format(date);
    } catch {
      return 'N/A';
    }
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="group"
    >
      <Card
        className="h-full p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-sm hover:shadow-lg hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 transition-all duration-200 cursor-pointer overflow-hidden relative"
        onClick={handleProjectClick}
      >
        {/* Gradient overlay */}
        {/* <div className={`absolute inset-0 bg-gradient-to-br ${statusConfig.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300`} /> */}

        <div className="relative space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-brand-500 dark:text-gray-100 mb-1 truncate group-hover:text-gray-800 dark:group-hover:text-gray-200 transition-colors">
                {project.name}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                {project.problem_statement || 'No description provided'}
              </p>
            </div>
            <Badge className={`${statusConfig.color} ml-2 flex items-center gap-1 shrink-0`}>
              <StatusIcon className="h-3 w-3" />
              {statusConfig.label}
            </Badge>
          </div>



          {/* Statistics Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-1">
                <Target className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">VPS v2</span>
              </div>
              <p className="text-2xl font-bold text-brand-500 dark:text-gray-100">{totalVpsV2}</p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-1">
                <Users className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Personas</span>
              </div>
              <p className="text-2xl font-bold text-brand-500 dark:text-gray-100">{totalPersonas}</p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-1">
                <BarChart3 className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">BMC v2</span>
              </div>
              <Badge className={hasBmcV2 ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}>
                {hasBmcV2 ? 'Complete' : 'Pending'}
              </Badge>
            </div>

            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-1">
                <FileText className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Business Model Innovation</span>
              </div>
              <Badge className={
                module3Status === 'complete'
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : module3Status === 'partial'
                    ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
              }>
                {module3Status === 'complete' ? 'Complete' : module3Status === 'partial' ? 'Partial' : 'Pending'}
              </Badge>
            </div>
          </div>

          {/* AMRG Ready Badge */}
          {isAmrgReady && (
            <div className="flex items-center gap-2">
              <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                <CheckCircle2 className="h-3 w-3 mr-1" />
                AMRG Ready
              </Badge>
            </div>
          )}

          {/* Project Info */}
          <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700 pt-2">
            <div className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              <span>{formatDate(project.created_at)}</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              <span>Updated {formatDate(project.updated_at)}</span>
            </div>
          </div>

          {/* Navigation Loading Overlay */}
          {isNavigating && (
            <div className="absolute inset-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm flex items-center justify-center rounded-xl z-10">
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-6 w-6 animate-spin text-gray-600 dark:text-gray-400" />
                <span className="text-xs text-gray-600 dark:text-gray-400 font-medium">Opening project...</span>
              </div>
            </div>
          )}

        </div>
      </Card>
    </motion.div>
  );
});

ProjectCard.displayName = 'ProjectCard';

// Filter and Sort Types
type SortOption = 'name' | 'created_at' | 'updated_at' | 'questionnaires';
type SortDirection = 'asc' | 'desc';
type StatusFilter = 'all' | 'active' | 'completed' | 'paused' | 'archived';

interface FilterState {
  search: string;
  status: StatusFilter;
  sortBy: SortOption;
  sortDirection: SortDirection;
}

// BULLETPROOF: Single status state
type LoadStatus = 'loading' | 'success' | 'error' | 'empty';

// Main Component
export default function ProjectsPRComponent({ path }: { path: string }) {
  const router = useRouter();
  const { isAuthenticated, isInitialized, token } = useAuthStore();

  // BULLETPROOF: Simple state - starts as 'loading', NEVER shows empty until API confirms
  const [projects, setProjects] = useState<Project[]>([]);
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    search: '',
    status: 'all',
    sortBy: 'updated_at',
    sortDirection: 'desc'
  });

  // Track if we're currently fetching to prevent duplicate requests
  const isFetchingRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch projects with AbortController and caching
  const fetchData = useCallback(async (forceRefresh: boolean = false) => {
    if (!isInitialized || !isAuthenticated || !token) {
      if (process.env.NODE_ENV === 'development') {
        console.log('Waiting for authentication...');
      }
      return;
    }

    // Prevent duplicate requests
    if (isFetchingRef.current) {
      if (process.env.NODE_ENV === 'development') {
        console.log('Request already in progress, skipping...');
      }
      return;
    }

    // Check cache first unless force refresh
    if (!forceRefresh) {
      const cached = getCachedData();
      if (cached && cached.length > 0) {
        if (process.env.NODE_ENV === 'development') {
          console.log('Using cached data:', cached.length);
        }
        setProjects(cached);
        setStatus('success');
        setError(null);
        return;
      }
    } else {
      clearCache();
    }

    // Abort previous request if exists
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    isFetchingRef.current = true;

    try {
      setStatus('loading');
      setError(null);

      if (process.env.NODE_ENV === 'development') {
        console.log('Fetching VPS v2 completed projects from API...');
      }

      const response = await fetchCompletedQuestionnaires(abortControllerRef.current.signal);

      if (response.success) {
        setProjects(response.data.projects);
        setCachedData(response.data.projects);
        // BULLETPROOF: Only set success/empty AFTER API confirms
        setStatus(response.data.projects.length > 0 ? 'success' : 'empty');

        if (process.env.NODE_ENV === 'development') {
          console.log('Loaded projects:', response.data.projects.length);
        }
      } else {
        throw new Error(response.message || 'Failed to fetch projects');
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Request aborted');
        }
        return;
      }

      const errorMessage = err.message || 'An unexpected error occurred';
      setError(errorMessage);
      setStatus('error');

      if (process.env.NODE_ENV === 'development') {
        console.error('Error fetching projects:', err);
      }

      toast.error(errorMessage);
    } finally {
      isFetchingRef.current = false;
    }
  }, [isInitialized, isAuthenticated, token]);

  // Initial load with cleanup
  useEffect(() => {
    if (isInitialized && isAuthenticated && token) {
      fetchData();
    }

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      isFetchingRef.current = false;
    };
  }, [isInitialized, isAuthenticated, token, fetchData]);

  // Filter and sort projects
  const filteredAndSortedProjects = useMemo(() => {
    let filtered = [...projects];

    // Apply search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(project =>
        project.name.toLowerCase().includes(searchLower) ||
        project.problem_statement?.toLowerCase().includes(searchLower)
      );
    }

    // Apply status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(project =>
        project.status.toLowerCase() === filters.status
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (filters.sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'created_at':
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
        case 'updated_at':
          comparison = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime();
          break;
        case 'questionnaires':
          comparison = (a.vps_v2_count ?? 0) - (b.vps_v2_count ?? 0);
          break;
      }

      return filters.sortDirection === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [projects, filters]);

  // Handle retry with force refresh
  const handleRetry = useCallback(() => {
    fetchData(true);
  }, [fetchData]);

  // Handle project selection
  const handleProjectSelect = useCallback((project: Project) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('Selected project:', project.id);
    }
    router.push(`/${path}/product-requirement/projects/${project.id}`);
  }, [router, path]);

  // Redirect if not authenticated
  if (isInitialized && !isAuthenticated) {
    router.push('/signin');
    return null;
  }

  // BULLETPROOF: Show ONLY loading skeleton until API responds - NO other UI
  if (status === 'loading') {
    return (
      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
        <ProjectsLoading />
      </div>
    );
  }

  // Error state - early return
  if (status === 'error') {
    return (
      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
        <ProjectsError error={error || 'An error occurred'} onRetry={handleRetry} />
      </div>
    );
  }

  // Empty state - early return (ONLY after API confirms 0 projects)
  if (status === 'empty') {
    return (
      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
        <ProjectsEmpty
          onGoToCustomerUnderstanding={() => router.push(`/${path}/product-requirement/projects`)}
          onStartValidationProject={() => router.push(`/${path}/product-requirement/projects`)}
        />
      </div>
    );
  }

  // SUCCESS state - show full UI with filters and projects
  return (
    <div className="min-h-screen rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
      {/* Header */}
      <div className="mb-4">


        {/* Filters and Search */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search projects..."
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              className="pl-10 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
            />
          </div>

          <Select
            value={filters.status}
            onValueChange={(value: StatusFilter) => setFilters(prev => ({ ...prev, status: value }))}
          >
            <SelectTrigger className="w-[180px] dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="paused">Paused</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={filters.sortBy}
            onValueChange={(value: SortOption) => setFilters(prev => ({ ...prev, sortBy: value }))}
          >
            <SelectTrigger className="w-[180px] dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="name">Name</SelectItem>
              <SelectItem value="created_at">Created Date</SelectItem>
              <SelectItem value="updated_at">Updated Date</SelectItem>
              <SelectItem value="questionnaires">VPS v2 Count</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="icon"
            onClick={() => setFilters(prev => ({
              ...prev,
              sortDirection: prev.sortDirection === 'asc' ? 'desc' : 'asc'
            }))}
            className="dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            {filters.sortDirection === 'asc' ? (
              <SortAsc className="h-4 w-4" />
            ) : (
              <SortDesc className="h-4 w-4" />
            )}
          </Button>
          <Button
            onClick={handleRetry}
            variant="outline"
            className="dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* Results count - we're guaranteed to be in success state here */}
        <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
          Showing {filteredAndSortedProjects.length} of {projects.length} projects
        </div>
      </div>

      {/* Content - status is guaranteed to be 'success' here due to early returns above */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
      >
        {filteredAndSortedProjects.map((project, index) => (
          <ProjectCard
            key={project.id}
            project={project}
            index={index}
            onSelect={handleProjectSelect}
          />
        ))}
      </motion.div>
    </div>
  );
}