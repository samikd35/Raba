'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Check, ChevronLeft, ChevronRight, Loader2, X} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { cofounderAPI } from '@/lib/api/cofounderService';
import { getStepValidator } from '@/lib/cofounder/validation';
import type { ProfileFormData, WizardStep } from '@/types/cofounder';
import { COMMUNITY_DECLARATION_ITEMS } from '@/constants/communityDeclaration';
import Declaration from './Declaration';
import Step1Identity from './Step1Identity';
import Step2Professional from './Step2Professional';
import Step3Capabilities from './Step3Capabilities';
import Step4Location from './Step4Location';
import Step5Commitment from './Step5Commitment';
import Step6Review from './Step6Review';
import ProfileCompletionProgress from '../ProfileCompletionProgress';

const initialFormData: ProfileFormData = {
  // Step 1: Identity
  first_name: '',
  last_name: '',
  gender: 'Prefer not to say',
  date_of_birth: '',
  email: '',
  profile_picture_url: '',
  country: '',
  linkedin_url: '',
  website_url: '',
  education: [],
  employment_history: { entries: [] },
  achievement: '',
  personal_statement: '',
  social_links: {},

  // Step 2: Professional & Interests
  professional_background: '',
  industries_of_interest: [],

  // Step 3: Capabilities
  responsibilities_offered: [],
  skills_needed: [],

  // Step 4: Languages & Location
  preferred_country: '',
  preferred_country_importance: 'important',
  preferred_languages: [],

  // Step 5: Commitment & Stage
  expected_commitment: 'Full-time',
  preferred_commitment: 'Full-time',
  commitment_importance: 'important',
  venture_stage: [],
  preferred_venture_stage: [],

  // Step 6: Age Preference
  age_preference: {
    enabled: false,
    min: null,
    max: null,
    importance: null,
  },
};

const TOTAL_STEPS = 7;

export default function ProfileWizard() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<WizardStep>(0);
  const [formData, setFormData] = useState<ProfileFormData>(initialFormData);
  const [profilePictureFile, setProfilePictureFile] = useState<File | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [declarationChecks, setDeclarationChecks] = useState<boolean[]>(
    COMMUNITY_DECLARATION_ITEMS.map(() => false)
  );
  const [isEditingExistingProfile, setIsEditingExistingProfile] = useState(false);
  const allDeclarationsAccepted = declarationChecks.every(Boolean);

  const handleDeclarationToggle = (index: number) => {
    setDeclarationChecks((prev) =>
      prev.map((checked, i) => (i === index ? !checked : checked))
    );
  };

  // Helper function to map importance values
  const mapImportanceFromApi = (importance: string): 'important' | 'non_negotiable' => {
    return importance === 'nice_to_have' ? 'important' : 'non_negotiable';
  };

  const transformFromApiFormat = (profile: any): ProfileFormData => {
    return {
      // Step 1: Identity
      first_name: profile.first_name || '',
      last_name: profile.last_name || '',
      gender: profile.gender || 'Prefer not to say',
      date_of_birth: profile.date_of_birth || '',
      email: profile.email || '',
      profile_picture_url: profile.profile_picture_url || '',
      country: profile.country || '',
      linkedin_url: profile.linkedin_url || '',
      website_url: profile.website_url || '',
      education: profile.education || [],
      employment_history: {
        entries: (profile.employment_history || []).map((entry: any) => ({
          organization: entry.organization,
          role: entry.role_title || entry.role,
          start_date: entry.start_date,
          end_date: entry.end_date || null,
          is_current: entry.is_current || false,
          responsibilities: entry.responsibilities_description || entry.responsibilities || '',
        }))
      },
      achievement: profile.achievement || '',
      personal_statement: profile.personal_statement || '',
      social_links: profile.social_links || {},

      // Step 2: Professional & Interests
      professional_background: profile.professional_background || '',
      industries_of_interest: profile.industries_of_interest || [],

      // Step 3: Capabilities
      responsibilities_offered: profile.responsibilities_offered || [],
      skills_needed: profile.skills_needed || [],

      // Step 4: Languages & Location
      preferred_country: profile.preferred_country || '',
      preferred_country_importance: profile.preferred_country_importance ? mapImportanceFromApi(profile.preferred_country_importance) : 'important',
      preferred_languages: (profile.preferred_languages || [])
        .map((lang: any) => ({
          language: lang.language_id || lang.code || lang.language || '',
          importance: mapImportanceFromApi(lang.importance),
        }))
        .filter((lang: any) => lang.language && lang.language.trim() !== ''),

      // Step 5: Commitment & Stage
      expected_commitment: profile.expected_commitment || 'Full-time',
      preferred_commitment: profile.preferred_commitment || 'Full-time',
      commitment_importance: profile.commitment_importance ? mapImportanceFromApi(profile.commitment_importance) : 'important',
      venture_stage: profile.venture_stage || [],
      preferred_venture_stage: profile.preferred_venture_stage || [],

      // Step 6: Age Preference - Reconstruct from flattened fields
      age_preference: {
        enabled: profile.age_enabled || false,
        min: profile.age_min || null,
        max: profile.age_max || null,
        importance: profile.age_importance ? mapImportanceFromApi(profile.age_importance) : null,
      },
    };
  };

  useEffect(() => {
    const loadProfile = async () => {
      localStorage.removeItem('cofounder-profile-draft');
      localStorage.removeItem('cofounder-community-declaration');

      try {
        const drafts = await cofounderAPI.profiles.listDrafts(1);
        if (drafts && drafts.length > 0) {
          setFormData(transformFromApiFormat(drafts[0]));
          setDeclarationChecks(COMMUNITY_DECLARATION_ITEMS.map(() => true));
          setCurrentStep(1);
          setIsEditingExistingProfile(true);
          setIsLoading(false);
          return;
        }
      } catch (error) {
      }

      try {
        const summary = await cofounderAPI.profiles.getMyProfileSummary();
        if (summary?.last_approved) {
          setFormData(transformFromApiFormat(summary.last_approved));
          setDeclarationChecks(COMMUNITY_DECLARATION_ITEMS.map(() => true));
          setCurrentStep(1);
          setIsEditingExistingProfile(true);
          setIsLoading(false);
          return;
        }
      } catch (error) {
      }

      setCurrentStep(0);
      setIsLoading(false);
    };

    loadProfile();
  }, []);


  const validateCurrentStep = (): boolean => {
    const validator = getStepValidator(currentStep);
    const dataForValidation =
      currentStep === 1
        ? ({ ...formData, profile_picture_file: profilePictureFile || null } as Partial<ProfileFormData>)
        : formData;
    const result = validator(dataForValidation);
    setValidationErrors(result.errors);
    return result.isValid;
  };


  const handleNext = () => {
    // Step 0: Check declarations
    if (currentStep === 0) {
      if (!allDeclarationsAccepted) {
        toast.error('Please agree to all community guidelines to continue');
        return;
      }
      setCurrentStep(1);
      return;
    }

    if (validateCurrentStep() && currentStep < TOTAL_STEPS) {
      setCurrentStep((prev) => (prev + 1) as WizardStep);
      setValidationErrors([]);
    }
  };

  // Handle previous step
  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => (prev - 1) as WizardStep);
      setValidationErrors([]);
    }
  };

  // Handle step click in progress indicator
  const handleStepClick = (step: WizardStep) => {
    setCurrentStep(step);
    setValidationErrors([]);
  };

  // Update field helper
  const updateField = <K extends keyof ProfileFormData>(
    field: K,
    value: ProfileFormData[K]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Helper function to map importance values from UI to API format
  const mapImportanceToApi = (importance: string): string => {
    return importance === 'important' ? 'nice_to_have' : 'must_have';
  };

  // Transform form data to API format
  const transformToApiFormat = (data: ProfileFormData): any => {
    const payload: any = {
      // Identity
      first_name: data.first_name,
      last_name: data.last_name,
      gender: data.gender,
      date_of_birth: data.date_of_birth,
      email: data.email,
      country: data.country,
      linkedin_url: data.linkedin_url,
      website_url: data.website_url || null,
      education: data.education,
      employment_history: data.employment_history.entries.map(entry => ({
        organization: entry.organization,
        role_title: entry.role,
        start_date: entry.start_date,
        end_date: entry.end_date ?? '',
        is_current: entry.is_current,
        responsibilities_description: entry.responsibilities,
      })),
      achievement: data.achievement,
      personal_statement: data.personal_statement,
      social_links: data.social_links,

      // Professional
      professional_background: data.professional_background,
      industries_of_interest: data.industries_of_interest,

      // Capabilities
      responsibilities_offered: data.responsibilities_offered,
      skills_needed: data.skills_needed,

      // Location & Languages 
      preferred_country: data.preferred_country,
      preferred_country_importance: mapImportanceToApi(data.preferred_country_importance),
      preferred_languages: data.preferred_languages.map(lang => ({
        language_id: lang.language,
        importance: mapImportanceToApi(lang.importance),
      })),

      // Commitment
      expected_commitment: data.expected_commitment,
      preferred_commitment: data.preferred_commitment,
      commitment_importance: mapImportanceToApi(data.commitment_importance),
      venture_stage: data.venture_stage,
      preferred_venture_stage: data.preferred_venture_stage,

      // Age preference
      age_enabled: data.age_preference.enabled,
      age_min: data.age_preference.min,
      age_max: data.age_preference.max,
      age_importance: data.age_preference.importance ? mapImportanceToApi(data.age_preference.importance) : null,
    };

    return payload;
  };

  // Handle save draft
  const handleSaveDraft = async () => {
    try {
      setIsSaving(true);
      const apiPayload = transformToApiFormat(formData);
      await cofounderAPI.profiles.saveDraft(apiPayload, profilePictureFile || undefined);
      toast.success('Draft saved successfully!');
    } catch (error: any) {
      console.error('Failed to save draft:', error);
      toast.error(`Failed to save draft: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Handle submit
  const handleSubmit = async () => {
    if (!validateCurrentStep()) {
      toast.error('Please fill in all required fields correctly');
      return;
    }

    try {
      setIsSubmitting(true);
      const apiPayload = transformToApiFormat(formData);

      await cofounderAPI.profiles.saveDraft(apiPayload, profilePictureFile || undefined);
      await cofounderAPI.profiles.submitLatestDraft();

      // Clear any old localStorage data after successful submission
      localStorage.removeItem('cofounder-profile-draft');
      localStorage.removeItem('cofounder-community-declaration');

      toast.success('Profile submitted successfully! It will be reviewed by our team.');
    } catch (error: any) {
      console.error('Failed to submit profile:', error);
      toast.error(`Failed to submit profile: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    const shouldConfirm = currentStep > 0;
    const confirmed = !shouldConfirm || window.confirm('Are you sure you want to cancel? Unsaved changes will be lost.');
    if (confirmed) {
      router.push('/workspace/cofounder-matching/dashboard');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading your profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2">
            {/* Header */}
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                Cofounder Profile
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Complete your profile to get matched with potential cofounders
              </p>
            </div>

        {/* Progress Indicator*/}
        {currentStep > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between">
              {Array.from({ length: 6 }, (_, i) => i + 1).map((step) => (
                <React.Fragment key={step}>
                  <button
                    onClick={() => handleStepClick(step as WizardStep)}
                    className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all ${
                      step === currentStep
                        ? 'border-brand-500 bg-brand-500 text-white dark:border-brand-400 dark:bg-brand-400'
                        : step < currentStep
                        ? 'border-brand-500 bg-brand-500 text-white dark:border-brand-400 dark:bg-brand-400 cursor-pointer hover:scale-110'
                        : 'border-gray-300 bg-white text-gray-400 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-500'
                    }`}
                  >
                    {step < currentStep ? (
                      <Check className="w-5 h-5" />
                    ) : (
                      <span className="text-sm font-medium">{step}</span>
                    )}
                  </button>
                  {step < 6 && (
                    <div
                      className={`flex-1 h-0.5 mx-2 transition-all ${
                        step < currentStep
                          ? 'bg-brand-500 dark:bg-brand-400'
                          : 'bg-gray-300 dark:bg-gray-700'
                      }`}
                    />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}

        {/* Step Content */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
          {currentStep === 0 && <Declaration declarationChecks={declarationChecks} onToggle={handleDeclarationToggle} />}
          {currentStep === 1 && <Step1Identity formData={formData} updateField={updateField} setProfilePictureFile={setProfilePictureFile} />}
          {currentStep === 2 && <Step2Professional formData={formData} updateField={updateField} />}
          {currentStep === 3 && <Step3Capabilities formData={formData} updateField={updateField} />}
          {currentStep === 4 && <Step4Location formData={formData} updateField={updateField} />}
          {currentStep === 5 && <Step5Commitment formData={formData} updateField={updateField} />}
          {currentStep === 6 && <Step6Review formData={formData} updateField={updateField} />}

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
            >
              <h4 className="text-sm font-semibold text-red-900 dark:text-red-200 mb-2">
                Please fix the following errors:
              </h4>
              <ul className="list-disc list-inside space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index} className="text-sm text-red-700 dark:text-red-300">
                    {error}
                  </li>
                ))}
              </ul>
            </motion.div>
          )}
        </div>

        {/* Navigation Buttons */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {isEditingExistingProfile && (
              <button
                onClick={handleCancel}
                className="px-4 py-3 flex gap-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className='text-red-400 w-4 h-4'/>
                Cancel
              </button>
            )}
            <button
              onClick={handlePrevious}
              disabled={currentStep === 0}
              className="flex items-center gap-2 px-6 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft className="w-5 h-5" />
              Previous
            </button>
          </div>

          <div className="flex items-center gap-3">
            {currentStep === 6 && (
              <button
                onClick={handleSaveDraft}
                disabled={isSaving}
                className="px-6 py-3 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 transition-all"
              >
                {isSaving ? 'Saving...' : 'Save Draft'}
              </button>
            )}

            {currentStep < 6 ? (
              <button
                onClick={handleNext}
                disabled={currentStep === 0 && !allDeclarationsAccepted}
                className="flex items-center gap-2 px-6 py-3 bg-brand-500 dark:bg-brand-400 text-white rounded-lg hover:bg-brand-600 dark:hover:bg-brand-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {currentStep === 0 ? 'Continue' : 'Next'}
                <ChevronRight className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="px-6 py-3 bg-green-600 dark:bg-green-500 text-white rounded-lg hover:bg-green-700 dark:hover:bg-green-600 disabled:opacity-50 transition-all font-medium"
              >
                {isSubmitting ? 'Submitting...' : 'Submit for Review'}
              </button>
            )}
          </div>
        </div>
          </div>

          {/* Sidebar*/}
          <div className="lg:col-span-1">
            <div className="sticky top-8">
              <ProfileCompletionProgress formData={formData} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
