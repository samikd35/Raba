'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { useAuthStore } from '@/stores/authStore';
import {
  Question,
  BootstrapResponse,
  QuestionsResponse,
  StatusResponse,
  EnhancedContext,
  EnhancedContextResponse,
  ModalStep,
  EditableContext,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface UseProjectBootstrapReturn {
  // State
  step: ModalStep;
  projectName: string;
  ideaText: string;
  pdfFiles: File[];
  isSubmitting: boolean;
  processingMessage: string;
  projectId: string | null;
  questions: Question[];
  answers: Record<string, string>;
  answerErrors: Record<string, string>;
  error: string | null;
  showCancelConfirm: boolean;
  enhancedContext: EnhancedContext | null;
  editableContext: EditableContext | null;
  isFormValid: boolean;
  
  // Setters
  setProjectName: (value: string) => void;
  setIdeaText: (value: string) => void;
  setShowCancelConfirm: (value: boolean) => void;
  
  // Handlers
  handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleRemoveFile: (index: number) => void;
  handleAnswerChange: (questionId: string, value: string) => void;
  handleSubmit: () => Promise<void>;
  handleSubmitAnswers: () => Promise<void>;
  handleConfirmContext: () => Promise<void>;
  resetState: () => void;
  
  // Context update handlers
  updateEditableContext: (field: string, value: string | string[]) => void;
  updateNestedEditableContext: (parent: 'problem' | 'businessModelSeeds', field: string, value: string | string[]) => void;
  updateArrayItem: (field: 'customerSegments' | 'differentiation' | 'constraintsAndRisks', index: number, value: string) => void;
  updateCostDriver: (index: number, value: string) => void;
  
  // Utility functions
  getPriorityColor: (priority: string) => string;
  getCategoryDisplay: (category: string) => string;
}

export function useProjectBootstrap(
  onClose: () => void,
  onProjectCreated?: () => void
): UseProjectBootstrapReturn {
  const { token } = useAuthStore();
  const abortControllerRef = useRef<AbortController | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const statusPollingRef = useRef<NodeJS.Timeout | null>(null);
  const contextFetchedRef = useRef<boolean>(false);

  // Form state
  const [step, setStep] = useState<ModalStep>('input');
  const [projectName, setProjectName] = useState('');
  const [ideaText, setIdeaText] = useState('');
  const [pdfFiles, setPdfFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [processingMessage, setProcessingMessage] = useState('');
  
  // Project state
  const [projectId, setProjectId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [answerErrors, setAnswerErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  
  // Confirmation dialog state
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  
  // Enhanced context state
  const [enhancedContext, setEnhancedContext] = useState<EnhancedContext | null>(null);
  const [editableContext, setEditableContext] = useState<EditableContext | null>(null);

  /**
   * Reset modal state
   */
  const resetState = useCallback(() => {
    setStep('input');
    setProjectName('');
    setIdeaText('');
    setPdfFiles([]);
    setIsSubmitting(false);
    setProcessingMessage('');
    setProjectId(null);
    setQuestions([]);
    setAnswers({});
    setAnswerErrors({});
    setError(null);
    setEnhancedContext(null);
    setEditableContext(null);
    
    contextFetchedRef.current = false;
    
    if (statusPollingRef.current) {
      clearInterval(statusPollingRef.current);
      statusPollingRef.current = null;
    }
    
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  /**
   * Handle file selection
   */
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      const pdfFilesArray = Array.from(files).filter(file => file.type === 'application/pdf');
      if (pdfFilesArray.length !== files.length) {
        toast.error('Only PDF files are allowed');
      }
      setPdfFiles(prev => [...prev, ...pdfFilesArray]);
    }
    e.target.value = '';
  }, []);

  /**
   * Remove a file from the list
   */
  const handleRemoveFile = useCallback((index: number) => {
    setPdfFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  /**
   * Poll for questions
   */
  const pollForQuestions = useCallback(async (projectIdToFetch: string) => {
    if (!token) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v2/mvp/bootstrap/projects/${projectIdToFetch}/questions`,
        {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        if (response.status === 409) {
          setProcessingMessage('Processing your data... This may take a moment.');
          return;
        }
        throw new Error(`Failed to fetch questions: ${response.status}`);
      }

      const data: QuestionsResponse = await response.json();

      if (data.success && data.context_status === 'questions_pending') {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setQuestions(data.questions);
        setStep('questions');
        toast.success(`Retrieved ${data.questions.length} questions!`);
      } else if (data.context_status === 'embedding') {
        setProcessingMessage('Analyzing your content and generating questions...');
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Polling error:', err);
      }
    }
  }, [token]);

  /**
   * Start polling for questions
   */
  const startPolling = useCallback((projectIdToFetch: string) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    pollForQuestions(projectIdToFetch);

    pollingIntervalRef.current = setInterval(() => {
      pollForQuestions(projectIdToFetch);
    }, 3000);
  }, [pollForQuestions]);

  /**
   * Fetch enhanced context when ready
   */
  const fetchEnhancedContext = useCallback(async (projectIdToFetch: string) => {
    if (!token) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v2/mvp/bootstrap/projects/${projectIdToFetch}/enhanced-context`,
        {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        if (response.status === 402) {
          toast.error('Payment required. Please add credits to continue.');
          setError('Payment required to access enhanced context.');
          return;
        }
        if (response.status === 409) {
          return;
        }
        throw new Error(`Failed to fetch enhanced context: ${response.status}`);
      }

      const data: EnhancedContextResponse = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('Enhanced context response:', data);
      }

      if (data.success) {
        setEnhancedContext(data.enhanced_context);
        
        const draft = data.enhanced_context.draft;
        setEditableContext({
          ideaSummary: draft.IdeaSummary || '',
          customerSegments: draft.CustomerSegments || [],
          problem: {
            who: draft.Problem?.who || '',
            what: draft.Problem?.what || '',
            where: draft.Problem?.where || '',
            why_now: draft.Problem?.why_now || '',
          },
          solutionOverview: draft.SolutionOverview || '',
          differentiation: draft.Differentiation || [],
          businessModelSeeds: {
            revenue_model: draft.BusinessModelSeeds?.revenue_model || '',
            pricing_hypothesis: draft.BusinessModelSeeds?.pricing_hypothesis || '',
            cost_drivers: draft.BusinessModelSeeds?.cost_drivers || [],
          },
          constraintsAndRisks: draft.ConstraintsAndRisks || [],
        });
        
        setStep('context-ready');
        toast.success('Enhanced context generated successfully!');
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Fetch enhanced context error:', err);
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch enhanced context';
      setError(errorMessage);
      toast.error(errorMessage);
    }
  }, [token]);

  /**
   * Poll for status updates
   */
  const pollForStatus = useCallback(async (projectIdToFetch: string) => {
    if (!token) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v2/mvp/bootstrap/projects/${projectIdToFetch}/status`,
        {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.status}`);
      }

      const data: StatusResponse = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('Status response:', data);
      }

      if (data.success) {
        switch (data.context_status) {
          case 'answers_embedding':
            setProcessingMessage('Embedding your answers...');
            break;
          case 'researching':
            setProcessingMessage('Conducting AI-powered research...');
            break;
          case 'composing':
            setProcessingMessage('Composing enhanced context...');
            break;
          case 'context_ready':
            if (statusPollingRef.current) {
              clearInterval(statusPollingRef.current);
              statusPollingRef.current = null;
            }
            if (!contextFetchedRef.current) {
              contextFetchedRef.current = true;
              await fetchEnhancedContext(projectIdToFetch);
            }
            break;
          case 'payment_required':
            if (statusPollingRef.current) {
              clearInterval(statusPollingRef.current);
              statusPollingRef.current = null;
            }
            toast.error('Payment required. Please add credits to continue.');
            setError('Payment required. Please add credits to access your enhanced context.');
            break;
          default:
            setProcessingMessage('Processing your project...');
        }
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Status polling error:', err);
      }
    }
  }, [token, fetchEnhancedContext]);

  /**
   * Start polling for status updates
   */
  const startStatusPolling = useCallback((projectIdToFetch: string) => {
    if (statusPollingRef.current) {
      clearInterval(statusPollingRef.current);
    }

    contextFetchedRef.current = false;
    setProcessingMessage('Processing your answers...');

    pollForStatus(projectIdToFetch);

    statusPollingRef.current = setInterval(() => {
      pollForStatus(projectIdToFetch);
    }, 3000);
  }, [pollForStatus]);

  /**
   * Submit the bootstrap project
   */
  const handleSubmit = useCallback(async () => {
    if (!projectName.trim()) {
      toast.error('Project name is required');
      return;
    }

    if (pdfFiles.length === 0) {
      toast.error('Please upload at least one PDF document');
      return;
    }

    if (!token) {
      toast.error('Authentication required. Please sign in again.');
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setIsSubmitting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('project_name', projectName.trim());
      
      if (ideaText.trim()) {
        formData.append('idea_text', ideaText.trim());
      }

      pdfFiles.forEach((file) => {
        formData.append('pdf_files', file);
      });

      if (process.env.NODE_ENV === 'development') {
        console.log('Submitting bootstrap project:', {
          project_name: projectName,
          idea_text: ideaText ? 'provided' : 'not provided',
          pdf_files_count: pdfFiles.length,
        });
      }

      const response = await fetch(
        `${API_BASE_URL}/api/v2/mvp/bootstrap/projects`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formData,
          signal: abortControllerRef.current.signal,
        }
      );

      if (!response.ok) {
        let errorMessage = `Request failed: ${response.status}`;
        try {
          const errorData = await response.json();
          
          if (process.env.NODE_ENV === 'development') {
            console.error('API Error Response:', errorData);
          }
          
          errorMessage = errorData.error || 
                        errorData.message || 
                        errorData.detail || 
                        (errorData.details && JSON.stringify(errorData.details)) ||
                        errorMessage;
        } catch (parseError) {
          if (process.env.NODE_ENV === 'development') {
            console.error('Failed to parse error response:', parseError);
          }
        }
        
        throw new Error(errorMessage);
      }

      const data: BootstrapResponse = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('Bootstrap project response:', data);
      }

      if (data.success) {
        setProjectId(data.project_id);
        setStep('processing');
        setProcessingMessage(data.message || 'Project created. Processing in background...');
        
        toast.success('Project created successfully!');
        
        startPolling(data.project_id);
      } else {
        throw new Error(data.message || 'Failed to create project');
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      
      if (errorMessage.includes('duplicate key') || 
          errorMessage.includes('already exists') || 
          errorMessage.includes('23505') ||
          errorMessage.includes('unique_tenant_project_name')) {
        const displayMessage = `Project name "${projectName}" is already taken. Please choose a different name.`;
        setError(displayMessage);
        toast.error(displayMessage);
      } else if (errorMessage.includes('500')) {
        const displayMessage = 'Server error occurred. Please try again or contact support if the issue persists.';
        setError(displayMessage);
        toast.error(displayMessage);
      } else {
        const cleanErrorMessage = errorMessage.replace(/^Failed to create project:\s*/, '');
        setError(cleanErrorMessage);
        toast.error(cleanErrorMessage);
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error('Bootstrap project error:', err);
        console.error('Form data:', {
          project_name: projectName,
          idea_text: ideaText || 'not provided',
          pdf_files_count: pdfFiles.length,
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [projectName, ideaText, pdfFiles, token, startPolling]);

  /**
   * Validate answers
   */
  const validateAnswers = useCallback(() => {
    const errors: Record<string, string> = {};
    
    questions.forEach(question => {
      const answer = answers[question.id]?.trim();
      
      if (question.required && !answer) {
        errors[question.id] = 'This question is required';
      } else if (answer && answer.length < 10) {
        errors[question.id] = 'Please provide a more detailed answer (at least 10 characters)';
      }
    });

    setAnswerErrors(errors);
    return Object.keys(errors).length === 0;
  }, [questions, answers]);

  /**
   * Handle answer change
   */
  const handleAnswerChange = useCallback((questionId: string, value: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
    setAnswerErrors(prev => {
      if (prev[questionId]) {
        const newErrors = { ...prev };
        delete newErrors[questionId];
        return newErrors;
      }
      return prev;
    });
  }, []);

  /**
   * Handle submit answers
   */
  const handleSubmitAnswers = useCallback(async () => {
    if (!validateAnswers()) {
      toast.error('Please answer all required questions with sufficient detail');
      return;
    }

    if (!projectId || !token) {
      toast.error('Missing project information. Please try again.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const formattedAnswers = questions.map(question => ({
        question_id: question.id,
        answer: answers[question.id] || ''
      }));

      if (process.env.NODE_ENV === 'development') {
        console.log('Submitting answers:', formattedAnswers);
      }

      const response = await fetch(
        `${API_BASE_URL}/api/v2/mvp/bootstrap/projects/${projectId}/answers`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ answers: formattedAnswers }),
        }
      );

      if (!response.ok) {
        let errorMessage = `Request failed: ${response.status}`;
        try {
          const errorData = await response.json();
          
          if (process.env.NODE_ENV === 'development') {
            console.error('API Error Response:', errorData);
          }
          
          errorMessage = errorData.error || 
                        errorData.message || 
                        errorData.detail || 
                        errorMessage;
        } catch (parseError) {
          if (process.env.NODE_ENV === 'development') {
            console.error('Failed to parse error response:', parseError);
          }
        }
        
        throw new Error(errorMessage);
      }

      const data = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('Submit answers response:', data);
      }

      if (data.success) {
        toast.success('Answers submitted successfully! Processing your enhanced context...');
        
        setStep('processing-context');
        startStatusPolling(projectId);
      } else {
        throw new Error(data.message || 'Failed to submit answers');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      
      if (errorMessage.includes('400')) {
        const displayMessage = 'Invalid answers provided. Please check your responses and try again.';
        setError(displayMessage);
        toast.error(displayMessage);
      } else if (errorMessage.includes('404')) {
        const displayMessage = 'Project not found. Please try creating a new project.';
        setError(displayMessage);
        toast.error(displayMessage);
      } else if (errorMessage.includes('422')) {
        const displayMessage = 'Validation error. Please ensure all required questions are answered properly.';
        setError(displayMessage);
        toast.error(displayMessage);
      } else {
        const cleanErrorMessage = errorMessage.replace(/^Failed to submit answers:\s*/, '');
        setError(cleanErrorMessage);
        toast.error(cleanErrorMessage);
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error('Submit answers error:', err);
        console.error('Answers data:', answers);
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [validateAnswers, answers, questions, projectId, token, startStatusPolling]);

  /**
   * Update editable context field
   */
  const updateEditableContext = useCallback((field: string, value: string | string[]) => {
    setEditableContext(prev => {
      if (!prev) return prev;
      return { ...prev, [field]: value };
    });
  }, []);

  /**
   * Update nested editable context field
   */
  const updateNestedEditableContext = useCallback((parent: 'problem' | 'businessModelSeeds', field: string, value: string | string[]) => {
    setEditableContext(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        [parent]: {
          ...prev[parent],
          [field]: value,
        },
      };
    });
  }, []);

  /**
   * Update array item in editable context
   */
  const updateArrayItem = useCallback((field: 'customerSegments' | 'differentiation' | 'constraintsAndRisks', index: number, value: string) => {
    setEditableContext(prev => {
      if (!prev) return prev;
      const newArray = [...prev[field]];
      newArray[index] = value;
      return { ...prev, [field]: newArray };
    });
  }, []);

  /**
   * Update cost drivers array item
   */
  const updateCostDriver = useCallback((index: number, value: string) => {
    setEditableContext(prev => {
      if (!prev) return prev;
      const newDrivers = [...prev.businessModelSeeds.cost_drivers];
      newDrivers[index] = value;
      return {
        ...prev,
        businessModelSeeds: {
          ...prev.businessModelSeeds,
          cost_drivers: newDrivers,
        },
      };
    });
  }, []);

  /**
   * Confirm and save enhanced context
   */
  const handleConfirmContext = useCallback(async () => {
    if (!projectId || !token || !editableContext) {
      toast.error('Missing project information. Please try again.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const confirmedContext = {
        IdeaSummary: editableContext.ideaSummary,
        CustomerSegments: editableContext.customerSegments,
        Problem: {
          who: editableContext.problem.who,
          what: editableContext.problem.what,
          where: editableContext.problem.where,
          why_now: editableContext.problem.why_now,
        },
        SolutionOverview: editableContext.solutionOverview,
        Differentiation: editableContext.differentiation,
        BusinessModelSeeds: {
          revenue_model: editableContext.businessModelSeeds.revenue_model,
          pricing_hypothesis: editableContext.businessModelSeeds.pricing_hypothesis,
          cost_drivers: editableContext.businessModelSeeds.cost_drivers,
        },
        ConstraintsAndRisks: editableContext.constraintsAndRisks,
        Research: enhancedContext?.draft.Research || {},
        AlternativesAndCompetition: enhancedContext?.draft.AlternativesAndCompetition || {},
      };

      if (process.env.NODE_ENV === 'development') {
        console.log('Confirming context:', confirmedContext);
      }

      const response = await fetch(
        `${API_BASE_URL}/api/v2/mvp/bootstrap/projects/${projectId}/enhanced-context/confirm`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ confirmed_context: confirmedContext }),
        }
      );

      if (!response.ok) {
        let errorMessage = `Request failed: ${response.status}`;
        try {
          const errorData = await response.json();
          
          if (process.env.NODE_ENV === 'development') {
            console.error('API Error Response:', errorData);
          }
          
          errorMessage = errorData.error || 
                        errorData.message || 
                        errorData.detail || 
                        errorMessage;
        } catch (parseError) {
          if (process.env.NODE_ENV === 'development') {
            console.error('Failed to parse error response:', parseError);
          }
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Context confirmed successfully:', data);
      }

      if (data.success) {
        toast.success('Project created successfully!');
        
        if (onProjectCreated) {
          onProjectCreated();
        }
        
        resetState();
        onClose();
      } else {
        throw new Error(data.error || 'Failed to confirm context');
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Confirm context error:', err);
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to save context';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  }, [projectId, token, editableContext, enhancedContext, resetState, onClose, onProjectCreated]);

  /**
   * Get priority badge color
   */
  const getPriorityColor = useCallback((priority: string) => {
    switch (priority) {
      case 'P0':
        return 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300 border-red-200 dark:border-red-800';
      case 'P1':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800';
      case 'P2':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border-blue-200 dark:border-blue-800';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700';
    }
  }, []);

  /**
   * Get category display name
   */
  const getCategoryDisplay = useCallback((category: string) => {
    const categories: Record<string, string> = {
      target_customer: 'Target Customer',
      problem: 'Problem',
      solution: 'Solution',
      differentiation: 'Differentiation',
      revenue: 'Revenue',
      market_scope: 'Market Scope',
    };
    return categories[category] || category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
      if (statusPollingRef.current) {
        clearInterval(statusPollingRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const isFormValid = Boolean(projectName.trim() && pdfFiles.length > 0);

  return {
    // State
    step,
    projectName,
    ideaText,
    pdfFiles,
    isSubmitting,
    processingMessage,
    projectId,
    questions,
    answers,
    answerErrors,
    error,
    showCancelConfirm,
    enhancedContext,
    editableContext,
    isFormValid,
    
    // Setters
    setProjectName,
    setIdeaText,
    setShowCancelConfirm,
    
    // Handlers
    handleFileChange,
    handleRemoveFile,
    handleAnswerChange,
    handleSubmit,
    handleSubmitAnswers,
    handleConfirmContext,
    resetState,
    
    // Context update handlers
    updateEditableContext,
    updateNestedEditableContext,
    updateArrayItem,
    updateCostDriver,
    
    // Utility functions
    getPriorityColor,
    getCategoryDisplay,
  };
}
