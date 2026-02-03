"use client";

import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="fixed inset-0 z-[9999] flex h-screen w-full items-center justify-center bg-white/80 backdrop-blur-md dark:bg-gray-900/80">
      <div className="flex flex-col items-center space-y-6">
        {/* Enhanced Spinner Container */}
        <div className="relative">
          {/* Outer Glow Ring */}
          <div className="absolute inset-0 w-16 h-16 bg-brand-500/20 dark:bg-brand-400/20 rounded-full blur-lg animate-pulse"></div>
          
          {/* Main Spinner */}
          <Loader2 className="relative h-16 w-16 animate-spin text-brand-600 dark:text-brand-400 drop-shadow-lg" />
          
          {/* Inner Dot */}
          <div className="absolute inset-6 w-4 h-4 bg-brand-600 dark:bg-brand-400 rounded-full animate-pulse"></div>
        </div>

        {/* Enhanced Text Section */}
        <div className="text-center space-y-2">
          <h3 className="text-xl font-semibold text-brand-700 dark:text-brand-300 animate-pulse">
            Loading...
          </h3>
         
        </div>

        {/* Animated Progress Dots */}
        {/* <div className="flex space-x-2">
          <div className="w-2 h-2 bg-brand-600 dark:bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
          <div className="w-2 h-2 bg-brand-600 dark:bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
          <div className="w-2 h-2 bg-brand-600 dark:bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div> */}
      </div>

      {/* Bottom Progress Bar */}
      <div className="absolute bottom-0 left-0 w-full h-1 bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div className="h-full bg-gradient-to-r from-brand-500 to-brand-600 dark:from-brand-400 dark:to-brand-500 animate-pulse"></div>
      </div>
    </div>
  );
}