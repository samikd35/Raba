"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import { Users, Mail, Shield, UserCheck, Clock, AlertCircle, Trash2 } from 'lucide-react';

interface IndividualMember {
  user_id: string;
  user_email: string;
  user_name: string;
  role: string;
  status: string;
  joined_at: string;
  credits_allocated: number;
  credits_used: number;
}

interface MembersData {
  members: IndividualMember[];
}

export default function OrganizationMembersPage() {
  const router = useRouter();
  const params = useParams();
  const organizationId = params.id as string;
  const { isAuthenticated } = useAuthStore();
  
  const [members, setMembers] = useState<IndividualMember[]>([]);
  const [teamsCount, setTeamsCount] = useState<number>(0);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // if (!isAuthenticated) {
    //   router.push('/signin?redirect=/admin/organizations/' + organizationId + '/members');
    //   return;
    // }
    
    if (organizationId) {
      fetchMembersData();
    }
  }, [organizationId, isAuthenticated]);

  const fetchMembersData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch metrics, teams data, and individual members
      const [metricsData, teamsData, individualMembersData] = await Promise.all([
        organizationService.getOrganizationMetrics(organizationId),
        organizationService.getOrganizationTeams(organizationId),
        organizationService.getIndividualMembers(organizationId)
      ]);
      
      // Store metrics for displaying counts
      setMetrics(metricsData);
      setTeamsCount(teamsData.teams.length);
      
      // Transform individual members data to match our interface
      const transformedMembers: IndividualMember[] = individualMembersData.members.map(member => ({
        user_id: member.user_id,
        user_email: member.email,
        user_name: member.name,
        role: member.role,
        status: member.status,
        joined_at: member.joined_at,
        credits_allocated: member.credits_allocated,
        credits_used: member.credits_used,
      }));
      
      setMembers(transformedMembers);
      
      console.log('🔍 Fetched metrics:', metricsData);
      console.log('🔍 Teams count:', teamsCount);
      console.log('🔍 Individual members:', transformedMembers);
    } catch (err: any) {
      console.error('Error fetching members data:', err);
      setError(err.message || 'Failed to fetch members data');
      toast.error(err.message || 'Failed to fetch members data');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    router.push(`/admin/organizations/${organizationId}`);
  };

  const handleRefresh = () => {
    fetchMembersData();
  };

  const handleDeleteMember = async (userId: string, userName: string) => {
    if (!confirm(`Are you sure you want to remove ${userName} from this organization? This will return any allocated credits and allow them to be re-invited.`)) {
      return;
    }

    try {
      const result = await organizationService.deleteOrganizationMember(organizationId, userId);
      
      if (result.success) {
        toast.success(`${userName} removed successfully. ${result.credits_returned} credits returned.`);
        // Refresh the members list
        fetchMembersData();
      }
    } catch (err: any) {
      console.error('Error deleting member:', err);
      toast.error(err.message || 'Failed to delete member');
    }
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
          <h3 className="font-medium">Error loading members</h3>
          <p className="mt-1 text-sm">{error}</p>
          <div className="flex space-x-3 mt-3">
            <button
              onClick={handleBack}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-sm"
            >
              Back to Organization
            </button>
            <button
              onClick={fetchMembersData}
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
              Organization Members
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage team members across all teams
            </p>
          </div>
        </div>
        <div className="flex space-x-3">
          <Button onClick={handleRefresh}>
            <span className="text-lg mr-2">🔄</span>
            Refresh
          </Button>
          <Button onClick={() => router.push(`/admin/organizations/${organizationId}/invite-members`)}>
            <span className="text-lg mr-2">📤</span>
            Invite Members
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Users className="w-5 h-5 text-blue-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {metrics?.membership?.total || 0}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Total Members</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <UserCheck className="w-5 h-5 text-green-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {teamsCount}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Teams</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Shield className="w-5 h-5 text-purple-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {metrics?.membership?.individual_members || 0}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Individual Members</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Clock className="w-5 h-5 text-yellow-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {members.filter(m => m.status === 'pending').length}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Pending</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Individual Members List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Shield className="w-5 h-5" />
            <span>Individual Members</span>
          </CardTitle>
          <CardDescription>
            Organization members who are not part of any team. Team members are shown in the Teams page.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {members.length === 0 ? (
            <div className="text-center py-12">
              <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No individual members found
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                All organization members are currently part of teams. Individual members who join directly will appear here.
              </p>
              <Button onClick={() => router.push(`/admin/organizations/${organizationId}/invite-members`)}>
                <Mail className="w-4 h-4 mr-2" />
                Invite Members
              </Button>
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
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Joined</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.user_id} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-4 px-4">
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {member.user_name || member.user_email}
                          </p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {member.user_email}
                          </p>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <Badge className={getRoleColor(member.role)}>
                          {member.role}
                        </Badge>
                      </td>
                      <td className="py-4 px-4">
                        <div className="text-sm">
                          <p className="text-gray-900 dark:text-white">
                            {member.credits_used} / {member.credits_allocated}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {member.credits_allocated - member.credits_used} remaining
                          </p>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <Badge className={getStatusColor(member.status)}>
                          {member.status}
                        </Badge>
                      </td>
                      <td className="py-4 px-4">
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {member.joined_at ? new Date(member.joined_at).toLocaleDateString() : 'N/A'}
                        </p>
                      </td>
                      <td className="py-4 px-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteMember(member.user_id, member.user_name || member.user_email)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
