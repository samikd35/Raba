"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useAuthActions } from "@/stores/authStore";
import { useTeamStore } from "@/stores/teamStore";
import { clearAllProjectsCaches } from "@/components/DashboardProjects/cacheUtils";
import Button from "@/components/ui/button/Button";
import { toast } from "react-hot-toast";

// VB Token storage key
const VB_TOKEN_KEY = 'vb_invitation_token';
import { 
  User, 
  Building, 
  Users, 
  CheckCircle2, 
  ArrowRight, 
  AlertCircle, 
  RefreshCw,
  Loader2,
  Crown,
  Shield,
  UserCircle,
  Coins
} from 'lucide-react';
import Image from "next/image";
import Link from "next/link";
import WorkspaceCard from "@/components/workspace/WorkspaceCard";

interface Workspace {
  id: string;
  name: string;
  type: 'organization' | 'team' | 'personal' | 'individual_member';
  role: string;
  member_count: number;
  team_count?: number;
  total_credits?: number;
  credits_remaining?: number;
  last_accessed?: string | null;
  is_active?: boolean;
  organization_id?: string;
  organization_name?: string;
  description?: string | null;
}

interface TenantLoginResponse {
  access_token: string;
  tenant_id: string;
  tenant_type: string;
  user_id: string;
  email: string;
  roles: string[];
}

export default function ChooseWorkspacePage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loadingStep, setLoadingStep] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  
  const router = useRouter();
  const { user, token, isAuthenticated, isInitialized } = useAuthStore();
  const { setToken, setUser, logout } = useAuthActions();
  
  // Get clearTeam action to clear stale team cache when switching workspaces
  const clearTeam = useTeamStore((state) => state.clearTeam);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Fetch user's workspaces using optimized /fast endpoint
  const fetchWorkspaces = useCallback(async (skipCache = false) => {
    if (!token) {
      router.push('/signin');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // 🚀 Use optimized /fast endpoint - much faster than /contexts
      const headers: Record<string, string> = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };
      
      // Add cache bypass header if explicitly refreshing
      if (skipCache) {
        headers['X-Skip-Cache'] = 'true';
      }
      
      const workspacesResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/workspaces/fast`, {
        headers,
      });

      if (workspacesResponse.status === 401) {
        toast.error('Session expired. Please sign in again.');
        router.push('/signin');
        return;
      }

      if (!workspacesResponse.ok) {
        throw new Error(`Failed to fetch workspaces: ${workspacesResponse.status}`);
      }

      const workspacesData = await workspacesResponse.json();
      
      // Transform workspaces - handle both nested and flat formats
      const allWorkspaces: Workspace[] = [];

      // Track added IDs to prevent duplicates
      const addedIds = new Set<string>();

      // Track added types to prevent duplicate personal workspaces
      let hasPersonalWorkspace = false;

      // Helper function to add workspace (with deduplication)
      const addWorkspace = (ws: any, defaultRole: string = 'member') => {
        // Skip if already added by ID
        if (addedIds.has(ws.id)) return;
        // Skip organization members - they use individual_member workspaces instead
        if (ws.type === 'organization' && ws.role === 'member') return;
        // Only allow ONE personal workspace
        if (ws.type === 'personal') {
          if (hasPersonalWorkspace) return;
          hasPersonalWorkspace = true;
        }
        
        addedIds.add(ws.id);
        allWorkspaces.push({
          id: ws.id,
          name: ws.name,
          type: ws.type as 'organization' | 'team' | 'personal' | 'individual_member',
          role: ws.role || defaultRole,
          member_count: ws.member_count || 1,
          team_count: ws.team_count || 0,
          total_credits: ws.total_credits || 0,
          credits_remaining: ws.credits_remaining || 0,
          last_accessed: ws.last_accessed || null,
          is_active: ws.is_active !== false,
          organization_id: ws.organization_id || undefined,
          organization_name: ws.organization_name || undefined,
          description: ws.description || null,
        });
      };

      // Check if response has nested structure (organizations, teams, etc.)
      const hasNestedStructure = workspacesData.organizations || workspacesData.teams || workspacesData.individual_members;

      if (hasNestedStructure) {
        // Handle nested format
        if (workspacesData.organizations && Array.isArray(workspacesData.organizations)) {
          workspacesData.organizations.forEach((ws: any) => addWorkspace(ws));
        }
        if (workspacesData.teams && Array.isArray(workspacesData.teams)) {
          workspacesData.teams.forEach((ws: any) => addWorkspace(ws));
        }
        if (workspacesData.individual_members && Array.isArray(workspacesData.individual_members)) {
          workspacesData.individual_members.forEach((ws: any) => addWorkspace(ws));
        }
        // Add personal workspace (single object, not array) - only if not already added by ID or type
        if (workspacesData.personal && workspacesData.personal.id && workspacesData.personal.is_active !== false) {
          const personalAlreadyAdded = allWorkspaces.some(
            w => w.id === workspacesData.personal.id || w.type === 'personal'
          );
          if (!personalAlreadyAdded) {
            allWorkspaces.push({
              id: workspacesData.personal.id,
              name: workspacesData.personal.name,
              type: 'personal',
              role: 'owner',
              member_count: 1,
              team_count: 0,
              total_credits: workspacesData.personal.total_credits || 0,
              credits_remaining: workspacesData.personal.credits_remaining || 0,
              last_accessed: null,
              is_active: true,
              organization_id: undefined,
              organization_name: undefined,
              description: null,
            });
          }
        }
      } else if (workspacesData.workspaces && Array.isArray(workspacesData.workspaces)) {
        // Handle flat workspaces array format
        workspacesData.workspaces.forEach((ws: any) => addWorkspace(ws));
      }

      setWorkspaces(allWorkspaces);

      // Auto-select if only one workspace
      if (allWorkspaces.length === 1) {
        setSelectedWorkspace(allWorkspaces[0].id);
      }

    } catch (error: any) {
      console.error('Error fetching workspaces:', error);
      setError(error.message || 'Failed to load workspaces');
      toast.error('Failed to load workspaces');
    } finally {
      setIsLoading(false);
    }
  }, [token, router]);

  // Initialize on mount
  useEffect(() => {
    if (isInitialized) {
      if (isAuthenticated && token) {
        fetchWorkspaces();
      } else {
        router.push('/signin');
      }
    }
  }, [isInitialized, isAuthenticated, token, fetchWorkspaces, router]);

  // Get workspace icon
  const getWorkspaceIcon = (type: string, role: string) => {
    if (role === 'owner' || role === 'admin') {
      return <Crown className="w-5 h-5" />;
    }
    if (type === 'individual_member') {
      return <UserCircle className="w-5 h-5" />;
    }
    return type === 'organization' ? <Building className="w-5 h-5" /> : type === 'team' ? <Users className="w-5 h-5" /> : <Shield className="w-5 h-5" />;
  };

  // Get role badge color
  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'owner':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-700';
      case 'admin':
        return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700';
      case 'leader':
        return 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700';
      default:
        return 'bg-gray-100 text-brand-500 border-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600';
    }
  };

  // Format workspace names: for personal/individual member accounts the backend may append
  // IDs and suffixes (e.g., "YOSEF LAKEW-68f4...-individual"). Show only the real name
  // before the first hyphen using regex.
  const formatWorkspaceName = useCallback((name?: string, type?: string) => {
    if (!name) return 'workspace';
    // Only format for personal and individual member accounts to avoid altering org/team names
    if (type === 'personal' || type === 'individual_member') {
      const match = name.match(/^[^-]+/); // capture everything before the first hyphen
      return (match ? match[0] : name).trim();
    }
    return name;
  }, []);

  // Get workspace name helper
  const getWorkspaceName = useCallback((workspaceId: string) => {
    const workspace = workspaces.find(w => w.id === workspaceId);
    if (!workspace) return 'workspace';
    return formatWorkspaceName(workspace.name, workspace.type);
  }, [workspaces, formatWorkspaceName]);

  // Get loading message based on step
  const getLoadingMessage = useCallback((step: number) => {
    switch (step) {
      case 1:
        return `Authenticating...`;
      case 2:
        return 'Setting up your workspace...';
      case 3:
        return 'Taking you to your dashboard...';
      default:
        return 'Joining workspace...';
    }
  }, []);

  const joinWorkspace = async (workspaceId: string) => {
    if (!workspaceId) {
      toast.error('Please select a workspace');
      return;
    }
    if (!token) {
      toast.error('Your session has expired. Please sign in again.');
      router.push('/signin');
      return;
    }

    // Abort any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    const workspaceName = getWorkspaceName(workspaceId);
    const toastId = `joining-${workspaceId}`;

    try {
      setIsSubmitting(true);
      setLoadingStep(1);

      // CRITICAL: Clear any cached data before switching workspaces
      // This prevents stale data from being displayed when navigating to a different team
      clearTeam();
      clearAllProjectsCaches(); // Clear projects cache to prevent cross-tenant data leakage
      
      if (process.env.NODE_ENV === 'development') {
        console.log('ChooseWorkspace: Cleared team and projects cache before workspace switch', { targetWorkspaceId: workspaceId });
      }

      // Show initial toast
      toast.loading(getLoadingMessage(1), { id: toastId });

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/auth/login/${workspaceId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        signal: abortControllerRef.current.signal,
      });

      if (!res.ok) {
        if (res.status === 401) {
          toast.error('Authentication expired. Please sign in again.', { id: toastId });
          router.push('/signin');
          return;
        }
        if (res.status === 403) {
          toast.error('You do not have access to this workspace.', { id: toastId });
          return;
        }
        const errorData = await res.json().catch(() => null);
        throw new Error(errorData?.message || `Failed to join workspace: ${res.status}`);
      }

      const data: TenantLoginResponse = await res.json();

      // Step 2: Update authentication state
      setLoadingStep(2);
      toast.loading(getLoadingMessage(2), { id: toastId });

      // Small delay to show progress
      await new Promise(resolve => setTimeout(resolve, 300));

      // Update token first
      setToken(data.access_token);

      // Update user information from response
      if (user) {
        setUser({
          ...user,
          id: data.user_id,
          email: data.email || user.email,
          tenant_id: data.tenant_id,
          tenant_type: data.tenant_type,
          roles: Array.isArray(data.roles) ? data.roles : user.roles,
        });
      } else {
        // Construct a minimal user object if missing
        setUser({
          id: data.user_id,
          email: data.email,
          full_name: '',
          avatar_url: null,
          timezone: 'UTC',
          preferences: {},
          bio: '',
          website: '',
          location: '',
          roles: Array.isArray(data.roles) ? data.roles : ['user'],
          tenant_id: data.tenant_id,
          tenant_type: data.tenant_type,
        });
      }

      // Step 3: Prepare for navigation
      setLoadingStep(3);
      toast.loading(getLoadingMessage(3), { id: toastId });

      // Small delay to ensure state updates are processed
      await new Promise(resolve => setTimeout(resolve, 400));

      // Show success message
      toast.success(`Welcome to ${workspaceName}!`, { id: toastId });

      // Check for VB invitation token
      const vbToken = localStorage.getItem(VB_TOKEN_KEY);

      if (vbToken) {
        if (process.env.NODE_ENV === 'development') {
          console.log('🎯 VB invitation token found, redirecting to VB onboarding');
        }

        // Clear the token from localStorage as we're about to use it
        localStorage.removeItem(VB_TOKEN_KEY);

        // Small delay before navigation for better UX
        await new Promise(resolve => setTimeout(resolve, 500));

        // Redirect to VB onboarding with token
        router.push(`/vb-onboarding?token=${vbToken}`);
        return;
      }

      // Route based on tenant_type (normal flow without VB invitation)
      const tenantType = (data.tenant_type || '').toLowerCase();

      // Small delay before navigation for better UX
      await new Promise(resolve => setTimeout(resolve, 500));

      if (tenantType === 'organization') {
        router.push('/organization');
      } else if (tenantType === 'team') {
        router.push('/team-workspace/dashboard');
      } else if (tenantType === 'individual_member' || tenantType === 'individual') {
        router.push('/workspace');
      } else if (tenantType === 'personal') {
        router.push('/workspace');
      } else {
        // Fallback
        router.push('/workspace');
      }
    } catch (err: any) {
      // Don't show error if request was aborted
      if (err.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Workspace join request aborted');
        }
        return;
      }

      console.error('Failed to join workspace:', err);
      toast.error(err?.message || 'Failed to join workspace', { id: toastId });
    } finally {
      setIsSubmitting(false);
      setLoadingStep(0);
    }
  };

  // Loading state
  if (!isInitialized || isLoading) {
    return (
      <div className="min-h-screen bg-gray-50  dark:bg-brand-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-gray-600 dark:text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-brand-500 dark:text-gray-100">
            Loading your workspaces...
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Please wait while we prepare your options
          </p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50  dark:bg-brand-900 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-8">
          <AlertCircle className="w-16 h-16 text-red-500 dark:text-red-400 mx-auto mb-4" />
          <h3 className="text-2xl font-bold text-brand-500 dark:text-gray-100 mb-3">
            Unable to Load Workspaces
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">{error}</p>
          <div className="space-y-3">
            <Button onClick={fetchWorkspaces} className="w-full bg-gray-600 hover:bg-gray-700 dark:bg-gray-600 dark:hover:bg-gray-700">
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
            <Button
              onClick={async () => {
                try {
                  await logout();
                } finally {
                  router.push('/signin');
                }
              }}
              variant="outline"
              className="w-full border-gray-300 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-brand-500"
            >
              Back to Sign In
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50  dark:bg-brand-900">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header */}
        <div className="text-center mb-4">
          <Link href="/" className="inline-block mb-2 hover:opacity-80 transition-opacity">
            <Image src="/images/logo/yuba-logo-icon-colored.png" alt="Yuba" width={60} height={60} priority />
          </Link>
          <h1 className="text-2xl font-bold text-brand-500 dark:text-gray-100">
            Go To Your Workspace
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Select a workspace to continue
          </p>
          {/* Refresh button - bypasses cache to show newly added workspaces */}
          <button
            onClick={() => fetchWorkspaces(true)}
            disabled={isLoading}
            className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors disabled:opacity-50"
            title="Refresh workspaces list"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {/* Workspaces List */}
        {workspaces.length > 0 ? (
          <div className="space-y-3 mb-8">
            {workspaces.map((workspace) => (
              <WorkspaceCard
                key={workspace.id}
                workspace={workspace}
                isSelected={selectedWorkspace === workspace.id}
                onSelect={() => setSelectedWorkspace(workspace.id)}
                formatWorkspaceName={formatWorkspaceName}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-100 dark:bg-brand-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Building className="w-8 h-8 text-gray-400 dark:text-gray-500" />
            </div>
            <h3 className="text-lg font-semibold text-brand-500 dark:text-gray-100 mb-2">
              No Workspaces Available
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              You don't have access to any workspaces yet.
            </p>
            <Button onClick={() => router.push('/signin')} variant="outline" className="border-gray-300 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-brand-500">
              Back to Sign In
            </Button>
          </div>
        )}

        {/* Action Buttons */}
        {workspaces.length > 0 && (
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button 
              onClick={() => router.push('/signin')} 
              variant="outline" 
              className="min-w-[180px] h-11 border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800 dark:hover:border-gray-500 dark:hover:text-brand-300 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isSubmitting}
            >
              Back to Sign In
            </Button>
            <Button 
              disabled={!selectedWorkspace || isSubmitting}
              className="min-w-[180px] h-11 bg-brand-500 hover:bg-brand-600 dark:bg-brand-600 dark:hover:bg-brand-500 dark:shadow-brand-500/20 dark:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={() => selectedWorkspace && joinWorkspace(selectedWorkspace)}
            >
              {isSubmitting ? (
                <>
                  {loadingStep > 0 && selectedWorkspace ? (
                    <span className="flex items-center gap-1">
                      {getLoadingMessage(loadingStep).split('...')[0]}
                      <span className="flex gap-0.5">
                        <span className={`w-1 h-1 rounded-full bg-current ${loadingStep >= 1 ? 'animate-pulse' : 'opacity-30'}`} />
                        <span className={`w-1 h-1 rounded-full bg-current ${loadingStep >= 2 ? 'animate-pulse animation-delay-200' : 'opacity-30'}`} />
                        <span className={`w-1 h-1 rounded-full bg-current ${loadingStep >= 3 ? 'animate-pulse animation-delay-400' : 'opacity-30'}`} />
                      </span>
                    </span>
                  ) : (
                    'Joining...'
                  )}
                </>
              ) : (
                <>
                  Continue
                </>
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}