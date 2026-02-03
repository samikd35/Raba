'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Rocket, UserPlus, Search, MessageCircle, CheckCircle } from 'lucide-react';
import Link from 'next/link';

interface WelcomePanelProps {
  onDismiss: () => void;
}

export default function WelcomePanel({ onDismiss }: WelcomePanelProps) {
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    {
      icon: <UserPlus className="w-8 h-8" />,
      title: 'Create Your Profile',
      description: 'Tell us about your background, skills, and what you\'re looking for in a cofounder.',
      action: 'Start Profile',
      link: '/workspace/cofounder-matching',
    },
    {
      icon: <CheckCircle className="w-8 h-8" />,
      title: 'Get Approved',
      description: 'Our team will review your profile to ensure quality matches for everyone.',
      action: 'View Dashboard',
      link: '/workspace/cofounder-matching/dashboard',
    },
    {
      icon: <Search className="w-8 h-8" />,
      title: 'Browse Profiles',
      description: 'Discover potential cofounders who match your criteria and vision.',
      action: 'Browse Now',
      link: '/workspace/cofounder-matching/browse',
    },
    {
      icon: <MessageCircle className="w-8 h-8" />,
      title: 'Connect & Build',
      description: 'Reach out to matches, start conversations, and build your dream team.',
      action: 'Get Started',
      link: '/workspace/cofounder-matching',
    },
  ];

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onDismiss();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="bg-gradient-to-r from-brand-500 to-brand-600 dark:from-brand-600 dark:to-brand-700 rounded-lg p-6 mb-8 relative overflow-hidden"
    >
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -mr-32 -mt-32"></div>
      <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full -ml-24 -mb-24"></div>

      {/* Close button */}
      <button
        onClick={onDismiss}
        className="absolute top-4 right-4 p-1 text-white/80 hover:text-white hover:bg-white/10 rounded transition-colors"
      >
        <X className="w-5 h-5" />
      </button>

      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 bg-white/10 rounded-lg">
            <Rocket className="w-8 h-8 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Welcome to Cofounder Matching!</h2>
            <p className="text-white/90 text-sm">Find the perfect partner to build your startup</p>
          </div>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {steps.map((step, index) => (
            <div
              key={index}
              className={`p-4 rounded-lg transition-all cursor-pointer ${
                currentStep === index
                  ? 'bg-white text-brand-600 dark:text-brand-700 shadow-lg scale-105'
                  : 'bg-white/10 text-white hover:bg-white/20'
              }`}
              onClick={() => setCurrentStep(index)}
            >
              <div className="flex flex-col items-center text-center">
                <div className="mb-2">{step.icon}</div>
                <h3 className="font-semibold text-sm mb-1">{step.title}</h3>
                <p className={`text-xs ${currentStep === index ? 'text-gray-600 dark:text-gray-700' : 'text-white/80'}`}>
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Progress Dots */}
        <div className="flex items-center justify-center gap-2 mb-4">
          {steps.map((_, index) => (
            <div
              key={index}
              className={`h-2 rounded-full transition-all ${
                index === currentStep ? 'w-8 bg-white' : 'w-2 bg-white/40'
              }`}
            />
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 0}
            className="px-4 py-2 text-white/80 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>

          <div className="flex gap-2">
            <button
              onClick={onDismiss}
              className="px-4 py-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            >
              Skip Tour
            </button>
            {currentStep === steps.length - 1 ? (
              <Link
                href={steps[currentStep].link}
                className="px-6 py-2 bg-white text-brand-600 dark:text-brand-700 rounded-lg hover:bg-white/90 transition-colors font-medium"
                onClick={onDismiss}
              >
                {steps[currentStep].action}
              </Link>
            ) : (
              <button
                onClick={handleNext}
                className="px-6 py-2 bg-white text-brand-600 dark:text-brand-700 rounded-lg hover:bg-white/90 transition-colors font-medium"
              >
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
