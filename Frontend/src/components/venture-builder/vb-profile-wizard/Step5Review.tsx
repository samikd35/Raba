'use client';

import React, { useState, useEffect } from 'react';
import { Check, Mail, FileText, Briefcase, Star, ArrowLeft, Loader2, CheckCircle, User, Quote, Linkedin, ExternalLink } from 'lucide-react';
import { VBProfileFormData } from './VBProfileWizard';
import { createVBProfile, fetchExpertiseAreas } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';

interface Step5ReviewProps {
  formData: VBProfileFormData;
  profilePictureFile: File | null;
  onBack: () => void;
  onSuccess: () => void;
  invitationToken?: string;
}

export default function Step5Review({ formData, profilePictureFile, onBack, onSuccess, invitationToken }: Step5ReviewProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [expertiseAreas, setExpertiseAreas] = useState<any[]>([]);
  const [profilePicturePreview, setProfilePicturePreview] = useState<string | null>(null);

  // Create preview URL from uploaded file
  useEffect(() => {
    if (profilePictureFile) {
      const previewUrl = URL.createObjectURL(profilePictureFile);
      setProfilePicturePreview(previewUrl);
      return () => URL.revokeObjectURL(previewUrl);
    } else {
      setProfilePicturePreview(null);
    }
  }, [profilePictureFile]);

  // Fetch expertise areas to get names for main_expertise fallback
  useEffect(() => {
    const loadExpertiseAreas = async () => {
      try {
        const data = await fetchExpertiseAreas();
        setExpertiseAreas(data);
      } catch (error) {
        console.error('Error fetching expertise areas:', error);
      }
    };
    loadExpertiseAreas();
  }, []);

  const handleSubmit = async () => {
    try {
      setIsSubmitting(true);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required. Please sign in again.');
      }

      if (!invitationToken) {
        throw new Error('Invitation token is required. Please use the link from your invitation email.');
      }

      // Derive main_expertise from the first selected expertise area if not set
      let mainExpertise = formData.mainExpertise;
      if (!mainExpertise && formData.expertiseIds.length > 0) {
        const firstExpertiseId = formData.expertiseIds[0];
        const firstExpertiseArea = expertiseAreas.find((area) => area.id === firstExpertiseId);
        mainExpertise = firstExpertiseArea?.name || 'Venture Building';
      }

      // Fallback if still empty
      if (!mainExpertise) {
        mainExpertise = 'Venture Building';
      }

      const payload = {
        name: formData.name,
        contact_email: formData.contactEmail,
        main_expertise: mainExpertise,
        short_intro: formData.shortIntro,
        biography: formData.biography,
        linkedin_url: formData.linkedinUrl || undefined,
        work_experience: formData.workExperience,
        expertise_ids: formData.expertiseIds,
      };

      await createVBProfile(payload, profilePictureFile, token, invitationToken);
      setIsComplete(true);
      toast.success('Profile created successfully!');

      setTimeout(() => {
        onSuccess();
      }, 2000);
    } catch (error: any) {
      console.error('Error creating profile:', error);
      toast.error(error.message || 'Failed to create profile');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isComplete) {
    return (
      <div className="space-y-8 py-8">
        <div className="flex flex-col items-center justify-center text-center">
          <div className="w-24 h-24 rounded-full bg-success-100 dark:bg-success-900/30 flex items-center justify-center mb-6 animate-bounce">
            <CheckCircle className="w-12 h-12 text-success-600 dark:text-success-400" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
            Profile Created Successfully!
          </h3>
          <p className="text-gray-600 dark:text-gray-400 max-w-md">
            Your venture builder profile has been submitted for admin review. You'll be notified once it's approved.
          </p>
        </div>

        <div className="p-5 bg-blue-light-50 dark:bg-blue-light-900/20 border border-blue-light-200 dark:border-blue-light-700 rounded-xl">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-light-100 dark:bg-blue-light-800/40 flex items-center justify-center flex-shrink-0">
              <FileText className="w-4 h-4 text-blue-light-600 dark:text-blue-light-400" />
            </div>
            <div>
              <p className="text-sm font-semibold text-blue-light-800 dark:text-blue-light-300 mb-1">
                Next Steps
              </p>
              <p className="text-sm text-blue-light-700 dark:text-blue-light-400">
                Our admin team will review your profile and set up your pricing and calendar. This typically takes 1-2 business days.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Section Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Review Your Profile
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Please review all information before submitting
        </p>
      </div>

      {/* Profile Card Preview */}
      <div className="p-6 bg-gradient-to-br from-brand-50 to-white dark:from-brand-900/20 dark:to-gray-800 border border-brand-200 dark:border-brand-800 rounded-xl shadow-sm">
        <div className="flex items-start gap-5 mb-5">
          {/* Profile Image or Placeholder */}
          <div className="w-20 h-20 rounded-xl overflow-hidden border-2 border-brand-200 dark:border-brand-700 flex-shrink-0 bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
            {(profilePicturePreview || formData.profilePictureUrl) ? (
              <img
                src={profilePicturePreview || formData.profilePictureUrl}
                alt="Profile"
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                }}
              />
            ) : (
              <User className="w-10 h-10 text-gray-400" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
              {formData.name || 'Your Name'}
            </h4>
            <div className="flex items-center gap-2 text-sm text-brand-600 dark:text-brand-400 font-medium mb-2">
              <Mail className="w-4 h-4" />
              {formData.contactEmail}
            </div>
            {formData.linkedinUrl && (
              <a
                href={formData.linkedinUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-blue-light-600 dark:text-blue-light-400 hover:underline"
              >
                <Linkedin className="w-4 h-4" />
                LinkedIn Profile
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>

        {/* Short Intro */}
        {formData.shortIntro && (
          <div className="p-4 bg-white/60 dark:bg-gray-800/60 rounded-lg mb-4 border border-brand-100 dark:border-brand-800">
            <div className="flex items-start gap-2">
              <Quote className="w-4 h-4 text-brand-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-gray-700 dark:text-gray-300 italic">
                "{formData.shortIntro}"
              </p>
            </div>
          </div>
        )}

        {/* Biography */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-brand-500 dark:text-brand-400" />
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">Biography</p>
          </div>
          <div className="p-4 bg-white dark:bg-gray-800/80 rounded-lg border border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
              {formData.biography || 'No biography provided'}
            </p>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
            {formData.biography.length} characters
          </p>
        </div>
      </div>

      {/* Work Experience Section */}
      <div className="p-5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
            <Briefcase className="w-5 h-5 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 dark:text-white">Work Experience</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{formData.workExperience.length} entries</p>
          </div>
        </div>
        <div className="space-y-3">
          {formData.workExperience.map((exp, index) => (
            <div key={index} className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gray-200 dark:bg-gray-600 flex items-center justify-center flex-shrink-0">
                  <Briefcase className="w-4 h-4 text-gray-600 dark:text-gray-300" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-gray-900 dark:text-white">{exp.position}</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{exp.organization}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5">{exp.years}</p>
                  {exp.description && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 line-clamp-2">{exp.description}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Expertise Section */}
      <div className="p-5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
            <Star className="w-5 h-5 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 dark:text-white">Expertise Areas</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {formData.expertiseIds.length} area{formData.expertiseIds.length > 1 ? 's' : ''} selected
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-success-500" />
          <p className="text-sm text-success-700 dark:text-success-400 font-medium">
            {formData.expertiseIds.length} expertise area{formData.expertiseIds.length > 1 ? 's' : ''} selected
          </p>
        </div>
      </div>

      {/* Important Notice */}
      <div className="p-5 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-700 rounded-xl">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-warning-100 dark:bg-warning-800/40 flex items-center justify-center flex-shrink-0">
            <FileText className="w-4 h-4 text-warning-600 dark:text-warning-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-warning-800 dark:text-warning-300 mb-1">
              Important Notice
            </p>
            <p className="text-sm text-warning-700 dark:text-warning-400">
              Your profile will be submitted for admin review. Pricing and calendar setup will be configured by our team after approval.
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Buttons */}
      <div className="flex gap-4 pt-4">
        <button
          onClick={onBack}
          disabled={isSubmitting}
          className="flex-1 py-3.5 px-6 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
        >
          <ArrowLeft className="w-5 h-5" />
          Back
        </button>
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className={`flex-1 py-3.5 px-6 rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-gray-800 ${
            isSubmitting
              ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
              : 'bg-success-600 hover:bg-success-700 text-white shadow-md hover:shadow-lg focus:ring-success-500'
          }`}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Submitting...
            </>
          ) : (
            <>
              <Check className="w-5 h-5" />
              Submit Profile
            </>
          )}
        </button>
      </div>
    </div>
  );
}
