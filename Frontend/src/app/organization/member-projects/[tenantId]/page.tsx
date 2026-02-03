"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { TenantProjectsResponse, ProjectSummary, TenantInfo } from '@/types/organization';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { useAuthStore } from '@/stores/authStore';
import { toast } from 'sonner';
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
} from 'lucide-react';
import { motion } from 'framer-motion';

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
  const [page, setPage] = useState(1);
  const pageSize = 20;

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
  }, [organizationId, tenantId, page]);

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
    // Navigate to project detail page (Phase 4+)
    router.push(`/organization/member-projects/project/${projectId}`);
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
      project_setup: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
      vpc_composition: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      field_prep: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
      data_collection: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      analysis: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
      completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    };
    return stepColors[step] || 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
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
      <div className="container mx-auto px-4 py-8 space-y-6">
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
      <div className="container mx-auto px-4 py-8">
        <Button variant="ghost" onClick={handleBack} className="mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        
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
      <div className="container mx-auto px-4 py-8">
        <Button variant="ghost" onClick={handleBack} className="mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        
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
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="icon" onClick={handleBack}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center">
              <TenantIcon className="w-6 h-6 text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{data.tenant.name}</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 flex items-center space-x-2">
                <Badge className={data.tenant.tenant_type === 'team' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}>
                  {data.tenant.tenant_type === 'team' ? 'Team' : 'Individual'}
                </Badge>
                {data.tenant.contact_email && <span>• {data.tenant.contact_email}</span>}
              </p>
            </div>
          </div>
        </div>
        
        <Button variant="outline" onClick={handleRefresh} disabled={loading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <FolderOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Projects</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                <GitBranch className="w-6 h-6 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.active}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Active Projects</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg flex items-center justify-center">
                <Calendar className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.completed}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Completed</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <FolderOpen className="w-5 h-5" />
                <span>Projects ({filteredProjects.length})</span>
              </CardTitle>
              <CardDescription>Track and Review all projects for this member</CardDescription>
            </div>
            
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search projects..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {filteredProjects.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <FolderOpen className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                {searchTerm ? 'No matching projects found' : 'No projects yet'}
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                {searchTerm 
                  ? 'Try adjusting your search criteria.' 
                  : 'Projects will appear here once this member creates their first project.'}
              </p>
              {searchTerm && (
                <Button variant="outline" onClick={() => setSearchTerm('')}>
                  Clear Search
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredProjects.map((project, index) => (
                <motion.div
                  key={project.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                >
                  <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer group" onClick={() => handleViewProject(project.id)}>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <CardTitle className="text-lg truncate group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                            {project.name}
                          </CardTitle>
                          <Badge className={`${getStepColor(project.current_step)} mt-2`}>
                            {formatStepName(project.current_step)}
                          </Badge>
                        </div>
                        <Button variant="ghost" size="icon" className="opacity-0 group-hover:opacity-100 transition-opacity">
                          <Eye className="w-4 h-4" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {project.description && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                          {project.description}
                        </p>
                      )}
                      
                      <div className="space-y-2 text-xs text-gray-500 dark:text-gray-400">
                        <div className="flex items-center space-x-2">
                          <Calendar className="w-3 h-3" />
                          <span>Created: {formatDate(project.created_at)}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Clock className="w-3 h-3" />
                          <span>Updated: {formatDate(project.updated_at)}</span>
                        </div>
                      </div>

                      <Button className="w-full" size="sm" variant="outline">
                        <Eye className="w-4 h-4 mr-2" />
                        View Details
                      </Button>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {data.total_count > pageSize && (
            <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Page {page} of {Math.ceil(data.total_count / pageSize)} • Total: {data.total_count} projects
              </p>
              <div className="flex items-center space-x-2">
                <Button onClick={() => setPage((p) => p - 1)} disabled={page === 1 || loading} variant="outline" size="sm">
                  Previous
                </Button>
                <Button onClick={() => setPage((p) => p + 1)} disabled={!data.has_next || loading} variant="outline" size="sm">
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
