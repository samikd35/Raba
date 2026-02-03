"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { CreditRequestService, CreditRequest } from '@/lib/api/creditRequestService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import { 
  Building2, 
  Users, 
  CreditCard, 
  UserCheck, 
  Plus, 
  AlertCircle, 
  TrendingUp, 
  X, 
  Mail, 
  ArrowLeft,
  RefreshCw,
  Search,
  Filter,
  MoreVertical,
  Crown,
  Target,
  Eye,
  Settings,
  Download,
  BarChart3,
  Shield,
  Coins,
  Loader2,
  Trash2,
  AlertTriangle
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

interface Team {
  team_id: string;
  team_name: string;
  member_count: number;
  leader_name: string;
  leader_email: string;
  credits: {
    total: number;
    used: number;
    remaining: number;
  };
  created_at?: string;
  status?: 'active' | 'inactive';
}

interface TeamMember {
  user_id: string;
  user_email: string;
  user_name: string;
  role: string;
  status: string;
  credits_allocated: number;
  credits_used: number;
  last_active?: string;
}

interface TeamsData {
  teams: Team[];
}

interface TeamCreditAllocationState {
  isOpen: boolean;
  team: Team | null;
  amount: string;
  isAllocating: boolean;
}

export default function OrganizationTeamsPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const currentWorkspaceTenantId = user?.tenant_id;
  
  const organizationId = currentWorkspaceTenantId;
  
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('all');
  const [creditAllocation, setCreditAllocation] = useState<TeamCreditAllocationState>({
    isOpen: false,
    team: null,
    amount: "",
    isAllocating: false,
  });
  
  // Delete team state
  const [deleteTeamState, setDeleteTeamState] = useState<{
    isOpen: boolean;
    team: Team | null;
    isDeleting: boolean;
  }>({
    isOpen: false,
    team: null,
    isDeleting: false,
  });

  // Credit requests state
  const [creditRequests, setCreditRequests] = useState<CreditRequest[]>([]);
  const [pendingRequestsCount, setPendingRequestsCount] = useState(0);

  const fetchTeamsData = useCallback(async () => {
    if (!organizationId) {
      setError('No organization ID available. Please select a workspace.');
      setLoading(false);
      return;
    }

    if (!isAuthenticated) {
      setError('Authentication required. Please sign in.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('🏢 Fetching teams data for organization ID:', organizationId);
      }
      
      const teamsData = await organizationService.getOrganizationTeams(organizationId);
      
      const transformedTeams: Team[] = teamsData.teams?.map(team => ({
        team_id: team.team_id,
        team_name: team.team_name,
        member_count: team.members_count || team.member_count || 0,
        leader_name: team.team_leader?.full_name || team.leader_name || 'No leader assigned',
        leader_email: team.team_leader?.email || team.leader_email || '',
        credits: {
          total: team.credit_pool?.total || team.credits?.total || 0,
          used: team.credit_pool?.used || team.credits?.used || 0,
          remaining: team.credit_pool?.remaining || team.credits?.remaining || 0,
        },
        status: 'active',
        created_at: team.created_at
      })) || [];
      
      setTeams(transformedTeams);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Teams data loaded successfully');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load teams data';
      
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error fetching teams data:', error);
      }
      
      if (errorMessage.includes('401') || errorMessage.includes('Unauthorized')) {
        setError('Authentication expired. Please sign in again.');
        toast.error('Session expired. Please sign in again.');
        setTimeout(() => router.push('/signin'), 2000);
        return;
      }
      
      if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
        setError('Access denied. You may not have permission to view this organization.');
        toast.error('Access denied to organization data.');
        return;
      }
      
      if (errorMessage.includes('404') || errorMessage.includes('Not Found')) {
        setError('Organization not found. It may have been deleted or you may not have access.');
        toast.error('Organization not found.');
        return;
      }
      
      setError(errorMessage);
      toast.error('Failed to load teams data');
      
      if (retryCount < 3 && (errorMessage.includes('Network') || errorMessage.includes('fetch'))) {
        const retryDelay = Math.pow(2, retryCount) * 1000;
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchTeamsData();
        }, retryDelay);
      }
    } finally {
      setLoading(false);
    }
  }, [organizationId, isAuthenticated, retryCount, router]);

  useEffect(() => {
    if (!isAuthenticated) {
      if (process.env.NODE_ENV === 'development') {
        console.log('🔒 User not authenticated, redirecting to signin');
      }
      router.push('/signin');
      return;
    }

    if (!organizationId) {
      if (process.env.NODE_ENV === 'development') {
        console.log('🏢 No organization ID available, redirecting to workspace selection');
      }
      router.push('/choose-workspace');
      return;
    }

    fetchTeamsData();
    
    // Fetch credit requests
    const fetchCreditRequests = async () => {
      if (!organizationId) {
        console.log('🔍 DEBUG Teams: No organizationId for credit requests');
        return;
      }
      console.log('🔍 DEBUG Teams: Fetching credit requests for org:', organizationId);
      try {
        const response = await CreditRequestService.getOrganizationCreditRequests(organizationId);
        console.log('🔍 DEBUG Teams: Credit requests response:', response);
        setCreditRequests(response.requests || []);
        setPendingRequestsCount(response.pending_count || 0);
      } catch (err) {
        console.error("Failed to load credit requests:", err);
      }
    };
    fetchCreditRequests();
  }, [isAuthenticated, organizationId, fetchTeamsData, router]);

  // Helper to get team credit request status
  const getTeamCreditRequestStatus = useCallback((teamId: string) => {
    const teamRequests = creditRequests.filter(r => r.team_id === teamId);
    const pendingRequests = teamRequests.filter(r => r.status === 'pending');
    const totalPendingAmount = pendingRequests.reduce((sum, r) => sum + r.requested_amount, 0);
    
    return {
      hasPendingRequests: pendingRequests.length > 0,
      pendingCount: pendingRequests.length,
      totalPendingAmount,
      totalRequests: teamRequests.length,
    };
  }, [creditRequests]);

  // Filter and sort teams
  const { filteredTeams, sortedTeams } = useMemo(() => {
    const filtered = teams.filter(team => {
      const matchesSearch = 
        team.team_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        team.leader_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        team.leader_email.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesTab = activeTab === 'all' || team.status === activeTab;
      
      return matchesSearch && matchesTab;
    });

    const sorted = [...filtered].sort((a, b) => 
      b.credits.used - a.credits.used
    );

    return { filteredTeams: filtered, sortedTeams: sorted };
  }, [teams, searchTerm, activeTab]);

  // Statistics with enhanced metrics
  const stats = useMemo(() => {
    const totalTeams = teams.length;
    const totalMembers = teams.reduce((total, team) => total + team.member_count, 0);
    const totalCredits = teams.reduce((total, team) => total + team.credits.total, 0);
    const totalUsedCredits = teams.reduce((total, team) => total + team.credits.used, 0);
    const totalRemainingCredits = teams.reduce((total, team) => total + team.credits.remaining, 0);
    const avgTeamSize = totalTeams > 0 ? totalMembers / totalTeams : 0;
    const overallUsage = totalCredits > 0 ? (totalUsedCredits / totalCredits) * 100 : 0;

    return {
      totalTeams,
      totalMembers,
      totalCredits,
      totalUsedCredits,
      totalRemainingCredits,
      avgTeamSize,
      overallUsage: Math.round(overallUsage)
    };
  }, [teams]);

  const handleBack = useCallback(() => {
    router.push('/organization');
  }, [router]);

  const handleRefresh = useCallback(() => {
    fetchTeamsData();
    toast.success('Teams data refreshed');
  }, [fetchTeamsData]);

  const handleRetry = useCallback(() => {
    setRetryCount(0);
    fetchTeamsData();
  }, [fetchTeamsData]);

  const handleBackToWorkspaces = useCallback(() => {
    router.push('/choose-workspace');
  }, [router]);

  const handleViewDetails = useCallback(async (team: Team) => {
    setSelectedTeam(team);
    setLoadingMembers(true);
    try {
      const membersData = await organizationService.getOrganizationMembers(organizationId);
      const teamSpecificMembers = membersData.members
        ?.filter(m => m.team_id === team.team_id)
        .map(m => ({
          user_id: m.user_id,
          user_email: m.email || '',
          user_name: m.name || m.user_name,
          role: m.role,
          status: m.status,
          credits_allocated: m.credits_allocated || 0,
          credits_used: m.credits_used || 0,
          last_active: m.last_active
        })) || [];
      setTeamMembers(teamSpecificMembers);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch team members';
      if (process.env.NODE_ENV === 'development') {
        console.error('Error fetching team members:', error);
      }
      toast.error(errorMessage);
    } finally {
      setLoadingMembers(false);
    }
  }, [organizationId]);

  const handleCloseModal = useCallback(() => {
    setSelectedTeam(null);
    setTeamMembers([]);
  }, []);

  const handleManageCredits = useCallback((team: Team) => {
    setCreditAllocation({
      isOpen: true,
      team,
      amount: "",
      isAllocating: false,
    });
  }, []);

  const handleAllocateCredits = useCallback(async () => {
    if (!organizationId || !creditAllocation.team) {
      toast.error("No organization or team selected");
      return;
    }

    const amount = parseInt(creditAllocation.amount, 10);
    if (isNaN(amount) || amount < 1) {
      toast.error("Please enter a valid credit amount (minimum 1)");
      return;
    }

    try {
      setCreditAllocation((prev) => ({ ...prev, isAllocating: true }));
      
      const result = await organizationService.allocateCreditsToMember(
        organizationId,
        creditAllocation.team.team_id,
        "team",
        amount
      );

      // Show success message with email notification status
      let successMessage = `Successfully allocated ${amount} credits to ${creditAllocation.team.team_name}`;
      if (result.email_sent) {
        successMessage += ` - Notification sent to ${result.email_recipient}`;
      }
      toast.success(successMessage);

      // Close modal and refresh data
      setCreditAllocation({
        isOpen: false,
        team: null,
        amount: "",
        isAllocating: false,
      });
      fetchTeamsData();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to allocate credits";
      if (process.env.NODE_ENV === "development") {
        console.error("Error allocating credits:", error);
      }
      toast.error(errorMessage);
    } finally {
      setCreditAllocation((prev) => ({ ...prev, isAllocating: false }));
    }
  }, [organizationId, creditAllocation.team, creditAllocation.amount, fetchTeamsData]);

  const handleExportData = useCallback(() => {
    toast.success('Exporting teams data...');
  }, []);

  // Delete team handlers
  const handleDeleteTeamClick = useCallback((team: Team) => {
    setDeleteTeamState({
      isOpen: true,
      team,
      isDeleting: false,
    });
  }, []);

  const handleDeleteTeamConfirm = useCallback(async () => {
    if (!organizationId || !deleteTeamState.team) {
      toast.error("No organization or team selected");
      return;
    }

    try {
      setDeleteTeamState((prev) => ({ ...prev, isDeleting: true }));
      
      const result = await organizationService.deleteTeam(
        organizationId,
        deleteTeamState.team.team_id
      );

      toast.success(result.message || `Team "${deleteTeamState.team.team_name}" has been deleted`);
      
      if (result.credits_returned_to_org > 0) {
        toast.success(`${result.credits_returned_to_org} credits returned to organization`);
      }

      // Close modal and refresh data
      setDeleteTeamState({
        isOpen: false,
        team: null,
        isDeleting: false,
      });
      fetchTeamsData();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to delete team";
      if (process.env.NODE_ENV === "development") {
        console.error("Error deleting team:", error);
      }
      toast.error(errorMessage);
    } finally {
      setDeleteTeamState((prev) => ({ ...prev, isDeleting: false }));
    }
  }, [organizationId, deleteTeamState.team, fetchTeamsData]);

  const handleDeleteTeamCancel = useCallback(() => {
    setDeleteTeamState({
      isOpen: false,
      team: null,
      isDeleting: false,
    });
  }, []);

  const getRoleColor = useCallback((role: string) => {
    switch (role?.toLowerCase()) {
      case 'owner':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 border-purple-200';
      case 'admin':
        return 'bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-200 border-brand-200';
      case 'team_leader':
        return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200 border-amber-200';
      case 'member':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200 border-gray-200';
    }
  }, []);

  const getStatusColor = useCallback((status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 border-green-200';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 border-yellow-200';
      case 'inactive':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200 border-gray-200';
    }
  }, []);

  const getCreditUsagePercentage = useCallback((used: number, total: number) => {
    return total > 0 ? Math.round((used / total) * 100) : 0;
  }, []);

  const getUsageColor = useCallback((percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 75) return 'bg-yellow-500';
    return 'bg-brand-500';
  }, []);

  const getUsageVariant = useCallback((percentage: number) => {
    if (percentage >= 90) return 'destructive';
    if (percentage >= 75) return 'default';
    return 'default';
  }, []);

  // Enhanced loading state
  if (loading) {
    return (
      <div className="space-y-6 animate-in fade-in duration-500">
        {/* Enhanced Header Skeleton */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center space-x-4">
            <Skeleton className="h-10 w-10 rounded-lg" />
            <div className="space-y-2">
              <Skeleton className="h-8 w-64 rounded-md" />
              <Skeleton className="h-4 w-96 rounded-md" />
            </div>
          </div>
          <div className="flex space-x-3">
            <Skeleton className="h-10 w-24 rounded-lg" />
            <Skeleton className="h-10 w-40 rounded-lg" />
          </div>
        </div>

        {/* Enhanced Stats Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          {[...Array(5)].map((_, i) => (
            <Card key={i} className="overflow-hidden">
              <CardContent className="p-6">
                <div className="flex items-center space-x-4">
                  <Skeleton className="h-12 w-12 rounded-xl" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-6 w-16 rounded-md" />
                    <Skeleton className="h-4 w-24 rounded-md" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Enhanced Teams Grid Skeleton */}
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="space-y-2">
                <Skeleton className="h-6 w-48 rounded-md" />
                <Skeleton className="h-4 w-96 rounded-md" />
              </div>
              <Skeleton className="h-10 w-64 rounded-lg" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <Card key={i} className="overflow-hidden">
                  <CardHeader className="pb-4">
                    <Skeleton className="h-6 w-3/4 rounded-md" />
                    <Skeleton className="h-4 w-full rounded-md mt-2" />
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Skeleton className="h-16 w-full rounded-lg" />
                    <div className="grid grid-cols-2 gap-4">
                      <Skeleton className="h-12 rounded-lg" />
                      <Skeleton className="h-12 rounded-lg" />
                    </div>
                    <Skeleton className="h-2 w-full rounded-full" />
                    <div className="flex space-x-2">
                      <Skeleton className="h-9 flex-1 rounded-lg" />
                      <Skeleton className="h-9 flex-1 rounded-lg" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Enhanced error state
  if (error) {
    return (
      <div className="space-y-6 animate-in fade-in duration-500">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="icon" onClick={handleBack}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Organization Teams
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage teams and their credit allocations
            </p>
          </div>
        </div>

        <Card className="border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-900/20">
          <CardContent className="pt-6">
            <div className="flex items-start space-x-4">
              <div className="w-12 h-12 bg-red-100 dark:bg-red-900 rounded-lg flex items-center justify-center flex-shrink-0">
                <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-red-800 dark:text-red-200 text-lg">
                  Unable to Load Teams
                </h3>
                <p className="text-red-700 dark:text-red-300 mt-2">
                  {error}
                </p>
                <div className="flex flex-wrap gap-3 mt-6">
                  <Button onClick={handleRetry} className="flex items-center space-x-2 bg-red-600 hover:bg-red-700">
                    <RefreshCw className="w-4 h-4" />
                    <span>Try Again</span>
                  </Button>
                  <Button variant="outline" onClick={handleBackToWorkspaces}>
                    Back to Workspaces
                  </Button>
                  <Button variant="ghost" onClick={() => setError(null)}>
                    Dismiss
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="space-y-6 animate-in fade-in duration-500 px-4">
        {/* Enhanced Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center space-x-4">
            <Button variant="ghost" size="icon" onClick={handleBack} className="rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-brand-500 dark:text-white tracking-tight">
                Team Management
              </h1>
              <p className="text-gray-600 dark:text-gray-400  flex items-center gap-2">
                Manage teams and their credit allocations across your organization
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" onClick={handleRefresh} className="flex items-center space-x-2 rounded-lg">
                  <RefreshCw className="w-4 h-4" />
                  <span className="hidden sm:inline">Refresh</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Refresh data</p>
              </TooltipContent>
            </Tooltip>
            
            <Button 
              onClick={() => router.push('/organization/invite-members')}
              className="flex items-center space-x-2 rounded-lg bg-brand-600 hover:bg-brand-700"
            >
              <Plus className="w-4 h-4" />
              <span>Invite Team Leaders</span>
            </Button>
          </div>
        </div>

        {/* Enhanced Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <Card className="relative overflow-hidden border-brand-200 dark:border-brand-800 bg-gradient-to-br from-brand-50 to-white dark:from-brand-950/20 dark:to-gray-900">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stats.totalTeams}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">Total Teams</p>
                </div>
                <div className="w-12 h-12 bg-brand-100 dark:bg-brand-900 rounded-xl flex items-center justify-center">
                  <Building2 className="w-6 h-6 text-brand-600 dark:text-brand-400" />
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="relative overflow-hidden border-green-200 dark:border-green-800 bg-gradient-to-br from-green-50 to-white dark:from-green-950/20 dark:to-gray-900">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stats.totalMembers}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">Total Members</p>
                </div>
                <div className="w-12 h-12 bg-green-100 dark:bg-green-900 rounded-xl flex items-center justify-center">
                  <Users className="w-6 h-6 text-green-600 dark:text-green-400" />
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="relative overflow-hidden border-purple-200 dark:border-purple-800 bg-gradient-to-br from-purple-50 to-white dark:from-purple-950/20 dark:to-gray-900">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stats.totalCredits.toLocaleString()}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">Total Credits</p>
                </div>
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900 rounded-xl flex items-center justify-center">
                  <CreditCard className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="relative overflow-hidden border-orange-200 dark:border-orange-800 bg-gradient-to-br from-orange-50 to-white dark:from-orange-950/20 dark:to-gray-900">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stats.totalUsedCredits.toLocaleString()}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">Credits Used</p>
                </div>
                <div className="w-12 h-12 bg-orange-100 dark:bg-orange-900 rounded-xl flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="relative overflow-hidden border-cyan-200 dark:border-cyan-800 bg-gradient-to-br from-cyan-50 to-white dark:from-cyan-950/20 dark:to-gray-900">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stats.avgTeamSize.toFixed(1)}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">Avg Team Size</p>
                </div>
                <div className="w-12 h-12 bg-cyan-100 dark:bg-cyan-900 rounded-xl flex items-center justify-center">
                  <Target className="w-6 h-6 text-cyan-600 dark:text-cyan-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

       
        {/* Enhanced Teams List */}
        <Card>
          <CardHeader>
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div>
                <CardTitle className="flex items-center space-x-2 text-xl ">
                  <span>Teams Overview</span>
                </CardTitle>
                <CardDescription className="text-sm ">
                  Manage teams, monitor credit usage, and allocate resources efficiently
                </CardDescription>
              </div>
              
              <div className="flex flex-col sm:flex-row gap-3">
                {/* Tabs for filtering */}
                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full sm:w-auto">
                  <TabsList className="grid w-full grid-cols-3 sm:w-auto">
                    <TabsTrigger value="all" className="text-sm">
                      All ({teams.length})
                    </TabsTrigger>
                    <TabsTrigger value="active" className="text-sm">
                      Active
                    </TabsTrigger>
                    <TabsTrigger value="inactive" className="text-sm">
                      Inactive
                    </TabsTrigger>
                  </TabsList>
                </Tabs>

                {/* Search */}
                <div className="relative w-full sm:w-64">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    placeholder="Search teams, leaders..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 rounded-lg"
                  />
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {filteredTeams.length === 0 ? (
              <div className="text-center py-8">
                <div className="w-20 h-20 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-6">
                  <AlertCircle className="w-10 h-10 text-gray-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
                  {searchTerm || activeTab !== 'all' ? 'No matching teams found' : 'No teams created yet'}
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mb-8 max-w-md mx-auto text-lg">
                  {searchTerm || activeTab !== 'all' 
                    ? 'Try adjusting your search criteria or filter settings.'
                    : 'Get started by inviting team leaders to create your first team.'
                  }
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                  <Button 
                    onClick={() => router.push('/organization/invite-members')}
                    className="flex items-center space-x-2 bg-brand-600 hover:bg-brand-700 rounded-lg px-6 py-2"
                    size="lg"
                  >
                    <Plus className="w-5 h-5" />
                    <span>Invite First Team Leader</span>
                  </Button>
                  {(searchTerm || activeTab !== 'all') && (
                    <Button 
                      variant="outline"
                      onClick={() => {
                        setSearchTerm('');
                        setActiveTab('all');
                      }}
                      size="lg"
                    >
                      Clear All Filters
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {sortedTeams.map((team) => {
                  const usagePercentage = getCreditUsagePercentage(team.credits.used, team.credits.total);
                  
                  return (
                    <Card 
                      key={team.team_id} 
                      className="hover:shadow-xl transition-all duration-300 group border hover:border-brand-200 dark:hover:border-brand-800 cursor-pointer"
                      onClick={() => handleViewDetails(team)}
                    >
                      <CardHeader>
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <CardTitle className="text-lg font-semibold truncate flex items-center gap-2">
                              {team.team_name}
                              {team.status === 'active' && (
                                <Badge variant="secondary" className="bg-green-100 text-green-800 border-green-200">
                                  Active
                                </Badge>
                              )}
                            </CardTitle>
                            <CardDescription className="mt-1 line-clamp-2">
                              {team.member_count} member{team.member_count !== 1 ? 's' : ''} • {team.credits.total} total credits
                            </CardDescription>
                          </div>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                              <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity rounded-lg">
                                <MoreVertical className="w-4 h-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-48">
                              <DropdownMenuItem onClick={() => handleViewDetails(team)}>
                                <Eye className="w-4 h-4 mr-2" />
                                View Details
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={(e) => {
                                e.stopPropagation();
                                handleManageCredits(team);
                              }}>
                                <CreditCard className="w-4 h-4 mr-2" />
                                Manage Credits
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem>
                                <Settings className="w-4 h-4 mr-2" />
                                Team Settings
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteTeamClick(team);
                                }}
                                className="text-red-600 dark:text-red-400 focus:text-red-600 focus:bg-red-50 dark:focus:bg-red-900/20"
                              >
                                <Trash2 className="w-4 h-4 mr-2" />
                                Delete Team
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {/* Team Leader */}
                        <div className="flex items-center space-x-3 p-3 bg-gradient-to-r from-brand-50 to-indigo-50 dark:from-brand-900/20 dark:to-indigo-900/20 rounded-xl border border-brand-100 dark:border-brand-800">
                          <div className="w-10 h-10 bg-brand-100 dark:bg-brand-800 rounded-full flex items-center justify-center flex-shrink-0">
                            <Crown className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                              {team.leader_name}
                            </p>
                            <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
                              Team Leader
                            </p>
                          </div>
                        </div>

                        {/* Credit Request Status */}
                        {(() => {
                          const reqStatus = getTeamCreditRequestStatus(team.team_id);
                          if (reqStatus.hasPendingRequests) {
                            return (
                              <div className="flex items-center justify-between p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl border border-yellow-200 dark:border-yellow-800">
                                <div className="flex items-center space-x-2">
                                  <div className="w-8 h-8 bg-yellow-100 dark:bg-yellow-800 rounded-full flex items-center justify-center">
                                    <CreditCard className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                                  </div>
                                  <div>
                                    <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                                      Credit Request Pending
                                    </p>
                                    <p className="text-xs text-yellow-600 dark:text-yellow-400">
                                      {reqStatus.pendingCount} request{reqStatus.pendingCount > 1 ? 's' : ''} • {reqStatus.totalPendingAmount.toLocaleString()} credits
                                    </p>
                                  </div>
                                </div>
                                <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 border-yellow-300">
                                  Pending
                                </Badge>
                              </div>
                            );
                          } else if (reqStatus.totalRequests > 0) {
                            return (
                              <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                                <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center">
                                  <CreditCard className="w-3 h-3 mr-1" />
                                  {reqStatus.totalRequests} past request{reqStatus.totalRequests > 1 ? 's' : ''}
                                </span>
                                <Badge variant="outline" className="text-xs">No pending</Badge>
                              </div>
                            );
                          }
                          return (
                            <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                              <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center">
                                <CreditCard className="w-3 h-3 mr-1" />
                                Credit Requests
                              </span>
                              <span className="text-xs text-gray-400 dark:text-gray-500">No requests</span>
                            </div>
                          );
                        })()}

                        {/* Enhanced Team Stats */}
                        <div className="grid grid-cols-3 gap-3 text-sm">
                          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                            <Users className="w-4 h-4 text-gray-600 mx-auto mb-2" />
                            <p className="font-bold text-gray-900 dark:text-white text-lg">{team.member_count}</p>
                            <p className="text-xs text-gray-500 font-medium">Members</p>
                          </div>
                          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                            <CreditCard className="w-4 h-4 text-green-600 mx-auto mb-2" />
                            <p className="font-bold text-gray-900 dark:text-white text-lg">{team.credits.remaining}</p>
                            <p className="text-xs text-gray-500 font-medium">Available</p>
                          </div>
                          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                            <TrendingUp className="w-4 h-4 text-orange-600 mx-auto mb-2" />
                            <p className="font-bold text-gray-900 dark:text-white text-lg">{team.credits.used}</p>
                            <p className="text-xs text-gray-500 font-medium">Used</p>
                          </div>
                        </div>

                        {/* Enhanced Credits Progress */}
                        <div className="space-y-3">
                          <div className="flex justify-between items-center">
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Credit Usage</span>
                            <div className="flex items-center space-x-2">
                              <span className={`text-sm font-bold ${
                                usagePercentage >= 90 ? 'text-red-600' : 
                                usagePercentage >= 75 ? 'text-yellow-600' : 'text-brand-600'
                              }`}>
                                {usagePercentage}%
                              </span>
                              <Badge variant={getUsageVariant(usagePercentage)} className="text-xs">
                                {usagePercentage >= 90 ? 'High' : usagePercentage >= 75 ? 'Medium' : 'Low'}
                              </Badge>
                            </div>
                          </div>
                          <Progress value={usagePercentage} className="h-2" />
                          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 font-medium">
                            <span>{team.credits.used.toLocaleString()} used</span>
                            <span>{team.credits.total.toLocaleString()} total</span>
                          </div>
                        </div>

                        {/* Enhanced Actions */}
                        <div className="flex space-x-2 pt-2">
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="flex-1 rounded-lg border-2"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleViewDetails(team);
                            }}
                          >
                            <Eye className="w-4 h-4 mr-2" />
                            Details
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="flex-1 rounded-lg border-2 border-brand-200 hover:bg-brand-50 dark:border-brand-800 dark:hover:bg-brand-900/20"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleManageCredits(team);
                            }}
                          >
                            <Coins className="w-4 h-4 mr-2 text-brand-600" />
                            Allocate
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}

            {/* Enhanced Summary */}
            {filteredTeams.length > 0 && (
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pt-6 mt-6 border-t border-gray-200 dark:border-gray-700">
                <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">
                  Showing <span className="font-bold text-gray-900 dark:text-white">{filteredTeams.length}</span> of{' '}
                  <span className="font-bold text-gray-900 dark:text-white">{teams.length}</span> teams
                </p>
                <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400 font-medium">
                  <span className="flex items-center space-x-1">
                    <CreditCard className="w-4 h-4" />
                    <span>Total Credits: <span className="font-bold">{stats.totalCredits.toLocaleString()}</span></span>
                  </span>
                  <span>•</span>
                  <span>Teams: <span className="font-bold">{stats.totalTeams}</span></span>
                  <span>•</span>
                  <span>Members: <span className="font-bold">{stats.totalMembers}</span></span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Modals and Dialogs */}
        {/* Team Members Modal - Minimalistic Design */}
        {selectedTeam && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg max-w-4xl w-full max-h-[90vh] overflow-hidden border border-gray-200 dark:border-gray-800">
              {/* Modal Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-800">
                <div>
                  <h2 className="text-lg font-semibold text-brand-500 dark:text-white">
                    {selectedTeam.team_name}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                    Team details and members
                  </p>
                </div>
                <Button 
                  variant="ghost" 
                  size="icon" 
                  onClick={handleCloseModal}
                  className="h-8 w-8 rounded-md"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>

              {/* Modal Content */}
              <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)] space-y-6">
                {/* Team Stats - Compact Grid */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="space-y-1 rounded-lg border border-gray-200 dark:border-gray-800 p-2 bg-brand-25">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Members</p>
                    <p className="text-xl font-semibold text-brand-500 dark:text-white">{selectedTeam.member_count}</p>
                  </div>
                  <div className="space-y-1 rounded-lg border border-gray-200 dark:border-gray-800 p-2 bg-brand-25">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Total Credits</p>
                    <p className="text-xl font-semibold text-brand-500 dark:text-white">{selectedTeam.credits.total}</p>
                  </div>
                  <div className="space-y-1 rounded-lg border border-gray-200 dark:border-gray-800 p-2 bg-brand-25">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Used</p>
                    <p className="text-xl font-semibold text-brand-500 dark:text-white">{selectedTeam.credits.used}</p>
                  </div>
                  <div className="space-y-1 rounded-lg border border-gray-200 dark:border-gray-800 p-2 bg-brand-25">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Available</p>
                    <p className="text-xl font-semibold text-brand-500 dark:text-white">{selectedTeam.credits.remaining}</p>
                  </div>
                </div>

                {/* Team Leader */}
                <div className="flex items-center justify-between p-4 rounded-lg border border-brand-200 dark:border-brand-800 bg-brand-25 dark:bg-brand-800/50">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
                      <Crown className="w-5 h-5 text-brand-500 dark:text-gray-400" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-brand-500 dark:text-white">{selectedTeam.leader_name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{selectedTeam.leader_email}</p>
                    </div>
                  </div>
                  <Badge variant="secondary" className="text-xs text-brand-500 dark:text-brand-400 border-brand-500 dark:border-brand-400">
                    Team Leader
                  </Badge>
                </div>

                {/* Team Members List */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                      Members ({teamMembers.length})
                    </h3>
                    <Button 
                      onClick={() => router.push('/organization/invite-members')}
                      size="sm"
                      variant="outline"
                      className="h-8 text-xs"
                    >
                      <Mail className="w-3 h-3 mr-1.5" />
                      Invite
                    </Button>
                  </div>

                  {loadingMembers ? (
                    <div className="space-y-3">
                      {[...Array(3)].map((_, i) => (
                        <div key={i} className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-800 rounded-lg">
                          <Skeleton className="w-10 h-10 rounded-full" />
                          <div className="space-y-2 flex-1">
                            <Skeleton className="h-3 w-32" />
                            <Skeleton className="h-2 w-24" />
                          </div>
                          <Skeleton className="h-6 w-16" />
                        </div>
                      ))}
                    </div>
                  ) : teamMembers.length === 0 ? (
                    <div className="text-center py-8">
                      <div className="w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-3">
                        <Users className="w-6 h-6 text-gray-400" />
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                        No team members yet
                      </p>
                      <Button 
                        onClick={() => router.push('/organization/invite-members')}
                        size="sm"
                        variant="outline"
                      >
                        <Mail className="w-3 h-3 mr-1.5" />
                        Invite Members
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {teamMembers.map((member) => {
                        const memberUsage = getCreditUsagePercentage(member.credits_used, member.credits_allocated);
                        
                        return (
                          <div 
                            key={member.user_id} 
                            className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                          >
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                              <div className="w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                                <UserCheck className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <p className="text-sm font-medium text-brand-500 dark:text-white truncate">
                                    {member.user_name || member.user_email}
                                  </p>
                                  <Badge variant="outline" className="text-xs">
                                    {member.role}
                                  </Badge>
                                </div>
                                {member.user_email && member.user_name && (
                                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                    {member.user_email}
                                  </p>
                                )}
                              </div>
                            </div>
                            
                            <div className="flex items-center gap-4">
                              <div className="text-right">
                                <p className="text-xs font-medium text-gray-900 dark:text-white">
                                  {member.credits_used} / {member.credits_allocated}
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                  {memberUsage}% used
                                </p>
                              </div>
                              
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="icon" className="h-8 w-8">
                                    <MoreVertical className="w-4 h-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem>
                                    View Profile
                                  </DropdownMenuItem>
                                  <DropdownMenuItem>
                                    Adjust Credits
                                  </DropdownMenuItem>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem className="text-red-600">
                                    Remove from Team
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Created {selectedTeam.created_at ? new Date(selectedTeam.created_at).toLocaleDateString() : 'recently'}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleCloseModal} size="sm">
                    Close
                  </Button>
                  <Button 
                    onClick={() => handleManageCredits(selectedTeam)}
                    size="sm"
                    className="bg-brand-600 hover:bg-brand-700"
                  >
                    <Coins className="w-3 h-3 mr-1.5" />
                    Allocate Credits
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Credit Allocation Dialog */}
        <Dialog
          open={creditAllocation.isOpen}
          onOpenChange={(open) => {
            if (!open) {
              setCreditAllocation({
                isOpen: false,
                team: null,
                amount: "",
                isAllocating: false,
              });
            }
          }}
        >
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-brand-100 dark:bg-brand-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Coins className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                </div>
                <DialogTitle className="text-lg">Allocate Credits to Team</DialogTitle>
              </div>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <DialogDescription className="text-base">
                Allocate credits from your organization pool to{" "}
                <span className="font-semibold text-gray-900 dark:text-white">
                  {creditAllocation.team?.team_name}
                </span>
              </DialogDescription>

              {creditAllocation.team && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Current Team Credits:</span>
                    <span className="font-medium">
                      {creditAllocation.team.credits.remaining} available
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Total Allocated:</span>
                    <span className="font-medium">{creditAllocation.team.credits.total}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Team Members:</span>
                    <span className="font-medium">{creditAllocation.team.member_count}</span>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="team-credit-amount">Credits to Allocate</Label>
                <Input
                  id="team-credit-amount"
                  type="number"
                  min="1"
                  placeholder="Enter amount"
                  value={creditAllocation.amount}
                  onChange={(e) =>
                    setCreditAllocation((prev) => ({ ...prev, amount: e.target.value }))
                  }
                  disabled={creditAllocation.isAllocating}
                />
                <p className="text-xs text-gray-500">
                  Credits will be deducted from your organization's pool and added to the team
                </p>
              </div>
            </div>

            <DialogFooter className="flex gap-3 pt-4">
              <Button
                variant="outline"
                onClick={() => {
                  setCreditAllocation({
                    isOpen: false,
                    team: null,
                    amount: "",
                    isAllocating: false,
                  });
                }}
                disabled={creditAllocation.isAllocating}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAllocateCredits}
                disabled={creditAllocation.isAllocating || !creditAllocation.amount}
                className="flex items-center space-x-2 bg-brand-600 hover:bg-brand-700"
              >
                {creditAllocation.isAllocating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Allocating...</span>
                  </>
                ) : (
                  <>
                    <Coins className="w-4 h-4" />
                    <span>Allocate Credits</span>
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Team Confirmation Dialog */}
        <Dialog
          open={deleteTeamState.isOpen}
          onOpenChange={(open) => {
            if (!open && !deleteTeamState.isDeleting) {
              handleDeleteTeamCancel();
            }
          }}
        >
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                  <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
                </div>
                <DialogTitle className="text-lg">Delete Team</DialogTitle>
              </div>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <DialogDescription className="text-base">
                Are you sure you want to delete{" "}
                <span className="font-semibold text-gray-900 dark:text-white">
                  {deleteTeamState.team?.team_name}
                </span>
                ? This action cannot be undone.
              </DialogDescription>

              {deleteTeamState.team && (
                <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 space-y-3 border border-red-200 dark:border-red-800">
                  <p className="text-sm font-medium text-red-800 dark:text-red-200">
                    The following will happen:
                  </p>
                  <ul className="text-sm text-red-700 dark:text-red-300 space-y-2">
                    <li className="flex items-start space-x-2">
                      <span className="mt-1">•</span>
                      <span>
                        <strong>{deleteTeamState.team.member_count}</strong> team member(s) will lose access
                      </span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <span className="mt-1">•</span>
                      <span>
                        <strong>{deleteTeamState.team.credits.remaining}</strong> remaining credits will be returned to the organization
                      </span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <span className="mt-1">•</span>
                      <span>The team will be permanently deactivated</span>
                    </li>
                  </ul>
                </div>
              )}
            </div>

            <DialogFooter className="flex gap-3 pt-4">
              <Button
                variant="outline"
                onClick={handleDeleteTeamCancel}
                disabled={deleteTeamState.isDeleting}
              >
                Cancel
              </Button>
              <Button
                onClick={handleDeleteTeamConfirm}
                disabled={deleteTeamState.isDeleting}
                className="flex items-center space-x-2 bg-red-600 hover:bg-red-700 text-white"
              >
                {deleteTeamState.isDeleting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    <span>Delete Team</span>
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  );
}