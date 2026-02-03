"use client";
import React, { useState, useEffect } from "react";
import { useModal } from "../../hooks/useModal";
import Button from "../ui/button/Button";
import { useAuth } from "@/hooks/useAuth";

interface UserFormData {
  full_name: string;
  email: string;
  phone?: string;
  bio?: string;
  location?: string;
  website?: string;
}

export default function UserInfoCard() {
  const { openModal } = useModal();
  const { user, isLoading } = useAuth();
  const [setFormData] = useState<UserFormData>({
    full_name: '',
    email: '',
    phone: '',
    bio: '',
    location: '',
    website: ''
  });

  // Initialize form data when user data is available
  useEffect(() => {
    if (user) {
      setFormData({
        full_name: user.full_name || '',
        email: user.email || '',
        phone: user.phone || '',
        bio: user.bio || '',
        location: user.location || '',
        website: user.website || ''
      });
    }
  }, [user]);




  const getFirstName = () => {
    return user?.full_name?.split(' ')[0] || 'User';
  };

  const getLastName = () => {
    const nameParts = user?.full_name?.split(' ') || [];
    return nameParts.length > 1 ? nameParts.slice(1).join(' ') : '';
  };

  if (isLoading) {
    return (
      <div className="p-5 border border-gray-200 rounded-2xl dark:border-gray-800 lg:p-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex-1">
            <div className="h-6 bg-gray-200 rounded animate-pulse w-48 mb-6"></div>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-7">
              {[...Array(6)].map((_, i) => (
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
      <div className="p-5 border border-gray-200 rounded-2xl dark:border-gray-800 lg:p-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex-1">
            <h4 className="text-lg font-semibold text-gray-800 dark:text-white/90 mb-6">
              Personal Information
            </h4>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-7 2xl:gap-x-32">
              <div>
                <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                  First Name
                </p>
                <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                  {getFirstName()}
                </p>
              </div>

              <div>
                <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                  Last Name
                </p>
                <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                  {getLastName() || 'Not provided'}
                </p>
              </div>

            

    
            </div>
          </div>

          <Button
          disabled
            onClick={openModal}
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
            Edit
          </Button>
        </div>
      </div>

  );
}
