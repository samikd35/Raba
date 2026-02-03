"use client";

import { CheckCircle, AlertCircle, Loader2, CreditCard } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Textarea } from "@/components/ui/textarea";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useAutoResizeTextarea } from "@/hooks/use-auto-resize-textarea";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/authStore";
import { refineIdea, validateIdeaInput, IdeaRefinementResponse } from "@/lib/api/ideaRefinement";
import toast from 'react-hot-toast';
import { InsufficientCreditsModal } from "@/components/common/InsufficientCreditsModal";

interface IdeaRefinerInputProps {
  initialValue?: string;
  path : string
}

export default function IdeaRefinerInput({ initialValue = "", path }: IdeaRefinerInputProps) {
  const [value, setValue] = useState(initialValue);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isInsufficientCreditsModalOpen, setIsInsufficientCreditsModalOpen] = useState(false);
  const { textareaRef, adjustHeight } = useAutoResizeTextarea({
    minHeight: 52,
    maxHeight: 200,
  });
  const [isFocused, setIsFocused] = useState(false);
  const { user, token, isAuthenticated } = useAuthStore();
  const router = useRouter();

  // Constants for better maintainability
  const MIN_TEXTAREA_HEIGHT = 52;
  const MAX_TEXTAREA_HEIGHT = 200;
  const REDIRECT_DELAY_MS = 500;
  const MIN_CHARACTERS = 10;
  const MIN_WORDS = 3;

  // Custom validation function
  const validateInput = useCallback((input: string) => {
    const trimmedInput = input.trim();

    if (!trimmedInput) {
      return { isValid: false, error: 'Please enter your idea' };
    }

    if (trimmedInput.length < MIN_CHARACTERS) {
      return {
        isValid: false,
        error: `Your idea must be at least ${MIN_CHARACTERS} characters long (currently ${trimmedInput.length})`
      };
    }

    const wordCount = trimmedInput.split(/\s+/).filter(word => word.length > 0).length;
    if (wordCount < MIN_WORDS) {
      return {
        isValid: false,
        error: `Your idea must contain at least ${MIN_WORDS} words (currently ${wordCount})`
      };
    }

    return { isValid: true, error: null };
  }, [MIN_CHARACTERS, MIN_WORDS]);

  // Check if input meets minimum requirements
  const inputValidation = validateInput(value);
  const isInputValid = inputValidation.isValid;

  // Calculate character and word count
  const characterCount = value.length;
  const wordCount = value.trim().split(/\s+/).filter(word => word.length > 0).length;

  // Update value when initialValue changes
  useEffect(() => {
    if (initialValue && initialValue !== value) {
      setValue(initialValue);
      setError(null);
      adjustHeight();
    }
  }, [initialValue, adjustHeight]);

  const handleSubmit = useCallback(async () => {
    // Clear previous errors
    setError(null);

    // Validate input
    const validation = validateIdeaInput(value);
    if (!validation.isValid) {
      setError(validation.error || 'Invalid input');
      return;
    }

    // Check authentication
    if (!isAuthenticated || !user) {
      setError('Please log in to refine your idea');
      return;
    }

    // Get auth token from Zustand store
    if (!token) {
      setError('Authentication required. Please log in again.');
      return;
    }

    setIsLoading(true);

    try {
      const response: IdeaRefinementResponse = await refineIdea(value, token);

      console.log(`idea refiner responseeeeeeeeee`,response)

      // Show success state briefly before redirecting
      setIsLoading(false);
      setIsSuccess(true);

      // Redirect after short delay to show success state
      setTimeout(() => {
        router.push(`${path}/idea-refiner/results/${response.session_id}`);
      }, REDIRECT_DELAY_MS);

    } catch (err) {
      console.error('Error refining idea:', err);

      // Check if it's an IdeaRefinementError with 402 status (insufficient credits)
      if (err && typeof err === 'object' && 'status' in err && err.status === 402) {
        setIsInsufficientCreditsModalOpen(true);
      } else {
        const message = err instanceof Error ? err.message : String(err) || 'Failed to refine idea. Please try again.';
        setError(message);
      }
      setIsLoading(false);
    }
  }, [value, isAuthenticated, user, token, router]);

  const handleFocus = useCallback(() => {
    setIsFocused(true);
  }, []);

  const handleBlur = useCallback(() => {
    setIsFocused(false);
  }, []);

  const handleContainerClick = useCallback(() => {
    if (textareaRef.current && !isLoading && !isSuccess) {
      textareaRef.current.focus();
    }
  }, [textareaRef, isLoading, isSuccess]);

  const handleTryAgain = useCallback(() => {
    setError(null);
    setIsSuccess(false);
  }, []);

  return (
    <div className="w-full py-4">
      <div className="relative max-w-[630px] w-full mx-auto">
        <div
          tabIndex={0}
          aria-label="Idea input container"
          className={cn(
            "relative flex flex-col rounded-xl transition-all duration-200 w-full text-left cursor-text",
            "ring-1 ring-black/10 dark:ring-white/10",
            isFocused && "ring-black/20 dark:ring-white/20"
          )}
          onClick={handleContainerClick}
        >
          <div className="overflow-y-auto max-h-[200px]">
            <Textarea
              id="ai-input-04"
              value={value}
              placeholder="Start typing your idea..."
              className="w-full rounded-xl rounded-b-none px-4 py-3 bg-brand-25 dark:bg-[#101828] border-none dark:text-white placeholder:text-black/70 dark:placeholder:text-white/70 resize-none focus-visible:ring-0 leading-[1.2]"
              ref={textareaRef}
              onFocus={handleFocus}
              onBlur={handleBlur}
              disabled={isLoading || isSuccess}
              aria-describedby={error ? "error-message" : undefined}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              onChange={(e) => {
                setValue(e.target.value);
                adjustHeight();
                // Clear error when user starts typing
                if (error) setError(null);
              }}
            />
          </div>

          <div className="h-12 bg-brand-25 dark:bg-[#101828] rounded-b-xl">
            {/* Character and word count display */}
            <div className="absolute left-3 bottom-3 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
              <span className={cn(
                "transition-colors",
                characterCount >= MIN_CHARACTERS ? "text-green-600 dark:text-green-400" : "text-gray-500 dark:text-gray-400"
              )}>
                {characterCount}/{MIN_CHARACTERS} chars
              </span>
              <span className={cn(
                "transition-colors",
                wordCount >= MIN_WORDS ? "text-green-600 dark:text-green-400" : "text-gray-500 dark:text-gray-400"
              )}>
                {wordCount}/{MIN_WORDS} words
              </span>
            </div>

            <div className="absolute right-3 bottom-3">
              <Button
                variant="default"
                onClick={handleSubmit}
                disabled={isLoading || isSuccess || !isInputValid || !isAuthenticated}
                className="flex items-center gap-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Predicting...
                  </>
                ) : isSuccess ? (
                  <>
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    Redirecting...
                  </>
                ) : (
                  'Predict the Problem'
                )}
              </Button>
            </div>
          </div>
        </div>

        {/* Success Display */}
        <AnimatePresence>
          {isSuccess && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg"
              aria-live="polite"
            >
              <div className="flex items-center gap-3">
                <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
                <p className="text-green-700 dark:text-green-300 text-sm">
                  Idea refined successfully! Redirecting to results...
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error Display */}
        <AnimatePresence>
          {error && (
            <motion.div
              id="error-message"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
              aria-live="polite"
            >
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-red-700 dark:text-red-300 text-sm">{error}</p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Insufficient Credits Modal */}
        <InsufficientCreditsModal
          isOpen={isInsufficientCreditsModalOpen}
          onClose={() => setIsInsufficientCreditsModalOpen(false)}
        />
      </div>
    </div>
  );
}