"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { ArrowRight, Layers, FileCheck, Cog } from 'lucide-react';

// Feature card data for Module 3
const featureCards = [
  {
    id: 1,
    icon: Layers,
    title: "Business Model Innovation",
    description: "Design a compelling Value Proposition to underpin the architecturing of your Business Model Canvas, and receive an initial version for each, and a final version, following your solution critique.",
  },
  {
    id: 2,
    icon: FileCheck,
    title: "Solution Critique",
    description: "Thoroughly evaluate your solution across six critical pillars for strategic soundness, including Market Viability, Operational Feasibility, Competitive Differentiation, Scalability Potential, Business Model Differentiation, and the Dominant Logic Business impact.",
  },
  {
    id: 3,
    icon: Cog,
    title: "Product Requirement Details",
    description: "Design and generate a detailed product requirement document for MVP feature prioritization. Download the report for offline use, or export it to any coding tools and part ways with prompting challenges.",
  },
];

// Feature Card Component (Dark Theme)
const FeatureCard = ({ 
  icon: Icon, 
  title, 
  description 
}: { 
  icon: React.ElementType; 
  title: string; 
  description: string;
}) => {
  return (
    <div
      className="
        relative p-5 md:p-7 rounded-xl
        bg-white/10
        backdrop-blur-md
        border border-white/20
        shadow-[0_4px_24px_0_rgba(0,0,0,0.2)]
        transition-all duration-300 ease-out
        hover:shadow-[0_8px_32px_0_rgba(0,0,0,0.3)]
        hover:-translate-y-1
        hover:bg-white/15
      "
    >
      {/* Icon and Title Row */}
      <div className="flex items-center gap-3 mb-3">
        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-brand-500 to-[#128AA3] flex items-center justify-center">
          <Icon className="w-6 h-6 text-white" />
        </div>
        <h3 className="text-base md:text-lg font-bold text-brand-400">
          {title}
        </h3>
      </div>

      {/* Description */}
      <p className="text-xs md:text-sm text-gray-200 leading-relaxed">
        {description}
      </p>
    </div>
  );
};

const Module3Section = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  const handleGetStarted = () => {
    if (!isAuthenticated) {
      router.push('/signup');
    } else {
      router.push('/choose-workspace');
    }
  };

  return (
    <section
      className="relative py-14 md:py-20 lg:py-24 md:pt-0 lg:pt-0 overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
      }}
    >
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Module Header */}
        <div className="text-center mb-10 md:mb-14">
          {/* Vertical Connector Line */}
          <div className="flex flex-col items-center">
            <div className="w-px h-14 md:h-20 bg-gradient-to-b from-transparent via-brand-500 to-brand-500" />
          </div>

          {/* Module Pill */}
          <span className="inline-block px-4 py-1.5 rounded-full text-xs font-medium text-brand-400 bg-brand-500/10 border border-brand-500/70 mb-4">
            Module 3
          </span>

          {/* Title */}
          <h2 className="text-2xl sm:text-3xl md:text-[2.75rem] font-bold text-white tracking-tight mb-3">
            MVP & Business Model Development
          </h2>

          {/* Subtitle */}
          <p className="text-sm md:text-base text-gray-400 max-w-2xl mx-auto">
            Validate your market assumptions and build confidence in your business model.
          </p>
        </div>

        {/* Main Content Row */}
        <div className="grid lg:grid-cols-2 gap-6 lg:gap-10 items-center mb-12 md:mb-20">
          {/* Left Column - Text Content */}
          <div className="order-2 lg:order-1 p-6 md:p-8 lg:p-10 pr-4 md:pr-6 lg:pr-8">
            <div>
              <h3 className="text-xl md:text-2xl font-bold text-white mb-4">
                Business Model Innovation
                 <br /> & Product Requirement 
              </h3>
              <p className="text-sm md:text-base text-gray-300 leading-relaxed mb-6">
                Translate your compelling value proposition into a robust and market-adaptive business model, critique your solution for strategic soundness, and craft your product requirements. 
              </p>

              {/* CTA Button */}
              <button
                onClick={handleGetStarted}
                className="
                  inline-flex items-center gap-2
                  px-6 py-2.5
                  rounded-full
                  bg-gradient-to-r from-brand-500 to-[#128AA3]
                  text-sm text-white font-semibold
                  transition-all duration-300
                  hover:shadow-[0_0_24px_0_rgba(36,70,148,0.4)]
                  hover:scale-105
                "
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Right Column - GIF Media Card */}
          <div className="order-1 lg:order-2">
            <div
              className="
                relative rounded-xl overflow-hidden
                bg-slate-800/50
                border border-slate-700/50
                shadow-[0_8px_32px_0_rgba(0,0,0,0.3)]
              "
            >
              <video
                src="/assets/Solution/product.gif"
                autoPlay
                loop
                muted
                playsInline
                className="w-full h-auto object-cover"
              />
            </div>
          </div>
        </div>

        {/* Feature Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 md:gap-6 mb-10">
          {featureCards.map((card) => (
            <FeatureCard
              key={card.id}
              icon={card.icon}
              title={card.title}
              description={card.description}
            />
          ))}
        </div>

        {/* Bottom CTA */}
        <div className="text-center">
          <button
            onClick={handleGetStarted}
            className="
              inline-flex items-center gap-2
              px-7 py-3
              rounded-full
              bg-gradient-to-r from-brand-500 to-[#128AA3]
              text-sm text-white font-semibold
              transition-all duration-300
              hover:shadow-[0_0_24px_0_rgba(36,70,148,0.4)]
              hover:scale-105
            "
          >
            Get Started
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </section>
  );
};

export default Module3Section;
