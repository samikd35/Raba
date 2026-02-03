/**
 * Invitation Flow Manager
 * 
 * Manages invitation token storage and authentication redirects for:
 * - Organization member invitations
 * - Team leader invitations
 * - Team member invitations
 */

const STORAGE_KEY = 'invitation_token';
const TOKEN_EXPIRY_HOURS = 48;

export interface InvitationToken {
  token: string;
  type: 'org_member' | 'team_leader' | 'team_member';
  organizationId?: string;
  teamId?: string;
  timestamp: number;
}

export class InvitationFlowManager {
  /**
   * Store invitation token in sessionStorage before authentication
   * @param token - The invitation token data to store
   * @throws Error if storage operation fails
   */
  static storeInvitationToken(token: InvitationToken): void {
    try {
      const tokenData = JSON.stringify(token);
      sessionStorage.setItem(STORAGE_KEY, tokenData);
    } catch (error) {
      console.error('[InvitationFlowManager] Failed to store invitation token:', error);
      throw new Error('Failed to store invitation token. Please try again.');
    }
  }

  /**
   * Retrieve stored invitation token from sessionStorage
   * @returns The stored invitation token or null if not found or invalid
   */
  static getStoredInvitationToken(): InvitationToken | null {
    try {
      const tokenData = sessionStorage.getItem(STORAGE_KEY);
      
      if (!tokenData) {
        return null;
      }

      const token = JSON.parse(tokenData) as InvitationToken;
      
      // Validate token structure
      if (!token.token || !token.type || !token.timestamp) {
        console.warn('[InvitationFlowManager] Invalid token structure');
        this.clearInvitationToken();
        return null;
      }

      return token;
    } catch (error) {
      console.error('[InvitationFlowManager] Failed to retrieve invitation token:', error);
      this.clearInvitationToken();
      return null;
    }
  }

  /**
   * Clear invitation token from sessionStorage
   */
  static clearInvitationToken(): void {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.error('[InvitationFlowManager] Failed to clear invitation token:', error);
    }
  }

  /**
   * Check if token is expired (48 hours from creation)
   * @param token - The invitation token to check
   * @returns true if token is expired, false otherwise
   */
  static isTokenExpired(token: InvitationToken): boolean {
    const now = Date.now();
    const expiryTime = token.timestamp + (TOKEN_EXPIRY_HOURS * 60 * 60 * 1000);
    return now > expiryTime;
  }

  /**
   * Get redirect URL after authentication based on invitation type
   * @param token - The invitation token
   * @returns The appropriate redirect URL
   */
  static getPostAuthRedirectUrl(token: InvitationToken): string {
    switch (token.type) {
      case 'org_member':
        return `/org-invite/${token.token}`;
      
      case 'team_leader':
        return `/org-invite/${token.token}`;
      
      case 'team_member':
        return `/team-invite/${token.token}`;
      
      default:
        console.warn('[InvitationFlowManager] Unknown token type:', token.type);
        return '/admin/organization-dashboard';
    }
  }

  /**
   * Check if there's a valid stored token and return redirect URL
   * @returns Redirect URL if valid token exists, null otherwise
   */
  static getRedirectUrlIfTokenExists(): string | null {
    const token = this.getStoredInvitationToken();
    
    if (!token) {
      return null;
    }

    if (this.isTokenExpired(token)) {
      console.warn('[InvitationFlowManager] Token expired, clearing');
      this.clearInvitationToken();
      return null;
    }

    return this.getPostAuthRedirectUrl(token);
  }
}
