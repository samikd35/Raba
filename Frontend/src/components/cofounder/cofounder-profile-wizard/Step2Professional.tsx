'use client';

import React, { useState, useEffect, useRef } from 'react';
import { X, ChevronDown } from 'lucide-react';
import type { ProfileFormData, EnumItem } from '@/types/cofounder';
import { ProfilesEnumsAPI } from '@/lib/api/cofounderService';
import { toast } from 'react-hot-toast';
import { PROFESSIONAL_BACKGROUND_OPTIONS } from '@/constants/onboarding';
import { useOnClickOutside } from '@/hooks/useOnClickOutside';

interface StepProps {
  formData: ProfileFormData;
  updateField: <K extends keyof ProfileFormData>(
    field: K,
    value: ProfileFormData[K]
  ) => void;
}

export default function Step2Professional({ formData, updateField }: StepProps) {
  const [industries, setIndustries] = useState<EnumItem[]>([]);
  const [loadingIndustries, setLoadingIndustries] = useState(false);
  const [showIndustryDropdown, setShowIndustryDropdown] = useState(false);
  const [showProfessionalDropdown, setShowProfessionalDropdown] = useState(false);
  const industryDropdownRef = useRef<HTMLDivElement | null>(null);
  const professionalDropdownRef = useRef<HTMLDivElement | null>(null);

  useOnClickOutside(industryDropdownRef, () => setShowIndustryDropdown(false), showIndustryDropdown);
  useOnClickOutside(professionalDropdownRef, () => setShowProfessionalDropdown(false), showProfessionalDropdown);

  // Fetch industries on mount
  useEffect(() => {
    const fetchIndustries = async () => {
      setLoadingIndustries(true);
      try {
        const response = await ProfilesEnumsAPI.listIndustries({ pageSize: 200 });
        setIndustries(response.data);
      } catch (error: any) {
        toast.error(`Failed to load industries: ${error.message}`);
      } finally {
        setLoadingIndustries(false);
      }
    };
    fetchIndustries();
  }, []);

  const addIndustry = (industryName: string) => {
    if (formData.industries_of_interest.length < 5 && !formData.industries_of_interest.includes(industryName)) {
      updateField('industries_of_interest', [
        ...formData.industries_of_interest,
        industryName,
      ]);
    }
    setShowIndustryDropdown(false);
  };

  const removeIndustry = (index: number) => {
    updateField(
      'industries_of_interest',
      formData.industries_of_interest.filter((_, i) => i !== index)
    );
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Professional Background & Interests
      </h2>

      {/* Professional Background */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Professional Background * (Display field)
        </label>
        <div className="relative" ref={professionalDropdownRef}>
          <button
            type="button"
            onClick={() => setShowProfessionalDropdown(!showProfessionalDropdown)}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent flex items-center justify-between"
          >
            <span className={!formData.professional_background ? 'text-gray-500' : ''}>
              {formData.professional_background || 'Select a professional background'}
            </span>
            <ChevronDown className="w-4 h-4" />
          </button>
          {showProfessionalDropdown && (
            <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {PROFESSIONAL_BACKGROUND_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => {
                    updateField('professional_background', option);
                    setShowProfessionalDropdown(false);
                  }}
                  className="w-full px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-900 dark:text-white text-sm"
                >
                  {option}
                </button>
              ))}
            </div>
          )}
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          This is a summary field shown on your profile
        </p>
      </div>

      {/* Industries of Interest */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Industries of Interest * (2-5 recommended, max 5)
        </label>
        <div className="relative mb-3" ref={industryDropdownRef}>
          <button
            type="button"
            onClick={() => setShowIndustryDropdown(!showIndustryDropdown)}
            disabled={formData.industries_of_interest.length >= 5 || loadingIndustries}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent disabled:opacity-50 flex items-center justify-between"
          >
            <span className={formData.industries_of_interest.length >= 5 ? 'text-gray-500' : ''}>
              {loadingIndustries ? 'Loading...' : formData.industries_of_interest.length >= 5 ? 'Maximum reached' : 'Select an industry'}
            </span>
            <ChevronDown className="w-4 h-4" />
          </button>
          {showIndustryDropdown && !loadingIndustries && (
            <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {industries
                .filter(ind => !formData.industries_of_interest.includes(ind.name))
                .map((industry) => (
                  <button
                    key={industry.id}
                    type="button"
                    onClick={() => addIndustry(industry.name)}
                    className="w-full px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  >
                    <div className="font-medium">{industry.name}</div>
                    {industry.description && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">{industry.description}</div>
                    )}
                  </button>
                ))}
              {industries.filter(ind => !formData.industries_of_interest.includes(ind.name)).length === 0 && (
                <div className="px-4 py-2 text-sm text-gray-500 dark:text-gray-400">
                  All industries selected
                </div>
              )}
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {formData.industries_of_interest.map((industry, index) => (
            <div
              key={index}
              className="flex items-center gap-2 px-3 py-1.5 bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300 rounded-full border border-brand-200 dark:border-brand-800"
            >
              <span className="text-sm">{industry}</span>
              <button
                type="button"
                onClick={() => removeIndustry(index)}
                className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          {formData.industries_of_interest.length}/5 industries selected
        </p>
      </div>
    </div>
  );
}
