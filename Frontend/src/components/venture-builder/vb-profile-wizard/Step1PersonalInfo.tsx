'use client';

import React, { useState, useRef } from 'react';
import { Mail, User, Upload, ArrowRight, X, Image as ImageIcon, Linkedin, FileText, Quote } from 'lucide-react';
import { toast } from 'react-hot-toast';
import Image from 'next/image';
import { VBProfileFormData } from './VBProfileWizard';

interface Step1PersonalInfoProps {
  formData: VBProfileFormData;
  updateFormData: (data: Partial<VBProfileFormData>) => void;
  onNext: () => void;
  setProfilePictureFile: (file: File | null) => void;
  lockEmail?: boolean;
}

export default function Step1PersonalInfo({ formData, updateFormData, onNext, setProfilePictureFile, lockEmail }: Step1PersonalInfoProps) {
  const [errors, setErrors] = useState<{ name?: string; contactEmail?: string; shortIntro?: string; biography?: string; profilePicture?: string }>({});
  const [uploadedImagePreview, setUploadedImagePreview] = useState<string | null>(null);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Allowed image extensions based on backend spec
    const allowedExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'];
    const fileName = file.name.toLowerCase();
    const fileExtension = fileName.substring(fileName.lastIndexOf('.'));

    // Validate extension
    if (!allowedExtensions.includes(fileExtension)) {
      toast.error(
        `Invalid file type. Allowed formats: ${allowedExtensions.join(', ')}`
      );
      return;
    }

    // Validate MIME type (extra safety)
    if (!file.type.startsWith('image/')) {
      toast.error('Please upload an image file');
      return;
    }

    // Validate file size (max 5MB)
    const maxSizeBytes = 5 * 1024 * 1024; // 5 MB
    if (file.size > maxSizeBytes) {
      toast.error('Image size must be less than 5MB');
      return;
    }

    try {
      setIsUploadingImage(true);

      // Store the file object for later upload
      setProfilePictureFile(file);

      // Create a local preview URL for showing in the UI
      const previewUrl = URL.createObjectURL(file);
      setUploadedImagePreview(previewUrl);

      // Clear any profile picture error
      if (errors.profilePicture) {
        setErrors({ ...errors, profilePicture: undefined });
      }

      toast.success('Image uploaded successfully');
    } catch (error) {
      console.error('Failed to process image:', error);
      toast.error('Failed to process image. Please try again.');
    } finally {
      setIsUploadingImage(false);
    }
  };

  const handleRemoveImage = () => {
    // Revoke the preview URL if it's a blob URL (local upload)
    if (uploadedImagePreview?.startsWith('blob:')) {
      URL.revokeObjectURL(uploadedImagePreview);
    }

    // Clear local preview + file
    setUploadedImagePreview(null);
    setProfilePictureFile(null);

    // Clear the profile picture URL from formData
    updateFormData({ profilePictureUrl: '' });

    // Reset the file input element
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleNext = () => {
    const newErrors: { name?: string; contactEmail?: string; shortIntro?: string; biography?: string; profilePicture?: string } = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Full name is required';
    } else if (formData.name.trim().length < 2) {
      newErrors.name = 'Name must be at least 2 characters';
    }

    if (!formData.contactEmail.trim()) {
      newErrors.contactEmail = 'Contact email is required';
    } else if (!validateEmail(formData.contactEmail)) {
      newErrors.contactEmail = 'Please enter a valid email address';
    }

    // Profile picture is required
    if (!uploadedImagePreview && !formData.profilePictureUrl) {
      newErrors.profilePicture = 'Profile picture is required';
    }

    if (!formData.shortIntro.trim()) {
      newErrors.shortIntro = 'Short introduction is required';
    } else if (formData.shortIntro.trim().length < 20) {
      newErrors.shortIntro = 'Introduction must be at least 20 characters';
    }

    if (!formData.biography.trim()) {
      newErrors.biography = 'Biography is required';
    } else if (formData.biography.trim().length < 100) {
      newErrors.biography = 'Biography must be at least 100 characters';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    onNext();
  };

  return (
    <div className="space-y-8">
      {/* Section Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Personal Information
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Let's start with your basic contact information and introduction
        </p>
      </div>

      {/* Basic Info Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Full Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Full Name <span className="text-error-500">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <User className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => {
                updateFormData({ name: e.target.value });
                if (errors.name) {
                  setErrors({ ...errors, name: undefined });
                }
              }}
              placeholder="John Doe"
              className={`w-full pl-10 pr-4 py-3 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all ${
                errors.name
                  ? 'border-error-500 dark:border-error-500'
                  : 'border-gray-300 dark:border-gray-600'
              }`}
            />
          </div>
          {errors.name && (
            <p className="text-sm text-error-600 dark:text-error-400 mt-1">{errors.name}</p>
          )}
        </div>

        {/* Contact Email */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Contact Email <span className="text-error-500">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Mail className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="email"
              value={formData.contactEmail}
              onChange={(e) => {
                if (lockEmail) return; // Don't allow changes if email is locked
                updateFormData({ contactEmail: e.target.value });
                if (errors.contactEmail) {
                  setErrors({ ...errors, contactEmail: undefined });
                }
              }}
              placeholder="your.email@example.com"
              disabled={lockEmail}
              readOnly={lockEmail}
              className={`w-full pl-10 pr-4 py-3 border rounded-lg text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all ${
                lockEmail
                  ? 'bg-gray-100 dark:bg-gray-800 cursor-not-allowed'
                  : 'bg-white dark:bg-gray-700'
              } ${
                errors.contactEmail
                  ? 'border-error-500 dark:border-error-500'
                  : 'border-gray-300 dark:border-gray-600'
              }`}
            />
          </div>
          {lockEmail && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              This email is linked to your invitation
            </p>
          )}
          {errors.contactEmail && (
            <p className="text-sm text-error-600 dark:text-error-400 mt-1">{errors.contactEmail}</p>
          )}
        </div>
      </div>

      {/* LinkedIn URL (Optional) */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          LinkedIn URL (Optional)
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Linkedin className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="url"
            value={formData.linkedinUrl}
            onChange={(e) => updateFormData({ linkedinUrl: e.target.value })}
            placeholder="https://linkedin.com/in/yourprofile"
            className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
          />
        </div>
      </div>

      {/* Profile Picture */}
      <div className={`p-5 bg-gray-50 dark:bg-gray-700/30 rounded-xl border ${errors.profilePicture ? 'border-error-500 dark:border-error-500' : 'border-gray-200 dark:border-gray-600'}`}>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Profile Picture <span className="text-error-500">*</span>
        </label>
        <div className="flex items-start gap-5">
          {/* Preview or Placeholder */}
          <div className="relative flex-shrink-0">
            {uploadedImagePreview ? (
              <div className="relative w-28 h-28 rounded-xl overflow-hidden border-2 border-brand-200 dark:border-brand-700 shadow-md">
                <Image
                  src={uploadedImagePreview}
                  alt="Profile preview"
                  fill
                  className="object-cover"
                  unoptimized={true}
                />
                {!isUploadingImage && (
                  <button
                    type="button"
                    onClick={handleRemoveImage}
                    className="absolute top-1 right-1 p-1.5 bg-error-500 text-white rounded-full hover:bg-error-600 transition-colors shadow-md"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ) : (
              <div className="w-28 h-28 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-500 flex items-center justify-center bg-white dark:bg-gray-800">
                <ImageIcon className="w-10 h-10 text-gray-400 dark:text-gray-500" />
              </div>
            )}
            {isUploadingImage && (
              <div className="absolute inset-0 bg-black/50 rounded-xl flex items-center justify-center">
                <svg className="animate-spin h-8 w-8 text-white" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </div>
            )}
          </div>

          {/* Upload Button */}
          <div className="flex-1">
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.gif,.webp,.bmp"
              onChange={handleImageUpload}
              className="hidden"
              id="vb-profile-picture-upload"
            />
            <label
              htmlFor="vb-profile-picture-upload"
              className={`inline-flex items-center gap-2 px-5 py-2.5 border border-brand-300 dark:border-brand-600 rounded-lg text-sm font-medium text-brand-700 dark:text-brand-300 bg-brand-50 dark:bg-brand-900/20 hover:bg-brand-100 dark:hover:bg-brand-900/40 transition-colors cursor-pointer ${
                isUploadingImage ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              <Upload className="w-4 h-4" />
              {uploadedImagePreview ? 'Change Photo' : 'Upload Photo'}
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              Recommended: Square image, at least 400x400px
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Max 5MB • JPG, PNG, GIF, WebP, or BMP
            </p>
          </div>
        </div>
        {errors.profilePicture && (
          <p className="text-sm text-error-600 dark:text-error-400 mt-3">{errors.profilePicture}</p>
        )}
      </div>

      {/* Short Introduction */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          <div className="flex items-center gap-2">
            <Quote className="w-4 h-4 text-brand-500" />
            Short Introduction <span className="text-error-500">*</span>
          </div>
        </label>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          A brief tagline that describes your expertise (shown on your profile card)
        </p>
        <input
          type="text"
          value={formData.shortIntro}
          onChange={(e) => {
            updateFormData({ shortIntro: e.target.value });
            if (errors.shortIntro) {
              setErrors({ ...errors, shortIntro: undefined });
            }
          }}
          placeholder="e.g., Serial entrepreneur with 15+ years in fintech and AI"
          maxLength={150}
          className={`w-full px-4 py-3 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all ${
            errors.shortIntro
              ? 'border-error-500 dark:border-error-500'
              : 'border-gray-300 dark:border-gray-600'
          }`}
        />
        <div className="flex justify-between mt-1">
          {errors.shortIntro ? (
            <p className="text-sm text-error-600 dark:text-error-400">{errors.shortIntro}</p>
          ) : (
            <span />
          )}
          <span className={`text-xs ${formData.shortIntro.length >= 20 ? 'text-success-600 dark:text-success-400' : 'text-gray-400'}`}>
            {formData.shortIntro.length}/150
          </span>
        </div>
      </div>

      {/* Biography */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-brand-500" />
            Full Biography <span className="text-error-500">*</span>
          </div>
        </label>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          Tell founders about your background, experience, and what you can help them with
        </p>
        <textarea
          value={formData.biography}
          onChange={(e) => {
            updateFormData({ biography: e.target.value });
            if (errors.biography) {
              setErrors({ ...errors, biography: undefined });
            }
          }}
          rows={5}
          placeholder="Share your professional journey, areas of expertise, notable achievements, and how you can help startup founders succeed..."
          maxLength={2000}
          className={`w-full px-4 py-3 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all resize-none ${
            errors.biography
              ? 'border-error-500 dark:border-error-500'
              : 'border-gray-300 dark:border-gray-600'
          }`}
        />
        <div className="flex justify-between mt-1">
          {errors.biography ? (
            <p className="text-sm text-error-600 dark:text-error-400">{errors.biography}</p>
          ) : (
            <span className="text-xs text-gray-400">Minimum 100 characters</span>
          )}
          <span className={`text-xs ${formData.biography.length >= 100 ? 'text-success-600 dark:text-success-400' : 'text-gray-400'}`}>
            {formData.biography.length}/2000
          </span>
        </div>
      </div>

      {/* Continue Button */}
      <button
        onClick={handleNext}
        className="w-full py-3.5 px-6 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
      >
        Continue
        <ArrowRight className="w-5 h-5" />
      </button>
    </div>
  );
}
