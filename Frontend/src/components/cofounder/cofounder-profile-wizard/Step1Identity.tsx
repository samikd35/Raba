'use client';

import React, { useState, useRef } from 'react';
import { X, Upload, Image as ImageIcon } from 'lucide-react';
import { toast } from 'react-hot-toast';
import type { ProfileFormData, EmploymentEntry, Gender } from '@/types/cofounder';
import Image from 'next/image';
import { CountrySelection } from '@/components/CountrySelection';
import { DatePicker } from '@/components/ui/date-picker';

interface StepProps {
  formData: ProfileFormData;
  updateField: <K extends keyof ProfileFormData>(
    field: K,
    value: ProfileFormData[K]
  ) => void;
  setProfilePictureFile: (file: File | null) => void;
}

export default function Step1Identity({ formData, updateField, setProfilePictureFile }: StepProps) {
  const [newEducation, setNewEducation] = useState('');
  const [employmentForm, setEmploymentForm] = useState<EmploymentEntry>({
    organization: '',
    role: '',
    start_date: '',
    end_date: null,
    is_current: false,
    responsibilities: '',
  });
  const [uploadedImagePreview, setUploadedImagePreview] = useState<string | null>(null);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const eighteenYearsAgo = React.useMemo(() => {
    const date = new Date();
    date.setFullYear(date.getFullYear() - 18);
    return date;
  }, []);
  const dobDefaultMonth = React.useMemo(() => {
    const date = new Date();
    date.setFullYear(date.getFullYear() - 25);
    return date;
  }, []);
  const employmentYearStart = 1980;
  const employmentYearEnd = React.useMemo(() => {
    const date = new Date();
    return date.getFullYear() + 5;
  }, []);

  // Initialize profile picture preview when editing existing profile
  React.useEffect(() => {
    if (formData.profile_picture_url &&
        !formData.profile_picture_url.includes('dummy') &&
        !uploadedImagePreview?.startsWith('blob:')) {
      setUploadedImagePreview(formData.profile_picture_url);
    }
  }, [formData.profile_picture_url, uploadedImagePreview]);

  const addEducation = () => {
    if (newEducation.trim()) {
      updateField('education', [...formData.education, newEducation.trim()]);
      setNewEducation('');
    }
  };

  const removeEducation = (index: number) => {
    updateField(
      'education',
      formData.education.filter((_, i) => i !== index)
    );
  };

  const addEmployment = () => {
    if (employmentForm.organization && employmentForm.role && employmentForm.responsibilities) {
      updateField('employment_history', {
        entries: [...formData.employment_history.entries, employmentForm],
      });
      setEmploymentForm({
        organization: '',
        role: '',
        start_date: '',
        end_date: null,
        is_current: false,
        responsibilities: '',
      });
    }
  };

  const removeEmployment = (index: number) => {
    updateField('employment_history', {
      entries: formData.employment_history.entries.filter((_, i) => i !== index),
    });
  };

  const charCount = employmentForm.responsibilities.length;
  const isCharCountValid = charCount >= 280 && charCount <= 600;

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

    // Store the file object for later upload in the wizard parent
    setProfilePictureFile(file);

    // Create a local preview URL for showing in the UI
    const previewUrl = URL.createObjectURL(file);
    setUploadedImagePreview(previewUrl);

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
  updateField('profile_picture_url', '');

  // Reset the file input element
  if (fileInputRef.current) {
    fileInputRef.current.value = '';
  }
};


  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Personal Identity
      </h2>

      {/* Basic Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            First Name *
          </label>
          <input
            type="text"
            value={formData.first_name}
            onChange={(e) => updateField('first_name', e.target.value)}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
            placeholder="Enter your first name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Last Name *
          </label>
          <input
            type="text"
            value={formData.last_name}
            onChange={(e) => updateField('last_name', e.target.value)}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
            placeholder="Enter your last name"
          />
        </div>
      </div>

      {/* Gender and DOB */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Gender *
          </label>
          <select
            value={formData.gender}
            onChange={(e) => updateField('gender', e.target.value as Gender)}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
          >
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Prefer not to say">Prefer not to say</option>
          </select>
        </div>

        <DatePicker
          label="Date of Birth * (Must be 18+)"
          value={formData.date_of_birth || null}
          onChange={(val) => updateField('date_of_birth', val || '')}
          placeholder="Select date of birth"
          mode="date"
          fromYear={1924}
          toYear={eighteenYearsAgo.getFullYear()}
          maxDate={eighteenYearsAgo}
          defaultMonth={dobDefaultMonth}
          helperText="Select your birthday (must be at least 18 years old)"
          allowClear
        />
      </div>

      {/* Email and Country */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Email *
          </label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => updateField('email', e.target.value)}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
            placeholder="your@email.com"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Country of Residence *
          </label>
          <CountrySelection
            value={formData.country}
            onValueChange={(value) => updateField('country', value)}
            placeholder="Select your country"
          />
        </div>
      </div>

      {/* Profile Picture Upload */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Upload Profile Picture *
        </label>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          Upload an image file (max 5MB, JPG, PNG, GIF, WebP, or BMP)
        </p>

        <div className="flex items-start gap-4">
          {/* Preview or Placeholder */}
          <div className="relative">
            {(uploadedImagePreview || (formData.profile_picture_url && !formData.profile_picture_url.includes('dummy'))) ? (
              <div className="relative w-32 h-32 rounded-lg overflow-hidden border-2 border-gray-300 dark:border-gray-600">
                <Image
                  src={uploadedImagePreview || formData.profile_picture_url}
                  alt="Profile preview"
                  fill
                  className="object-cover"
                  unoptimized={uploadedImagePreview ? true : false}
                />
                {!isUploadingImage && (
                  <button
                    type="button"
                    onClick={handleRemoveImage}
                    className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ) : (
              <div className="w-32 h-32 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 flex items-center justify-center bg-gray-50 dark:bg-gray-700/50">
                <ImageIcon className="w-12 h-12 text-gray-400 dark:text-gray-500" />
              </div>
            )}
            {isUploadingImage && (
              <div className="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center">
                <svg className="animate-spin h-8 w-8 text-white" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
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
              id="profile-picture-upload"
            />
            <label
              htmlFor="profile-picture-upload"
              className={`inline-flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors cursor-pointer ${
                isUploadingImage ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              <Upload className="w-4 h-4" />
              {uploadedImagePreview || formData.profile_picture_url
                ? 'Change Photo'
                : 'Upload Photo'}
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              Recommended: Square image, at least 400x400px
            </p>
          </div>
        </div>
      </div>

      {/* LinkedIn and Website */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            LinkedIn URL *
          </label>
          <input
            type="url"
            value={formData.linkedin_url}
            onChange={(e) => updateField('linkedin_url', e.target.value)}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
            placeholder="https://linkedin.com/in/username"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Website (Optional)
          </label>
          <input
            type="url"
            value={formData.website_url}
            onChange={(e) => updateField('website_url', e.target.value)}
            className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
            placeholder="https://yourwebsite.com"
          />
        </div>
      </div>

      {/* Education */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Education * (At least one entry required)
        </label>
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={newEducation}
            onChange={(e) => setNewEducation(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addEducation()}
            className="flex-1 px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
            placeholder="e.g., BSc Computer Science - MIT - 2020"
          />
          <button
            type="button"
            onClick={addEducation}
            className="px-4 py-2 bg-brand-500 dark:bg-brand-400 text-white rounded-lg hover:bg-brand-600 dark:hover:bg-brand-500 transition-all"
          >
            Add
          </button>
        </div>
        <div className="space-y-2">
          {formData.education.map((edu, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
            >
              <span className="text-sm text-gray-700 dark:text-gray-300">{edu}</span>
              <button
                type="button"
                onClick={() => removeEducation(index)}
                className="text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Employment History */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Employment History * (At least one entry required)
        </label>
        <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg space-y-3 mb-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              type="text"
              value={employmentForm.organization}
              onChange={(e) =>
                setEmploymentForm({ ...employmentForm, organization: e.target.value })
              }
              className="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
              placeholder="Organization"
            />
            <input
              type="text"
              value={employmentForm.role}
              onChange={(e) =>
                setEmploymentForm({ ...employmentForm, role: e.target.value })
              }
              className="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
              placeholder="Role"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <DatePicker
              label="Start Date"
              value={employmentForm.start_date || null}
              onChange={(value) =>
                setEmploymentForm({
                  ...employmentForm,
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
              value={employmentForm.end_date}
              onChange={(value) =>
                setEmploymentForm({
                  ...employmentForm,
                  end_date: value,
                })
              }
              placeholder="Select end date"
              mode="month"
              fromYear={employmentYearStart}
              toYear={employmentYearEnd}
              disabled={employmentForm.is_current}
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={employmentForm.is_current}
                onChange={(e) =>
                  setEmploymentForm({
                    ...employmentForm,
                    is_current: e.target.checked,
                    end_date: e.target.checked ? null : employmentForm.end_date,
                  })
                }
                className="w-4 h-4 text-brand-500 focus:ring-brand-500"
              />
              <span className="text-gray-700 dark:text-gray-300">Current Role</span>
            </label>
          </div>
          <div>
            <textarea
              value={employmentForm.responsibilities}
              onChange={(e) =>
                setEmploymentForm({ ...employmentForm, responsibilities: e.target.value })
              }
              rows={4}
              className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
              placeholder="Key responsibilities (280-600 characters)"
            />
            <div
              className={`text-xs mt-1 ${
                isCharCountValid
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              {charCount}/600 characters {charCount < 280 && `(minimum 280)`}
            </div>
          </div>
          <button
            type="button"
            onClick={addEmployment}
            disabled={!isCharCountValid || !employmentForm.organization || !employmentForm.role}
            className="w-full px-4 py-2 bg-brand-500 dark:bg-brand-400 text-white rounded hover:bg-brand-600 dark:hover:bg-brand-500 disabled:opacity-50 transition-all text-sm"
          >
            Add Employment Entry
          </button>
        </div>
        <div className="space-y-2">
          {formData.employment_history.entries.map((entry, index) => (
            <div
              key={index}
              className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">
                    {entry.role} at {entry.organization}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {entry.start_date} - {entry.is_current ? 'Present' : entry.end_date}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeEmployment(index)}
                  className="text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300">{entry.responsibilities}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Achievement */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Notable Achievement *
        </label>
        <textarea
          value={formData.achievement}
          onChange={(e) => updateField('achievement', e.target.value)}
          rows={3}
          className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
          placeholder="I designed the first pay-as-you-go solar-powered irrigation system for remote farmers in Eastern Ethiopia."
        />
      </div>

      {/* Personal Statement */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Personal Statement * (2-4 sentences recommended)
        </label>
        <textarea
          value={formData.personal_statement}
          onChange={(e) => updateField('personal_statement', e.target.value)}
          rows={4}
          className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
          placeholder="5+ years of engineering experience at DPO Group (focused on high-scale payment infrastructure). Six years as CTO of two family-oriented startups (one successful exit, one failed). Deeply committed to building AI-driven solutions that help build scalable healthcare systems for Africans. I'm a hands-on engineer and can wear several other hats as may be needed."
        />
      </div>
    </div>
  );
}
