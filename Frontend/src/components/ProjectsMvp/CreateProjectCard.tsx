'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Plus } from 'lucide-react';
import { Card } from "@/components/ui/card";
import { Button } from '@/components/ui/button';

import { useAuthStore } from '@/stores/authStore';

interface CreateProjectCardProps {
  index: number;
  onClick: () => void;
}

/**
 * Create Project Card - triggers modal to create new project
 */
export const CreateProjectCard = React.memo(({ index, onClick }: CreateProjectCardProps) => {
  const { user } = useAuthStore();

  if (!user?.can_skip_module) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="group"
    >
      <Card
        className="h-auto p-4 bg-brand-25 dark:from-brand-900/20 dark:to-brand-800/20 dark:bg-gray-900/20 hover:bg-gray-900/20 border-2 border-dashed border-brand-300 dark:border-brand-600 rounded-xl hover:border-brand-500 dark:hover:border-brand-400 hover:shadow-lg transition-all duration-200 cursor-pointer overflow-hidden relative h-full flex items-center justify-center"
        onClick={onClick}
      >
        <div className="text-center space-y-4">
          {/* Icon */}
          <div className="flex justify-center">
            <div className="w-16 h-16 rounded-full border-2 border-brand-500 dark:border-brand-400 bg-brand-50 dark:bg-brand-900/10 flex items-center justify-center group-hover:scale-110 transition-transform duration-200">
              <Plus className="h-8 w-8 text-brand-500 dark:text-brand-400" />
            </div>
          </div>

          {/* Text */}
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-brand-500 dark:text-brand-300">
              Create New Project
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 max-w-xs mx-auto">
              Start a new value proposition project from scratch
            </p>
          </div>

          {/* Button - appears on hover */}
          <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <Button
              className="bg-brand-500 hover:bg-brand-600 text-white"
              size="sm"
            >
              Create Project
            </Button>
          </div>
        </div>
      </Card>
    </motion.div>
  );
});

CreateProjectCard.displayName = 'CreateProjectCard';
