import { useEffect, RefObject } from 'react';

/**
 * Trigger handler when clicking outside the referenced element.
 *
 * @param ref Element ref to watch
 * @param handler Callback invoked on outside click/touch
 * @param enabled Toggle listener on/off
 */
export function useOnClickOutside<T extends HTMLElement>(
  ref: RefObject<T | null>,
  handler: (event: MouseEvent | TouchEvent) => void,
  enabled: boolean = true
) {
  useEffect(() => {
    if (!enabled) return;

    const listener = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node | null;
      const element = ref.current;
      if (!element || !target || element.contains(target)) {
        return;
      }
      handler(event);
    };

    document.addEventListener('mousedown', listener);
    document.addEventListener('touchstart', listener);

    return () => {
      document.removeEventListener('mousedown', listener);
      document.removeEventListener('touchstart', listener);
    };
  }, [ref, handler, enabled]);
}
