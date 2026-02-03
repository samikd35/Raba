'use client';

import React, { useState } from 'react';
import { FileText, Linkedin, ArrowRight, ArrowLeft, Sparkles, Target } from 'lucide-react';
import { VBProfileFormData } from './VBProfileWizard';

interface Step2ProfessionalProps {
  formData: VBProfileFormData;
  updateFormData: (data: Partial<VBProfileFormData>) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function Step2Professional({ formData, updateFormData, onNext, onBack }: Step2ProfessionalProps) {
  const [errors, setErrors] = useState<{
    mainExpertise?: string;
    shortIntro?: string;
    biography?: string
  }>({});

  const handleNext = () => {
    const newErrors: {
      mainExpertise?: string;
      shortIntro?: string;
      biography?: string
    } = {};

    if (!formData.mainExpertise.trim()) {
      newErrors.mainExpertise = 'Main expertise is required';
    } else if (formData.mainExpertise.length < 5) {
      newErrors.mainExpertise = 'Main expertise must be at least 5 characters';
    } else if (formData.mainExpertise.length > 100) {
      newErrors.mainExpertise = 'Main expertise must not exceed 100 characters';
    }

    if (!formData.shortIntro.trim()) {
      newErrors.shortIntro = 'Short introduction is required';
    } else if (formData.shortIntro.length < 10) {
      newErrors.shortIntro = 'Short intro must be at least 10 characters';
    } else if (formData.shortIntro.length > 200) {
      newErrors.shortIntro = 'Short intro must not exceed 200 characters';
    }

    if (!formData.biography.trim()) {
      newErrors.biography = 'Biography is required';
    } else if (formData.biography.length < 50) {
      newErrors.biography = 'Biography must be at least 50 characters';
    } else if (formData.biography.length > 2000) {
      newErrors.biography = 'Biography must not exceed 2000 characters';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    onNext();
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
          Professional Background
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Tell us about your expertise and professional journey
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4" />
              Main Expertise <span className="text-red-500">*</span>
            </div>
          </label>
          <input
            type="text"
            value={formData.mainExpertise}
            onChange={(e) => {
              updateFormData({ mainExpertise: e.target.value });
              if (errors.mainExpertise) {
                setErrors({ ...errors, mainExpertise: undefined });
              }
            }}
            placeholder="e.g., Product Strategy and Go-to-Market"
            className={`w-full px-4 py-3 border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 ${
              errors.mainExpertise
                ? 'border-red-500 dark:border-red-500'
                : 'border-gray-200 dark:border-gray-700'
            }`}
          />
          <div className="flex items-center justify-between mt-1">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Your primary area of expertise (5-100 characters)
            </p>
            <p className={`text-xs ${
              formData.mainExpertise.length > 100
                ? 'text-red-500 dark:text-red-400'
                : 'text-gray-500 dark:text-gray-400'
            }`}>
              {formData.mainExpertise.length}/100
            </p>
          </div>
          {errors.mainExpertise && (
            <p className="text-sm text-red-500 dark:text-red-400 mt-1">{errors.mainExpertise}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Short Introduction <span className="text-red-500">*</span>
            </div>
          </label>
          <input
            type="text"
            value={formData.shortIntro}
            onChange={(e) => {
              updateFormData({ shortIntro: e.target.value });
              if (errors.shortIntro) {
                setErrors({ ...errors, shortIntro: undefined });
              }
            }}
            placeholder="e.g., 15+ years building successful startups"
            className={`w-full px-4 py-3 border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 ${
              errors.shortIntro
                ? 'border-red-500 dark:border-red-500'
                : 'border-gray-200 dark:border-gray-700'
            }`}
          />
          <div className="flex items-center justify-between mt-1">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              A catchy tagline about your experience (10-200 characters)
            </p>
            <p className={`text-xs ${
              formData.shortIntro.length > 200
                ? 'text-red-500 dark:text-red-400'
                : 'text-gray-500 dark:text-gray-400'
            }`}>
              {formData.shortIntro.length}/200
            </p>
          </div>
          {errors.shortIntro && (
            <p className="text-sm text-red-500 dark:text-red-400 mt-1">{errors.shortIntro}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Full Biography <span className="text-red-500">*</span>
            </div>
          </label>
          <textarea
            value={formData.biography}
            onChange={(e) => {
              updateFormData({ biography: e.target.value });
              if (errors.biography) {
                setErrors({ ...errors, biography: undefined });
              }
            }}
            rows={8}
            placeholder="Share your background, expertise, and what makes you a great venture builder..."
            className={`w-full px-4 py-3 border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 ${
              errors.biography
                ? 'border-red-500 dark:border-red-500'
                : 'border-gray-200 dark:border-gray-700'
            }`}
          />
          <div className="flex items-center justify-between mt-1">
            <p className={`text-xs ${
              formData.biography.length < 50
                ? 'text-red-500 dark:text-red-400'
                : formData.biography.length > 2000
                ? 'text-red-500 dark:text-red-400'
                : 'text-gray-500 dark:text-gray-400'
            }`}>
              {formData.biography.length} / 2000 characters (minimum 50)
            </p>
          </div>
          {errors.biography && (
            <p className="text-sm text-red-500 dark:text-red-400 mt-1">{errors.biography}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            <div className="flex items-center gap-2">
              <Linkedin className="w-4 h-4" />
              LinkedIn Profile URL (Optional)
            </div>
          </label>
          <input
            type="url"
            value={formData.linkedinUrl}
            onChange={(e) => updateFormData({ linkedinUrl: e.target.value })}
            placeholder="https://linkedin.com/in/your-profile"
            className="w-full px-4 py-3 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Help clients learn more about your professional background
          </p>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="flex-1 py-3 px-6 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 hover:bg-gray-200 dark:hover:bg-gray-700"
        >
          <ArrowLeft className="w-5 h-5" />
          Back
        </button>
        <button
          onClick={handleNext}
          className="flex-1 py-3 px-6 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 shadow-md hover:shadow-lg"
        >
          Continue
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
