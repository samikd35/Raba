import React from 'react';
import Image from 'next/image';

interface OGImageGeneratorProps {
  title?: string;
  subtitle?: string;
}

const OGImageGenerator: React.FC<OGImageGeneratorProps> = ({
  title = "A Sounding Board for",
  subtitle = "African Entrepreneurs"
}) => {
  return (
    <div className="relative w-[1200px] h-[630px] bg-gradient-to-br from-brand-500 via-[#1a3a7a] to-[#128AA3] flex items-center justify-center overflow-hidden">
      {/* Background Pattern */}
      <div 
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage: "radial-gradient(circle at 1px 1px, rgba(255, 255, 255, 0.3) 1px, transparent 0)",
          backgroundSize: "40px 40px"
        }}
      />

      {/* Decorative Circles */}
      <div className="absolute top-10 right-10 w-64 h-64 rounded-full bg-white/5 blur-3xl" />
      <div className="absolute bottom-10 left-10 w-96 h-96 rounded-full bg-white/5 blur-3xl" />

      {/* Content Container */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center px-20">
        {/* Logo */}
        <div className="relative w-32 h-32 mb-8">
          <Image
            src="/images/logo/yuba-logo-icon-white.png"
            alt="Yuba Logo"
            fill
            className="object-contain drop-shadow-2xl"
          />
        </div>

        {/* Brand Name */}
        <h1 className="text-8xl font-bold text-white mb-6 tracking-tight drop-shadow-lg">
          Yuba
        </h1>

        {/* Title */}
        <h2 className="text-5xl font-semibold text-white/95 mb-3 leading-tight">
          {title}
        </h2>

        {/* Subtitle */}
        <h3 className="text-6xl font-bold text-white leading-tight mb-8">
          {subtitle}
        </h3>

        {/* Tagline */}
        <p className="text-2xl text-white/90 max-w-3xl leading-relaxed">
          Get contextual and actionable market insights to validate your business ideas
        </p>

        {/* Bottom Badge */}
        <div className="absolute bottom-12 left-1/2 transform -translate-x-1/2">
          <div className="px-8 py-4 rounded-full bg-white/10 backdrop-blur-md border border-white/20">
            <p className="text-xl font-medium text-white">yuba.app</p>
          </div>
        </div>
      </div>

      {/* Corner Accent */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-white/10 to-transparent rounded-bl-full" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-gradient-to-tr from-white/10 to-transparent rounded-tr-full" />
    </div>
  );
};

export default OGImageGenerator;
