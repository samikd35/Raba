"use client";
import React, { useState, useEffect, useCallback, useRef } from "react";
import { useUser, useIsLoading, useIsAuthenticated, useIsInitialized, useInitializeAuth } from '@/stores/authStore';
import { authService } from '@/services/authService';
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import Button from "@/components/ui/button/Button";
import { EyeIcon, EyeCloseIcon } from "@/icons";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";

interface ProfileFormData {
  full_name: string;
  bio: string;
  website: string;
  location: string;
  timezone: string;
}

interface PasswordChangeData {
  new_password: string;
  confirm_password: string;
}

interface PasswordValidation {
  isValid: boolean;
}

const isValidUrl = (url: string): boolean => {
  if (!url) return true;
  try {
    new URL(url);
    return url.startsWith('http://') || url.startsWith('https://');
  } catch {
    return false;
  }
};

export default function Profile() {
  const router = useRouter();
  
  // Enhanced Zustand authentication
  const user = useUser();
  const isAuthLoading = useIsLoading();
  const isAuthenticated = useIsAuthenticated();
  const isInitialized = useIsInitialized();
  const initializeAuth = useInitializeAuth();
  
  // Local state
  const [isEditing, setIsEditing] = useState(false);
  const [isProfileLoading, setIsProfileLoading] = useState(false);
  const [isPasswordLoading, setIsPasswordLoading] = useState(false);
  const [showPasswordSection, setShowPasswordSection] = useState(false);
  
  // Form states
  const [formData, setFormData] = useState<ProfileFormData>({
    full_name: '',
    bio: '',
    website: '',
    location: '',
    timezone: '',
  });
  const [passwordData, setPasswordData] = useState<PasswordChangeData>({
    new_password: '',
    confirm_password: '',
  });
  const [passwordValidation, setPasswordValidation] = useState<PasswordValidation>({
    isValid: true,
  });
  
  // Password visibility states
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Abort controller reference for password change
  const passwordAbortControllerRef = useRef<AbortController | null>(null);

  // Initialize authentication on component mount
  useEffect(() => {
    const init = async () => {
      try {
        console.log('Profile: Initializing auth...');
        await initializeAuth();
        console.log('Profile: Auth initialized');
      } catch (error) {
        console.error('Profile: Auth initialization failed:', error);
      }
    }
    
    if (!isInitialized) {
      init();
    }
  }, [initializeAuth, isInitialized]);

  // Redirect to signin if not authenticated after initialization
  useEffect(() => {
    if (isInitialized && !isAuthLoading && !isAuthenticated) {
      console.log('Profile: User not authenticated, redirecting to signin');
      router.push('/signin');
    }
  }, [isInitialized, isAuthLoading, isAuthenticated, router]);

  // Initialize form data when user loads
  useEffect(() => {
    if (user) {
      setFormData({
        full_name: user.full_name || '',
        bio: user.bio || '',
        website: user.website || '',
        location: user.location || '',
        timezone: user.timezone || 'Africa/Nairobi', // Default to Nairobi if empty
      });
    }
  }, [user]);

  // Handle profile form changes
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  }, []);

  // Handle password form changes
  const handlePasswordChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    
    // Password validation
    let sanitizedValue = value;
    
    // Remove spaces and limit length
    sanitizedValue = value.replace(/\s/g, '').slice(0, 128);
    
    setPasswordData(prev => ({
      ...prev,
      [name]: sanitizedValue
    }));
  }, []);

  // Validate password fields when password data changes
  useEffect(() => {
    const isValid = passwordData.new_password && 
                   passwordData.confirm_password && 
                   passwordData.new_password === passwordData.confirm_password && 
                   passwordData.new_password.length >= 8;
    setPasswordValidation({ isValid });
  }, [passwordData]);

  // Save profile changes
  const handleSaveProfile = useCallback(async () => {
    if (!user?.id) {
      toast.error('User ID not found');
      return;
    }

    // Validate form data
    if (!formData.full_name.trim()) {
      toast.error('Full name is required');
      return;
    }


    if (formData.website && !isValidUrl(formData.website)) {
      toast.error('Please enter a valid website URL');
      return;
    }

    try {
      setIsProfileLoading(true);

      // Only send changed fields
      const changedFields: Partial<ProfileFormData> = {};
      Object.keys(formData).forEach(key => {
        const typedKey = key as keyof ProfileFormData;
        if (formData[typedKey] !== user[typedKey]) {
          changedFields[typedKey] = formData[typedKey] as any;
        }
      });

      if (Object.keys(changedFields).length === 0) {
        toast.success('No changes to save');
        setIsEditing(false);
        return;
      }

      console.log('Profile: Updating profile with changes:', changedFields);
      await authService.updateProfile(user.id, changedFields);
      
      toast.success('Profile updated successfully!');
      setIsEditing(false);
    } catch (error: any) {
      console.error('Profile: Update error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to update profile';
      toast.error(errorMessage);
    } finally {
      setIsProfileLoading(false);
    }
  }, [user, formData]);

  // Change password
  const handleChangePassword = useCallback(async () => {
    // Prevent multiple simultaneous operations
    if (isPasswordLoading) {
      return;
    }

    if (!passwordValidation.isValid) {
      toast.error('Please fill in all required fields');
      return;
    }

    // Create new abort controller for this operation
    const abortController = new AbortController();
    passwordAbortControllerRef.current = abortController;

    try {
      setIsPasswordLoading(true);

      if (process.env.NODE_ENV === 'development') {
        console.log('Profile: Changing password...');
      }
      
      await authService.changePassword(passwordData.new_password);
      
      // Check if operation was aborted
      if (abortController.signal.aborted) {
        return;
      }
      
      toast.success('Password changed successfully!');
      setPasswordData({
        new_password: '',
        confirm_password: '',
      });
      setShowPasswordSection(false);
    } catch (error: any) {
      if (error.name === 'AbortError') {
        return; // Operation was cancelled
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error('Profile: Password change error:', error);
      }
      const errorMessage = error instanceof Error ? error.message : 'Failed to change password';
      toast.error(errorMessage);
    } finally {
      setIsPasswordLoading(false);
      // Clear the abort controller reference
      if (passwordAbortControllerRef.current === abortController) {
        passwordAbortControllerRef.current = null;
      }
    }
  }, [passwordData, passwordValidation, isPasswordLoading]);

  // Cancel editing
  const handleCancelEdit = useCallback(() => {
    if (user) {
      setFormData({
        full_name: user.full_name || '',
        bio: user.bio || '',
        website: user.website || '',
        location: user.location || '',
        timezone: user.timezone || 'Africa/Nairobi',
      });
    }
    setIsEditing(false);
  }, [user]);

  // Loading state for authentication initialization
  if (!isInitialized || isAuthLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500 mx-auto mb-4"></div>
          <p className="text-gray-500">Initializing authentication...</p>
        </div>
      </div>
    );
  }

  // Loading state for user data
  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto p-4">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-brand-500 dark:text-white ">
          Profile Settings
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Manage your account information and preferences
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Profile Information Card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Personal Information
            </h2>
            {!isEditing ? (
              <Button
                onClick={() => setIsEditing(true)}
                variant="outline"
                size="sm"
              >
                Edit Profile
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button
                  onClick={handleCancelEdit}
                  variant="ghost"
                  size="sm"
                  disabled={isProfileLoading}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSaveProfile}
                  size="sm"
                  disabled={isProfileLoading}
                >
                  {isProfileLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Saving...
                    </>
                  ) : (
                    "Save Changes"
                  )}
                </Button>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Full Name */}
            <div className="col-span-2">
              <Label htmlFor="full_name">
                Full Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="full_name"
                name="full_name"
                value={formData.full_name}
                onChange={handleInputChange}
                disabled={!isEditing || isProfileLoading}
                placeholder={formData.full_name ? formData.full_name : "Enter your full name"}
                required
              />
            </div>

          

            {/* Location */}
            <div>
              <Label htmlFor="location">Location</Label>
              <Input
                id="location"
                name="location"
                value={formData.location}
                onChange={handleInputChange}
                disabled={!isEditing || isProfileLoading}
                placeholder={formData.location ? formData.location : "Enter your location"}
              />
            </div>

            {/* Website */}
            <div>
              <Label htmlFor="website">Website</Label>
              <Input
                id="website"
                name="website"
                type="url"
                value={formData.website}
                onChange={handleInputChange}
                disabled={!isEditing || isProfileLoading}
                placeholder={formData.website ? formData.website : "https://yourwebsite.com"}
                className={!isValidUrl(formData.website || '') ? 'border-red-500' : ''}
              />
              {formData.website && !isValidUrl(formData.website) && (
                <p className="text-sm text-red-500 mt-1">Please enter a valid URL</p>
              )}
            </div>
          </div>

          {/* Bio */}
          <div className="mt-6">
            <Label htmlFor="bio">Bio</Label>
            <textarea
              id="bio"
              name="bio"
              value={formData.bio}
              onChange={handleInputChange}
              disabled={!isEditing || isProfileLoading}
              placeholder={formData.bio ? formData.bio : "Tell us about yourself..."}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent dark:bg-gray-700 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            />
          </div>

          {/* Timezone */}
          <div className="mt-6">
            <Label htmlFor="timezone">Timezone</Label>
            <select
              id="timezone"
              name="timezone"
              value={formData.timezone}
              onChange={handleInputChange}
              disabled={!isEditing || isProfileLoading}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent dark:bg-gray-700 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            >
              <option value="Africa/Nairobi">Africa/Nairobi (EAT)</option>
              <option value="America/New_York">America/New_York (EST/EDT)</option>
              <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</option>
              <option value="Europe/London">Europe/London (GMT/BST)</option>
              <option value="Europe/Paris">Europe/Paris (CET/CEST)</option>
              <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
              <option value="Asia/Shanghai">Asia/Shanghai (CST)</option>
              <option value="Australia/Sydney">Australia/Sydney (AEST/AEDT)</option>
            </select>
          </div>
        </div>

        {/* Account Security Card */}
        <div className="bg-red-50/40 dark:bg-gray-800 rounded-xl border border-red-200 dark:border-gray-700 p-6 ">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Account Security
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Update your password to keep your account secure
              </p>
            </div>
            <Button
              onClick={() => setShowPasswordSection(!showPasswordSection)}
              variant="outline"
              size="sm"
              disabled={isPasswordLoading}
            >
              {showPasswordSection ? "Cancel" : "Change Password"}
            </Button>
          </div>

          {showPasswordSection && (
            <div className="space-y-4 border-t pt-4">
              {/* New Password */}
              <div>
                <Label htmlFor="new_password">
                  New Password <span className="text-red-500">*</span>
                </Label>
                <div className="relative">
                  <Input
                    id="new_password"
                    name="new_password"
                    type={showNewPassword ? "text" : "password"}
                    value={passwordData.new_password}
                    onChange={handlePasswordChange}
                    disabled={isPasswordLoading}
                    placeholder="Enter new password (min 8 characters)"
                    minLength={8}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    disabled={isPasswordLoading}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                  >
                    {showNewPassword ? <EyeCloseIcon /> : <EyeIcon />}
                  </button>
                </div>
                {passwordData.new_password && passwordData.new_password.length < 8 && (
                  <p className="text-sm text-red-500 mt-1">Password must be at least 8 characters</p>
                )}
              </div>

              {/* Confirm Password */}
              <div>
                <Label htmlFor="confirm_password">
                  Confirm New Password <span className="text-red-500">*</span>
                </Label>
                <div className="relative">
                  <Input
                    id="confirm_password"
                    name="confirm_password"
                    type={showConfirmPassword ? "text" : "password"}
                    value={passwordData.confirm_password}
                    onChange={handlePasswordChange}
                    disabled={isPasswordLoading}
                    placeholder="Confirm new password"
                    minLength={8}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    disabled={isPasswordLoading}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                  >
                    {showConfirmPassword ? <EyeCloseIcon /> : <EyeIcon />}
                  </button>
                </div>
                {passwordData.confirm_password && passwordData.new_password !== passwordData.confirm_password && (
                  <p className="text-sm text-red-500 mt-1">Passwords do not match</p>
                )}
              </div>

              <div className="flex justify-end">
                <Button
                  onClick={handleChangePassword}
                  disabled={isPasswordLoading || !passwordValidation.isValid}
                  className="min-w-[120px]"
                >
                  {isPasswordLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Updating...
                    </>
                  ) : (
                    "Update Password"
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}