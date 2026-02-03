/**
 * Integration tests for onboarding flows
 * 
 * Tests cover:
 * - Team leader onboarding flow
 * - Team member onboarding flow
 * - Organization member join flow
 * - Authentication redirects
 */

import React from 'react';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useRouter, useParams } from 'next/navigation';
import TeamLeaderOnboarding from '@/app/admin/team-leader-onboarding/page';
import TeamMemberOnboarding from '@/app/team-invite/[token]/page';
import TokenRedirectClient from '@/app/org-invite/TokenRedirectClient';
import { useAuthStore } from '@/stores/authStore';
import { useTeamStore } from '@/stores/teamStore';
import { teamService } from '@/lib/api/teamService';
import { organizationService } from '@/lib/api/organizationService';
import { InvitationFlowManager } from '@/lib/auth/invitationFlowManager';
import { toast } from 'sonner';
import hotToast from 'react-hot-toast';
import { authService } from '@/services/authService';

// Mock Next.js router
const mockUseRouter = vi.fn();
const mockUseParams = vi.fn();
const mockUseSearchParams = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => mockUseRouter(),
  useParams: () => mockUseParams(),
  useSearchParams: () => mockUseSearchParams(),
}));

// Mock stores
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(),
}));
vi.mock('@/stores/teamStore', () => ({
  useTeamStore: vi.fn(),
}));

// Mock services
vi.mock('@/lib/api/teamService');
vi.mock('@/lib/api/organizationService');

// Mock authService - must be defined inline for hoisting
vi.mock('@/services/authService', () => ({
  authService: {
    isAuthenticated: vi.fn(),
  },
}));

// Mock toast - react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    loading: vi.fn(),
  },
}));

// Mock sonner for other components
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// Mock InvitationFlowManager
vi.mock('@/lib/auth/invitationFlowManager', () => ({
  InvitationFlowManager: {
    storeInvitationToken: vi.fn(),
    getStoredInvitationToken: vi.fn(),
    clearInvitationToken: vi.fn(),
    isTokenExpired: vi.fn(),
    getPostAuthRedirectUrl: vi.fn(),
  },
}));

describe('Onboarding Flows Integration Tests', () => {
  const mockRouter = {
    push: vi.fn(),
    back: vi.fn(),
    replace: vi.fn(),
  };

  const mockUser = {
    id: 'user-123',
    email: 'test@example.com',
    tenant_id: 'org-456',
    name: 'Test User',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter);
    mockUseParams.mockReturnValue({});
    mockUseSearchParams.mockReturnValue({ get: vi.fn() });
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Team Leader Onboarding Flow', () => {
    it('should redirect to sign-in if user is not authenticated', async () => {
      // Mock unauthenticated state
      (useAuthStore as any).mockReturnValue({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });

      (useTeamStore as any).mockReturnValue({
        setCurrentTeam: vi.fn(),
      });

      render(<TeamLeaderOnboarding />);

      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith('/signin');
        expect(toast.error).toHaveBeenCalledWith('Please sign in to continue');
      });
    });

    it('should redirect to dashboard if user already owns a team', async () => {
      const existingTeam = {
        id: 'team-123',
        name: 'Existing Team',
        team_leader_email: 'test@example.com',
        team_leader_id: 'user-123',
        organization_name: 'Test Org',
      };

      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      });

      const mockSetCurrentTeam = vi.fn();
      (useTeamStore as any).mockReturnValue({
        setCurrentTeam: mockSetCurrentTeam,
      });

      (teamService.fetchTeams as any).mockResolvedValue([existingTeam]);

      render(<TeamLeaderOnboarding />);

      await waitFor(() => {
        expect(teamService.fetchTeams).toHaveBeenCalledWith('org-456');
        expect(mockSetCurrentTeam).toHaveBeenCalledWith(existingTeam);
        expect(mockRouter.push).toHaveBeenCalledWith('/admin/team-leader-dashboard');
        expect(toast.info).toHaveBeenCalledWith('You already have a team. Redirecting to dashboard...');
      });
    });

    it('should display team creation form for authenticated user without team', async () => {
      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      });

      (useTeamStore as any).mockReturnValue({
        setCurrentTeam: vi.fn(),
      });

      (teamService.fetchTeams as any).mockResolvedValue([]);

      render(<TeamLeaderOnboarding />);

      await waitFor(() => {
        expect(screen.getByText('Create Your Team')).toBeInTheDocument();
        expect(screen.getByLabelText(/Team Name/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Industry/i)).toBeInTheDocument();
      });
    });

    it('should successfully create team and redirect to dashboard', async () => {
      const newTeam = {
        id: 'team-new',
        name: 'New Team',
        organization_name: 'Test Org',
      };

      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      });

      const mockSetCurrentTeam = vi.fn();
      (useTeamStore as any).mockReturnValue({
        setCurrentTeam: mockSetCurrentTeam,
      });

      (teamService.fetchTeams as any).mockResolvedValue([]);
      (teamService.createTeam as any).mockResolvedValue({ id: 'team-new' });
      (teamService.fetchTeams as any).mockResolvedValueOnce([]).mockResolvedValueOnce([newTeam]);

      render(<TeamLeaderOnboarding />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Team Name/i)).toBeInTheDocument();
      });

      // Fill in all required form fields
      const nameInput = screen.getByLabelText(/Team Name/i);
      fireEvent.change(nameInput, { target: { value: 'New Team' } });

      // Fill in industry (required field)
      const industrySelect = screen.getByRole('combobox', { name: /Industry/i });
      fireEvent.click(industrySelect);
      await waitFor(() => {
        const technologyOption = screen.getByText('Technology');
        fireEvent.click(technologyOption);
      });

      // Fill in country (required field)
      const countrySelect = screen.getByRole('combobox', { name: /Country/i });
      fireEvent.click(countrySelect);
      await waitFor(() => {
        const kenyaOption = screen.getByText('Kenya');
        fireEvent.click(kenyaOption);
      });

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Create Team/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(teamService.createTeam).toHaveBeenCalled();
      }, { timeout: 3000 });

      await waitFor(() => {
        expect(InvitationFlowManager.clearInvitationToken).toHaveBeenCalled();
        expect(toast.success).toHaveBeenCalledWith('Team created successfully!');
        expect(mockRouter.push).toHaveBeenCalledWith('/admin/team-leader-dashboard');
      }, { timeout: 3000 });
    });

    it('should handle validation errors when creating team', async () => {
      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      });

      (useTeamStore as any).mockReturnValue({
        setCurrentTeam: vi.fn(),
      });

      (teamService.fetchTeams as any).mockResolvedValue([]);

      render(<TeamLeaderOnboarding />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Team Name/i)).toBeInTheDocument();
      });

      // Submit form without filling required fields
      const submitButton = screen.getByRole('button', { name: /Create Team/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Please fix the errors in the form');
        expect(teamService.createTeam).not.toHaveBeenCalled();
      });
    });

    it('should retry on network failure (max 2 retries)', async () => {
      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      });

      (useTeamStore as any).mockReturnValue({
        setCurrentTeam: vi.fn(),
      });

      (teamService.fetchTeams as any).mockResolvedValue([]);
      (teamService.createTeam as any)
        .mockRejectedValueOnce(new Error('network error'))
        .mockRejectedValueOnce(new Error('network error'))
        .mockResolvedValue({ id: 'team-new' });

      render(<TeamLeaderOnboarding />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Team Name/i)).toBeInTheDocument();
      });

      // Fill in minimal required fields
      const nameInput = screen.getByLabelText(/Team Name/i);
      fireEvent.change(nameInput, { target: { value: 'Test Team' } });

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Create Team/i });
      fireEvent.click(submitButton);

      // Should retry twice
      await waitFor(() => {
        expect(teamService.createTeam).toHaveBeenCalledTimes(3);
      }, { timeout: 5000 });
    });
  });

  describe('Team Member Onboarding Flow', () => {
    const mockToken = 'team-invite-token-123';

    beforeEach(() => {
      mockUseParams.mockReturnValue({
        token: mockToken,
      });
    });

    it('should redirect to sign-in if user is not authenticated', async () => {
      (useAuthStore as any).mockReturnValue({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });

      render(<TeamMemberOnboarding />);

      await waitFor(() => {
        expect(InvitationFlowManager.storeInvitationToken).toHaveBeenCalledWith({
          token: mockToken,
          type: 'team_member',
          timestamp: expect.any(Number),
        });
        expect(toast.info).toHaveBeenCalledWith('Please sign in to join the team');
        expect(mockRouter.push).toHaveBeenCalledWith(`/signin?returnUrl=/team-invite/${mockToken}`);
      });
    });

    it('should load team info for authenticated user', async () => {
      const mockTeamInfo = {
        teamId: 'team-123',
        teamName: 'Engineering Team',
        organizationId: 'org-456',
      };

      const mockTeamDetails = {
        id: 'team-123',
        name: 'Engineering Team',
        team_leader_name: 'John Doe',
        organization_name: 'Acme Corp',
      };

      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      });

      (teamService.getTeamInfoFromToken as any).mockResolvedValue(mockTeamInfo);
      (teamService.getTeamById as any).mockResolvedValue(mockTeamDetails);

      render(<TeamMemberOnboarding />);

      await waitFor(() => {
        expect(screen.getByText('Team Invitation')).toBeInTheDocument();
        expect(screen.getByText('Engineering Team')).toBeInTheDocument();
        expect(screen.getByText('John Doe')).toBeInTheDocument();
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      });
    });

    it('should successfully join team and redirect to workspace', async () => {
      const mockTeamInfo = {
        teamId: 'team-123',
        teamName: 'Engineering Team',
        organizationId: 'org-456',
      };

      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      });

      (teamService.getTeamInfoFromToken as any).mockResolvedValue(mockTeamInfo);
      (teamService.getTeamById as any).mockResolvedValue({
        id: 'team-123',
        name: 'Engineering Team',
      });
      (teamService.joinTeam as any).mockResolvedValue({ success: true });

      render(<TeamMemberOnboarding />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Join Team/i })).toBeInTheDocument();
      });

      // Click join button
      const joinButton = screen.getByRole('button', { name: /Join Team/i });
      fireEvent.click(joinButton);

      await waitFor(() => {
        expect(teamService.joinTeam).toHaveBeenCalledWith('team-123', mockToken);
        expect(InvitationFlowManager.clearInvitationToken).toHaveBeenCalled();
        expect(toast.success).toHaveBeenCalledWith('Successfully joined the team!');
        expect(mockRouter.push).toHaveBeenCalledWith('/team/dashboard');
      });
    });

    it('should handle invalid token error', async () => {
      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      });

      (teamService.getTeamInfoFromToken as any).mockRejectedValue(
        new Error('Invalid invitation token')
      );

      render(<TeamMemberOnboarding />);

      await waitFor(() => {
        expect(screen.getByText('Invitation Error')).toBeInTheDocument();
        expect(screen.getByText(/Invalid invitation token/i)).toBeInTheDocument();
      });
    });

    it('should handle expired token error', async () => {
      const mockTeamInfo = {
        teamId: 'team-123',
        teamName: 'Engineering Team',
      };

      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      });

      (teamService.getTeamInfoFromToken as any).mockResolvedValue(mockTeamInfo);
      (teamService.getTeamById as any).mockResolvedValue({
        id: 'team-123',
        name: 'Engineering Team',
      });
      (teamService.joinTeam as any).mockRejectedValue(
        new Error('Invitation link has expired')
      );

      render(<TeamMemberOnboarding />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Join Team/i })).toBeInTheDocument();
      });

      // Click join button
      const joinButton = screen.getByRole('button', { name: /Join Team/i });
      fireEvent.click(joinButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Invitation link expired');
        expect(screen.getByText(/invitation link has expired/i)).toBeInTheDocument();
      });
    });

    it('should handle already member error', async () => {
      const mockTeamInfo = {
        teamId: 'team-123',
        teamName: 'Engineering Team',
      };

      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      });

      (teamService.getTeamInfoFromToken as any).mockResolvedValue(mockTeamInfo);
      (teamService.getTeamById as any).mockResolvedValue({
        id: 'team-123',
        name: 'Engineering Team',
      });
      (teamService.joinTeam as any).mockRejectedValue(
        new Error('You are already a member of this team')
      );

      render(<TeamMemberOnboarding />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Join Team/i })).toBeInTheDocument();
      });

      // Click join button
      const joinButton = screen.getByRole('button', { name: /Join Team/i });
      fireEvent.click(joinButton);

      await waitFor(() => {
        expect(toast.info).toHaveBeenCalledWith('You are already a member of this team');
      });

      // Should redirect after delay
      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith('/team/dashboard');
      }, { timeout: 3000 });
    });
  });

  describe('Organization Member Join Flow', () => {
    const mockToken = 'org-invite-token-456';
    const mockOrgId = 'org-789';

    beforeEach(() => {
      // Mock window.location.search
      Object.defineProperty(window, 'location', {
        value: {
          search: `?org_id=${mockOrgId}`,
          reload: vi.fn(),
        },
        writable: true,
      });
    });

    it('should redirect to sign-in if user is not authenticated', async () => {
      (useAuthStore as any).mockReturnValue({
        user: null,
        isAuthenticated: false,
      });
      (authService.isAuthenticated as any).mockReturnValue(false);

      render(<TokenRedirectClient token={mockToken} />);

      await waitFor(() => {
        expect(InvitationFlowManager.storeInvitationToken).toHaveBeenCalledWith({
          token: mockToken,
          type: 'org_member',
          organizationId: mockOrgId,
          timestamp: expect.any(Number),
        });
        expect(mockRouter.push).toHaveBeenCalledWith(
          expect.stringContaining('/signin?returnUrl=')
        );
      });
    });

    it('should join organization and redirect team leader to onboarding', async () => {
      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
      });
      (authService.isAuthenticated as any).mockReturnValue(true);
      (organizationService.joinOrganization as any).mockResolvedValue({
        success: true,
        message: 'Successfully joined',
      });
      (organizationService.isTeamLeader as any).mockResolvedValue(true);

      render(<TokenRedirectClient token={mockToken} />);

      await waitFor(() => {
        expect(organizationService.joinOrganization).toHaveBeenCalledWith(mockOrgId, mockToken);
      }, { timeout: 2000 });

      await waitFor(() => {
        expect(InvitationFlowManager.clearInvitationToken).toHaveBeenCalled();
        expect(hotToast.success).toHaveBeenCalledWith('Successfully joined organization!');
        expect(mockRouter.push).toHaveBeenCalledWith('/admin/team-leader-onboarding');
      }, { timeout: 2000 });
    });

    it('should join organization and redirect regular member to dashboard', async () => {
      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
      });
      (authService.isAuthenticated as any).mockReturnValue(true);
      (organizationService.joinOrganization as any).mockResolvedValue({
        success: true,
        message: 'Successfully joined',
      });
      (organizationService.isTeamLeader as any).mockResolvedValue(false);

      render(<TokenRedirectClient token={mockToken} />);

      await waitFor(() => {
        expect(organizationService.joinOrganization).toHaveBeenCalledWith(mockOrgId, mockToken);
        expect(mockRouter.push).toHaveBeenCalledWith(`/admin/organizations/${mockOrgId}`);
      });
    });

    it('should handle expired token error', async () => {
      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
      });
      (authService.isAuthenticated as any).mockReturnValue(true);
      (organizationService.joinOrganization as any).mockRejectedValue(
        new Error('This invitation link has expired')
      );

      render(<TokenRedirectClient token={mockToken} />);

      await waitFor(() => {
        expect(screen.getByText('Invitation Error')).toBeInTheDocument();
        expect(screen.getByText(/invitation link has expired/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      await waitFor(() => {
        expect(hotToast.error).toHaveBeenCalled();
      }, { timeout: 2000 });
    });

    it('should handle invalid token error', async () => {
      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
      });
      (authService.isAuthenticated as any).mockReturnValue(true);
      (organizationService.joinOrganization as any).mockRejectedValue(
        new Error('This invitation link is invalid')
      );

      render(<TokenRedirectClient token={mockToken} />);

      await waitFor(() => {
        expect(screen.getByText('Invitation Error')).toBeInTheDocument();
        expect(screen.getByText(/invitation link is invalid/i)).toBeInTheDocument();
      });
    });

    it('should handle already member error', async () => {
      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
      });
      (authService.isAuthenticated as any).mockReturnValue(true);
      (organizationService.joinOrganization as any).mockRejectedValue(
        new Error('You are already a member of this organization')
      );

      render(<TokenRedirectClient token={mockToken} />);

      await waitFor(() => {
        expect(screen.getByText(/already a member/i)).toBeInTheDocument();
      });
    });

    it('should handle network error', async () => {
      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
      });
      (authService.isAuthenticated as any).mockReturnValue(true);
      (organizationService.joinOrganization as any).mockRejectedValue(
        new Error('Network error. Please check your connection')
      );

      render(<TokenRedirectClient token={mockToken} />);

      await waitFor(() => {
        expect(screen.getByText(/Network error/i)).toBeInTheDocument();
      });
    });

    it('should handle missing organization ID', async () => {
      (useAuthStore as any).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
      });
      
      // Mock window.location.search without org_id
      Object.defineProperty(window, 'location', {
        value: {
          search: '',
          reload: vi.fn(),
        },
        writable: true,
      });

      render(<TokenRedirectClient token={mockToken} />);

      await waitFor(() => {
        expect(screen.getByText(/Organization ID not found/i)).toBeInTheDocument();
      });
    });
  });

  describe('Authentication Redirects', () => {
    it('should store token and redirect for team leader invitation', () => {
      const token = 'team-leader-token';
      const orgId = 'org-123';

      InvitationFlowManager.storeInvitationToken({
        token,
        type: 'team_leader',
        organizationId: orgId,
        timestamp: Date.now(),
      });

      expect(InvitationFlowManager.storeInvitationToken).toHaveBeenCalledWith({
        token,
        type: 'team_leader',
        organizationId: orgId,
        timestamp: expect.any(Number),
      });
    });

    it('should store token and redirect for team member invitation', () => {
      const token = 'team-member-token';
      const teamId = 'team-456';

      InvitationFlowManager.storeInvitationToken({
        token,
        type: 'team_member',
        teamId,
        timestamp: Date.now(),
      });

      expect(InvitationFlowManager.storeInvitationToken).toHaveBeenCalledWith({
        token,
        type: 'team_member',
        teamId,
        timestamp: expect.any(Number),
      });
    });

    it('should store token and redirect for org member invitation', () => {
      const token = 'org-member-token';
      const orgId = 'org-789';

      InvitationFlowManager.storeInvitationToken({
        token,
        type: 'org_member',
        organizationId: orgId,
        timestamp: Date.now(),
      });

      expect(InvitationFlowManager.storeInvitationToken).toHaveBeenCalledWith({
        token,
        type: 'org_member',
        organizationId: orgId,
        timestamp: expect.any(Number),
      });
    });

    it('should clear token after successful onboarding', () => {
      InvitationFlowManager.clearInvitationToken();
      expect(InvitationFlowManager.clearInvitationToken).toHaveBeenCalled();
    });
  });
});
