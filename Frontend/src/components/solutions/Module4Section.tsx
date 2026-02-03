"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { ArrowRight, Rocket, MessageCircle, Target } from 'lucide-react';

// Feature card data for Module 4
const featureCards = [
  {
    id: 1,
    icon: Rocket,
    title: "Ask Yuba AI Expert",
    description: "Your Project Expert feature, which learns about your work from the very beginning, can help extract quick and customized project insights upon request.",
  },
  {
    id: 2,
    icon: MessageCircle,
    title: "Market Validation Metrics",
    description: "Craft your market validation metrics and take your MVP to market, knowing exactly the success signals that will inform clear go or pivot decisions.",
  },
  {
    id: 3,
    icon: Target,
    title: "Pricing & GTM Strategies",
    description: "Design adaptive strategies that respond to your validation goals, the type of product you’re building, the customer segment, and take into account evolving market dynamics.",
  },
];

// Feature Card Component (Light Theme)
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
        bg-white/80
        backdrop-blur-md
        border border-brand-200/30
        shadow-[0_4px_24px_0_rgba(0,0,0,0.08)]
        transition-all duration-300 ease-out
        hover:shadow-[0_8px_32px_0_rgba(0,0,0,0.12)]
        hover:-translate-y-1
        hover:border-brand-300/50
      "
    >
      {/* Icon and Title Row */}
      <div className="flex items-center gap-3 mb-3">
        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-brand-500 to-[#128AA3] flex items-center justify-center">
          <Icon className="w-6 h-6 text-white" />
        </div>
        <h3 className="text-base md:text-lg font-bold text-brand-600">
          {title}
        </h3>
      </div>

      {/* Description */}
      <p className="text-xs md:text-sm text-gray-600 leading-relaxed">
        {description}
      </p>
    </div>
  );
};

const Module4Section = () => {
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
      className="relative py-14 md:py-20 lg:py-24 pt-0 md:pt-0 lg:pt-0 overflow-hidden"
      style={{
        background: "#f8fafc",
        backgroundImage: "radial-gradient(circle at 1px 1px, rgba(0, 0, 0, 0.06) 1px, transparent 0)",
        backgroundSize: "24px 24px",
      }}
    >
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Module Header */}
        <div className="text-center mb-10 md:mb-14">
          {/* Vertical Connector Line */}
          <div className="flex flex-col items-center">
            <div className="w-px h-14 md:h-20 bg-gradient-to-b from-transparent via-gray-300 to-gray-400" />
          </div>

          {/* Module Pill */}
          <span className="inline-block px-4 py-1.5 rounded-full text-xs font-medium text-brand-600 bg-brand-500/10 border border-brand-500/30 mb-4">
            Module 4
          </span>

          {/* Title */}
          <h2 className="text-2xl sm:text-3xl md:text-[2.75rem] font-bold text-brand-600 tracking-tight mb-3">
            Market Validation
          </h2>

          {/* Subtitle */}
          <p className="text-sm md:text-base text-gray-600 max-w-2xl mx-auto">
            Test your assumptions in the real market and validate demand before committing significant time or capital.
          </p>
        </div>

        {/* Upper Content Row */}
        <div className="grid lg:grid-cols-2 gap-6 lg:gap-10 items-center mb-12 md:mb-20">
          {/* Left Column - GIF Media Card */}
          <div className="order-2 lg:order-1">
            <div
              className="
                relative rounded-xl overflow-hidden
                bg-slate-800/50
                border border-slate-700/50
                shadow-[0_8px_32px_0_rgba(0,0,0,0.3)]
              "
            >
              <video
                src="/assets/Solution/money.gif"
                autoPlay
                loop
                muted
                playsInline
                className="w-full h-auto object-cover"
              />
            </div>
          </div>

          {/* Right Column - Text Content */}
          <div className="order-1 lg:order-2 p-6 md:p-8 lg:p-10">
            <div>
              <h3 className="text-xl md:text-3xl font-bold text-brand-600 mb-4">
                Strategy Formulator & <br /> Yuba AI Expert Chat
              </h3>
              <p className="text-sm md:text-base text-gray-600 leading-relaxed mb-6">
                Craft and design responsive strategies, validate with purpose, and accelerate your time to market.
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

export default Module4Section;
