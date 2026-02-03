'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FolderOpen, 
  Loader2, 
  AlertCircle,
  RefreshCw,
  ArrowRight,
  Target,
  Eye,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from "@/components/ui/card";
import { authService } from '@/services/authService';
import toast from "react-hot-toast";

import { AllProjectCard } from '@/components/AllProjects/AllProjectCard';
import { DashboardProject, LatestProjectsResponse } from './types';
import { getCachedProjects, setCachedProjects, clearProjectsCache } from './cacheUtils';
import { AllProject } from '@/components/AllProjects/types';

/**
 * Fetch latest projects from API
 * @param signal - AbortController signal
 * @param skipCache - If true, bypasses backend Redis cache
 */
async function fetchLatestProjects(signal?: AbortSignal, skipCache = false): Promise<LatestProjectsResponse> {
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

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/latest?limit=6`, {
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
    {[...Array(3)].map((_, i) => (
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
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
              <div className="h-4 bg-gray-100 dark:bg-gray-700 rounded w-1/3 animate-pulse"></div>
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
    className="flex flex-col items-center justify-center py-12 text-center"
  >
    <div className="p-4 rounded-full bg-red-100 dark:bg-red-900/30 mb-4">
      <AlertCircle className="w-10 h-10 text-red-600 dark:text-red-400" />
    </div>
    <h3 className="text-lg font-semibold text-brand-500 dark:text-gray-100 mb-2">Failed to Load Projects</h3>
    <p className="text-gray-600 dark:text-gray-400 mb-4 max-w-md">{error}</p>
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
const EmptyProjects = React.memo(() => {
  const router = useRouter();
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-12 text-center"
    >
      <div className="p-6 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 border dark:border-gray-600 mb-6">
        <FolderOpen className="w-12 h-12 text-brand-600 dark:text-gray-400" />
      </div>
      <h3 className="text-lg font-bold text-brand-500 dark:text-gray-100 mb-2">No Projects Yet</h3>
      <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md">
        Start by validating your problem or exploring new opportunities.
      </p>
      <div className="flex flex-col sm:flex-row gap-3">
        <Button 
          onClick={() => router.push('/workspace/problem-validator')}
          className="bg-brand-600 hover:bg-brand-700 text-white"
        >
          <Target className="w-4 h-4 mr-2" />
          Validate Problems
        </Button>
        <Button 
          onClick={() => router.push('/workspace/problem-explorer')}
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

// BULLETPROOF: Single status state
type LoadStatus = 'loading' | 'success' | 'error' | 'empty';

/**
 * Main Dashboard Projects component
 * Uses /api/v2/vmp/projects/latest endpoint with client-side caching
 */
export function DashboardProjects() {
  const [projects, setProjects] = useState<DashboardProject[]>([]);
  // BULLETPROOF: Single status state - starts as 'loading', NEVER shows empty until API confirms
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const router = useRouter();

  /**
   * Load projects from cache or API
   */
  const loadProjects = useCallback(async (forceRefresh = false) => {
    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      setStatus('loading');
      setError(null);

      // Try cache first (unless force refresh)
      if (!forceRefresh) {
        const cached = getCachedProjects();
        if (cached && cached.length > 0) {
          if (process.env.NODE_ENV === 'development') {
            console.log('📦 Dashboard projects loaded from cache:', cached.length);
          }
          setProjects(cached);
          setStatus('success');
          return;
        }
      } else {
        clearProjectsCache();
      }

      // Fetch from API
      if (process.env.NODE_ENV === 'development') {
        console.log('🌐 Fetching dashboard projects from API');
      }

      const response = await fetchLatestProjects(abortControllerRef.current.signal, forceRefresh);

      if (response.success && response.data?.projects) {
        setProjects(response.data.projects);
        setCachedProjects(response.data.projects);
        // BULLETPROOF: Only set success/empty AFTER API confirms
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
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to load dashboard projects:', err);
      }
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadProjects();

    // Cleanup
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadProjects]);

  // Listen for cache invalidation events
  useEffect(() => {
    const handleInvalidate = () => {
      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 Cache invalidation event received, reloading projects');
      }
      loadProjects(true);
    };

    window.addEventListener('dashboard-projects-invalidate', handleInvalidate);
    return () => {
      window.removeEventListener('dashboard-projects-invalidate', handleInvalidate);
    };
  }, [loadProjects]);

  const handleRetry = useCallback(() => {
    loadProjects(true);
  }, [loadProjects]);

  const handleRefresh = useCallback(() => {
    loadProjects(true);
    toast.success('Projects refreshed');
  }, [loadProjects]);

  const handleNavigateToProject = useCallback((projectId: string) => {
    router.push(`/workspace/projects/${projectId}`);
  }, [router]);

  const handleViewAllProjects = useCallback(() => {
    router.push('/workspace/projects');
  }, [router]);

  // BULLETPROOF: Early return for loading - shows ONLY skeleton
  if (status === 'loading') {
    return (
      <Card className="space-y-4 px-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100">
            Recent Projects
          </h2>
        </div>
        <ProjectsLoading />
      </Card>
    );
  }

  // Early return for error
  if (status === 'error') {
    return (
      <Card className="space-y-4 px-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100">
            Recent Projects
          </h2>
        </div>
        <ProjectsError error={error || 'An error occurred'} onRetry={handleRetry} />
      </Card>
    );
  }

  // Early return for empty (ONLY after API confirms 0 projects)
  if (status === 'empty') {
    return (
      <Card className="space-y-4 px-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100">
            Recent Projects
          </h2>
        </div>
        <EmptyProjects />
      </Card>
    );
  }

  // SUCCESS state - show full UI
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      <Card className="px-4">
        
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100">
            Recent Projects
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Your {projects.length} most recently updated projects
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          className="border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Projects Grid */}
      <AnimatePresence mode="wait">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {projects.map((project, index) => (
            <AllProjectCard
              key={project.id}
              project={project as AllProject}
              index={index}
              onNavigate={handleNavigateToProject}
            />
          ))}
        </div>
      </AnimatePresence>

      {/* View All Projects Link */}
      <div className="flex justify-center pt-4">
        <Button
          variant="outline"
          onClick={handleViewAllProjects}
          className="border-gray-200 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800 group"
        >
          <span>View All Projects</span>
          <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
        </Button>
      </div>
      </Card>
    </motion.div>
  );
}
