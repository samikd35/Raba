"use client";

import React, { useState, useEffect } from 'react';
import { toast } from "react-hot-toast";
import { teamService } from '@/lib/api/teamService';
import { organizationService } from '@/lib/api/organizationService';
import { Search, Filter, Mail, Plus, Pause, Trash2 } from 'lucide-react';

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'member' | 'team_leader' | 'admin';
  team_id?: string;
  team_name?: string;
  credits_allocated: number;
  credits_used: number;
  status: 'active' | 'frozen' | 'suspended';
  joined_date: string;
}

export default function MembersPage() {
    const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
                const [organizations, setOrganizations] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>('');
  const [teams, setTeams] = useState<any[]>([]);

  useEffect(() => {
    initOrganizations();
  }, []);

  useEffect(() => {
    if (selectedOrgId) {
      loadTeamsForOrg(selectedOrgId);
    }
  }, [selectedOrgId]);

  const initOrganizations = async () => {
    try {
      setLoading(true);
      const orgs = await organizationService.fetchOrganizations();
      const mapped = orgs.map((o: any) => ({ id: o.id, name: o.name }));
      setOrganizations(mapped);
      if (mapped.length) setSelectedOrgId(mapped[0].id);
    } catch (e: any) {
      setError(e.message || 'Failed to load organizations');
      toast.error(e.message || 'Failed to load organizations');
    } finally {
      setLoading(false);
    }
  };

  const loadTeamsForOrg = async (orgId: string) => {
    try {
      setLoading(true);
      const fetchedTeams = await teamService.fetchTeams(orgId);
      setTeams(fetchedTeams);
      // Rebuild members from teams
      buildMembersFromTeams(fetchedTeams);
    } catch (e: any) {
      setError(e.message || 'Failed to load teams');
      toast.error(e.message || 'Failed to load teams');
    } finally {
      setLoading(false);
    }
  };

  
  const buildMembersFromTeams = (fetchedTeams: any[]) => {
    // Synthesize members from teams: include team leaders as members with basic credit info
    const synthesized: TeamMember[] = fetchedTeams.map((t: any, idx: number) => ({
      id: `tl_${t.id}`,
      name: t.team_leader_name || `Team Leader ${idx + 1}`,
      email: t.team_leader_email || `leader${idx + 1}@example.com`,
      role: 'team_leader',
      team_id: t.id,
      team_name: t.name,
      credits_allocated: Math.max(100, Math.floor((t.credit_pool_total || 0) / Math.max(t.member_count || 1, 1))),
      credits_used: Math.floor((t.credit_pool_used || 0) / Math.max(t.member_count || 1, 1)),
      status: 'active',
      joined_date: new Date().toISOString().slice(0, 10),
    }));
    setMembers(synthesized);
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
          <button
            onClick={initOrganizations}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            All Members
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage all members across all organizations
          </p>
        </div>
              </div>

      {/* Organization selector */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Organization</label>
          <select
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            value={selectedOrgId}
            onChange={(e) => setSelectedOrgId(e.target.value)}
          >
            {organizations.map((o) => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
        </div>
      </div>

      

      {/* Filters and Search */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search members..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2">
              <Filter className="w-4 h-4" />
              <span>Filter</span>
            </button>
            <button className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
              All Roles
            </button>
            <button className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
              All Status
            </button>
            <button className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
              All Teams
            </button>
          </div>
        </div>
      </div>

      {/* Members Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Members Overview</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">All members across all organizations with their roles and credit usage</p>
        </div>
        <div className="p-6">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Member</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Role</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Team</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Credits Allocated</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Credits Used</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Joined</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Actions</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-full bg-brand-500 flex items-center justify-center">
                          <span className="text-white text-sm font-medium">
                            {member.name.split(' ').map(n => n[0]).join('')}
                          </span>
                        </div>
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">
                            {member.name}
                          </div>
                          <div className="text-sm text-gray-500">{member.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        member.role === 'admin' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' :
                        member.role === 'team_leader' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                        'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                      }`}>
                        {member.role === 'admin' ? 'Admin' : 
                         member.role === 'team_leader' ? 'Team Leader' : 'Member'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {member.team_name || (
                        <span className="text-gray-400 italic">Individual</span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-medium">
                      {member.credits_allocated}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium">{member.credits_used}</span>
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-brand-500 h-2 rounded-full" 
                            style={{ 
                              width: `${Math.min((member.credits_used / member.credits_allocated) * 100, 100)}%` 
                            }}
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        member.status === 'active' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                        member.status === 'frozen' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' :
                        'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                      }`}>
                        {member.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      {new Date(member.joined_date).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                          <Mail className="w-4 h-4" />
                        </button>
                        <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                          <Plus className="w-4 h-4" />
                        </button>
                        <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                          <Pause className="w-4 h-4" />
                        </button>
                        <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
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
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{members.length}</div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Total Members</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {members.filter(member => member.status === 'active').length}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Active Members</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {members.filter(member => member.role === 'team_leader').length}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Team Leaders</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {members.reduce((sum, member) => sum + member.credits_used, 0)}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Total Credits Used</p>
        </div>
      </div>
    </div>
  );
}