import toast, { ToastOptions } from "react-hot-toast";
import { TOAST_CONFIG } from "@/components/ui/AppToaster";

/**
 * Toast Wrapper with Dedupe and Cleanup
 * 
 * This wrapper prevents duplicate toasts and manages the toast queue
 * to prevent UI flooding. Use these helpers instead of direct toast calls
 * for better UX.
 * 
 * Features:
 * - Dedupe: Same message won't show multiple times in quick succession
 * - Cap: Limits max visible toasts
 * - Consistent defaults
 */

// Track recent messages to prevent duplicates
const recentMessages = new Map<string, number>();
const DEDUPE_WINDOW_MS = 2000; // Don't show same message within 2 seconds

// Track active toast IDs for cleanup
const activeToasts = new Set<string>();

/**
 * Check if message was recently shown (dedupe)
 */
function isDuplicate(message: string): boolean {
  const now = Date.now();
  const lastShown = recentMessages.get(message);
  
  if (lastShown && now - lastShown < DEDUPE_WINDOW_MS) {
    return true;
  }
  
  // Clean up old entries
  for (const [msg, timestamp] of recentMessages.entries()) {
    if (now - timestamp > DEDUPE_WINDOW_MS) {
      recentMessages.delete(msg);
    }
  }
  
  recentMessages.set(message, now);
  return false;
}

/**
 * Enforce max visible toasts by dismissing oldest
 */
function enforceMaxToasts(): void {
  if (activeToasts.size >= TOAST_CONFIG.maxVisible) {
    // Get the oldest toast and dismiss it
    const oldestId = activeToasts.values().next().value;
    if (oldestId) {
      toast.dismiss(oldestId);
      activeToasts.delete(oldestId);
    }
  }
}

/**
 * Track toast and auto-cleanup when dismissed
 */
function trackToast(toastId: string): void {
  activeToasts.add(toastId);
  
  // Auto-remove from tracking after max duration
  setTimeout(() => {
    activeToasts.delete(toastId);
  }, TOAST_CONFIG.duration.error + 1000); // Use longest duration + buffer
}

/**
 * Show a success toast
 */
export function notifySuccess(
  message: string,
  options?: Partial<ToastOptions>
): string | undefined {
  if (isDuplicate(message)) return undefined;
  
  enforceMaxToasts();
  
  const toastId = toast.success(message, {
    duration: TOAST_CONFIG.duration.success,
    ...options,
  });
  
  trackToast(toastId);
  return toastId;
}

/**
 * Show an error toast
 */
export function notifyError(
  message: string,
  options?: Partial<ToastOptions>
): string | undefined {
  if (isDuplicate(message)) return undefined;
  
  enforceMaxToasts();
  
  const toastId = toast.error(message, {
    duration: TOAST_CONFIG.duration.error,
    ...options,
  });
  
  trackToast(toastId);
  return toastId;
}

/**
 * Show a generic toast (info style)
 */
export function notify(
  message: string,
  options?: Partial<ToastOptions>
): string | undefined {
  if (isDuplicate(message)) return undefined;
  
  enforceMaxToasts();
  
  const toastId = toast(message, {
    duration: TOAST_CONFIG.duration.default,
    ...options,
  });
  
  trackToast(toastId);
  return toastId;
}

/**
 * Show a loading toast (returns ID for later dismissal)
 */
export function notifyLoading(
  message: string,
  options?: Partial<ToastOptions>
): string {
  enforceMaxToasts();
  
  const toastId = toast.loading(message, {
    ...options,
  });
  
  trackToast(toastId);
  return toastId;
}

/**
 * Dismiss a specific toast or all toasts
 */
export function dismissToast(toastId?: string): void {
  if (toastId) {
    toast.dismiss(toastId);
    activeToasts.delete(toastId);
  } else {
    toast.dismiss();
    activeToasts.clear();
  }
}

/**
 * Dismiss all toasts and clear tracking
 * Useful for route changes or cleanup
 */
export function dismissAllToasts(): void {
  toast.dismiss();
  activeToasts.clear();
  recentMessages.clear();
}

/**
 * Promise-based toast that shows loading, then success/error
 */
export function notifyPromise<T>(
  promise: Promise<T>,
  messages: {
    loading: string;
    success: string | ((data: T) => string);
    error: string | ((err: unknown) => string);
  },
  options?: Partial<ToastOptions>
): Promise<T> {
  return toast.promise(promise, messages, {
    ...options,
  });
}

// Re-export the raw toast for edge cases where you need direct access
export { toast };
