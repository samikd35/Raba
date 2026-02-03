"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileText, ChevronDown, ChevronRight, Zap, ListOrdered } from "lucide-react";
import type { Workflow } from "@/hooks/usePRD";

interface PRDWorkflowsSectionProps {
  workflows: Workflow[];
  index?: number;
}

export function PRDWorkflowsSection({ workflows, index = 7 }: PRDWorkflowsSectionProps) {
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
              className="text-brand-600 border-brand-200 dark:text-brand-400 dark:border-brand-700 px-2 py-0.5 rounded-lg bg-brand-50 dark:bg-brand-900/30 w-fit"
            >
              <FileText className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Critical Workflows ({workflows.length})</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              End-to-end user journeys and processes
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
            <CardContent className="px-4 space-y-3 pb-4">
              {workflows.map((workflow, idx) => (
                <div
                  key={idx}
                  className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-start gap-3">
                    <div className="shrink-0 w-8 h-8 rounded-full bg-brand-500 dark:bg-brand-600 text-white flex items-center justify-center text-sm font-bold">
                      {idx + 1}
                    </div>
                    <div className="flex-1 space-y-3">
                      <div className="flex items-start justify-between">
                        <h4 className="font-semibold text-gray-900 dark:text-gray-100">{workflow.workflow_name}</h4>
                        {/* {workflow.is_must_have && (
                          <Badge className="bg-green-500 text-white text-xs">Must Have</Badge>
                        )} */}
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                        {workflow.description}
                      </p>

                      {/* Value Delivered */}
                      <div className="p-3 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700/60">
                        <h5 className="text-xs font-semibold text-brand-700 dark:text-brand-400 mb-1 flex items-center gap-1">
                          <Zap className="w-3 h-3" />
                          Value Delivered
                        </h5>
                        <p className="text-xs text-brand-700 dark:text-brand-200">{workflow.value_delivered}</p>
                      </div>

                      {/* Steps */}
                      <div className="p-3 bg-white dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                        <h5 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1">
                          <ListOrdered className="w-3 h-3" />
                          Workflow Steps
                        </h5>
                        <div className="space-y-2">
                          {workflow.steps.map((step, stepIdx) => (
                            <div key={stepIdx} className="flex items-start gap-2">
                              <div className="shrink-0 w-5 h-5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 flex items-center justify-center text-xs font-medium">
                                {stepIdx + 1}
                              </div>
                              <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed flex-1">
                                {step}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
