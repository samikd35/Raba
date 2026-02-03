"use client";

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import Image from 'next/image';

// Mentor images for rotation
export const mentorImages = [
  { src: '/assets/mentor/Isidore.png', alt: 'Isidore' },
  { src: '/assets/mentor/thijan-dippenaar.webp', alt: 'Thijan Dippenaar' },
  { src: '/assets/mentor/Dennis.png', alt: 'Dennis' },
  { src: '/assets/mentor/kalkidan-mulu.webp', alt: 'Kalkidan Mulu' },
  { src: '/assets/mentor/David.png', alt: 'David' },
  { src: '/assets/mentor/boniface-m.webp', alt: 'Boniface M' },
  { src: '/assets/mentor/eyassu-girma.webp', alt: 'Eyassu Girma' },
  { src: '/assets/mentor/jean-michel.webp', alt: 'Jean Michel' },
  { src: '/assets/mentor/Naz.jpg', alt: 'Naz' },
  { src: '/assets/mentor/shingirai-elton.jpg', alt: 'Shingirai Elton' },
];

interface MentorOrbitProps {
  /** Size variant for different contexts */
  size?: 'default' | 'large';
  /** Rotation interval in milliseconds */
  rotationInterval?: number;
  /** Custom class name for the container */
  className?: string;
}

// Rotating Orbit Component
export const MentorOrbit = ({ 
  size = 'default', 
  rotationInterval = 5000,
  className = ''
}: MentorOrbitProps) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Get visible mentors (5 at a time)
  const visibleMentors = useMemo(() => {
    const mentors = [];
    for (let i = 0; i < 5; i++) {
      const index = (currentIndex + i) % mentorImages.length;
      mentors.push({ ...mentorImages[index], position: i });
    }
    return mentors;
  }, [currentIndex]);

  // Rotation animation
  const rotate = useCallback(() => {
    setIsAnimating(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev + 1) % mentorImages.length);
      setIsAnimating(false);
    }, 300);
  }, []);

  // Start rotation interval
  useEffect(() => {
    intervalRef.current = setInterval(rotate, rotationInterval);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [rotate, rotationInterval]);

  // Position configurations for 5 avatars around the orbit
  const positions = size === 'large' ? [
    { top: '5%', left: '50%', transform: 'translateX(-50%)', size: 'w-24 h-24 md:w-32 md:h-32 lg:w-40 lg:h-40' },
    { top: '28%', right: '7%', transform: 'none', size: 'w-24 h-24 md:w-32 md:h-32 lg:w-40 lg:h-40' },
    { bottom: '15%', right: '15%', transform: 'none', size: 'w-24 h-24 md:w-32 md:h-32 lg:w-40 lg:h-40' },
    { bottom: '15%', left: '15%', transform: 'none', size: 'w-24 h-24 md:w-32 md:h-32 lg:w-40 lg:h-40' },
    { top: '28%', left: '7%', transform: 'none', size: 'w-24 h-24 md:w-32 md:h-32 lg:w-40 lg:h-40' },
  ] : [
    { top: '5%', left: '50%', transform: 'translateX(-50%)', size: 'w-20 h-20 md:w-24 md:h-24 lg:w-32 lg:h-32' },
    { top: '28%', right: '7%', transform: 'none', size: 'w-20 h-20 md:w-24 md:h-24 lg:w-32 lg:h-32' },
    { bottom: '15%', right: '15%', transform: 'none', size: 'w-20 h-20 md:w-24 md:h-24 lg:w-32 lg:h-32' },
    { bottom: '15%', left: '15%', transform: 'none', size: 'w-20 h-20 md:w-24 md:h-24 lg:w-32 lg:h-32' },
    { top: '28%', left: '7%', transform: 'none', size: 'w-20 h-20 md:w-24 md:h-24 lg:w-32 lg:h-32' },
  ];

  const containerSize = size === 'large' 
    ? 'max-w-[600px] md:max-w-[700px] lg:max-w-[800px]' 
    : 'max-w-[500px] md:max-w-[600px]';

  const centerDotSize = size === 'large'
    ? 'w-20 h-20 md:w-24 md:h-24 lg:w-28 lg:h-28'
    : 'w-16 h-16 md:w-20 md:h-20';

  return (
    <div className={`relative w-full ${containerSize} aspect-square mx-auto ${className}`}>
      {/* Concentric orbit rings */}
      <div className="absolute inset-[5%] border border-white/20 rounded-full" aria-hidden="true" />
      <div className="absolute inset-[15%] border border-white/20 rounded-full" aria-hidden="true" />
      <div className="absolute inset-[25%] border border-white/20 rounded-full" aria-hidden="true" />
      <div className="absolute inset-[35%] border border-white/20 rounded-full" aria-hidden="true" />

      {/* Center dot with gradient */}
      <div 
        className={`
          absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
          ${centerDotSize} rounded-full
          bg-gradient-to-b from-[#128AA3] to-[#244694]
          shadow-lg shadow-brand-500/30
          z-10
        `}
        aria-hidden="true"
      />

      {/* Rotating mentor avatars */}
      {visibleMentors.map((mentor, idx) => {
        const pos = positions[idx];
        return (
          <div
            key={`${mentor.src}-${idx}`}
            className={`
              absolute z-20
              transition-all duration-500 ease-in-out
              ${pos.size}
              ${isAnimating ? 'opacity-70 scale-95' : 'opacity-100 scale-100'}
            `}
            style={{
              top: pos.top,
              bottom: (pos as any).bottom,
              left: pos.left,
              right: (pos as any).right,
              transform: pos.transform,
            }}
          >
            <div 
              className="
                w-full h-full rounded-full overflow-hidden
                ring-3 ring-brand-500/60 hover:ring-brand-400
                shadow-lg shadow-black/30
                transition-all duration-300
                hover:scale-110 hover:z-30
                cursor-pointer
              "
            >
              <Image
                src={mentor.src}
                alt={mentor.alt}
                fill
                className="object-cover rounded-full"
                sizes="(max-width: 768px) 64px, (max-width: 1024px) 80px, 128px"
                quality={100}
              />
            </div>
          </div>
        );
      })}

      {/* Decorative glow */}
      <div 
        className={`
          absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
          ${size === 'large' ? 'w-64 h-64 md:w-80 md:h-80' : 'w-48 h-48 md:w-64 md:h-64'} rounded-full
          bg-gradient-to-br from-brand-500/20 to-blue-light-500/10
          blur-3xl
        `}
        aria-hidden="true"
      />
    </div>
  );
};

export default MentorOrbit;
