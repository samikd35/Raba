'use client';

import { Play } from 'lucide-react';
import { motion } from 'framer-motion';


interface FeatureVideoButtonProps {
  onClick: () => void;
  className?: string;
}

export default function FeatureVideoButton({
  onClick,
  className = '',
}: FeatureVideoButtonProps) {
  return (
    <motion.button
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0, opacity: 0 }}
      whileHover={{ scale: 1.1 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={`
        fixed z-40
        w-14 h-14 rounded-full
        bg-brand-500 hover:bg-brand-600
        shadow-lg hover:shadow-xl
        flex items-center justify-center
        transition-colors duration-200
        ${className || 'bottom-6 right-6'}
      `}
      aria-label="Watch Explanation video"
      title="Watch Explanation video"
    >
      <Play className="w-6 h-6 text-white ml-0.5" />
    </motion.button>
  );
}
