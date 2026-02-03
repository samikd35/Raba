/**
 * Unit tests for InvitationFlowManager
 * 
 * Tests cover:
 * - Token storage and retrieval
 * - Token expiry validation
 * - Redirect URL generation
 * - Error handling for storage failures
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { InvitationFlowManager, InvitationToken } from '../invitationFlowManager';

describe('InvitationFlowManager', () => {
  beforeEach(() => {
    // Clear sessionStorage before each test
    sessionStorage.clear();
    // Clear all mocks
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Restore console methods
    vi.restoreAllMocks();
  });

  describe('Token Storage and Retrieval', () => {
    it('should store invitation token successfully', () => {
      const token: InvitationToken = {
        token: 'test-token-123',
        type: 'org_member',
        organizationId: 'org-456',
        timestamp: Date.now(),
      };

      InvitationFlowManager.storeInvitationToken(token);

      const stored = sessionStorage.getItem('invitation_token');
      expect(stored).toBeTruthy();
      expect(JSON.parse(stored!)).toEqual(token);
    });

    it('should retrieve stored invitation token successfully', () => {
      const token: InvitationToken = {
        token: 'test-token-123',
        type: 'team_member',
        teamId: 'team-789',
        timestamp: Date.now(),
      };

      InvitationFlowManager.storeInvitationToken(token);
      const retrieved = InvitationFlowManager.getStoredInvitationToken();

      expect(retrieved).toEqual(token);
    });

    it('should return null when no token is stored', () => {
      const retrieved = InvitationFlowManager.getStoredInvitationToken();
      expect(retrieved).toBeNull();
    });

    it('should return null for invalid token structure (missing token field)', () => {
      const invalidToken = {
        type: 'org_member',
        timestamp: Date.now(),
      };

      sessionStorage.setItem('invitation_token', JSON.stringify(invalidToken));
      const retrieved = InvitationFlowManager.getStoredInvitationToken();

      expect(retrieved).toBeNull();
      // Should also clear the invalid token
      expect(sessionStorage.getItem('invitation_token')).toBeNull();
    });

    it('should return null for invalid token structure (missing type field)', () => {
      const invalidToken = {
        token: 'test-token',
        timestamp: Date.now(),
      };

      sessionStorage.setItem('invitation_token', JSON.stringify(invalidToken));
      const retrieved = InvitationFlowManager.getStoredInvitationToken();

      expect(retrieved).toBeNull();
    });

    it('should return null for invalid token structure (missing timestamp field)', () => {
      const invalidToken = {
        token: 'test-token',
        type: 'org_member',
      };

      sessionStorage.setItem('invitation_token', JSON.stringify(invalidToken));
      const retrieved = InvitationFlowManager.getStoredInvitationToken();

      expect(retrieved).toBeNull();
    });

    it('should clear invitation token successfully', () => {
      const token: InvitationToken = {
        token: 'test-token-123',
        type: 'org_member',
        timestamp: Date.now(),
      };

      InvitationFlowManager.storeInvitationToken(token);
      expect(sessionStorage.getItem('invitation_token')).toBeTruthy();

      InvitationFlowManager.clearInvitationToken();
      expect(sessionStorage.getItem('invitation_token')).toBeNull();
    });

    it('should handle storing multiple token types', () => {
      const orgToken: InvitationToken = {
        token: 'org-token',
        type: 'org_member',
        organizationId: 'org-123',
        timestamp: Date.now(),
      };

      InvitationFlowManager.storeInvitationToken(orgToken);
      let retrieved = InvitationFlowManager.getStoredInvitationToken();
      expect(retrieved?.type).toBe('org_member');

      const teamToken: InvitationToken = {
        token: 'team-token',
        type: 'team_member',
        teamId: 'team-456',
        timestamp: Date.now(),
      };

      InvitationFlowManager.storeInvitationToken(teamToken);
      retrieved = InvitationFlowManager.getStoredInvitationToken();
      expect(retrieved?.type).toBe('team_member');
    });
  });

  describe('Token Expiry Validation', () => {
    it('should return false for non-expired token (recent)', () => {
      const token: InvitationToken = {
        token: 'test-token',
        type: 'org_member',
        timestamp: Date.now(), // Just created
      };

      const isExpired = InvitationFlowManager.isTokenExpired(token);
      expect(isExpired).toBe(false);
    });

    it('should return false for token within 48 hours', () => {
      const token: InvitationToken = {
        token: 'test-token',
        type: 'org_member',
        timestamp: Date.now() - (24 * 60 * 60 * 1000), // 24 hours ago
      };

      const isExpired = InvitationFlowManager.isTokenExpired(token);
      expect(isExpired).toBe(false);
    });

    it('should return false for token at exactly 47 hours', () => {
      const token: InvitationToken = {
        token: 'test-token',
        type: 'org_member',
        timestamp: Date.now() - (47 * 60 * 60 * 1000), // 47 hours ago
      };

      const isExpired = InvitationFlowManager.isTokenExpired(token);
      expect(isExpired).toBe(false);
    });

    it('should return true for token older than 48 hours', () => {
      const token: InvitationToken = {
        token: 'test-token',
        type: 'org_member',
        timestamp: Date.now() - (49 * 60 * 60 * 1000), // 49 hours ago
      };

      const isExpired = InvitationFlowManager.isTokenExpired(token);
      expect(isExpired).toBe(true);
    });

    it('should return true for token at exactly 48 hours + 1ms', () => {
      const token: InvitationToken = {
        token: 'test-token',
        type: 'org_member',
        timestamp: Date.now() - (48 * 60 * 60 * 1000 + 1), // 48 hours + 1ms ago
      };

      const isExpired = InvitationFlowManager.isTokenExpired(token);
      expect(isExpired).toBe(true);
    });

    it('should return true for very old token', () => {
      const token: InvitationToken = {
        token: 'test-token',
        type: 'org_member',
        timestamp: Date.now() - (7 * 24 * 60 * 60 * 1000), // 7 days ago
      };

      const isExpired = InvitationFlowManager.isTokenExpired(token);
      expect(isExpired).toBe(true);
    });
  });

  describe('Redirect URL Generation', () => {
    it('should generate correct URL for org_member token', () => {
      const token: InvitationToken = {
        token: 'org-token-123',
        type: 'org_member',
        organizationId: 'org-456',
        timestamp: Date.now(),
      };

      const url = InvitationFlowManager.getPostAuthRedirectUrl(token);
      expect(url).toBe('/org-invite/org-token-123');
    });

    it('should generate correct URL for team_leader token', () => {
      const token: InvitationToken = {
        token: 'leader-token-456',
        type: 'team_leader',
        organizationId: 'org-789',
        timestamp: Date.now(),
      };

      const url = InvitationFlowManager.getPostAuthRedirectUrl(token);
      expect(url).toBe('/org-invite/leader-token-456');
    });

    it('should generate correct URL for team_member token', () => {
      const token: InvitationToken = {
        token: 'member-token-789',
        type: 'team_member',
        teamId: 'team-123',
        timestamp: Date.now(),
      };

      const url = InvitationFlowManager.getPostAuthRedirectUrl(token);
      expect(url).toBe('/team-invite/member-token-789');
    });

    it('should return default URL for unknown token type', () => {
      const token = {
        token: 'unknown-token',
        type: 'unknown_type' as any,
        timestamp: Date.now(),
      };

      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const url = InvitationFlowManager.getPostAuthRedirectUrl(token);

      expect(url).toBe('/admin/organization-dashboard');
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[InvitationFlowManager] Unknown token type:',
        'unknown_type'
      );
    });

    it('should handle tokens with special characters', () => {
      const token: InvitationToken = {
        token: 'token-with-special-chars-!@#$%',
        type: 'team_member',
        teamId: 'team-123',
        timestamp: Date.now(),
      };

      const url = InvitationFlowManager.getPostAuthRedirectUrl(token);
      expect(url).toBe('/team-invite/token-with-special-chars-!@#$%');
    });
  });

  describe('Error Handling for Storage Failures', () => {
    it('should throw error when storage fails during storeInvitationToken', () => {
      const token: InvitationToken = {
        token: 'test-token',
        type: 'org_member',
        timestamp: Date.now(),
      };

      // Mock sessionStorage.setItem to throw error
      const setItemSpy = vi.spyOn(sessionStorage, 'setItem').mockImplementation(() => {
        throw new Error('Storage quota exceeded');
      });

      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        InvitationFlowManager.storeInvitationToken(token);
      }).toThrow('Failed to store invitation token. Please try again.');

      expect(consoleErrorSpy).toHaveBeenCalled();
      setItemSpy.mockRestore();
    });

    it('should return null and clear token when retrieval fails due to parse error', () => {
      // Store invalid JSON
      sessionStorage.setItem('invitation_token', 'invalid-json{');

      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const retrieved = InvitationFlowManager.getStoredInvitationToken();

      expect(retrieved).toBeNull();
      expect(sessionStorage.getItem('invitation_token')).toBeNull();
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    it('should handle errors gracefully when clearing token fails', () => {
      const removeItemSpy = vi.spyOn(sessionStorage, 'removeItem').mockImplementation(() => {
        throw new Error('Storage error');
      });

      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // Should not throw
      expect(() => {
        InvitationFlowManager.clearInvitationToken();
      }).not.toThrow();

      expect(consoleErrorSpy).toHaveBeenCalled();
      removeItemSpy.mockRestore();
    });

    it('should handle getItem returning null gracefully', () => {
      const getItemSpy = vi.spyOn(sessionStorage, 'getItem').mockReturnValue(null);

      const retrieved = InvitationFlowManager.getStoredInvitationToken();
      expect(retrieved).toBeNull();

      getItemSpy.mockRestore();
    });

    it('should log warning and clear token for invalid structure', () => {
      const invalidToken = {
        token: 'test',
        // missing type and timestamp
      };

      sessionStorage.setItem('invitation_token', JSON.stringify(invalidToken));
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const retrieved = InvitationFlowManager.getStoredInvitationToken();

      expect(retrieved).toBeNull();
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[InvitationFlowManager] Invalid token structure'
      );
      expect(sessionStorage.getItem('invitation_token')).toBeNull();
    });
  });

  describe('getRedirectUrlIfTokenExists', () => {
    it('should return redirect URL for valid non-expired token', () => {
      const token: InvitationToken = {
        token: 'valid-token',
        type: 'org_member',
        timestamp: Date.now(),
      };

      InvitationFlowManager.storeInvitationToken(token);
      const url = InvitationFlowManager.getRedirectUrlIfTokenExists();

      expect(url).toBe('/org-invite/valid-token');
    });

    it('should return null when no token exists', () => {
      const url = InvitationFlowManager.getRedirectUrlIfTokenExists();
      expect(url).toBeNull();
    });

    it('should return null and clear token when token is expired', () => {
      const expiredToken: InvitationToken = {
        token: 'expired-token',
        type: 'org_member',
        timestamp: Date.now() - (49 * 60 * 60 * 1000), // 49 hours ago
      };

      InvitationFlowManager.storeInvitationToken(expiredToken);
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const url = InvitationFlowManager.getRedirectUrlIfTokenExists();

      expect(url).toBeNull();
      expect(sessionStorage.getItem('invitation_token')).toBeNull();
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        '[InvitationFlowManager] Token expired, clearing'
      );
    });

    it('should handle team_member token correctly', () => {
      const token: InvitationToken = {
        token: 'team-token',
        type: 'team_member',
        teamId: 'team-123',
        timestamp: Date.now(),
      };

      InvitationFlowManager.storeInvitationToken(token);
      const url = InvitationFlowManager.getRedirectUrlIfTokenExists();

      expect(url).toBe('/team-invite/team-token');
    });

    it('should handle team_leader token correctly', () => {
      const token: InvitationToken = {
        token: 'leader-token',
        type: 'team_leader',
        organizationId: 'org-123',
        timestamp: Date.now(),
      };

      InvitationFlowManager.storeInvitationToken(token);
      const url = InvitationFlowManager.getRedirectUrlIfTokenExists();

      expect(url).toBe('/org-invite/leader-token');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty string token', () => {
      const token: InvitationToken = {
        token: '',
        type: 'org_member',
        timestamp: Date.now(),
      };

      sessionStorage.setItem('invitation_token', JSON.stringify(token));
      const retrieved = InvitationFlowManager.getStoredInvitationToken();

      // Empty string is falsy, should be treated as invalid
      expect(retrieved).toBeNull();
    });

    it('should handle token with timestamp of 0', () => {
      const token: InvitationToken = {
        token: 'test-token',
        type: 'org_member',
        timestamp: 0,
      };

      sessionStorage.setItem('invitation_token', JSON.stringify(token));
      const retrieved = InvitationFlowManager.getStoredInvitationToken();

      // 0 is falsy, should be treated as invalid
      expect(retrieved).toBeNull();
    });

    it('should handle concurrent storage operations', () => {
      const token1: InvitationToken = {
        token: 'token-1',
        type: 'org_member',
        timestamp: Date.now(),
      };

      const token2: InvitationToken = {
        token: 'token-2',
        type: 'team_member',
        timestamp: Date.now(),
      };

      InvitationFlowManager.storeInvitationToken(token1);
      InvitationFlowManager.storeInvitationToken(token2);

      const retrieved = InvitationFlowManager.getStoredInvitationToken();
      // Should have the last stored token
      expect(retrieved?.token).toBe('token-2');
    });

    it('should handle very long token strings', () => {
      const longToken = 'a'.repeat(10000);
      const token: InvitationToken = {
        token: longToken,
        type: 'org_member',
        timestamp: Date.now(),
      };

      InvitationFlowManager.storeInvitationToken(token);
      const retrieved = InvitationFlowManager.getStoredInvitationToken();

      expect(retrieved?.token).toBe(longToken);
    });

    it('should handle tokens with unicode characters', () => {
      const token: InvitationToken = {
        token: 'token-with-unicode-🎉-✨',
        type: 'team_member',
        timestamp: Date.now(),
      };

      InvitationFlowManager.storeInvitationToken(token);
      const retrieved = InvitationFlowManager.getStoredInvitationToken();

      expect(retrieved?.token).toBe('token-with-unicode-🎉-✨');
    });
  });
});
