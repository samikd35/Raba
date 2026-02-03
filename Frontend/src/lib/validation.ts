// Validation utilities for forms

export interface ValidationError {
  field: string;
  message: string;
}

export class FormValidator {
  static validateEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  static validatePhoneNumber(phone: string): boolean {
    // Basic phone number validation (allows various formats)
    const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
    // Remove spaces, dashes, parentheses for validation
    const cleanPhone = phone.replace(/[\s\-\(\)]/g, '');
    return phoneRegex.test(cleanPhone);
  }

  static validateRequired(value: string): boolean {
    return value.trim().length > 0;
  }

  static validateCreditAllocation(
    numberOfInvitees: number,
    assignedCredits: number,
    organizationMonthlyLimit: number,
    currentUsage: number
  ): { isValid: boolean; errorMessage?: string } {
    const totalRequested = numberOfInvitees * assignedCredits;
    const availableCredits = organizationMonthlyLimit - currentUsage;
    
    if (totalRequested > availableCredits) {
      return {
        isValid: false,
        errorMessage: `Insufficient credits. You need ${totalRequested} credits but only ${availableCredits} are available.`
      };
    }
    
    return { isValid: true };
  }
}

// Credit allocation helper functions
export class CreditAllocator {
  static calculateTotalCreditsNeeded(numberOfInvitees: number, creditsPerInvitee: number): number {
    return numberOfInvitees * creditsPerInvitee;
  }

  static calculateAvailableCredits(monthlyLimit: number, currentUsage: number): number {
    return monthlyLimit - currentUsage;
  }

  static isAllocationValid(
    numberOfInvitees: number,
    creditsPerInvitee: number,
    monthlyLimit: number,
    currentUsage: number
  ): { isValid: boolean; message: string } {
    const totalNeeded = this.calculateTotalCreditsNeeded(numberOfInvitees, creditsPerInvitee);
    const available = this.calculateAvailableCredits(monthlyLimit, currentUsage);
    
    if (totalNeeded > available) {
      return {
        isValid: false,
        message: `Not enough credits. You need ${totalNeeded} but only ${available} are available.`
      };
    }
    
    return {
      isValid: true,
      message: `Allocation is valid. ${totalNeeded} credits will be used.`
    };
  }
}