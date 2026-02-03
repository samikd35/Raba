"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Users, ChevronDown, ChevronRight, Briefcase } from "lucide-react";
import type { PrimaryPersona } from "@/hooks/usePRD";

interface PRDPersonaSectionProps {
  persona: PrimaryPersona;
  index?: number;
}

export function PRDPersonaSection({ persona, index = 2 }: PRDPersonaSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card className="border-gray-200 dark:border-gray-700 dark:bg-gray-900/50 transition-all hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/70 rounded-lg overflow-hidden">
      {/* Collapsible Header */}
      <div
        className="px-3 py-1 cursor-pointer select-none transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start gap-2">
          <div className="text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">
            {isOpen ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </div>

          <div className="flex-1 flex flex-col gap-2">
            <Badge
              variant="outline"
              className="text-green-600 border-green-200 dark:text-green-400 dark:border-green-700 px-2 py-0.5 rounded-lg bg-green-50 dark:bg-green-900/30 w-fit"
            >
              <Users className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Primary Persona: {persona.name}</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200 line-clamp-1">
              {persona.description.slice(0, 100)}...
            </span>
          </div>
        </div>
      </div>

      {/* Collapsible Content */}
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <CardContent className="px-4 space-y-2 pb-3">
              {/* Persona Description */}
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Description
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                  {persona.description}
                </p>
              </div>

              {/* Primary Job */}
              <div className="p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700/60">
                <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-400 mb-2 flex items-center gap-2">
                  <Briefcase className="w-4 h-4" />
                  Primary Job
                </h4>
                <p className="text-sm text-brand-700 dark:text-brand-200 leading-relaxed mt-2">
                  {persona.primary_job.job_statement}
                </p>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
