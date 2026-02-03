"use client";

import { useRouter } from 'next/navigation';
import { useNavigationLoading } from '@/context/NavigationLoadingContext';
import { useCallback } from 'react';

export function useNavigationWithLoading() {
  const router = useRouter();
  const { startLoading } = useNavigationLoading();

  const push = useCallback((href: string) => {
    startLoading();
    router.push(href);
  }, [router, startLoading]);

  const replace = useCallback((href: string) => {
    startLoading();
    router.replace(href);
  }, [router, startLoading]);

  const back = useCallback(() => {
    startLoading();
    router.back();
  }, [router, startLoading]);

  const forward = useCallback(() => {
    startLoading();
    router.forward();
  }, [router, startLoading]);

  const refresh = useCallback(() => {
    startLoading();
    router.refresh();
  }, [router, startLoading]);

  return {
    push,
    replace,
    back,
    forward,
    refresh,
    // Also expose the original router for cases where loading isn't needed
    router,
  };
}
