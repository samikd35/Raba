"use client";

import React from 'react';

const SolutionsHero = () => {
  return (
    <section
      className="relative py-16 md:py-24 lg:py-32 overflow-hidden"
      style={{
        background: "#ffffff",
        backgroundImage: "radial-gradient(circle at 1px 1px, rgba(0, 0, 0, 0.12) 1px, transparent 0)",
        backgroundSize: "20px 20px",
      }}
    >
      <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Headline */}
        <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 tracking-tight mb-6 leading-tight">
          The Founder's Journey: A guided path from ambiguous ideas to validated ventures.
        </h1>

        {/* Supporting text */}
        <p className="text-base md:text-lg text-gray-600 leading-relaxed max-w-3xl mx-auto">
          At the heart of the Yuba ecosystem is a meticulously designed, four-module journey that progressively guides founders through the critical stages of building a venture.
        </p>
      </div>
    </section>
  );
};

export default SolutionsHero;
