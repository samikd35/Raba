"use client";

import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useTeamStore } from "@/stores/teamStore";
import { useAuthStore } from "@/stores/authStore";
import { 
  Settings as SettingsIcon, 
  Save, 
  AlertCircle,
  Users,
  CreditCard,
  Bell,
  Shield,
  Building,
  Mail,
  Crown,
  RefreshCw,
  AlertTriangle
} from "lucide-react";
import { toast, Toaster } from "react-hot-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

// Live credits interfaces and hook (shared pattern with header/dashboard)
interface CreditLot {
  id: string;
  credit_amount: number;
  valid_from: string;
  expires_at: string;
}

interface CreditsData {
  tenant_id: string;
  lots: CreditLot[];
  tenant_total_active_credits: number;
  user_total_consumed_in_tenant: number;
}

const useCreditsData = (currentTeam: { id: string } | null) => {
  const [creditsData, setCreditsData] = useState<CreditsData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { token, isInitialized, isAuthenticated } = useAuthStore();
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);
  const isFetchingRef = useRef(false);
  const lastFetchAtRef = useRef<number>(0);

  const fetchCreditsData = useCallback(async (forceRefresh = false) => {
    if (!isInitialized || !isAuthenticated || !currentTeam?.id || !token) {
      setCreditsData(null);
      setError(null);
      return;
    }

    if (isFetchingRef.current && !forceRefresh) return;

    const now = Date.now();
    if (!forceRefresh && now - lastFetchAtRef.current < 10000) return;

    try {
      setIsLoading(true);
      setError(null);
      isFetchingRef.current = true;

      if (abortControllerRef.current) abortControllerRef.current.abort();
      abortControllerRef.current = new AbortController();

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/me/credits`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        switch (response.status) {
          case 401: throw new Error('Authentication expired. Please sign in again.');
          case 403: throw new Error('Access forbidden. Check your permissions.');
          case 404: throw new Error('Credits endpoint not found.');
          case 429: throw new Error('Too many requests. Please try again later.');
          default: throw new Error(`Failed to fetch credits: ${response.status} ${response.statusText}`);
        }
      }

      const contentType = response.headers.get('content-type');
      if (!contentType?.includes('application/json')) {
        throw new Error('Invalid response format from credits API');
      }

      const data: CreditsData = await response.json();
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid data structure received from API');
      }

      const validated: CreditsData = {
        tenant_id: data.tenant_id || currentTeam.id,
        lots: Array.isArray(data.lots)
          ? data.lots.filter((lot: any) => lot?.id && typeof lot.credit_amount === 'number' && lot.valid_from && lot.expires_at)
          : [],
        tenant_total_active_credits: typeof data.tenant_total_active_credits === 'number' ? Math.max(0, data.tenant_total_active_credits) : 0,
        user_total_consumed_in_tenant: typeof data.user_total_consumed_in_tenant === 'number' ? Math.max(0, data.user_total_consumed_in_tenant) : 0,
      };

      if (isMountedRef.current) setCreditsData(validated);
    } catch (err: any) {
      if (err?.name === 'AbortError') return;
      if (isMountedRef.current) setError(err?.message || 'Failed to fetch credits data');
    } finally {
      if (isMountedRef.current) setIsLoading(false);
      lastFetchAtRef.current = Date.now();
      isFetchingRef.current = false;
    }
  }, [currentTeam?.id, token, isInitialized, isAuthenticated]);

  useEffect(() => {
    isMountedRef.current = true;
    isFetchingRef.current = false;
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, []);

  return { creditsData, isLoading, error, fetchCreditsData };
};

export default function TeamWorkspaceSettings() {
  const { currentTeam } = useTeamStore();
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState('general');
  const [teamName, setTeamName] = useState('');
  const [teamDescription, setTeamDescription] = useState('');
  const [teamWebsite, setTeamWebsite] = useState('');
  const [teamIndustry, setTeamIndustry] = useState('');
  const [teamSize, setTeamSize] = useState('');
  const [teamCountry, setTeamCountry] = useState('');
  const [saving, setSaving] = useState(false);
  const [notifications, setNotifications] = useState({
    email: true,
    slack: false,
    weeklyReport: true,
    creditAlerts: true
  });

  // Live credits integration
  const { creditsData, isLoading: creditsLoading, error: creditsError, fetchCreditsData } = useCreditsData(currentTeam);
  const formatNumber = useCallback((num: number) => {
    if (num === 0) return '0';
    return new Intl.NumberFormat('en-US', { notation: num > 999 ? 'compact' : 'standard', maximumFractionDigits: 1 }).format(num);
  }, []);
  const creditStats = useMemo(() => {
    if (creditsData) {
      const total = Math.max(creditsData.tenant_total_active_credits + creditsData.user_total_consumed_in_tenant, 1);
      const remaining = Math.max(creditsData.tenant_total_active_credits, 0);
      const used = Math.max(creditsData.user_total_consumed_in_tenant, 0);
      const percentage = total > 0 ? Math.round((remaining / total) * 100) : 0;
      const usedPercentage = total > 0 ? Math.round((used / total) * 100) : 0;
      return { total, remaining, used, percentage, usedPercentage };
    }
    const total = currentTeam?.credit_pool_total || 0;
    const remaining = currentTeam?.credit_pool_remaining || 0;
    const used = currentTeam?.credit_pool_used || 0;
    const percentage = total > 0 ? Math.round((remaining / total) * 100) : 0;
    const usedPercentage = total > 0 ? Math.round((used / total) * 100) : 0;
    return { total, remaining, used, percentage, usedPercentage };
  }, [creditsData, currentTeam]);
  useEffect(() => {
    if (!currentTeam?.id) return;
    const t = setTimeout(() => fetchCreditsData(), 300);
    return () => clearTimeout(t);
  }, [currentTeam?.id, fetchCreditsData]);
  useEffect(() => {
    if (!currentTeam?.id) return;
    const interval = setInterval(() => fetchCreditsData(), 60000);
    return () => clearInterval(interval);
  }, [currentTeam?.id, fetchCreditsData]);

  // Initialize form fields when currentTeam changes
  useEffect(() => {
    if (currentTeam) {
      setTeamName(currentTeam.name || '');
      setTeamDescription(currentTeam.description || '');
      setTeamWebsite(currentTeam.website || '');
      setTeamIndustry(currentTeam.industry || '');
      setTeamSize(currentTeam.size || '');
      setTeamCountry(currentTeam.country || '');
    }
  }, [currentTeam]);

  const isTeamLeader = currentTeam?.team_leader_id === user?.id || 
                        currentTeam?.team_leader_email === user?.email;

  const handleSave = async () => {
    if (!currentTeam?.id) {
      toast.error('Team ID not found');
      return;
    }

    // Validate team name
    if (teamName.trim().length < 2 || teamName.trim().length > 100) {
      toast.error('Team name must be between 2-100 characters');
      return;
    }

    setSaving(true);
    
    try {
      // Get auth token
      const token = useAuthStore.getState().token;
      if (!token) {
        toast.error('Authentication required');
        return;
      }

      // Prepare update payload - only include changed fields
      const updatePayload: Record<string, any> = {};
      
      if (teamName !== currentTeam.name) {
        updatePayload.name = teamName.trim();
      }
      if (teamDescription !== (currentTeam.description || '')) {
        updatePayload.description = teamDescription.trim() || null;
      }
      if (teamWebsite !== (currentTeam.website || '')) {
        updatePayload.website = teamWebsite.trim() || null;
      }
      if (teamIndustry !== (currentTeam.industry || '')) {
        updatePayload.industry = teamIndustry.trim() || null;
      }
      if (teamSize !== (currentTeam.size || '')) {
        updatePayload.size = teamSize.trim() || null;
      }
      if (teamCountry !== (currentTeam.country || '')) {
        updatePayload.country = teamCountry.trim() || null;
      }

      // Check if there are any changes
      if (Object.keys(updatePayload).length === 0) {
        toast.info('No changes to save');
        setSaving(false);
        return;
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 Updating team with payload:', updatePayload);
      }

      // Make API request - canonical path per backend docs
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(`${apiUrl}/api/teams/${currentTeam.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatePayload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to update team' }));
        
        if (response.status === 401) {
          toast.error('Authentication required. Please sign in again.');
          return;
        } else if (response.status === 403) {
          toast.error('You do not have permission to update this team');
          return;
        } else if (response.status === 404) {
          toast.error('Team not found');
          return;
        } else if (response.status === 405) {
          toast.error('Method not allowed by server. Please contact support.');
          return;
        } else if (response.status === 400) {
          toast.error(errorData.detail || 'Invalid team data');
          return;
        }
        
        throw new Error(errorData.detail || 'Failed to update team');
      }

      const updatedTeam = await response.json();
      
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Team updated successfully:', updatedTeam);
      }

      // Update the team store with new data
      const teamStore = useTeamStore.getState();
      if (teamStore.setCurrentTeam) {
        teamStore.setCurrentTeam({
          ...currentTeam,
          ...updatedTeam,
        });
      }

      toast.success('Team settings updated successfully');
    } catch (error) {
      console.error('Failed to update team:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (!currentTeam) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="w-full max-w-md text-center">
          <CardContent className="pt-6">
            <SettingsIcon className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold">No Team Selected</h3>
            <p className="text-muted-foreground mt-2">
              Please select a team to manage settings
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!isTeamLeader) {
    return (
      <div className="space-y-4 max-w-4xl mx-auto p-4">
        <div>
          <h1 className="text-2xl font-bold text-brand-500">Team Settings</h1>
          <p className="text-muted-foreground">
            Configure your team preferences and settings
          </p>
        </div>

        <Alert className="bg-yellow-50 border-yellow-200 dark:bg-yellow-950/20 dark:border-yellow-800">
          <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
          <AlertTitle className="text-yellow-800 dark:text-yellow-200">
            Team Leader Access Required
          </AlertTitle>
          <AlertDescription className="text-yellow-700 dark:text-yellow-300">
            Only team leaders can modify team settings. Contact your team leader if you need to make changes.
          </AlertDescription>
        </Alert>

        {/* Read-only team info for non-leaders */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building className="h-5 w-5" />
              Team Information
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1">
              <Label className="text-muted-foreground">Team Name</Label>
              <p className="font-medium">{currentTeam.name}</p>
            </div>
            <div className="space-y-1">
              <Label className="text-muted-foreground">Organization</Label>
              <p className="font-medium">{currentTeam.organization_name}</p>
            </div>
            <div className="space-y-1">
              <Label className="text-muted-foreground">Team Leader</Label>
              <p className="font-medium">{currentTeam.team_leader_email}</p>
            </div>
            <div className="space-y-1">
              <Label className="text-muted-foreground">Member Count</Label>
              <p className="font-medium">{currentTeam.member_count || 0}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 mx-auto p-2">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          
          <div>
            <h1 className="text-2xl font-bold text-brand-500">Team Settings</h1>
            <p className="text-muted-foreground">
              Manage your team configuration and preferences
            </p>
          </div>
        </div>
        {/* <Badge variant="secondary" className="flex items-center gap-1 w-fit">
          <Crown className="h-3 w-3" />
          Team Leader
        </Badge> */}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        {/* Enhanced Tabs List */}
        <TabsList className="grid w-full grid-cols-4 h-12">
          <TabsTrigger value="general" className="flex items-center gap-2">
            <SettingsIcon className="h-4 w-4" />
            General
          </TabsTrigger>
          <TabsTrigger value="members" className="flex items-center gap-2 opacity-50 cursor-not-allowed" disabled title="Coming soon">
            <Users className="h-4 w-4" />
            Members
          </TabsTrigger>
          <TabsTrigger value="billing" className="flex items-center gap-2 opacity-50 cursor-not-allowed" disabled title="Coming soon">
            <CreditCard className="h-4 w-4" />
            Billing
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-2 opacity-50 cursor-not-allowed" disabled title="Coming soon">
            <Bell className="h-4 w-4" />
            Notifications
          </TabsTrigger>
        </TabsList>

        {/* General Settings */}
        <TabsContent value="general" className="space-y-4">
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Team Information</CardTitle>
                  <CardDescription>
                    Update your team's basic information and description
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="team-name">Team Name *</Label>
                    <Input
                      id="team-name"
                      value={teamName}
                      onChange={(e) => setTeamName(e.target.value)}
                      placeholder="Enter team name"
                      maxLength={100}
                    />
                    <p className="text-xs text-muted-foreground">
                      {teamName.length}/100 characters
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="team-description">Description</Label>
                    <Textarea
                      id="team-description"
                      value={teamDescription}
                      onChange={(e) => setTeamDescription(e.target.value)}
                      placeholder="Describe your team's purpose and goals"
                      rows={4}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="team-website">Website</Label>
                    <Input
                      id="team-website"
                      type="url"
                      value={teamWebsite}
                      onChange={(e) => setTeamWebsite(e.target.value)}
                      placeholder="https://example.com"
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="team-industry">Industry</Label>
                      <Input
                        id="team-industry"
                        value={teamIndustry}
                        onChange={(e) => setTeamIndustry(e.target.value)}
                        placeholder="e.g., Technology, Healthcare"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="team-size">Team Size</Label>
                      <Input
                        id="team-size"
                        value={teamSize}
                        onChange={(e) => setTeamSize(e.target.value)}
                        placeholder="e.g., 10-50, 50-100"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="team-country">Country</Label>
                    <Input
                      id="team-country"
                      value={teamCountry}
                      onChange={(e) => setTeamCountry(e.target.value)}
                      placeholder="e.g., United States, Kenya"
                    />
                  </div>

                  <Separator />

                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <p className="text-sm font-medium">Last Updated</p>
                      <p className="text-sm text-muted-foreground">
                        {currentTeam?.updated_at 
                          ? new Date(currentTeam.updated_at).toLocaleDateString('en-US', { 
                              year: 'numeric', 
                              month: 'long', 
                              day: 'numeric' 
                            })
                          : new Date().toLocaleDateString('en-US', { 
                              year: 'numeric', 
                              month: 'long', 
                              day: 'numeric' 
                            })
                        }
                      </p>
                    </div>
                    <Button onClick={handleSave} disabled={saving}>
                      {saving ? (
                        <>
                          <Save className="h-4 w-4 animate-spin mr-2" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save className="h-4 w-4 mr-2" />
                          Save Changes
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Team Overview Sidebar */}
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Team Overview</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 -mt-4">
                  {/* Members Row */}
                  <div className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-800 px-3 py-2">
                    <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                      <Users className="h-3.5 w-3.5 text-brand-500" />
                      Members
                    </span>
                    <Badge variant="secondary" className="font-semibold">
                      {currentTeam.member_count || 0}
                    </Badge>
                  </div>

                  {/* Credits Row */}
                  <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                        <CreditCard className="h-3.5 w-3.5 text-brand-500" />
                        Available Credits
                      </span>
                      <Badge variant="outline" className="font-semibold">
                        {creditsLoading ? (
                          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><RefreshCw className="w-3 h-3 animate-spin" /> Loading</span>
                        ) : creditsError ? (
                          <span className="inline-flex items-center gap-1 text-xs text-red-500"><AlertTriangle className="w-3 h-3" /> Error</span>
                        ) : (
                          formatNumber(creditStats.remaining)
                        )}
                      </Badge>
                    </div>

                    {/* Usage + Progress */}
                    <div className="mt-3 space-y-2">
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>Usage</span>
                        <span>
                          {creditsData ? (
                            <>of {formatNumber(creditStats.total)} total • {creditStats.usedPercentage}% used</>
                          ) : (
                            <>live credits syncing…</>
                          )}
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-gray-200 dark:bg-gray-800 overflow-hidden">
                        <div
                          className="h-2 rounded-full bg-gradient-to-r from-brand-500 to-brand-600 transition-all duration-500"
                          style={{ width: `${creditStats.percentage}%` }}
                        />
                      </div>
                      {/* Status pill */}
                      <div className="flex items-center justify-end">
                        {(() => {
                          const pct = creditStats.percentage;
                          const statusColor = pct > 60 ? 'bg-emerald-500' : pct > 30 ? 'bg-amber-500' : pct > 0 ? 'bg-red-500' : 'bg-gray-400';
                          const text = pct > 60 ? 'Healthy' : pct > 30 ? 'Moderate' : pct > 0 ? 'Low' : 'Empty';
                          return (
                            <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                              <span className={`h-2 w-2 rounded-full ${statusColor}`} />
                              {text}
                            </span>
                          );
                        })()}
                      </div>
                    </div>
                  </div>

                  {/* Status Row */}
                  <div className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-800 px-3 py-2">
                    <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                      <Shield className="h-3.5 w-3.5 text-brand-500" />
                      Status
                    </span>
                    <Badge className="bg-brand-500 text-white">Active</Badge>
                  </div>
                </CardContent>
              </Card>

              
            </div>
          </div>
        </TabsContent>

        {/* Members Settings */}
        <TabsContent value="members" className="space-y-4">
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Member Management</CardTitle>
                  <CardDescription>
                    Manage team members and their permissions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                          <Users className="h-4 w-4 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">John Doe</p>
                          <p className="text-sm text-muted-foreground">john@example.com</p>
                        </div>
                      </div>
                      <Badge variant="secondary">Admin</Badge>
                    </div>

                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-muted rounded-full flex items-center justify-center">
                          <Users className="h-4 w-4" />
                        </div>
                        <div>
                          <p className="font-medium">Jane Smith</p>
                          <p className="text-sm text-muted-foreground">jane@example.com</p>
                        </div>
                      </div>
                      <Badge variant="outline">Member</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Permission Settings</CardTitle>
                  <CardDescription>
                    Configure what team members can do
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Allow member invitations</Label>
                      <p className="text-sm text-muted-foreground">
                        Members can invite new users to the team
                      </p>
                    </div>
                    <Switch />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Credit usage alerts</Label>
                      <p className="text-sm text-muted-foreground">
                        Notify members when credits are running low
                      </p>
                    </div>
                    <Switch defaultChecked />
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Quick Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button variant="outline" className="w-full justify-start">
                    <Mail className="h-4 w-4 mr-2" />
                    Invite Members
                  </Button>
                  <Button variant="outline" className="w-full justify-start">
                    <Shield className="h-4 w-4 mr-2" />
                    Manage Roles
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Billing Settings */}
        <TabsContent value="billing" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Billing Information</CardTitle>
                  <CardDescription>
                    Manage your team's billing and subscription details
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Current Plan</Label>
                      <div className="p-3 border rounded-lg">
                        <p className="font-semibold">Team Pro</p>
                        <p className="text-sm text-muted-foreground">$49/month</p>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>Next Billing Date</Label>
                      <div className="p-3 border rounded-lg">
                        <p className="font-semibold">
                          {new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-4">
                    <h4 className="font-semibold">Credit Usage</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Available Credits</span>
                        <span className="font-medium">
                          {creditsLoading ? (
                            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><RefreshCw className="w-3 h-3 animate-spin" /> Loading</span>
                          ) : creditsError ? (
                            <span className="inline-flex items-center gap-1 text-xs text-red-500"><AlertTriangle className="w-3 h-3" /> Error</span>
                          ) : (
                            formatNumber(creditStats.remaining)
                          )}
                        </span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div 
                          className="bg-primary h-2 rounded-full" 
                          style={{ width: `${creditStats.percentage}%` }}
                        />
                      </div>
                      <div className="text-xs text-muted-foreground text-right">
                        {creditsData ? (
                          <>of {formatNumber(creditStats.total)} total • {creditStats.usedPercentage}% used</>
                        ) : (
                          <>live credits syncing…</>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Billing History</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span>October 2024</span>
                    <span className="font-medium">$49.00</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span>September 2024</span>
                    <span className="font-medium">$49.00</span>
                  </div>
                  <Button variant="outline" className="w-full" size="sm">
                    View All Invoices
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Notifications Settings */}
        <TabsContent value="notifications" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Notification Preferences</CardTitle>
                  <CardDescription>
                    Configure how and when you receive team notifications
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-4">
                    <h4 className="font-semibold">Email Notifications</h4>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label>Team invitations</Label>
                          <p className="text-sm text-muted-foreground">
                            When new members are invited
                          </p>
                        </div>
                        <Switch checked={notifications.email} onCheckedChange={(checked) => 
                          setNotifications(prev => ({ ...prev, email: checked }))
                        } />
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label>Weekly reports</Label>
                          <p className="text-sm text-muted-foreground">
                            Team activity and usage summary
                          </p>
                        </div>
                        <Switch checked={notifications.weeklyReport} onCheckedChange={(checked) => 
                          setNotifications(prev => ({ ...prev, weeklyReport: checked }))
                        } />
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label>Credit alerts</Label>
                          <p className="text-sm text-muted-foreground">
                            When credits are running low
                          </p>
                        </div>
                        <Switch checked={notifications.creditAlerts} onCheckedChange={(checked) => 
                          setNotifications(prev => ({ ...prev, creditAlerts: checked }))
                        } />
                      </div>
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-4">
                    <h4 className="font-semibold">Integration Notifications</h4>
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Slack notifications</Label>
                        <p className="text-sm text-muted-foreground">
                          Receive alerts in Slack
                        </p>
                      </div>
                      <Switch checked={notifications.slack} onCheckedChange={(checked) => 
                        setNotifications(prev => ({ ...prev, slack: checked }))
                      } />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Notification Preview</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="p-3 border rounded-lg text-sm">
                    <p className="font-medium">Team Update</p>
                    <p className="text-muted-foreground">
                      Your team has used 75% of available credits
                    </p>
                  </div>
                  <div className="p-3 border rounded-lg text-sm">
                    <p className="font-medium">New Member</p>
                    <p className="text-muted-foreground">
                      John Doe joined the team
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}