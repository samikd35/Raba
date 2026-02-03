"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { teamService } from '@/lib/api/teamService';
import { tenantService } from '@/lib/api/tenantService';
import { Tenant, TenantCreateRequest } from '@/types/tenant';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import { 
  Building2, Users, TrendingUp, CreditCard, DollarSign, 
  Plus, Eye, Settings, Pause, Edit, Trash2, Search,
  Filter, Download, RefreshCw, AlertTriangle
} from 'lucide-react';

// Types
interface OrganizationStats {
  total_organizations: number;
  total_members: number;
  total_teams: number;
  total_credits_utilized: number;
  total_credits_remaining: number;
  average_team_size: number;
}

interface Organization {
  id: string;
  name: string;
  type?: 'prepay_org' | 'grant_org';
  country: string;
  created_date: string;
  total_members: number;
  total_teams: number;
  credits_utilized: number;
  credits_remaining: number;
  total_credits?: number;
  used_credits?: number;
  created_at?: string;
}

interface Filters {
  search: string;
  type: string;
  country: string;
}

export default function SuperAdminDashboard() {
  const router = useRouter();
  const { user, isAuthenticated, token } = useAuthStore();
  const [stats, setStats] = useState<OrganizationStats>({
    total_organizations: 0,
    total_members: 0,
    total_teams: 0,
    total_credits_utilized: 0,
    total_credits_remaining: 0,
    average_team_size: 0,
  });
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [filteredOrganizations, setFilteredOrganizations] = useState<Organization[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [filteredTenants, setFilteredTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateTenantForm, setShowCreateTenantForm] = useState(false);
  const [creatingTenant, setCreatingTenant] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const [deletingTenantId, setDeletingTenantId] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  
  // Filters
  const [orgFilters, setOrgFilters] = useState<Filters>({
    search: '',
    type: 'all',
    country: 'all'
  });
  
  const [tenantFilters, setTenantFilters] = useState({
    search: '',
    type: 'all'
  });

  const [tenantForm, setTenantForm] = useState({
    name: '',
    tenant_type: 'individual',
    description: '',
    website: '',
    industry: '',
    size: 'startup',
    country: ''
  });

  // Memoized data fetching
  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [summaryData, orgs] = await Promise.all([
        organizationService.getOrganizationSummary(),
        organizationService.fetchOrganizations()
      ]);

      const orgRows: Organization[] = orgs.map((o) => {
        const creditsUtilized = Number(o.used_credits || 0);
        const creditsRemaining = Number(o.total_credits || 0) - creditsUtilized;
        const createdDate = o.created_at ? new Date(o.created_at).toISOString().slice(0, 10) : new Date().toISOString().slice(0, 10);
        
        return {
          id: o.id,
          name: o.name,
          type: o.type || 'grant_org',
          country: o.country || 'Unknown',
          created_date: createdDate,
          total_members: Number(o.total_members || 0),
          total_teams: Number(o.total_teams || 0),
          credits_utilized: creditsUtilized,
          credits_remaining: creditsRemaining > 0 ? creditsRemaining : 0,
        } as Organization;
      });

      const averageTeamSize = summaryData.total_teams > 0 
        ? Number((summaryData.total_members / summaryData.total_teams).toFixed(1)) 
        : 0;

      setStats({
        total_organizations: summaryData.total_organizations,
        total_members: summaryData.total_members,
        total_teams: summaryData.total_teams,
        total_credits_utilized: summaryData.total_credits_used,
        total_credits_remaining: summaryData.total_credits_allocated - summaryData.total_credits_used,
        average_team_size: averageTeamSize,
      });

      setOrganizations(orgRows);
      setFilteredOrganizations(orgRows);
    } catch (err: any) {
      console.error('Dashboard data fetch error:', err);
      const errorMessage = err.message || 'Failed to fetch dashboard data';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTenants = useCallback(async () => {
    try {
      const list = await tenantService.listTenants();
      const tenantsList = list.tenants || [];
      setTenants(tenantsList);
      setFilteredTenants(tenantsList);
    } catch (e: any) {
      console.error('Tenants fetch error:', e);
      if (e?.message?.includes('401') || e?.message?.includes('Unauthorized') || e?.message?.includes('No authentication token')) {
        toast.error('Authentication failed. Please log in again.');
        router.push('/signin');
      }
    }
  }, [router]);

  useEffect(() => {
    // Authentication check (uncomment when ready)
    // if (!isAuthenticated || !token) {
    //   router.push('/signin');
    //   return;
    // }
    // if (!user?.roles?.includes('super_admin')) {
    //   router.push('/unauthorized');
    //   return;
    // }
    
    fetchDashboardData();
    fetchTenants();
  }, [fetchDashboardData, fetchTenants, isAuthenticated, token, user, router]);

  // Filter organizations
  useEffect(() => {
    let filtered = organizations;
    
    if (orgFilters.search) {
      const searchLower = orgFilters.search.toLowerCase();
      filtered = filtered.filter(org => 
        org.name.toLowerCase().includes(searchLower) ||
        org.country.toLowerCase().includes(searchLower)
      );
    }
    
    if (orgFilters.type !== 'all') {
      filtered = filtered.filter(org => org.type === orgFilters.type);
    }
    
    if (orgFilters.country !== 'all') {
      filtered = filtered.filter(org => org.country === orgFilters.country);
    }
    
    setFilteredOrganizations(filtered);
  }, [organizations, orgFilters]);

  // Filter tenants
  useEffect(() => {
    let filtered = tenants;
    
    if (tenantFilters.search) {
      const searchLower = tenantFilters.search.toLowerCase();
      filtered = filtered.filter(tenant => 
        tenant.name.toLowerCase().includes(searchLower) ||
        tenant.description?.toLowerCase().includes(searchLower) ||
        tenant.industry?.toLowerCase().includes(searchLower)
      );
    }
    
    if (tenantFilters.type !== 'all') {
      filtered = filtered.filter(tenant => tenant.tenant_type === tenantFilters.type);
    }
    
    setFilteredTenants(filtered);
  }, [tenants, tenantFilters]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchDashboardData(), fetchTenants()]);
    setRefreshing(false);
    toast.success('Data refreshed successfully');
  };

  const handleTenantInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setTenantForm(prev => ({ ...prev, [name]: value }));
  };

  const handleCreateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantForm.name.trim()) {
      toast.error('Tenant name is required');
      return;
    }
    
    setCreatingTenant(true);
    try {
      const tenantData: TenantCreateRequest = {
        name: tenantForm.name.trim(),
        tenant_type: tenantForm.tenant_type as 'individual' | 'company',
        description: tenantForm.description.trim(),
        website: tenantForm.website.trim(),
        industry: tenantForm.industry.trim(),
        size: tenantForm.size,
        country: tenantForm.country.trim()
      };

      const created = await tenantService.createTenant(tenantData);
      setTenants(prev => [created, ...prev]);
      toast.success(`Tenant "${created.name}" created successfully`);
      resetTenantForm();
    } catch (err: any) {
      console.error('Create tenant failed', err);
      handleAuthError(err);
    } finally {
      setCreatingTenant(false);
    }
  };

  const handleUpdateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantForm.name.trim() || !editingTenant) {
      toast.error('Tenant name is required');
      return;
    }
    
    setCreatingTenant(true);
    try {
      const updated = await tenantService.updateTenant(editingTenant.id, {
        name: tenantForm.name.trim(),
        description: tenantForm.description.trim(),
        website: tenantForm.website.trim(),
        industry: tenantForm.industry.trim(),
        size: tenantForm.size,
        country: tenantForm.country.trim()
      });

      setTenants(prev => prev.map(t => t.id === updated.id ? updated : t));
      toast.success(`Tenant "${updated.name}" updated successfully`);
      resetTenantForm();
    } catch (err: any) {
      console.error('Update tenant failed', err);
      handleAuthError(err);
    } finally {
      setCreatingTenant(false);
    }
  };

  const handleDeleteTenant = async (tenantId: string) => {
    setDeletingTenantId(tenantId);
    try {
      await tenantService.deleteTenant(tenantId);
      setTenants(prev => prev.filter(t => t.id !== tenantId));
      toast.success('Tenant deleted successfully');
    } catch (err: any) {
      console.error('Delete tenant failed', err);
      handleAuthError(err);
    } finally {
      setDeletingTenantId(null);
    }
  };

  const handleAuthError = (err: any) => {
    if (err?.message?.includes('401') || err?.message?.includes('Unauthorized') || err?.message?.includes('No authentication token')) {
      toast.error('Authentication failed. Please log in again.');
      router.push('/signin');
    } else {
      toast.error(err?.message || 'Operation failed');
    }
  };

  const resetTenantForm = () => {
    setTenantForm({ 
      name: '', 
      tenant_type: 'individual', 
      description: '', 
      website: '', 
      industry: '', 
      size: 'startup', 
      country: '' 
    });
    setEditingTenant(null);
    setShowCreateTenantForm(false);
  };

  const handleInviteOrganization = () => {
    router.push('/admin/invite');
  };

  const confirmDelete = (tenantId: string, tenantName: string) => {
    if (window.confirm(`Are you sure you want to delete tenant "${tenantName}"? This action cannot be undone.`)) {
      handleDeleteTenant(tenantId);
    }
  };

  const exportData = (type: 'organizations' | 'tenants') => {
    toast.info(`Export ${type} feature coming soon`);
  };

  // Get unique countries for filter
  const uniqueCountries = [...new Set(organizations.map(org => org.country))].filter(Boolean);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading dashboard data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto mt-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-medium text-red-800 dark:text-red-200">Error loading dashboard</h3>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">{error}</p>
              <div className="mt-4 flex space-x-3">
                <button
                  onClick={fetchDashboardData}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium"
                >
                  Try Again
                </button>
                <button
                  onClick={handleRefresh}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-sm font-medium"
                >
                  Refresh All
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Super Admin Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Overview of all organizations, members, and credit usage
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <button 
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 flex items-center space-x-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button 
            onClick={handleInviteOrganization}
            className="bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 font-medium"
          >
            <Plus className="w-4 h-4" />
            <span>Invite Organization</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 sm:gap-6">
        {[
          { label: 'Organizations', value: stats.total_organizations, icon: Building2, desc: 'Active organizations' },
          { label: 'Total Members', value: stats.total_members, icon: Users, desc: 'Individual + team members' },
          { label: 'Teams', value: stats.total_teams, icon: TrendingUp, desc: `Avg size: ${stats.average_team_size}` },
          { label: 'Credits Used', value: stats.total_credits_utilized.toLocaleString(), icon: CreditCard, desc: 'Total utilized' },
          { label: 'Credits Remaining', value: stats.total_credits_remaining.toLocaleString(), icon: DollarSign, desc: 'Available credits' },
        ].map((stat, index) => (
          <div key={index} className="bg-white dark:bg-gray-800 p-4 sm:p-6 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">{stat.label}</h3>
              <stat.icon className="w-5 h-5 text-gray-400" />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{stat.desc}</p>
          </div>
        ))}
      </div>

      {/* Organizations Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Organizations Overview</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {filteredOrganizations.length} of {organizations.length} organizations
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex gap-2">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search organizations..."
                    value={orgFilters.search}
                    onChange={(e) => setOrgFilters(prev => ({ ...prev, search: e.target.value }))}
                    className="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
                  />
                </div>
                <select
                  value={orgFilters.type}
                  onChange={(e) => setOrgFilters(prev => ({ ...prev, type: e.target.value }))}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
                >
                  <option value="all">All Types</option>
                  <option value="prepay_org">Prepay</option>
                  <option value="grant_org">Grant</option>
                </select>
                {uniqueCountries.length > 0 && (
                  <select
                    value={orgFilters.country}
                    onChange={(e) => setOrgFilters(prev => ({ ...prev, country: e.target.value }))}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
                  >
                    <option value="all">All Countries</option>
                    {uniqueCountries.map(country => (
                      <option key={country} value={country}>{country}</option>
                    ))}
                  </select>
                )}
              </div>
              <button 
                onClick={() => exportData('organizations')}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2 text-sm"
              >
                <Download className="w-4 h-4" />
                <span>Export</span>
              </button>
            </div>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                {['Organization', 'Type', 'Country', 'Created', 'Members', 'Teams', 'Credits Used', 'Credits Remaining', 'Actions'].map((header) => (
                  <th key={header} className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white text-sm">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredOrganizations.map((org) => (
                <tr key={org.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-medium text-gray-900 dark:text-white">{org.name}</div>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      org.type === 'prepay_org' 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                        : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                    }`}>
                      {org.type === 'prepay_org' ? 'Prepay' : 'Grant'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{org.country}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                    {new Date(org.created_date).toLocaleDateString()}
                  </td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{org.total_members}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{org.total_teams}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{org.credits_utilized.toLocaleString()}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                    <span className={org.credits_remaining < 1000 ? 'text-orange-600 dark:text-orange-400' : ''}>
                      {org.credits_remaining.toLocaleString()}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center space-x-1">
                      <button 
                        className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-600 rounded text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button 
                        className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-600 rounded text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                        title="Settings"
                      >
                        <Settings className="w-4 h-4" />
                      </button>
                      <button 
                        className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-600 rounded text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                        title="Suspend"
                      >
                        <Pause className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {filteredOrganizations.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 dark:text-gray-500 mb-2">
                <Filter className="w-12 h-12 mx-auto" />
              </div>
              <p className="text-gray-500 dark:text-gray-400">No organizations found matching your filters</p>
              {(orgFilters.search || orgFilters.type !== 'all' || orgFilters.country !== 'all') && (
                <button
                  onClick={() => setOrgFilters({ search: '', type: 'all', country: 'all' })}
                  className="mt-2 text-brand-500 hover:text-brand-600 text-sm font-medium"
                >
                  Clear filters
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Tenants Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Tenants Overview</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {filteredTenants.length} of {tenants.length} tenants
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex gap-2">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search tenants..."
                    value={tenantFilters.search}
                    onChange={(e) => setTenantFilters(prev => ({ ...prev, search: e.target.value }))}
                    className="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
                  />
                </div>
                <select
                  value={tenantFilters.type}
                  onChange={(e) => setTenantFilters(prev => ({ ...prev, type: e.target.value }))}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
                >
                  <option value="all">All Types</option>
                  <option value="individual">Individual</option>
                  <option value="company">Company</option>
                </select>
              </div>
              <button 
                onClick={() => exportData('tenants')}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2 text-sm"
              >
                <Download className="w-4 h-4" />
                <span>Export</span>
              </button>
              <button 
                onClick={() => {
                  setEditingTenant(null);
                  resetTenantForm();
                  setShowCreateTenantForm(true);
                }}
                className="bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 text-sm font-medium"
              >
                <Plus className="w-4 h-4" />
                <span>Create Tenant</span>
              </button>
            </div>
          </div>
        </div>
        
        {showCreateTenantForm && (
          <div className="p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <h3 className="text-md font-semibold text-gray-900 dark:text-white mb-4">
              {editingTenant ? 'Edit Tenant' : 'Create New Tenant'}
            </h3>
            <form onSubmit={editingTenant ? handleUpdateTenant : handleCreateTenant} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Tenant Name <span className="text-red-500">*</span>
                </label>
                <input 
                  name="name" 
                  value={tenantForm.name} 
                  onChange={handleTenantInputChange} 
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-brand-500 focus:border-transparent" 
                  required
                  placeholder="Enter tenant name"
                />
              </div>
              
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Type</label>
                <select 
                  name="tenant_type" 
                  value={tenantForm.tenant_type} 
                  onChange={handleTenantInputChange} 
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                >
                  <option value="individual">Individual</option>
                  <option value="company">Company</option>
                </select>
              </div>
              
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Country</label>
                <input 
                  name="country" 
                  value={tenantForm.country} 
                  onChange={handleTenantInputChange} 
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-brand-500 focus:border-transparent" 
                  placeholder="Country"
                />
              </div>
              
              <div className="space-y-2 md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Description</label>
                <input 
                  name="description" 
                  value={tenantForm.description} 
                  onChange={handleTenantInputChange} 
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-brand-500 focus:border-transparent" 
                  placeholder="Brief description"
                />
              </div>
              
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Website</label>
                <input 
                  name="website" 
                  value={tenantForm.website} 
                  onChange={handleTenantInputChange} 
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-brand-500 focus:border-transparent" 
                  placeholder="https://example.com"
                />
              </div>
              
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Industry</label>
                <input 
                  name="industry" 
                  value={tenantForm.industry} 
                  onChange={handleTenantInputChange} 
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-brand-500 focus:border-transparent" 
                  placeholder="Industry"
                />
              </div>
              
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Size</label>
                <select 
                  name="size" 
                  value={tenantForm.size} 
                  onChange={handleTenantInputChange} 
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                >
                  <option value="startup">Startup</option>
                  <option value="small">Small</option>
                  <option value="medium">Medium</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
              
              <div className="flex items-center space-x-3 md:col-span-3 pt-2">
                <button 
                  type="submit" 
                  disabled={creatingTenant} 
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg flex items-center space-x-2 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {creatingTenant ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>{editingTenant ? 'Updating...' : 'Creating...'}</span>
                    </>
                  ) : (
                    <>
                      {editingTenant ? (
                        <>
                          <Edit className="w-4 h-4" />
                          <span>Update Tenant</span>
                        </>
                      ) : (
                        <>
                          <Plus className="w-4 h-4" />
                          <span>Create Tenant</span>
                        </>
                      )}
                    </>
                  )}
                </button>
                <button 
                  type="button"
                  onClick={resetTenantForm}
                  className="px-4 py-2 bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-700 dark:text-gray-300 rounded-lg font-medium"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                {['Tenant', 'Type', 'Industry', 'Size', 'Country', 'Website', 'Created', 'Actions'].map((header) => (
                  <th key={header} className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white text-sm">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredTenants.map((tenant) => (
                <tr key={tenant.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-medium text-gray-900 dark:text-white">{tenant.name}</div>
                    {tenant.description && (
                      <div className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">{tenant.description}</div>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      tenant.tenant_type === 'individual' 
                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' 
                        : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                    }`}>
                      {tenant.tenant_type}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{tenant.industry || '-'}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400 capitalize">{tenant.size || '-'}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{tenant.country || '-'}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                    {tenant.website ? (
                      <a 
                        href={tenant.website} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="text-brand-500 hover:text-brand-600 hover:underline flex items-center space-x-1"
                      >
                        <span>Visit</span>
                      </a>
                    ) : '-'}
                  </td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                    {tenant.created_at ? new Date(tenant.created_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center space-x-1">
                      <button 
                        onClick={() => handleEditTenant(tenant)}
                        className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-600 rounded text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                        title="Edit Tenant"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={() => confirmDelete(tenant.id, tenant.name)}
                        disabled={deletingTenantId === tenant.id}
                        className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-600 rounded text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 transition-colors disabled:opacity-50"
                        title="Delete Tenant"
                      >
                        {deletingTenantId === tenant.id ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600 dark:border-red-400"></div>
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {filteredTenants.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 dark:text-gray-500 mb-2">
                <Users className="w-12 h-12 mx-auto" />
              </div>
              <p className="text-gray-500 dark:text-gray-400">
                {tenants.length === 0 ? 'No tenants found' : 'No tenants found matching your filters'}
              </p>
              {(tenantFilters.search || tenantFilters.type !== 'all') && tenants.length > 0 && (
                <button
                  onClick={() => setTenantFilters({ search: '', type: 'all' })}
                  className="mt-2 text-brand-500 hover:text-brand-600 text-sm font-medium"
                >
                  Clear filters
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}