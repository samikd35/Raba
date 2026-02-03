"use client";
import React, { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useModal } from "../../hooks/useModal";
import { Modal } from "../ui/modal";
import Input from "../form/input/InputField";
import Label from "../form/Label";
import Button from "@/components/ui/button/Button";
import { authService } from "@/services/authService";
import { useAuthStore } from "@/stores/authStore";
import toast from "react-hot-toast";

interface PasswordFormData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

interface SecuritySettings {
  twoFactorEnabled: boolean;
  lastPasswordChange: string;
  activeSessions: number;
  loginNotifications: boolean;
}

export default function UserAddressCard() {
  const { openModal, closeModal } = useModal();
  const [isOpen, setIsOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const router = useRouter();
  
  // Use new auth system
  const { user, isLoading } = useAuthStore();
  
  const [passwordForm, setPasswordForm] = useState<PasswordFormData>({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Partial<PasswordFormData>>({});
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  });

  // Memoized validation function
  const validatePasswordForm = useCallback((): boolean => {
    const newErrors: Partial<PasswordFormData> = {};

    if (!passwordForm.currentPassword) {
      newErrors.currentPassword = 'Current password is required';
    }

    if (!passwordForm.newPassword) {
      newErrors.newPassword = 'New password is required';
    } else if (passwordForm.newPassword.length < 8) {
      newErrors.newPassword = 'Password must be at least 8 characters long';
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(passwordForm.newPassword)) {
      newErrors.newPassword = 'Password must contain at least one uppercase letter, one lowercase letter, and one number';
    }

    if (!passwordForm.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your new password';
    } else if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [passwordForm]);

  // Memoized password change handler
  const handlePasswordChange = useCallback((field: keyof PasswordFormData, value: string) => {
    setPasswordForm(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  }, [errors]);

  // Updated password update function using authService
  const handlePasswordUpdate = useCallback(async () => {
    if (!validatePasswordForm()) return;

    setIsSubmitting(true);
    try {
      // Use new authService for password change - only takes newPassword
      await authService.changePassword(passwordForm.newPassword);
      
      // Reset form
      setPasswordForm({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
      
      closeModal();
      toast.success('Password updated successfully!');
    } catch (error: any) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Password update failed:', error);
      }
      
      // Enhanced error handling
      let errorMessage = 'Failed to update password';
      if (error?.message) {
        errorMessage = error.message;
      } else if (error?.response?.status === 401) {
        errorMessage = 'Current password is incorrect';
      } else if (error?.response?.status === 422) {
        errorMessage = 'Password does not meet requirements';
      }
      
      setErrors({ currentPassword: errorMessage });
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  }, [passwordForm, validatePasswordForm, closeModal]);

  // Memoized close dropdown function
  const closeDropdown = useCallback(() => {
    setIsOpen(false);
  }, []);

  // Updated logout function using authService
  const handleLogout = useCallback(async () => {
    try {
      setIsLoggingOut(true);
      await authService.logout();
      closeDropdown();
      router.push('/');
      toast.success('Logged out successfully');
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Logout error:', error);
      }
      toast.error('Failed to log out. Please try again.');
    } finally {
      setIsLoggingOut(false);
    }
  }, [router, closeDropdown]);

  // Memoized password strength function
  const getPasswordStrength = useCallback((password: string) => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[^a-zA-Z\d]/.test(password)) strength++;
    
    if (strength <= 2) return { label: 'Weak', color: 'bg-red-500' };
    if (strength <= 3) return { label: 'Fair', color: 'bg-yellow-500' };
    if (strength <= 4) return { label: 'Good', color: 'bg-blue-500' };
    return { label: 'Strong', color: 'bg-green-500' };
  }, []);

  if (isLoading) {
    return (
      <div className="p-5 border border-gray-200 rounded-2xl dark:border-gray-800 lg:p-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex-1">
            <div className="h-6 bg-gray-200 rounded animate-pulse w-32 mb-6"></div>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-7">
              {[...Array(4)].map((_, i) => (
                <div key={i}>
                  <div className="h-3 bg-gray-200 rounded animate-pulse w-20 mb-2"></div>
                  <div className="h-4 bg-gray-200 rounded animate-pulse w-32"></div>
                </div>
              ))}
            </div>
          </div>
          <div className="h-10 bg-gray-200 rounded animate-pulse w-20"></div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="p-5 border border-gray-200 rounded-2xl dark:border-gray-800 lg:p-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex-1">
            <h4 className="text-lg font-semibold text-gray-800 dark:text-white/90 mb-6">
              Security Settings
            </h4>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-7 2xl:gap-x-32">
              <div>
                <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                  Password
                </p>
                <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                  ••••••••••••
                </p>
                
              </div>

           
            </div>

            {/* Quick Actions */}
            <button
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="flex items-center gap-3 px-3 py-2 mt-3 font-medium text-red-600 rounded-lg group text-theme-sm hover:bg-gray-100 hover:text-red-700 dark:text-red-400 dark:hover:bg-white/5 dark:hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
        >
          {isLoggingOut ? (
            <>
              <div className="w-6 h-6 flex items-center justify-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-500"></div>
              </div>
              Signing out...
            </>
          ) : (
            <>
              <svg
                className="fill-red-500 group-hover:fill-red-700 dark:group-hover:fill-red-300"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M15.1007 19.247C14.6865 19.247 14.3507 18.9112 14.3507 18.497L14.3507 14.245H12.8507V18.497C12.8507 19.7396 13.8581 20.747 15.1007 20.747H18.5007C19.7434 20.747 20.7507 19.7396 20.7507 18.497L20.7507 5.49609C20.7507 4.25345 19.7433 3.24609 18.5007 3.24609H15.1007C13.8581 3.24609 12.8507 4.25345 12.8507 5.49609V9.74501L14.3507 9.74501V5.49609C14.3507 5.08188 14.6865 4.74609 15.1007 4.74609L18.5007 4.74609C18.9149 4.74609 19.2507 5.08188 19.2507 5.49609L19.2507 18.497C19.2507 18.9112 18.9149 19.247 18.5007 19.247H15.1007ZM3.25073 11.9984C3.25073 12.2144 3.34204 12.4091 3.48817 12.546L8.09483 17.1556C8.38763 17.4485 8.86251 17.4487 9.15549 17.1559C9.44848 16.8631 9.44863 16.3882 9.15583 16.0952L5.81116 12.7484L16.0007 12.7484C16.4149 12.7484 16.7507 12.4127 16.7507 11.9984C16.7507 11.5842 16.4149 11.2484 16.0007 11.2484L5.81528 11.2484L9.15585 7.90554C9.44864 7.61255 9.44847 7.13767 9.15547 6.84488C8.86248 6.55209 8.3876 6.55226 8.09481 6.84525L3.52309 11.4202C3.35673 11.5577 3.25073 11.7657 3.25073 11.9984Z"
                  fill=""
                />
              </svg>
              Sign out
            </>
          )}
        </button>
          </div>

          <Button
            onClick={openModal}
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Change Password
          </Button>
        </div>
      </div>

      {/* Change Password Modal */}
      <Modal isOpen={isOpen} onClose={closeModal} className="max-w-lg m-4">
        <div className="relative w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-xl dark:bg-gray-900">
          {/* Header */}
          <div className="border-b border-gray-200 bg-gray-50 px-6 py-5 dark:border-gray-800 dark:bg-gray-800/50">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Change Password
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Update your account password
                </p>
              </div>
              <button
                onClick={closeModal}
                className="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-500 dark:hover:bg-gray-700"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Form Content */}
          <div className="px-6 py-6">
            <form className="space-y-6" onSubmit={(e) => { e.preventDefault(); handlePasswordUpdate(); }}>
              <div>
                <Label htmlFor="currentPassword">
                  Current Password <span className="text-red-500">*</span>
                </Label>
                <div className="relative">
                  <Input
                    id="currentPassword"
                    type={showPasswords.current ? "text" : "password"}
                    value={passwordForm.currentPassword}
                    onChange={(e) => handlePasswordChange('currentPassword', e.target.value)}
                    placeholder="Enter your current password"
                    className={errors.currentPassword ? 'border-red-300 focus:border-red-500' : ''}
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    onClick={() => setShowPasswords(prev => ({ ...prev, current: !prev.current }))}
                  >
                    <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      {showPasswords.current ? (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                      ) : (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      )}
                    </svg>
                  </button>
                </div>
                {errors.currentPassword && (
                  <p className="mt-1 text-sm text-red-600">{errors.currentPassword}</p>
                )}
              </div>

              <div>
                <Label htmlFor="newPassword">
                  New Password <span className="text-red-500">*</span>
                </Label>
                <div className="relative">
                  <Input
                    id="newPassword"
                    type={showPasswords.new ? "text" : "password"}
                    value={passwordForm.newPassword}
                    onChange={(e) => handlePasswordChange('newPassword', e.target.value)}
                    placeholder="Enter your new password"
                    className={errors.newPassword ? 'border-red-300 focus:border-red-500' : ''}
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    onClick={() => setShowPasswords(prev => ({ ...prev, new: !prev.new }))}
                  >
                    <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      {showPasswords.new ? (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                      ) : (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      )}
                    </svg>
                  </button>
                </div>
                {passwordForm.newPassword && (
                  <div className="mt-2">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full transition-all ${getPasswordStrength(passwordForm.newPassword).color}`}
                          style={{ width: `${(getPasswordStrength(passwordForm.newPassword).label === 'Weak' ? 25 : getPasswordStrength(passwordForm.newPassword).label === 'Fair' ? 50 : getPasswordStrength(passwordForm.newPassword).label === 'Good' ? 75 : 100)}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-gray-500">
                        {getPasswordStrength(passwordForm.newPassword).label}
                      </span>
                    </div>
                  </div>
                )}
                {errors.newPassword && (
                  <p className="mt-1 text-sm text-red-600">{errors.newPassword}</p>
                )}
              </div>

              <div>
                <Label htmlFor="confirmPassword">
                  Confirm New Password <span className="text-red-500">*</span>
                </Label>
                <div className="relative">
                  <Input
                    id="confirmPassword"
                    type={showPasswords.confirm ? "text" : "password"}
                    value={passwordForm.confirmPassword}
                    onChange={(e) => handlePasswordChange('confirmPassword', e.target.value)}
                    placeholder="Confirm your new password"
                    className={errors.confirmPassword ? 'border-red-300 focus:border-red-500' : ''}
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    onClick={() => setShowPasswords(prev => ({ ...prev, confirm: !prev.confirm }))}
                  >
                    <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      {showPasswords.confirm ? (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                      ) : (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      )}
                    </svg>
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="mt-1 text-sm text-red-600">{errors.confirmPassword}</p>
                )}
              </div>

              {/* Password Requirements */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Password Requirements:
                </h4>
                <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                  <li className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${passwordForm.newPassword.length >= 8 ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                    At least 8 characters long
                  </li>
                  <li className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${/[A-Z]/.test(passwordForm.newPassword) ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                    One uppercase letter
                  </li>
                  <li className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${/[a-z]/.test(passwordForm.newPassword) ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                    One lowercase letter
                  </li>
                  <li className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${/\d/.test(passwordForm.newPassword) ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                    One number
                  </li>
                </ul>
              </div>
            </form>
          </div>

          {/* Footer */}
          <div className="border-t border-gray-200 bg-gray-50 px-6 py-4 dark:border-gray-800 dark:bg-gray-800/50">
            <div className="flex justify-end space-x-3">
              <Button
                type="button"
                variant="outline"
                onClick={closeModal}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handlePasswordUpdate}
                disabled={isSubmitting || !passwordForm.currentPassword || !passwordForm.newPassword || !passwordForm.confirmPassword}
                className="bg-brand-600 hover:bg-brand-700 text-white"
              >
                {isSubmitting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Updating...
                  </>
                ) : (
                  'Update Password'
                )}
              </Button>
            </div>
          </div>
        </div>
      </Modal>
    </>
  );
}
