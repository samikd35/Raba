// lib/cofounder/validation.ts
/**
 * Validation utilities for Cofounder Profile Wizard
 */

import type { ProfileFormData, StepValidation, FieldError } from '@/types/cofounder';

type ProfileFormDataWithPictureFile = ProfileFormData & {
  profile_picture?: File | Blob | null;
  profile_picture_file?: File | Blob | null;
};

/**
 * Email validation regex
 */
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * URL validation regex
 */
const URL_REGEX = /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/;

/**
 * LinkedIn URL validation
 */
const LINKEDIN_REGEX = /^https?:\/\/(www\.)?linkedin\.com\/in\/[a-zA-Z0-9_-]+\/?$/;

/**
 * Validate Step 1: Identity
 */
export function validateStep1(data: Partial<ProfileFormData>): StepValidation {
  const errors: FieldError[] = [];

  // Required fields
  if (!data.first_name?.trim()) {
    errors.push({ field: 'first_name', message: 'First name is required' });
  }

  if (!data.last_name?.trim()) {
    errors.push({ field: 'last_name', message: 'Last name is required' });
  }

  if (!data.gender) {
    errors.push({ field: 'gender', message: 'Gender is required' });
  }

  if (!data.date_of_birth) {
    errors.push({ field: 'date_of_birth', message: 'Date of birth is required' });
  } else {
    // Validate age (must be 18+)
    const birthDate = new Date(data.date_of_birth);
    const today = new Date();
    const age = today.getFullYear() - birthDate.getFullYear();
    if (age < 18) {
      errors.push({ field: 'date_of_birth', message: 'You must be at least 18 years old' });
    }
  }

  if (!data.email?.trim()) {
    errors.push({ field: 'email', message: 'Email is required' });
  } else if (!EMAIL_REGEX.test(data.email)) {
    errors.push({ field: 'email', message: 'Invalid email format' });
  }

  // Profile picture validation - allow either an uploaded file or an existing URL
  const dataWithPicture = data as Partial<ProfileFormDataWithPictureFile>;
  const uploadedPicture =
    dataWithPicture.profile_picture_file ?? dataWithPicture.profile_picture ?? null;
  const hasUploadedPicture =
    (typeof File !== 'undefined' && uploadedPicture instanceof File) ||
    (typeof Blob !== 'undefined' && uploadedPicture instanceof Blob) ||
    Boolean(uploadedPicture);
  if (!hasUploadedPicture && !data.profile_picture_url?.trim()) {
    errors.push({ field: 'profile_picture', message: 'Profile picture is required' });
  }

  if (!data.country?.trim()) {
    errors.push({ field: 'country', message: 'Country of residence is required' });
  }

  if (!data.linkedin_url?.trim()) {
    errors.push({ field: 'linkedin_url', message: 'LinkedIn URL is required' });
  } else if (!LINKEDIN_REGEX.test(data.linkedin_url)) {
    errors.push({ field: 'linkedin_url', message: 'Invalid LinkedIn URL format' });
  }

  // Optional website URL
  if (data.website_url && data.website_url.trim() && !URL_REGEX.test(data.website_url)) {
    errors.push({ field: 'website_url', message: 'Invalid website URL format' });
  }

  // Education: at least one entry required
  if (!data.education || data.education.length === 0) {
    errors.push({ field: 'education', message: 'At least one education entry is required' });
  }

  // Employment history: at least one entry required
  if (!data.employment_history?.entries || data.employment_history.entries.length === 0) {
    errors.push({ field: 'employment_history', message: 'At least one employment entry is required' });
  } else {
    // Validate each employment entry
    data.employment_history.entries.forEach((entry, index) => {
      if (!entry.organization?.trim()) {
        errors.push({ field: `employment_history.${index}.organization`, message: 'Organization is required' });
      }
      if (!entry.role?.trim()) {
        errors.push({ field: `employment_history.${index}.role`, message: 'Role title is required' });
      }
      if (!entry.start_date) {
        errors.push({ field: `employment_history.${index}.start_date`, message: 'Start date is required' });
      }
      if (!entry.is_current && !entry.end_date) {
        errors.push({ field: `employment_history.${index}.end_date`, message: 'End date is required if not current role' });
      }
      if (!entry.responsibilities?.trim()) {
        errors.push({ field: `employment_history.${index}.responsibilities`, message: 'Responsibilities are required' });
      } else if (entry.responsibilities.length < 280 || entry.responsibilities.length > 600) {
        errors.push({ field: `employment_history.${index}.responsibilities`, message: 'Responsibilities must be between 280-600 characters' });
      }
    });
  }

  if (!data.achievement?.trim()) {
    errors.push({ field: 'achievement', message: 'Notable achievement is required' });
  }

  if (!data.personal_statement?.trim()) {
    errors.push({ field: 'personal_statement', message: 'Personal statement is required' });
  }

  return {
    isValid: errors.length === 0,
    errors: errors.map(e => e.message),
  };
}

/**
 * Validate Step 2: Professional & Interests
 */
export function validateStep2(data: Partial<ProfileFormData>): StepValidation {
  const errors: FieldError[] = [];

  if (!data.professional_background?.trim()) {
    errors.push({ field: 'professional_background', message: 'Professional background is required' });
  }

  if (!data.industries_of_interest || data.industries_of_interest.length === 0) {
    errors.push({ field: 'industries_of_interest', message: 'At least one industry is required' });
  } else if (data.industries_of_interest.length > 5) {
    errors.push({ field: 'industries_of_interest', message: 'Maximum 5 industries allowed (recommended 2-5)' });
  }

  return {
    isValid: errors.length === 0,
    errors: errors.map(e => e.message),
  };
}

/**
 * Validate Step 3: Capabilities
 */
export function validateStep3(data: Partial<ProfileFormData>): StepValidation {
  const errors: FieldError[] = [];

  if (!data.responsibilities_offered || data.responsibilities_offered.length === 0) {
    errors.push({ field: 'responsibilities_offered', message: 'At least one responsibility you can own is required' });
  }

  if (!data.skills_needed || data.skills_needed.length === 0) {
    errors.push({ field: 'skills_needed', message: 'At least one skill needed in a cofounder is required' });
  }

  return {
    isValid: errors.length === 0,
    errors: errors.map(e => e.message),
  };
}

/**
 * Validate Step 4: Languages & Location
 */
export function validateStep4(data: Partial<ProfileFormData>): StepValidation {
  const errors: FieldError[] = [];

  if (!data.preferred_country?.trim()) {
    errors.push({ field: 'preferred_country', message: 'Preferred cofounder country is required' });
  }

  if (!data.preferred_country_importance) {
    errors.push({ field: 'preferred_country_importance', message: 'Country importance is required' });
  }

  if (!data.preferred_languages || data.preferred_languages.length === 0) {
    errors.push({ field: 'preferred_languages', message: 'At least one working language is required' });
  } else {
    // Validate each language has importance set
    data.preferred_languages.forEach((lang, index) => {
      if (!lang.language?.trim()) {
        errors.push({ field: `preferred_languages.${index}.language`, message: 'Language is required' });
      }
      if (!lang.importance) {
        errors.push({ field: `preferred_languages.${index}.importance`, message: 'Language importance is required' });
      }
    });
  }

  return {
    isValid: errors.length === 0,
    errors: errors.map(e => e.message),
  };
}

/**
 * Validate Step 5: Commitment & Stage
 */
export function validateStep5(data: Partial<ProfileFormData>): StepValidation {
  const errors: FieldError[] = [];

  if (!data.expected_commitment) {
    errors.push({ field: 'expected_commitment', message: 'Your commitment level is required' });
  }

  if (!data.preferred_commitment) {
    errors.push({ field: 'preferred_commitment', message: 'Expected cofounder commitment is required' });
  }

  if (!data.commitment_importance) {
    errors.push({ field: 'commitment_importance', message: 'Commitment importance is required' });
  }

  if (!data.venture_stage || data.venture_stage.length === 0) {
    errors.push({ field: 'venture_stage', message: 'Your current stage is required' });
  }

  if (!data.preferred_venture_stage || data.preferred_venture_stage.length === 0) {
    errors.push({ field: 'preferred_venture_stage', message: 'Preferred venture stages are required' });
  }

  return {
    isValid: errors.length === 0,
    errors: errors.map(e => e.message),
  };
}

/**
 * Validate Step 6: Age Preference & Review
 */
export function validateStep6(data: Partial<ProfileFormData>): StepValidation {
  const errors: FieldError[] = [];

  if (data.age_preference?.enabled) {
    if (data.age_preference.min === null || data.age_preference.min === undefined) {
      errors.push({ field: 'age_preference.min', message: 'Minimum age is required when age preference is enabled' });
    } else if (data.age_preference.min < 20 || data.age_preference.min > 50) {
      errors.push({ field: 'age_preference.min', message: 'Minimum age must be between 20-50' });
    }

    if (data.age_preference.max === null || data.age_preference.max === undefined) {
      errors.push({ field: 'age_preference.max', message: 'Maximum age is required when age preference is enabled' });
    } else if (data.age_preference.max < 20 || data.age_preference.max > 50) {
      errors.push({ field: 'age_preference.max', message: 'Maximum age must be between 20-50' });
    }

    if (
      data.age_preference.min !== null &&
      data.age_preference.max !== null &&
      data.age_preference.min > data.age_preference.max
    ) {
      errors.push({ field: 'age_preference', message: 'Minimum age cannot be greater than maximum age' });
    }

    if (!data.age_preference.importance) {
      errors.push({ field: 'age_preference.importance', message: 'Age importance is required when age preference is enabled' });
    }
  }

  return {
    isValid: errors.length === 0,
    errors: errors.map(e => e.message),
  };
}

/**
 * Validate entire form (all steps)
 */
export function validateAllSteps(data: Partial<ProfileFormData>): StepValidation {
  const step1 = validateStep1(data);
  const step2 = validateStep2(data);
  const step3 = validateStep3(data);
  const step4 = validateStep4(data);
  const step5 = validateStep5(data);
  const step6 = validateStep6(data);

  return {
    isValid: step1.isValid && step2.isValid && step3.isValid && step4.isValid && step5.isValid && step6.isValid,
    errors: [
      ...step1.errors,
      ...step2.errors,
      ...step3.errors,
      ...step4.errors,
      ...step5.errors,
      ...step6.errors,
    ],
  };
}

/**
 * Get validation function for a specific step
 */
export function getStepValidator(step: number): (data: Partial<ProfileFormData>) => StepValidation {
  switch (step) {
    case 0:
      return () => ({ isValid: true, errors: [] });
    case 1:
      return validateStep1;
    case 2:
      return validateStep2;
    case 3:
      return validateStep3;
    case 4:
      return validateStep4;
    case 5:
      return validateStep5;
    case 6:
      return validateStep6;
    default:
      throw new Error(`Invalid step number: ${step}`);
  }
}
