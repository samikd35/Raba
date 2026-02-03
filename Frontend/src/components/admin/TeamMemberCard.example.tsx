/**
 * TeamMemberCard Component Example
 * 
 * This file demonstrates how to use the TeamMemberCard component
 * in different scenarios.
 */

import TeamMemberCard from './TeamMemberCard';
import { TeamMember } from '@/types/team';

// Example usage in a team leader dashboard
export function TeamMemberListExample() {
  // Sample team members data
  const teamMembers: TeamMember[] = [
    {
      id: '1',
      user_id: 'user-123',
      name: 'John Doe',
      email: 'john.doe@company.com',
      role: 'team_leader',
      team_id: 'team-1',
      team_name: 'Engineering Team',
      credits_allocated: 1000,
      credits_used: 450,
      status: 'active',
      joined_date: '2024-01-15',
    },
    {
      id: '2',
      user_id: 'user-456',
      name: 'Jane Smith',
      email: 'jane.smith@company.com',
      role: 'member',
      team_id: 'team-1',
      team_name: 'Engineering Team',
      credits_allocated: 500,
      credits_used: 120,
      status: 'active',
      joined_date: '2024-02-01',
    },
    {
      id: '3',
      user_id: 'user-789',
      name: 'Bob Johnson',
      email: 'bob.johnson@company.com',
      role: 'member',
      team_id: 'team-1',
      team_name: 'Engineering Team',
      credits_allocated: 500,
      credits_used: 480,
      status: 'frozen',
      joined_date: '2024-01-20',
    },
  ];

  // Handler for suspending a member
  const handleSuspendMember = async (memberId: string) => {
    console.log('Suspending member:', memberId);
    // Call API to suspend member
    // await creditService.freezeCreditLot(organizationId, userId);
  };

  // Handler for removing a member
  const handleRemoveMember = async (memberId: string) => {
    console.log('Removing member:', memberId);
    // Call API to remove member
    // await teamService.removeMember(teamId, userId);
  };

  return (
    <div className="space-y-3">
      {teamMembers.map((member) => (
        <TeamMemberCard
          key={member.id}
          member={member}
          onSuspend={handleSuspendMember}
          onRemove={handleRemoveMember}
          isTeamLeader={member.role === 'team_leader'}
        />
      ))}
    </div>
  );
}

// Example: Team leader (no action buttons)
export function TeamLeaderExample() {
  const teamLeader: TeamMember = {
    id: '1',
    user_id: 'user-123',
    name: 'John Doe',
    email: 'john.doe@company.com',
    role: 'team_leader',
    team_id: 'team-1',
    team_name: 'Engineering Team',
    credits_allocated: 1000,
    credits_used: 450,
    status: 'active',
    joined_date: '2024-01-15',
  };

  return (
    <TeamMemberCard
      member={teamLeader}
      isTeamLeader={true}
      // No onSuspend or onRemove handlers for team leader
    />
  );
}

// Example: Active member (with action buttons)
export function ActiveMemberExample() {
  const activeMember: TeamMember = {
    id: '2',
    user_id: 'user-456',
    name: 'Jane Smith',
    email: 'jane.smith@company.com',
    role: 'member',
    team_id: 'team-1',
    team_name: 'Engineering Team',
    credits_allocated: 500,
    credits_used: 120,
    status: 'active',
    joined_date: '2024-02-01',
  };

  const handleSuspend = async (memberId: string) => {
    console.log('Suspending:', memberId);
  };

  const handleRemove = async (memberId: string) => {
    console.log('Removing:', memberId);
  };

  return (
    <TeamMemberCard
      member={activeMember}
      onSuspend={handleSuspend}
      onRemove={handleRemove}
    />
  );
}

// Example: Frozen member (only remove button)
export function FrozenMemberExample() {
  const frozenMember: TeamMember = {
    id: '3',
    user_id: 'user-789',
    name: 'Bob Johnson',
    email: 'bob.johnson@company.com',
    role: 'member',
    team_id: 'team-1',
    team_name: 'Engineering Team',
    credits_allocated: 500,
    credits_used: 480,
    status: 'frozen',
    joined_date: '2024-01-20',
  };

  const handleRemove = async (memberId: string) => {
    console.log('Removing:', memberId);
  };

  return (
    <TeamMemberCard
      member={frozenMember}
      onRemove={handleRemove}
      // No onSuspend handler since member is already frozen
    />
  );
}

// Example: Empty state
export function EmptyStateExample() {
  return (
    <div className="text-center py-8 text-gray-500 dark:text-gray-400">
      <svg
        className="w-12 h-12 mx-auto mb-3 opacity-50"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
        />
      </svg>
      <p>No team members yet</p>
      <p className="text-sm mt-1">Invite members to get started</p>
    </div>
  );
}

// Example: Loading state
export function LoadingStateExample() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="animate-pulse p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
        >
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
  );
}
