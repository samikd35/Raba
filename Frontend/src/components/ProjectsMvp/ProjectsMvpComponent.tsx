'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { AnimatePresence } from 'framer-motion';
import { toast } from "react-hot-toast";
import { useAuthStore } from '@/stores/authStore';

// Import sub-components and utilities
import { ProjectsLoading } from './ProjectsLoading';
import { ProjectsError } from './ProjectsError';
import { ProjectsEmpty } from './ProjectsEmpty';
import { ProjectCard } from './ProjectCard';
import { CreateProjectCard } from './CreateProjectCard';
import { CreateProjectModal } from './CreateProjectModal';
import { ProjectsFilters } from './ProjectsFilters';
import { getCachedData, setCachedData, clearCache } from './cacheUtils';
import { fetchCompletedValueMaps } from './apiService';
import { Project, SortField, SortOrder, StatusFilter } from './types';

interface ProjectsMvpProps {
  path?: 'workspace' | 'team-workspace';
}

// BULLETPROOF: Single status state
type LoadStatus = 'loading' | 'success' | 'error' | 'empty';

/**
 * Main ProjectsMvp component - displays completed value map projects
 */
export const ProjectsMvp: React.FC<ProjectsMvpProps> = ({ path = 'team-workspace' }) => {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuthStore();
  const abortControllerRef = useRef<AbortController | null>(null);

  // State management - BULLETPROOF: starts as 'loading', NEVER shows empty until API confirms
  const [projects, setProjects] = useState<Project[]>([]);
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('updated_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  /**
   * Load projects from cache or API
   */
  const loadProjects = useCallback(async (forceRefresh = false) => {
    // Cancel any ongoing requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    try {
      setStatus('loading');
      setError(null);

      // Try to load from cache first (unless force refresh)
      if (!forceRefresh) {
        const cachedData = getCachedData();
        if (cachedData && cachedData.length > 0) {
          if (process.env.NODE_ENV === 'development') {
            console.log('Loaded projects from cache:', cachedData.length);
          }
          setProjects(cachedData);
          setStatus('success');
          return;
        }
      } else {
        clearCache();
      }

      // Fetch from API
      if (process.env.NODE_ENV === 'development') {
        console.log('Fetching projects from API');
      }

      const response = await fetchCompletedValueMaps(abortControllerRef.current.signal, forceRefresh);

      if (response.success && response.data.projects) {
        setProjects(response.data.projects);
        setCachedData(response.data.projects);
        // BULLETPROOF: Only set success/empty AFTER API confirms
        setStatus(response.data.projects.length > 0 ? 'success' : 'empty');
      } else {
        throw new Error(response.message || 'Failed to load projects');
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(errorMessage);
      setStatus('error');

      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to load projects:', err);
      }
    }
  }, []);

  /**
   * Initial load on mount
   */
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      loadProjects();
    }

    // Cleanup on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [authLoading, isAuthenticated, loadProjects]);

  /**
   * Handle retry
   */
  const handleRetry = useCallback(() => {
    loadProjects(true);
  }, [loadProjects]);

  /**
   * Navigation handlers
   */
  const handleNavigateToProject = useCallback((projectId: string) => {
    // Find the project to check context_mode
    const project = projects.find(p => p.id === projectId);

    if (project?.context_mode === 'bootstrap') {
      router.push(`/${path}/projects-mvp/bootstrap/${projectId}`);
    } else {
      router.push(`/${path}/projects-mvp/${projectId}`);
    }
  }, [router, path, projects]);

  const handleGoToCustomerUnderstanding = useCallback(() => {
    router.push(`/${path}/customer-understanding`);
  }, [router, path]);

  const handleStartValidationProject = useCallback(() => {
    router.push(`/${path}/validation-project/new`);
  }, [router, path]);

  /**
   * Filter and sort projects
   */
  const filteredAndSortedProjects = useMemo(() => {
    let filtered = [...projects];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (project) =>
          project.name.toLowerCase().includes(query) ||
          project.problem_statement.toLowerCase().includes(query)
      );
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(
        (project) => project.status.toLowerCase() === statusFilter
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (sortField) {
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
        case 'personas_count':
          aValue = a.personas_count;
          bValue = b.personas_count;
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [projects, searchQuery, statusFilter, sortField, sortOrder]);

  /**
   * Toggle sort order
   */
  const handleSortOrderToggle = useCallback(() => {
    setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
  }, []);

  /**
   * Handle create project modal
   */
  const handleOpenCreateModal = useCallback(() => {
    setIsCreateModalOpen(true);
  }, []);

  const handleCloseCreateModal = useCallback(() => {
    setIsCreateModalOpen(false);
  }, []);

  // BULLETPROOF: Use single status state - Loading ALWAYS shows first
  if (status === 'loading') {
    return <ProjectsLoading />;
  }

  // Error state
  if (status === 'error') {
    return (
      <ProjectsError
        error={error || 'An error occurred'}
        onRetry={handleRetry}
        onGoToCustomerUnderstanding={handleGoToCustomerUnderstanding}
        onStartValidationProject={handleStartValidationProject}
      />
    );
  }

  // Empty state - ONLY when API confirms zero projects
  if (status === 'empty') {
    return (
      <ProjectsEmpty
        onGoToCustomerUnderstanding={handleGoToCustomerUnderstanding}
        onStartValidationProject={handleStartValidationProject}
        isCreateModalOpen={isCreateModalOpen}
        onCloseCreateModal={handleCloseCreateModal}
        onProjectCreated={() => loadProjects(true)}
        onOpenCreateModal={handleOpenCreateModal}
      />
    );
  }

  // Main content
  return (
    <div className="space-y-4">
      {/* Filters */}
      <ProjectsFilters
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        sortField={sortField}
        onSortFieldChange={setSortField}
        sortOrder={sortOrder}
        onSortOrderToggle={handleSortOrderToggle}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
      />

      {/* Results count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Showing {filteredAndSortedProjects.length} of {projects.length} projects
        </p>
      </div>

      {/* Projects Grid */}
      <AnimatePresence mode="wait">
        {filteredAndSortedProjects.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {/* Create Project Card */}
            <CreateProjectCard
              index={0}
              onClick={handleOpenCreateModal}
            />

            {/* Existing Projects */}
            {filteredAndSortedProjects.map((project, index) => (
              <ProjectCard
                key={project.id}
                project={project}
                index={index + 1}
                onNavigate={handleNavigateToProject}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-500 dark:text-gray-400">
              No projects match your search criteria
            </p>
          </div>
        )}
      </AnimatePresence>

      {/* Create Project Modal */}
      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={handleCloseCreateModal}
        onProjectCreated={() => loadProjects(true)}
      />
    </div>
  );
};
