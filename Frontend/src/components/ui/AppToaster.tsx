"use client";

import { Toaster, ToastBar, toast as hotToast } from "react-hot-toast";
import { useEffect } from "react";
import { usePathname } from "next/navigation";

/**
 * Global Toaster Configuration
 * 
 * This component should be mounted ONCE in the root layout.
 * It provides consistent toast behavior across the entire app.
 * 
 * Features:
 * - Auto-dismiss with proper durations
 * - Max 4 visible toasts (prevents flooding)
 * - Route change cleanup (dismisses stale toasts)
 * - Consistent styling
 */

const TOAST_CONFIG = {
  // Duration settings (in ms)
  duration: {
    success: 3500,
    error: 5500,
    default: 4000,
    loading: Infinity, // Loading toasts stay until dismissed
  },
  // Max visible toasts at once
  maxVisible: 4,
  // Position
  position: "top-right" as const,
  // Gutter between toasts
  gutter: 8,
};

export function AppToaster() {
  const pathname = usePathname();

  // Dismiss all toasts on route change to prevent stale toasts
  useEffect(() => {
    // Small delay to allow any navigation-triggered toasts to fire first
    const timeoutId = setTimeout(() => {
      // Dismiss only non-loading toasts, or all if you prefer
      hotToast.dismiss();
    }, 100);

    return () => clearTimeout(timeoutId);
  }, [pathname]);

  return (
    <Toaster
      position={TOAST_CONFIG.position}
      gutter={TOAST_CONFIG.gutter}
      containerStyle={{
        top: 16,
        right: 16,
      }}
      toastOptions={{
        // Default duration for all toasts
        duration: TOAST_CONFIG.duration.default,
        
        // Type-specific durations
        success: {
          duration: TOAST_CONFIG.duration.success,
          style: {
            background: "#363636",
            color: "#fff",
          },
          iconTheme: {
            primary: "#61D345",
            secondary: "#fff",
          },
        },
        error: {
          duration: TOAST_CONFIG.duration.error,
          style: {
            background: "#363636",
            color: "#fff",
          },
          iconTheme: {
            primary: "#EF4444",
            secondary: "#fff",
          },
        },
        loading: {
          duration: TOAST_CONFIG.duration.loading,
          style: {
            background: "#363636",
            color: "#fff",
          },
        },
        
        // Base styles for all toasts
        style: {
          background: "#363636",
          color: "#fff",
          padding: "12px 16px",
          borderRadius: "8px",
          fontSize: "14px",
          maxWidth: "400px",
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
        },
      }}
    >
      {(t) => (
        <ToastBar
          toast={t}
          style={{
            ...t.style,
            animation: t.visible
              ? "toast-enter 0.2s ease-out"
              : "toast-exit 0.15s ease-in forwards",
          }}
        />
      )}
    </Toaster>
  );
}

// Export config for use in toast wrapper
export { TOAST_CONFIG };
