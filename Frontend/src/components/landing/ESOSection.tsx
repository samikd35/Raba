"use client";

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import DemoRequestModal from '@/components/pricing/DemoRequestModal';

// Industry data for pills animation
const industries = [
  "Agriculture", "Finance", "Retail", "Education", "Healthcare", "Technology",
  "Manufacturing", "Logistics", "Real Estate", "Hospitality", "Marketing",
  "Entertainment", "Legal", "Consulting", "Insurance", "Construction", "Transportation",
  "E-commerce", "Telecommunications", "Media", "Automotive", "Energy", "Food & Beverage",
  "Fashion", "Sports", "Travel", "Gaming", "Non-profit", "Aerospace", "Pharmaceuticals",
  "Biotech", "Mining"
];

const INDUSTRIES_PER_SET = 7;
const ANIMATION_INTERVAL = 4000;
const FADE_OUT_DURATION = 250;
const STAGGER_DELAY = 50;

// Card data with exact content from specifications
const cardData = [
  {
    id: 1,
    title: "Expand Reach, Quantify Impact",
    body: "Part ways with geographical barriers and broaden your pipeline by reaching candidates in remote locations.",
  },
  {
    id: 2,
    title: "Scale World-class Venture Support",
    body: "Cut down your hiring costs by tapping into Yuba’s growing pool of vetted Venture Builders for world-class venture-building support. ",
  },
  {
    id: 3,
    title: "Direct Program Oversight",
    body: "Run as many programs as you wish, down to the level of cohorts, track participants’ progress in real-time, and chat with them & their projects",
  },
  {
    id: 4,
    title: "On-Demand Customization",
    body: "Customize your accounts to meet your program operations and reporting needs and team structure requirements.",
  },
];

// Industry Pills Component with Animation
const IndustryPills = () => {
  const [currentSet, setCurrentSet] = useState(0);
  const [isVisible, setIsVisible] = useState(true);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const totalSets = useMemo(() => 
    Math.ceil(industries.length / INDUSTRIES_PER_SET), 
    []
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handleMediaChange = () => setPrefersReducedMotion(mediaQuery.matches);
    setPrefersReducedMotion(mediaQuery.matches);
    mediaQuery.addEventListener('change', handleMediaChange);
    return () => mediaQuery.removeEventListener('change', handleMediaChange);
  }, []);

  const getCurrentIndustries = useCallback(() => {
    const startIndex = (currentSet * INDUSTRIES_PER_SET) % industries.length;
    const currentIndustries: string[] = [];
    for (let i = 0; i < INDUSTRIES_PER_SET; i++) {
      currentIndustries.push(industries[(startIndex + i) % industries.length]);
    }
    return currentIndustries;
  }, [currentSet]);

  const currentIndustries = getCurrentIndustries();

  const startAnimationCycle = useCallback(() => {
    if (prefersReducedMotion) return;
    intervalRef.current = setInterval(() => {
      setIsVisible(false);
      timeoutRef.current = setTimeout(() => {
        setCurrentSet(prev => (prev + 1) % totalSets);
        setIsVisible(true);
      }, FADE_OUT_DURATION);
    }, ANIMATION_INTERVAL);
  }, [prefersReducedMotion, totalSets]);

  useEffect(() => {
    startAnimationCycle();
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [startAnimationCycle]);

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (!prefersReducedMotion) startAnimationCycle();
  }, [prefersReducedMotion, startAnimationCycle]);

  const tagPositions = useMemo(() => [
    { position: 'top-[4%] left-1/2 -translate-x-1/2', delay: 0 },
    { position: 'top-[23%] left-[21%] -translate-x-1/2', delay: STAGGER_DELAY },
    { position: 'top-[23%] right-[21%] translate-x-1/2', delay: STAGGER_DELAY * 2 },
    { position: 'top-[49%] left-1/2 -translate-x-1/2 -translate-y-1/2', delay: STAGGER_DELAY * 3 },
    { position: 'bottom-[25%] left-[21%] -translate-x-1/2', delay: STAGGER_DELAY * 4 },
    { position: 'bottom-[25%] right-[21%] translate-x-1/2', delay: STAGGER_DELAY * 5 },
    { position: 'bottom-[6%] left-1/2 -translate-x-1/2', delay: STAGGER_DELAY * 6 }
  ], []);

  const baseTagClasses = `
    inline-flex items-center justify-center
    px-4 py-3 md:px-8 md:py-4 
    rounded-full text-white font-medium leading-none
    bg-gradient-to-b from-[#128AA3] to-[#244694] 
    shadow-lg shadow-[#128AA3]/30 hover:shadow-[#244694]/40 
    transition-all duration-300 ease-out
    text-sm sm:text-base md:text-lg lg:text
  `;

  const visibilityClass = isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4';

  return (
    <div 
      className="relative w-full max-w-[280px] sm:max-w-[340px] md:w-[380px] md:h-[380px] lg:w-[420px] lg:h-[420px] aspect-square mx-auto"
      role="img"
      aria-label="Rotating industry tags showing various business sectors"
    >
      {/* Subtle glow background matching ESO light mode */}
      <div className="absolute inset-0 grid place-items-center">
        <div 
          className="w-[280px] h-[280px] sm:w-[320px] sm:h-[320px] md:w-[400px] md:h-[400px] lg:w-[440px] lg:h-[440px] rounded-full blur-3xl"
          style={{
            background: 'radial-gradient(closest-side, rgba(36,70,148,0.12), rgba(18,138,163,0.06), transparent 70%)'
          }}
          aria-hidden="true"
        />
      </div>

      {/* Positioned Tags */}
      <div className="absolute inset-0">
        {tagPositions.map((pos, index) => (
          <div 
            key={index}
            className={`absolute ${pos.position}`}
          >
            <span 
              className={`${baseTagClasses} ${visibilityClass}`}
              style={{
                transitionDelay: prefersReducedMotion ? '0ms' : `${pos.delay}ms`
              }}
              role="listitem"
              aria-label={currentIndustries[index]}
            >
              {currentIndustries[index]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Glassmorphic Card Component
const EsoCard = ({ 
  card, 
  onBookDemo 
}: { 
  card: typeof cardData[0]; 
  onBookDemo: () => void;
}) => {
  return (
    <div className="group relative h-full">
      <div
        className="
          relative h-full p-5 md:p-6 pb-8 md:pb-12 rounded-2xl
          bg-white/60
          backdrop-blur-xl
          border border-gray-200/60
          shadow-[0_8px_32px_0_rgba(0,0,0,0.08)]
          transition-all duration-300 ease-out
          hover:border-brand-400/40
          hover:shadow-[0_12px_40px_0_rgba(36,70,148,0.15)]
          overflow-hidden
        "
      >
        {/* Soft inner gradient highlight */}
        <div
          className="absolute inset-0 bg-gradient-to-br from-white/80 via-white/40 to-transparent pointer-events-none rounded-2xl"
          aria-hidden="true"
        />
        
        {/* Subtle brand-tinted top edge glow */}
        <div
          className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-brand-400/50 to-transparent"
          aria-hidden="true"
        />

        <div className="relative z-10 flex flex-col h-full">
          {/* Title */}
          <h3 className="text-lg md:text-2xl font-bold text-gray-900 mb-2 md:mb-3 leading-tight text-brand-600 text-transparent bg-clip-text bg-gradient-to-r from-brand-500 to-blue-light-600">
            {card.title}
          </h3>

          {/* Body */}
          <p className="text-sm md:text-base text-gray-600 leading-relaxed flex-grow line-clamp-3 md:line-clamp-none">
            {card.body}
          </p>
        </div>

        {/* Glassmorphic Book a Demo Button - Persistent on mobile, hover on desktop */}
        <button
          onClick={onBookDemo}
          className="
            absolute bottom-2 left-2 md:left-auto md:right-4 z-20
            inline-flex items-center justify-center
            px-4 py-2 md:px-5 md:py-2.5
            min-h-[44px]
            rounded-lg
            bg-white/70
            backdrop-blur-md
            border border-gray-300/60
            text-sm font-medium text-gray-900
            transition-all duration-300 ease-out
            opacity-100 translate-y-0
            md:opacity-0 md:translate-y-2
            md:group-hover:opacity-100 md:group-hover:translate-y-0
            hover:bg-white/90
            hover:border-brand-400/60
            hover:shadow-[0_0_20px_0_rgba(36,70,148,0.2)]
            focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:ring-offset-2 focus:ring-offset-white
            active:scale-95
            w-fit
          "
        >
          Book a Demo
        </button>
      </div>
    </div>
  );
};

// Main EsoSection Component
const EsoSection = () => {
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);

  const handleOpenDemo = () => {
    setIsDemoModalOpen(true);
  };

  return (
    <section
      id="eso"
      className="relative py-12 md:py-20 lg:py-26 overflow-hidden bg-[#f8fafc]"
      aria-labelledby="how-it-works-heading"
    >
      {/* Background */}
      <div className="absolute inset-0 bg-[#f8fafc]" aria-hidden="true" />

      {/* Background Blur Spot - Centered behind cards */}
      <div
        className="
          absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
          w-[600px] h-[600px] md:w-[800px] md:h-[800px]
          rounded-full
          blur-3xl
          pointer-events-none
        "
        style={{
          background: 'radial-gradient(circle, rgba(36,70,148,0.08) 0%, rgba(18,138,163,0.05) 40%, transparent 70%)',
        }}
        aria-hidden="true"
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.05fr_2fr] gap-4 lg:gap-6 xl:gap-10 items-start">
          {/* Left Column - Heading Block */}
          <div className="lg:sticky lg:top-10 text-center lg:text-left">
            {/* <span className="inline-block text-xs font-medium uppercase tracking-wider text-gray-500 mb-3 ">
              HOW TO SUPERCHARGE YOUR PROGRAMS
            </span> */}
            <h2
              id="how-it-works-heading"
              className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 tracking-tight mb-4 leading-tight"
            >
              From Fragmented Stacks to an <span className="text-brand-600 text-transparent bg-clip-text bg-gradient-to-r from-brand-500 to-blue-light-600">Integrated System: What ESOs get</span>
            </h2>
            <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
              End-to-End Entrepreneurship Support Platform.
            </p>
          </div>

          {/* Right Column - Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 md:gap-6 lg:gap-8">
            {cardData.map((card) => (
              <EsoCard key={card.id} card={card} onBookDemo={handleOpenDemo} />
            ))}
          </div>
        </div>
      </div>

      {/* Industry Agnostic Section - Integrated */}
      <div className="relative max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 md:mt-12 lg:mt-16">
        <div className="grid md:grid-cols-2 gap-6 md:gap-12 lg:gap-24 items-center">
          {/* Industry Pills Cluster */}
          <div className="flex justify-center md:justify-start order-2 md:order-1">
            <IndustryPills />
          </div>

          {/* Text Content */}
          <div className="max-w-xl mx-auto md:mx-0 text-center md:text-left order-1 md:order-2">
            <h2 
              className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 leading-tight tracking-tight mb-4"
            >
              <span className="text-brand-600">Industry</span> Agnostic
            </h2>
            <p className="text-base text-gray-600 leading-relaxed max-w-prose">
              Whether you support founders in agriculture, finance, health, education, or technology, Yuba helps you run programs with structure, visibility, and measurable outcomes across every cohort.
            </p>
          </div>
        </div>
      </div>

      {/* Demo Request Modal */}
      <DemoRequestModal
        isOpen={isDemoModalOpen}
        onOpenChange={setIsDemoModalOpen}
        requestedTier="organization"
        source="eso_section"
      />
    </section>
  );
};

export default EsoSection;
