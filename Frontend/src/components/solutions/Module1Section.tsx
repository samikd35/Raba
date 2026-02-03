"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { Target, FileText, Sparkles, ArrowRight } from 'lucide-react';

// Feature card data
const featureCards = [
  {
    id: 1,
    icon: Target,
    title: "Frame the Opportunity",
    description: "Begin with your formulated problem statement. Do you not have a problem statement? No problem. With a simple description of your idea or what you wish to build, the problem predictor gives you a spectrum of options.",
  },
  {
    id: 2,
    icon: FileText,
    title: "Generate Cornerstone Report",
    description: "Get your comprehensive report whose highly contextualized findings and insights serve as the cornerstone for all subsequent tasks, ensuring that every step of the journey is built on a validated market reality.",
  },
  {
    id: 3,
    icon: Sparkles,
    title: "Extract Actionable Insights",
    description: "Engage directly with the report via chat or a dedicated actionable insights section. The full report can be downloaded or shared, privately or publicly.",
  },
];

// Feature Card Component
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

const Module1Section = () => {
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
          <span className="inline-block px-4 py-1.5 rounded-full text-xs font-medium text-brand-400 bg-brand-500/10 border border-brand-500/80 mb-4">
            Module 1
          </span>

          {/* Title */}
          <h2 className="text-2xl sm:text-3xl md:text-[2.75rem] font-bold text-white tracking-tight mb-3">
            Problem Discovery
          </h2>

          {/* Subtitle */}
          <p className="text-sm md:text-base text-gray-400 max-w-2xl mx-auto">
            De-Risk the Foundation with Rigorous Problem Validation.
          </p>
        </div>

        {/* Main Content Row */}
        <div className="grid lg:grid-cols-2 gap-6 lg:gap-10 items-center mb-12 md:mb-20">
          {/* Left Column - Text Content */}
          <div className="order-2 lg:order-1 p-6 md:p-8 lg:p-10 pr-4 md:pr-6 lg:pr-8">
            <div>
              <h3 className="text-xl md:text-2xl font-bold text-white mb-4">
                Problem Validator
              </h3>
              <p className="text-sm md:text-base text-gray-300 leading-relaxed mb-6">
                Delve deep into your industry, understand it in the context of your geography, and discover the reality surrounding the problem you’re exploring.
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
                src="/assets/Solution/dog.gif"
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

export default Module1Section;
