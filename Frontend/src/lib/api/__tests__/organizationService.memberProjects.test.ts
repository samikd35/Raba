/**
 * Unit Tests for Member Projects API Methods
 * 
 * These tests verify the new API methods added to OrganizationService:
 * - getMemberProjects()
 * - getTenantProjects()
 * - getMemberProjectDetail()
 */

import { OrganizationService } from '../organizationService';
import { authService } from '../../../services/authService';

// Mock the authService
jest.mock('../../../services/authService', () => ({
  authService: {
    getCurrentToken: jest.fn(() => 'mock-jwt-token'),
  },
}));

// Mock fetch globally
global.fetch = jest.fn();

describe('OrganizationService - Member Projects', () => {
  const mockOrgId = 'org-123';
  const mockTenantId = 'tenant-456';
  const mockProjectId = 'proj-789';

  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  describe('getMemberProjects', () => {
    it('should fetch member projects with default parameters', async () => {
      const mockResponse = {
        members: [
          {
            user_id: 'user-1',
            user_email: 'user@example.com',
            user_name: 'Test User',
            member_type: 'individual',
            tenant_id: 'tenant-1',
            project_count: 5,
            projects: [],
          },
        ],
        total_count: 1,
        page: 1,
        page_size: 20,
        has_next: false,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        text: async () => JSON.stringify(mockResponse),
      });

      const result = await OrganizationService.getMemberProjects(mockOrgId);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/organization/${mockOrgId}/member-projects`),
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            Authorization: 'Bearer mock-jwt-token',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
      expect(result.members).toHaveLength(1);
      expect(result.page).toBe(1);
      expect(result.page_size).toBe(20);
    });

    it('should apply pagination parameters correctly', async () => {
      const mockResponse = {
        members: [],
        total_count: 50,
        page: 2,
        page_size: 10,
        has_next: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        text: async () => JSON.stringify(mockResponse),
      });

      await OrganizationService.getMemberProjects(mockOrgId, {
        page: 2,
        page_size: 10,
      });

      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).toContain('page=2');
      expect(callUrl).toContain('page_size=10');
    });

    it('should filter by member type', async () => {
      const mockResponse = {
        members: [],
        total_count: 0,
        page: 1,
        page_size: 20,
        has_next: false,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        text: async () => JSON.stringify(mockResponse),
      });

      await OrganizationService.getMemberProjects(mockOrgId, {
        member_type: 'individual',
      });

      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).toContain('member_type=individual');
    });

    it('should not add member_type param when set to "all"', async () => {
      const mockResponse = {
        members: [],
        total_count: 0,
        page: 1,
        page_size: 20,
        has_next: false,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        text: async () => JSON.stringify(mockResponse),
      });

      await OrganizationService.getMemberProjects(mockOrgId, {
        member_type: 'all',
      });

      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).not.toContain('member_type=all');
    });

    it('should throw error on 403 Forbidden', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ message: 'Access denied' }),
      });

      await expect(
        OrganizationService.getMemberProjects(mockOrgId)
      ).rejects.toThrow();
    });
  });

  describe('getTenantProjects', () => {
    it('should fetch tenant projects with default parameters', async () => {
      const mockResponse = {
        tenant: {
          tenant_id: mockTenantId,
          tenant_type: 'individual',
          name: 'Test Tenant',
          contact_email: 'tenant@example.com',
        },
        projects: [
          {
            id: 'proj-1',
            name: 'Project 1',
            description: 'Test project',
            current_step: 'vpc_composition',
            created_at: '2025-01-01T00:00:00Z',
            updated_at: '2025-01-02T00:00:00Z',
          },
        ],
        total_count: 1,
        page: 1,
        page_size: 20,
        has_next: false,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        text: async () => JSON.stringify(mockResponse),
      });

      const result = await OrganizationService.getTenantProjects(
        mockOrgId,
        mockTenantId
      );

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(
          `/api/organization/${mockOrgId}/tenants/${mockTenantId}/projects`
        ),
        expect.any(Object)
      );

      expect(result).toEqual(mockResponse);
      expect(result.tenant.tenant_id).toBe(mockTenantId);
      expect(result.projects).toHaveLength(1);
    });

    it('should apply pagination parameters', async () => {
      const mockResponse = {
        tenant: {
          tenant_id: mockTenantId,
          tenant_type: 'team',
          name: 'Team Tenant',
        },
        projects: [],
        total_count: 30,
        page: 3,
        page_size: 10,
        has_next: false,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        text: async () => JSON.stringify(mockResponse),
      });

      await OrganizationService.getTenantProjects(mockOrgId, mockTenantId, {
        page: 3,
        page_size: 10,
      });

      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).toContain('page=3');
      expect(callUrl).toContain('page_size=10');
    });
  });

  describe('getMemberProjectDetail', () => {
    it('should fetch complete project details', async () => {
      const mockResponse = {
        project: {
          id: mockProjectId,
          tenant_id: mockTenantId,
          user_id: 'user-1',
          name: 'Test Project',
          description: 'Project description',
          pv_report_id: 'report-1',
          status: 'active',
          current_step: 'field_prep',
          vpc_data: {
            vpcs: {
              'persona-1': {
                status: 'completed',
                value_map: {},
                created_at: '2025-01-01T00:00:00Z',
                persona_id: 'persona-1',
                canvas_data: {},
                persona_name: 'Test Persona',
                customer_profile: {
                  gains: [],
                  pains: [],
                  jobs_to_be_done: [],
                },
              },
            },
            vpc_status: 'completed',
            primary_persona_id: 'persona-1',
          },
          field_prep_data: {
            stage: 'completed',
            hypotheses: [
              {
                id: 'hyp-1',
                text: 'Test hypothesis',
                evidence: ['Evidence 1'],
                persona_id: 'persona-1',
                generated_at: '2025-01-01T00:00:00Z',
                persona_name: 'Test Persona',
              },
            ],
            assumptions: [],
            questionnaires: [],
          },
          settings: {},
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-02T00:00:00Z',
        },
        owner: {
          user_id: 'user-1',
          user_email: 'owner@example.com',
          user_name: 'Project Owner',
          member_type: 'individual',
          tenant_id: mockTenantId,
        },
        pv_report: {
          id: 'report-1',
          title: 'Problem Validation Report',
          content: { summary: 'Test summary' },
        },
        access_log: {
          accessed_by: 'admin-user',
          accessed_at: '2025-01-03T00:00:00Z',
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        text: async () => JSON.stringify(mockResponse),
      });

      const result = await OrganizationService.getMemberProjectDetail(
        mockOrgId,
        mockProjectId
      );

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(
          `/api/organization/${mockOrgId}/member-projects/${mockProjectId}`
        ),
        expect.objectContaining({
          method: 'GET',
        })
      );

      expect(result).toEqual(mockResponse);
      expect(result.project.id).toBe(mockProjectId);
      expect(result.owner.member_type).toBe('individual');
      expect(result.pv_report).toBeTruthy();
      expect(result.access_log).toBeTruthy();
    });

    it('should handle project without PV report', async () => {
      const mockResponse = {
        project: {
          id: mockProjectId,
          tenant_id: mockTenantId,
          user_id: 'user-1',
          name: 'Test Project',
          description: 'Project description',
          pv_report_id: '',
          status: 'active',
          current_step: 'project_setup',
          vpc_data: {
            vpcs: {},
            vpc_status: 'pending',
            primary_persona_id: '',
          },
          field_prep_data: {
            stage: 'pending',
            hypotheses: [],
            assumptions: [],
            questionnaires: [],
          },
          settings: {},
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
        },
        owner: {
          user_id: 'user-1',
          user_email: 'owner@example.com',
          user_name: 'Project Owner',
          member_type: 'team',
          tenant_id: mockTenantId,
          team_name: 'Test Team',
        },
        pv_report: null,
        access_log: {
          accessed_by: 'admin-user',
          accessed_at: '2025-01-03T00:00:00Z',
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        text: async () => JSON.stringify(mockResponse),
      });

      const result = await OrganizationService.getMemberProjectDetail(
        mockOrgId,
        mockProjectId
      );

      expect(result.pv_report).toBeNull();
      expect(result.owner.member_type).toBe('team');
      expect(result.owner.team_name).toBe('Test Team');
    });

    it('should throw error on 404 Not Found', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ message: 'Project not found' }),
      });

      await expect(
        OrganizationService.getMemberProjectDetail(mockOrgId, mockProjectId)
      ).rejects.toThrow();
    });
  });
});
