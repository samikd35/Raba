"use client";

import React, { useState } from 'react';
import { BookOpen, ExternalLink, ChevronDown, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { motion, AnimatePresence } from 'framer-motion';
import { Source } from '../types';

interface ResearchSourcesProps {
  sources: Source[];
}

/**
 * Research Sources Component - Displays web sources used in the critique
 */
export const ResearchSources: React.FC<ResearchSourcesProps> = ({ sources }) => {
  const [isOpen, setIsOpen] = useState(false);
  const webSources = sources.filter(s => s.type === 'web' && s.url);

  if (webSources.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 py-0 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg">
        {/* Collapsible Header */}
        <div 
          className="px-4 py-3 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
          onClick={() => setIsOpen(!isOpen)}
        >
          <div className="flex items-center gap-3">
            {/* Expand/Collapse Icon */}
            <div className="text-gray-500 dark:text-gray-400 shrink-0">
              {isOpen ? (
                <ChevronDown className="w-5 h-5" />
              ) : (
                <ChevronRight className="w-5 h-5" />
              )}
            </div>
            
            {/* Title */}
            <BookOpen className="w-5 h-5 text-brand-500 shrink-0" />
            <h3 className="text-lg font-semibold text-brand-600 dark:text-brand-400 flex-1">
              Critique Refernces ({webSources.length})
            </h3>
          </div>
        </div>

        {/* Collapsible Content */}
        <AnimatePresence initial={false}>
          {isOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
              style={{ overflow: 'hidden' }}
            >
              <div className="px-4 pb-4">
                <div className="grid gap-2 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                  {webSources.map((source) => (
                    <a
                      key={source.id}
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 p-3 rounded-lg bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-md transition-all group w-full min-w-0"
                    >
                      <div className="flex-shrink-0 w-7 h-7 rounded-full bg-brand-100 dark:bg-brand-900/50 flex items-center justify-center text-xs font-bold text-brand-600 dark:text-brand-400">
                        {source.id}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-brand-600 dark:text-brand-300 truncate group-hover:text-brand-700 dark:group-hover:text-brand-200 transition-colors">
                          {source.title || 'Untitled Source'}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {source.url?.replace(/^https?:\/\//, '').split('/')[0]}
                        </p>
                      </div>
                      <ExternalLink className="w-4 h-4 text-gray-500 dark:text-gray-400 group-hover:text-brand-600 dark:group-hover:text-brand-400 flex-shrink-0 transition-colors" />
                    </a>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </div>
  );
};

export default ResearchSources;
