"use client";

import React from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, ArrowLeft, Check, X, Loader2, Pencil, RefreshCw, CheckCircle, XCircle } from "lucide-react";

interface PRDHeaderProps {
  validationStatus: string;
  version: number;
  isEditing: boolean;
  isSaving: boolean;
  isRegenerating: boolean;
  isBackLoading: boolean;
  isContinueLoading: boolean;
  onBack: () => void;
  onEditToggle: () => void;
  onSave: () => void;
  onRegenerate: () => void;
  onGeneratePRD?: () => void;
  onContinue: () => void;
  backLabel?: string;
  continueLabel?: string;
  showGenerateOption?: boolean;
}

export function PRDHeader({
  validationStatus,
  version,
  isEditing,
  isSaving,
  isRegenerating,
  isBackLoading,
  isContinueLoading,
  onBack,
  onEditToggle,
  onSave,
  onRegenerate,
  onGeneratePRD,
  onContinue,
  backLabel = "Back to projects",
  continueLabel = "Continue to next step",
  showGenerateOption = false,
}: PRDHeaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center justify-between p-2 bg-brand-25 border border-brand-100 rounded-lg dark:bg-gray-800 dark:border-gray-600">
        <div className="flex items-center gap-4">
          <p className="text-sm text-brand-500 dark:text-gray-400 flex items-center gap-2 px-4 bg-brand-50 dark:bg-gray-800 border-gray-200 dark:border-gray-600 py-2 border rounded-lg justify-center">
            <AlertCircle className="w-5 h-5" />
            Review your Product Requirement Detail
          </p>
         
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={onBack}
            variant="outline"
            disabled={isBackLoading}
            className="border-brand-300 dark:border-brand-600 text-brand-700 dark:text-brand-200 hover:bg-brand-50 dark:hover:bg-brand-800"
          >
            {isBackLoading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <ArrowLeft className="w-4 h-4 mr-2" />
            )}
            {backLabel}
          </Button>

          {/* Edit/Save/Cancel Buttons */}
          {/* {isEditing ? (
            <>
              <Button
                onClick={onSave}
                disabled={isSaving}
                className="bg-green-600 hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700"
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                Save Changes
              </Button>
              <Button
                onClick={onEditToggle}
                variant="outline"
                className="border-red-300 dark:border-red-600 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/40"
              >
                <X className="w-4 h-4 mr-2" />
                Cancel
              </Button>
            </>
          ) : (
            <Button
              onClick={onEditToggle}
              variant="outline"
              disabled={isRegenerating}
              className="border-brand-300 dark:border-brand-600 text-brand-600 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-800/50"
            >
              <Pencil className="w-4 h-4 mr-2" />
              Edit
            </Button>
          )} */}

          {showGenerateOption && onGeneratePRD ? (
            <Button
              onClick={onGeneratePRD}
              variant="default"
              disabled={isRegenerating || isEditing}
              className="bg-green-600 hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Generate PR
            </Button>
          ) : (
            <Button
              onClick={onRegenerate}
              variant="default"
              disabled={isRegenerating || isEditing}
              className="bg-green-600 hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRegenerating ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              Regenerate
            </Button>
          )}

          <Button
            onClick={onContinue}
            disabled={isContinueLoading || isEditing}
            className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-600 dark:hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isContinueLoading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <ArrowLeft className="w-4 h-4 mr-2 rotate-180" />
            )}
            {continueLabel}
          </Button>
        </div>
      </div>
    </motion.div>
  );
}
