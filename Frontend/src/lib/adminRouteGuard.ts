import { authService } from '@/services/authService';

/**
 * Check if the current user has admin privileges
 * @returns boolean indicating if user is admin or super admin
 */
export const isAdminUser = (): boolean => {
  try {
    // Get current user from auth store
    const user = authService.getCurrentUserFromStore();
    
    if (!user || !user.roles || user.roles.length === 0) {
      return false;
    }
    
    // Check if user has admin or super_admin role
    return user.roles.includes('admin') || user.roles.includes('super_admin');
  } catch (error) {
    console.error('Error checking admin status:', error);
    return false;
  }
};

/**
 * Check if the current user is a super admin
 * @returns boolean indicating if user is super admin
 */
export const isSuperAdminUser = (): boolean => {
  try {
    // Get current user from auth store
    const user = authService.getCurrentUserFromStore();
    
    if (!user || !user.roles || user.roles.length === 0) {
      return false;
    }
    
    // Check if user has super_admin role
    return user.roles.includes('super_admin');
  } catch (error) {
    console.error('Error checking super admin status:', error);
    return false;
  }
};

/**
 * Check if the current user is an organization admin
 * @returns boolean indicating if user is organization admin
 */
export const isOrganizationAdminUser = (): boolean => {
  try {
    // Get current user from auth store
    const user = authService.getCurrentUserFromStore();
    
    if (!user || !user.roles || user.roles.length === 0) {
      return false;
    }
    
    // Check if user has admin role (organization admin)
    return user.roles.includes('admin');
  } catch (error) {
    console.error('Error checking organization admin status:', error);
    return false;
  }
};

/**
 * Check if the current user is a team leader
 * @returns boolean indicating if user is team leader
 */
export const isTeamLeaderUser = (): boolean => {
  try {
    // Get current user from auth store
    const user = authService.getCurrentUserFromStore();
    
    if (!user || !user.roles || user.roles.length === 0) {
      return false;
    }
    
    // Check if user has team_leader role
    return user.roles.includes('team_leader');
  } catch (error) {
    console.error('Error checking team leader status:', error);
    return false;
  }
};