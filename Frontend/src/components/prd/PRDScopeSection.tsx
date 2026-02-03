"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Settings, CheckCircle, XCircle, ChevronDown, ChevronRight, Globe, Users, Workflow } from "lucide-react";
import type { Scope } from "@/hooks/usePRD";

interface PRDScopeSectionProps {
  scope: Scope;
  index?: number;
}

export function PRDScopeSection({ scope, index = 3 }: PRDScopeSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  const totalInScope = scope.in_scope.user_segments.length + scope.in_scope.core_flows.length;
  const totalOutScope = scope.out_of_scope.length;

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
              <Settings className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Scope</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              {totalInScope} in-scope items · {totalOutScope} out-of-scope items
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
              {/* In Scope Section */}
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700/60">
                <h4 className="text-sm font-semibold text-green-700 dark:text-green-400 mb-3 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  In Scope
                </h4>

                {/* Geography */}
                <div className="mb-3 p-3 bg-white dark:bg-gray-800/50 rounded-lg border border-green-100 dark:border-green-800">
                  <div className="flex items-center gap-2 mb-1">
                    <Globe className="w-4 h-4 text-green-600 dark:text-green-400" />
                    <span className="text-xs font-semibold text-green-700 dark:text-green-400">Geography</span>
                  </div>
                  <p className="text-sm text-green-700 dark:text-green-200">{scope.in_scope.geography}</p>
                </div>

                {/* User Segments */}
                <div className="mb-3 p-3 bg-white dark:bg-gray-800/50 rounded-lg border border-green-100 dark:border-green-800">
                  <div className="flex items-center gap-2 mb-2">
                    <Users className="w-4 h-4 text-green-600 dark:text-green-400" />
                    <span className="text-xs font-semibold text-green-700 dark:text-green-400">User Segments</span>
                  </div>
                  <div className="space-y-2">
                    {scope.in_scope.user_segments.map((segment, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-sm text-green-700 dark:text-green-200">
                        <span className="shrink-0 w-2 h-2 rounded-full bg-green-500 dark:bg-green-600 mt-1.5" />
                        <span>{segment}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Core Flows */}
                <div className="p-3 bg-white dark:bg-gray-800/50 rounded-lg border border-green-100 dark:border-green-800">
                  <div className="flex items-center gap-2 mb-2">
                    <Workflow className="w-4 h-4 text-green-600 dark:text-green-400" />
                    <span className="text-xs font-semibold text-green-700 dark:text-green-400">Core Flows</span>
                  </div>
                  <div className="space-y-2">
                    {scope.in_scope.core_flows.map((flow, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-sm text-green-700 dark:text-green-200">
                        <span className="shrink-0 w-2 h-2 rounded-full bg-green-500 dark:bg-green-600 mt-1.5" />
                        <span>{flow}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Out of Scope Section */}
              <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700/60">
                <h4 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-3 flex items-center gap-2">
                  <XCircle className="w-4 h-4" />
                  Out of Scope
                </h4>
                <div className="space-y-2">
                  {scope.out_of_scope.map((item, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm text-red-700 dark:text-red-200">
                      <span className="shrink-0 w-2 h-2 rounded-full bg-red-500 dark:bg-red-600 mt-1.5" />
                      <span>{item}</span>
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
