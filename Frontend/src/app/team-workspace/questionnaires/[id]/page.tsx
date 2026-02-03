"use client";

import PageBreadcrumb from "@/components/common/module 2/PageBreadCrumb";
import CreditCostBadge from "@/components/common/CreditCostBadge";
import FeatureVideoOverlay from "@/components/feature-videos/FeatureVideoOverlay";
import { FEATURE_IDS, getFeatureVideoConfig } from "@/lib/featureVideos";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { authService } from "@/services/authService";
import { MessageSquare, CheckCircle, RefreshCw, ChevronRight, ScrollText, HelpCircle, Users, Target, Printer, Edit3, Save, X, Loader2, UserCircle2, Frown, TrendingUp } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import toast from "react-hot-toast";
import { motion } from "framer-motion";
import DownloadQuestionnairesDrawer from "@/components/kokonutui/DownloadQuestionnairesDrawer";

interface Questionnaire {
  id: string;
  text: string;
  component_type: 'jtbd' | 'pain' | 'gain';
  type: string;
  assumption_id: string;
  persona_name: string;
  hypothesis_id: string;
  generated_at: string;
}

interface QuestionnaireResponse {
  questionnaires: Questionnaire[];
  project_id: string;
  stage: string;
  total_questions: number;
  assumptions_count: number;
  personas_count: number;
  questions_per_assumption: number;
}

interface ExistingQuestionnairesResponse {
  success: boolean;
  data: {
    questionnaires: Questionnaire[];
    project_id: string;
    stage: string;
    total_questions: number;
    assumptions_count: number;
    personas_count: number;
    questions_per_assumption: number;
  };
  message: string;
}

interface EditQuestionnairesRequest {
  questionnaires: Questionnaire[];
}

interface EditQuestionnairesResponse {
  success: boolean;
  data: any;
  message: string;
}

export default function QuestionnairesPage() {
  const params = useParams();
  const projectId = params.id as string;
  const router = useRouter();
  const featureConfig = getFeatureVideoConfig(FEATURE_IDS.QUESTIONNAIRES);
  const [generating, setGenerating] = useState(false);
  const [questionnaires, setQuestionnaires] = useState<Questionnaire[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");
  const [saving, setSaving] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Persona toggle state
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [availablePersonas, setAvailablePersonas] = useState<string[]>([]);

  const sanitizeInput = useCallback((input: string): string => {
    return input
      .replace(/<[^>]*>/g, '') // Remove HTML tags
      .substring(0, 2000) // Limit length
      .trim();
  }, []);

  // Get display name for persona
  const getPersonaDisplayName = useCallback((personaId: string | null) => {
    if (!personaId) return "All Personas";
    if (personaId === "all") return "All Personas";
    
    // persona_name is already the display name in the backend response
    return personaId;
  }, []);

  // Get component type icon and color
  const getComponentTypeInfo = useCallback((type: 'jtbd' | 'pain' | 'gain') => {
    switch (type) {
      case 'jtbd':
        return {
          icon: Target,
          color: 'text-green-600 dark:text-green-400',
          bgColor: 'bg-green-100 dark:bg-green-800/30',
          borderColor: 'border-green-200 dark:border-green-600',
          label: 'Customer JOBS-TO-BE-DONE'
        };
      case 'pain':
        return {
          icon: Frown,
          color: 'text-red-600 dark:text-red-400',
          bgColor: 'bg-red-100 dark:bg-red-800/30',
          borderColor: 'border-red-200 dark:border-red-600',
          label: 'Customer Pains'
        };
      case 'gain':
        return {
          icon: TrendingUp,
          color: 'text-brand-600 dark:text-brand-400',
          bgColor: 'bg-brand-100 dark:bg-brand-800/30',
          borderColor: 'border-brand-200 dark:border-brand-600',
          label: 'Customer Gains'
        };
    }
  }, []);

  // Filter questionnaires by selected persona
  const filteredQuestionnaires = useMemo(() => {
    if (!selectedPersona) {
      return questionnaires;
    }
    return questionnaires.filter(q => q.persona_name === selectedPersona);
  }, [questionnaires, selectedPersona]);

  const getCacheKey = useCallback(() => `questionnaires_${projectId}`, [projectId]);
  const getCacheTimestampKey = useCallback(() => `questionnaires_${projectId}_timestamp`, [projectId]);

  const saveToCache = useCallback((data: Questionnaire[]) => {
    try {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem(getCacheKey(), JSON.stringify(data));
        sessionStorage.setItem(getCacheTimestampKey(), Date.now().toString());
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to save questionnaires to cache:', error);
      }
    }
  }, [getCacheKey, getCacheTimestampKey]);

  const getFromCache = useCallback((): { data: Questionnaire[] | null; isExpired: boolean } => {
    try {
      if (typeof window === 'undefined') {
        return { data: null, isExpired: true };
      }

      const cachedData = sessionStorage.getItem(getCacheKey());
      const cachedTimestamp = sessionStorage.getItem(getCacheTimestampKey());

      if (!cachedData || !cachedTimestamp) {
        return { data: null, isExpired: true };
      }

      const timestamp = parseInt(cachedTimestamp, 10);
      const thirtyMinutes = 30 * 60 * 1000; // 30 minutes in milliseconds
      const isExpired = Date.now() - timestamp > thirtyMinutes;

      if (isExpired) {
        return { data: null, isExpired: true };
      }

      return { data: JSON.parse(cachedData), isExpired: false };
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to get questionnaires from cache:', error);
      }
      return { data: null, isExpired: true };
    }
  }, [getCacheKey, getCacheTimestampKey]);

  const clearCache = useCallback(() => {
    try {
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem(getCacheKey());
        sessionStorage.removeItem(getCacheTimestampKey());
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to clear questionnaires cache:', error);
      }
    }
  }, [getCacheKey, getCacheTimestampKey]);

  const checkExistingQuestionnaires = useCallback(async (signal: AbortSignal): Promise<Questionnaire[] | null> => {
    try {
      const token = authService.getCurrentToken();
      if (!token) {
        toast.error("Authentication required. Please sign in again.");
        router.push("/signin");
        return null;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/field-prep/questionnaires`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          signal,
        }
      );

      if (response.ok) {
        const result: ExistingQuestionnairesResponse = await response.json();
        if (process.env.NODE_ENV === 'development') {
          console.log('✅ Loaded existing questionnaires:', result.data.questionnaires.length);
        }
        return result.data.questionnaires || [];
      } else if (response.status === 404) {
        if (process.env.NODE_ENV === 'development') {
          console.log('ℹ️ No existing questionnaires found, will generate new ones');
        }
        return null;
      } else if (response.status === 401) {
        toast.error("Session expired. Please sign in again.");
        router.push("/signin");
        return null;
      } else {
        throw new Error(`Failed to check existing questionnaires: ${response.status}`);
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Check existing questionnaires request aborted');
        }
        return null;
      }
      throw error;
    }
  }, [projectId, router]);

  const generateNewQuestionnaires = useCallback(async (signal: AbortSignal): Promise<Questionnaire[]> => {
    const token = authService.getCurrentToken();
    if (!token) {
      toast.error("Authentication required. Please sign in again.");
      router.push("/signin");
      throw new Error("No authentication token");
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/field-prep/questionnaires`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          questions_per_assumption: 5,
          include_demographic_questions: true
        }),
        signal,
      }
    );

    if (!response.ok) {
      if (response.status === 401) {
        toast.error("Session expired. Please sign in again.");
        router.push("/signin");
        throw new Error("Authentication failed");
      }
      throw new Error(`Failed to generate questionnaires: ${response.status}`);
    }

    const data: QuestionnaireResponse = await response.json();
    if (process.env.NODE_ENV === 'development') {
      console.log('✅ Generated new questionnaires:', data.questionnaires.length);
    }
    return data.questionnaires || [];
  }, [projectId, router]);

  const saveQuestionnaires = useCallback(async (updatedQuestionnaires: Questionnaire[]): Promise<boolean> => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    try {
      setSaving(true);
      const token = authService.getCurrentToken();
      
      if (!token) {
        toast.error("Authentication required. Please sign in again.");
        router.push("/signin");
        return false;
      }

      const requestBody: EditQuestionnairesRequest = {
        questionnaires: updatedQuestionnaires
      };

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/field-prep/questionnaires`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
          signal,
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Session expired. Please sign in again.");
          router.push("/signin");
          return false;
        }
        throw new Error(`Failed to save questionnaires: ${response.status}`);
      }

      const result: EditQuestionnairesResponse = await response.json();
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Saved questionnaires:', result.message);
      }
      
      setQuestionnaires(updatedQuestionnaires);
      saveToCache(updatedQuestionnaires);
      toast.success("Questionnaires saved successfully!");
      return true;

    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Save questionnaires request aborted');
        }
        return false;
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error("Error saving questionnaires:", error);
      }
      const errorMessage = error instanceof Error ? error.message : "Failed to save questionnaires";
      toast.error(errorMessage);
      return false;
    } finally {
      setSaving(false);
      abortControllerRef.current = null;
    }
  }, [projectId, router, saveToCache]);

  const fetchOrGenerateQuestionnaires = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    try {
      setGenerating(true);
      setError(null);

      const existingQuestionnaires = await checkExistingQuestionnaires(signal);
      
      let finalQuestionnaires: Questionnaire[];
      
      if (existingQuestionnaires && existingQuestionnaires.length > 0) {
        finalQuestionnaires = existingQuestionnaires;
        toast.success("Loaded existing questionnaires");
      } else {
        finalQuestionnaires = await generateNewQuestionnaires(signal);
        toast.success("Generated new questionnaires successfully!");
      }

      setQuestionnaires(finalQuestionnaires);
      saveToCache(finalQuestionnaires);
      
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Questionnaires request aborted');
        }
        return;
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error("Error fetching/generating questionnaires:", err);
      }
      const errorMessage = err instanceof Error ? err.message : "Failed to load questionnaires";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setGenerating(false);
      setIsLoaded(true);
      abortControllerRef.current = null;
    }
  }, [checkExistingQuestionnaires, generateNewQuestionnaires, saveToCache]);

  const handleRegenerateQuestionnaires = useCallback(async () => {
    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Create new AbortController
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    try {
      setGenerating(true);
      setError(null);
      
      // Clear current data and cache
      setQuestionnaires([]);
      clearCache();

      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 Regenerating questionnaires...');
      }

      // Generate new questionnaires
      const newQuestionnaires = await generateNewQuestionnaires(signal);
      
      setQuestionnaires(newQuestionnaires);
      saveToCache(newQuestionnaires);
      toast.success("Questionnaires regenerated successfully!");
      
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Regenerate questionnaires request aborted');
        }
        return;
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error("Error regenerating questionnaires:", err);
      }
      const errorMessage = err instanceof Error ? err.message : "Failed to regenerate questionnaires";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setGenerating(false);
      abortControllerRef.current = null;
    }
  }, [generateNewQuestionnaires, clearCache, saveToCache]);

  useEffect(() => {
    if (!projectId || isLoaded) return;

    const { data: cachedData, isExpired } = getFromCache();
    
    if (cachedData && !isExpired) {
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Loaded questionnaires from cache:', cachedData.length);
      }
      setQuestionnaires(cachedData);
      setIsLoaded(true);
    } else {
      fetchOrGenerateQuestionnaires();
    }
  }, [projectId, isLoaded, getFromCache, fetchOrGenerateQuestionnaires]);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  // Initialize personas and selected persona from questionnaires data
  useEffect(() => {
    if (questionnaires.length > 0 && availablePersonas.length === 0) {
      const personaNames = new Set<string>();
      questionnaires.forEach(questionnaire => {
        if (questionnaire.persona_name) {
          personaNames.add(questionnaire.persona_name);
        }
      });
      
      const personas = Array.from(personaNames).sort();
      setAvailablePersonas(personas);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('📊 Questionnaires data:', questionnaires.length);
        console.log('📊 Extracted personas from persona_name:', personas);
        console.log('📊 Sample questionnaire:', questionnaires[0]);
      }
      
      // Set first persona as default if not already set
      if (personas.length > 0 && !selectedPersona) {
        setSelectedPersona(personas[0]);
        
        if (process.env.NODE_ENV === 'development') {
          console.log('Initialized selected persona to:', personas[0]);
        }
      }
    }
  }, [questionnaires, availablePersonas.length, selectedPersona]);

  const formatDate = useCallback((dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return "Invalid date";
    }
  }, []);

  const getQuestionTypeColor = useCallback((type: string) => {
    switch (type.toLowerCase()) {
      case 'pain':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      case 'gain':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
      case 'jobs to be done':
        return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400';
    }
  }, []);

  const getQuestionTypeIcon = useCallback((type: string) => {
    switch (type.toLowerCase()) {
      case 'pain':
        return Users;
      case 'gain':
        return Target;
      case 'jobs to be done':
        return HelpCircle;
      default:
        return MessageSquare;
    }
  }, []);

  const handleRetry = useCallback(() => {
    clearCache();
    setQuestionnaires([]);
    setError(null);
    setIsLoaded(false);
    fetchOrGenerateQuestionnaires();
  }, [clearCache, fetchOrGenerateQuestionnaires]);

  const startEditing = useCallback((questionnaire: Questionnaire) => {
    setEditingId(questionnaire.id);
    setEditingText(questionnaire.text);
  }, []);

  const cancelEditing = useCallback(() => {
    setEditingId(null);
    setEditingText("");
  }, []);

  const saveEditing = useCallback(async () => {
    if (!editingId) return;

    const sanitizedText = sanitizeInput(editingText);

    if (!sanitizedText.trim()) {
      toast.error("Question text cannot be empty");
      return;
    }

    const updatedQuestionnaires = questionnaires.map(questionnaire => 
      questionnaire.id === editingId 
        ? { ...questionnaire, text: sanitizedText }
        : questionnaire
    );

    const success = await saveQuestionnaires(updatedQuestionnaires);
    if (success) {
      cancelEditing();
    }
  }, [editingId, editingText, questionnaires, sanitizeInput, saveQuestionnaires, cancelEditing]);

  // Persona selector component
  const PersonaSelector = ({ compact = false }: { compact?: boolean }) => {
    if (availablePersonas.length === 0) {
      if (process.env.NODE_ENV === 'development') {
        console.log('⚠️ PersonaSelector hidden: no personas available');
      }
      return null;
    }

    if (process.env.NODE_ENV === 'development') {
      console.log('✅ PersonaSelector rendering with personas:', availablePersonas);
    }

    return (
      <div className={`flex justify-center ${compact ? 'mb-2 -mt-2' : 'mb-2 -mt-2'}`}>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm">
          <Tabs 
            value={selectedPersona || availablePersonas[0]} 
            onValueChange={(value) => setSelectedPersona(value)}
            className="w-full"
          >
            <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${availablePersonas.length}, 1fr)` }}>
              {availablePersonas.map((personaId) => (
                <TabsTrigger 
                  key={personaId} 
                  value={personaId}
                  className="flex items-center gap-2 text-brand-500"
                >
                  <UserCircle2 className="w-4 h-4" />
                  {getPersonaDisplayName(personaId)}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
      </div>
    );
  };

  return (
    <div>
      <FeatureVideoOverlay
        featureId={FEATURE_IDS.QUESTIONNAIRES}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      />
      <PageBreadcrumb pageTitle="Assembling Your Interview Questions" titleSuffix={<CreditCostBadge cost={15} />} />
      <div className=" min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-white/[0.03] xl:px-10">
        
        {/* Loading State */}
        {generating && (
             <motion.div
             initial={{ opacity: 0, y: 20 }}
             animate={{ opacity: 1, y: 0 }}
             transition={{ duration: 0.3 }}
             className="flex flex-col items-center justify-center py-12"
           >
                         <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
             <h3 className="text-lg font-medium text-brand-500 dark:text-brand-400 mb-2">
             Assembling Your interview questions
 
             </h3>
             <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-md">
             Extracting targeted interview questions based on your assumptions to help validate your hypotheses.
             </p>
           </motion.div>

        )}








        {/* Error State */}
        {error && !generating && (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="p-4 rounded-full bg-red-100 dark:bg-red-900/20 mb-4">
              <ScrollText className="w-8 h-8 text-red-600 dark:text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-brand-900 dark:text-white mb-2">
              Failed to Load Questionnaires
            </h3>
            <p className="text-brand-600 dark:text-brand-400 mb-6 text-center max-w-md">
              {error}
            </p>
            <div className="flex gap-3">
              <Button
                onClick={handleRetry}
                className="bg-brand-600 hover:bg-brand-700 text-white"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Try Again
              </Button>
              <Button
                onClick={() => router.push(`/team-workspace/hypothesis/${projectId}`)}
                variant="outline"
              >
                Back to Hypothesis
              </Button>
            </div>
          </div>
        )}

        {/* Empty State - Only show if not generating, no error, and no questionnaires */}
        {!generating && !error && questionnaires.length === 0 && isLoaded && (
           <div className="flex flex-col items-center justify-center py-16">
           <div className="relative">
             <div className="w-16 h-16 border-4 border-brand-200 dark:border-brand-800 rounded-full animate-pulse"></div>
             <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-t-brand-600 rounded-full animate-spin"></div>
           </div>
           <div className="mt-6 text-center">
             <h3 className="text-lg font-semibold text-brand-700 dark:text-white">
               Assembling Your interview questions
             </h3>
             <p className="text-brand-600 dark:text-brand-400 max-w-md text-sm mt-2">
               Extracting targeted interview questions based on your assumptions to help validate your hypotheses...
             </p>
           </div>
         </div>
        )}

        {/* Questionnaires Results */}
        {questionnaires.length > 0 && !generating && (
          <div className="space-y-6">
            {/* Header with actions - Sticky */}
            <div className="sticky top-[130px] z-30 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 -mx-4 xl:-mx-10 px-4 xl:px-10 py-4 shadow-sm">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-brand-100 dark:bg-brand-800">
                    <MessageSquare className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                  </div>
                  <h2 className="text-xl font-bold text-brand-500 dark:text-gray-100">
                    Questionnaires
                  </h2>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    onClick={() => router.push(`/team-workspace/assumptions/${projectId}`)}
                    variant="outline"
                    className="dark:border-brand-600 dark:text-brand-300 dark:hover:bg-brand-800 w-full sm:w-auto"
                  >
                    <ChevronRight className="w-4 h-4 mr-2 rotate-180" />
                    Back to Assumptions
                  </Button>

                  <Button
                    onClick={handleRegenerateQuestionnaires}
                    disabled={generating}
                    className="bg-green-600 hover:bg-green-700 text-white dark:bg-green-500 dark:hover:bg-green-600 w-full sm:w-auto"
                  >
                    {generating ? (
                      <>
                        <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
                        Regenerating...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Regenerate
                      </>
                    )}
                  </Button>

                  <DownloadQuestionnairesDrawer projectId={projectId} />
                </div>
              </div>
            </div>

            {/* Persona Selector */}
            <PersonaSelector />

            {/* Questions grouped by persona */}
            <div className="space-y-8">
              {Object.entries(filteredQuestionnaires.reduce((acc, question) => {
                if (!acc[question.persona_name]) {
                  acc[question.persona_name] = [];
                }
                acc[question.persona_name].push(question);
                return acc;
              }, {} as Record<string, Questionnaire[]>)).map(([personaName, questions], personaIndex) => (
                <motion.div
                  key={personaName}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ 
                    duration: 0.4,
                    delay: personaIndex * 0.2 
                  }}
                  className="space-y-4"
                >
                  {/* Persona Header */}
                  <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 dark:border-green-700 dark:bg-transparent  rounded-lg">
                    <div className="p-2 rounded-full bg-green-100 dark:bg-green-800">
                      <Users className="w-5 h-5 text-green-600 dark:text-green-400" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-green-700 dark:text-white">
                        {personaName}
                      </h3>
                      <p className="text-sm text-brand-600 dark:text-green-400">
                        {questions.length} interview questions
                      </p>
                    </div>
                  </div>

                  {/* Questions for this persona */}
                  <div className="grid gap-4">
                    {questions.map((question, questionIndex) => {
                      const TypeIcon = getQuestionTypeIcon(question.type);
                      return (
                        <motion.div
                          key={question.id}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ 
                            duration: 0.3,
                            delay: (personaIndex * 0.2) + (questionIndex * 0.1)
                          }}
                          className="p-5 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-lg shadow-sm hover:shadow-md hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 group dark:hover:bg-brand-700/50 transition-all duration-200"
                        >
                          {/* Question Header */}
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-3 gap-2">
                           
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-brand-500 dark:text-brand-400">
                                Question #{questionIndex + 1}
                              </span>
                             
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-brand-500 dark:text-brand-400">To validate </span>
                              <span className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full ${getComponentTypeInfo(question.component_type).bgColor} ${getComponentTypeInfo(question.component_type).color} border ${getComponentTypeInfo(question.component_type).borderColor}`}>
                                {getComponentTypeInfo(question.component_type).label}
                              </span>
                              {editingId !== question.id && (
                                <Button
                                  onClick={() => startEditing(question)}
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 px-4 text-brand-500 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-200 hover:bg-brand-100 dark:hover:bg-brand-800"
                                >
                                  <Edit3 className="w-4 h-4" />
                                 <span>Edit</span>
                                </Button>
                              )}
                            </div>
                          </div>
                          
                          {/* Question Text */}
                          <div className="mb-4">
                            {editingId === question.id ? (
                              <div className="space-y-3">
                                <Textarea
                                  value={editingText}
                                  onChange={(e) => setEditingText(e.target.value)}
                                  className="min-h-[80px] resize-none dark:bg-brand-900/50 dark:border-brand-700"
                                  placeholder="Enter question text..."
                                />
                               
                              </div>
                            ) : (
                              <p className="text-brand-700 dark:text-brand-200 leading-relaxed text-base">
                                {question.text}
                              </p>
                            )}
                          </div>

                          {editingId === question.id && (
                            <div className="flex gap-2 my-2 justify-end">
                              <Button
                                onClick={saveEditing}
                                disabled={saving || !editingText.trim()}
                                size="sm"
                                className="bg-brand-600 hover:bg-brand-700 text-white"
                              >
                                {saving ? (
                                  <>
                                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                                    Saving...
                                  </>
                                ) : (
                                  <>
                                    <Save className="w-4 h-4 mr-2" />
                                    Save
                                  </>
                                )}
                              </Button>
                              <Button
                                onClick={cancelEditing}
                                disabled={saving}
                                variant="outline"
                                size="sm"
                              >
                                <X className="w-4 h-4 mr-2" />
                                Cancel
                              </Button>
                            </div>
                          )}

                          {/* Question Metadata */}
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pt-3 border-t border-brand-200 dark:border-brand-700 text-xs text-brand-500 dark:text-brand-400">
                            
                            <span>Generated on {formatDate(question.generated_at)}</span>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Continue Button */}
            <div className="flex justify-center pt-6">
              <Button
                onClick={() => router.push(`/team-workspace/projects-questionnaire-completed`)}
                className="bg-brand-600 hover:bg-brand-700 text-white dark:bg-brand-500 dark:hover:bg-brand-600"
              >
                Continue to Next Step
                <ChevronRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}