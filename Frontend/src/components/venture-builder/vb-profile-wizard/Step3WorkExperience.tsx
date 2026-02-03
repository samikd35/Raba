'use client';

import React, { useState, useMemo } from 'react';
import { X, ArrowRight, ArrowLeft, Briefcase, Building2, Plus, CheckCircle } from 'lucide-react';
import { VBProfileFormData } from './VBProfileWizard';
import { WorkExperience } from '@/types/ventureBuilder';
import { DatePicker } from '@/components/ui/date-picker';

interface Step3WorkExperienceProps {
  formData: VBProfileFormData;
  updateFormData: (data: Partial<VBProfileFormData>) => void;
  onNext: () => void;
  onBack: () => void;
}

interface ExperienceForm {
  position: string;
  organization: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  description: string;
}

export default function Step3WorkExperience({ formData, updateFormData, onNext, onBack }: Step3WorkExperienceProps) {
  const [errors, setErrors] = useState<string>('');
  const [experienceForm, setExperienceForm] = useState<ExperienceForm>({
    position: '',
    organization: '',
    start_date: '',
    end_date: null,
    is_current: false,
    description: '',
  });

  const employmentYearStart = 1980;
  const employmentYearEnd = useMemo(() => {
    const date = new Date();
    return date.getFullYear() + 5;
  }, []);

  const charCount = experienceForm.description.length;
  const isCharCountValid = charCount >= 50 && charCount <= 600;
  const canAddEntry = isCharCountValid && experienceForm.organization && experienceForm.position;

  const formatYearsFromDates = (start: string, end: string | null, isCurrent: boolean): string => {
    if (!start) return '';
    const startFormatted = start;
    if (isCurrent) {
      return `${startFormatted} - Present`;
    }
    return end ? `${startFormatted} - ${end}` : startFormatted;
  };

  const addExperience = () => {
    if (experienceForm.organization && experienceForm.position && experienceForm.description) {
      const newExperience: WorkExperience = {
        position: experienceForm.position,
        organization: experienceForm.organization,
        years: formatYearsFromDates(experienceForm.start_date, experienceForm.end_date, experienceForm.is_current),
        description: experienceForm.description,
      };
      updateFormData({
        workExperience: [...formData.workExperience, newExperience],
      });
      setExperienceForm({
        position: '',
        organization: '',
        start_date: '',
        end_date: null,
        is_current: false,
        description: '',
      });
      if (errors) setErrors('');
    }
  };

  const removeExperience = (index: number) => {
    updateFormData({
      workExperience: formData.workExperience.filter((_, i) => i !== index),
    });
  };

  const handleNext = () => {
    if (formData.workExperience.length === 0) {
      setErrors('Please add at least one work experience');
      return;
    }

    setErrors('');
    onNext();
  };

  return (
    <div className="space-y-8">
      {/* Section Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Work Experience
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Add your relevant professional experience to build credibility with founders
        </p>
      </div>

      {/* Error State */}
      {errors && (
        <div className="p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-700 rounded-lg">
          <p className="text-sm text-error-600 dark:text-error-400 font-medium">{errors}</p>
        </div>
      )}

      {/* Employment Form */}
      <div className="p-6 bg-gray-50 dark:bg-gray-700/30 rounded-xl border border-gray-200 dark:border-gray-600">
        <div className="flex items-center gap-2 mb-5">
          <div className="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
            <Briefcase className="w-4 h-4 text-brand-600 dark:text-brand-400" />
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-white">
            Add Employment Entry
          </h3>
          <span className="text-xs text-error-500 font-medium ml-auto">* Required</span>
        </div>

        <div className="space-y-5">
          {/* Organization and Position */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Organization <span className="text-error-500">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Building2 className="h-4 w-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  value={experienceForm.organization}
                  onChange={(e) =>
                    setExperienceForm({ ...experienceForm, organization: e.target.value })
                  }
                  className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                  placeholder="Company or Organization name"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Role / Position <span className="text-error-500">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Briefcase className="h-4 w-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  value={experienceForm.position}
                  onChange={(e) =>
                    setExperienceForm({ ...experienceForm, position: e.target.value })
                  }
                  className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                  placeholder="Your title or role"
                />
              </div>
            </div>
          </div>

          {/* Dates and Current Role */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <DatePicker
              label="Start Date"
              value={experienceForm.start_date || null}
              onChange={(value) =>
                setExperienceForm({
                  ...experienceForm,
                  start_date: value || '',
                })
              }
              placeholder="Select start date"
              mode="month"
              fromYear={employmentYearStart}
              toYear={employmentYearEnd}
            />
            <DatePicker
              label="End Date"
              value={experienceForm.end_date}
              onChange={(value) =>
                setExperienceForm({
                  ...experienceForm,
                  end_date: value,
                })
              }
              placeholder="Select end date"
              mode="month"
              fromYear={employmentYearStart}
              toYear={employmentYearEnd}
              disabled={experienceForm.is_current}
            />
            <label className="flex items-center gap-3 h-11 px-4 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors">
              <input
                type="checkbox"
                checked={experienceForm.is_current}
                onChange={(e) =>
                  setExperienceForm({
                    ...experienceForm,
                    is_current: e.target.checked,
                    end_date: e.target.checked ? null : experienceForm.end_date,
                  })
                }
                className="w-4 h-4 text-brand-500 border-gray-300 rounded focus:ring-brand-500"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Current Role</span>
            </label>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Key Responsibilities & Achievements <span className="text-error-500">*</span>
            </label>
            <textarea
              value={experienceForm.description}
              onChange={(e) =>
                setExperienceForm({ ...experienceForm, description: e.target.value })
              }
              rows={4}
              maxLength={600}
              className="w-full px-4 py-3 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all resize-none"
              placeholder="Describe your key responsibilities and notable achievements in this role..."
            />
            <div className="flex justify-between mt-1.5">
              <span className="text-xs text-gray-500 dark:text-gray-400">Minimum 50 characters</span>
              <span className={`text-xs font-medium ${
                isCharCountValid
                  ? 'text-success-600 dark:text-success-400'
                  : charCount > 0 ? 'text-warning-600 dark:text-warning-400' : 'text-gray-400'
              }`}>
                {charCount}/600
              </span>
            </div>
          </div>

          {/* Add Button */}
          <button
            type="button"
            onClick={addExperience}
            disabled={!canAddEntry}
            className="w-full py-3 px-4 bg-brand-500 dark:bg-brand-500 text-white rounded-lg font-medium hover:bg-brand-600 dark:hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Add Employment Entry
          </button>
        </div>
      </div>

      {/* Added Entries List */}
      {formData.workExperience.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
            Added Experiences ({formData.workExperience.length})
          </h3>
          {formData.workExperience.map((entry, index) => (
            <div
              key={index}
              className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
                    <Briefcase className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900 dark:text-white">
                      {entry.position}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {entry.organization}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-500 mt-0.5">
                      {entry.years}
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeExperience(index)}
                  className="p-1.5 text-error-500 hover:bg-error-50 dark:hover:bg-error-900/20 rounded-lg transition-colors"
                  title="Remove entry"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 ml-13 pl-0.5 line-clamp-2">{entry.description}</p>
            </div>
          ))}
        </div>
      )}

      {/* Success Counter */}
      {formData.workExperience.length > 0 && (
        <div className="p-4 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-700 rounded-lg flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-success-100 dark:bg-success-800/40 flex items-center justify-center">
            <CheckCircle className="w-5 h-5 text-success-600 dark:text-success-400" />
          </div>
          <p className="text-sm text-success-700 dark:text-success-300 font-medium">
            <strong>{formData.workExperience.length}</strong> experience{formData.workExperience.length > 1 ? 's' : ''} added
          </p>
        </div>
      )}

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
