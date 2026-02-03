"use client";

import PageBreadcrumb from "@/components/common/module 2/PageBreadCrumb";
import CreditCostBadge from "@/components/common/CreditCostBadge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { authService } from "@/services/authService";
import FeatureVideoOverlay from "@/components/feature-videos/FeatureVideoOverlay";
import { FEATURE_IDS, getFeatureVideoConfig } from "@/lib/featureVideos";
import { Lightbulb, CheckCircle, RefreshCw, ChevronRight, ScrollText, Edit3, Save, X, Plus, Trash2, Loader2, UserCircle2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import toast from "react-hot-toast";
import { motion } from "framer-motion";

interface HypothesisText {
  we_believe_that: string;
  are_struggling_with: string;
  thus: string;
  that_guarantees: string;
}

interface Hypothesis {
  id: string;
  text: HypothesisText | string;
  evidence: string[];
  persona_id: string;
  persona_name: string;
  generated_at: string;
}

// Helper functions for hypothesis text handling
function isStructuredHypothesisText(text: HypothesisText | string): text is HypothesisText {
  return typeof text === 'object' && 
         text !== null && 
         'we_believe_that' in text;
}

function formatHypothesisText(text: HypothesisText | string): string {
  if (isStructuredHypothesisText(text)) {
    return `We believe that ${text.we_believe_that} are struggling with ${text.are_struggling_with}, thus ${text.thus}, that guarantees ${text.that_guarantees}`;
  }
  return text;
}

interface HypothesisResponse {
  hypothesis: Hypothesis[];
  project_id: string;
  stage: string;
  context_summary: Record<string, unknown>;
  total_hypotheses: number;
  personas_count: number;
}

interface GetHypothesesResponse {
  success: boolean;
  data: {
    project_id: string;
    hypotheses: Hypothesis[];
    total_hypotheses: number;
    generated_at: string;
    stage: string;
  };
  message: string;
}

interface EditHypothesesRequest {
  hypotheses: Hypothesis[];
}

interface EditHypothesesResponse {
  success: boolean;
  data: Record<string, unknown>;
  message: string;
}

export default function HypothesisPage() {
  const params = useParams();
  const projectId = params.id as string;
  const router = useRouter();
  const featureConfig = getFeatureVideoConfig(FEATURE_IDS.HYPOTHESIS);
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingHypothesis, setEditingHypothesis] = useState<Hypothesis | null>(null);
  const [saving, setSaving] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  
  // Persona toggle state
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [availablePersonas, setAvailablePersonas] = useState<string[]>([]);
  
  // AbortController for request cancellation
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  // Function to fetch existing hypotheses
  const fetchExistingHypotheses = useCallback(async (signal?: AbortSignal) => {
    try {
      setLoading(true);
      setError(null);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('=== FETCH EXISTING HYPOTHESES DEBUG ===');
        console.log('Project ID:', projectId);
      }
      
      const token = authService.getCurrentToken();
      
      if (!token) {
        toast.error("Authentication required. Please sign in again.");
        router.push("/signin");
        return null;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/field-prep/hypotheses`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          signal,
        }
      );

      if (signal?.aborted) {
        if (process.env.NODE_ENV === 'development') {
          console.log('Fetch hypotheses request was aborted');
        }
        return null;
      }

      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Session expired. Please sign in again.");
          authService.logout();
          router.push("/signin");
          return null;
        }
        // If no hypotheses exist (404), this is not an error - we'll generate them
        if (response.status === 404) {
          if (process.env.NODE_ENV === 'development') {
            console.log('No existing hypotheses found (404)');
          }
          return null;
        }
        throw new Error(`Failed to fetch hypotheses: ${response.status}`);
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('Response:', response);
      }

      const data: GetHypothesesResponse = await response.json();

      console.log('Dataaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:', data);
      
      if (data.success && data.data && data.data.hypotheses && data.data.hypotheses.length > 0) {
        const existingHypotheses = data.data.hypotheses;
        
        if (!isMountedRef.current) return null;
        
        setHypotheses(existingHypotheses);
        
        if (process.env.NODE_ENV === 'development') {
          console.log('Loaded existing hypotheses:', existingHypotheses.length);
        }
        
        return existingHypotheses;
      }
      
      return null;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Fetch hypotheses request was aborted');
        }
        return null;
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error("Error fetching hypotheses:", err);
      }
      // Don't show error for failed fetch - we'll try to generate instead
      return null;
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [projectId, router]);

  const generateHypotheses = useCallback(async (signal?: AbortSignal) => {
    try {
      setGenerating(true);
      setError(null);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('=== GENERATE HYPOTHESES DEBUG ===');
        console.log('Project ID:', projectId);
      }
      
      const token = authService.getCurrentToken();
      
      if (!token) {
        toast.error("Authentication required. Please sign in again.");
        router.push("/signin");
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/field-prep/hypothesis`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            creativity_level: 0.5
          }),
          signal,
        }
      );

      if (signal?.aborted) {
        if (process.env.NODE_ENV === 'development') {
          console.log('Generate hypotheses request was aborted');
        }
        return;
      }

      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Session expired. Please sign in again.");
          authService.logout();
          router.push("/signin");
          return;
        }
        throw new Error(`Failed to generate hypotheses: ${response.status}`);
      }

      const data: HypothesisResponse = await response.json();
      const newHypotheses = data.hypothesis || [];
      
      if (!isMountedRef.current) return;
      
      setHypotheses(newHypotheses);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Generated hypotheses:', newHypotheses.length);
      }
      
      toast.success(`Generated ${newHypotheses.length} hypotheses successfully!`);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Generate hypotheses request was aborted');
        }
        return;
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error("Error generating hypotheses:", err);
      }
      const errorMessage = err instanceof Error ? err.message : "Failed to generate hypotheses";
      
      if (isMountedRef.current) {
        setError(errorMessage);
        toast.error(errorMessage);
      }
    } finally {
      if (isMountedRef.current) {
        setGenerating(false);
      }
    }
  }, [projectId, router]);

  // Initialize data loading
  useEffect(() => {
    if (!projectId) return;
    
    // Create new AbortController for this effect
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    // Start loading process
    if (process.env.NODE_ENV === 'development') {
      console.log('Starting hypothesis loading process');
    }
    
    fetchExistingHypotheses(signal).then((existingHypotheses) => {
      // If no existing hypotheses were found and component is still mounted, generate new ones
      if (!existingHypotheses && !signal.aborted && isMountedRef.current && !generating) {
        if (process.env.NODE_ENV === 'development') {
          console.log('No existing hypotheses found, generating new ones');
        }
        generateHypotheses(signal);
      }
    }).catch((error) => {
      if (process.env.NODE_ENV === 'development') {
        console.error('Error in hypothesis loading process:', error);
      }
    });

    return () => {
      if (abortControllerRef.current && !abortControllerRef.current.signal.aborted) {
        abortControllerRef.current.abort();
      }
    };
  }, [projectId]); // Removed circular dependencies

  // Extract unique personas from hypotheses
  useEffect(() => {
    if (hypotheses.length > 0 && availablePersonas.length === 0) {
      const personaIds = new Set<string>();
      
      hypotheses.forEach(hypothesis => {
        if (hypothesis.persona_id) {
          personaIds.add(hypothesis.persona_id);
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
  }, [hypotheses, availablePersonas.length, selectedPersona]);

  // Get display name for persona
  const getPersonaDisplayName = useCallback((personaId: string | null) => {
    if (!personaId) return "All Personas";
    if (personaId === "all") return "All Personas";
    
    // Try to find the persona name from hypotheses
    const hypothesis = hypotheses.find(h => h.persona_id === personaId);
    if (hypothesis?.persona_name) {
      return hypothesis.persona_name;
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
  }, [hypotheses]);

  // Filter hypotheses by selected persona
  const filteredHypotheses = useMemo(() => {
    if (!selectedPersona) {
      return hypotheses;
    }
    return hypotheses.filter(hypothesis => hypothesis.persona_id === selectedPersona);
  }, [hypotheses, selectedPersona]);

  // Persona selector component
  const PersonaSelector = ({ compact = false }: { compact?: boolean }) => {
    if (availablePersonas.length <= 1) return null;

    return (
      <div className={`flex justify-center ${compact ? 'my-4' : 'my-4'}`}>
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

  const formatDate = useCallback((dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return "Invalid date";
    }
  }, []);

  const handleRetry = useCallback(() => {
    setHypotheses([]);
    setError(null);
    setLoading(true);
    
    // Create new AbortController for retry
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;
    
    generateHypotheses(signal);
  }, [generateHypotheses]);

  const handleFetchAndRegenerate = useCallback(() => {
    setHypotheses([]);
    setError(null);
    setLoading(true);
    
    // Create new AbortController for regenerate
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;
    
    fetchExistingHypotheses(signal).then((existingHypotheses) => {
      if (!existingHypotheses && !signal.aborted && isMountedRef.current) {
        generateHypotheses(signal);
      }
    });
  }, [fetchExistingHypotheses, generateHypotheses]);

  // Edit functionality
  const handleEditStart = useCallback((hypothesis: Hypothesis) => {
    setEditingId(hypothesis.id);
    setEditingHypothesis({ ...hypothesis });
  }, []);

  const handleEditCancel = useCallback(() => {
    setEditingId(null);
    setEditingHypothesis(null);
  }, []);

  const handleEditSave = useCallback(async () => {
    if (!editingHypothesis || !editingId) return;

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
      setError(null);

      if (process.env.NODE_ENV === 'development') {
        console.log('=== SAVE HYPOTHESIS DEBUG ===');
        console.log('Project ID:', projectId);
        console.log('Editing hypothesis:', editingHypothesis);
      }

      const token = authService.getCurrentToken();
      
      if (!token) {
        toast.error("Authentication required. Please sign in again.");
        router.push("/signin");
        return;
      }

      // Sanitize and validate the hypothesis data
      const sanitizeText = (text: HypothesisText | string): HypothesisText | string => {
        if (isStructuredHypothesisText(text)) {
          return {
            we_believe_that: text.we_believe_that.replace(/[<>]/g, '').trim().slice(0, 100),
            are_struggling_with: text.are_struggling_with.replace(/[<>]/g, '').trim().slice(0, 300),
            thus: text.thus.replace(/[<>]/g, '').trim().slice(0, 200),
            that_guarantees: text.that_guarantees.replace(/[<>]/g, '').trim().slice(0, 300)
          };
        }
        return text.replace(/[<>]/g, '').trim().slice(0, 2000);
      };

      const sanitizedHypothesis: Hypothesis = {
        id: editingHypothesis.id,
        text: sanitizeText(editingHypothesis.text),
        evidence: editingHypothesis.evidence
          .map(evidence => evidence.replace(/[<>]/g, '').trim().slice(0, 1000))
          .filter(evidence => evidence.length > 0),
        persona_id: editingHypothesis.persona_id,
        persona_name: editingHypothesis.persona_name,
        generated_at: editingHypothesis.generated_at
      };

      // Validate required fields
      const isTextValid = isStructuredHypothesisText(sanitizedHypothesis.text) 
        ? sanitizedHypothesis.text.we_believe_that.trim() !== ''
        : (sanitizedHypothesis.text as string).trim() !== '';
      
      if (!isTextValid) {
        toast.error("Hypothesis text is required");
        return;
      }

      if (!sanitizedHypothesis.id || !sanitizedHypothesis.persona_id) {
        toast.error("Invalid hypothesis data");
        return;
      }

      // Update the hypothesis in the current list
      const updatedHypotheses = hypotheses.map(h => 
        h.id === editingId ? sanitizedHypothesis : h
      );

      let requestBody: any = {
        hypotheses: updatedHypotheses
      };

      // Some backends might expect wrapped format
      const alternativeRequestBody = {
        data: {
          hypotheses: updatedHypotheses
        }
      };

      if (process.env.NODE_ENV === 'development') {
        console.log('=== REQUEST DEBUG ===');
        console.log('Request URL:', `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/field-prep/hypotheses`);
        console.log('Request method: PUT');
        console.log('Request headers:', {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        });
        console.log('Primary request body:', JSON.stringify(requestBody, null, 2));
        console.log('Alternative request body:', JSON.stringify(alternativeRequestBody, null, 2));
        console.log('Updated hypotheses count:', updatedHypotheses.length);
        console.log('Sanitized hypothesis:', sanitizedHypothesis);
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/field-prep/hypotheses`,
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

      if (signal.aborted) {
        if (process.env.NODE_ENV === 'development') {
          console.log('Save hypothesis request was aborted');
        }
        return;
      }

      if (!response.ok) {
        if (process.env.NODE_ENV === 'development') {
          console.error('=== RESPONSE ERROR DEBUG ===');
          console.error('Status:', response.status);
          console.error('Status Text:', response.statusText);
          console.error('URL:', response.url);
          console.error('Response headers:', Object.fromEntries(response.headers.entries()));
        }
        
        if (response.status === 401) {
          toast.error("Session expired. Please sign in again.");
          authService.logout();
          router.push("/signin");
          return;
        }
        
        let errorMessage = `Failed to update hypothesis: ${response.status}`;
        
        // Try to get more specific error message from response
        try {
          const responseText = await response.text();
          if (process.env.NODE_ENV === 'development') {
            console.error('Raw response text:', responseText);
            console.error('Response text length:', responseText.length);
          }
          
          if (responseText && responseText.trim().length > 0) {
            try {
              const errorData = JSON.parse(responseText);
              if (process.env.NODE_ENV === 'development') {
                console.error('Parsed error response:', errorData);
              }
              
              if (errorData.message) {
                errorMessage = errorData.message;
              } else if (errorData.detail && Array.isArray(errorData.detail)) {
                // Handle FastAPI validation errors
                const validationErrors = errorData.detail.map((err: any) => 
                  `${err.loc?.join('.')} - ${err.msg}`
                ).join(', ');
                errorMessage = `Validation error: ${validationErrors}`;
              } else if (Object.keys(errorData).length === 0) {
                errorMessage = `Server error: Empty response body (${response.status}). Check server logs for details.`;
              }
            } catch (jsonParseError) {
              if (process.env.NODE_ENV === 'development') {
                console.error('Failed to parse JSON from response:', jsonParseError);
              }
              errorMessage = `Server error: ${responseText.slice(0, 200)}`;
            }
          } else {
            if (process.env.NODE_ENV === 'development') {
              console.error('Empty response body from server - this indicates a server-side processing error');
            }
            errorMessage = `Server returned empty response (${response.status}). This may indicate a server-side validation or processing error. Check the request data format.`;
          }
        } catch (textError) {
          if (process.env.NODE_ENV === 'development') {
            console.error('Failed to read response text:', textError);
          }
          errorMessage = `Failed to read server response (${response.status})`;
        }
        
        throw new Error(errorMessage);
      }

      const data: EditHypothesesResponse = await response.json();
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Save response:', data);
      }
      
      if (data.success) {
        // Update local state
        setHypotheses(updatedHypotheses);
        setEditingId(null);
        setEditingHypothesis(null);
        
        toast.success("Hypothesis updated successfully!");
        
        if (process.env.NODE_ENV === 'development') {
          console.log('Hypothesis updated successfully');
        }
      } else {
        throw new Error(data.message || "Failed to update hypothesis");
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('Save hypothesis request was aborted');
        }
        return;
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error("Error updating hypothesis:", err);
      }
      const errorMessage = err instanceof Error ? err.message : "Failed to update hypothesis";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setSaving(false);
      abortControllerRef.current = null;
    }
  }, [editingHypothesis, editingId, hypotheses, projectId, router]);

  const handleTextChange = useCallback((value: string) => {
    if (editingHypothesis) {
      setEditingHypothesis({
        ...editingHypothesis,
        text: value
      });
    }
  }, [editingHypothesis]);

  const handleStructuredTextChange = useCallback((field: keyof HypothesisText, value: string) => {
    if (editingHypothesis && isStructuredHypothesisText(editingHypothesis.text)) {
      setEditingHypothesis({
        ...editingHypothesis,
        text: {
          ...editingHypothesis.text,
          [field]: value
        }
      });
    }
  }, [editingHypothesis]);

  const handleEvidenceChange = useCallback((index: number, value: string) => {
    if (editingHypothesis) {
      const newEvidence = [...editingHypothesis.evidence];
      newEvidence[index] = value;
      setEditingHypothesis({
        ...editingHypothesis,
        evidence: newEvidence
      });
    }
  }, [editingHypothesis]);

  const handleAddEvidence = useCallback(() => {
    if (editingHypothesis) {
      setEditingHypothesis({
        ...editingHypothesis,
        evidence: [...editingHypothesis.evidence, ""]
      });
    }
  }, [editingHypothesis]);

  const handleRemoveEvidence = useCallback((index: number) => {
    if (editingHypothesis && editingHypothesis.evidence.length > 1) {
      const newEvidence = editingHypothesis.evidence.filter((_, i) => i !== index);
      setEditingHypothesis({
        ...editingHypothesis,
        evidence: newEvidence
      });
    }
  }, [editingHypothesis]);

  return (
    <div>
      <FeatureVideoOverlay
        featureId={FEATURE_IDS.HYPOTHESIS}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      />
      <PageBreadcrumb pageTitle="Framing Your Hypothesis" titleSuffix={<CreditCostBadge cost={5} />} />
      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-white/[0.03] xl:px-10 ">
        
        {/* Initial Loading State */}
        {loading && hypotheses.length === 0 && !generating && (
          <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center justify-center py-12"
        >
                      <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-brand-500 dark:text-brand-400 mb-2">
          Checking for hypotheses...

          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-md">
          We're looking for previously generated hypotheses for your project.
          </p>
        </motion.div>
        )}


        


        {/* Generating State */}
        {generating && (
          
<motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center py-12"
          >
                        <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-brand-500 dark:text-brand-400 mb-2">
            Framing Your Hypothesis

            </h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-md">
            We're analyzing your customer profile selections, and generating a tailored hypothesis...
            </p>
          </motion.div>
        )}






        {/* Error State */}
        {error && !generating && !loading && (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="p-4 rounded-full bg-red-100 dark:bg-red-900/20 mb-4">
              <ScrollText className="w-8 h-8 text-red-600 dark:text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-brand-900 dark:text-white mb-2">
              Failed to Generate Hypotheses
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
                onClick={() => router.push(`/team-workspace/customer-profile/${projectId}`)}
                variant="outline"
              >
                Back to Profiles
              </Button>
            </div>
          </div>
        )}

        {/* Empty State - Only show if not loading, not generating, no error, and no hypotheses */}
        {!loading && !generating && !error && hypotheses.length === 0 && (
        
<motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center py-12"
          >
                        <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-brand-500 dark:text-brand-400 mb-2">
            Framing Your Hypothesis

            </h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-md">
            We're analyzing your customer profile selections, and generating a tailored hypothesis...
            </p>
          </motion.div>
        )}





        {/* Hypotheses Results */}
        {hypotheses.length > 0 && !generating && !loading && (
          <div className="space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-200 dark:border-gray-700 pb-2">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                <h2 className="text-xl font-bold text-brand-500 dark:text-gray-100">
                   Value Hypothesis 
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
                <>
                  <Button
                    onClick={() => {
                      // Cancel any in-flight request
                      if (abortControllerRef.current) {
                        abortControllerRef.current.abort();
                        abortControllerRef.current = null;
                      }
                      // Create a fresh controller for this regenerate action
                      abortControllerRef.current = new AbortController();
                      const signal = abortControllerRef.current.signal;
                      generateHypotheses(signal);
                    }}
                    disabled={generating}
                    aria-busy={generating}
                    className="bg-green-600 hover:bg-green-700 text-white dark:bg-green-500 dark:hover:bg-green-600 w-full sm:w-auto"
                    >
                    {generating ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        Regenerating...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Reframe Hypotheses
                      </>
                    )}
                  </Button>
                </>
               
              </div>
            </div>

            {/* Persona Selector */}
            <PersonaSelector />

            <div className="grid gap-6">
              {filteredHypotheses.map((hypothesis, index) => (
                <motion.div
                  key={hypothesis.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ 
                    duration: 0.4,
                    delay: index * 0.1 
                  }}
                  className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 group dark:hover:bg-brand-700/50 transition-all duration-200 relative"
                >
                  {/* Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-2 gap-2">
                    <div className="flex items-center gap-3">
                      {/* <h4 className="text-lg font-semibold text-brand-500 dark:text-brand-100">
                        Hypothesis Statement
                      </h4> */}
                      <span
                        className="inline-flex items-center px-3 py-1 text-xs font-medium bg-green-100 dark:bg-brand-800 text-brand-700 dark:text-brand-200 rounded-full border border-brand-200 dark:border-brand-700"
                        title={hypothesis.persona_name || hypothesis.persona_id}
                      >
                        Persona : {hypothesis.persona_name || `Persona ${hypothesis.persona_id}`}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                     
                      {editingId !== hypothesis.id && (
                        <Button
                          onClick={() => handleEditStart(hypothesis)}
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
                  
                  {/* Hypothesis Statement */}
                  <div className="mb-6">
                   
                    {editingId === hypothesis.id && editingHypothesis ? (
                      // Edit Mode - Structured inputs with static keywords
                      isStructuredHypothesisText(editingHypothesis.text) ? (
                        <div className="bg-brand-50 dark:bg-brand-800/50 p-4 rounded-lg border border-brand-200 dark:border-brand-700 space-y-4">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-brand-600 dark:text-brand-300 font-bold text-lg whitespace-nowrap">We believe that</span>
                            <input
                              type="text"
                              value={editingHypothesis.text.we_believe_that}
                              onChange={(e) => handleStructuredTextChange('we_believe_that', e.target.value)}
                              className="flex-1 min-w-[200px] px-3 py-1.5 text-brand-700 dark:text-brand-200 bg-white dark:bg-brand-900/50 border border-brand-300 dark:border-brand-600 rounded-lg focus:border-brand-500 dark:focus:border-brand-400 focus:outline-none"
                              placeholder="Target market..."
                            />
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-brand-600 dark:text-brand-300 font-bold text-lg whitespace-nowrap">Are struggling with</span>
                            <input
                              type="text"
                              value={editingHypothesis.text.are_struggling_with}
                              onChange={(e) => handleStructuredTextChange('are_struggling_with', e.target.value)}
                              className="flex-1 min-w-[200px] px-3 py-1.5 text-brand-700 dark:text-brand-200 bg-white dark:bg-brand-900/50 border border-brand-300 dark:border-brand-600 rounded-lg focus:border-brand-500 dark:focus:border-brand-400 focus:outline-none"
                              placeholder="Problem/pain..."
                            />
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-brand-600 dark:text-brand-300 font-bold text-lg whitespace-nowrap">Thus</span>
                            <input
                              type="text"
                              value={editingHypothesis.text.thus}
                              onChange={(e) => handleStructuredTextChange('thus', e.target.value)}
                              className="flex-1 min-w-[200px] px-3 py-1.5 text-brand-700 dark:text-brand-200 bg-white dark:bg-brand-900/50 border border-brand-300 dark:border-brand-600 rounded-lg focus:border-brand-500 dark:focus:border-brand-400 focus:outline-none"
                              placeholder="Action they might adopt..."
                            />
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-brand-600 dark:text-brand-300 font-bold text-lg whitespace-nowrap">That guarantees</span>
                            <input
                              type="text"
                              value={editingHypothesis.text.that_guarantees}
                              onChange={(e) => handleStructuredTextChange('that_guarantees', e.target.value)}
                              className="flex-1 min-w-[200px] px-3 py-1.5 text-brand-700 dark:text-brand-200 bg-white dark:bg-brand-900/50 border border-brand-300 dark:border-brand-600 rounded-lg focus:border-brand-500 dark:focus:border-brand-400 focus:outline-none"
                              placeholder="Value proposition..."
                            />
                          </div>
                        </div>
                      ) : (
                        // Legacy string edit mode
                        <Textarea
                          value={editingHypothesis.text as string}
                          onChange={(e) => handleTextChange(e.target.value)}
                          className="min-h-[100px] text-brand-700 dark:text-brand-200 bg-brand-50 dark:bg-brand-800/50 border-brand-200 dark:border-brand-700 focus:border-brand-500 dark:focus:border-brand-400"
                          placeholder="Enter hypothesis statement..."
                        />
                      )
                    ) : (
                      // View Mode - Bold keywords with values
                      isStructuredHypothesisText(hypothesis.text) ? (
                        <div className="bg-brand-50 dark:bg-brand-800/50 p-4 rounded-lg border border-brand-200 dark:border-brand-700 space-y-3">
                          <p className="text-brand-700 dark:text-brand-200 leading-relaxed">
                            <span className="text-brand-600 dark:text-brand-300 font-bold text-base">We believe that </span>
                            {hypothesis.text.we_believe_that}
                          </p>
                          <p className="text-brand-700 dark:text-brand-200 leading-relaxed">
                            <span className="text-brand-600 dark:text-brand-300 font-bold text-base">Are struggling with </span>
                            {hypothesis.text.are_struggling_with}
                          </p>
                          <p className="text-brand-700 dark:text-brand-200 leading-relaxed">
                            <span className="text-brand-600 dark:text-brand-300 font-bold text-base">Thus </span>
                            {hypothesis.text.thus}
                          </p>
                          <p className="text-brand-700 dark:text-brand-200 leading-relaxed">
                            <span className="text-brand-600 dark:text-brand-300 font-bold text-base">That guarantees </span>
                            {hypothesis.text.that_guarantees}
                          </p>
                        </div>
                      ) : (
                        // Legacy string display
                        <p className="text-brand-700 dark:text-brand-200 leading-relaxed text-md bg-brand-50 dark:bg-brand-800/50 p-4 rounded-lg border border-brand-200 dark:border-brand-700 transition-colors">
                          {hypothesis.text as string}
                        </p>
                      )
                    )}
                  </div>
                  
                  {/* Supporting Evidence */}
                  {((editingId === hypothesis.id && editingHypothesis?.evidence) || hypothesis.evidence) && (
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <h5 className="font-semibold text-brand-500 dark:text-brand-100 text-base">
                          Supporting Evidence:
                        </h5>
                        {editingId === hypothesis.id && (
                          <Button
                            onClick={handleAddEvidence}
                            variant="ghost"
                            size="sm"
                            className="h-8 text-brand-500 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-200"
                          >
                            <Plus className="w-4 h-4 mr-1" />
                            Add Evidence
                          </Button>
                        )}
                      </div>
                      <div className="grid gap-3">
                        {(editingId === hypothesis.id ? editingHypothesis?.evidence : hypothesis.evidence)?.map((evidence, evidenceIndex) => (
                          <div
                            key={evidenceIndex}
                            className="flex items-start gap-3 p-3 bg-brand-50 dark:bg-brand-800/30 rounded-lg group-hover:bg-brand-100 dark:group-hover:bg-brand-800/50 transition-colors"
                          >
                            <div 
                              className="flex-shrink-0 w-6 h-6 bg-brand-500 text-white rounded-full flex items-center justify-center text-xs font-bold mt-0.5"
                            >
                              {evidenceIndex + 1}
                            </div>
                            {editingId === hypothesis.id ? (
                              <div className="flex-1 flex items-start gap-2">
                                <Textarea
                                  value={evidence}
                                  onChange={(e) => handleEvidenceChange(evidenceIndex, e.target.value)}
                                  className="flex-1 min-h-[60px] text-brand-600 dark:text-brand-200 bg-white dark:bg-brand-900/50 border-brand-200 dark:border-brand-600 focus:border-brand-500 dark:focus:border-brand-400 text-sm"
                                  placeholder="Enter supporting evidence..."
                                />
                                {editingHypothesis && editingHypothesis.evidence.length > 1 && (
                                  <Button
                                    onClick={() => handleRemoveEvidence(evidenceIndex)}
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 w-8 p-0 text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-200 hover:bg-red-100 dark:hover:bg-red-900/20 mt-1"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </Button>
                                )}
                              </div>
                            ) : (
                              <p className="text-brand-600 dark:text-brand-200 leading-relaxed text-sm">
                                {evidence}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Edit Actions */}
                  {editingId === hypothesis.id && (
                    <div className="flex items-center justify-end gap-2 mt-6 pt-4 border-t border-brand-200 dark:border-brand-700">
                      <Button
                        onClick={handleEditCancel}
                        variant="outline"
                        size="sm"
                        disabled={saving}
                        className="text-brand-600 dark:text-brand-300 border-brand-300 dark:border-brand-600 hover:bg-brand-50 dark:hover:bg-brand-800"
                      >
                        <X className="w-4 h-4 mr-1" />
                        Cancel
                      </Button>
                      <Button
                        onClick={handleEditSave}
                        size="sm"
                        disabled={saving || !(editingHypothesis && (
                          isStructuredHypothesisText(editingHypothesis.text) 
                            ? editingHypothesis.text.we_believe_that.trim() !== ''
                            : (editingHypothesis.text as string).trim() !== ''
                        ))}
                        className="bg-brand-600 hover:bg-brand-700 text-white dark:bg-brand-500 dark:hover:bg-brand-600"
                      >
                        {saving ? (
                          <>
                            <RefreshCw className="w-4 h-4 mr-1 animate-spin" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Save className="w-4 h-4 mr-1" />
                            Save Changes
                          </>
                        )}
                      </Button>
                    </div>
                  )}

                  {/* Generated timestamp */}
                  {editingId !== hypothesis.id && (
                    <div className="mt-4 pt-3 border-t border-brand-200 dark:border-brand-700">
                      <p className="text-xs text-brand-500 dark:text-brand-400">
                        Generated on {formatDate(hypothesis.generated_at)}
                      </p>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>

            {/* Continue Button - NEW WORKFLOW: After hypothesis, go to questionnaires */}
            <div className="flex justify-center pt-6">
              <Button
                onClick={() => {
                  setIsNavigating(true);
                  router.push(`/team-workspace/questionnaires/${projectId}`);
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
                    Continue to Next Step ( Questionnaires )
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