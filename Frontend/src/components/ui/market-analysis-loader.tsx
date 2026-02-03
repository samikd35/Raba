"use client";
import { cn } from "@/lib/utils";
import { AnimatePresence, motion } from "motion/react";
import { useState, useEffect, useRef, useMemo } from "react";
import { X, Loader2 } from "lucide-react";

const CheckIcon = ({ className }: { className?: string }) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2}
      stroke="currentColor"
      className={cn("w-5 h-5", className)}
    >
      <path d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
};

type LoadingState = {
  text: string;
  description?: string;
};

const LoaderCore = ({
  loadingStates,
  value = 0,
  progressPercent,
}: {
  loadingStates: LoadingState[];
  value?: number;
  progressPercent: number;
}) => {
  return (
    <div className="w-full max-w-md mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-brand-500 dark:text-white">
          Market Findings Analysis
        </h2>
       
      </div>

      {/* Progress Steps */}
      <div className="space-y-2">
        {loadingStates.map((loadingState, index) => {
          const isCompleted = index < value;
          const isCurrent = index === value;
          const isPending = index > value;

          return (
            <motion.div
              key={index}
              className="flex items-start gap-4"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              {/* Step Icon */}
              <div className="flex-shrink-0 mt-1">
                {isCompleted && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    className="w-6 h-6 rounded-full bg-brand-500 flex items-center justify-center"
                  >
                    <CheckIcon className="text-white w-4 h-4" />
                  </motion.div>
                )}
                
                {isCurrent && (
                  <motion.div
                    className="w-6 h-6 rounded-full border-2 border-brand-500 bg-white dark:bg-gray-900 flex items-center justify-center"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  >
                    <div className="w-2 h-2 rounded-full bg-brand-500" />
                  </motion.div>
                )}
                
                {isPending && (
                  <div className="w-6 h-6 rounded-full border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900" />
                )}
              </div>

              {/* Step Content */}
              <div className="flex-1 min-w-0">
                <h3 className={cn(
                  "font-semibold text-md leading-tight",
                  isCompleted && "text-gray-900 dark:text-white",
                  isCurrent && "text-brand-500",
                  isPending && "text-gray-500 dark:text-gray-400"
                )}>
                  {loadingState.text}
                </h3>
                {/* {loadingState.description && (
                  <p className={cn(
                    "text-sm mt-1 leading-relaxed",
                    isCompleted && "text-gray-600 dark:text-gray-300",
                    isCurrent && "text-gray-700 dark:text-gray-300",
                    isPending && "text-gray-400 dark:text-gray-500"
                  )}>
                    {loadingState.description}
                  </p>
                )} */}
              </div>

              {/* Loading Spinner for Current Step */}
              {isCurrent && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex-shrink-0 mt-1"
                >
                  <Loader2 className="w-4 h-4 text-brand-500 animate-spin" />
                </motion.div>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Progress Bar */}
      <div className="mt-8">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Progress
          </span>
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            {Math.round(progressPercent)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <motion.div
            className="bg-brand-500 h-2 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.5, ease: "easeInOut" }}
          />
        </div>
      </div>
    </div>
  );
};

export const MarketAnalysisLoader = ({
  loadingStates,
  loading,
  onCancel,
  totalDuration = 1 * 30 * 1000, 
}: {
  loadingStates: LoadingState[];
  loading?: boolean;
  onCancel?: () => void;
  totalDuration?: number; // in milliseconds
}) => {
  const [currentState, setCurrentState] = useState(0);
  const [progressPercent, setProgressPercent] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  
  const startTimeRef = useRef<number>(0);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const animationFrameRef = useRef<number>(0);

  // Memoized progress milestones to prevent recalculation on every render
  const progressMilestones = useMemo(() => {
    if (loadingStates.length === 0) return [];
    
    const steps = loadingStates.length;
    const milestones = [] as Array<{ progress: number; time: number; state: number }>;
    
    // Handle single-step gracefully
    if (steps === 1) {
      milestones.push({ progress: 100, time: totalDuration, state: 0 });
      return milestones;
    }
    
    // Create evenly distributed milestones based on number of steps
    for (let i = 0; i < steps; i++) {
      const progress = (i / (steps - 1)) * 100;
      const time = (i / (steps - 1)) * totalDuration;
      milestones.push({
        progress,
        time,
        state: i
      });
    }
    
    return milestones;
  }, [loadingStates.length, totalDuration]);

  // Reset state when loading becomes false
  useEffect(() => {
    if (!loading) {
      setCurrentState(0);
      setProgressPercent(0);
      setIsComplete(false);
      
      // Clear any existing intervals
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    }
  }, [loading]);

  // Start progress simulation when loading becomes true
  useEffect(() => {
    if (!loading || isComplete) return;

    // Initialize progress tracking
    startTimeRef.current = Date.now();
    setCurrentState(0);
    setProgressPercent(0);

    if (process.env.NODE_ENV === 'development') {
      console.log('🔄 MultiStepLoader started:', {
        totalDuration,
        loadingStatesCount: loadingStates.length,
        milestones: progressMilestones
      });
    }

    const updateProgress = () => {
      const now = Date.now();
      const elapsed = now - startTimeRef.current;
      
      // Calculate progress percentage based on elapsed time
      const rawProgress = Math.min((elapsed / totalDuration) * 100, 100);
      setProgressPercent(rawProgress);

      // Advance to the furthest milestone reached so far
      let reachedState = 0;
      for (let i = 0; i < progressMilestones.length; i++) {
        if (rawProgress >= progressMilestones[i].progress) {
          reachedState = progressMilestones[i].state;
        } else {
          break;
        }
      }
      setCurrentState(reachedState);

      if (process.env.NODE_ENV === 'development' && elapsed % 500 < 100) {
        console.log('📊 Progress update:', {
          elapsed,
          totalDuration,
          rawProgress: rawProgress.toFixed(2),
          reachedState,
          currentState: reachedState
        });
      }

      // Check if completed
      if (elapsed >= totalDuration) {
        setIsComplete(true);
        setProgressPercent(100);
        setCurrentState(loadingStates.length - 1);
        
        if (process.env.NODE_ENV === 'development') {
          console.log('✅ MultiStepLoader completed');
        }
        
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
        }
      }
    };

    // Use requestAnimationFrame for smoother progress updates
    const animateProgress = () => {
      updateProgress();
      if (!isComplete && loading) {
        animationFrameRef.current = requestAnimationFrame(animateProgress);
      }
    };

    // Start the animation
    animateProgress();

    // Fallback: also update via interval to ensure progress continues
    progressIntervalRef.current = setInterval(updateProgress, 100);

    // Cleanup function
    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [loading, isComplete, totalDuration, progressMilestones, loadingStates.length]);

  // Handle completion
  useEffect(() => {
    if (isComplete && progressPercent >= 100) {
      // Optional: Add a small delay before auto-closing or showing completion
      const timer = setTimeout(() => {
        // You could auto-close here or show a completion state
        console.log('Process completed');
      }, 1000);

      return () => clearTimeout(timer);
    }
  }, [isComplete, progressPercent]);

  const handleCancel = () => {
    // Clean up intervals and animation frames
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    if (onCancel) {
      onCancel();
    } else {
      window.location.reload();
    }
  };

  // Don't render if no loading states
  if (!loadingStates || loadingStates.length === 0) {
    return null;
  }

  return (
    <AnimatePresence mode="wait">
      {loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 p-8 m-4 w-full max-w-lg"
          >
            <button
              onClick={handleCancel}
              className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors rounded-full hover:bg-gray-100 dark:hover:bg-gray-800"
              aria-label="Cancel process"
            >
              <X className="w-5 h-5" />
            </button>

            <LoaderCore 
              value={currentState} 
              loadingStates={loadingStates} 
              progressPercent={progressPercent} 
            />

            <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={handleCancel}
                className="w-full px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                Cancel Process
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};