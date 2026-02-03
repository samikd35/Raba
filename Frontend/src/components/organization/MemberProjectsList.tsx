"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { fetchCohortProjects } from '@/components/organization/cohorts/cohortsApi';
import { CohortProjectsResponse, CohortProject } from '@/types/organization';
import { useAuthStore } from '@/stores/authStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import {
  Building2,
  FolderOpen,
  Search,
  AlertCircle,
  RefreshCw,
  ChevronRight,
  Filter,
  User,
  FolderKanban,
  ArrowLeft,
  Calendar,
  Clock,
} from 'lucide-react';

interface MemberProjectsListProps {
  organizationId: string;
  cohortId: string;
}

export default function MemberProjectsList({ organizationId, cohortId }: MemberProjectsListProps) {
  const router = useRouter();
  const { token } = useAuthStore();

  const [data, setData] = useState<CohortProjectsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewingProjectId, setViewingProjectId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [tenantTypeFilter, setTenantTypeFilter] = useState<'all' | 'individual' | 'team'>('all');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const handleBack = () => {
    router.push('/organization/member-projects/cohorts');
  };

  const fetchProjects = useCallback(async () => {
    if (!organizationId || !cohortId) {
      setError('No organization ID or cohort ID provided');
      setLoading(false);
      return;
    }

    if (!token) {
      setError('Authentication required. Please sign in again.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      if (process.env.NODE_ENV === 'development') {
        console.log('🔍 Fetching cohort projects:', { organizationId, cohortId, page });
      }

      const response = await fetchCohortProjects(
        organizationId,
        cohortId,
        token,
        { page, page_size: pageSize }
      );

      console.log('Cohort projects response:', response);

      setData(response);

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Cohort projects loaded:', {
          totalProjects: response.total_count,
          currentPage: response.page,
          hasNext: response.has_next,
          cohortName: response.cohort_name,
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load cohort projects';
      setError(message);
      toast.error(message);
      console.error('Failed to fetch cohort projects:', err);
    } finally {
      setLoading(false);
    }
  }, [organizationId, cohortId, page, token]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Filter projects by search term and tenant type (client-side)
  const filteredProjects = useMemo(() => {
    if (!data?.projects) return [];

    let projects = data.projects;

    // Filter by tenant type
    if (tenantTypeFilter !== 'all') {
      projects = projects.filter((project) => project.tenant_type === tenantTypeFilter);
    }

    // Filter by search term
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      projects = projects.filter(
        (project) =>
          project.name?.toLowerCase().includes(search) ||
          project.description?.toLowerCase().includes(search) ||
          project.tenant_name?.toLowerCase().includes(search) ||
          project.owner_name?.toLowerCase().includes(search) ||
          project.owner_email?.toLowerCase().includes(search)
      );
    }

    return projects;
  }, [data?.projects, searchTerm, tenantTypeFilter]);

  const handleViewProject = (project: CohortProject) => {
    setViewingProjectId(project.id);
    // Navigate to project detail page
    router.push(`/organization/member-projects/cohorts/${cohortId}/${project.id}`);
  };

  const handleRefresh = () => {
    setPage(1);
    fetchProjects();
  };

  const handleNextPage = () => {
    if (data?.has_next) {
      setPage((prev) => prev + 1);
    }
  };

  const handlePrevPage = () => {
    if (page > 1) {
      setPage((prev) => prev - 1);
    }
  };

  const getTenantIcon = (tenantType: string) => {
    return tenantType === 'team' ? Building2 : User;
  };

  const getTenantTypeColor = (tenantType: string) => {
    return tenantType === 'team'
      ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
      : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
      case 'completed':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
      case 'paused':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatStepName = (step: string) => {
    return step
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Loading State
  if (loading && !data) {
    return (
      <Card className="p-0 pb-6 overflow-hidden">
        <div className="bg-brand-25 dark:bg-brand-900/10 border-b border-brand-50 dark:border-brand-800 rounded-t-xl px-6 py-4 mt-0 flex justify-between items-center">
          <div>
            <Skeleton className="h-6 w-48 mb-2" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-9 w-24 rounded-md" />
        </div>
        <CardContent className="mt-6">
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center justify-between p-4 border border-gray-100 dark:border-gray-800 rounded-lg">
                <div className="flex items-center space-x-4 flex-1">
                  <Skeleton className="w-12 h-12 rounded-full" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                </div>
                <Skeleton className="h-9 w-24" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error State
  if (error && !data) {
    return (
      <Card className="p-0 pb-6 overflow-hidden">
        <div className="bg-brand-25 dark:bg-brand-900/10 border-b border-brand-50 dark:border-brand-800 rounded-t-xl px-6 py-4 mt-0 flex justify-between items-center">
          <CardTitle className="flex items-center space-x-2 text-lg">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <span>Error</span>
          </CardTitle>
          <Button variant="outline" size="sm" onClick={handleBack} className="flex items-center gap-2 text-brand-500">
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </Button>
        </div>
        <CardContent className="py-16">
          <div className="text-center">
            <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Failed to Load Cohort Projects
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">{error}</p>
            <Button onClick={handleRefresh} className="flex items-center space-x-2 bg-brand-500 hover:bg-brand-600 text-white">
              <RefreshCw className="w-4 h-4" />
              <span>Try Again</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Empty State
  if (!loading && filteredProjects.length === 0) {
    return (
      <Card className="p-0 pb-6 overflow-hidden">
        <div className="bg-brand-25 dark:bg-brand-900/10 border-b border-brand-50 dark:border-brand-800 rounded-t-xl px-6 py-4 mt-0 flex justify-between items-center">
          <div>
            <CardTitle className="flex items-center space-x-2 text-lg">
              <FolderKanban className="w-5 h-5" />
              <span>{data?.cohort_name || 'Cohort'} Projects</span>
            </CardTitle>
            <CardDescription className="text-xs">
              View projects from cohort members
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={handleBack} className="flex items-center gap-2 text-brand-500 dark:text-white">
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </Button>
        </div>
        <CardContent className="py-16">
          <div className="text-center">
            <div className="w-16 h-16 bg-brand-50 dark:bg-brand-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <FolderOpen className="w-8 h-8 text-brand-400" />
            </div>
            <h3 className="text-xl font-semibold text-brand-500 dark:text-white mb-2">
              {searchTerm || tenantTypeFilter !== 'all' ? 'No matching projects found' : 'No projects yet'}
            </h3>
            <p className="text-brand-500 dark:text-brand-400 mb-8 max-w-md mx-auto">
              {searchTerm || tenantTypeFilter !== 'all'
                ? 'Try adjusting your search or filter criteria.'
                : 'Projects will appear here once cohort members create them.'}
            </p>
            <div className="flex justify-center">
            {(searchTerm || tenantTypeFilter !== 'all') ? (
              <Button
                variant="outline"
                className="text-brand-500 border-brand-200 hover:bg-brand-50"
                onClick={() => {
                  setSearchTerm('');
                  setTenantTypeFilter('all');
                }}
              >
                Clear Filters
              </Button>
            ) : (
              <Button onClick={handleRefresh} variant="outline" className="flex items-center space-x-2 text-brand-500 border-brand-200">
                <RefreshCw className="w-4 h-4" />
                <span>Refresh View</span>
              </Button>
            )}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="p-0 pb-6 overflow-hidden">
      <div className="bg-brand-25 dark:bg-brand-900/10 border-b border-brand-50 dark:border-brand-800 rounded-t-xl px-6 py-3 mt-0 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        {/* Left: Title and count */}
        <div className="flex items-center space-x-3 flex-shrink-0">
          <div>
            <CardTitle className="flex items-center space-x-2 text-lg">
              <FolderKanban className="w-5 h-5" />
              <span>{data?.cohort_name || 'Cohort'} Projects</span>
            </CardTitle>
            <CardDescription className="text-xs">
              {filteredProjects.length} of {data?.total_count || 0} projects
            </CardDescription>
          </div>
        </div>

        {/* Center: Search and Filter */}
        <div className="flex flex-1 items-center gap-3 max-w-2xl">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-brand-500 dark:text-white w-4 h-4" />
            <Input
              placeholder="Search projects..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 h-9 bg-white dark:bg-gray-950"
            />
          </div>
          <Select
            value={tenantTypeFilter}
            onValueChange={(value: 'all' | 'individual' | 'team') => {
              setTenantTypeFilter(value);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-36 h-9 bg-white dark:bg-gray-950 text-brand-500 dark:text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem className="text-brand-500 dark:text-white" value="all">All Types</SelectItem>
              <SelectItem className="text-brand-500 dark:text-white" value="individual">Individuals</SelectItem>
              <SelectItem className="text-brand-500 dark:text-white" value="team">Teams</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Right: Refresh button */}
        <div className="flex items-center justify-end gap-2 flex-shrink-0">
          <Button variant="outline" size="sm" onClick={handleBack} className="flex items-center gap-2 h-9 text-brand-500 dark:text-white">
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </Button>
          <Button variant="outline" size="icon" onClick={handleRefresh} disabled={loading} className="h-9 w-9">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''} text-brand-500 dark:text-white`} />
          </Button>
        </div>
      </div>

      <CardContent className="-mt-4">
        {/* Desktop View - Table */}
        <div className="hidden md:block">
          <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 bg-brand-25 dark:bg-brand-900/10">
                  <th className="text-left py-3 px-4 font-medium text-brand-500 dark:text-white border-r border-gray-200 dark:border-gray-700 last:border-r-0">Project</th>
                  <th className="text-left py-3 px-4 font-medium text-brand-500 dark:text-white border-r border-gray-200 dark:border-gray-700 last:border-r-0">Type</th>
                  <th className="text-left py-3 px-4 font-medium text-brand-500 dark:text-white border-r border-gray-200 dark:border-gray-700 last:border-r-0">Current Step</th>
                  <th className="text-left py-3 px-4 font-medium text-brand-500 dark:text-white border-r border-gray-200 dark:border-gray-700 last:border-r-0">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-brand-500 dark:text-white border-r border-gray-200 dark:border-gray-700 last:border-r-0">Updated</th>
                  <th className="text-right py-3 px-4 font-medium text-brand-500 dark:text-white">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredProjects.map((project) => {
                  return (
                    <tr
                      key={project.id}
                      className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors last:border-b-0"
                    >
                      <td className="py-4 px-4 border-r border-gray-100 dark:border-gray-800 last:border-r-0">
                        <div className="min-w-0">
                          <p className="font-medium text-brand-500 dark:text-white truncate" title={project.name}>
                            {project.name.length > 30 ? `${project.name.substring(0, 30)}...` : project.name}
                          </p>
                          {project.description && (
                            <p className="text-sm text-gray-500 dark:text-gray-400 truncate" title={project.description}>
                              {project.description.length > 50 ? `${project.description.substring(0, 50)}...` : project.description}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-4 border-r border-gray-100 dark:border-gray-800 last:border-r-0">
                        <Badge className={getTenantTypeColor(project.tenant_type)}>
                          {project.tenant_type === 'team' ? 'Team' : 'Individual'}
                        </Badge>
                      </td>
                      <td className="py-4 px-4 border-r border-gray-100 dark:border-gray-800 last:border-r-0">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {formatStepName(project.current_step)}
                        </span>
                      </td>
                      <td className="py-4 px-4 border-r border-gray-100 dark:border-gray-800 last:border-r-0">
                        <Badge className={getStatusColor(project.status)}>
                          {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                        </Badge>
                      </td>
                      <td className="py-4 px-4 border-r border-gray-100 dark:border-gray-800 last:border-r-0">
                        <div className="flex items-center space-x-1 text-sm text-gray-500 dark:text-gray-400">
                          <Clock className="w-3 h-3" />
                          <span>{formatDate(project.updated_at)}</span>
                        </div>
                      </td>
                      <td className="py-4 px-4 text-right">
                        <Button
                          onClick={() => handleViewProject(project)}
                          size="sm"
                          variant="outline"
                          disabled={viewingProjectId === project.id}
                          className="flex items-center space-x-1 bg-brand-25 text-brand-500 dark:text-brand-400 min-w-16"
                        >
                          {viewingProjectId === project.id ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <>
                              <span>View</span>
                              <ChevronRight className="w-4 h-4" />
                            </>
                          )}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Mobile View - Cards */}
        <div className="md:hidden space-y-4">
          {filteredProjects.map((project) => {
            const Icon = getTenantIcon(project.tenant_type);
            return (
              <Card key={project.id} className="p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 dark:text-white truncate">{project.name}</p>
                    {project.description && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2 mt-1">
                        {project.description}
                      </p>
                    )}
                  </div>
                  <Badge className={getStatusColor(project.status)}>
                    {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                  </Badge>
                </div>

                <div className="flex items-center space-x-3 mb-3">
                  <div className="w-10 h-10 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center flex-shrink-0">
                    <Icon className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {project.owner_name || project.tenant_name}
                    </p>
                    <Badge className={`${getTenantTypeColor(project.tenant_type)} text-xs`}>
                      {project.tenant_type === 'team' ? 'Team' : 'Individual'}
                    </Badge>
                  </div>
                </div>

                <div className="space-y-2 mb-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Current Step</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {formatStepName(project.current_step)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Updated</span>
                    <span className="text-gray-600 dark:text-gray-400">{formatDate(project.updated_at)}</span>
                  </div>
                </div>

                <Button
                  onClick={() => handleViewProject(project)}
                  size="sm"
                  disabled={viewingProjectId === project.id}
                  className="w-full flex items-center justify-center space-x-1"
                >
                  {viewingProjectId === project.id ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <span>View Project</span>
                      <ChevronRight className="w-4 h-4" />
                    </>
                  )}
                </Button>
              </Card>
            );
          })}
        </div>

        {/* Pagination */}
        {data && data.total_count > pageSize && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Page {page} of {Math.ceil(data.total_count / pageSize)} • Total: {data.total_count} projects
            </p>
            <div className="flex items-center space-x-2">
              <Button onClick={handlePrevPage} disabled={page === 1 || loading} variant="outline" size="sm">
                Previous
              </Button>
              <Button onClick={handleNextPage} disabled={!data.has_next || loading} variant="outline" size="sm">
                Next
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
