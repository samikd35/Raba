"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { MentorOrbit, mentorImages } from '@/components/venture-builders/MentorOrbit';
import VentureBuilderInterestModal from '@/components/venture-builders/VentureBuilderInterestModal';
import { ventureBuilders } from '@/components/landing/data/ventureBuilders';
import { HeroHeader } from '@/components/header';
import Footer from '@/components/landing/Footer';

// How it works steps for Venture Builders
const howItWorksSteps = [
  {
    id: 1,
    title: "Apply & Get Vetted",
    description: "Submit your application through our expression of interest form. Our team reviews your experience, expertise, and alignment with founder needs.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 4V28M4 16H28" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    id: 2,
    title: "Join the Network",
    description: "Once accepted, you become part of our curated pool of venture builders. Access our platform and connect with high-potential founders.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="16" cy="10" r="6" stroke="currentColor" strokeWidth="2"/>
        <path d="M6 28C6 22.4772 10.4772 18 16 18C21.5228 18 26 22.4772 26 28" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    id: 3,
    title: "Support Founders",
    description: "Provide coaching, mentorship, and hands-on support to founders through their journey relevant with your domain expertise.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 4L20 12L28 14L22 20L24 28L16 24L8 28L10 20L4 14L12 12L16 4Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
      </svg>
    ),
  },
  {
    id: 4,
    title: "Grow Together",
    description: "Build lasting relationships, expand your network, and contribute to the success of Africa's next generation of entrepreneurs.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 24L12 16L18 22L28 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M20 8H28V16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
];

// Step Card Component
const StepCard = ({ step, index }: { step: typeof howItWorksSteps[0]; index: number }) => {
  return (
    <div className="group relative h-full">
      <div 
        className="
          relative h-full p-6 md:p-8 rounded-2xl
          bg-gradient-to-br from-gray-900/50 to-gray-900/70 
          backdrop-blur-xl
          border border-white/10
          shadow-[0_4px_24px_0_rgba(0,0,0,0.4)]
          transition-all duration-300 ease-out
          hover:border-brand-500/30
          hover:shadow-[0_8px_32px_0_rgba(36,70,148,0.2)]
          overflow-hidden
        "
      >
        {/* Subtle inner gradient */}
        <div 
          className="absolute inset-0 bg-gradient-to-br from-white/[0.03] to-transparent pointer-events-none"
          aria-hidden="true"
        />

        <div className="relative z-10">
          {/* Step number */}
          <div className="mb-5 flex items-center gap-4">
            <span className="flex items-center justify-center w-10 h-10 rounded-full bg-brand-500 text-white text-lg font-bold">
              {step.id}
            </span>
            <div className="text-brand-400">
              {step.icon}
            </div>
          </div>

          {/* Title */}
          <h3 className="text-xl md:text-2xl font-bold text-white mb-3 leading-tight">
            {step.title}
          </h3>

          {/* Description */}
          <p className="text-base text-gray-400 leading-relaxed">
            {step.description}
          </p>
        </div>
      </div>
    </div>
  );
};

// Featured Venture Builder Card
const VentureBuilderCard = ({ builder }: { builder: typeof ventureBuilders[0] }) => {
  return (
    <div 
      className="
        relative p-6 rounded-2xl
        bg-gradient-to-br from-gray-900/60 to-gray-900/80 
        backdrop-blur-xl
        border border-white/10
        hover:border-brand-500/30
        transition-all duration-300
      "
    >
      <div className="flex items-start gap-4">
        <div className="relative w-16 h-16 rounded-full overflow-hidden ring-2 ring-brand-500/50 flex-shrink-0">
          <Image
            src={builder.profileImage}
            alt={builder.fullName}
            fill
            className="object-cover"
          />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-lg font-semibold text-white truncate">{builder.fullName}</h4>
          <p className="text-sm text-brand-400 mb-2">{builder.domain}</p>
          <p className="text-sm text-gray-400 line-clamp-2">{builder.bio}</p>
        </div>
      </div>
    </div>
  );
};

// Main Venture Builders Page
export default function VentureBuilderPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Get 4 featured venture builders
  const featuredBuilders = ventureBuilders.slice(0, 4);

  return (
    <>
      <HeroHeader darkMode={true} />
      <div className="min-h-screen bg-[#100F1F]">
        {/* Hero Section */}
        <section className="relative pt-16 pb-8 md:pt-24 md:pb-8 overflow-hidden">
        {/* Background gradients */}
        <div 
          className="absolute inset-0 bg-gradient-to-b from-brand-500/5 via-transparent to-transparent"
          aria-hidden="true"
        />
        <div 
          className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-brand-500/10 rounded-full blur-[120px]"
          aria-hidden="true"
        />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            {/* Text Content */}
            <div className="text-center lg:text-left">
              <span className="inline-block text-xs font-medium uppercase tracking-wider text-brand-400 mb-4">
                Venture Builder Network
              </span>
              <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-6xl font-bold text-white tracking-tight mb-6">
                Access to Vetted{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-blue-light-400">
                  Venture Builders
                </span>
              </h1>
              <p className="text-lg md:text-xl text-gray-400 leading-relaxed mb-8 max-w-xl mx-auto lg:mx-0">
                Connect with world-class Venture Builders who are, themselves, current and ex-founders. 
                Their experiences and insights will catalyze your entrepreneurial journey.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
                <Link
                  href="/signin"
                  className="
                    inline-flex items-center justify-center px-8 py-4 
                    rounded-xl bg-brand-500 hover:bg-brand-600 
                    text-white font-semibold text-lg
                    transition-all duration-200 text-center
                    shadow-lg shadow-brand-500/25
                  "
                >
                  Get Started as a Founder
                </Link>
                <button
                  onClick={() => setIsModalOpen(true)}
                  className="
                    inline-flex items-center justify-center px-8 py-4 
                    rounded-xl border border-brand-500/50 hover:border-brand-400
                    text-brand-400 hover:text-brand-300 font-semibold text-lg
                    transition-all duration-200
                    hover:bg-brand-500/10
                  "
                >
                  Become a Venture Builder
                  <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Mentor Orbit Visual - Large Size */}
            <div className="order-first lg:order-last">
              <MentorOrbit size="large" />
            </div>
          </div>
        </div>
      </section>

      {/* Featured Venture Builders Section */}
      <section className="relative py-4 md:py-8 overflow-hidden">
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <span className="inline-block text-xs font-medium uppercase tracking-wider text-gray-400 mb-3">
              Meet Our Network
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-tight mb-4">
              World-Class{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-blue-light-400">
                Experts
              </span>
            </h2>
            <p className="text-base md:text-lg text-gray-400 max-w-2xl mx-auto">
              Our venture builders bring decades of combined experience across industries, 
              stages, and geographies.
            </p>
          </div>

          {/* Featured Builders Grid */}
          <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {featuredBuilders.map((builder) => (
              <VentureBuilderCard key={builder.id} builder={builder} />
            ))}
          </div>

          {/* Stats */}
          <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: '10+', label: 'Venture Builders' },
              { value: '50+', label: 'Years Combined Experience' },
              { value: '8+', label: 'Countries Covered' },
              { value: '100+', label: 'Founders Supported' },
            ].map((stat, idx) => (
              <div key={idx} className="text-center">
                <div className="text-3xl md:text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-blue-light-400 mb-2">
                  {stat.value}
                </div>
                <div className="text-sm text-gray-400">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="relative py-4 md:py-8 overflow-hidden">
        {/* Subtle background */}
        <div 
          className="absolute inset-0 bg-gradient-to-b from-transparent via-brand-500/5 to-transparent"
          aria-hidden="true"
        />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <span className="inline-block text-xs font-medium uppercase tracking-wider text-gray-400 mb-3">
              How It Works
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-tight mb-4">
              Become a{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-blue-light-400">
                Venture Builder
              </span>
            </h2>
            <p className="text-base md:text-lg text-gray-400 max-w-2xl mx-auto">
              Join our growing pool of experienced venture builders and help shape 
              the future of entrepreneurship in Africa.
            </p>
          </div>

          {/* Steps Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {howItWorksSteps.map((step, index) => (
              <StepCard key={step.id} step={step} index={index} />
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-20 md:py-32 overflow-hidden">
        {/* Background glow */}
        <div 
          className="absolute inset-0 bg-gradient-to-t from-brand-500/10 via-transparent to-transparent"
          aria-hidden="true"
        />
        <div 
          className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-brand-500/15 rounded-full blur-[100px]"
          aria-hidden="true"
        />

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-tight mb-6">
            Ready to Make an Impact?
          </h2>
          <p className="text-lg md:text-xl text-gray-400 leading-relaxed mb-10 max-w-2xl mx-auto">
            Join our growing pool of venture builders and help founders turn their 
            ideas into successful ventures. Share your expertise, build lasting 
            relationships, and contribute to Africa's entrepreneurial ecosystem.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="
              inline-flex items-center justify-center px-10 py-5 
              rounded-xl bg-brand-500 hover:bg-brand-600 
              text-white font-semibold text-xl
              transition-all duration-200
              shadow-xl shadow-brand-500/30
              hover:shadow-brand-500/40
              hover:scale-105
            "
          >
            Join Our Growing Pool of Venture Builders
            <svg className="w-6 h-6 ml-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </button>
        </div>
      </section>

      {/* Venture Builder Interest Modal */}
      <VentureBuilderInterestModal
        isOpen={isModalOpen}
        onOpenChange={setIsModalOpen}
      />
      </div>
      
      {/* Footer */}
      <Footer />
    </>
  );
}
