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
import { Lightbulb, CheckCircle, RefreshCw, ChevronRight, ScrollText, Edit3, Save, X, Loader2, UserCircle2, Target, Frown, TrendingUp } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import toast from "react-hot-toast";
import { motion } from "framer-motion";

interface Assumption {
  id: string;
  text: string;
  component_type: 'jtbd' | 'pain' | 'gain';
  evidence: string[];
  hypothesis_id: string;
  persona_name: string;
  persona_id: string;
  generated_at: string;
  quality_validation?: {
    is_valid: boolean;
    warnings: string[];
    has_current_state_language: boolean;
  };
}

interface AssumptionResponse {
  assumptions: Assumption[];
  project_id: string;
  stage: string;
  total_assumptions: number;
  hypotheses_count: number;
  hypotheses_reference: {
    id: string;
    text: string;
    evidence: string[];
    persona_id: string;
    generated_at: string;
    persona_name: string;
  }[];
}

// Interface for existing assumptions (GET endpoint)
interface ExistingAssumptionsResponse {
  success: boolean;
  data: {
    assumptions: Assumption[];
    project_id: string;
    stage: string;
    total_assumptions: number;
    hypotheses_count: number;
    hypotheses_reference: {
      id: string;
      text: string;
      evidence: string[];
      persona_id: string;
      generated_at: string;
      persona_name: string;
    }[];
  };
  message: string;
}

// Interface for editing assumptions (PUT endpoint)
interface EditAssumptionsRequest {
  assumptions: Assumption[];
}

interface EditAssumptionsResponse {
  success: boolean;
  data: any;
  message: string;
}

export default function AssumptionsPage() {
  const params = useParams();
  const projectId = params.id as string;
  const router = useRouter();
  const featureConfig = getFeatureVideoConfig(FEATURE_IDS.ASSUMPTIONS);
  const [generating, setGenerating] = useState(false);
  const [assumptions, setAssumptions] = useState<Assumption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");
  const [editingEvidence, setEditingEvidence] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  
  // Persona toggle state
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [availablePersonas, setAvailablePersonas] = useState<string[]>([]);

  // Cache management functions
  const getCacheKey = useCallback(() => `assumptions_${projectId}`, [projectId]);
  const getCacheTimestampKey = useCallback(() => `assumptions_${projectId}_timestamp`, [projectId]);

  const saveToCache = useCallback((data: Assumption[]) => {
    try {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem(getCacheKey(), JSON.stringify(data));
        sessionStorage.setItem(getCacheTimestampKey(), Date.now().toString());
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to save assumptions to cache:', error);
      }
    }
  }, [getCacheKey, getCacheTimestampKey]);

  const getFromCache = useCallback((): { data: Assumption[] | null; isExpired: boolean } => {
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
        console.error('Failed to get assumptions from cache:', error);
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
        console.error('Failed to clear assumptions cache:', error);
      }
    }
  }, [getCacheKey, getCacheTimestampKey]);

  // Check for existing assumptions first (GET endpoint)
  const checkExistingAssumptions = useCallback(async (signal: AbortSignal): Promise<Assumption[] | null> => {
    try {
      const token = authService.getCurrentToken();
      if (!token) {
        toast.error("Authentication required. Please sign in again.");
        router.push("/signin");
        return null;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/field-prep/assumptions`,
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
        const result: ExistingAssumptionsResponse = await response.json();
        if (process.env.NODE_ENV === 'development') {
          console.log('✅ Loaded existing assumptions:', result.data.assumptions.length);
        }
        return result.data.assumptions || [];
      } else if (response.status === 404) {
        // No existing assumptions found, will need to generate
        if (process.env.NODE_ENV === 'development') {
          console.log('ℹ️ No existing assumptions found, will generate new ones');
        }
        return null;
      } else if (response.status === 401) {
        toast.error("Session expired. Please sign in again.");
        router.push("/signin");
        return null;
      } else {
        throw new Error(`Failed to check existing assumptions: ${response.status}`);
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Check existing assumptions request aborted');
        }
        return null;
      }
      throw error;
    }
  }, [projectId, router]);

  // Generate new assumptions (POST endpoint)
  const generateNewAssumptions = useCallback(async (signal: AbortSignal): Promise<Assumption[]> => {
    const token = authService.getCurrentToken();
    if (!token) {
      toast.error("Authentication required. Please sign in again.");
      router.push("/signin");
      throw new Error("No authentication token");
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/field-prep/assumptions`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          max_assumptions: 2
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
      throw new Error(`Failed to generate assumptions: ${response.status}`);
    }

    const data: AssumptionResponse = await response.json();
    if (process.env.NODE_ENV === 'development') {
      console.log('✅ Generated new assumptions:', data.assumptions.length);
    }
    return data.assumptions || [];
  }, [projectId, router]);

  // Regenerate assumptions handler
  const handleRegenerateAssumptions = useCallback(async () => {
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
      setAssumptions([]);
      clearCache();

      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 Regenerating assumptions...');
      }

      // Generate new assumptions
      const newAssumptions = await generateNewAssumptions(signal);
      
      setAssumptions(newAssumptions);
      saveToCache(newAssumptions);
      toast.success("Assumptions regenerated successfully!");
      
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Regenerate assumptions request aborted');
        }
        return;
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error("Error regenerating assumptions:", err);
      }
      const errorMessage = err instanceof Error ? err.message : "Failed to regenerate assumptions";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setGenerating(false);
      abortControllerRef.current = null;
    }
  }, [generateNewAssumptions, clearCache, saveToCache]);

  // Main function to fetch or generate assumptions
  const fetchOrGenerateAssumptions = useCallback(async () => {
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

      // First, check for existing assumptions
      const existingAssumptions = await checkExistingAssumptions(signal);
      
      let finalAssumptions: Assumption[];
      
      if (existingAssumptions && existingAssumptions.length > 0) {
        // Use existing assumptions
        finalAssumptions = existingAssumptions;
        toast.success("Loaded existing assumptions");
      } else {
        // Generate new assumptions
        finalAssumptions = await generateNewAssumptions(signal);
        toast.success("Generated new assumptions successfully!");
      }

      setAssumptions(finalAssumptions);
      saveToCache(finalAssumptions);
      
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Assumptions request aborted');
        }
        return;
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error("Error fetching/generating assumptions:", err);
      }
      const errorMessage = err instanceof Error ? err.message : "Failed to load assumptions";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setGenerating(false);
      setIsLoaded(true);
      abortControllerRef.current = null;
    }
  }, [checkExistingAssumptions, generateNewAssumptions, saveToCache]);

  // Initialize assumptions on component mount
  useEffect(() => {
    if (!projectId || isLoaded) return;

    // Try to load from cache first
    const { data: cachedData, isExpired } = getFromCache();
    
    if (cachedData && !isExpired) {
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Loaded assumptions from cache:', cachedData.length);
      }
      setAssumptions(cachedData);
      setIsLoaded(true);
    } else {
      // Cache is empty or expired, fetch from API
      fetchOrGenerateAssumptions();
    }
  }, [projectId, isLoaded, getFromCache, fetchOrGenerateAssumptions]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  // Memoized formatDate function
  const formatDate = useCallback((dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return "Invalid date";
    }
  }, []);

  const handleRetry = useCallback(() => {
    clearCache(); // Clear cache to ensure fresh data
    setAssumptions([]);
    setError(null);
    setIsLoaded(false);
    fetchOrGenerateAssumptions();
  }, [clearCache, fetchOrGenerateAssumptions]);

  // Input sanitization function
  const sanitizeInput = useCallback((input: string): string => {
    return input
      .replace(/<[^>]*>/g, '') // Remove HTML tags
      .substring(0, 2000) // Limit length
      .trim();
  }, []);

  // Edit assumptions (PUT endpoint)
  const saveAssumptions = useCallback(async (updatedAssumptions: Assumption[]): Promise<boolean> => {
    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Create new AbortController
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

      const requestBody: EditAssumptionsRequest = {
        assumptions: updatedAssumptions
      };

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/field-prep/assumptions`,
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
        throw new Error(`Failed to save assumptions: ${response.status}`);
      }

      const result: EditAssumptionsResponse = await response.json();
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Saved assumptions:', result.message);
      }
      
      // Update local state and cache
      setAssumptions(updatedAssumptions);
      saveToCache(updatedAssumptions);
      toast.success("Assumptions saved successfully!");
      return true;

    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Save assumptions request aborted');
        }
        return false;
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error("Error saving assumptions:", error);
      }
      const errorMessage = error instanceof Error ? error.message : "Failed to save assumptions";
      toast.error(errorMessage);
      return false;
    } finally {
      setSaving(false);
      abortControllerRef.current = null;
    }
  }, [projectId, router, saveToCache]);

  // Editing functions
  const startEditing = useCallback((assumption: Assumption) => {
    setEditingId(assumption.id);
    setEditingText(assumption.text);
    setEditingEvidence([...assumption.evidence]);
  }, []);

  const cancelEditing = useCallback(() => {
    setEditingId(null);
    setEditingText("");
    setEditingEvidence([]);
  }, []);

  const saveEditing = useCallback(async () => {
    if (!editingId) return;

    const sanitizedText = sanitizeInput(editingText);
    const sanitizedEvidence = editingEvidence.map(evidence => sanitizeInput(evidence));

    if (!sanitizedText.trim()) {
      toast.error("Assumption text cannot be empty");
      return;
    }

    const updatedAssumptions = assumptions.map(assumption => 
      assumption.id === editingId 
        ? { 
            ...assumption, 
            text: sanitizedText,
            evidence: sanitizedEvidence.filter(e => e.trim() !== '')
          }
        : assumption
    );

    const success = await saveAssumptions(updatedAssumptions);
    if (success) {
      cancelEditing();
    }
  }, [editingId, editingText, editingEvidence, assumptions, sanitizeInput, saveAssumptions, cancelEditing]);

  const updateEvidenceItem = useCallback((index: number, value: string) => {
    const newEvidence = [...editingEvidence];
    newEvidence[index] = value;
    setEditingEvidence(newEvidence);
  }, [editingEvidence]);

  const addEvidenceItem = useCallback(() => {
    setEditingEvidence([...editingEvidence, ""]);
  }, [editingEvidence]);

  const removeEvidenceItem = useCallback((index: number) => {
    const newEvidence = editingEvidence.filter((_, i) => i !== index);
    setEditingEvidence(newEvidence);
  }, [editingEvidence]);

  // Initialize personas and selected persona from assumptions data
  useEffect(() => {
    if (assumptions.length > 0 && availablePersonas.length === 0) {
      const personaIds = new Set<string>();
      assumptions.forEach(assumption => {
        if (assumption.persona_id) {
          personaIds.add(assumption.persona_id);
        }
      });
      
      const personas = Array.from(personaIds).sort();
      setAvailablePersonas(personas);
      
      // Set first persona as default if not already set
      if (personas.length > 0 && !selectedPersona) {
        setSelectedPersona(personas[0]);
        
        if (process.env.NODE_ENV === 'development') {
          console.log('Initialized selected persona to:', personas[0]);
        }
      }
    }
  }, [assumptions, availablePersonas.length, selectedPersona]);

  // Get display name for persona
  const getPersonaDisplayName = useCallback((personaId: string | null) => {
    if (!personaId) return "All Personas";
    if (personaId === "all") return "All Personas";
    
    // Try to find the persona name from assumptions
    const assumption = assumptions.find(a => a.persona_id === personaId);
    if (assumption?.persona_name) {
      return assumption.persona_name;
    }
    
    // Fallback to persona ID formatting
    if (personaId.includes('_')) {
      const parts = personaId.split('_');
      const lastPart = parts[parts.length - 1];
      if (!isNaN(Number(lastPart))) {
        return `Persona ${lastPart}`;
      }
    }
    
    return `Persona ${personaId}`;
  }, [assumptions]);

  // Filter assumptions by selected persona
  const filteredAssumptions = useMemo(() => {
    if (!selectedPersona) {
      return assumptions;
    }
    return assumptions.filter(assumption => assumption.persona_id === selectedPersona);
  }, [assumptions, selectedPersona]);

  // Get component type icon and color
  const getComponentTypeInfo = useCallback((type: 'jtbd' | 'pain' | 'gain') => {
    switch (type) {
      case 'jtbd':
        return {
          icon: Target,
          color: 'text-green-600 dark:text-green-400',
          bgColor: 'bg-green-50 dark:bg-green-800/30',
          borderColor: 'border-green-200 dark:border-green-600',
          label: 'Customer Jobs-to-be-Done'
        };
      case 'pain':
        return {
          icon: Frown,
          color: 'text-red-600 dark:text-red-400',
          bgColor: 'bg-red-50 dark:bg-red-800/30',
          borderColor: 'border-red-200 dark:border-red-600',
          label: 'Customer Pains'
        };
      case 'gain':
        return {
          icon: TrendingUp,
          color: 'text-blue-600 dark:text-blue-400',
          bgColor: 'bg-blue-50 dark:bg-blue-800/30',
          borderColor: 'border-blue-200 dark:border-blue-600',
          label: 'Customer Gains'
        };
    }
  }, []);

  // Persona selector component
  const PersonaSelector = ({ compact = false }: { compact?: boolean }) => {
    if (availablePersonas.length <= 1) return null;

    return (
      <div className={`flex justify-center ${compact ? 'mb-2 -mt-2' : 'mb-2 -mt-2'}`}>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm">
          <Tabs 
            value={selectedPersona || "all"} 
            onValueChange={(value) => setSelectedPersona(value === "all" ? null : value)}
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
        featureId={FEATURE_IDS.ASSUMPTIONS}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      />
      <PageBreadcrumb pageTitle="Framing Your Key Assumptions" titleSuffix={<CreditCostBadge cost={5} />} />
      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-white/[0.03] xl:px-10">
        

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
              Framing Your Key Assumptions
  
              </h3>
              <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-md">
              Analyzing your personas and generating assumptions for Market Research.
              </p>
            </motion.div>
        )}


    

        {/* Error State */}
        {error && !generating && (
          <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center justify-center py-12"
        >
                      <ScrollText className="w-8 h-8 text-red-600 dark:text-red-400" />
          <h3 className="text-lg font-medium text-brand-500 dark:text-brand-400 mb-2">
          Failed to Load Assumptions
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
                onClick={() => router.push(`/team-workspace/vpc/${projectId}`)}
                variant="outline"
              >
                Back to VPC
              </Button>
            </div>
          </motion.div>
        )}

        {/* Empty State - Only show if not generating, no error, and no assumptions */}
        {!generating && !error && assumptions.length === 0 && isLoaded && (
          <div className="flex flex-col items-center justify-center py-16">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-brand-200 dark:border-brand-800 rounded-full animate-pulse"></div>
            <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-t-brand-600 rounded-full animate-spin"></div>
          </div>
          <div className="mt-6 text-center">
            <h3 className="text-lg font-semibold text-brand-700 dark:text-white">
              Framing Your Key Assumptions
            </h3>
            <p className="text-brand-600 dark:text-brand-400 max-w-md text-sm mt-2">
              Analyzing your personas and generating assumptions for Market Research.
            </p>
          </div>
        </div>
        )}

        {/* Assumptions Results */}
        {assumptions.length > 0 && !generating && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-200 dark:border-gray-800 pb-4">
              <div className="flex items-center gap-3 flex-wrap">
                <CheckCircle className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                <h2 className="text-xl font-bold text-brand-500 dark:text-gray-100">
                  Assumptions
                </h2>
              </div>
              <div className="flex items-center gap-2">

              <Button
                onClick={() => router.push(`/team-workspace/vpc/${projectId}`)}
                variant="outline"
                className="dark:border-brand-600 dark:text-brand-300 dark:hover:bg-brand-800 w-full sm:w-auto"
              >
                <ChevronRight className="w-4 h-4 mr-2 rotate-180" />
                Back to VPC
              </Button>

              <Button
                onClick={handleRegenerateAssumptions}
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
                    Reframe Assumptions
                  </>
                )}
              </Button>
             
          </div>

            </div>

            {/* Persona Selector */}
            <PersonaSelector />

            <div className="grid gap-4">
              {filteredAssumptions.map((assumption, index) => {
                const typeInfo = getComponentTypeInfo(assumption.component_type);
                const TypeIcon = typeInfo.icon;
                
                return (
                  <motion.div
                    key={`${assumption.id}-${assumption.persona_id}-${index}`}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ 
                      duration: 0.4,
                      delay: index * 0.1 
                    }}
                    className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 group dark:hover:bg-brand-700/50 transition-all duration-200 relative"
                  >
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-brand-500 dark:text-brand-400">
                          Assumption #{index + 1}
                        </span>
                        <Badge 
                          className={`${typeInfo.bgColor} ${typeInfo.borderColor} border flex items-center gap-1`}
                        >
                          <TypeIcon className={`w-3 h-3 ${typeInfo.color}`} />
                          <span className={`text-xs font-medium ${typeInfo.color}`}>
                            {typeInfo.label}
                          </span>
                        </Badge>
                      </div>
                    
                      <div className="flex items-center gap-2">
                        <span 
                          className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium bg-brand-50 dark:bg-brand-800 text-brand-700 dark:text-brand-200 rounded-full"
                        >
                          <UserCircle2 className="w-3 h-3" />
                          {assumption.persona_name}
                        </span>
                       
                        {editingId !== assumption.id && (
                          <Button
                            onClick={() => startEditing(assumption)}
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
                    
                    {/* Assumption Statement */}
                    <div className="mb-6">
                      
                      {editingId === assumption.id ? (
                        <div className="space-y-3">
                          <Textarea
                            value={editingText}
                            onChange={(e) => setEditingText(e.target.value)}
                            className="min-h-[100px] resize-none dark:bg-brand-900/50 dark:border-brand-700"
                            placeholder="Enter assumption text..."
                          />
                         
                        </div>
                      ) : (
                        <p className="text-brand-700 dark:text-brand-200 leading-relaxed text-md bg-brand-50 dark:bg-brand-800/50 p-4 rounded-lg border border-brand-200 dark:border-brand-700 transition-colors">
                          {assumption.text}
                        </p>
                      )}
                    </div>
                    
                    {/* Supporting Evidence */}
                    <div>
                      <h5 className="font-semibold text-brand-500 dark:text-brand-100 mb-3 text-base">
                        Supporting Evidence:
                      </h5>
                      {editingId === assumption.id ? (
                        <div className="space-y-3">
                          {editingEvidence.map((evidence, evidenceIndex) => (
                            <div key={evidenceIndex} className="flex items-start gap-2">
                              <div className="flex-shrink-0 w-6 h-6 bg-brand-500 text-white rounded-full flex items-center justify-center text-xs font-bold mt-2">
                                {evidenceIndex + 1}
                              </div>
                              <Textarea
                                value={evidence}
                                onChange={(e) => updateEvidenceItem(evidenceIndex, e.target.value)}
                                className="flex-1 min-h-[60px] resize-none dark:bg-brand-900/50 dark:border-brand-700"
                                placeholder={`Evidence item ${evidenceIndex + 1}...`}
                              />
                              <Button
                                onClick={() => removeEvidenceItem(evidenceIndex)}
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 mt-2 hover:bg-red-100 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400"
                              >
                                <X className="w-4 h-4" />
                              </Button>
                            </div>
                          ))}
                          <Button
                            onClick={addEvidenceItem}
                            variant="outline"
                            size="sm"
                            className="w-full"
                          >
                            Add Evidence Item
                          </Button>
                        </div>
                      ) : (
                        <div className="grid gap-3">
                          {assumption.evidence && assumption.evidence.length > 0 ? (
                            assumption.evidence.map((evidence, evidenceIndex) => (
                              <div
                                key={evidenceIndex}
                                className="flex items-start gap-3 p-3 bg-brand-50 dark:bg-brand-800/30 rounded-lg group-hover:bg-brand-100 dark:group-hover:bg-brand-800/50 transition-colors"
                              >
                                <div 
                                  className="flex-shrink-0 w-6 h-6 bg-brand-500 text-white rounded-full flex items-center justify-center text-xs font-bold mt-0.5"
                                >
                                  {evidenceIndex + 1}
                                </div>
                                <p className="text-brand-600 dark:text-brand-200 leading-relaxed text-sm">
                                  {evidence}
                                </p>
                              </div>
                            ))
                          ) : (
                            <p className="text-brand-500 dark:text-brand-400 text-sm italic">
                              No evidence provided
                            </p>
                          )}
                        </div>
                      )}
                    </div>

                    {editingId === assumption.id && (
                      <div className="flex gap-2 mt-4 justify-end">
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

                    {/* Generated timestamp */}
                    <div className="mt-4 pt-3 border-t border-brand-200 dark:border-brand-700">
                      <p className="text-xs text-brand-500 dark:text-brand-400">
                        Generated on {formatDate(assumption.generated_at)}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* Continue Button - NEW WORKFLOW: After assumptions, go to hypothesis */}
            <div className="flex justify-center pt-6">
              <Button
                onClick={() => {
                  setIsNavigating(true);
                  router.push(`/team-workspace/hypothesis/${projectId}`);
                }}
                disabled={isNavigating}
                aria-busy={isNavigating}
                className="bg-brand-600 hover:bg-brand-700 text-white dark:bg-brand-500 dark:hover:bg-brand-600 flex items-center"
              >
                {isNavigating ? (
                  <>
                                <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
                    Continuing...
                  </>
                ) : (
                  <>
                    Continue to Next Step ( Hypothesis ) 
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}