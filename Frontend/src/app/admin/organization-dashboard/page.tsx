"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { CreditSummary, InvitationAnalytics, Team, TeamMember } from '@/types/organization';
import { teamService } from '@/lib/api/teamService'; // Added import for teamService
import { organizationService } from '@/lib/api/organizationService';
import { FormValidator } from '@/lib/validation';
import { useAuthStore } from '@/stores/authStore';
import { Badge } from '@/components/ui/badge';
import { Building2, Users, User, Mail, CreditCard, Send, Trash2, Eye, Settings, Pause, Plus, Crown, CheckCircle, XCircle, Clock } from 'lucide-react';
import PendingCreditRequestsPanel from '@/components/admin/PendingCreditRequestsPanel';


export default function OrganizationAdminDashboard() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState('invite');
  const [teams, setTeams] = useState<Team[]>([]); // Added state for teams
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(false); // Added loading state
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [creditSummary, setCreditSummary] = useState<CreditSummary>({ total_credits: 0, used_credits: 0, remaining_credits: 0, monthly_limit: 0, reset_date: new Date().toISOString().slice(0, 10) });
  const [inviteAnalytics, setInviteAnalytics] = useState<InvitationAnalytics>({ total_invitations_sent: 0, invitations_accepted: 0, acceptance_rate: 0, pending_invitations: 0 });

  // FIXED: Make default credit values configurable instead of hardcoded
  const DEFAULT_CREDITS_PER_INVITEE = 100; // Could be moved to config/environment
  const [inviteForm, setInviteForm] = useState({
    emails: '',
    creditsPerInvitee: DEFAULT_CREDITS_PER_INVITEE,
    isAdmin: false,
  });

  // Initialize organization ID from user context
  useEffect(() => {
    if (user?.tenant_id) {
      setOrganizationId(user.tenant_id);
    }
  }, [user]);

  // Fetch data when organization ID is available
  useEffect(() => {
    if (organizationId) {
      fetchOrgInfo();
      fetchTeams();
    }
  }, [organizationId]);

  // Added function to fetch teams
  const fetchTeams = async () => {
    if (!organizationId) return; // Don't fetch if no organization ID

    try {
      setLoading(true);
      const fetchedTeams = await teamService.fetchTeams(organizationId);
      setTeams(fetchedTeams as Team[]);
      // FIXED: Only create member entries for teams that actually have data
      const teamMembers: TeamMember[] = fetchedTeams
        .filter((t: any) => t.team_leader_name && t.team_leader_email) // Only real teams
        .map((t: any) => ({
          id: `tl_${t.id}`,
          name: t.team_leader_name,
          email: t.team_leader_email,
          role: 'team_leader',
          team_id: t.id,
          team_name: t.name,
          credits_allocated: Math.floor((t.credit_pool_total || 0) / Math.max(t.member_count || 1, 1)),
          credits_used: Math.floor((t.credit_pool_used || 0) / Math.max(t.member_count || 1, 1)),
          status: 'active',
          joined_date: new Date().toISOString().slice(0, 10),
        }));
      setMembers(teamMembers);
    } catch (error) {
      console.error('Failed to fetch teams:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchOrgInfo = async () => {
    if (!organizationId) return; // Don't fetch if no organization ID

    try {
      setLoading(true);
      // Fetch only the specific organization metrics instead of all organizations
      const metrics: any = await organizationService.getOrganizationMetrics(organizationId);

      console.log('🔍 FRONTEND RECEIVED:', JSON.stringify(metrics, null, 2));

      // Extract credit info from metrics with correct mapping
      const total_credits = Number(metrics?.credits?.total || 0);
      const used_credits = Number(metrics?.credits?.used || 0);
      const remaining_credits = Number(metrics?.credits?.remaining || 0);
      const monthly_limit = Number(metrics?.credits?.monthly_limit || total_credits);

      console.log('🔍 FRONTEND PARSED:', {
        total_credits,
        used_credits,
        remaining_credits,
        monthly_limit
      });

      setCreditSummary({
        total_credits,
        used_credits,
        remaining_credits,
        monthly_limit,
        reset_date: new Date().toISOString().slice(0, 10),
      });
      const sent = Number(metrics?.invitations?.sent || 0);
      const accepted = Number(metrics?.invitations?.accepted || 0);
      const pending = Math.max(0, sent - accepted);
      const acceptance_rate = sent > 0 ? Number(((accepted / sent) * 100).toFixed(1)) : 0;
      setInviteAnalytics({ total_invitations_sent: sent, invitations_accepted: accepted, acceptance_rate, pending_invitations: pending });
    } catch (e) {
      console.error('Failed to load organization info:', e);
    } finally {
      setLoading(false);
    }
  };

  const parseEmails = (raw: string): string[] =>
    raw
      .split(',')
      .map((e) => e.trim())
      .filter((e) => e.length > 0 && FormValidator.validateEmail(e));

  const invitees = useMemo(() => parseEmails(inviteForm.emails), [inviteForm.emails]);

  const totalRequestedCredits = useMemo(() => {
    return invitees.length * (inviteForm.creditsPerInvitee || 0);
  }, [invitees.length, inviteForm.creditsPerInvitee]);

  const availableCredits = useMemo(() => {
    return Math.max(0, (creditSummary.monthly_limit || 0) - (creditSummary.used_credits || 0));
  }, [creditSummary]);

  const allocationValidation = useMemo(() => {
    const res = FormValidator.validateCreditAllocation(
      invitees.length,
      inviteForm.creditsPerInvitee || 0,
      creditSummary.monthly_limit,
      creditSummary.used_credits
    );
    return res.isValid ? { isValid: true } : { isValid: false, errorMessage: res.errorMessage };
  }, [invitees.length, inviteForm.creditsPerInvitee, creditSummary.monthly_limit, creditSummary.used_credits]);

  const canSendInvites = useMemo(() => {
    const hasAnyEmails = invitees.length > 0;
    const creditsPositive = (inviteForm.creditsPerInvitee || 0) > 0;
    return hasAnyEmails && creditsPositive && allocationValidation.isValid;
  }, [invitees.length, inviteForm.creditsPerInvitee, allocationValidation.isValid]);

  const handleSendInvites = async () => {
    if (!canSendInvites || !organizationId) return;
    try {
      const is_team_leader = inviteForm.isAdmin; // ✅ FIXED: This checkbox actually means "team leader", not "admin"

      // Prepare the data structure expected by the API
      const inviteData = is_team_leader
        ? {
          individual_members: [],
          team_leaders: invitees.map(email => ({
            email,
            credits: inviteForm.creditsPerInvitee,
            is_admin: false // Default to false unless the UI adds a separate toggle for this
          }))
        }
        : {
          individual_members: invitees.map(email => ({
            email,
            credits: inviteForm.creditsPerInvitee,
            is_admin: false
          })),
          team_leaders: []
        };

      await organizationService.inviteUsersToOrganization(organizationId, inviteData);
      // Reset form
      setInviteForm({ emails: '', creditsPerInvitee: DEFAULT_CREDITS_PER_INVITEE, isAdmin: false });
    } catch (e) {
      console.error('Failed to send invites', e);
    }
  };

  const handleClearInputs = () => {
    setInviteForm({ emails: '', creditsPerInvitee: DEFAULT_CREDITS_PER_INVITEE, isAdmin: false });
  };

  const getUserInitials = (name: string) => {
    return name
      .split(' ')
      .map(part => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="space-y-6">
      {/* User Profile Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="h-16 w-16 rounded-full bg-brand-500 flex items-center justify-center">
              <User className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {user?.full_name || 'User'}
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                {user?.email || 'user@example.com'}
              </p>
              <div className="flex flex-wrap gap-2 mt-2">
                {user?.roles?.map((role) => (
                  <Badge
                    key={role}
                    variant="secondary"
                    className={
                      role === 'super_admin'
                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
                        : role === 'admin'
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                    }
                  >
                    {role === 'super_admin' ? 'Super Admin' : role === 'admin' ? 'Admin' : role}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
          {/* <div className="text-right">
            <p className="text-sm text-gray-500 dark:text-gray-400">User ID</p>
            <p className="font-mono text-sm text-gray-900 dark:text-white">{user?.id || 'N/A'}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Tenant ID</p>
            <p className="font-mono text-sm text-gray-900 dark:text-white">{user?.tenant_id || 'N/A'}</p>
          </div> */}
        </div>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center space-x-2">
            <Building2 className="w-8 h-8" />
            <span>Organization Dashboard</span>
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage your organization's members, teams, and credit allocation
          </p>
        </div>
        <div className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 px-3 py-1 rounded-full text-sm font-medium">
          Organization Admin
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Teams</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{teams.length}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Active teams</p>
            </div>
            <Users className="w-8 h-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Members</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{members.length}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Individual + team members</p>
            </div>
            <User className="w-8 h-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Invites Sent</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{inviteAnalytics.total_invitations_sent}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">{inviteAnalytics.acceptance_rate}% acceptance rate</p>
            </div>
            <Mail className="w-8 h-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Credits Remaining</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{creditSummary.remaining_credits.toLocaleString()}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">of {creditSummary.monthly_limit.toLocaleString()} monthly</p>
            </div>
            <CreditCard className="w-8 h-8 text-gray-400" />
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('invite')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'invite'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
          >
            <Mail className="w-4 h-4 mr-2" />
            Invite Members
          </button>
          <button
            onClick={() => setActiveTab('teams')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'teams'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
          >
            <Users className="w-4 h-4 mr-2" />
            Teams
          </button>
          <button
            onClick={() => setActiveTab('members')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'members'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
          >
            <User className="w-4 h-4 mr-2" />
            Members
          </button>
          <button
            onClick={() => setActiveTab('requests')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'requests'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
          >
            <Clock className="w-4 h-4 mr-2" />
            Credit Requests
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {/* Invite Members Tab */}
        {activeTab === 'invite' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 flex items-center space-x-2">
                <Mail className="w-5 h-5" />
                <span>Invite Members & Team Leaders</span>
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Send invitations to individual members and team leaders with credit allocation
              </p>
            </div>

            <div className="space-y-6">
              {/* Invite Settings */}
              <div className="space-y-4">
                <h4 className="text-lg font-medium text-gray-900 dark:text-white">Invite Settings</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      <input
                        type="checkbox"
                        className="mr-2 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        checked={inviteForm.isAdmin}
                        onChange={(e) => setInviteForm(prev => ({ ...prev, isAdmin: e.target.checked }))}
                      />
                      Is Team Leader
                    </label>
                  </div>
                  <div className="space-y-2 md:col-span-1">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Emails (comma-separated)</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                      placeholder="user1@company.com, user2@company.com"
                      value={inviteForm.emails}
                      onChange={(e) => setInviteForm(prev => ({ ...prev, emails: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Credits per Invitee</label>
                    <input
                      type="number"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                      value={inviteForm.creditsPerInvitee}
                      onChange={(e) => setInviteForm(prev => ({ ...prev, creditsPerInvitee: parseInt(e.target.value) || 0 }))}
                    />
                  </div>
                </div>
              </div>


              {/* Validation status */}
              {!allocationValidation.isValid && (
                <div className="border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20 p-3 rounded-md text-sm text-red-700 dark:text-red-300">
                  {allocationValidation.errorMessage || `Not enough credits. Requested ${totalRequestedCredits.toLocaleString()} but only ${availableCredits.toLocaleString()} are available.`}
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end space-x-4 pt-4">
                <button
                  onClick={handleClearInputs}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center space-x-2"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Clear Inputs</span>
                </button>
                <button
                  onClick={handleSendInvites}
                  disabled={!canSendInvites}
                  className={`px-4 py-2 rounded-md transition-colors flex items-center space-x-2 ${canSendInvites ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'bg-gray-300 text-gray-600 cursor-not-allowed'
                    }`}
                >
                  <Send className="w-4 h-4" />
                  <span>Send Invites</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Teams Tab */}
        {activeTab === 'teams' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 flex items-center space-x-2">
                <Users className="w-5 h-5" />
                <span>Team Overview</span>
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Manage teams and their credit pools
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Team Name</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Team Leader</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Members</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Credit Pool</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {teams.map((team) => (
                    <tr key={team.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">{team.name}</td>
                      <td className="py-3 px-4">
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">{team.team_leader_name}</div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">{team.team_leader_email}</div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-gray-900 dark:text-white">{team.member_count}</td>
                      <td className="py-3 px-4">
                        <div className="text-sm">
                          <div className="text-gray-900 dark:text-white">Total: {team.credit_pool_total}</div>
                          <div className="text-gray-900 dark:text-white">Used: {team.credit_pool_used}</div>
                          <div className="font-medium text-green-600 dark:text-green-400">Remaining: {team.credit_pool_remaining}</div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-2">
                          <button className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                            <Eye className="w-4 h-4" />
                          </button>
                          <button className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                            <Settings className="w-4 h-4" />
                          </button>
                          <button className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                            <Pause className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Members Tab */}
        {activeTab === 'members' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 flex items-center space-x-2">
                <User className="w-5 h-5" />
                <span>Member Management</span>
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                View and manage all organization members
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Name</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Role</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Credits Allocated</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Credits Used</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Team</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="py-3 px-4">
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">{member.name}</div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">{member.email}</div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${member.role === 'team_leader'
                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                            : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                          }`}>
                          {member.role === 'team_leader' ? (
                            <>
                              <Crown className="w-3 h-3 inline mr-1" />
                              Team Leader
                            </>
                          ) : (
                            <>
                              <User className="w-3 h-3 inline mr-1" />
                              Member
                            </>
                          )}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-900 dark:text-white">{member.credits_allocated}</td>
                      <td className="py-3 px-4 text-gray-900 dark:text-white">{member.credits_used}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${member.status === 'active'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                            : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                          }`}>
                          {member.status === 'active' ? (
                            <>
                              <CheckCircle className="w-3 h-3 inline mr-1" />
                              Active
                            </>
                          ) : (
                            <>
                              <XCircle className="w-3 h-3 inline mr-1" />
                              Inactive
                            </>
                          )}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-900 dark:text-white">{member.team_name || 'Individual'}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-2">
                          <button className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                            <Plus className="w-4 h-4" />
                          </button>
                          <button className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                            <Pause className="w-4 h-4" />
                          </button>
                          <button className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center space-x-2">
                <CreditCard className="w-5 h-5" />
                <span>Credit Summary</span>
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Total Credits:</span>
                  <span className="font-medium text-gray-900 dark:text-white">{creditSummary.total_credits.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Used Credits:</span>
                  <span className="font-medium text-orange-600 dark:text-orange-400">{creditSummary.used_credits.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Remaining Credits:</span>
                  <span className="font-medium text-green-600 dark:text-green-400">{creditSummary.remaining_credits.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Monthly Limit:</span>
                  <span className="font-medium text-gray-900 dark:text-white">{creditSummary.monthly_limit.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Reset Date:</span>
                  <span className="font-medium text-gray-900 dark:text-white">{new Date(creditSummary.reset_date).toLocaleDateString()}</span>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center space-x-2">
                <Mail className="w-5 h-5" />
                <span>Invitation Analytics</span>
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Total Sent:</span>
                  <span className="font-medium text-gray-900 dark:text-white">{inviteAnalytics.total_invitations_sent}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Accepted:</span>
                  <span className="font-medium text-green-600 dark:text-green-400">{inviteAnalytics.invitations_accepted}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Acceptance Rate:</span>
                  <span className="font-medium text-gray-900 dark:text-white">{inviteAnalytics.acceptance_rate}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Pending:</span>
                  <span className="font-medium text-orange-600 dark:text-orange-400">{inviteAnalytics.pending_invitations}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Credit Requests Tab */}
        {activeTab === 'requests' && (
          <PendingCreditRequestsPanel organizationId="org-1" />
        )}
      </div>
    </div>
  );
}