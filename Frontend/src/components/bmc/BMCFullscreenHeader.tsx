"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { ArrowLeft, RefreshCw, Play, Loader2, Minimize2, Edit2, Eye } from "lucide-react";

interface BMCFullscreenHeaderProps {
  onBack: () => void;
  onGenerate: () => void;
  onContinue: () => void;
  onToggleFullscreen: () => void;
  isGenerating: boolean;
  isContinuing?: boolean;
  projectName?: string;
  // Edit mode props
  isEditMode?: boolean;
  onToggleEditMode?: () => void;
  isEditing?: boolean;
}

export const BMCFullscreenHeader: React.FC<BMCFullscreenHeaderProps> = ({
  onBack,
  onGenerate,
  onContinue,
  onToggleFullscreen,
  isGenerating,
  isContinuing = false,
  projectName = '',
  isEditMode = false,
  onToggleEditMode,
  isEditing = false
}) => {
  return (
    <div className="grid grid-cols-3 md:flex-row md:items-center md:justify-between gap-3 mb-1 pb-4 border-b border-gray-200 dark:border-gray-700">
      <div className="min-w-0 flex items-center gap-3">
        <h1 className="text-xl font-semibold text-brand-500 dark:text-white truncate">
          Business Model Canvas v2 - {projectName || 'Untitled Project'}
        </h1>
        
      </div>
      
      <div className="flex-1 flex justify-center">
        {/* Edit mode toggle button in center */}
        {onToggleEditMode && (
          <Button
            onClick={onToggleEditMode}
            variant="default"
            size="sm"
            disabled={isEditing}
            className={`flex items-center gap-2 w-64  ${
              isEditMode 
                ? "bg-green-500 hover:bg-green-600 text-white" 
                : "bg-green-500 hover:bg-green-600 text-white"
            }`}
          >
            {isEditMode ? (
              <>
                <Eye className="w-4 h-4" />
                Exit Edit Mode
              </>
            ) : (
              <>
                <Edit2 className="w-4 h-4" />
                Edit Canvas
              </>
            )}
          </Button>
        )}
      </div>
      
      <div className="flex justify-end gap-2 items-center">

        <Button
          onClick={onBack}
          variant="outline"
          size="sm"
          className="flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to VPS v2
        </Button>

        <Button 
          onClick={onGenerate} 
          disabled={isGenerating}
          size="sm"
          className="bg-brand-500 hover:bg-brand-600 transition-all duration-200"
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

       

        <Button
          onClick={onToggleFullscreen}
          variant="outline"
          size="sm"
          className="flex items-center gap-2"
        >
          <Minimize2 className="w-4 h-4" />
          Exit Fullscreen
        </Button>

         <Button 
          onClick={onContinue} 
          variant="default" 
          size="sm"
          disabled={isContinuing}
          className="bg-brand-500 hover:bg-brand-600 shadow-lg hover:shadow-xl transition-all duration-200"
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
    </div>
  );
};
