'use client';

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronLeft, ChevronRight, Check } from 'lucide-react';
import { VBProfile } from '@/types/ventureBuilder';
import StepPreWorkspaceSelector from './StepPreWorkspaceSelector';
import Step0TermsConditions from './Step0TermsConditions';
import Step1SelectProject from './Step1SelectProject';
import Step2CheckCredits from './Step2CheckCredits';
import Step3SelectTimeSlot from './Step3SelectTimeSlot';
import Step4Agenda from './Step4Agenda';
import Step5Confirmation from './Step5Confirmation';

export interface BookingFormData {
  workspaceSelected: boolean;
  termsAccepted: boolean;
  termsVersion: string;
  projectId: string;
  projectName: string;
  tenantId: string;
  hasCredits: boolean;
  creditDetails: {
    currentBalance: number;
    requiredCredits: number;
    vbCreditPrice: number;
  } | null;
  sessionDatetime: string;
  agenda: string;
  sessionDuration: number;
}

interface BookingWizardProps {
  isOpen: boolean;
  onClose: () => void;
  ventureBuilder: VBProfile;
}

const TOTAL_STEPS = 7;

export default function BookingWizard({ isOpen, onClose, ventureBuilder }: BookingWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<BookingFormData>({
    workspaceSelected: false,
    termsAccepted: false,
    termsVersion: '',
    projectId: '',
    projectName: '',
    tenantId: '',
    hasCredits: false,
    creditDetails: null,
    sessionDatetime: '',
    agenda: '',
    sessionDuration: 60,
  });

  const updateFormData = useCallback(<K extends keyof BookingFormData>(
    field: K,
    value: BookingFormData[K]
  ) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleNext = useCallback(() => {
    if (currentStep < TOTAL_STEPS - 1) {
      setCurrentStep(prev => prev + 1);
    }
  }, [currentStep]);

  const handleBack = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  }, [currentStep]);

  const handleClose = useCallback(() => {
    setCurrentStep(0);
    setFormData({
      workspaceSelected: false,
      termsAccepted: false,
      termsVersion: '',
      projectId: '',
      projectName: '',
      tenantId: '',
      hasCredits: false,
      creditDetails: null,
      sessionDatetime: '',
      agenda: '',
      sessionDuration: 60,
    });
    onClose();
  }, [onClose]);

  const canProceed = useCallback(() => {
    switch (currentStep) {
      case 0:
        return formData.workspaceSelected;
      case 1:
        return formData.termsAccepted;
      case 2:
        return formData.projectId !== '' && formData.tenantId !== '';
      case 3:
        return formData.hasCredits;
      case 4:
        return formData.sessionDatetime !== '';
      case 5:
        return formData.agenda.trim().length >= 10;
      case 6:
        return true;
      default:
        return false;
    }
  }, [currentStep, formData]);

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return (
          <StepPreWorkspaceSelector
            onWorkspaceSelected={(tenantId, workspaceName) => {
              updateFormData('tenantId', tenantId);
              updateFormData('workspaceSelected', true);
            }}
          />
        );
      case 1:
        return (
          <Step0TermsConditions
            termsAccepted={formData.termsAccepted}
            onToggle={(accepted, version) => {
              updateFormData('termsAccepted', accepted);
              updateFormData('termsVersion', version);
            }}
          />
        );
      case 2:
        return (
          <Step1SelectProject
            selectedProjectId={formData.projectId}
            onSelectProject={(projectId, projectName, tenantId) => {
              updateFormData('projectId', projectId);
              updateFormData('projectName', projectName);
              updateFormData('tenantId', tenantId);
            }}
          />
        );
      case 3:
        return (
          <Step2CheckCredits
            ventureBuilder={ventureBuilder}
            onCreditsChecked={(hasCredits, creditDetails) => {
              updateFormData('hasCredits', hasCredits);
              updateFormData('creditDetails', creditDetails);
            }}
          />
        );
      case 4:
        return (
          <Step3SelectTimeSlot
            vbId={ventureBuilder.id}
            selectedDatetime={formData.sessionDatetime}
            onSelectTime={(datetime) => updateFormData('sessionDatetime', datetime)}
            ventureBuilderName={ventureBuilder.full_name || ventureBuilder.name || 'Venture Builder'}
          />
        );
      case 5:
        return (
          <Step4Agenda
            agenda={formData.agenda}
            onAgendaChange={(agenda) => updateFormData('agenda', agenda)}
          />
        );
      case 6:
        return (
          <Step5Confirmation
            formData={formData}
            ventureBuilder={ventureBuilder}
            onSuccess={handleClose}
          />
        );
      default:
        return null;
    }
  };

  if (!isOpen) return null;

  const displayName = ventureBuilder.full_name || ventureBuilder.name || 'Venture Builder';

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 overflow-y-auto">
      <div className="min-h-screen w-full bg-gray-50 dark:bg-gray-900 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Book a Session
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Schedule a consultation with {displayName}
            </p>
          </div>

          {/* Progress Indicator */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              {Array.from({ length: TOTAL_STEPS }, (_, i) => i).map((step) => (
                <React.Fragment key={step}>
                  <button
                    onClick={() => setCurrentStep(step)}
                    disabled={step > currentStep}
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
                      <span className="text-sm font-medium">{step + 1}</span>
                    )}
                  </button>
                  {step < TOTAL_STEPS - 1 && (
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

          {/* Step Content */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentStep}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
              >
                {renderStep()}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={handleClose}
                className="px-4 py-3 flex gap-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="text-red-400 w-4 h-4" />
                Cancel
              </button>
              <button
                onClick={handleBack}
                disabled={currentStep === 0}
                className="flex items-center gap-2 px-6 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <ChevronLeft className="w-5 h-5" />
                Previous
              </button>
            </div>

            <div className="flex items-center gap-3">
              {currentStep < TOTAL_STEPS - 1 ? (
                <button
                  onClick={handleNext}
                  disabled={!canProceed()}
                  className="flex items-center gap-2 px-6 py-3 bg-brand-500 dark:bg-brand-400 text-white rounded-lg hover:bg-brand-600 dark:hover:bg-brand-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {currentStep === 0 ? 'Continue' : 'Next'}
                  <ChevronRight className="w-5 h-5" />
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
