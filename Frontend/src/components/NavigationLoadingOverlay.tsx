"use client";

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigationLoading } from '@/context/NavigationLoadingContext';

const NavigationLoadingOverlay: React.FC = () => {
  const { isLoading } = useNavigationLoading();

  return (
    <AnimatePresence>
      {isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm"
        >
          <div className="flex flex-col items-center space-y-4">
            {/* Loading Spinner */}
            <div className="relative">
              {/* Outer Ring */}
              <motion.div
                className="w-16 h-16 border-4 border-brand-200 dark:border-brand-700 rounded-full"
                animate={{ rotate: 360 }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "linear"
                }}
              />
              
              {/* Inner Ring */}
              <motion.div
                className="absolute inset-2 w-12 h-12 border-4 border-transparent border-t-brand-600 dark:border-t-brand-400 rounded-full"
                animate={{ rotate: -360 }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: "linear"
                }}
              />
              
              {/* Center Dot */}
              <motion.div
                className="absolute inset-6 w-4 h-4 bg-brand-600 dark:bg-brand-400 rounded-full"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              />
            </div>

            {/* Loading Text */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-center"
            >
              <h3 className="text-lg font-semibold text-brand-700 dark:text-brand-300 mb-1">
                Loading...
              </h3>
             
            </motion.div>

            {/* Animated Dots */}
            <div className="flex space-x-1">
              {[0, 1, 2].map((index) => (
                <motion.div
                  key={index}
                  className="w-2 h-2 bg-brand-600 dark:bg-brand-400 rounded-full"
                  animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    delay: index * 0.2,
                    ease: "easeInOut"
                  }}
                />
              ))}
            </div>
          </div>

          {/* Progress Bar */}
          <motion.div
            className="absolute bottom-0 left-0 h-1 bg-gradient-to-r from-brand-500 to-brand-600 dark:from-brand-400 dark:to-brand-500"
            initial={{ width: "0%" }}
            animate={{ width: "100%" }}
            transition={{
              duration: 8,
              ease: "easeOut"
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default NavigationLoadingOverlay;
