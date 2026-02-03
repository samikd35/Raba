/**
 * Accessibility Audit Utilities
 * 
 * These utilities help identify and fix accessibility issues in components
 */

export interface AccessibilityIssue {
  severity: 'error' | 'warning' | 'info';
  element: string;
  issue: string;
  recommendation: string;
  wcagCriterion?: string;
}

/**
 * Audit a component for common accessibility issues
 * 
 * @param container - Container element to audit
 * @returns Array of accessibility issues found
 */
export function auditAccessibility(container: HTMLElement): AccessibilityIssue[] {
  const issues: AccessibilityIssue[] = [];

  // Check for images without alt text
  const images = container.querySelectorAll('img');
  images.forEach((img, index) => {
    if (!img.hasAttribute('alt')) {
      issues.push({
        severity: 'error',
        element: `img[${index}]`,
        issue: 'Image missing alt attribute',
        recommendation: 'Add alt attribute to describe the image or use alt="" for decorative images',
        wcagCriterion: '1.1.1 Non-text Content',
      });
    }
  });

  // Check for buttons without accessible names
  const buttons = container.querySelectorAll('button');
  buttons.forEach((button, index) => {
    const hasText = button.textContent?.trim();
    const hasAriaLabel = button.hasAttribute('aria-label');
    const hasAriaLabelledBy = button.hasAttribute('aria-labelledby');
    
    if (!hasText && !hasAriaLabel && !hasAriaLabelledBy) {
      issues.push({
        severity: 'error',
        element: `button[${index}]`,
        issue: 'Button has no accessible name',
        recommendation: 'Add text content, aria-label, or aria-labelledby to the button',
        wcagCriterion: '4.1.2 Name, Role, Value',
      });
    }
  });

  // Check for inputs without labels
  const inputs = container.querySelectorAll('input, select, textarea');
  inputs.forEach((input, index) => {
    const id = input.getAttribute('id');
    const hasLabel = id && container.querySelector(`label[for="${id}"]`);
    const hasAriaLabel = input.hasAttribute('aria-label');
    const hasAriaLabelledBy = input.hasAttribute('aria-labelledby');
    
    if (!hasLabel && !hasAriaLabel && !hasAriaLabelledBy) {
      issues.push({
        severity: 'error',
        element: `${input.tagName.toLowerCase()}[${index}]`,
        issue: 'Form control has no associated label',
        recommendation: 'Add a <label> element with for attribute, or use aria-label/aria-labelledby',
        wcagCriterion: '3.3.2 Labels or Instructions',
      });
    }
  });

  // Check for links without href
  const links = container.querySelectorAll('a');
  links.forEach((link, index) => {
    if (!link.hasAttribute('href')) {
      issues.push({
        severity: 'warning',
        element: `a[${index}]`,
        issue: 'Link missing href attribute',
        recommendation: 'Add href attribute or use a button element instead',
        wcagCriterion: '4.1.2 Name, Role, Value',
      });
    }
  });

  // Check for elements with click handlers that aren't keyboard accessible
  const clickableElements = container.querySelectorAll('[onclick]');
  clickableElements.forEach((element, index) => {
    const tagName = element.tagName.toLowerCase();
    const isInteractive = ['button', 'a', 'input', 'select', 'textarea'].includes(tagName);
    const hasTabIndex = element.hasAttribute('tabindex');
    const hasRole = element.hasAttribute('role');
    
    if (!isInteractive && !hasTabIndex && !hasRole) {
      issues.push({
        severity: 'error',
        element: `${tagName}[${index}]`,
        issue: 'Clickable element is not keyboard accessible',
        recommendation: 'Add tabindex="0" and keyboard event handlers, or use a button element',
        wcagCriterion: '2.1.1 Keyboard',
      });
    }
  });

  // Check for heading hierarchy
  const headings = Array.from(container.querySelectorAll('h1, h2, h3, h4, h5, h6'));
  let previousLevel = 0;
  headings.forEach((heading, index) => {
    const level = parseInt(heading.tagName.charAt(1));
    if (previousLevel > 0 && level > previousLevel + 1) {
      issues.push({
        severity: 'warning',
        element: `${heading.tagName.toLowerCase()}[${index}]`,
        issue: `Heading level skipped from h${previousLevel} to h${level}`,
        recommendation: 'Use heading levels in sequential order',
        wcagCriterion: '1.3.1 Info and Relationships',
      });
    }
    previousLevel = level;
  });

  // Check for color contrast (simplified check)
  const textElements = container.querySelectorAll('p, span, div, button, a, label');
  textElements.forEach((element, index) => {
    const styles = window.getComputedStyle(element);
    const fontSize = parseFloat(styles.fontSize);
    const fontWeight = styles.fontWeight;
    
    // Flag small text (< 18px or < 14px bold) for manual contrast check
    if (fontSize < 18 || (fontSize < 14 && fontWeight !== 'bold')) {
      const hasLowContrastClass = element.className.includes('text-gray-400') || 
                                   element.className.includes('text-muted');
      if (hasLowContrastClass) {
        issues.push({
          severity: 'warning',
          element: `${element.tagName.toLowerCase()}[${index}]`,
          issue: 'Potential color contrast issue',
          recommendation: 'Verify color contrast ratio is at least 4.5:1 for normal text',
          wcagCriterion: '1.4.3 Contrast (Minimum)',
        });
      }
    }
  });

  return issues;
}

/**
 * Generate accessibility report
 * 
 * @param issues - Array of accessibility issues
 * @returns Formatted report string
 */
export function generateAccessibilityReport(issues: AccessibilityIssue[]): string {
  if (issues.length === 0) {
    return 'No accessibility issues found! ✓';
  }

  const errors = issues.filter(i => i.severity === 'error');
  const warnings = issues.filter(i => i.severity === 'warning');
  const info = issues.filter(i => i.severity === 'info');

  let report = `Accessibility Audit Report\n`;
  report += `${'='.repeat(50)}\n\n`;
  report += `Total Issues: ${issues.length}\n`;
  report += `  Errors: ${errors.length}\n`;
  report += `  Warnings: ${warnings.length}\n`;
  report += `  Info: ${info.length}\n\n`;

  if (errors.length > 0) {
    report += `ERRORS (${errors.length}):\n`;
    report += `${'-'.repeat(50)}\n`;
    errors.forEach((issue, index) => {
      report += `${index + 1}. ${issue.element}\n`;
      report += `   Issue: ${issue.issue}\n`;
      report += `   Fix: ${issue.recommendation}\n`;
      if (issue.wcagCriterion) {
        report += `   WCAG: ${issue.wcagCriterion}\n`;
      }
      report += `\n`;
    });
  }

  if (warnings.length > 0) {
    report += `WARNINGS (${warnings.length}):\n`;
    report += `${'-'.repeat(50)}\n`;
    warnings.forEach((issue, index) => {
      report += `${index + 1}. ${issue.element}\n`;
      report += `   Issue: ${issue.issue}\n`;
      report += `   Fix: ${issue.recommendation}\n`;
      if (issue.wcagCriterion) {
        report += `   WCAG: ${issue.wcagCriterion}\n`;
      }
      report += `\n`;
    });
  }

  return report;
}

/**
 * Log accessibility issues to console
 * 
 * @param container - Container element to audit
 */
export function logAccessibilityIssues(container: HTMLElement): void {
  const issues = auditAccessibility(container);
  const report = generateAccessibilityReport(issues);
  
  if (issues.length > 0) {
    console.warn('Accessibility Issues Found:');
    console.log(report);
  } else {
    console.log('✓ No accessibility issues found');
  }
}

/**
 * Check if development mode and log accessibility issues
 * Only runs in development to avoid performance impact in production
 */
export function devAccessibilityCheck(container: HTMLElement): void {
  if (process.env.NODE_ENV === 'development') {
    // Delay check to allow DOM to fully render
    setTimeout(() => {
      logAccessibilityIssues(container);
    }, 1000);
  }
}
