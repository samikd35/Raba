/**
 * Example usage of InvitationFlowManager
 * 
 * This file demonstrates how to use the InvitationFlowManager utility
 * in different scenarios.
 */

import { InvitationFlowManager, InvitationToken } from './invitationFlowManager';

// Example 1: Storing an organization member invitation token
export function storeOrgMemberInvitation(token: string, organizationId: string) {
  const invitationToken: InvitationToken = {
    token,
    type: 'org_member',
    organizationId,
    timestamp: Date.now(),
  };
  
  InvitationFlowManager.storeInvitationToken(invitationToken);
}

// Example 2: Storing a team member invitation token
export function storeTeamMemberInvitation(token: string, teamId: string) {
  const invitationToken: InvitationToken = {
    token,
    type: 'team_member',
    teamId,
    timestamp: Date.now(),
  };
  
  InvitationFlowManager.storeInvitationToken(invitationToken);
}

// Example 3: Checking for stored token after authentication
export function handlePostAuthRedirect(): string | null {
  const redirectUrl = InvitationFlowManager.getRedirectUrlIfTokenExists();
  
  if (redirectUrl) {
    console.log('Redirecting to:', redirectUrl);
    return redirectUrl;
  }
  
  console.log('No valid invitation token found');
  return null;
}

// Example 4: Manual token validation
export function validateStoredToken(): boolean {
  const token = InvitationFlowManager.getStoredInvitationToken();
  
  if (!token) {
    console.log('No token found');
    return false;
  }
  
  if (InvitationFlowManager.isTokenExpired(token)) {
    console.log('Token expired');
    InvitationFlowManager.clearInvitationToken();
    return false;
  }
  
  console.log('Token is valid');
  return true;
}

// Example 5: Usage in invitation link handler
export function handleInvitationLink(
  token: string,
  type: 'org_member' | 'team_leader' | 'team_member',
  isAuthenticated: boolean,
  organizationId?: string,
  teamId?: string
): string {
  if (isAuthenticated) {
    // User is already authenticated, proceed directly
    return type === 'team_member' 
      ? `/team-invite/${token}` 
      : `/org-invite/${token}`;
  }
  
  // User not authenticated, store token and redirect to sign-in
  InvitationFlowManager.storeInvitationToken({
    token,
    type,
    organizationId,
    teamId,
    timestamp: Date.now(),
  });
  
  return '/signin';
}

// Example 6: Usage in sign-in success handler
export function handleSignInSuccess(): string {
  const redirectUrl = InvitationFlowManager.getRedirectUrlIfTokenExists();
  
  if (redirectUrl) {
    // Clear token after getting redirect URL (will be cleared again after successful join)
    return redirectUrl;
  }
  
  // Default redirect
  return '/admin/organization-dashboard';
}

// Example 7: Clearing token after successful join
export function handleSuccessfulJoin() {
  InvitationFlowManager.clearInvitationToken();
  console.log('Invitation token cleared after successful join');
}
