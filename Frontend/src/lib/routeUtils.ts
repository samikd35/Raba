// lib/routeUtils.ts
// Centralized helpers for role-based redirects and route access checks

export type RequiredRole = 'admin' | 'super_admin' | 'any';

interface User {
  roles?: string[];
  tenant_type?: string;
  tenant_id?: string;
}

function normalizeRoles(roles?: string[] | null): string[] {
  if (!roles || !Array.isArray(roles)) return [];
  return roles.map((r) => (r || '').toLowerCase());
}

export function getRedirectPathBasedOnRole(roles?: string[] | null, user?: User): string {
  const normalized = normalizeRoles(roles);
  const isSuperAdmin = normalized.includes('super_admin');
  const isOrganizationOwner = user?.tenant_type === 'organization';
  
  // Super admins go to /admin
  if (isSuperAdmin) return '/admin';
  
  // Organization owners go to their organization dashboard
  if (isOrganizationOwner && user?.tenant_id) {
    return `/admin/organizations/${user.tenant_id}`;
  }
  
  // Everyone else goes to /team
  return '/team-workspace';
}

export function canAccessRoute(
  userRoles: string[] | undefined | null,
  requiredRole: RequiredRole,
  user?: User
): boolean {
  const roles = normalizeRoles(userRoles);
  const isSuperAdmin = roles.includes('super_admin');
  const isAdmin = roles.includes('admin');
  const isOrganizationOwner = user?.tenant_type === 'organization';

  switch (requiredRole) {
    case 'super_admin':
      return isSuperAdmin;
    case 'admin':
      // Allow super_admin as superset of admin privileges
      // Also allow organization owners to access admin routes
      return isAdmin || isSuperAdmin || isOrganizationOwner;
    case 'any':
    default:
      // Any admin privilege (admin, super_admin, or organization owner)
      return isAdmin || isSuperAdmin || isOrganizationOwner;
  }
}
