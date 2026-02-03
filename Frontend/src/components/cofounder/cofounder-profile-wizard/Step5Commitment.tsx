'use client';

import React, { useState, useEffect, useRef } from 'react';
import { X, ChevronDown } from 'lucide-react';
import type { ProfileFormData, Commitment, EnumItem } from '@/types/cofounder';
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

export default function Step5Commitment({ formData, updateField }: StepProps) {
  const [commitmentOptions, setCommitmentOptions] = useState<EnumItem[]>([]);
  const [ventureStages, setVentureStages] = useState<EnumItem[]>([]);
  const [loadingCommitment, setLoadingCommitment] = useState(false);
  const [loadingVentureStages, setLoadingVentureStages] = useState(false);
  const [showVentureStageDropdown, setShowVentureStageDropdown] = useState(false);
  const [showPreferredStageDropdown, setShowPreferredStageDropdown] = useState(false);
  const ventureStageDropdownRef = useRef<HTMLDivElement | null>(null);
  const preferredStageDropdownRef = useRef<HTMLDivElement | null>(null);

  useOnClickOutside(
    ventureStageDropdownRef,
    () => setShowVentureStageDropdown(false),
    showVentureStageDropdown
  );
  useOnClickOutside(
    preferredStageDropdownRef,
    () => setShowPreferredStageDropdown(false),
    showPreferredStageDropdown
  );

  // Fetch commitment and venture stages on mount
  useEffect(() => {
    const fetchData = async () => {
      setLoadingCommitment(true);
      setLoadingVentureStages(true);
      try {
        const [commitmentResponse, ventureStagesResponse] = await Promise.all([
          ProfilesEnumsAPI.listCommitment({ pageSize: 50 }),
          ProfilesEnumsAPI.listVentureStages({ pageSize: 200 }),
        ]);
        setCommitmentOptions(commitmentResponse.data);
        setVentureStages(ventureStagesResponse.data);
      } catch (error: any) {
        toast.error(`Failed to load options: ${error.message}`);
      } finally {
        setLoadingCommitment(false);
        setLoadingVentureStages(false);
      }
    };
    fetchData();
  }, []);

  const addVentureStage = (stageName: string) => {
    if (!formData.venture_stage.includes(stageName)) {
      updateField('venture_stage', [...formData.venture_stage, stageName]);
    }
    setShowVentureStageDropdown(false);
  };

  const removeVentureStage = (index: number) => {
    updateField(
      'venture_stage',
      formData.venture_stage.filter((_, i) => i !== index)
    );
  };

  const addPreferredStage = (stageName: string) => {
    if (!formData.preferred_venture_stage.includes(stageName)) {
      updateField('preferred_venture_stage', [
        ...formData.preferred_venture_stage,
        stageName,
      ]);
    }
    setShowPreferredStageDropdown(false);
  };

  const removePreferredStage = (index: number) => {
    updateField(
      'preferred_venture_stage',
      formData.preferred_venture_stage.filter((_, i) => i !== index)
    );
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Commitment & Venture Stage
      </h2>

      {/* Your Commitment */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Your Commitment Level *
        </label>
        {loadingCommitment ? (
          <div className="text-sm text-gray-500">Loading commitment options...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {commitmentOptions.map((option) => (
              <label
                key={option.id}
                className="flex items-start gap-3 text-sm text-gray-700 dark:text-gray-300 cursor-pointer"
              >
                <input
                  type="radio"
                  name="expected-commitment"
                  value={option.name}
                  checked={formData.expected_commitment === option.name}
                  onChange={() => updateField('expected_commitment', option.name as Commitment)}
                  className="mt-1 h-4 w-4 text-brand-600 focus:ring-brand-500"
                />
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">
                    {option.name}
                  </div>
                  {option.description && (
                    <div className="text-xs mt-1 text-gray-500 dark:text-gray-400">
                      {option.description}
                    </div>
                  )}
                </div>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Preferred Commitment */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Expected Cofounder Commitment *
        </label>
        {loadingCommitment ? (
          <div className="text-sm text-gray-500">Loading commitment options...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {commitmentOptions.map((option) => (
              <label
                key={option.id}
                className="flex items-start gap-3 text-sm text-gray-700 dark:text-gray-300 cursor-pointer"
              >
                <input
                  type="radio"
                  name="preferred-commitment"
                  value={option.name}
                  checked={formData.preferred_commitment === option.name}
                  onChange={() => updateField('preferred_commitment', option.name as Commitment)}
                  className="mt-1 h-4 w-4 text-brand-600 focus:ring-brand-500"
                />
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">
                    {option.name}
                  </div>
                  {option.description && (
                    <div className="text-xs mt-1 text-gray-500 dark:text-gray-400">
                      {option.description}
                    </div>
                  )}
                </div>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Commitment Importance */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Commitment Match Importance *
        </label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
            <input
              type="radio"
              name="commitment-importance"
              value="important"
              checked={formData.commitment_importance === 'important'}
              onChange={() => updateField('commitment_importance', 'important')}
              className="mt-1 h-4 w-4 text-brand-600 focus:ring-brand-500"
            />
            <div className="space-y-1">
              <div className="font-medium text-gray-900 dark:text-white">Nice to Have</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Weighted in matching
              </div>
            </div>
          </label>
          <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
            <input
              type="radio"
              name="commitment-importance"
              value="non_negotiable"
              checked={formData.commitment_importance === 'non_negotiable'}
              onChange={() => updateField('commitment_importance', 'non_negotiable')}
              className="mt-1 h-4 w-4 text-brand-600 focus:ring-brand-500"
            />
            <div>
              <div className="font-medium text-gray-900 dark:text-white">Must Have</div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Hard filter
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Your Current Stage */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          I am * (At least one required)
        </label>
        <div className="relative mb-3" ref={ventureStageDropdownRef}>
          <button
            type="button"
            onClick={() => setShowVentureStageDropdown(!showVentureStageDropdown)}
            disabled={loadingVentureStages}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent disabled:opacity-50 flex items-center justify-between"
          >
            <span>
              {loadingVentureStages ? 'Loading...' : 'Select a venture stage'}
            </span>
            <ChevronDown className="w-4 h-4" />
          </button>
          {showVentureStageDropdown && !loadingVentureStages && (
            <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {ventureStages
                .filter(stage => !formData.venture_stage.includes(stage.name))
                .map((stage) => (
                  <button
                    key={stage.id}
                    type="button"
                    onClick={() => addVentureStage(stage.name)}
                    className="w-full px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  >
                    <div className="font-medium">{stage.name}</div>
                    {stage.description && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">{stage.description}</div>
                    )}
                  </button>
                ))}
              {ventureStages.filter(stage => !formData.venture_stage.includes(stage.name)).length === 0 && (
                <div className="px-4 py-2 text-sm text-gray-500 dark:text-gray-400">
                  All stages selected
                </div>
              )}
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {formData.venture_stage.map((stage, index) => (
            <div
              key={index}
              className="flex items-center gap-2 px-3 py-1.5 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 rounded-full border border-orange-200 dark:border-orange-800"
            >
              <span className="text-sm">{stage}</span>
              <button
                type="button"
                onClick={() => removeVentureStage(index)}
                className="text-orange-600 hover:text-orange-700 dark:text-orange-400 dark:hover:text-orange-300"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Preferred Stages */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          I am looking for *(At least one required)
        </label>
        <div className="relative mb-3" ref={preferredStageDropdownRef}>
          <button
            type="button"
            onClick={() => setShowPreferredStageDropdown(!showPreferredStageDropdown)}
            disabled={loadingVentureStages}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent disabled:opacity-50 flex items-center justify-between"
          >
            <span>
              {loadingVentureStages ? 'Loading...' : 'Select a venture stage'}
            </span>
            <ChevronDown className="w-4 h-4" />
          </button>
          {showPreferredStageDropdown && !loadingVentureStages && (
            <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {ventureStages
                .filter(stage => !formData.preferred_venture_stage.includes(stage.name))
                .map((stage) => (
                  <button
                    key={stage.id}
                    type="button"
                    onClick={() => addPreferredStage(stage.name)}
                    className="w-full px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  >
                    <div className="font-medium">{stage.name}</div>
                    {stage.description && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">{stage.description}</div>
                    )}
                  </button>
                ))}
              {ventureStages.filter(stage => !formData.preferred_venture_stage.includes(stage.name)).length === 0 && (
                <div className="px-4 py-2 text-sm text-gray-500 dark:text-gray-400">
                  All stages selected
                </div>
              )}
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {formData.preferred_venture_stage.map((stage, index) => (
            <div
              key={index}
              className="flex items-center gap-2 px-3 py-1.5 bg-teal-50 dark:bg-teal-900/20 text-teal-700 dark:text-teal-300 rounded-full border border-teal-200 dark:border-teal-800"
            >
              <span className="text-sm">{stage}</span>
              <button
                type="button"
                onClick={() => removePreferredStage(index)}
                className="text-teal-600 hover:text-teal-700 dark:text-teal-400 dark:hover:text-teal-300"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
