"use client";

import React from "react";
import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";

interface BMCBlockProps {
  title: string;
  icon: LucideIcon;
  children: React.ReactNode;
  className?: string;
  compact?: boolean;
}

export const BMCBlock: React.FC<BMCBlockProps> = ({ 
  title, 
  icon: Icon, 
  children, 
  className = "",
  compact = false
}) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5 }}
    className={` rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow duration-200 p-2 h-full ${className}`}
  >
    <div className="flex items-center gap-2 mb-4 pb-2 border-b border-brand-200 dark:border-gray-700">
      <div className="p-2 bg-gradient-to-br from-brand-50 to-brand-100 dark:from-brand-900/30 dark:to-brand-800/30 rounded-lg">
        <Icon className="w-5 h-5 text-brand-600 dark:text-brand-400" />
      </div>
      <h3 className={`font-semibold text-brand-500 dark:text-white tracking-wide ${compact ? 'text-lg' : 'text-md'}`}>{title}</h3>
    </div>
    <div className="space-y-3 text-xs overflow-visible">
      {children}
    </div>
  </motion.div>
);
