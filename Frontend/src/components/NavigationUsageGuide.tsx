/**
 * Navigation Loading System Usage Guide
 * 
 * This file demonstrates how to use the new navigation loading system
 * to improve UX with loading states during page transitions.
 */

"use client";

import React from 'react';
import { useNavigationWithLoading } from '@/hooks/useNavigationWithLoading';
import { useNavigationLoading } from '@/context/NavigationLoadingContext';
import NavigationLink from '@/components/NavigationLink';

// Example 1: Using NavigationLink component (Recommended for most cases)
export const ExampleNavigationLinks = () => {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Using NavigationLink Component</h3>
      
      {/* Simple navigation link */}
      <NavigationLink 
        href="/team-workspace/projects" 
        className="inline-block px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
      >
        Go to Projects
      </NavigationLink>

      {/* Navigation link with custom onClick */}
      <NavigationLink 
        href="/team-workspace/profile" 
        className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        onClick={() => console.log('Navigating to profile...')}
      >
        Go to Profile
      </NavigationLink>
    </div>
  );
};

// Example 2: Using the navigation hook for programmatic navigation
export const ExampleProgrammaticNavigation = () => {
  const navigation = useNavigationWithLoading();

  const handleCreateProject = async () => {
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Navigate with loading state
      navigation.push('/team-workspace/projects/new-project-id');
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  };

  const handleGoBack = () => {
    navigation.back();
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Programmatic Navigation</h3>
      
      <button 
        onClick={handleCreateProject}
        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
      >
        Create Project & Navigate
      </button>

      <button 
        onClick={handleGoBack}
        className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
      >
        Go Back
      </button>
    </div>
  );
};

// Example 3: Manual loading state control
export const ExampleManualLoadingControl = () => {
  const { isLoading, startLoading, stopLoading } = useNavigationLoading();
  const navigation = useNavigationWithLoading();

  const handleComplexOperation = async () => {
    startLoading();
    
    try {
      // Simulate complex operation
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // Navigate without additional loading (already started)
      navigation.router.push('/team-workspace/dashboard');
    } catch (error) {
      console.error('Operation failed:', error);
      stopLoading(); // Stop loading on error
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Manual Loading Control</h3>
      
      <p className="text-sm text-gray-600">
        Current loading state: {isLoading ? 'Loading...' : 'Idle'}
      </p>

      <button 
        onClick={handleComplexOperation}
        disabled={isLoading}
        className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
      >
        {isLoading ? 'Processing...' : 'Start Complex Operation'}
      </button>
    </div>
  );
};

// Example 4: Form submission with navigation
export const ExampleFormWithNavigation = () => {
  const navigation = useNavigationWithLoading();
  const [formData, setFormData] = React.useState({ name: '', email: '' });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      // Simulate form submission
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Navigate to success page with loading
      navigation.push('/team-workspace/success');
    } catch (error) {
      console.error('Form submission failed:', error);
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Form with Navigation</h3>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          placeholder="Name"
          value={formData.name}
          onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        
        <input
          type="email"
          placeholder="Email"
          value={formData.email}
          onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        
        <button 
          type="submit"
          className="w-full px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
        >
          Submit & Continue
        </button>
      </form>
    </div>
  );
};

/**
 * USAGE INSTRUCTIONS:
 * 
 * 1. For simple navigation links, use <NavigationLink> component
 * 2. For programmatic navigation, use useNavigationWithLoading() hook
 * 3. For manual loading control, use useNavigationLoading() hook
 * 4. The loading overlay will automatically appear and disappear
 * 5. Loading state automatically stops when route changes
 * 6. 10-second timeout prevents infinite loading states
 * 
 * MIGRATION GUIDE:
 * 
 * Replace existing navigation patterns:
 * 
 * OLD:
 * import Link from 'next/link';
 * <Link href="/path">Text</Link>
 * 
 * NEW:
 * import NavigationLink from '@/components/NavigationLink';
 * <NavigationLink href="/path">Text</NavigationLink>
 * 
 * OLD:
 * import { useRouter } from 'next/navigation';
 * const router = useRouter();
 * router.push('/path');
 * 
 * NEW:
 * import { useNavigationWithLoading } from '@/hooks/useNavigationWithLoading';
 * const navigation = useNavigationWithLoading();
 * navigation.push('/path');
 */

export default function NavigationUsageGuide() {
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
          Navigation Loading System
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-300">
          Improved UX with loading states during page transitions
        </p>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg">
          <ExampleNavigationLinks />
        </div>

        <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg">
          <ExampleProgrammaticNavigation />
        </div>

        <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg">
          <ExampleManualLoadingControl />
        </div>

        <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg">
          <ExampleFormWithNavigation />
        </div>
      </div>
    </div>
  );
}
