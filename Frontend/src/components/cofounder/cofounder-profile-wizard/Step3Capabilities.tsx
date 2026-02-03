'use client';

import React, { useState, useEffect, useRef } from 'react';
import { X, ChevronDown } from 'lucide-react';
import type { ProfileFormData, EnumItem } from '@/types/cofounder';
import { ProfilesEnumsAPI } from '@/lib/api/cofounderService';
import { toast } from 'react-hot-toast';
import { useOnClickOutside } from '@/hooks/useOnClickOutside';

interface StepProps {
  formData: ProfileFormData;
  updateField: <K extends keyof ProfileFormData>(
    field: K,
    value: ProfileFormData[K]
  ) => void;
}

export default function Step3Capabilities({ formData, updateField }: StepProps) {
  const [responsibilities, setResponsibilities] = useState<EnumItem[]>([]);
  const [loadingResponsibilities, setLoadingResponsibilities] = useState(false);
  const [showResponsibilityDropdown, setShowResponsibilityDropdown] = useState(false);
  const [showSkillDropdown, setShowSkillDropdown] = useState(false);
  const responsibilityDropdownRef = useRef<HTMLDivElement | null>(null);
  const skillDropdownRef = useRef<HTMLDivElement | null>(null);

  useOnClickOutside(
    responsibilityDropdownRef,
    () => setShowResponsibilityDropdown(false),
    showResponsibilityDropdown
  );

  useOnClickOutside(skillDropdownRef, () => setShowSkillDropdown(false), showSkillDropdown);

  // Fetch responsibilities on mount
  useEffect(() => {
    const fetchResponsibilities = async () => {
      setLoadingResponsibilities(true);
      try {
        const response = await ProfilesEnumsAPI.listResponsibilities({ pageSize: 200 });
        setResponsibilities(response.data);
      } catch (error: any) {
        toast.error(`Failed to load responsibilities: ${error.message}`);
      } finally {
        setLoadingResponsibilities(false);
      }
    };
    fetchResponsibilities();
  }, []);

  const addResponsibility = (responsibilityName: string) => {
    if (!formData.responsibilities_offered.includes(responsibilityName)) {
      updateField('responsibilities_offered', [
        ...formData.responsibilities_offered,
        responsibilityName,
      ]);
    }
    setShowResponsibilityDropdown(false);
  };

  const removeResponsibility = (index: number) => {
    updateField(
      'responsibilities_offered',
      formData.responsibilities_offered.filter((_, i) => i !== index)
    );
  };

  const addSkill = (skillName: string) => {
    if (!formData.skills_needed.includes(skillName)) {
      updateField('skills_needed', [...formData.skills_needed, skillName]);
    }
    setShowSkillDropdown(false);
  };

  const removeSkill = (index: number) => {
    updateField(
      'skills_needed',
      formData.skills_needed.filter((_, i) => i !== index)
    );
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Capabilities & Skills
      </h2>

      {/* Responsibilities Offered */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Responsibilities You Can Own * (At least one required)
        </label>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          What areas can you take full ownership of in a startup?
        </p>
        <div className="relative mb-3" ref={responsibilityDropdownRef}>
          <button
            type="button"
            onClick={() => setShowResponsibilityDropdown(!showResponsibilityDropdown)}
            disabled={loadingResponsibilities}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent disabled:opacity-50 flex items-center justify-between"
          >
            <span>
              {loadingResponsibilities ? 'Loading...' : 'Select a responsibility'}
            </span>
            <ChevronDown className="w-4 h-4" />
          </button>
          {showResponsibilityDropdown && !loadingResponsibilities && (
            <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {responsibilities
                .filter(resp => !formData.responsibilities_offered.includes(resp.name))
                .map((responsibility) => (
                  <button
                    key={responsibility.id}
                    type="button"
                    onClick={() => addResponsibility(responsibility.name)}
                    className="w-full px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  >
                    <div className="font-medium">{responsibility.name}</div>
                    {responsibility.description && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">{responsibility.description}</div>
                    )}
                  </button>
                ))}
              {responsibilities.filter(resp => !formData.responsibilities_offered.includes(resp.name)).length === 0 && (
                <div className="px-4 py-2 text-sm text-gray-500 dark:text-gray-400">
                  All responsibilities selected
                </div>
              )}
            </div>
          )}
        </div>
        <div className="space-y-2">
          {formData.responsibilities_offered.map((resp, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg"
            >
              <span className="text-sm text-gray-700 dark:text-gray-300">{resp}</span>
              <button
                type="button"
                onClick={() => removeResponsibility(index)}
                className="text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Skills Needed */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Skills Needed in a Cofounder * (At least one required)
        </label>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          What skills or expertise are you looking for in your cofounder?
        </p>
        <div className="relative mb-3" ref={skillDropdownRef}>
          <button
            type="button"
            onClick={() => setShowSkillDropdown(!showSkillDropdown)}
            disabled={loadingResponsibilities}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent disabled:opacity-50 flex items-center justify-between"
          >
            <span>{loadingResponsibilities ? 'Loading...' : 'Select a skill need'}</span>
            <ChevronDown className="w-4 h-4" />
          </button>
          {showSkillDropdown && !loadingResponsibilities && (
            <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {responsibilities
                .filter((resp) => !formData.skills_needed.includes(resp.name))
                .map((responsibility) => (
                  <button
                    key={responsibility.id}
                    type="button"
                    onClick={() => addSkill(responsibility.name)}
                    className="w-full px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  >
                    <div className="font-medium">{responsibility.name}</div>
                    {responsibility.description && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {responsibility.description}
                      </div>
                    )}
                  </button>
                ))}
              {responsibilities.filter((resp) => !formData.skills_needed.includes(resp.name)).length === 0 && (
                <div className="px-4 py-2 text-sm text-gray-500 dark:text-gray-400">
                  All skills selected
                </div>
              )}
            </div>
          )}
        </div>
        <div className="space-y-2">
          {formData.skills_needed.map((skill, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
            >
              <span className="text-sm text-gray-700 dark:text-gray-300">{skill}</span>
              <button
                type="button"
                onClick={() => removeSkill(index)}
                className="text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
