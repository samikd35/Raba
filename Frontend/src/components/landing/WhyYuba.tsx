"use client"

import React from 'react';
import Image from 'next/image';

interface CardData {
  icon: React.ReactNode;
  title: string;
  body: string;
}

const WhyYuba = () => {
  const cards: CardData[] = [
    {
      icon: (
        <div className="relative w-10 h-10 md:w-12 md:h-12">
          <Image
            src="/images/icons/early.png"
            alt="Early-stage founders icon"
            fill
            className="object-contain"
            style={{
              filter: 'brightness(0) saturate(100%) invert(27%) sepia(65%) saturate(1847%) hue-rotate(192deg) brightness(91%) contrast(92%)'
            }}
          />
        </div>
      ),
      title: "For Early-Stage Founders",
      body: "Early-stage founders often face a high-risk path filled with fragmented tools, biased feedback, and a lack of structured guidance, which contributes to high failure rates. Designed around a four-module journey, Yuba's ecosystem guides founders through the critical stages of building a venture. By ensuring systematic de-risking, an integrated workflow, and actionable outputs at every step, Yuba is your sounding board and a trusted co-founder you never knew you needed."
    },
    {
      icon: (
        <div className="relative w-10 h-10 md:w-12 md:h-12">
          <Image
            src="/images/icons/eso.png"
            alt="ESO icon"
            fill
            className="object-contain"
            style={{
              filter: 'brightness(0) saturate(100%) invert(27%) sepia(65%) saturate(1847%) hue-rotate(192deg) brightness(91%) contrast(92%)'
            }}
          />
        </div>
      ),
      title: "For Entrepreneurship Support Organizations",
      body: "Our integrated platform empowers you to streamline your venture portfolio management, track progress in real-time, and scale your reach while cutting overhead costs. We're more than a platform; we're your reliable venture builder in producing higher-quality ventures. By enabling unparalleled efficiency in delivering world-class venture support, we help you elevate your reputation and attract top founders and more funders."
    }
  ];

  return (
    <section
      id="why-yuba"
      className="relative py-16 md:py-24 lg:py-32 overflow-hidden"
      aria-labelledby="why-yuba-heading"
    >
      {/* Background with subtle gradient */}
      <div 
        className="absolute inset-0 bg-gradient-to-br from-gray-50 via-white to-brand-25 dark:from-gray-950 dark:via-gray-900 dark:to-brand-950"
        aria-hidden="true"
      />
      
      {/* Subtle dot pattern overlay */}
      <div 
        className="absolute inset-0 opacity-40 dark:opacity-20"
        style={{
          backgroundImage: "radial-gradient(circle at 1px 1px, rgba(36, 70, 148, 0.15) 1px, transparent 0)",
          backgroundSize: "24px 24px",
        }}
        aria-hidden="true"
      />

      {/* Gradient orbs for depth */}
      <div 
        className="absolute top-0 left-1/4 w-96 h-96 bg-brand-200/20 dark:bg-brand-500/10 rounded-full blur-3xl"
        aria-hidden="true"
      />
      <div 
        className="absolute bottom-0 right-1/4 w-80 h-80 bg-blue-light-200/20 dark:bg-blue-light-500/10 rounded-full blur-3xl"
        aria-hidden="true"
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-12 md:mb-16 lg:mb-20">
          <h2 
            id="why-yuba-heading"
            className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight"
          >
            <span className="text-gray-900 dark:text-white">Why You Should </span>
            <span className="text-brand-500 dark:text-brand-400">Choose Us</span>
          </h2>
        </div>

        {/* Cards Container */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8 lg:gap-10">
          {cards.map((card, index) => (
            <article
              key={index}
              className="group relative"
            >
              {/* Glassmorphic Card */}
              <div 
                className="
                  relative h-full p-6 md:p-8 lg:p-10 rounded-2xl md:rounded-3xl
                  bg-white/70 dark:bg-white/5
                  backdrop-blur-xl
                  border border-white/50 dark:border-white/10
                  shadow-lg shadow-gray-200/50 dark:shadow-black/20
                  transition-all duration-300 ease-out
                  hover:shadow-xl hover:shadow-brand-200/30 dark:hover:shadow-brand-500/10
                  hover:border-brand-200/50 dark:hover:border-brand-500/20
                  hover:bg-white/80 dark:hover:bg-white/[0.07]
                "
              >
                {/* Subtle glow effect on hover */}
                <div 
                  className="
                    absolute inset-0 rounded-2xl md:rounded-3xl opacity-0 
                    group-hover:opacity-100 transition-opacity duration-300
                    bg-gradient-to-br from-brand-100/20 via-transparent to-blue-light-100/20
                    dark:from-brand-500/5 dark:via-transparent dark:to-blue-light-500/5
                  "
                  aria-hidden="true"
                />

                {/* Card Content */}
                <div className="relative z-10">
                  {/* Icon Container */}
                  <div 
                    className="
                      inline-flex items-center justify-center
                      w-16 h-16 md:w-20 md:h-20 mb-6 md:mb-8
                      rounded-xl md:rounded-2xl
                      bg-gradient-to-br from-brand-50 to-blue-light-50
                      dark:from-brand-500/20 dark:to-blue-light-500/20
                      border border-brand-100/50 dark:border-brand-500/30
                      shadow-sm
                      group-hover:scale-105 transition-transform duration-300
                    "
                  >
                    {card.icon}
                  </div>

                  {/* Title */}
                  <h3 
                    className="
                      text-xl md:text-2xl lg:text-[1.625rem] font-bold mb-4 md:mb-5
                      text-gray-900 dark:text-white
                      leading-tight tracking-tight
                    "
                  >
                    {card.title}
                  </h3>

                  {/* Body */}
                  <p 
                    className="
                      text-sm md:text-base lg:text-[0.9375rem] leading-relaxed
                      text-gray-600 dark:text-gray-300
                    "
                  >
                    {card.body}
                  </p>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};

export default WhyYuba;
