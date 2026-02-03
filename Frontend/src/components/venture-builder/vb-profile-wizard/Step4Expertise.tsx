'use client';

import React, { useState, useEffect } from 'react';
import { Star, ArrowRight, ArrowLeft, Loader2, CheckCircle } from 'lucide-react';
import { VBProfileFormData } from './VBProfileWizard';
import { fetchExpertiseAreas } from '@/lib/api/venture-builder';
import { toast } from 'react-hot-toast';

interface Step4ExpertiseProps {
  formData: VBProfileFormData;
  updateFormData: (data: Partial<VBProfileFormData>) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function Step4Expertise({ formData, updateFormData, onNext, onBack }: Step4ExpertiseProps) {
  const [expertiseAreas, setExpertiseAreas] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errors, setErrors] = useState<string>('');

  useEffect(() => {
    const loadExpertiseAreas = async () => {
      try {
        setIsLoading(true);
        const data = await fetchExpertiseAreas();
        setExpertiseAreas(data.filter((area: any) => area.is_active));
      } catch (error: any) {
        console.error('Error fetching expertise areas:', error);
        toast.error('Failed to load expertise areas');
        setExpertiseAreas([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadExpertiseAreas();
  }, []);

  const MAX_EXPERTISE = 2;

  const toggleExpertise = (expertiseId: string) => {
    const isSelected = formData.expertiseIds.includes(expertiseId);
    const selectedArea = expertiseAreas.find((area) => area.id === expertiseId);

    if (isSelected) {
      const newExpertiseIds = formData.expertiseIds.filter((id) => id !== expertiseId);
      // Update mainExpertise to the first remaining selection, or empty if none
      const firstRemainingId = newExpertiseIds[0];
      const firstRemainingArea = expertiseAreas.find((area) => area.id === firstRemainingId);
      updateFormData({
        expertiseIds: newExpertiseIds,
        mainExpertise: firstRemainingArea?.name || '',
      });
    } else {
      // Check if max limit reached
      if (formData.expertiseIds.length >= MAX_EXPERTISE) {
        toast.error(`You can only select up to ${MAX_EXPERTISE} areas of expertise`);
        return;
      }
      const newExpertiseIds = [...formData.expertiseIds, expertiseId];
      // If this is the first selection, set it as mainExpertise
      const mainExpertise = formData.expertiseIds.length === 0 && selectedArea
        ? selectedArea.name
        : formData.mainExpertise;
      updateFormData({
        expertiseIds: newExpertiseIds,
        mainExpertise,
      });
    }
    if (errors) setErrors('');
  };

  const handleNext = () => {
    if (formData.expertiseIds.length === 0) {
      setErrors('Please select at least one area of expertise');
      return;
    }

    setErrors('');
    onNext();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-brand-100 dark:bg-brand-900/30 mb-4">
            <Loader2 className="w-8 h-8 text-brand-500 dark:text-brand-400 animate-spin" />
          </div>
          <p className="text-gray-600 dark:text-gray-400 font-medium">Loading expertise areas...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Section Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Main Expertise
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Select up to {MAX_EXPERTISE} main areas of expertise to help founders find you
        </p>
      </div>

      {/* Error State */}
      {errors && (
        <div className="p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-700 rounded-lg">
          <p className="text-sm text-error-600 dark:text-error-400 font-medium">{errors}</p>
        </div>
      )}

      {/* Empty State */}
      {expertiseAreas.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-200 dark:bg-gray-700 mb-4">
            <Star className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-600 dark:text-gray-400 font-medium">No expertise areas available</p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">Please contact support if this persists</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {expertiseAreas.map((area) => {
            const isSelected = formData.expertiseIds.includes(area.id);
            const isMaxReached = formData.expertiseIds.length >= MAX_EXPERTISE;
            const isDisabled = !isSelected && isMaxReached;
            return (
              <button
                key={area.id}
                onClick={() => toggleExpertise(area.id)}
                disabled={isDisabled}
                className={`p-5 rounded-xl border-2 text-left transition-all duration-200 group ${
                  isSelected
                    ? 'border-brand-500 dark:border-brand-400 bg-brand-50 dark:bg-brand-900/20 shadow-md ring-1 ring-brand-500/20'
                    : isDisabled
                    ? 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 opacity-50 cursor-not-allowed'
                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-sm'
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-all ${
                    isSelected
                      ? 'border-brand-500 dark:border-brand-400 bg-brand-500 dark:bg-brand-400'
                      : isDisabled
                      ? 'border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-700'
                      : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 group-hover:border-brand-400'
                  }`}>
                    {isSelected && (
                      <CheckCircle className="w-4 h-4 text-white" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className={`font-semibold mb-1 transition-colors ${
                      isSelected
                        ? 'text-brand-700 dark:text-brand-300'
                        : 'text-gray-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-400'
                    }`}>
                      {area.name}
                    </h4>
                    {area.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {area.description}
                      </p>
                    )}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Selection Counter */}
      <div className={`p-4 rounded-lg flex items-center gap-3 ${
        formData.expertiseIds.length > 0
          ? 'bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-700'
          : 'bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700'
      }`}>
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
          formData.expertiseIds.length > 0
            ? 'bg-success-100 dark:bg-success-800/40'
            : 'bg-gray-200 dark:bg-gray-700'
        }`}>
          {formData.expertiseIds.length > 0 ? (
            <CheckCircle className="w-5 h-5 text-success-600 dark:text-success-400" />
          ) : (
            <Star className="w-5 h-5 text-gray-400" />
          )}
        </div>
        <p className={`text-sm font-medium ${
          formData.expertiseIds.length > 0
            ? 'text-success-700 dark:text-success-300'
            : 'text-gray-600 dark:text-gray-400'
        }`}>
          <strong>{formData.expertiseIds.length}</strong> of {MAX_EXPERTISE} expertise area{formData.expertiseIds.length !== 1 ? 's' : ''} selected
        </p>
      </div>

      {/* Navigation Buttons */}
      <div className="flex gap-4 pt-4">
        <button
          onClick={onBack}
          className="flex-1 py-3.5 px-6 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
        >
          <ArrowLeft className="w-5 h-5" />
          Back
        </button>
        <button
          onClick={handleNext}
          className="flex-1 py-3.5 px-6 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
        >
          Continue
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
