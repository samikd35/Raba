"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { useDebounce } from '@/hooks/useDebounce';
import { TenantProjectsResponse, ProjectSummary, TenantInfo } from '@/types/organization';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuthStore } from '@/stores/authStore';
import { toast } from 'react-hot-toast';
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import {
  ArrowLeft,
  FolderOpen,
  Search,
  AlertCircle,
  RefreshCw,
  Eye,
  Calendar,
  GitBranch,
  Building2,
  User,
  Clock,
  Filter,
  ChevronRight,
  Loader2,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Normalized data structure for display
interface NormalizedTenantData {
  tenant: TenantInfo;
  projects: ProjectSummary[];
  total_count: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

// Helper to normalize backend response
// Backend returns: { member: { tenant_id, tenant_type, tenant_name, ... }, projects: [...], ... }
function normalizeResponse(response: any, tenantId: string): NormalizedTenantData | null {
  if (process.env.NODE_ENV === 'development') {
    console.log('🔄 normalizeResponse called with:', JSON.stringify(response, null, 2));
  }

  if (!response) {
    console.log('❌ normalizeResponse: No response');
    return null;
  }

  // Extract tenant info - handle various response structures
  let tenant: TenantInfo | null = null;

  // Case 1: response.member exists (actual backend structure)
  // Backend returns: { member: { tenant_id, tenant_type, tenant_name, user_email, team_name, ... } }
  if (response.member) {
    console.log('✅ Case 1: Using response.member');
    const m = response.member;
    tenant = {
      tenant_id: m.tenant_id || tenantId,
      tenant_type: (m.tenant_type || 'individual') as 'individual' | 'team',
      // Use tenant_name, or team_name for teams, or user_name for individuals
      name: m.tenant_name || (m.tenant_type === 'team' ? m.team_name : m.user_name) || 'Unknown',
      // Use team_contact_email for teams, or user_email for individuals
      contact_email: m.tenant_type === 'team' ? (m.team_contact_email || m.user_email) : m.user_email,
    };
  }
  // Case 2: response.tenant exists with tenant_type
  else if (response.tenant && response.tenant.tenant_type) {
    console.log('✅ Case 2: Using response.tenant');
    tenant = {
      tenant_id: response.tenant.tenant_id || response.tenant.id || tenantId,
      tenant_type: response.tenant.tenant_type,
      name: response.tenant.name || response.tenant.tenant_name || 'Unknown',
      contact_email: response.tenant.contact_email,
    };
  }
  // Case 3: response.tenant exists but tenant_type might be missing
  else if (response.tenant) {
    console.log('⚠️ Case 3: response.tenant exists but checking for tenant_type');
    const tenantType = response.tenant.tenant_type || response.tenant_type || 'individual';
    tenant = {
      tenant_id: response.tenant.tenant_id || response.tenant.id || tenantId,
      tenant_type: tenantType as 'individual' | 'team',
      name: response.tenant.name || response.tenant.tenant_name || 'Unknown',
      contact_email: response.tenant.contact_email,
    };
  }
  // Case 4: Flat structure - tenant fields at root level
  else if (response.tenant_type || response.tenant_name) {
    console.log('⚠️ Case 4: Using flat structure from root');
    tenant = {
      tenant_id: response.tenant_id || tenantId,
      tenant_type: (response.tenant_type || 'individual') as 'individual' | 'team',
      name: response.tenant_name || response.name || 'Unknown',
      contact_email: response.contact_email,
    };
  }
  // Case 5: No tenant/member info at all - create placeholder
  else if (response.projects !== undefined) {
    console.log('⚠️ Case 5: No tenant/member info, creating placeholder');
    tenant = {
      tenant_id: tenantId,
      tenant_type: 'individual',
      name: 'Member',
      contact_email: undefined,
    };
  }

  if (!tenant) {
    console.log('❌ normalizeResponse: Could not extract tenant info');
    return null;
  }

  // Ensure tenant_type is valid
  if (!tenant.tenant_type || !['individual', 'team'].includes(tenant.tenant_type)) {
    console.log('⚠️ Invalid tenant_type, defaulting to individual');
    tenant.tenant_type = 'individual';
  }

  console.log('✅ normalizeResponse: Normalized tenant:', tenant);

  return {
    tenant,
    projects: response.projects || [],
    total_count: response.total_count || response.projects?.length || 0,
    page: response.page || 1,
    page_size: response.page_size || 20,
    has_next: response.has_next || false,
  };
}

export default function MemberProjectsPage() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuthStore();

  const organizationId = user?.tenant_id;
  const tenantId = params.tenantId as string;

  const [data, setData] = useState<NormalizedTenantData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearchTerm = useDebounce(searchTerm, 500);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [navigatingProjectId, setNavigatingProjectId] = useState<string | null>(null);

  // Reset page to 1 when search term changes
  useEffect(() => {
    setPage(1);
  }, [debouncedSearchTerm]);

  const fetchTenantProjects = useCallback(async () => {
    if (!organizationId || !tenantId) {
      setError('Missing organization or tenant ID');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      if (process.env.NODE_ENV === 'development') {
        console.log('🔍 Fetching tenant projects:', { organizationId, tenantId, page });
      }

      const response = await organizationService.getTenantProjects(organizationId, tenantId, {
        page,
        page_size: pageSize,
        search: debouncedSearchTerm,
      });

      // Log raw response for debugging
      if (process.env.NODE_ENV === 'development') {
        console.log('📦 Raw API Response:', response);
        console.log('📦 Response keys:', response ? Object.keys(response) : 'null');
        console.log('📦 Member object:', (response as any)?.member);
        console.log('📦 Has member?:', !!(response as any)?.member);
      }

      // Normalize the response to handle different backend formats
      const normalizedData = normalizeResponse(response, tenantId);

      if (!normalizedData) {
        console.error('Failed to normalize API response:', {
          response,
          hasResponse: !!response,
          hasTenant: !!response?.tenant,
          hasProjects: !!response?.projects,
          responseKeys: response ? Object.keys(response) : []
        });
        throw new Error('Invalid response from server. Could not parse the data.');
      }

      setData(normalizedData);

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Tenant projects loaded (normalized):', {
          tenantName: normalizedData?.tenant?.name,
          tenantType: normalizedData?.tenant?.tenant_type,
          projectCount: normalizedData?.total_count,
          currentPage: normalizedData?.page,
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load projects';
      const detailedError = `${message}${process.env.NODE_ENV === 'development' ? ` (Tenant ID: ${tenantId})` : ''}`;
      setError(detailedError);
      toast.error(message);
      console.error('Failed to fetch tenant projects:', {
        error: err,
        organizationId,
        tenantId,
        page,
        responseReceived: !!err
      });
    } finally {
      setLoading(false);
    }
  }, [organizationId, tenantId, page, debouncedSearchTerm]);

  useEffect(() => {
    fetchTenantProjects();
  }, [fetchTenantProjects]);

  // Filter projects by search term - with safety check
  const filteredProjects = useMemo(() => {
    if (!data || !data.projects || !Array.isArray(data.projects)) return [];

    if (!searchTerm) return data.projects;

    const search = searchTerm.toLowerCase();
    return data.projects.filter(
      (project) =>
        project.name?.toLowerCase().includes(search) ||
        project.description?.toLowerCase().includes(search) ||
        project.current_step?.toLowerCase().includes(search)
    );
  }, [data, searchTerm]);

  const handleBack = () => {
    router.back();
  };

  const handleViewProject = (projectId: string) => {
    // Navigate to project detail page nested under cohort and tenant
    setNavigatingProjectId(projectId);
    router.push(`/organization/cohorts/${params.id}/${tenantId}/project/${projectId}`);
  };

  const handleRefresh = () => {
    setPage(1);
    fetchTenantProjects();
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return 'N/A';
    }
  };

  const getStepColor = (step: string) => {
    const stepColors: Record<string, string> = {
      project_setup: 'border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-300',
      vpc_composition: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
      field_prep: 'border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
      data_collection: 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400',
      analysis: 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-800 dark:bg-orange-900/20 dark:text-orange-400',
      completed: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-400',
    };
    return stepColors[step] || 'border-gray-200 bg-gray-50 text-gray-700';
  };

  const formatStepName = (step: string) => {
    return step
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Stats calculations - with safety check
  const stats = useMemo(() => {
    if (!data || !data.projects || !Array.isArray(data.projects)) {
      return { total: 0, active: 0, completed: 0 };
    }

    const projects = data.projects;
    return {
      total: data.total_count || 0,
      active: projects.filter((p) => p.current_step !== 'completed').length,
      completed: projects.filter((p) => p.current_step === 'completed').length,
    };
  }, [data]);

  // Loading State
  if (loading && !data) {
    return (
      <div className="space-y-6">
        <PageBreadcrumb pageTitle="Member Projects" />
        <div className="flex items-center space-x-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-48" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-64" />
          ))}
        </div>
      </div>
    );
  }

  // Error State
  if (error && !data) {
    return (
      <div className="space-y-6">
        <PageBreadcrumb pageTitle="Member Projects" />


        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Failed to Load Projects</h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">{error}</p>
              <div className="flex items-center justify-center space-x-3">
                <Button variant="outline" onClick={handleBack}>
                  Go Back
                </Button>
                <Button onClick={handleRefresh}>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Try Again
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Safety check: ensure data, tenant, and tenant_type exist before rendering
  if (!data || !data.tenant || !data.tenant.tenant_type) {
    console.log('⚠️ Safety check failed:', {
      hasData: !!data,
      hasTenant: !!data?.tenant,
      hasTenantType: !!data?.tenant?.tenant_type,
      tenantData: data?.tenant
    });
    return (
      <div className="space-y-6">
        <PageBreadcrumb pageTitle="Member Projects" />


        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <div className="w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-amber-600 dark:text-amber-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Invalid Data Received
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                The server returned incomplete data. This may be because the backend API endpoint is not yet implemented or the tenant type is missing.
              </p>
              <div className="flex items-center justify-center space-x-3">
                <Button variant="outline" onClick={handleBack}>
                  Go Back
                </Button>
                <Button onClick={handleRefresh}>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Try Again
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const TenantIcon = data.tenant.tenant_type === 'team' ? Building2 : User;

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle="Member Projects" />

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >



        <Card>
          <CardContent className="space-y-6 px-4 ">
            {/* Header Section */}
            <div className="flex flex-col md:flex-row items-center justify-between p-3 border border-brand-100 bg-brand-50/20 dark:bg-brand-900/10 rounded-xl gap-6 md:gap-3">
              {/* Left: Member Info */}
              <div className="flex items-center gap-4 w-full md:w-auto">
                <div className="w-12 h-12 bg-white dark:bg-gray-800 border border-brand-100 dark:border-brand-800 rounded-full flex items-center justify-center shadow-sm shrink-0">
                  <TenantIcon className="w-6 h-6 text-brand-500" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <h1 className="text-lg font-bold text-brand-500 dark:text-white truncate">{data.tenant.name}</h1>
                    <Badge variant="outline" className={data.tenant.tenant_type === 'team' ? 'bg-purple-50 text-purple-600 border-purple-100' : 'bg-blue-50 text-blue-600 border-blue-100'}>
                      {data.tenant.tenant_type === 'team' ? 'Team' : 'Individual'}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[200px]">
                    {data.tenant.contact_email || 'No contact email'}
                  </p>
                </div>
              </div>

              {/* Middle: Integrated Stats */}
              <div className="hidden lg:flex items-center gap-8 px-8 border-x border-brand-100/30">
                <div className="text-center">
                  <p className="text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-0.5">Total</p>
                  <p className="text-lg font-bold text-brand-500 leading-none">{stats.total}</p>
                </div>
                <div className="text-center">
                  <p className="text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-0.5">Active</p>
                  <p className="text-lg font-bold text-green-500 leading-none">{stats.active}</p>
                </div>
                <div className="text-center">
                  <p className="text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-0.5">Done</p>
                  <p className="text-lg font-bold text-emerald-500 leading-none">{stats.completed}</p>
                </div>
              </div>

              {/* Right: Actions */}
              <div className="flex gap-2 w-full md:w-auto justify-end">
                <Button variant="outline" size="sm" onClick={handleBack} className="text-gray-500 hover:text-brand-500 border-gray-200 dark:border-gray-800 h-9 px-3 shrink-0">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
                <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading} className="text-brand-500 border-brand-200 bg-white hover:bg-brand-50 h-9 px-3 shrink-0">
                  <RefreshCw className={`w-3.5 h-3.5 mr-2 ${loading ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              </div>
            </div>

            {/* Content Section */}
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 px-1">
                <div className="space-y-1">
                  <h2 className="text-lg font-bold text-brand-500 flex items-center gap-2.5 leading-none">
                    Project Tracking
                    <Badge variant="secondary" className="bg-brand-50 text-brand-600 dark:bg-brand-900/20 border-none font-bold px-2 h-5 flex items-center justify-center text-[10px] min-w-[24px]">
                      {filteredProjects.length}
                    </Badge>
                  </h2>
                  <p className="text-gray-400 text-sm">Review member progress & deliverables</p>
                </div>

                <div className="relative w-full sm:w-80">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    placeholder="Search projects..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 h-10 border-gray-200 focus:border-brand-300 bg-white shadow-sm rounded-lg text-sm"
                  />
                </div>
              </div>

              <Card className="border-none shadow-none bg-white dark:bg-transparent overflow-hidden -mt-6">
                <CardContent className="p-0">
                  {filteredProjects.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-24 text-center">
                      <div className="w-20 h-20 bg-gray-50 dark:bg-gray-800/50 rounded-full flex items-center justify-center mb-4 border border-dashed border-gray-200">
                        <FolderOpen className="w-10 h-10 text-gray-300" />
                      </div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        {searchTerm ? "No matches found" : "No projects yet"}
                      </h3>
                      <p className="text-sm text-gray-500 max-w-sm mt-2">
                        {searchTerm
                          ? "We couldn't find any projects matching your search."
                          : "This member hasn't initiated any projects in this cohort yet."}
                      </p>
                      {searchTerm && (
                        <Button
                          variant="outline"
                          onClick={() => setSearchTerm('')}
                          className="mt-6 border-brand-200 text-brand-600 hover:bg-brand-50"
                        >
                          Clear Search
                        </Button>
                      )}
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <Table className="border-collapse border border-gray-100 dark:border-gray-800">
                        <TableHeader className="bg-brand-25 dark:bg-gray-900/40">
                          <TableRow className="border-b border-t border-gray-100 dark:border-gray-800 hover:bg-transparent">
                            <TableHead className="w-[80px] px-6 text-sm text-gray-400 border-r border-gray-100 dark:border-gray-800 h-12">ID</TableHead>
                            <TableHead className="min-w-[300px] px-6 text-sm text-gray-400 border-r border-gray-100 dark:border-gray-800 h-12">Project Details</TableHead>
                            <TableHead className="px-6 text-sm text-gray-400 border-r border-gray-100 dark:border-gray-800 h-12">Current Step</TableHead>
                            <TableHead className="px-6 text-sm text-gray-400 h-12">Timeline</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          <AnimatePresence mode="popLayout">
                            {filteredProjects.map((project, index) => (
                              <motion.tr
                                key={project.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.98 }}
                                transition={{
                                  duration: 0.3,
                                  delay: index * 0.04,
                                  ease: [0.23, 1, 0.32, 1]
                                }}
                                className="border-b border-gray-100 dark:border-gray-800 transition-colors cursor-pointer group hover:bg-brand-50/40"
                                onClick={() => handleViewProject(project.id)}
                              >
                                <TableCell className="px-6 text-sm text-gray-400 border-r border-gray-100 dark:border-gray-800 relative">
                                  {navigatingProjectId === project.id ? (
                                    <div className="flex items-center justify-center">
                                      <Loader2 className="w-4 h-4 animate-spin text-brand-500" />
                                    </div>
                                  ) : (
                                    ((page - 1) * pageSize + index + 1).toString().padStart(2, '0')
                                  )}
                                </TableCell>
                                <TableCell className="px-6 border-r border-gray-100 dark:border-gray-800">
                                  <div className="flex items-center justify-between gap-2">
                                    <div className="space-y-1 py-1">
                                      <h4 className="font-semibold text-sm text-brand-500 dark:text-gray-100 group-hover:text-brand-500 transition-colors">
                                        {project.name}
                                      </h4>
                                      {project.description && (
                                        <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-1 max-w-[400px]">
                                          {project.description}
                                        </p>
                                      )}
                                    </div>
                                    <ChevronRight className={`w-4 h-4 text-gray-300 transition-all duration-300 ${navigatingProjectId === project.id ? "opacity-0 translate-x-4" : "group-hover:text-brand-500 group-hover:translate-x-1"}`} />
                                  </div>
                                </TableCell>
                                <TableCell className="px-6 border-r border-gray-100 dark:border-gray-800">
                                  <Badge
                                    variant="outline"
                                    className={`${getStepColor(project.current_step)} h-6 px-4 font-semibold text-xs transition-all`}
                                  >
                                    <div className="flex items-center gap-1.5">
                                      {formatStepName(project.current_step)}
                                    </div>
                                  </Badge>
                                </TableCell>
                                <TableCell className="px-6">
                                  <div className="space-y-1 text-[10px]">
                                    <div className="flex items-center gap-1.5 text-gray-400">
                                      <Calendar className="w-3 h-3" />
                                      <span>Created {formatDate(project.created_at)}</span>
                                    </div>
                                    <div className="flex items-center gap-1.5 text-brand-500/70">
                                      <Clock className="w-3 h-3" />
                                      <span className="font-bold tracking-tight">Active {formatDate(project.updated_at)}</span>
                                    </div>
                                  </div>
                                </TableCell>

                              </motion.tr>
                            ))}
                          </AnimatePresence>
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Pagination Section */}
              {data.total_count > pageSize && (
                <div className="flex items-center justify-between mt-6 px-1">
                  <div className="flex flex-col space-y-1">
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                      Metadata
                    </p>
                    <p className="text-xs font-medium text-gray-500">
                      Page <span className="text-brand-500">{page}</span> of {Math.ceil(data.total_count / pageSize)}
                      <span className="mx-2 text-gray-300">•</span>
                      Showing <span className="text-gray-900 dark:text-white font-bold">{filteredProjects.length}</span> items
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => setPage((p) => p - 1)}
                      disabled={page === 1 || loading}
                      variant="outline"
                      size="sm"
                      className="h-9 border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 px-4"
                    >
                      Previous
                    </Button>
                    <Button
                      onClick={() => setPage((p) => p + 1)}
                      disabled={!data.has_next || loading}
                      variant="outline"
                      size="sm"
                      className="h-9 border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 px-4"
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
