"use client";

import React from "react";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { PRDMetadata } from "@/hooks/usePRD";

interface PRDMetadataFooterProps {
  metadata: PRDMetadata;
  validationStatus: string;
  delay?: number;
}

export function PRDMetadataFooter({ metadata, validationStatus, delay = 0.8 }: PRDMetadataFooterProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
    >
      <Card className="bg-gray-50 dark:bg-gray-900">
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-600 dark:text-gray-400">Template</p>
              <p className="font-medium text-gray-900 dark:text-gray-100">{metadata.template_name}</p>
            </div>
            <div>
              <p className="text-gray-600 dark:text-gray-400">Version</p>
              <p className="font-medium text-gray-900 dark:text-gray-100">{metadata.template_version}</p>
            </div>
            <div>
              <p className="text-gray-600 dark:text-gray-400">Generated</p>
              <p className="font-medium text-gray-900 dark:text-gray-100">
                {new Date(metadata.generated_at).toLocaleDateString()}
              </p>
            </div>
            <div>
              <p className="text-gray-600 dark:text-gray-400">Status</p>
              <Badge variant={validationStatus === "valid" ? "default" : "destructive"}>
                {validationStatus}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
