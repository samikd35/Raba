"use client";

import React from 'react';

const AdvantagesSection = () => {
  return (
    <section
      id="advantages"
      className="relative py-16 md:py-24 lg:py-32 overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
      }}
      aria-labelledby="advantages-heading"
    >
      {/* Background */}
      <div className="absolute inset-0" aria-hidden="true" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-12 md:mb-16">
          <h2
            id="advantages-heading"
            className="text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-tight mb-4"
          >
            The Yuba Advantage
          </h2>
        </div>

        {/* Comparison Cards Container */}
        <div className="relative max-w-6xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-24 items-center">
            {/* Left Card - The Old Way */}
            <div
              className="
                relative rounded-2xl
                bg-slate-700/40
                backdrop-blur-sm
                border border-slate-600/30
                shadow-[0_2px_16px_0_rgba(0,0,0,0.2)]
                transition-all duration-300 ease-out
                hover:shadow-[0_4px_20px_0_rgba(0,0,0,0.25)]
                hover:-translate-y-1
                overflow-hidden
              "
            >
              {/* Header Band - Neutral */}
              <div className="bg-slate-600/30 px-6 py-4 border-b border-slate-500/30">
                <div className="flex items-center gap-3">
                  {/* Icon */}
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-600/50 border-2 border-slate-500 flex items-center justify-center">
                    <svg
                      className="w-5 h-5 text-gray-300"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2.5}
                        d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                      />
                    </svg>
                  </div>
                  <h3 className="text-xl md:text-2xl font-bold text-white">
                    The Old Way
                  </h3>
                </div>
              </div>

              {/* Content */}
              <div className="p-6 md:p-8">
                <ul className="space-y-4">
                  <li className="flex items-start gap-3 text-gray-300">
                    <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-gray-400 mt-2" />
                    <span className="text-base md:text-lg leading-relaxed">
                      Fragmented Process
                    </span>
                  </li>
                  <li className="flex items-start gap-3 text-gray-300">
                    <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-gray-400 mt-2" />
                    <span className="text-base md:text-lg leading-relaxed">
                      One size fits all curricula
                    </span>
                  </li>
                  <li className="flex items-start gap-3 text-gray-300">
                    <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-gray-400 mt-2" />
                    <span className="text-base md:text-lg leading-relaxed">
                      Disjointed mentor advisory
                    </span>
                  </li>
                  <li className="flex items-start gap-3 text-gray-300">
                    <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-gray-400 mt-2" />
                    <span className="text-base md:text-lg leading-relaxed">
                      Lagging success indicators
                    </span>
                  </li>
                  <li className="flex items-start gap-3 text-gray-300">
                    <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-gray-400 mt-2" />
                    <span className="text-base md:text-lg leading-relaxed">
                      Lack of internal team capacity building
                    </span>
                  </li>
                </ul>
              </div>
            </div>

            {/* Arrow Indicator - Desktop: Right Arrow, Mobile: Down Arrow */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 hidden lg:flex items-center justify-center">
              <div className="w-12 h-12 rounded-full bg-slate-800 border-2 border-brand-400 shadow-lg flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-brand-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2.5}
                    d="M13 7l5 5m0 0l-5 5m5-5H6"
                  />
                </svg>
              </div>
            </div>

            {/* Mobile Arrow - Down */}
            <div className="flex lg:hidden items-center justify-center -my-4">
              <div className="w-12 h-12 rounded-full bg-slate-700 border-2 border-brand-400 shadow-lg flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-brand-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2.5}
                    d="M19 14l-7 7m0 0l-7-7m7 7V3"
                  />
                </svg>
              </div>
            </div>

            {/* Right Card - The Yuba Way */}
            <div
              className="
                relative rounded-2xl
                bg-gradient-to-br from-[#244694] to-[#128AA3]
                backdrop-blur-sm
                border border-brand-400/60
                shadow-[0_8px_32px_0_rgba(36,70,148,0.4)]
                transition-all duration-300 ease-out
                hover:shadow-[0_12px_40px_0_rgba(36,70,148,0.5)]
                hover:-translate-y-1
                overflow-hidden
              "
            >
              {/* Header Band - Brand Gradient */}
              <div className="bg-gradient-to-r from-[#128AA3] to-[#244694] px-6 py-4 border-b border-white/10">
                <div className="flex items-center gap-3">
                  {/* Icon */}
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/20 backdrop-blur-sm border border-white/40 flex items-center justify-center">
                    <svg
                      className="w-5 h-5 text-white"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2.5}
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                  <h3 className="text-xl md:text-2xl font-bold text-white">
                    The Yuba Way
                  </h3>
                </div>
              </div>

              {/* Content */}
              <div className="p-6 md:p-8">
                <ul className="space-y-4">
                  <li className="flex items-start gap-3 text-white">
                    <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-white mt-2" />
                    <span className="text-base md:text-lg leading-relaxed">
                      All in one integrated system
                    </span>
                  </li>
                  <li className="flex items-start gap-3 text-white">
                    <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-white mt-2" />
                    <span className="text-base md:text-lg leading-relaxed">
                      Rigorous & highly personalized journey
                    </span>
                  </li>
                  <li className="flex items-start gap-3 text-white">
                    <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-white mt-2" />
                    <span className="text-base md:text-lg leading-relaxed">
                      World-class Venture Building Support
                    </span>
                  </li>
                  <li className="flex items-start gap-3 text-white">
                    <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-white mt-2" />
                    <span className="text-base md:text-lg leading-relaxed">
                      Real-time progress metrics
                    </span>
                  </li>
                  <li className="flex items-start gap-3 text-white">
                    <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-white mt-2" />
                    <span className="text-base md:text-lg leading-relaxed">
                      In-design internal team capacity building
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default AdvantagesSection;
