"use client"

import React, { useState } from 'react';
import Link from 'next/link';
import VentureBuilderInterestModal from '@/components/venture-builders/VentureBuilderInterestModal';
import { MentorOrbit } from '@/components/venture-builders/MentorOrbit';

// Module data for How It Works section
const modules = [
  {
    id: 1,
    title: "Problem Discovery",
    description: "Discovery and explore problems worth solving for. Refine your ideas. Understand the contextual reality surrounding.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="14" cy="14" r="10" stroke="currentColor" strokeWidth="2"/>
        <path d="M22 22L28 28" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    id: 2,
    title: "Value Proposition Design",
    description: "Translate real customer pains into a clear value proposition. Map jobs, pains, and gains to what you will deliver.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 4L20 12L28 14L22 20L24 28L16 24L8 28L10 20L4 14L12 12L16 4Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
      </svg>
    ),
  },
  {
    id: 3,
    title: "MVP & Business Model Development",
    description: "Productize your market research findings by design compelling MVPs & Market adaptive business models.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="4" y="8" width="24" height="16" rx="2" stroke="currentColor" strokeWidth="2"/>
        <path d="M12 14L14 16L20 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
  {
    id: 4,
    title: "Market Validation",
    description: "Validate desirability, feasibility, and viability with real evidence. Decide: iterate, pivot, or scale with confidence",
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 16L12 22L26 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
];

// Module Card Component
const ModuleCard = ({ module, index }: { module: typeof modules[0]; index: number }) => {
  return (
    <div className="group relative h-full">
      <div 
        className="
          relative h-full p-4 md:p-6 lg:pl-8 rounded-3xl
          bg-gradient-to-br from-gray-900/50 to-gray-900/70 
          backdrop-blur-xl
          border border-white/10
          shadow-[0_4px_24px_0_rgba(0,0,0,0.4)]
          transition-all duration-300 ease-out
          hover:border-white/20
          hover:shadow-[0_8px_32px_0_rgba(36,70,148,0.15)]
          overflow-hidden
        "
      >
        {/* Subtle inner gradient */}
        <div 
          className="absolute inset-0 bg-gradient-to-br from-white/[0.05] to-transparent pointer-events-none"
          aria-hidden="true"
        />

        <div className="relative z-10">
          {/* Module badge */}
          <div className="mb-6">
            <span className="inline-block px-4 py-2 rounded-full bg-brand-500 text-white text-sm font-semibold">
              Module {module.id}
            </span>
          </div>

          {/* Title */}
          <h3 className="text-2xl md:text-3xl font-bold text-white mb-4 leading-tight">
            {module.title}
          </h3>

          {/* Description */}
          <p className="text-base md:text-lg text-gray-400 leading-relaxed mb-6">
            {module.description}
          </p>

          {/* Learn more CTA */}
          <a 
            href="/solutions"
            className="inline-block text-sm text-white underline hover:text-gray-300 transition-colors duration-200"
          >
            Learn more →
          </a>
        </div>
      </div>
    </div>
  );
};

// Main FounderWorks Component
const FounderWorks = () => {
  const [isVentureBuilderModalOpen, setIsVentureBuilderModalOpen] = useState(false);

  return (
    <div className="relative">
      {/* Section 1: How It Works */}
      <section 
        id="how-it-works"
        className="relative pt-8 md:pt-16 lg:pt-20 overflow-hidden bg-[#100F1F]"
        aria-labelledby="how-it-works-heading"
      >
        {/* Dark smooth gradient background */}
        <div 
          className="absolute inset-0 bg-[#100F1F]"
          aria-hidden="true"
        />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-6">
          {/* Section Header */}
          <div className="text-center mb-8 md:mb-12">
            <span className="inline-block text-xs font-medium uppercase tracking-wider text-gray-400 mb-3">
              HOW IT WORKS
            </span>
            <h2 
              id="how-it-works-heading"
              className="text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-tight mb-4"
            >
              From <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-blue-light-400">Problem Discovery</span> to <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-blue-light-400">Market Validation</span>: The Founder's Journey
            </h2>
            <p className="text-base text-gray-500 max-w-xl mx-auto">
              A Guided approach to the complex founder's journey.
            </p>
          </div>

          {/* Module Cards Grid - 2x2 Layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 max-w-6xl mx-auto">
            {modules.map((module, index) => (
              <ModuleCard key={module.id} module={module} index={index} />
            ))}
          </div>
        </div>
      </section>

      {/* Section 2: Access to Vetted Venture Builders */}
      <section 
        id="venture-builders"
        className="relative pt-4 md:pt-4 pb-16 md:pb-24 lg:pb-32 overflow-hidden bg-[#100F1F]"
        aria-labelledby="venture-builders-heading"
      >
        {/* Dark background */}
        <div 
          className="absolute inset-0"
          aria-hidden="true"
        />
        
        {/* Subtle dot pattern */}
        <div 
          className="absolute inset-0 "
          aria-hidden="true"
        />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 md:gap-16 lg:gap-20 items-center">
            {/* Text Content */}
            <div className="max-w-xl mx-auto lg:mx-0 text-center lg:text-left order-2 lg:order-1">
              <h2 
                id="venture-builders-heading"
                className="text-xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white tracking-tight mb-6"
              >
                Access to Vetted{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-blue-light-400">
                  Venture Builders
                </span>
              </h2>
              <p className="text-base md:text-lg text-gray-400 leading-relaxed mb-6">
                Connect with world-class Venture Builders who are, themselves, current and ex-founders, whose experiences and insights will only catalyze your entrepreneurial journey.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 items-center lg:items-start">
                <button
                  onClick={() => setIsVentureBuilderModalOpen(true)}
                  className="inline-flex items-center text-brand-400 hover:text-brand-300 font-medium text-lg md:text-xl transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:ring-offset-2 focus:ring-offset-[#100F1F] rounded-md px-1 -mx-1"
                >
                  Join Our Growing Pool of Venture Builders
                  <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                </button>
                <Link
                  href="/vb"
                  className="text-sm text-gray-400 hover:text-white transition-colors duration-200 underline underline-offset-4"
                >
                  Learn more about our network →
                </Link>
              </div>
            </div>

            {/* Mentor Orbit Visual */}
            <div className="order-1 lg:order-2">
              <MentorOrbit />
            </div>
          </div>
        </div>
      </section>

      {/* Venture Builder Interest Modal */}
      <VentureBuilderInterestModal
        isOpen={isVentureBuilderModalOpen}
        onOpenChange={setIsVentureBuilderModalOpen}
      />
    </div>
  );
};

export default FounderWorks;
