'use client';

import React, { useState } from 'react';
import { Check, ChevronLeft, ChevronRight, User, Star, Briefcase, ClipboardCheck } from 'lucide-react';
import { WorkExperience } from '@/types/ventureBuilder';
import Step1PersonalInfo from './Step1PersonalInfo';
import Step4Expertise from './Step4Expertise';
import Step3WorkExperience from './Step3WorkExperience';
import Step5Review from './Step5Review';

export interface VBProfileFormData {
  name: string;
  contactEmail: string;
  mainExpertise: string;
  shortIntro: string;
  profilePictureUrl: string;
  biography: string;
  linkedinUrl: string;
  workExperience: WorkExperience[];
  expertiseIds: string[];
}

interface VBProfileWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  invitationToken?: string;
  invitedEmail?: string | null;
}

const STEP_CONFIG = [
  { label: 'Personal Info', icon: User },
  { label: 'Expertise', icon: Star },
  { label: 'Experience', icon: Briefcase },
  { label: 'Review', icon: ClipboardCheck },
];

export default function VBProfileWizard({ isOpen, onClose, onSuccess, invitationToken, invitedEmail }: VBProfileWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<VBProfileFormData>({
    name: '',
    contactEmail: invitedEmail || '',
    mainExpertise: '',
    shortIntro: '',
    profilePictureUrl: '',
    biography: '',
    linkedinUrl: '',
    workExperience: [],
    expertiseIds: [],
  });
  const [profilePictureFile, setProfilePictureFile] = useState<File | null>(null);

  // Update contactEmail when invitedEmail changes (e.g., on initial load)
  React.useEffect(() => {
    if (invitedEmail && !formData.contactEmail) {
      setFormData(prev => ({ ...prev, contactEmail: invitedEmail }));
    }
  }, [invitedEmail]);

  const totalSteps = 4;

  const updateFormData = (data: Partial<VBProfileFormData>) => {
    setFormData((prev) => ({ ...prev, ...data }));
  };

  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleClose = () => {
    setCurrentStep(1);
    setFormData({
      name: '',
      contactEmail: '',
      mainExpertise: '',
      shortIntro: '',
      profilePictureUrl: '',
      biography: '',
      linkedinUrl: '',
      workExperience: [],
      expertiseIds: [],
    });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-brand-100 dark:bg-brand-900/30 mb-4">
          <Star className="w-8 h-8 text-brand-600 dark:text-brand-400" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Venture Builder Profile
        </h1>
        <p className="text-gray-600 dark:text-gray-400 max-w-lg mx-auto">
          Complete your profile to start accepting consultation bookings from founders
        </p>
      </div>

      {/* Progress Indicator with Labels */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {STEP_CONFIG.map((stepConfig, index) => {
            const step = index + 1;
            const StepIcon = stepConfig.icon;
            return (
              <React.Fragment key={step}>
                <div className="flex flex-col items-center">
                  <button
                    onClick={() => step <= currentStep && setCurrentStep(step)}
                    disabled={step > currentStep}
                    className={`flex items-center justify-center w-12 h-12 rounded-full border-2 transition-all duration-200 ${
                      step === currentStep
                        ? 'border-brand-500 bg-brand-500 text-white dark:border-brand-400 dark:bg-brand-400 shadow-lg shadow-brand-500/25'
                        : step < currentStep
                        ? 'border-brand-500 bg-brand-500 text-white dark:border-brand-400 dark:bg-brand-400 cursor-pointer hover:scale-110'
                        : 'border-gray-300 bg-white text-gray-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-500'
                    }`}
                  >
                    {step < currentStep ? (
                      <Check className="w-5 h-5" />
                    ) : (
                      <StepIcon className="w-5 h-5" />
                    )}
                  </button>
                  <span
                    className={`mt-2 text-xs font-medium transition-colors ${
                      step === currentStep
                        ? 'text-brand-600 dark:text-brand-400'
                        : step < currentStep
                        ? 'text-gray-700 dark:text-gray-300'
                        : 'text-gray-400 dark:text-gray-500'
                    }`}
                  >
                    {stepConfig.label}
                  </span>
                </div>
                {step < totalSteps && (
                  <div
                    className={`flex-1 h-0.5 mx-3 mt-[-1.5rem] transition-all ${
                      step < currentStep
                        ? 'bg-brand-500 dark:bg-brand-400'
                        : 'bg-gray-200 dark:bg-gray-700'
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Step Content */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8 mb-6 shadow-theme-sm">
        {currentStep === 1 && (
          <Step1PersonalInfo
            formData={formData}
            updateFormData={updateFormData}
            onNext={handleNext}
            setProfilePictureFile={setProfilePictureFile}
            lockEmail={!!invitedEmail}
          />
        )}
        {currentStep === 2 && (
          <Step4Expertise
            formData={formData}
            updateFormData={updateFormData}
            onNext={handleNext}
            onBack={handleBack}
          />
        )}
        {currentStep === 3 && (
          <Step3WorkExperience
            formData={formData}
            updateFormData={updateFormData}
            onNext={handleNext}
            onBack={handleBack}
          />
        )}
        {currentStep === 4 && (
          <Step5Review
            formData={formData}
            profilePictureFile={profilePictureFile}
            onBack={handleBack}
            onSuccess={() => {
              handleClose();
              onSuccess();
            }}
            invitationToken={invitationToken}
          />
        )}
      </div>

      {/* Step indicator text */}
      <div className="text-center mb-4">
        <span className="text-sm text-gray-500 dark:text-gray-400">
          Step {currentStep} of {totalSteps}
        </span>
      </div>
    </div>
  );
}
