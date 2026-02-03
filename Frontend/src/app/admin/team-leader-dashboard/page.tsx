"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { teamService } from '@/lib/api/teamService';
import { FormValidator } from '@/lib/validation';
import { toast } from "react-hot-toast";
import { useAuthStore } from '@/stores/authStore';
import { useTeamStore } from '@/stores/teamStore';
import { Users, CreditCard, Mail, AlertTriangle, Calendar, History, RefreshCw } from 'lucide-react';
import CreditRequestModal from '@/components/admin/CreditRequestModal';
import CreditRequestHistoryTable from '@/components/admin/CreditRequestHistoryTable';
import TeamMemberCard from '@/components/admin/TeamMemberCard';
import { Team, TeamMember, TeamResponse } from '@/types/team';
import { creditService } from '@/lib/api/creditService';

export default function TeamLeaderDashboard() {
  const { user } = useAuthStore();
  const { currentTeam, setCurrentTeam, setTeams, setIsLoading: setStoreLoading } = useTeamStore();
  
  const [inviteEmails, setInviteEmails] = useState('');
  const [isInviting, setIsInviting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Load team data function
  const loadTeamData = useCallback(async (showRefreshIndicator = false) => {
    try {
      if (showRefreshIndicator) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setStoreLoading(true);

      // Get the organization ID from the user's current tenant context
      const orgId = user?.tenant_id;
      if (!orgId) {
        console.error('No organization ID found in user context');
        toast.error('No organization context found');
        return;
      }
      
      console.log('Loading teams for organization:', orgId);
      const teams = await teamService.fetchTeams(orgId);
      console.log('Loaded teams:', teams);
      
      // Store all teams in Zustand (convert TeamResponse to Team)
      const teamData: Team[] = teams.map((t: TeamResponse) => ({
        id: t.id,
        name: t.name,
        organization_id: t.organization_id,
        organization_name: t.organization_name || '',
        team_leader_id: t.team_leader_id || '',
        team_leader_name: t.team_leader_name || '',
        team_leader_email: t.team_leader_email || '',
        member_count: t.member_count || 0,
        credit_pool_total: t.credit_pool_total || 0,
        credit_pool_used: t.credit_pool_used || 0,
        credit_pool_remaining: t.credit_pool_remaining || 0,
        pool_reset_date: t.pool_reset_date || '',
        status: t.status || 'active',
        created_at: t.created_at || '',
      }));
      setTeams(teamData);
      
      // Find the team where the current user is the team leader
      const userTeam = teamData.find(
        (t: Team) => t.team_leader_email === user?.email || t.team_leader_id === user?.id
      );
      
      if (userTeam) {
        // Set current team in Zustand store
        setCurrentTeam(userTeam);
        
        // Load team members
        try {
          const members = await teamService.getTeamMembers(userTeam.id);
          setTeamMembers(members);
        } catch (memberError) {
          console.error('Failed to load team members:', memberError);
          // Don't fail the whole load if members fail
          setTeamMembers([]);
        }
      } else {
        console.log('No team found where user is team leader');
        setCurrentTeam(null);
        setTeamMembers([]);
      }
      
      setLastUpdated(new Date());
    } catch (error: any) {
      console.error('Failed to load team data:', error);
      toast.error(error?.message || 'Failed to load team data');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
      setStoreLoading(false);
    }
  }, [user?.tenant_id, user?.email, user?.id, setCurrentTeam, setTeams, setStoreLoading]);

  // Initial load
  useEffect(() => {
    loadTeamData();
  }, [loadTeamData]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      loadTeamData(true);
    }, 30000);

    return () => clearInterval(interval);
  }, [loadTeamData]);

  // Manual refresh handler
  const handleManualRefresh = () => {
    loadTeamData(true);
  };

  // Invite members handler
  const handleSendInvites = async () => {
    setIsInviting(true);
    try {
      if (!currentTeam?.id) {
        toast.error('Team not loaded yet');
        return;
      }
      const emails = inviteEmails
        .split(',')
        .map((e) => e.trim())
        .filter((e) => e.length > 0 && FormValidator.validateEmail(e));
      if (!emails.length) {
        toast.error('Enter at least one valid email');
        return;
      }
      
      const res = await teamService.inviteTeamMembers(currentTeam.id, {
        emails,
        is_admin: false,
      });
      toast.success(res?.message || `Invites sent to ${emails.length} user(s)`);
      setInviteEmails('');
      
      // Refresh team data to get updated member count
      await loadTeamData(true);
    } catch (error: any) {
      console.error('Failed to send invites:', error);
      toast.error(error?.message || 'Failed to send invites');
    } finally {
      setIsInviting(false);
    }
  };

  // Credit request handler
  const handleRequestCredits = () => {
    setShowRequestModal(true);
  };

  // Suspend member handler
  const handleSuspendMember = async (memberId: string) => {
    try {
      if (!currentTeam?.organization_id) {
        toast.error('Organization context not available');
        return;
      }

      // Find the member to get their credit lot ID
      const member = teamMembers.find(m => m.id === memberId);
      if (!member) {
        toast.error('Member not found');
        return;
      }

      // Call creditService to freeze the member's credit lot
      // Note: We need the lot_id, which should be part of the member data
      // For now, we'll use the member's user_id as a fallback
      await creditService.freezeCreditLot(currentTeam.organization_id, member.user_id);
      
      // Refresh team data to get updated member status
      await loadTeamData(true);
    } catch (error: any) {
      console.error('Failed to suspend member:', error);
      throw error; // Re-throw to let TeamMemberCard handle the error display
    }
  };

  // Remove member handler
  const handleRemoveMember = async (memberId: string) => {
    try {
      if (!currentTeam?.id) {
        toast.error('Team context not available');
        return;
      }

      // Find the member to get their user_id
      const member = teamMembers.find(m => m.id === memberId);
      if (!member) {
        toast.error('Member not found');
        return;
      }

      // Call teamService to remove the member
      await teamService.removeMember(currentTeam.id, member.user_id);
      
      // Refresh team data to get updated member list
      await loadTeamData(true);
    } catch (error: any) {
      console.error('Failed to remove member:', error);
      throw error; // Re-throw to let TeamMemberCard handle the error display
    }
  };

  // Calculate credit status
  const creditUsagePercentage = currentTeam 
    ? (currentTeam.credit_pool_used / currentTeam.credit_pool_total) * 100 
    : 0;
  const isLowCredits = currentTeam && currentTeam.credit_pool_remaining < currentTeam.credit_pool_total * 0.2;
  const isOutOfCredits = currentTeam && currentTeam.credit_pool_remaining === 0;

  // Format numbers with locale
  const formatNumber = (num: number) => {
    return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
  };

  // Format date with locale
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Loading skeleton component
  const LoadingSkeleton = () => (
    <div className="animate-pulse">
      <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-24 mb-2"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Team Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage your team members and shared credit pool
          </p>
          {lastUpdated && (
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleManualRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
            title="Refresh data"
          >
            <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
          <span className="px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
            Team Leader
          </span>
        </div>
      </div>

      {/* Alert Banners */}
      {isOutOfCredits && (
        <div className="border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20 p-6 rounded-lg">
        <div className="flex items-center space-x-3">
          <AlertTriangle className="w-6 h-6 text-red-600" />
          <div>
            <p className="font-medium text-red-800 dark:text-red-200">
              Credit Pool Exhausted
            </p>
            <p className="text-sm text-red-600 dark:text-red-300">
              Your team has used all available credits. Contact your organization admin for additional credits.
            </p>
          </div>
            <button 
              className="ml-auto px-4 py-2 border border-red-300 rounded-lg hover:bg-red-100 dark:hover:bg-red-800 text-sm"
              onClick={handleRequestCredits}
            >
              Request Credits
            </button>
          </div>
        </div>
      )}

      {isLowCredits && !isOutOfCredits && (
        <div className="border border-orange-200 bg-orange-50 dark:border-orange-800 dark:bg-orange-900/20 p-6 rounded-lg">
        <div className="flex items-center space-x-3">
          <AlertTriangle className="w-6 h-6 text-orange-600" />
          <div>
            <p className="font-medium text-orange-800 dark:text-orange-200">
              Low Credit Pool
            </p>
            <p className="text-sm text-orange-600 dark:text-orange-300">
              Your team is running low on credits. Consider requesting additional credits from your organization admin.
            </p>
          </div>
            <button 
              className="ml-auto px-4 py-2 border border-orange-300 rounded-lg hover:bg-orange-100 dark:hover:bg-orange-800 text-sm"
              onClick={handleRequestCredits}
            >
              Request Credits
            </button>
          </div>
        </div>
      )}

      {/* Team Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Team Name Card */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Team Name</h3>
            <Users className="w-5 h-5 text-gray-400" />
          </div>
          {isLoading ? (
            <LoadingSkeleton />
          ) : (
            <>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {currentTeam?.name || '—'}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {formatNumber(currentTeam?.member_count ?? 0)} member{currentTeam?.member_count !== 1 ? 's' : ''}
              </p>
            </>
          )}
        </div>

        {/* Credit Pool Total Card */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Credit Pool Total</h3>
            <CreditCard className="w-5 h-5 text-gray-400" />
          </div>
          {isLoading ? (
            <LoadingSkeleton />
          ) : (
            <>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatNumber(currentTeam?.credit_pool_total ?? 0)}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Monthly allocation
              </p>
            </>
          )}
        </div>

        {/* Credits Used Card */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Credits Used</h3>
            <CreditCard className="w-5 h-5 text-gray-400" />
          </div>
          {isLoading ? (
            <LoadingSkeleton />
          ) : (
            <>
              <div className="text-2xl font-bold text-orange-600">
                {formatNumber(currentTeam?.credit_pool_used ?? 0)}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {creditUsagePercentage.toFixed(1)}% of total
              </p>
            </>
          )}
        </div>

        {/* Credits Remaining Card */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Credits Remaining</h3>
            <CreditCard className="w-5 h-5 text-gray-400" />
          </div>
          {isLoading ? (
            <LoadingSkeleton />
          ) : (
            <>
              <div className="text-2xl font-bold text-green-600">
                {formatNumber(currentTeam?.credit_pool_remaining ?? 0)}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Available now
              </p>
            </>
          )}
        </div>
      </div>

      {/* Pool Reset Info */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-3">
          <Calendar className="w-6 h-6 text-blue-600" />
          <div>
            <p className="font-medium text-gray-900 dark:text-white">
              Pool Reset Date
            </p>
            {isLoading ? (
              <div className="animate-pulse">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-48 mt-1"></div>
              </div>
            ) : (
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Your team's credit pool will reset on {currentTeam?.pool_reset_date ? formatDate(currentTeam.pool_reset_date) : '—'}
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Invite Teammates */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Invite Teammates</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Send invitations to new team members
            </p>
          </div>
          <div className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="emails" className="text-sm font-medium text-gray-700 dark:text-gray-300">Email Addresses</label>
              <input
                id="emails"
                type="text"
                placeholder="teammate1@company.com, teammate2@company.com"
                value={inviteEmails}
                onChange={(e) => setInviteEmails(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
              <p className="text-sm text-gray-500">
                Separate multiple emails with commas
              </p>
            </div>
            
            <button 
              className="w-full bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg flex items-center justify-center space-x-2 disabled:opacity-50"
              onClick={handleSendInvites}
              disabled={!inviteEmails.trim() || isInviting || !currentTeam}
            >
              {isInviting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Sending...</span>
                </>
              ) : (
                <>
                  <Mail className="w-4 h-4" />
                  <span>Send Invites</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Team Members */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Team Members</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Manage your team members
            </p>
          </div>
          <div className="space-y-3">
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700"></div>
                      <div className="flex-1">
                        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32 mb-2"></div>
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-48"></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : teamMembers.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No team members yet</p>
                <p className="text-sm mt-1">Invite members to get started</p>
              </div>
            ) : (
              teamMembers.map((member) => (
                <TeamMemberCard
                  key={member.id}
                  member={member}
                  onSuspend={handleSuspendMember}
                  onRemove={handleRemoveMember}
                  isTeamLeader={member.role === 'team_leader'}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Credit Request History */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
              <History className="w-5 h-5" />
              <span>Credit Request History</span>
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Track your credit requests and their status
            </p>
          </div>
        </div>
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
        ) : currentTeam?.id ? (
          <CreditRequestHistoryTable teamId={currentTeam.id} />
        ) : (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <p>No team data available</p>
          </div>
        )}
      </div>

      {/* Credit Request Modal */}
      {currentTeam && (
        <CreditRequestModal
          isOpen={showRequestModal}
          onClose={() => {
            setShowRequestModal(false);
            // Refresh data after closing modal to get updated credit requests
            loadTeamData(true);
          }}
          teamId={currentTeam.id}
          currentCredits={{
            total: currentTeam.credit_pool_total || 0,
            used: currentTeam.credit_pool_used || 0,
            remaining: currentTeam.credit_pool_remaining || 0,
          }}
        />
      )}
    </div>
  );
}
