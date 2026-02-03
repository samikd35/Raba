"use client";

import React, { useEffect, useState, useRef, useReducer } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, AlertCircle, RefreshCw, User, Brain, CheckCircle, Lightbulb } from "lucide-react";
import toast from "react-hot-toast";

// Components
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import AI_Input_Search from "@/components/AI_Input_Search";
import { MultiStepLoader } from "@/components/ui/multi-step-loader";
import CreditCostBadge from "@/components/common/CreditCostBadge";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { InsufficientCreditsModal } from "@/components/common/InsufficientCreditsModal";

// Stores & Libs
import { useAuthStore } from "@/stores/authStore";
import {
  startWorkflow,
  submitAnswers,
  getReport,
  pollWorkflowStatus,
  WorkflowAPIError
} from "@/lib/api/workflow";

// Types
import {
  ChatMessage,
  ClarificationQuestion,
  ReportResponse
} from "@/types/validation";

// --- Types & Reducer ---

type WorkflowStatus =
  | "idle"
  | "starting"
  | "waiting_for_clarification"
  | "processing"
  | "completed"
  | "error";

interface WorkflowState {
  status: WorkflowStatus;
  sessionId: string | null;
  progress: number;
  questions: ClarificationQuestion[];
  currentQuestionIndex: number;
  answers: Record<string, string>;
  report: ReportResponse | null;
  error: string | null;
  progressDetails: string | null;
  isInsufficientCreditsModalOpen: boolean;
}

type Action =
  | { type: 'RESET' }
  | { type: 'START_INIT' }
  | { type: 'START_SUCCESS'; payload: { sessionId: string; progress: number } }
  | { type: 'SET_QUESTIONS'; payload: ClarificationQuestion[] }
  | { type: 'ANSWER_QUESTION'; payload: { id: string; answer: string } }
  | { type: 'SUBMIT_ANSWERS_INIT' }
  | { type: 'UPDATE_PROGRESS'; payload: { progress: number; details?: string } }
  | { type: 'COMPLETE'; payload: ReportResponse }
  | { type: 'ERROR'; payload: string }
  | { type: 'INSUFFICIENT_CREDITS' };

const initialState: WorkflowState = {
  status: "idle",
  sessionId: null,
  progress: 0,
  questions: [],
  currentQuestionIndex: 0,
  answers: {},
  report: null,
  error: null,
  progressDetails: null,
  isInsufficientCreditsModalOpen: false,
};

function workflowReducer(state: WorkflowState, action: Action): WorkflowState {
  switch (action.type) {
    case 'RESET':
      return initialState;
    case 'START_INIT':
      return { ...initialState, status: 'starting' };
    case 'START_SUCCESS':
      return { ...state, sessionId: action.payload.sessionId, progress: action.payload.progress };
    case 'SET_QUESTIONS':
      return {
        ...state,
        status: 'waiting_for_clarification',
        questions: action.payload,
        currentQuestionIndex: 0
      };
    case 'ANSWER_QUESTION':
      return {
        ...state,
        answers: { ...state.answers, [action.payload.id]: action.payload.answer },
        currentQuestionIndex: state.currentQuestionIndex + 1
      };
    case 'SUBMIT_ANSWERS_INIT':
      return { ...state, status: 'processing', progress: 0, progressDetails: "Analyzing answers..." };
    case 'UPDATE_PROGRESS':
      return {
        ...state,
        progress: action.payload.progress,
        progressDetails: action.payload.details || state.progressDetails
      };
    case 'COMPLETE':
      return { ...state, status: 'completed', report: action.payload, progress: 100 };
    case 'ERROR':
      return { ...state, status: 'error', error: action.payload };
    case 'INSUFFICIENT_CREDITS':
      return { ...state, status: 'error', isInsufficientCreditsModalOpen: true };
    default:
      return state;
  }
}

// --- Animation Variants ---

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: { y: 0, opacity: 1, transition: { type: "spring", stiffness: 100 } },
  exit: { opacity: 0, transition: { duration: 0.2 } }
};

export default function ProblemValidator() {
  // --- State & Refs ---
  const [state, dispatch] = useReducer(workflowReducer, initialState);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [initialInput, setInitialInput] = useState<string>("");
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isRedirecting, setIsRedirecting] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { user, token, isAuthenticated } = useAuthStore();
  const router = useRouter();

  // Loading states for MultiStepLoader
  const loadingStates = [
    { text: "Domain Specification", description: "Understanding and framing the user's research domain and core objective." },
    { text: "Keyword Expansion", description: "Generating and expanding relevant keywords based on user input." },
    { text: "Industry Analysis", description: "Identifying the overall industry landscape and trends." },
    { text: "Challenges", description: "Analyzing potential challenges and barriers to entry." },
    { text: "Recommendation", description: "Developing strategic recommendations based on findings." },
    { text: "Final Report Generation", description: "Synthesizing the findings into a comprehensive and structured report." }
  ];

  // --- Helpers ---

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, state.status]);

  const addMessage = (msg: Omit<ChatMessage, "id" | "timestamp">) => {
    const newMsg: ChatMessage = {
      ...msg,
      id: `msg-${Date.now()}-${Math.random()}`,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMsg]);
    return newMsg;
  };

  // --- Initialization ---

  useEffect(() => {
    // Check Auth
    if (!isAuthenticated && !isPageLoading) {
      // Only redirect if we are done loading local state
      // router.push('/signin'); 
    }

    // Load Session Data
    const storedData = sessionStorage.getItem('marketValidationData');
    if (storedData) {
      try {
        const parsedData = JSON.parse(storedData);
        setInitialInput(parsedData.selectedProblemStatement?.statement || "");
      } catch (e) {
        console.error("Failed to parse session data", e);
      }
    }
    setIsPageLoading(false);

    // Cleanup on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [isAuthenticated, isPageLoading]);

  /**
   * Centralized polling logic. 
   * It handles the two possible outcomes of polling:
   * 1. Status becomes 'completed' -> Fetch Report
   * 2. Status becomes 'waiting_for_clarification' -> Ask Questions
   */
  const runPolling = async (sessionId: string, authToken: string) => {
    try {
      const signal = abortControllerRef.current?.signal;

      const response = await pollWorkflowStatus(
        sessionId,
        authToken,
        (progressData) => {
          dispatch({
            type: 'UPDATE_PROGRESS',
            payload: {
              progress: progressData.progress,
              details: progressData.progress_details ?? undefined
            }
          });
        },
        undefined,
        undefined,
        signal
      );

      console.log(`status check Response: ${JSON.stringify(response)}`);

      if (response.status === 'completed') {
        // Fetch Final Report
        const report = await getReport(sessionId, authToken, signal);
        dispatch({ type: 'COMPLETE', payload: report });

        addMessage({
          from: "assistant",
          content: "🎉 Validation Complete! Redirecting you to the full report...",
          type: "system"
        });

        // Store and Redirect
        sessionStorage.setItem('validationResults', JSON.stringify({ report, sessionId }));
        setTimeout(() => {
          router.push(`/team-workspace/problem-validator/${sessionId}/results`);
        }, 2000);

      } else if (response.status === 'waiting_for_clarification' && response.clarification_questions) {
        // Handle Clarification Flow
        dispatch({ type: 'SET_QUESTIONS', payload: response.clarification_questions });

        // Display First Question
        const firstQ = response.clarification_questions[0];
        displayQuestion(firstQ);
      }

    } catch (error: any) {
      // Ignore cancellations
      if (error.code === 'POLLING_CANCELLED' || error.name === 'AbortError') return;

      const msg = error instanceof WorkflowAPIError ? error.message : "An unexpected error occurred.";
      dispatch({ type: 'ERROR', payload: msg });
      toast.error(msg);
      addMessage({ from: "assistant", content: `❌ Error: ${msg}`, type: "system" });
    }
  };

  const displayQuestion = (question: ClarificationQuestion) => {
    const questionText = question.options
      ? `${question.question}\n\nOptions:\n${question.options.map((opt, i) => `${i + 1}. ${opt}`).join('\n')}`
      : question.question;

    addMessage({
      from: "assistant",
      content: questionText,
      type: "question",
      questionId: question.id
    });
  };

  const handleStartWorkflow = async (query: string) => {
    if (!user || !token) {
      toast.error("Please log in to continue");
      return;
    }

    const userId = user.id || "";
    if (!userId) {
      toast.error("User identification failed");
      return;
    }

    // 1. Reset & Setup Cancellation
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();

    // 2. UI Updates
    dispatch({ type: 'START_INIT' });
    addMessage({ from: "user", content: query, type: "question" });

    try {
      // 3. Start API
      const response = await startWorkflow(
        query,
        userId,
        token,
        abortControllerRef.current.signal
      );

      dispatch({
        type: 'START_SUCCESS',
        payload: { sessionId: response.session_id, progress: response.progress }
      });

      // 4. Begin Polling
      await runPolling(response.session_id, token);

    } catch (error: any) {
      if (error.name === 'AbortError') return;

      // Check if it's a WorkflowAPIError with 402 status (insufficient credits)
      if (error && typeof error === 'object' && 'status' in error && error.status === 402) {
        dispatch({ type: 'INSUFFICIENT_CREDITS' });
      } else {
        const msg = error.message || "Failed to start workflow";
        dispatch({ type: 'ERROR', payload: msg });
        toast.error(msg);
      }
    }
  };

  const handleAnswerSubmit = async (answer: string) => {
    if (!state.sessionId || !token) return;

    const currentQ = state.questions[state.currentQuestionIndex];

    // 1. Show User Answer
    addMessage({
      from: "user",
      content: answer,
      type: "answer",
      questionId: currentQ?.id
    });

    // 2. Update Local State
    // API usually expects q_1, q_2 format or specific IDs. 
    // Using index-based ID for safety if API requires it, or currentQ.id if provided.
    const questionKey = `q_${state.currentQuestionIndex + 1}`;
    dispatch({ type: 'ANSWER_QUESTION', payload: { id: questionKey, answer } });

    const nextIndex = state.currentQuestionIndex + 1;

    // 3. Check if we have more questions
    if (nextIndex < state.questions.length) {
      // Delay slightly for UX before showing next question
      setTimeout(() => {
        const nextQ = state.questions[nextIndex];
        displayQuestion(nextQ);
      }, 600);
    } else {
      // 4. All Answered - Submit
      dispatch({ type: 'SUBMIT_ANSWERS_INIT' });

      try {
        const finalAnswers = {
          ...state.answers,
          [questionKey]: answer
        };

        const response = await submitAnswers(
          state.sessionId,
          finalAnswers,
          token,
          abortControllerRef.current?.signal
        );

        console.log(`submit Response: ${JSON.stringify(response)}`);

        // Resume polling for report
        await runPolling(state.sessionId, token);

      } catch (error: any) {
        if (error.name === 'AbortError') return;

        // Check if it's a WorkflowAPIError with 402 status (insufficient credits)
        if (error && typeof error === 'object' && 'status' in error && error.status === 402) {
          dispatch({ type: 'INSUFFICIENT_CREDITS' });
        } else {
          const msg = error.message || "Failed to submit answers";
          dispatch({ type: 'ERROR', payload: msg });
          toast.error(msg);
        }
      }
    }
  };

  const handleInputSubmit = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;

    if (state.status === 'idle' || state.status === 'error') {
      handleStartWorkflow(trimmed);
    } else if (state.status === 'waiting_for_clarification') {
      handleAnswerSubmit(trimmed);
    }
  };

  const handleRetry = () => {
    dispatch({ type: 'RESET' });
    setMessages([]);
    if (initialInput) {
      handleStartWorkflow(initialInput);
    }
  };

  const handleCloseInsufficientCreditsModal = () => {
    // Reset the entire workflow state and clear messages
    dispatch({ type: 'RESET' });
    setMessages([]);
  };

  // --- Render ---

  if (isPageLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
          className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full"
        />
      </div>
    );
  }

  const isInputDisabled =
    state.status === 'starting' ||
    state.status === 'processing' ||
    state.status === 'completed';

  const inputPlaceholder =
    state.status === 'waiting_for_clarification' ? "Type your answer..." :
      state.status === 'completed' ? "Validation complete!" :
        "Describe the problem you want to validate...";

  return (
    <div className="relative flex flex-col overflow-x-hidden max-h-screen">
      <PageBreadcrumb pageTitle="Problem Validator" titleSuffix={<CreditCostBadge cost={30} />} />

      <div className="flex-1 w-full overflow-x-hidden ">
        {/* Welcome Header */}
        {state.status === 'idle' && messages.length <= 1 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mt-8 flex flex-col gap-4"
          >
            <h1 className="text-2xl font-bold text-brand-500 dark:text-white">
              Welcome to Yuba!
            </h1>
            <p className="text-md text-gray-600 dark:text-gray-400 max-w-2xl mx-auto -mt-4">
              What problem are you looking to validate today?
            </p>
            {/* Idea Refiner CTA */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              whileTap={{ scale: 0.98 }}
              transition={{ delay: 0.3 }}
              onClick={() => {
                setIsRedirecting(true);
                router.push('/team-workspace/idea-refiner');
              }}
              className="mx-auto max-w-md cursor-pointer group hover:scale-105 transition-all duration-200"
            >
              <div className="relative overflow-hidden flex items-center gap-4 px-5 py-4 rounded-2xl border border-brand-300/60 dark:border-brand-600/40 bg-brand-25 dark:bg-brand-900/10 hover:border-brand-500/80 dark:hover:border-brand-400/80 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-all duration-300 shadow-sm hover:shadow-md">
                {/* Subtle background glow */}
                <div className="absolute -right-8 -top-8 w-24 h-24 bg-brand-500/5 rounded-full blur-2xl group-hover:bg-brand-500/10 transition-colors" />

                <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-brand-50 dark:bg-brand-900/40 flex items-center justify-center border border-brand-100 dark:border-brand-800 group-hover:scale-110 transition-transform duration-300">
                  {isRedirecting ? (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                      className="flex items-center justify-center"
                    >
                      <RefreshCw className="w-5 h-5 text-brand-500 dark:text-brand-400" />
                    </motion.div>
                  ) : (
                    <Lightbulb className="w-5 h-5 text-brand-500 dark:text-brand-400" />
                  )}
                </div>

                <div className="flex-1 text-left">
                  <p className="text-md font-bold text-brand-600 dark:text-brand-200 mb-1">
                    No Formulated Problem Statement yet?
                  </p>
                  <p className="text-[11px] text-gray-500 dark:text-brand-400/80 leading-tight">
                    Try our <span className="text-brand-600 dark:text-brand-300 font-semibold underline decoration-brand-200 dark:decoration-brand-800 underline-offset-2">Problem Predictor</span> Your Problem Formulation Assistant →
                  </p>
                </div>

                {/* Loading Shimmer Overlay */}
                {isRedirecting && (
                  <motion.div
                    className="absolute bottom-0 left-0 h-[2px] bg-brand-500 dark:bg-brand-400"
                    initial={{ width: 0 }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 1.5, ease: "easeInOut" }}
                  />
                )}
              </div>
            </motion.div>
          </motion.div>
        )}

        {/* Chat Area */}
        <div className="space-y-4 px-8 py-2">
          <AnimatePresence mode="popLayout">
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                layout
                initial="hidden"
                animate="visible"
                exit="exit"
                variants={itemVariants as any}
                className={`flex gap-3 ${msg.from === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {/* Bot Avatar */}
                {msg.from === 'assistant' && (
                  <div className="flex-shrink-0 w-8 h-8 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center mt-1">
                    <Bot className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                  </div>
                )}

                {/* Bubble */}
                <div className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-5 py-2 shadow-sm ${msg.from === 'user'
                  ? 'bg-brand-600 text-white rounded-br-none'
                  : msg.type === 'system'
                    ? 'bg-gray-100 dark:bg-gray-800/80 text-gray-600 border border-gray-200 dark:border-gray-700'
                    : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 border border-gray-100 dark:border-gray-700 rounded-bl-none'
                  }`}>
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                  </p>

                  {/* Metadata */}
                  <div className={`text-[10px]  opacity-70 flex items-center gap-1 ${msg.from === 'user' ? 'justify-end text-brand-100' : 'text-gray-400'}`}>
                    <span>{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </div>

                {/* User Avatar */}
                {msg.from === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 bg-brand-600 rounded-full flex items-center justify-center mt-1">
                    <User className="h-4 w-4 text-white" />
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing Indicator */}
          {state.status === 'starting' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
              <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center">
                <Bot className="h-4 w-4 text-brand-600" />
              </div>
              <div className="bg-gray-200 dark:bg-gray-800 rounded-2xl px-4 py-3 flex items-center gap-1.5">
                <motion.span className="w-1.5 h-1.5 bg-gray-500 rounded-full" animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 1 }} />
                <motion.span className="w-1.5 h-1.5 bg-gray-500 rounded-full" animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0.1 }} />
                <motion.span className="w-1.5 h-1.5 bg-gray-500 rounded-full" animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0.2 }} />
              </div>
            </motion.div>
          )}

          {/* Progress Indicator */}
          <MultiStepLoader
            loadingStates={loadingStates}
            loading={state.status === 'processing'}
            progress={state.progress}
            progressDetails={state.progressDetails}
            onCancel={() => {
              if (abortControllerRef.current) {
                abortControllerRef.current.abort();
              }
              dispatch({ type: 'RESET' });
              setMessages([]);
            }}
          />

          <div ref={messagesEndRef} className="h-1" />
        </div>
      </div>

      <motion.div
        className="sticky bottom-0 left-0 right-0  bg-white dark:bg-gray-900 overflow-hidden shadow-lg pb-4 "
        initial={{ y: 100 }}
        animate={{ y: 0 }}
        transition={{ type: "spring", stiffness: 100, damping: 20 }}
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-6 md:px-8 xl:px-10 w-full bg-white dark:bg-gray-900 ">
          <AI_Input_Search
            placeholder={inputPlaceholder}
            initialValue={state.status === 'idle' ? initialInput : ""}
            onSubmit={handleInputSubmit}
            disabled={isInputDisabled}
            autoFocus={state.status === 'waiting_for_clarification'}
          />
        </div>
      </motion.div>

      {/* Insufficient Credits Modal */}
      <InsufficientCreditsModal
        isOpen={state.isInsufficientCreditsModalOpen}
        onClose={handleCloseInsufficientCreditsModal}
        title="Insufficient Credits"
        description="You don't have enough credits to validate your problem. Please purchase more credits to continue."
        buttonText1="Request Credit"
        buttonText2="Close"
      />
    </div>
  );
}