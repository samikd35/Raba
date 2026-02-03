"use client";

import React, { useState } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { AlertCircle, AlertTriangle, Lightbulb, ChevronDown, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from 'framer-motion';
import { Critique, Source } from '../types';
import { CitationText } from './CitationText';

interface CritiqueCardProps {
  critique: Critique;
  index: number;
  allSources: Source[];
  dimensionSummary?: string;
}

/**
 * Critique Card Component - Displays a single critique with problem, impact, and recommendations
 */
export const CritiqueCard: React.FC<CritiqueCardProps> = ({ 
  critique, 
  index, 
  allSources,
  dimensionSummary 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  // Get summary from critique (new backend format)
  const summaryItems = critique.summary || [];
  
  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 py-0 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg">
      {/* Collapsible Header */}
      <div 
        className="px-4 py-4 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-3">
          {/* Expand/Collapse Icon */}
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? (
              <ChevronDown className="w-5 h-5" />
            ) : (
              <ChevronRight className="w-5 h-5" />
            )}
          </div>
          
          <div className="flex-1 flex flex-col gap-2">
            <Badge 
              variant="outline" 
              className="text-brand-500 border-brand-200 dark:text-brand-400 dark:border-brand-700 px-3 py-1 rounded-lg bg-brand-50 dark:bg-brand-900/30 w-fit"
            >
              <span className="text-[1rem] font-semibold">{index + 1}{critique.section_name ? ` · ${critique.section_name}` : ''}</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200 flex gap-2 items-center">
              <CitationText 
                text={critique.title} 
                sources={critique.sources} 
                allSources={allSources} 
              />
            </span>
          </div>
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
            {/* Key Findings Summary Section */}
            {summaryItems.length > 0 && (
              <CardContent className="mx-4 px-4 bg-gray-50 dark:bg-gray-800/50 p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div className="space-y-2">
                  {summaryItems.map((item, idx) => (
                    <div 
                      key={idx} 
                      className="flex items-start gap-3 text-sm text-brand-700 dark:text-brand-300 p-2"
                    >
                      <span className="shrink-0 w-2 h-2 rounded-full bg-brand-500 dark:bg-brand-600 mt-1.5" />
                      <span className="flex-1 leading-relaxed">
                        <CitationText 
                          text={item} 
                          sources={critique.sources} 
                          allSources={allSources} 
                        />
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            )}

            <CardContent className="px-4 space-y-2 mt-2">
              {/* Problem Section - Inner Accordion */}
              <Accordion type="single" collapsible defaultValue="rationale">
                <AccordionItem value="rationale" className="border-none">
                  <AccordionTrigger className="p-2 hover:no-underline border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <h4 className="text-md font-semibold text-brand-600 dark:text-brand-400 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                      Critique Rationale
                    </h4>
                  </AccordionTrigger>
                  <AccordionContent>
                    <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed p-2">
                      <CitationText 
                        text={critique.problem} 
                        sources={critique.sources} 
                        allSources={allSources} 
                      />
                    </p>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>

              {/* Impact Section */}
              <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700/60">
                <h4 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-2 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Implication on your Solution
                </h4>
                <p className="text-sm text-red-700 dark:text-red-200 leading-relaxed">
                  <CitationText 
                    text={critique.impact} 
                    sources={critique.sources} 
                    allSources={allSources} 
                  />
                </p>
              </div>

              {/* Recommendations Section */}
              {critique.suggestions.length > 0 && (
                <div className="my-4">
                  <h4 className="text-md font-semibold text-brand-600 dark:text-brand-400 mb-3 flex items-center gap-2">
                    <Lightbulb className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                    Recommendations
                  </h4>
                  <div className="space-y-3">
                    {critique.suggestions.map((suggestion, idx) => (
                      <div 
                        key={idx} 
                        className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-sm transition-shadow"
                      >
                        <div className="flex items-start gap-3">
                          <div className="shrink-0 w-6 h-6 rounded-full bg-brand-500 dark:bg-brand-600 text-white flex items-center justify-center text-xs font-bold">
                            {idx + 1}
                          </div>
                          <div className="flex-1 space-y-2">
                            <p className="text-sm font-medium text-gray-800 dark:text-gray-100">
                              <CitationText 
                                text={suggestion.action} 
                                sources={critique.sources} 
                                allSources={allSources} 
                              />
                            </p>
                            <p className="text-xs text-gray-600 dark:text-gray-300">
                              <CitationText 
                                text={suggestion.rationale} 
                                sources={critique.sources} 
                                allSources={allSources} 
                              />
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
};

export default CritiqueCard;
