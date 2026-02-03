"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Lightbulb, ChevronDown, ChevronRight, Briefcase, Link2, Clock } from "lucide-react";
import type { MVPFeatures } from "@/hooks/usePRD";

interface PRDFeaturesSectionProps {
  features: MVPFeatures;
  mustHavesDelay?: number;
  niceToHavesDelay?: number;
}

export function PRDMustHavesSection({ features, index = 5 }: { features: MVPFeatures; index?: number }) {
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
              <Lightbulb className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Must-Have Features ({features.must_haves.length})</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              Core features required for MVP launch
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
              {features.must_haves.map((feature, idx) => (
                <div
                  key={idx}
                  className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-start gap-3">
                    <div className="shrink-0 w-8 h-8 rounded-full bg-green-500 dark:bg-green-600 text-white flex items-center justify-center text-sm font-bold">
                      {idx + 1}
                    </div>
                    <div className="flex-1 space-y-3">
                      <div className="flex items-start justify-between">
                        <h4 className="font-semibold text-gray-900 dark:text-gray-100">{feature.feature_name}</h4>
                        <Badge variant="outline" className="text-xs">{feature.job_type}</Badge>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                        {feature.description}
                      </p>
                      {/* Job Supported */}
                      <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded border border-green-100 dark:border-green-700">
                        <div className="flex items-center gap-1 mb-1">
                          <Briefcase className="w-3 h-3 text-green-600 dark:text-green-400" />
                          <span className="text-xs font-medium text-green-600 dark:text-green-400">Job Supported</span>
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-300">{feature.job_supported}</p>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-2 bg-white dark:bg-gray-900/50 rounded border border-gray-100 dark:border-gray-700">
                          <div className="flex items-center gap-1 mb-1">
                            <Link2 className="w-3 h-3 text-brand-600 dark:text-brand-400" />
                            <span className="text-xs font-medium text-brand-600 dark:text-brand-400">VPC Reference</span>
                          </div>
                          <p className="text-xs text-gray-600 dark:text-gray-300">{feature.vpc_reference}</p>
                        </div>
                        <div className="p-2 bg-white dark:bg-gray-900/50 rounded border border-gray-100 dark:border-gray-700">
                          <div className="flex items-center gap-1 mb-1">
                            <Link2 className="w-3 h-3 text-purple-600 dark:text-purple-400" />
                            <span className="text-xs font-medium text-purple-600 dark:text-purple-400">BMC Reference</span>
                          </div>
                          <p className="text-xs text-gray-600 dark:text-gray-300">{feature.bmc_reference}</p>
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

export function PRDNiceToHavesSection({ features, index = 6 }: { features: MVPFeatures; index?: number }) {
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
              className="text-blue-600 border-blue-200 dark:text-blue-400 dark:border-blue-700 px-2 py-0.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 w-fit"
            >
              <Clock className="w-3 h-3 mr-1" />
              <span className="text-[0.9rem] font-semibold">{index} · Nice-to-Have Features ({features.nice_to_haves.length})</span>
            </Badge>
            <span className="text-sm font-medium text-gray-500 dark:text-brand-200">
              Features deferred for future iterations
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
              {features.nice_to_haves.map((feature, idx) => (
                <div
                  key={idx}
                  className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-start gap-3">
                    <div className="shrink-0 w-8 h-8 rounded-full bg-blue-500 dark:bg-blue-600 text-white flex items-center justify-center text-sm font-bold">
                      {idx + 1}
                    </div>
                    <div className="flex-1 space-y-3">
                      <div className="flex items-start justify-between">
                        <h4 className="font-semibold text-gray-900 dark:text-gray-100">{feature.feature_name}</h4>
                        {feature.job_type && (
                          <Badge variant="outline" className="text-xs">{feature.job_type}</Badge>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                        {feature.description}
                      </p>
                      
                      {/* Job Supported */}
                      <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded border border-purple-100 dark:border-purple-700">
                        <div className="flex items-center gap-1 mb-1">
                          <Briefcase className="w-3 h-3 text-purple-600 dark:text-purple-400" />
                          <span className="text-xs font-medium text-purple-600 dark:text-purple-400">Job Supported</span>
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-300">{feature.job_supported}</p>
                      </div>

                      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700/60">
                        <h5 className="text-xs font-semibold text-blue-700 dark:text-blue-400 mb-1 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Deferral Rationale
                        </h5>
                        <p className="text-xs text-blue-700 dark:text-blue-200">{feature.rationale_for_deferral}</p>
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

export function PRDFeaturesSection({ features, mustHavesDelay = 0.5, niceToHavesDelay = 0.6 }: PRDFeaturesSectionProps) {
  return (
    <>
      <PRDMustHavesSection features={features} />
      <PRDNiceToHavesSection features={features} />
    </>
  );
}
