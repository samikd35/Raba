/**
 * Debounce utility for optimizing API calls
 * 
 * Delays function execution until after a specified wait time has elapsed
 * since the last time it was invoked.
 */

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}

/**
 * Debounce with immediate execution option
 * 
 * @param func - Function to debounce
 * @param wait - Wait time in milliseconds
 * @param immediate - If true, trigger function on leading edge instead of trailing
 */
export function debounceImmediate<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  immediate = false
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const callNow = immediate && !timeout;

    const later = () => {
      timeout = null;
      if (!immediate) {
        func(...args);
      }
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);

    if (callNow) {
      func(...args);
    }
  };
}

/**
 * Async debounce that returns a promise
 * Useful for debouncing API calls
 */
export function debounceAsync<T extends (...args: any[]) => Promise<any>>(
  func: T,
  wait: number
): (...args: Parameters<T>) => Promise<ReturnType<T>> {
  let timeout: NodeJS.Timeout | null = null;
  let resolveList: Array<(value: any) => void> = [];
  let rejectList: Array<(reason?: any) => void> = [];

  return function executedFunction(...args: Parameters<T>): Promise<ReturnType<T>> {
    return new Promise((resolve, reject) => {
      resolveList.push(resolve);
      rejectList.push(reject);

      if (timeout) {
        clearTimeout(timeout);
      }

      timeout = setTimeout(async () => {
        timeout = null;
        const currentResolveList = resolveList;
        const currentRejectList = rejectList;
        resolveList = [];
        rejectList = [];

        try {
          const result = await func(...args);
          currentResolveList.forEach(res => res(result));
        } catch (error) {
          currentRejectList.forEach(rej => rej(error));
        }
      }, wait);
    });
  };
}

/**
 * Throttle utility - ensures function is called at most once per specified time period
 * 
 * @param func - Function to throttle
 * @param limit - Time limit in milliseconds
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  let lastResult: ReturnType<T>;

  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      inThrottle = true;
      lastResult = func(...args);
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
    return lastResult;
  };
}
