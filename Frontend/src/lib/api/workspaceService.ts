// lib/api/team-workspaceService.ts

import { authService } from '@/services/authService';

export interface Workspace {
    id: string;
    name: string;
    type: 'organization' | 'team' | 'personal';
    role: string;
    member_count: number;
    team_count: number;
    credits_remaining: number;
    last_accessed: string | null;
    is_active: boolean;
    description: string;
  }
  
  export interface WorkspacesResponse {
    organizations: Workspace[];
    teams: Workspace[];
    personal: Workspace | null;
    total_count: number;
  }
  
  export const workspaceService = {
    async getWorkspaces(): Promise<WorkspacesResponse> {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/team-workspaces/contexts`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authService.getCurrentToken()}`,
        },
      });
  
      if (!response.ok) {
        throw new Error('Failed to fetch workspaces');
      }
  
      return response.json();
    },
  };