"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Send, Loader2 } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useAutoResizeTextarea } from "@/hooks/use-auto-resize-textarea";

interface AI_Input_SearchProps {
  initialValue?: string;
  onSubmit?: (value: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export default function AI_Input_Search({
  initialValue = "",
  onSubmit,
  isLoading = false,
  disabled = false,
  placeholder = "Type your message or answer here...",
  className
}: AI_Input_SearchProps) {
  const [value, setValue] = useState(initialValue);
  const [isFocused, setIsFocused] = useState(false);
  const { textareaRef, adjustHeight } = useAutoResizeTextarea({
    minHeight: 52,
    maxHeight: 200,
  });

  // Debounced submit to prevent excessive API calls
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, 300);

    return () => clearTimeout(timer);
  }, [value]);

  useEffect(() => {
    if (initialValue && initialValue !== value) {
      setValue(initialValue);
      setTimeout(() => {
        if (adjustHeight) {
          adjustHeight();
        }
      }, 100);
    }
  }, [initialValue, adjustHeight]);

  const handleSubmit = useCallback(() => {
    if (!value.trim() || isLoading || disabled) return;
    
    if (onSubmit) {
      onSubmit(value.trim());
    }
    
    setValue("");
    adjustHeight?.(true);
  }, [value, isLoading, disabled, onSubmit, adjustHeight]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const canSubmit = value.trim().length > 0 && !isLoading && !disabled;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "relative w-full max-w-4xl mx-auto",
        className
      )}
    >
      <div
        className={cn(
          "relative flex items-end gap-3 rounded-2xl border bg-white p-3 shadow-sm transition-all duration-200 dark:bg-gray-900",
          isFocused
            ? "border-brand-300 shadow-md ring-2 ring-brand-100 dark:border-brand-600 dark:ring-brand-900/30"
            : "border-gray-200 dark:border-gray-700",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <div className="flex-1 min-w-0">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            disabled={disabled}
            className={cn(
              "min-h-[52px] w-full resize-none border-0 bg-transparent p-0 text-sm placeholder:text-gray-400 focus-visible:ring-0 focus-visible:ring-offset-0 dark:placeholder:text-gray-500",
              "scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent dark:scrollbar-thumb-gray-600"
            )}
            style={{ height: "auto" }}
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={handleSubmit}
            disabled={!canSubmit}
            size="sm"
            className={cn(
              "h-10 w-10 rounded-xl p-0 transition-all duration-200",
              canSubmit
                ? "bg-brand-500 hover:bg-brand-600 text-white shadow-sm"
                : "bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800 dark:text-gray-600"
            )}
            aria-label="Send message"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Loading indicator */}
      {isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute -top-8 left-0 right-0 flex items-center justify-center"
        >
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Processing your message...</span>
          </div>
        </motion.div>
      )}

      {/* Character count for longer messages */}
      {value.length > 100 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute -bottom-6 right-0 text-xs text-gray-400 dark:text-gray-500"
        >
          {value.length} characters
        </motion.div>
      )}
    </motion.div>
  );
}
