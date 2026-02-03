"use client";

import React from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowLeft, RefreshCw, Play, Loader2, Maximize2, Minimize2, Camera } from "lucide-react";

interface BMCHeaderProps {
  onBack: () => void;
  onGenerate: () => void;
  onContinue: () => void;
  isGenerating: boolean;
  isContinuing?: boolean;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
  onCaptureScreenshot?: () => void;
  isDownloading?: boolean;
}

export const BMCHeader: React.FC<BMCHeaderProps> = ({
  onBack,
  onGenerate,
  onContinue,
  isGenerating,
  isContinuing = false,
  isFullscreen = false,
  onToggleFullscreen,
  onCaptureScreenshot,
  isDownloading = false
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col lg:flex-row items-start lg:items-center justify-between rounded-xl mb-2 p-2 border border-brand-200 dark:border-brand-700 bg-brand-50 dark:bg-brand-900/20"
    >
      <div className="mb-4 lg:mb-0">
        <p className="text-brand-500 dark:text-brand-100 text-sm">
          Comprehensive strategic overview of your business model
        </p>
      </div>
      <div className="flex flex-col sm:flex-row gap-2 w-full lg:w-auto">
        <Button
          onClick={onBack}
          variant="outline"
          className="text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to VPS v2
        </Button>

        <Button 
          onClick={onGenerate} 
          disabled={isGenerating}
          className="bg-green-500 hover:bg-green-600 shadow-sm hover:shadow-xl transition-all duration-200"
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4 mr-2" />
              Regenerate 
            </>
          )}
        </Button>

        {onCaptureScreenshot && (
          <Button
            onClick={onCaptureScreenshot}
            disabled={isDownloading}
            variant="outline"
            size="sm"
            className="flex items-center gap-2 bg-blue-50 hover:bg-blue-100 text-blue-600 border-blue-200 dark:bg-blue-900/20 dark:hover:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800"
          >
            {isDownloading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Capturing...
              </>
            ) : (
              <>
                <Camera className="w-4 h-4" />
                Save as Image
              </>
            )}
          </Button>
        )}

        {onToggleFullscreen && (
          <Button
            onClick={onToggleFullscreen}
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            {isFullscreen ? (
              <>
                <Minimize2 className="w-4 h-4" />
                Exit Fullscreen
              </>
            ) : (
              <>
                <Maximize2 className="w-4 h-4" />
                View Fullscreen
              </>
            )}
          </Button>
        )}


         <Button 
          onClick={onContinue} 
          variant="default"
          disabled={isContinuing}
          className="bg-brand-500 hover:bg-brand-600 shadow-sm hover:shadow-xl transition-all duration-200"
        >
          {isContinuing ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Continuing...
            </>
          ) : (
            <>
              <Play className="w-4 h-4 mr-2" />
              Continue 
            </>
          )}
        </Button>
      </div>
    </motion.div>
  );
};
