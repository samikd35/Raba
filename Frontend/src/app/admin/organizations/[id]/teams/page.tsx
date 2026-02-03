"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import { Building2, Users, CreditCard, UserCheck, Plus, AlertCircle, TrendingUp, X, Mail } from 'lucide-react';

// Force dynamic rendering to prevent build errors
export const dynamic = 'force-dynamic';

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
}

interface TeamMember {
  user_id: string;
  user_email: string;
  user_name: string;
  role: string;
  status: string;
  credits_allocated: number;
  credits_used: number;
}

interface TeamsData {
  teams: Team[];
}

export default function OrganizationTeamsPage() {
  const router = useRouter();
  const params = useParams();
  const organizationId = params.id as string;
  const { isAuthenticated } = useAuthStore();
  
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);

  useEffect(() => {
    // if (!isAuthenticated) {
    //   router.push('/signin?redirect=/admin/organizations/' + organizationId + '/teams');
    //   return;
    // }
    
    if (organizationId) {
      fetchTeamsData();
    }
  }, [organizationId, isAuthenticated]);

  const fetchTeamsData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch teams data from the teams overview endpoint
      const teamsData = await organizationService.getOrganizationTeams(organizationId);
      
      // Transform backend data to match frontend interface
      const transformedTeams: Team[] = teamsData.teams.map(team => ({
        team_id: team.team_id,
        team_name: team.team_name,
        member_count: team.members_count,
        leader_name: team.team_leader?.full_name || 'No leader assigned',
        leader_email: team.team_leader?.email || '',
        credits: {
          total: team.credit_pool.total,
          used: team.credit_pool.used,
          remaining: team.credit_pool.remaining,
        }
      }));
      
      setTeams(transformedTeams);
    } catch (err: any) {
      console.error('Error fetching teams data:', err);
      setError(err.message || 'Failed to fetch teams data');
      toast.error(err.message || 'Failed to fetch teams data');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    router.push(`/admin/organizations/${organizationId}`);
  };

  const handleRefresh = () => {
    fetchTeamsData();
  };

  const getTotalMembers = () => {
    return teams.reduce((total, team) => total + team.member_count, 0);
  };

  const getTotalCredits = () => {
    return teams.reduce((total, team) => total + team.credits.total, 0);
  };

  const getTotalUsedCredits = () => {
    return teams.reduce((total, team) => total + team.credits.used, 0);
  };

  const handleViewDetails = async (team: Team) => {
    setSelectedTeam(team);
    setLoadingMembers(true);
    try {
      // Fetch team members for this specific team
      const membersData = await organizationService.getOrganizationMembers(organizationId);
      // Filter members for this specific team
      const teamSpecificMembers = membersData.members
        .filter(m => m.team_id === team.team_id)
        .map(m => ({
          user_id: m.user_id,
          user_email: '', // Not provided by current endpoint
          user_name: m.name,
          role: m.role,
          status: m.status,
          credits_allocated: m.credits_allocated,
          credits_used: m.credits_used,
        }));
      setTeamMembers(teamSpecificMembers);
    } catch (err: any) {
      console.error('Error fetching team members:', err);
      toast.error('Failed to fetch team members');
    } finally {
      setLoadingMembers(false);
    }
  };

  const handleCloseModal = () => {
    setSelectedTeam(null);
    setTeamMembers([]);
  };

  const getRoleColor = (role: string) => {
    switch (role.toLowerCase()) {
      case 'owner':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'admin':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'member':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'inactive':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <div className="text-red-800 dark:text-red-200">
          <h3 className="font-medium">Error loading teams</h3>
          <p className="mt-1 text-sm">{error}</p>
          <div className="flex space-x-3 mt-3">
            <button
              onClick={handleBack}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-sm"
            >
              Back to Organization
            </button>
            <button
              onClick={fetchTeamsData}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={handleBack}
          >
            <span className="text-lg">⬅️</span>
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
        <div className="flex space-x-3">
          <Button onClick={handleRefresh}>
            <span className="text-lg mr-2">🔄</span>
            Refresh
          </Button>
          <Button onClick={() => router.push(`/admin/organizations/${organizationId}/invite-members`)}>
            <Plus className="w-4 h-4 mr-2" />
            Invite Team Leaders
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Building2 className="w-5 h-5 text-blue-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {teams.length}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Total Teams</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Users className="w-5 h-5 text-green-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {getTotalMembers()}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Total Members</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <CreditCard className="w-5 h-5 text-purple-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {getTotalCredits()}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Total Credits</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-orange-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {getTotalUsedCredits()}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Credits Used</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Teams List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Building2 className="w-5 h-5" />
            <span>All Teams</span>
          </CardTitle>
          <CardDescription>
            Teams within this organization and their resource allocation
          </CardDescription>
        </CardHeader>
        <CardContent>
          {teams.length === 0 ? (
            <div className="text-center py-12">
              <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No teams found
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                This organization doesn't have any teams yet.
              </p>
              <Button onClick={() => router.push(`/admin/organizations/${organizationId}/invite-members`)}>
                <Plus className="w-4 h-4 mr-2" />
                Invite First Team Leader
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {teams.map((team) => (
                <Card key={team.team_id} className="hover:shadow-lg transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{team.team_name}</CardTitle>
                      <Badge variant="outline">
                        {team.member_count} member{team.member_count !== 1 ? 's' : ''}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Team Leader */}
                    <div>
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Team Leader</p>
                      <p className="text-sm text-gray-900 dark:text-white">{team.leader_name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{team.leader_email}</p>
                    </div>

                    {/* Credits */}
                    <div>
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Credits</p>
                      <div className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600 dark:text-gray-400">Total:</span>
                          <span className="font-medium">{team.credits.total}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600 dark:text-gray-400">Used:</span>
                          <span className="font-medium">{team.credits.used}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600 dark:text-gray-400">Remaining:</span>
                          <span className="font-medium text-green-600 dark:text-green-400">
                            {team.credits.remaining}
                          </span>
                        </div>
                      </div>
                      
                      {/* Progress Bar */}
                      <div className="mt-2">
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                          <div 
                            className="bg-blue-500 h-2 rounded-full transition-all duration-300" 
                            style={{ 
                              width: `${team.credits.total > 0 ? (team.credits.used / team.credits.total) * 100 : 0}%` 
                            }}
                          ></div>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {team.credits.total > 0 ? Math.round((team.credits.used / team.credits.total) * 100) : 0}% used
                        </p>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex space-x-2 pt-2">
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="flex-1"
                        onClick={() => handleViewDetails(team)}
                      >
                        View Details
                      </Button>
                      <Button variant="outline" size="sm" className="flex-1">
                        Manage Credits
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Team Members Modal */}
      {selectedTeam && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  {selectedTeam.team_name}
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Team members and their details
                </p>
              </div>
              <Button variant="ghost" size="icon" onClick={handleCloseModal}>
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
              {/* Team Info Summary */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-2">
                      <Users className="w-4 h-4 text-blue-500" />
                      <div>
                        <p className="text-lg font-bold">{selectedTeam.member_count}</p>
                        <p className="text-xs text-gray-500">Members</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-2">
                      <CreditCard className="w-4 h-4 text-green-500" />
                      <div>
                        <p className="text-lg font-bold">{selectedTeam.credits.total}</p>
                        <p className="text-xs text-gray-500">Total Credits</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-2">
                      <TrendingUp className="w-4 h-4 text-orange-500" />
                      <div>
                        <p className="text-lg font-bold">{selectedTeam.credits.remaining}</p>
                        <p className="text-xs text-gray-500">Remaining</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Team Leader Info */}
              <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Team Leader</h3>
                <p className="text-base font-medium text-gray-900 dark:text-white">{selectedTeam.leader_name}</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">{selectedTeam.leader_email}</p>
              </div>

              {/* Team Members List */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Team Members</h3>
                {loadingMembers ? (
                  <div className="flex justify-center items-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
                  </div>
                ) : teamMembers.length === 0 ? (
                  <div className="text-center py-8">
                    <Users className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-500 dark:text-gray-400">No members found in this team</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-200 dark:border-gray-700">
                          <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Member</th>
                          <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Role</th>
                          <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Credits</th>
                          <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {teamMembers.map((member) => (
                          <tr key={member.user_id} className="border-b border-gray-100 dark:border-gray-800">
                            <td className="py-3 px-4">
                              <div>
                                <p className="font-medium text-gray-900 dark:text-white">
                                  {member.user_name || member.user_email}
                                </p>
                                {member.user_email && (
                                  <p className="text-sm text-gray-500 dark:text-gray-400">
                                    {member.user_email}
                                  </p>
                                )}
                              </div>
                            </td>
                            <td className="py-3 px-4">
                              <Badge className={getRoleColor(member.role)}>
                                {member.role}
                              </Badge>
                            </td>
                            <td className="py-3 px-4">
                              <div className="text-sm">
                                <p className="text-gray-900 dark:text-white">
                                  {member.credits_used} / {member.credits_allocated}
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                  {member.credits_allocated - member.credits_used} remaining
                                </p>
                              </div>
                            </td>
                            <td className="py-3 px-4">
                              <Badge className={getStatusColor(member.status)}>
                                {member.status}
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700">
              <Button variant="outline" onClick={handleCloseModal}>
                Close
              </Button>
              <Button onClick={() => router.push(`/admin/organizations/${organizationId}/invite-members`)}>
                <Mail className="w-4 h-4 mr-2" />
                Invite More Members
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
