'use client';
import { useEffect, useMemo } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { 
  useAuthStore,
  useInitializeAuth,
  useIsInitialized,
  useIsLoading,
  useIsAuthenticated,
} from '@/stores/authStore';
import { authService } from '@/services/authService';
import Loading from '@/app/loading';

// Public routes (client) — keep in sync with middleware
const PUBLIC_ROUTES = [
  '/',
  '/signin',
  '/signup',
  '/reset-password',
  '/verify-email',
  '/terms',
  '/privacy',
  '/about',
  '/contact',
];

// Protected client routes (keep in sync with middleware)
const PROTECTED_ROUTES = [
  '/team',
  '/organization',
  '/profile',
  '/problem-validator',
  '/problem-explorer',
  '/customer-profile',
  '/value-map',
  '/vpc-composition',
];

// Routes that require a selected workspace/tenant context
const WORKSPACE_REQUIRED_ROUTES = [
  '/team',
  '/organization',
  '/problem-validator',
  '/problem-explorer',
  '/customer-profile',
  '/value-map',
  '/vpc-composition',
];

// Compute the best dashboard route based on role/tenant
function getDashboardRoute(user: ReturnType<typeof useAuthStore>['user']): string {
  const roles = user?.roles || [];
  const tenantType = (user as any)?.tenant_type || (user as any)?.tenantType;

  if (roles.includes('super_admin') || roles.includes('admin')) return '/admin';
  if (tenantType === 'organization') return '/organization';
  if (tenantType === 'team') return '/team';
  if (tenantType === 'individual' || tenantType === 'personal') return '/personal';
  return '/choose-workspace';
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const initializeAuth = useInitializeAuth();
  const isInitialized = useIsInitialized();
  const isLoading = useIsLoading();
  const isAuthenticated = useIsAuthenticated();
  const user = useAuthStore((s) => s.user);

  // Workspace context - get from user object
  const currentWorkspaceId = (user as any)?.workspace_id || null;
  const currentWorkspaceTenantId = (user as any)?.tenant_id || null;
  const hasWorkspace = useMemo(() => !!(currentWorkspaceTenantId || currentWorkspaceId), [currentWorkspaceId, currentWorkspaceTenantId]);

  // Initialize authentication on component mount
  useEffect(() => {
    if (!isInitialized && !isLoading) {
      if (process.env.NODE_ENV === 'development') {
        console.log('AuthProvider: Starting auth initialization...');
      }
      initializeAuth();
    }
  }, [initializeAuth, isInitialized, isLoading]);

  // Initialize auth service after store is ready
  useEffect(() => {
    if (isInitialized) {
      authService.initialize();
    }
  }, [isInitialized]);

  // Client-side route protection and smart redirects
  useEffect(() => {
    if (!isInitialized || isLoading) return;
    if (!pathname) return;

    const isPublic = PUBLIC_ROUTES.includes(pathname) || PUBLIC_ROUTES.some((r) => pathname.startsWith(r + '/'));
    const isProtected = PROTECTED_ROUTES.includes(pathname) || PROTECTED_ROUTES.some((r) => pathname.startsWith(r + '/'));
    const requiresWorkspace = WORKSPACE_REQUIRED_ROUTES.includes(pathname) || WORKSPACE_REQUIRED_ROUTES.some((r) => pathname.startsWith(r + '/'));

    // 1) If unauthenticated and on a protected route, redirect to signin (middleware also enforces this)
    if (!isAuthenticated && isProtected) {
      if (process.env.NODE_ENV === 'development') {
        console.log('AuthProvider: Unauthenticated access to protected route, redirecting to /signin');
      }
      router.replace(`/signin?next=${encodeURIComponent(pathname)}`);
      return;
    }

    // 2) If authenticated and on an auth/public entry page, send to dashboard
    if (isAuthenticated && (pathname === '/' || pathname === '/signin' || pathname === '/signup')) {
      const target = getDashboardRoute(user);
      if (process.env.NODE_ENV === 'development') {
        console.log(`AuthProvider: Authenticated on public route, redirecting to ${target}`);
      }
      router.replace(target);
      return;
    }

    // 3) If route requires workspace and none is selected, go to choose-workspace
    if (isAuthenticated && requiresWorkspace && !hasWorkspace) {
      if (process.env.NODE_ENV === 'development') {
        console.log('AuthProvider: Workspace required but none selected, redirecting to /choose-workspace');
      }
      router.replace(`/choose-workspace?next=${encodeURIComponent(pathname)}`);
      return;
    }
  }, [isInitialized, isLoading, isAuthenticated, pathname, router, user, hasWorkspace]);

  // Show loading state during initialization
  if (!isInitialized || isLoading) {
    return <Loading />;
  }

  // Render children
  return <>{children}</>;
}