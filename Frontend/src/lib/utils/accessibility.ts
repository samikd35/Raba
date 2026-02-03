/**
 * Accessibility utilities for WCAG 2.1 AA compliance
 * 
 * These utilities help ensure components meet accessibility standards
 */

/**
 * Generate a unique ID for form elements
 * Useful for connecting labels to inputs
 */
export function generateId(prefix: string = 'id'): string {
  return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Check if color contrast ratio meets WCAG AA standards
 * 
 * @param foreground - Foreground color in hex format
 * @param background - Background color in hex format
 * @returns Object with contrast ratio and compliance status
 */
export function checkColorContrast(
  foreground: string,
  background: string
): {
  ratio: number;
  meetsAA: boolean;
  meetsAAA: boolean;
} {
  const getLuminance = (hex: string): number => {
    // Remove # if present
    hex = hex.replace('#', '');
    
    // Convert to RGB
    const r = parseInt(hex.substr(0, 2), 16) / 255;
    const g = parseInt(hex.substr(2, 2), 16) / 255;
    const b = parseInt(hex.substr(4, 2), 16) / 255;
    
    // Apply gamma correction
    const [rs, gs, bs] = [r, g, b].map(c => 
      c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
    );
    
    // Calculate relative luminance
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  };

  const l1 = getLuminance(foreground);
  const l2 = getLuminance(background);
  
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  
  const ratio = (lighter + 0.05) / (darker + 0.05);
  
  return {
    ratio: Math.round(ratio * 100) / 100,
    meetsAA: ratio >= 4.5, // WCAG AA for normal text
    meetsAAA: ratio >= 7, // WCAG AAA for normal text
  };
}

/**
 * Create ARIA label for icon buttons
 * 
 * @param action - The action the button performs
 * @param context - Optional context for the action
 * @returns ARIA label string
 */
export function createAriaLabel(action: string, context?: string): string {
  if (context) {
    return `${action} ${context}`;
  }
  return action;
}

/**
 * Get ARIA attributes for loading state
 * 
 * @param isLoading - Whether component is loading
 * @param loadingText - Text to announce when loading
 * @returns ARIA attributes object
 */
export function getLoadingAriaAttributes(
  isLoading: boolean,
  loadingText: string = 'Loading'
): {
  'aria-busy': boolean;
  'aria-live': 'polite' | 'off';
  'aria-label'?: string;
} {
  return {
    'aria-busy': isLoading,
    'aria-live': isLoading ? 'polite' : 'off',
    ...(isLoading && { 'aria-label': loadingText }),
  };
}

/**
 * Get ARIA attributes for error state
 * 
 * @param hasError - Whether component has an error
 * @param errorId - ID of the error message element
 * @returns ARIA attributes object
 */
export function getErrorAriaAttributes(
  hasError: boolean,
  errorId?: string
): {
  'aria-invalid': boolean;
  'aria-describedby'?: string;
} {
  return {
    'aria-invalid': hasError,
    ...(hasError && errorId && { 'aria-describedby': errorId }),
  };
}

/**
 * Get ARIA attributes for required fields
 * 
 * @param isRequired - Whether field is required
 * @returns ARIA attributes object
 */
export function getRequiredAriaAttributes(
  isRequired: boolean
): {
  'aria-required': boolean;
  required?: boolean;
} {
  return {
    'aria-required': isRequired,
    ...(isRequired && { required: true }),
  };
}

/**
 * Get ARIA attributes for disabled state
 * 
 * @param isDisabled - Whether element is disabled
 * @returns ARIA attributes object
 */
export function getDisabledAriaAttributes(
  isDisabled: boolean
): {
  'aria-disabled': boolean;
  disabled?: boolean;
} {
  return {
    'aria-disabled': isDisabled,
    ...(isDisabled && { disabled: true }),
  };
}

/**
 * Get ARIA attributes for expandable/collapsible elements
 * 
 * @param isExpanded - Whether element is expanded
 * @param controlsId - ID of the element being controlled
 * @returns ARIA attributes object
 */
export function getExpandableAriaAttributes(
  isExpanded: boolean,
  controlsId?: string
): {
  'aria-expanded': boolean;
  'aria-controls'?: string;
} {
  return {
    'aria-expanded': isExpanded,
    ...(controlsId && { 'aria-controls': controlsId }),
  };
}

/**
 * Get ARIA attributes for modal dialogs
 * 
 * @param isOpen - Whether modal is open
 * @param labelId - ID of the element labeling the modal
 * @param descriptionId - ID of the element describing the modal
 * @returns ARIA attributes object
 */
export function getModalAriaAttributes(
  isOpen: boolean,
  labelId?: string,
  descriptionId?: string
): {
  role: 'dialog';
  'aria-modal': boolean;
  'aria-labelledby'?: string;
  'aria-describedby'?: string;
} {
  return {
    role: 'dialog',
    'aria-modal': isOpen,
    ...(labelId && { 'aria-labelledby': labelId }),
    ...(descriptionId && { 'aria-describedby': descriptionId }),
  };
}

/**
 * Get ARIA attributes for pagination
 * 
 * @param currentPage - Current page number
 * @param totalPages - Total number of pages
 * @returns ARIA label for pagination
 */
export function getPaginationAriaLabel(
  currentPage: number,
  totalPages: number
): string {
  return `Page ${currentPage} of ${totalPages}`;
}

/**
 * Get ARIA attributes for search input
 * 
 * @param resultsId - ID of the search results container
 * @param resultCount - Number of search results
 * @returns ARIA attributes object
 */
export function getSearchAriaAttributes(
  resultsId: string,
  resultCount?: number
): {
  role: 'search';
  'aria-controls': string;
  'aria-label': string;
} {
  const label = resultCount !== undefined 
    ? `Search, ${resultCount} results found`
    : 'Search';
    
  return {
    role: 'search',
    'aria-controls': resultsId,
    'aria-label': label,
  };
}

/**
 * Get ARIA attributes for status messages
 * 
 * @param type - Type of status message
 * @returns ARIA attributes object
 */
export function getStatusAriaAttributes(
  type: 'success' | 'error' | 'warning' | 'info'
): {
  role: 'status' | 'alert';
  'aria-live': 'polite' | 'assertive';
} {
  const isUrgent = type === 'error' || type === 'warning';
  
  return {
    role: isUrgent ? 'alert' : 'status',
    'aria-live': isUrgent ? 'assertive' : 'polite',
  };
}

/**
 * Trap focus within a container (useful for modals)
 * 
 * @param container - Container element to trap focus within
 * @returns Cleanup function
 */
export function trapFocus(container: HTMLElement): () => void {
  const focusableElements = container.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  
  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];
  
  const handleTabKey = (e: KeyboardEvent) => {
    if (e.key !== 'Tab') return;
    
    if (e.shiftKey) {
      // Shift + Tab
      if (document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      }
    } else {
      // Tab
      if (document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    }
  };
  
  container.addEventListener('keydown', handleTabKey);
  
  // Focus first element
  firstElement?.focus();
  
  // Return cleanup function
  return () => {
    container.removeEventListener('keydown', handleTabKey);
  };
}

/**
 * Announce message to screen readers
 * 
 * @param message - Message to announce
 * @param priority - Priority level ('polite' or 'assertive')
 */
export function announceToScreenReader(
  message: string,
  priority: 'polite' | 'assertive' = 'polite'
): void {
  const announcement = document.createElement('div');
  announcement.setAttribute('role', 'status');
  announcement.setAttribute('aria-live', priority);
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only'; // Visually hidden
  announcement.textContent = message;
  
  document.body.appendChild(announcement);
  
  // Remove after announcement
  setTimeout(() => {
    document.body.removeChild(announcement);
  }, 1000);
}

/**
 * Check if element is keyboard accessible
 * 
 * @param element - Element to check
 * @returns Whether element is keyboard accessible
 */
export function isKeyboardAccessible(element: HTMLElement): boolean {
  const tabIndex = element.getAttribute('tabindex');
  const isInteractive = ['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA'].includes(
    element.tagName
  );
  
  return isInteractive || (tabIndex !== null && tabIndex !== '-1');
}

/**
 * Get keyboard navigation handler
 * Handles arrow keys, Enter, and Space for custom interactive elements
 * 
 * @param onActivate - Function to call when element is activated
 * @returns Keyboard event handler
 */
export function getKeyboardNavigationHandler(
  onActivate: () => void
): (e: React.KeyboardEvent) => void {
  return (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onActivate();
    }
  };
}
