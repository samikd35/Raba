"use client";

import React from 'react';
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { AlertCircle, ArrowLeft, RefreshCw, Loader2 } from "lucide-react";

interface HeaderProps {
  isGoingBack: boolean;
  isGenerating: boolean;
  isContinueLoading: boolean;
  onGoBack: () => void;
  onRegenerate: () => void;
  onContinue: () => void;
}

/**
 * Header Component for Solution Critic
 */
export const Header: React.FC<HeaderProps> = ({
  isGoingBack,
  isGenerating,
  isContinueLoading,
  onGoBack,
  onRegenerate,
  onContinue,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4 min-w-0">
          <p className="text-sm text-brand-500 dark:text-brand-400 flex items-center gap-2 px-4 bg-brand-50 dark:bg-brand-900/30 border-brand-200 dark:border-brand-700 py-2 border rounded-lg justify-center whitespace-nowrap">
            <AlertCircle className="w-5 h-5" />
            Review your Solution Critique
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
          <Button 
            onClick={onGoBack} 
            variant="outline" 
            disabled={isGoingBack}
            className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            {isGoingBack ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <ArrowLeft className="w-4 h-4 mr-2" />
            )}
            Back 
          </Button>

          <Button 
            onClick={onRegenerate}
            disabled={isGenerating}
            variant="default" 
            className="bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Regenerate
          </Button>
          
          <Button 
            onClick={onContinue}
            className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isContinueLoading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : null}
            Continue to Vps v2
          </Button>
        </div>
      </div>
    </motion.div>
  );
};

export default Header;
