"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export interface CollapsibleSectionProps {
  title: string;
  description?: string;
  icon: React.ElementType;
  iconColor?: string;
  badge?: string | number;
  badgeVariant?: 'default' | 'success' | 'warning' | 'info';
  defaultOpen?: boolean;
  children: React.ReactNode;
  disabled?: boolean;
}

const badgeColors = {
  default: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  success: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
};

export function CollapsibleSection({
  title,
  description,
  icon: Icon,
  iconColor = 'text-brand-600',
  badge,
  badgeVariant = 'default',
  defaultOpen = false,
  children,
  disabled = false,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const handleToggle = () => {
    if (!disabled) {
      setIsOpen(!isOpen);
    }
  };

  return (
    <Card className={disabled ? 'opacity-60' : ''}>
      <CardHeader 
        className={`cursor-pointer select-none transition-colors ${
          disabled ? 'cursor-not-allowed' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'
        }`}
        onClick={handleToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Expand/Collapse Icon */}
            <div className="text-gray-400 dark:text-gray-500">
              {isOpen ? (
                <ChevronDown className="w-5 h-5" />
              ) : (
                <ChevronRight className="w-5 h-5" />
              )}
            </div>
            
            {/* Section Icon */}
            <Icon className={`w-5 h-5 ${iconColor}`} />
            
            {/* Title */}
            <CardTitle className="text-lg font-semibold">
              {title}
            </CardTitle>
            
            {/* Badge */}
            {badge !== undefined && (
              <Badge className={badgeColors[badgeVariant]}>
                {badge}
              </Badge>
            )}
          </div>
        </div>
        
        {/* Description - only show when collapsed */}
        {description && !isOpen && (
          <CardDescription className="ml-12 mt-1">
            {description}
          </CardDescription>
        )}
      </CardHeader>
      
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            <CardContent className="pt-0">
              {children}
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

export default CollapsibleSection;
