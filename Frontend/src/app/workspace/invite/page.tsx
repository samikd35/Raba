"use client";

import React, { useCallback, useMemo, useState, useEffect, useRef } from "react";
import { useTeamStore } from "@/stores/teamStore";
import { useAuthStore } from "@/stores/authStore";
import { TeamService } from "@/lib/api/teamService";
import { 
  Mail,
  UserPlus,
  AlertCircle,
  CheckCircle,
  X,
  Loader2,
  Info,
  Shield,
  Users,
  CreditCard,
  Building,
  RefreshCw,
  AlertTriangle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";
import PageBreadCrumb from "@/components/common/workspace/PageBreadCrumb";
import { toast, Toaster } from "react-hot-toast";

// Credits data interfaces and hook (mirrors TeamWorkspaceHeader/dashboard)
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

export default function TeamWorkspaceInvite() {
  const { currentTeam } = useTeamStore();
  const { user } = useAuthStore();
  const [emails, setEmails] = useState<string[]>([]);
  const [currentEmail, setCurrentEmail] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inputHint, setInputHint] = useState<string | null>(null);

  // Credits integration
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
    const total = (currentTeam?.credit_pool_total || 0);
    const remaining = (currentTeam?.credit_pool_remaining || 0);
    const used = (currentTeam?.credit_pool_used || 0);
    const percentage = total > 0 ? Math.round((remaining / total) * 100) : 0;
    const usedPercentage = total > 0 ? Math.round((used / total) * 100) : 0;
    return { total, remaining, used, percentage, usedPercentage };
  }, [creditsData, currentTeam]);

  // Fetch credits on team change and auto-refresh
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

  // Reasonable upper limit to prevent accidental bulk spam
  const MAX_EMAILS = 50;

  const isTeamLeader = user?.id === currentTeam?.team_leader_id;

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const sanitizeEmails = useCallback((raw: string): string[] => {
    // Split on common separators: comma, semicolon, whitespace, newline
    const parts = raw
      .split(/[\s,;]+/)
      .map((e) => e.trim())
      .filter(Boolean);
    // Deduplicate while preserving order
    const seen = new Set<string>();
    const result: string[] = [];
    for (const p of parts) {
      if (!seen.has(p)) {
        seen.add(p);
        result.push(p);
      }
    }
    return result;
  }, []);

  const addEmails = useCallback(
    (newEmails: string[]) => {
      if (newEmails.length === 0) return;

      let combined = [...emails];
      let invalids: string[] = [];

      for (const e of newEmails) {
        if (!validateEmail(e)) {
          invalids.push(e);
          continue;
        }
        if (!combined.includes(e)) combined.push(e);
      }

      if (combined.length > MAX_EMAILS) {
        combined = combined.slice(0, MAX_EMAILS);
        setInputHint(`Maximum of ${MAX_EMAILS} emails allowed. Extra entries were ignored.`);
      } else {
        setInputHint(null);
      }

      setEmails(combined);
      setCurrentEmail("");
      if (invalids.length) {
        setError(`Invalid email address${invalids.length > 1 ? 'es' : ''}: ${invalids.join(", ")}`);
      } else {
        setError(null);
      }
    },
    [emails]
  );

  const addEmail = useCallback(() => {
    const trimmedEmail = currentEmail.trim();
    if (!trimmedEmail) return;
    addEmails([trimmedEmail]);
  }, [currentEmail, addEmails]);

  const removeEmail = (index: number) => {
    setEmails(emails.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Add on Enter or when user types a separator
    if (e.key === "Enter" || e.key === "," || e.key === ";" || e.key === " ") {
      e.preventDefault();
      if (currentEmail.trim()) {
        addEmails(sanitizeEmails(currentEmail));
      }
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const paste = e.clipboardData.getData("text");
    const parsed = sanitizeEmails(paste);
    if (parsed.length > 1) {
      e.preventDefault();
      addEmails(parsed);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!currentTeam?.id) {
      setError("No team selected");
      return;
    }

    const validEmails = emails.filter(email => email.trim() !== "");

    if (validEmails.length === 0) {
      setError("Please add at least one email address");
      return;
    }

    const invalidEmails = validEmails.filter(email => !validateEmail(email));
    if (invalidEmails.length > 0) {
      setError(`Invalid email addresses: ${invalidEmails.join(", ")}`);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      await TeamService.inviteTeamMembers(currentTeam.id, {
        emails: validEmails,
        is_admin: isAdmin
      });

      const msg = `Successfully sent ${validEmails.length} invitation${validEmails.length !== 1 ? 's' : ''}!`;
      setSuccess(msg);
      toast.success(msg);
      setEmails([]);
      setCurrentEmail("");
      setIsAdmin(false);

      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      console.error('Error sending invitations:', err);
      const errMsg = err instanceof Error ? err.message : 'Failed to send invitations';
      setError(errMsg);
      toast.error(errMsg);
    } finally {
      setLoading(false);
    }
  };

  if (!currentTeam) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="w-full max-w-md text-center">
          <CardContent className="pt-6">
            <AlertCircle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold">No Team Selected</h3>
            <p className="text-muted-foreground mt-2">
              Please select a team to manage invitations
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!isTeamLeader) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="w-full max-w-md text-center">
          <CardContent className="pt-6">
            <AlertCircle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold">Team Leader Access Required</h3>
            <p className="text-muted-foreground mt-2">
              Only team leaders can invite new members to the workspace
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 mx-auto p-2">
      
      <div>
        <h1 className="text-2xl font-bold text-brand-500">Invite Team Members</h1>
        <p className="text-muted-foreground">
          Invite new members to join <span className="font-medium text-brand-500">{currentTeam.name}</span>
        </p>
      </div>

      {/* Alerts */}
      {success && (
        <Alert className="bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-800">
          <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
          <AlertTitle className="text-green-800 dark:text-green-200">Success!</AlertTitle>
          <AlertDescription className="text-green-700 dark:text-green-300">
            {success}
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {error}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Info Alert */}
          <Alert className="bg-blue-50 border-blue-200 dark:bg-blue-950/20 dark:border-blue-800">
            <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <AlertTitle className="text-blue-800 dark:text-blue-200">Important</AlertTitle>
            <AlertDescription className="text-blue-700 dark:text-blue-300">
              Invited users must already be members of the organization before they can join the team.
            </AlertDescription>
          </Alert>

          {/* Invitation Form */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserPlus className="h-5 w-5" />
                Send Invitations
              </CardTitle>
              <CardDescription>
                Add email addresses and select member roles
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Email Input */}
              <div className="space-y-3">
                <Label htmlFor="email">Email Address</Label>
                <div className="flex gap-2">
                  <div className="flex-1 relative">
                    <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="email"
                      type="email"
                      value={currentEmail}
                      onChange={(e) => setCurrentEmail(e.target.value)}
                      onKeyDown={handleKeyDown}
                      onPaste={handlePaste}
                      placeholder="Enter email address"
                      className="pl-10"
                    />
                  </div>
                  <Button
                    type="button"
                    onClick={addEmail}
                    disabled={!currentEmail.trim()}
                    variant="outline"
                    className="shrink-0"
                  >
                    Add
                  </Button>
                </div>
                <div className="text-xs text-muted-foreground space-y-1">
                  <p>Tip: Paste a list or use comma, semicolon, space, or Enter to add multiple emails.</p>
                  <p>
                    {emails.length}/{MAX_EMAILS} added
                    {inputHint ? (
                      <span className="ml-2 text-amber-600 dark:text-amber-400">{inputHint}</span>
                    ) : null}
                  </p>
                </div>
              </div>

              {/* Email List */}
              {emails.length > 0 && (
                <div className="space-y-3">
                  <Label>
                    Email List <Badge variant="secondary" className="ml-2">{emails.length}</Badge>
                  </Label>
                  <div className="flex flex-wrap gap-2 p-3 border rounded-lg bg-muted/50 min-h-12">
                    {emails.map((email, index) => (
                      <Badge key={index} variant="outline" className="pl-3 pr-2 py-1">
                        <Mail className="h-3 w-3 mr-1" />
                        {email}
                        <button
                          type="button"
                          onClick={() => removeEmail(index)}
                          className="ml-1 hover:bg-muted rounded-sm"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <Separator />

              {/* Role Selection */}
              <div className="space-y-4">
                <Label>Member Role</Label>
                <RadioGroup value={isAdmin ? "admin" : "member"} onValueChange={(value) => setIsAdmin(value === "admin")}>
                  <div className="flex flex-col gap-3">
                    <Label htmlFor="role-member" className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer hover:bg-muted/50 transition-colors ${!isAdmin ? 'border-brand-300 bg-brand-50 dark:bg-brand-800/30' : ''}`}>
                      <RadioGroupItem value="member" id="role-member" />
                      <div className="flex-1 space-y-1">
                        <div className="font-medium">Regular Member</div>
                        <p className="text-sm text-muted-foreground">
                          Can view team information and use team credits
                        </p>
                      </div>
                    </Label>
                    
                    <Label htmlFor="role-admin" className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer hover:bg-muted/50 transition-colors ${isAdmin ? 'border-brand-300 bg-brand-50 dark:bg-brand-800/30' : ''}`}>
                      <RadioGroupItem value="admin" id="role-admin" />
                      <div className="flex-1 space-y-1">
                        <div className="font-medium flex items-center gap-2">
                          <Shield className="h-4 w-4 text-blue-600" />
                          Cofounding Member
                        </div>
                        <p className="text-sm text-muted-foreground">
                          Can invite members and manage team settings
                        </p>
                      </div>
                    </Label>
                  </div>
                </RadioGroup>
                <p className="text-xs text-muted-foreground">You can change roles later from the members page.</p>
              </div>

              {/* Submit Buttons */}
              <div className="flex gap-3 pt-4">
                <Button
                  type="submit"
                  onClick={handleSubmit}
                  disabled={loading || emails.length === 0}
                  className="flex-1"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Sending Invitations...
                    </>
                  ) : (
                    <>
                      <Mail className="h-4 w-4 mr-2" />
                      Send {emails.length} Invitation{emails.length !== 1 ? 's' : ''}
                    </>
                  )}
                </Button>
                <Button
                  type="button"
                  onClick={() => {
                    setEmails([]);
                    setCurrentEmail("");
                    setIsAdmin(false);
                    setError(null);
                    setInputHint(null);
                  }}
                  disabled={loading}
                  variant="outline"
                >
                  Clear All
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Team Info Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Users className="h-5 w-5" />
                Team Overview
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 -mt-2">
              <div className="space-y-3">
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Team Name</div>
                  <div className="font-semibold text-brand-500">{currentTeam.name}</div>
                </div>
                
                <div>
                  <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    <Building className="h-3 w-3" />
                    Organization
                  </div>
                  <div className="font-semibold text-brand-500">{currentTeam.organization_name}</div>
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <div className="text-sm font-medium text-muted-foreground">Members</div>
                  <div className="text-2xl font-bold text-brand-500">{currentTeam.member_count || 0}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    <CreditCard className="h-3 w-3" />
                    Credits
                  </div>
                  <div className="text-2xl font-bold text-brand-500">
                    {creditsLoading ? (
                      <span className="inline-flex items-center gap-1 text-sm text-muted-foreground"><RefreshCw className="w-3 h-3 animate-spin" /> Loading</span>
                    ) : creditsError ? (
                      <span className="inline-flex items-center gap-1 text-sm text-red-500"><AlertTriangle className="w-3 h-3" /> Error</span>
                    ) : (
                      formatNumber(creditStats.remaining)
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {creditsData ? (
                      <>of {formatNumber(creditStats.total)} total • {creditStats.usedPercentage}% used</>
                    ) : (
                      <>live credits syncing…</>
                    )}
                  </div>
                </div>
              </div>
              <Separator />
              <div className="text-xs text-muted-foreground">
                Invites are sent from your organization and expire after 7 days.
              </div>
            </CardContent>
          </Card>

          {/* Quick Tips */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Tips</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm -mt-2">
              <div className="flex items-start gap-2">
                <div className="h-2 w-2 bg-blue-600 rounded-full mt-1.5 shrink-0" />
                <div>Users must accept organization invites first</div>
              </div>
              <div className="flex items-start gap-2">
                <div className="h-2 w-2 bg-blue-600 rounded-full mt-1.5 shrink-0" />
                <div>Team admins can manage settings and members</div>
              </div>
              <div className="flex items-start gap-2">
                <div className="h-2 w-2 bg-blue-600 rounded-full mt-1.5 shrink-0" />
                <div>Invitations expire after 7 days</div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}