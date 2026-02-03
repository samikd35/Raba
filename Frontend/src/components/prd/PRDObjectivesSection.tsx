"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, ChevronDown, ChevronRight, Target, CheckCircle } from "lucide-react";
import type { Objective } from "@/hooks/usePRD";

interface PRDObjectivesSectionProps {
  objective: Objective;
  index?: number;
}

export function PRDObjectivesSection({ objective, index = 4 }: PRDObjectivesSectionProps) {
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
              <TrendingUp className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Objectives</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              {objective.learning_goals.length} learning goals · {objective.success_criteria.length} success criteria
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
              {/* Learning Goals */}
              <div className="p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700/60">
                <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-400 mb-3 flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  Learning Goals
                </h4>
                <div className="space-y-3">
                  {objective.learning_goals.map((goal, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-white dark:bg-gray-800/50 rounded-lg border border-brand-100 dark:border-brand-800 hover:shadow-sm transition-shadow"
                    >
                      <div className="flex items-start gap-3">
                        <div className="shrink-0 w-6 h-6 rounded-full bg-brand-500 dark:bg-brand-600 text-white flex items-center justify-center text-xs font-bold">
                          {idx + 1}
                        </div>
                        <p className="text-sm text-brand-700 dark:text-brand-200 leading-relaxed">
                          {goal}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Success Criteria */}
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700/60">
                <h4 className="text-sm font-semibold text-green-700 dark:text-green-400 mb-3 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  Success Criteria
                </h4>
                <div className="space-y-3">
                  {objective.success_criteria.map((criteria, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-white dark:bg-gray-800/50 rounded-lg border border-green-100 dark:border-green-800 hover:shadow-sm transition-shadow"
                    >
                      <div className="flex items-start gap-3">
                        <div className="shrink-0 w-6 h-6 rounded-full bg-green-500 dark:bg-green-600 text-white flex items-center justify-center text-xs font-bold">
                          {idx + 1}
                        </div>
                        <p className="text-sm text-green-700 dark:text-green-200 leading-relaxed">
                          {criteria}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
