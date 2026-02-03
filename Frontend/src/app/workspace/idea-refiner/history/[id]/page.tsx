"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Target } from "lucide-react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb2";
import { Button } from "@/components/ui/button";
import { IdeaRefinementResponse, ProblemStatement, RefinementHistoryResponse, getRefinementHistory } from "@/lib/api/ideaRefinement";
import { useParams } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";

export default function IdeaRefinementResults() {
  const [session, setSession] = useState<RefinementHistoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const params = useParams();
  const { user, token, isAuthenticated } = useAuthStore();

  // Constants for maintainability - memoized to prevent recreation
  const constants = useMemo(() => ({
    ANIMATION_DELAY_BASE: 0.5,
    ANIMATION_DELAY_INCREMENT: 0.1,
    REFINER_ROUTE: '/workspace/idea-refiner',
    VALIDATOR_ROUTE: '/workspace/problem-validator',
    STORAGE_KEYS: {
      VALIDATION_DATA: 'marketValidationData'
    }
  }), []);

  // Single effect for data fetching from backend
  useEffect(() => {
    let isMounted = true;
    const abortController = new AbortController();

    const fetchSessionData = async () => {
      if (!isMounted) return;

      // Check authentication
      if (!isAuthenticated || !user || !token) {
        if (process.env.NODE_ENV === 'development') {
          console.log("❌ User not authenticated, redirecting to signin");
        }
        router.push('/signin');
        return;
      }

      // Get session ID from URL parameters
      const sessionId = params?.id as string;

      if (!sessionId) {
        if (process.env.NODE_ENV === 'development') {
          console.log("❌ No session ID provided in URL");
        }
        if (isMounted) {
          setError('Session ID is required to view refinement results.');
          setIsLoading(false);
        }
        return;
      }

      try {
        if (process.env.NODE_ENV === 'development') {
          console.log("🔍 Fetching session data:", { sessionId });
        }

        const sessionData = await getRefinementHistory(
          sessionId,
          token,
        );

        if (isMounted) {
          setSession(sessionData);
          setError(null);
          
          if (process.env.NODE_ENV === 'development') {
            console.log("✅ Session data loaded successfully:", {
              sessionId: sessionData.session_id,
              problemCount: sessionData.session.problem_statements.length,
              originalIdea: sessionData.session.original_idea.substring(0, 50) + "...",
              status: sessionData.session.status,
              averageScore: sessionData.session.metadata.average_score
            });
          }
        }
      } catch (err: any) {
        console.error('Error fetching session data:', err);
        
        if (isMounted) {
          if (err.status === 404) {
            setError('Refinement session not found. It may have been deleted or the session ID is incorrect.');
          } else if (err.status === 401 || err.status === 403) {
            setError('Authentication failed. Please log in again.');
            // Redirect to signin after a delay
            setTimeout(() => router.push('/signin'), 2000);
          } else {
            setError(err.message || 'Failed to load refinement results. Please try again.');
          }
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    // Fetch data immediately
    fetchSessionData();

    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, [isAuthenticated, user, token, router, params]);

  const handleBackToRefiner = useCallback(() => {
    const { REFINER_ROUTE } = constants;
    router.push(REFINER_ROUTE);
  }, [router, constants]);

  const handleProblemStatementClick = useCallback((statement: ProblemStatement, index: number) => {
    if (!session) return;
    
    const validationData = {
      selectedProblemStatement: statement,
      problemIndex: index,
      originalIdea: session.session.original_idea,
      contextAnalysis: session.session.parsed_context,
      sessionId: session.session_id,
      allProblemStatements: session.session.problem_statements
    };
    
    try {
      sessionStorage.setItem(constants.STORAGE_KEYS.VALIDATION_DATA, JSON.stringify(validationData));
      router.push(constants.VALIDATOR_ROUTE);
    } catch (storageError) {
      console.error('Failed to store validation data:', storageError);
      setError('Failed to prepare validation data. Please try again.');
    }
  }, [session, router, constants]);

  // Memoized problem statements list to prevent unnecessary re-renders
  const problemStatementsList = useMemo(() => {
    if (!session?.session?.problem_statements?.length) return null;

    return session.session.problem_statements.map((statement, index) => (
      <motion.div
        key={`problem-${index}-${statement.statement.substring(0, 30)}`} // Better key with index and content
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ 
          delay: constants.ANIMATION_DELAY_BASE + index * constants.ANIMATION_DELAY_INCREMENT 
        }}
        role="button"
        tabIndex={0}
        aria-label={`Select problem statement ${index + 1} for ${statement.stakeholder}`}
        className="p-6 bg-white dark:bg-[#101828] border border-gray-200 dark:border-gray-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 group dark:hover:bg-brand-700/50 transition-all duration-200 cursor-pointer relative focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-opacity-50"
        onClick={() => handleProblemStatementClick(statement, index)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleProblemStatementClick(statement, index);
          }
        }}
      >
        {/* Clickable Indicator */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span 
              className="inline-block px-4 py-2 text-sm font-semibold bg-brand-100 dark:bg-brand-800 text-brand-700 dark:text-brand-200 rounded-full"
              aria-label={`Problem for ${statement.stakeholder}`}
            >
              Problem #{index + 1}: {statement.stakeholder}
            </span>
           
          </div>
          <Button 
            className="flex items-center gap-2 bg-brand-500 text-white dark:bg-brand-500/50 dark:text-brand-200 border border-brand-200 dark:border-brand-800 p-2 rounded-lg px-4 transition-all ease-in-out group-hover:gap-4 group-hover:scale-105 hover:bg-brand-800 dark:hover:bg-brand-800 focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            onClick={(e) => {
              e.stopPropagation();
              handleProblemStatementClick(statement, index);
            }}
            aria-label={`Validate problem statement ${index + 1}`}
          >
            <span className="text-sm font-medium">Validate this problem</span>
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
        
        {/* Problem Statement */}
        <div className="mb-4">
          <h4 className="text-lg font-semibold text-brand-500 dark:text-brand-100 mb-2">
            Problem Statement
          </h4>
          <p className="text-brand-700 dark:text-brand-200 leading-relaxed text-sm bg-brand-50 dark:bg-brand-700/50 p-4 rounded-lg border border-brand-200 dark:border-brand-800 transition-colors">
            {statement.statement}
          </p>
        </div>
        
        {/* Assumptions */}
        {statement.assumptions && statement.assumptions.length > 0 && (
          <div>
            <h5 className="font-semibold text-brand-500 dark:text-brand-100 mb-3 text-base">
              Key Assumptions to Validate:
            </h5>
            <div className="grid gap-2">
              {statement.assumptions.map((assumption, assumptionIndex) => (
                <div
                  key={assumptionIndex}
                  className="flex items-start gap-2 p-2 bg-brand-25 dark:bg-brand-700/30 rounded-lg group-hover:bg-brand-25 dark:group-hover:bg-brand-700/50 transition-colors"
                >
                  <div 
                    className="flex-shrink-0 w-6 h-6 bg-brand-500 text-white rounded-full flex items-center justify-center text-xs font-bold mt-0.5"
                    aria-hidden="true"
                  >
                    {assumptionIndex + 1}
                  </div>
                  <p className="text-brand-600 dark:text-brand-200 leading-relaxed text-md">
                    {assumption}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Hover Overlay */}
        <div 
          className="absolute inset-0 bg-brand-500/5 dark:bg-brand-400/5 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" 
          aria-hidden="true"
        />
      </motion.div>
    ));
  }, [session, handleProblemStatementClick, constants]);

  // Early return for error state
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center" role="alert" aria-live="polite">
        <div className="text-center p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg max-w-md">
          <p className="text-red-700 dark:text-red-300 text-sm mb-4">{error}</p>
          <Button 
            onClick={() => router.push(constants.REFINER_ROUTE)}
            className="bg-red-600 hover:bg-red-700 text-white"
          >
            Go Back to Refiner
          </Button>
        </div>
      </div>
    );
  }

  // Early return for loading state
  if (isLoading || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center" role="status" aria-live="polite">
        <div className="text-center">
          <div 
            className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 mx-auto mb-4" 
            aria-hidden="true"
          />
          <p className="text-gray-600 dark:text-gray-400">Loading results...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col overflow-x-hidden ">
      <PageBreadcrumb pageTitle="Idea Refinement Results" />
      
      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-[#101828]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-6xl mx-auto"
        >
          {/* Original Idea Display */}
          {session?.session?.original_idea && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="mb-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700"
            >
              <h3 className="text-lg font-semibold text-brand-500 dark:text-gray-200 mb-2 flex items-center gap-2">
                <Target className="h-5 w-5 text-brand-500 dark:text-brand-200" aria-hidden="true" />
                Your Original Idea
              </h3>
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed text-sm">
                {session.session.original_idea}
              </p>
              
              
            </motion.div>
          )}

          {/* Problem Statements */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-100 text-center mb-1">
              Refined Problem Statements
              <span className="ml-2 text-lg font-medium text-brand-500 dark:text-brand-300">
                ({session.session.problem_statements.length} identified)
              </span>
            </h2>

            <p className="text-md text-gray-600 dark:text-gray-400 max-w-2xl mx-auto mb-4 text-center">
              Select the problem statement that best captures your idea
            </p>
            
            <div className="space-y-4" role="list" aria-label="List of refined problem statements">
              {problemStatementsList}
            </div>
          </motion.div>

          {/* Action Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="flex flex-col sm:flex-row gap-4 justify-center pt-8"
          >
            <Button
              variant="outline"
              onClick={handleBackToRefiner}
              className="flex items-center gap-2 px-16 py-3 bg-brand-50 dark:bg-brand-700/50 border border-brand-200 dark:border-brand-800 text-brand-500 dark:text-brand-200 hover:bg-brand-100 dark:hover:bg-brand-700 focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
              size="lg"
            >
              <ArrowLeft className="h-5 w-5" aria-hidden="true" />
              
              Predict Another Idea
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}