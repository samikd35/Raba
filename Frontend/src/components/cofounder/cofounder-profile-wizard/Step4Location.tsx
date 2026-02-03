'use client';

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { toast } from 'react-hot-toast';
import type { ProfileFormData, Importance } from '@/types/cofounder';
import { cofounderAPI } from '@/lib/api/cofounderService';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { CountrySelection } from '@/components/CountrySelection';

interface StepProps {
  formData: ProfileFormData;
  updateField: <K extends keyof ProfileFormData>(
    field: K,
    value: ProfileFormData[K]
  ) => void;
}

const importanceOptions: Array<{ value: Importance; title: string; description: string }> = [
  { value: 'important', title: 'Nice to Have', description: 'Weighted in matching' },
  { value: 'non_negotiable', title: 'Must Have', description: 'Hard filter' },
];

export default function Step4Location({ formData, updateField }: StepProps) {
  const [languageInput, setLanguageInput] = useState('');
  const [languageImportance, setLanguageImportance] = useState<Importance>('important');
  const [availableLanguages, setAvailableLanguages] = useState<Array<{ id: string; name: string }>>([]);
  const [isLoadingLanguages, setIsLoadingLanguages] = useState(true);

  useEffect(() => {
    const loadLanguages = async () => {
      try {
        setIsLoadingLanguages(true);
        const response = await cofounderAPI.enums.listLanguages({ pageSize: 500 });
        setAvailableLanguages(response.data.map((item) => ({ id: item.id, name: item.name })));
      } catch (error) {
        console.error('Failed to load languages:', error);
    
      } finally {
        setIsLoadingLanguages(false);
      }
    };

    loadLanguages();
  }, []);

  const addLanguage = () => {
    if (languageInput && languageInput.trim()) {
      // Check if language already exists
      const alreadyExists = formData.preferred_languages.some(
        (lang) => lang.language === languageInput.trim()
      );

      if (alreadyExists) {
        toast.error('This language has already been added');
        return;
      }

      updateField('preferred_languages', [
        ...formData.preferred_languages,
        { language: languageInput.trim(), importance: languageImportance },
      ]);
      setLanguageInput('');
    }
  };

  // Helper to get language name from ID
  const getLanguageName = (languageId: string): string => {
    const lang = availableLanguages.find(l => l.id === languageId);
    return lang ? lang.name : languageId;
  };

  const removeLanguage = (index: number) => {
    updateField(
      'preferred_languages',
      formData.preferred_languages.filter((_, i) => i !== index)
    );
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Languages & Location Preferences
      </h2>

      {/* Preferred Country */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Preferred Cofounder Country *
        </label>
        <CountrySelection
          value={formData.preferred_country}
          onValueChange={(value) => updateField('preferred_country', value)}
          placeholder="Select preferred country"
        />
      </div>

      {/* Country Importance */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Country Match Importance *
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {importanceOptions.map((option) => (
            <label
              key={option.value}
              className="flex items-start gap-3 text-sm text-gray-700 dark:text-gray-300 cursor-pointer"
            >
              <input
                type="radio"
                name="country-importance"
                value={option.value}
                checked={formData.preferred_country_importance === option.value}
                onChange={() => updateField('preferred_country_importance', option.value)}
                className="mt-1 h-4 w-4 text-brand-600 focus:ring-brand-500"
              />
              <div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {option.title}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {option.description}
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Preferred Languages */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Working Languages * (At least one required)
        </label>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          Languages you prefer to work in with your cofounder
        </p>
        <div className="space-y-3 mb-3">
          <Select
            value={languageInput}
            onValueChange={setLanguageInput}
            disabled={isLoadingLanguages}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder={isLoadingLanguages ? "Loading languages..." : "Select a language"} />
            </SelectTrigger>
            <SelectContent>
              {availableLanguages.map((language) => (
                <SelectItem key={language.id} value={language.id}>
                  {language.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 flex-1">
              <input
                type="radio"
                checked={languageImportance === 'important'}
                onChange={() => setLanguageImportance('important')}
                className="w-4 h-4 text-brand-500 focus:ring-brand-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Nice to Have</span>
            </label>
            <label className="flex items-center gap-2 flex-1">
              <input
                type="radio"
                checked={languageImportance === 'non_negotiable'}
                onChange={() => setLanguageImportance('non_negotiable')}
                className="w-4 h-4 text-brand-500 focus:ring-brand-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Must Have</span>
            </label>
            <button
              type="button"
              onClick={addLanguage}
              disabled={!languageInput.trim() || isLoadingLanguages}
              className="px-4 py-2 bg-brand-500 dark:bg-brand-400 text-white rounded-lg hover:bg-brand-600 dark:hover:bg-brand-500 disabled:opacity-50 transition-all"
            >
              Add Language
            </button>
          </div>
        </div>
        <div className="space-y-2">
          {formData.preferred_languages.map((lang, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg"
            >
              <div>
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {getLanguageName(lang.language)}
                </span>
                <span className="ml-2 text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded">
                  {lang.importance === 'non_negotiable' ? 'Must Have' : 'Nice to Have'}
                </span>
              </div>
              <button
                type="button"
                onClick={() => removeLanguage(index)}
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
