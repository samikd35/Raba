"use client";

import PageBreadcrumb from "@/components/common/module 2/sub-module-2/PageBreadCrumb";
import CreditCostBadge from "@/components/common/CreditCostBadge";
import FeatureVideoOverlay from "@/components/feature-videos/FeatureVideoOverlay";
import { FEATURE_IDS, getFeatureVideoConfig } from "@/lib/featureVideos";
import React, { useState, useEffect, use, useCallback, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Target,
  TrendingUp,
  ArrowLeft,
  Loader2,
  AlertCircle,
  Users,
  ChevronRight,
  UserCircle2,
  Edit,
  Save,
  X,
  Plus,
  Trash2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import toast from "react-hot-toast";
import { motion } from "framer-motion";

// Fixed: Add proper type for SVG props
const PainIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" {...props}>
    <path fillRule="evenodd" d="M13.293 0c.39 0 .707.317.707.707V2h1.293a.707.707 0 0 1 .5 1.207l-1.46 1.46A1.14 1.14 0 0 1 13.53 5h-1.47L8.53 8.53a.75.75 0 0 1-1.06-1.06L11 3.94V2.47c0-.301.12-.59.333-.804l1.46-1.46a.7.7 0 0 1 .5-.207M2.5 8a5.5 5.5 0 0 1 6.598-5.39a.75.75 0 0 0 .298-1.47A7 7 0 1 0 14.86 6.6a.75.75 0 0 0-1.47.299q.109.533.11 1.101a5.5 5.5 0 1 1-11 0m5.364-2.496a.75.75 0 0 0-.08-1.498A4 4 0 1 0 11.988 8.3a.75.75 0 0 0-1.496-.111a2.5 2.5 0 1 1-2.63-2.686" clipRule="evenodd" />
  </svg>
);

interface Evidence {
  quote: string;
  source: string;
}

interface EnhancementRationale {
  updated: string;
  evidence: string;
  original: string;
  reason?: string;
}

interface CustomerProfileItem {
  id: string;
  type: "jtbd" | "pain" | "gain";
  label: string;
  text?: string;
  description: string;
  evidence?: Evidence[];
  confidence?: number;
  persona_id: string;
  persona_name?: string;
  enhancement_rationale?: EnhancementRationale;
}

interface CustomerProfile {
  gains: CustomerProfileItem[];
  pains: CustomerProfileItem[];
  jobs_to_be_done: CustomerProfileItem[];
  change_log?: any;
  validation_summary?: string;
}

interface ValueMapSelections {
  gain_creators?: any[];
  pain_relievers?: any[];
  products_services?: any[];
}

interface PersonaData {
  status: string;
  version: string;
  persona_id: string;
  updated_at: string;
  persona_name: string;
  customer_profile: CustomerProfile;
  original_customer_profile?: CustomerProfile;
  validation_metadata?: any;
  value_map_candidates?: string;
  value_map_selections?: ValueMapSelections;
  changes?: {
    jobs_to_be_done?: {
      validated_ids?: string[];
      updated?: Array<{
        id: string;
        original_text: string;
        updated_text: string;
        explanation: string;
        evidence_citation?: string;
      }>;
      removed?: Array<{
        id: string;
        original_text: string;
        explanation: string;
      }>;
    };
    pains?: {
      validated_ids?: string[];
      updated?: Array<{
        id: string;
        original_text: string;
        updated_text: string;
        explanation: string;
        evidence_citation?: string;
      }>;
      removed?: Array<{
        id: string;
        original_text: string;
        explanation: string;
      }>;
    };
    gains?: {
      validated_ids?: string[];
      updated?: Array<{
        id: string;
        original_text: string;
        updated_text: string;
        explanation: string;
        evidence_citation?: string;
      }>;
      removed?: Array<{
        id: string;
        original_text: string;
        explanation: string;
      }>;
    };
  };
}

interface BackendResponse {
  success: boolean;
  customer_profiles: {
    [personaId: string]: PersonaData;
  };
  personas_processed: string[];
  message: string;
}

interface CustomerProfileSelections {
  gains: CustomerProfileItem[];
  pains: CustomerProfileItem[];
  jobs_to_be_done: CustomerProfileItem[];
}

interface SelectionsData {
  project_id: string;
  customer_profile_selections: CustomerProfileSelections;
  total_jtbd: number;
  total_pains: number;
  total_gains: number;
}

// Constants
const API_BASE_URL = `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp`;

const DEFAULT_SELECTIONS: CustomerProfileSelections = {
  gains: [],
  pains: [],
  jobs_to_be_done: [],
};

// Fixed: Add type configuration with static Tailwind classes
const TYPE_CONFIG = {
  pain: {
    title: "Customer Pains",
    color: "red",
    icon: PainIcon,
    bgColor: "bg-red-50 dark:bg-red-900/20",
    textColor: "text-red-600 dark:text-red-400",
    borderColor: "border-red-200 dark:border-red-800",
    badgeColor: "text-red-700 dark:text-red-300 border-red-300 dark:border-red-700",
  },
  jtbd: {
    title: "Customer Jobs",
    color: "brand",
    icon: Target,
    bgColor: "bg-brand-50 dark:bg-brand-900/20",
    textColor: "text-brand-600 dark:text-brand-400",
    borderColor: "border-brand-200 dark:border-brand-800",
    badgeColor: "text-brand-700 dark:text-brand-300 border-brand-300 dark:border-brand-700",
  },
  gain: {
    title: "Customer Gains",
    color: "green",
    icon: TrendingUp,
    bgColor: "bg-green-50 dark:bg-green-900/20",
    textColor: "text-green-600 dark:text-green-400",
    borderColor: "border-green-200 dark:border-green-800",
    badgeColor: "text-green-700 dark:text-green-300 border-green-300 dark:border-green-700",
  },
} as const;

export default function CustomerProfileV2Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  // const featureConfig = getFeatureVideoConfig(FEATURE_IDS.CUSTOMER_PROFILE_V2);
  const router = useRouter();
  const { isAuthenticated, token } = useAuthStore();

  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  // State
  const [loading, setLoading] = useState(true);
  const [isContinuing, setIsContinuing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existingSelections, setExistingSelections] =
    useState<CustomerProfileSelections>(DEFAULT_SELECTIONS);
  const [originalSelections, setOriginalSelections] =
    useState<CustomerProfileSelections>(DEFAULT_SELECTIONS);
  const [stats, setStats] = useState<{
    jtbd: number;
    pains: number;
    gains: number;
  } | null>(null);

  // --- State for Persona Toggle ---
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [availablePersonas, setAvailablePersonas] = useState<string[]>([]);

  // --- State for Editing ---
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState("");
  const [editingDescription, setEditingDescription] = useState("");
  const [editingEvidence, setEditingEvidence] = useState<Evidence[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // --- State for Description Expansion ---
  const [expandedDescriptions, setExpandedDescriptions] = useState<Set<string>>(new Set());

  // Computed values
  const isReady = isAuthenticated && token && projectId;

  const hasSelections = useMemo(() => {
    return (
      existingSelections.gains.length > 0 ||
      existingSelections.pains.length > 0 ||
      existingSelections.jobs_to_be_done.length > 0
    );
  }, [existingSelections]);

  // Fixed: Memoize persona display names to prevent recalculations
  const personaDisplayNames = useMemo(() => {
    const names: Record<string, string> = {};
    const allItems = [
      ...existingSelections.gains,
      ...existingSelections.pains,
      ...existingSelections.jobs_to_be_done,
    ];

    availablePersonas.forEach(personaId => {
      if (personaId === "all") {
        names[personaId] = "All Personas";
        return;
      }

      const match = allItems.find(
        (item) => item.persona_id === personaId && (item as any).persona_name
      ) as (CustomerProfileItem & { persona_name?: string }) | undefined;
      
      if (match?.persona_name) {
        names[personaId] = match.persona_name;
      } else if (personaId.includes("_")) {
        const parts = personaId.split("_");
        const lastPart = parts[parts.length - 1];
        if (!isNaN(Number(lastPart))) {
          names[personaId] = `Persona ${lastPart}`;
        } else {
          names[personaId] = "Persona";
        }
      } else {
        names[personaId] = "Persona";
      }
    });

    return names;
  }, [existingSelections, availablePersonas]);

  const getPersonaDisplayName = useCallback((personaId: string | null) => {
    if (!personaId) return "All Personas";
    return personaDisplayNames[personaId] || "Persona";
  }, [personaDisplayNames]);

  // Fixed: Optimized filtered selections
  const getFilteredSelections = useMemo(() => {
    if (!selectedPersona || selectedPersona === "all") {
      return existingSelections;
    }

    return {
      gains: existingSelections.gains.filter(item => item.persona_id === selectedPersona),
      pains: existingSelections.pains.filter(item => item.persona_id === selectedPersona),
      jobs_to_be_done: existingSelections.jobs_to_be_done.filter(item => item.persona_id === selectedPersona),
    };
  }, [existingSelections, selectedPersona]);

  // Filtered original selections (for side-by-side comparison)
  const getFilteredOriginalSelections = useMemo(() => {
    if (!selectedPersona || selectedPersona === "all") {
      return originalSelections;
    }

    return {
      gains: originalSelections.gains.filter(item => item.persona_id === selectedPersona),
      pains: originalSelections.pains.filter(item => item.persona_id === selectedPersona),
      jobs_to_be_done: originalSelections.jobs_to_be_done.filter(item => item.persona_id === selectedPersona),
    };
  }, [originalSelections, selectedPersona]);

  // Fixed: Add proper abort controller cleanup with dynamic timeout
  const makeRequest = useCallback(
    async (endpoint: string, options: RequestInit = {}): Promise<any> => {
      if (!token) {
        throw new Error("No authentication token available");
      }

      const url = `${API_BASE_URL}${endpoint}`;
      const method = options.method || "GET";
      const body = options.body;
      const headers = {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
        ...options.headers,
      };

      // Dynamic timeout strategy based on endpoint
      const isGenerateOperation = endpoint.includes('/generate');
      const timeoutDuration = isGenerateOperation ? 120000 : 30000; // 2 minutes for generate, 30 seconds for others
      
      if (process.env.NODE_ENV === 'development') {
        console.log(`🔄 Making ${method} request to ${endpoint} with ${timeoutDuration/1000}s timeout`);
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        if (process.env.NODE_ENV === 'development') {
          console.log(`⏰ Request timeout after ${timeoutDuration/1000} seconds`);
        }
        controller.abort();
      }, timeoutDuration);

      try {
        const response = await fetch(url, {
          method,
          headers,
          body,
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        if (response.status === 401) {
          toast.error("Session expired. Please sign in again.");
          if (typeof window !== "undefined") {
            window.location.href = "/signin";
          }
          throw new Error("Authentication required");
        }

        const responseText = await response.text();

        if (!response.ok) {
          let errorMessage = `Request failed with status ${response.status}`;
          try {
            const errorData = responseText ? JSON.parse(responseText) : {};
            errorMessage =
              errorData.detail ||
              errorData.message ||
              errorData.error ||
              errorMessage;
          } catch (e) {
            errorMessage = responseText || errorMessage;
          }
          throw new Error(errorMessage);
        }

        try {
          return responseText ? JSON.parse(responseText) : {};
        } catch (e) {
          return responseText;
        }
      } catch (error: any) {
        clearTimeout(timeoutId);
        if (error.name === "AbortError") {
          const timeoutMessage = `Request timeout after ${timeoutDuration/1000} seconds. The operation is taking longer than expected.`;
          if (isGenerateOperation) {
            toast.error("Customer profile generation is taking longer than expected. This can happen with complex market research data.", {
              duration: 5000
            });
          } else {
            toast.error(timeoutMessage, { duration: 4000 });
          }
          throw new Error(timeoutMessage);
        }
        throw error;
      }
    },
    [token]
  );

  // Fixed: Add proper error handling and cleanup
  const loadSelections = useCallback(async () => {
    if (!isReady) return;

    try {
      setLoading(true);
      setError(null);

      const data: BackendResponse = await makeRequest(
        `/projects/${projectId}/vpc-v2/customer-profile`
      );

      if (data?.success && data.customer_profiles) {
        const allPains: CustomerProfileItem[] = [];
        const allJTBD: CustomerProfileItem[] = [];
        const allGains: CustomerProfileItem[] = [];
        const personaIds: string[] = [];

        // Arrays for original profile items (no enhancement rationale)
        const originalPains: CustomerProfileItem[] = [];
        const originalJTBD: CustomerProfileItem[] = [];
        const originalGains: CustomerProfileItem[] = [];

        Object.entries(data.customer_profiles).forEach(([personaId, personaData]) => {
          personaIds.push(personaId);
          
          const profile = personaData.customer_profile;
          const originalProfile = personaData.original_customer_profile;
          const personaName = personaData.persona_name;
          const changes = personaData.changes;

          // Helper function to get enhancement rationale for an item
          const getEnhancementRationale = (itemId: string, itemType: 'gain' | 'pain' | 'jtbd'): EnhancementRationale | undefined => {
            if (!changes || typeof changes !== 'object') return undefined;
            
            const sectionKey = itemType === 'jtbd' ? 'jobs_to_be_done' : 
                              itemType === 'pain' ? 'pains' : 
                              'gains';
            
            const updatedArray = changes[sectionKey]?.updated;
            if (!Array.isArray(updatedArray)) return undefined;
            
            const change = updatedArray.find((c: any) => c.id === itemId);
            if (change) {
              return {
                updated: change.updated_text || '',
                evidence: change.evidence_citation || '',
                original: change.original_text || '',
                reason: change.explanation || ''
              };
            }
            return undefined;
          };

          // Process final profile pains
          if (profile?.pains) {
            profile.pains.forEach(item => {
              allPains.push({
                ...item,
                persona_id: personaId,
                persona_name: personaName,
                description: item.description || item.text || '',
                evidence: item.evidence || [],
                confidence: item.confidence || 0,
                enhancement_rationale: getEnhancementRationale(item.id, 'pain')
              });
            });
          }

          // Process final profile jobs_to_be_done
          if (profile?.jobs_to_be_done) {
            profile.jobs_to_be_done.forEach(item => {
              allJTBD.push({
                ...item,
                persona_id: personaId,
                persona_name: personaName,
                description: item.description || item.text || '',
                evidence: item.evidence || [],
                confidence: item.confidence || 0,
                enhancement_rationale: getEnhancementRationale(item.id, 'jtbd')
              });
            });
          }

          // Process final profile gains
          if (profile?.gains) {
            profile.gains.forEach(item => {
              allGains.push({
                ...item,
                persona_id: personaId,
                persona_name: personaName,
                description: item.description || item.text || '',
                evidence: item.evidence || [],
                confidence: item.confidence || 0,
                enhancement_rationale: getEnhancementRationale(item.id, 'gain')
              });
            });
          }

          // Process original profile gains (NO enhancement rationale)
          if (originalProfile?.gains) {
            originalProfile.gains.forEach(item => {
              originalGains.push({
                ...item,
                persona_id: personaId,
                persona_name: personaName,
                description: item.description || item.text || '',
                evidence: item.evidence || [],
                confidence: item.confidence || 0,
              });
            });
          }

          // Process original profile pains (NO enhancement rationale)
          if (originalProfile?.pains) {
            originalProfile.pains.forEach(item => {
              originalPains.push({
                ...item,
                persona_id: personaId,
                persona_name: personaName,
                description: item.description || item.text || '',
                evidence: item.evidence || [],
                confidence: item.confidence || 0,
              });
            });
          }

          // Process original profile jobs_to_be_done (NO enhancement rationale)
          if (originalProfile?.jobs_to_be_done) {
            originalProfile.jobs_to_be_done.forEach(item => {
              originalJTBD.push({
                ...item,
                persona_id: personaId,
                persona_name: personaName,
                description: item.description || item.text || '',
                evidence: item.evidence || [],
                confidence: item.confidence || 0,
              });
            });
          }
        });



        const normalizedSelections: CustomerProfileSelections = {
          pains: allPains,
          jobs_to_be_done: allJTBD,
          gains: allGains,
        };

        const normalizedOriginalSelections: CustomerProfileSelections = {
          pains: originalPains,
          jobs_to_be_done: originalJTBD,
          gains: originalGains,
        };

        setExistingSelections(normalizedSelections);
        setOriginalSelections(normalizedOriginalSelections);
        setStats({
          jtbd: allJTBD.length,
          pains: allPains.length,
          gains: allGains.length,
        });

        // Set available personas
        const sortedPersonas = personaIds.sort();
        setAvailablePersonas(sortedPersonas);
        
        if (sortedPersonas.length > 0 && !selectedPersona) {
          setSelectedPersona(sortedPersonas[0]);
        }

      } else {
        throw new Error(data?.message || "Failed to load customer profiles");
      }
    } catch (err: any) {
      console.error('Load selections error:', err);
      if (err.message.includes("404") || err.message.includes("not found")) {
        setExistingSelections(DEFAULT_SELECTIONS);
        setOriginalSelections(DEFAULT_SELECTIONS);
        setStats(null);
        await generateCustomerProfile();
      } else {
        const errorMessage = err.message || "Failed to load customer profiles";
        setError(errorMessage);
        toast.error(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  }, [isReady, projectId, makeRequest, selectedPersona]);

  const handleBackToProject = () => {
    router.push(`/workspace/market-research-analysis/${projectId}`);
  };

  // Generate VPC v2 Customer Profile - using direct fetch to backend URL
const generateCustomerProfile = useCallback(
  async (): Promise<void> => {
    if (!isReady) {
      toast.error("Authentication required");
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      // Create the request body exactly as the backend expects
      const requestBody = {
        creativity_level: 0.7,
        include_context_summary: true
      };

      console.log("Sending request body:", JSON.stringify(requestBody, null, 2));
      console.log("Project ID:", projectId);
      console.log("Token available:", !!token);

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/vpc-v2/customer-profile/generate`,
        {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        }
      );

      console.log("Response status:", response.status);
      
      // if (!response.ok) {
      //   let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
        
      //   // Try to get more detailed error message from response body
      //   try {
      //     const errorText = await response.text();
      //     console.error("Error response body:", errorText);
          
      //     if (errorText) {
      //       const errorData = JSON.parse(errorText);
      //       errorDetail = errorData.detail || errorData.message || errorData.error || errorDetail;
      //     }
      //   } catch (parseError) {
      //     console.error("Could not parse error response:", parseError);
      //   }
        
      //   throw new Error(`Failed to generate customer profiles: ${errorDetail}`);
      // }

      await loadSelections();

    } catch (err: any) {
      console.error("Generation error details:", err);
      const errorMessage = err.message || "Failed to generate customer profiles";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  }, 
  [isReady, projectId, token, loadSelections]
);



  // Fixed: Remove unnecessary timeout and add proper error handling
  const handleContinueToVPC = useCallback(async () => {
    if (!projectId) {
      toast.error("Project ID is missing");
      return;
    }
    
    setIsContinuing(true);
    try {
      router.push(`/workspace/value-map-selections/${projectId}`);
    } catch (err) {
      console.error('Continue to VPC navigation error:', err);
      toast.error("Failed to navigate to VPC page");
    } finally {
      setIsContinuing(false);
    }
  }, [router, projectId]);

  // Load data on mount
  useEffect(() => {
    if (isReady) {
      loadSelections();
    }
  }, [isReady, loadSelections]);

  // Input sanitization function
  const sanitizeInput = useCallback((input: string): string => {
    return input.replace(/<[^>]*>/g, '');
  }, []);

  // Handle edit start
  const handleEditStart = useCallback((item: CustomerProfileItem) => {
    setEditingId(item.id);
    setEditingLabel(item.label);
    setEditingDescription(item.description);
    setEditingEvidence(item.evidence || []);
  }, []);

  // Handle edit cancel
  const handleEditCancel = useCallback(() => {
    setEditingId(null);
    setEditingLabel("");
    setEditingDescription("");
    setEditingEvidence([]);
  }, []);

  // Handle evidence add
  const handleAddEvidence = useCallback(() => {
    setEditingEvidence(prev => [...prev, { quote: "", source: "" }]);
  }, []);

  // Handle evidence remove
  const handleRemoveEvidence = useCallback((index: number) => {
    setEditingEvidence(prev => prev.filter((_, i) => i !== index));
  }, []);

  // Handle evidence change
  const handleEvidenceChange = useCallback((index: number, field: 'quote' | 'source', value: string) => {
    setEditingEvidence(prev => {
      const newEvidence = [...prev];
      newEvidence[index] = { ...newEvidence[index], [field]: sanitizeInput(value) };
      return newEvidence;
    });
  }, [sanitizeInput]);

  // Toggle description expansion
  const toggleDescriptionExpansion = useCallback((itemId: string) => {
    setExpandedDescriptions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  }, []);

  // Clamped Description Component
  const ClampedDescription = ({ text, itemId, className = "" }: { text: string; itemId: string; className?: string }) => {
    const [needsClamp, setNeedsClamp] = useState(false);
    const textRef = React.useRef<HTMLDivElement>(null);
    const isExpanded = expandedDescriptions.has(itemId);

    React.useEffect(() => {
      if (textRef.current) {
        const lineHeight = parseInt(window.getComputedStyle(textRef.current).lineHeight);
        const height = textRef.current.scrollHeight;
        const lines = Math.round(height / lineHeight);
        setNeedsClamp(lines > 4);
      }
    }, [text]);

    return (
      <div className={className}>
        <div
          ref={textRef}
          className={`text-sm ${!isExpanded && needsClamp ? 'line-clamp-4' : ''}`}
        >
          {text}
        </div>
        {needsClamp && (
          <button
            onClick={() => toggleDescriptionExpansion(itemId)}
            className="text-xs text-brand-600 dark:text-brand-400 hover:underline mt-1 focus:outline-none"
          >
            {isExpanded ? 'Less' : 'More'}
          </button>
        )}
      </div>
    );
  };

  // Fixed: Save edited item with better error handling and validation
  const handleEditSave = useCallback(async (item: CustomerProfileItem) => {
    if (!projectId || !editingId) {
      toast.error("Missing project ID or editing ID");
      return;
    }

    // Validate inputs
    const sanitizedLabel = sanitizeInput(editingLabel).trim();
    const sanitizedDescription = sanitizeInput(editingDescription).trim();

    if (!sanitizedLabel || sanitizedLabel.length > 200) {
      toast.error("Label must be between 1 and 200 characters");
      return;
    }

    if (!sanitizedDescription || sanitizedDescription.length > 2000) {
      toast.error("Description must be between 1 and 2000 characters");
      return;
    }

    setIsSaving(true);

    try {
      // Create updated item
      const updatedItem: CustomerProfileItem = {
        ...item,
        label: sanitizedLabel,
        description: sanitizedDescription,
        text: sanitizedDescription,
        evidence: editingEvidence.filter(e => e.quote.trim() && e.source.trim()),
      };

      // Update local state immediately for better UX
      setExistingSelections(prev => {
        const updated = { ...prev };
        
        if (item.type === 'gain') {
          updated.gains = updated.gains.map(g => g.id === editingId ? updatedItem : g);
        } else if (item.type === 'pain') {
          updated.pains = updated.pains.map(p => p.id === editingId ? updatedItem : p);
        } else if (item.type === 'jtbd') {
          updated.jobs_to_be_done = updated.jobs_to_be_done.map(j => j.id === editingId ? updatedItem : j);
        }
        
        return updated;
      });

      // Build the request payload
      const personaToUpdate = item.persona_id;
      const personaItems = {
        gains: existingSelections.gains.filter(g => g.persona_id === personaToUpdate).map(g => 
          g.id === editingId ? updatedItem : g
        ),
        pains: existingSelections.pains.filter(p => p.persona_id === personaToUpdate).map(p => 
          p.id === editingId ? updatedItem : p
        ),
        jobs_to_be_done: existingSelections.jobs_to_be_done.filter(j => j.persona_id === personaToUpdate).map(j => 
          j.id === editingId ? updatedItem : j
        ),
      };

      const personaName = personaItems.gains[0]?.persona_name || 
                         personaItems.pains[0]?.persona_name || 
                         personaItems.jobs_to_be_done[0]?.persona_name || 
                         personaToUpdate;

      const requestBody = {
        customer_profile: {
          [personaToUpdate]: {
            persona_name: personaName,
            persona_id: personaToUpdate,
            jobs_to_be_done: personaItems.jobs_to_be_done.map(j => ({
              id: j.id,
              label: j.label,
              text: j.description,
            })),
            pains: personaItems.pains.map(p => ({
              id: p.id,
              label: p.label,
              text: p.description,
            })),
            gains: personaItems.gains.map(g => ({
              id: g.id,
              label: g.label,
              text: g.description,
            })),
          }
        }
      };

      // Include persona_id as query parameter for multi-persona projects
      const endpoint = availablePersonas.length > 1 
        ? `/projects/${projectId}/vpc-v2/customer-profile?persona_id=${encodeURIComponent(personaToUpdate)}`
        : `/projects/${projectId}/vpc-v2/customer-profile`;

      const response = await makeRequest(
        endpoint,
        {
          method: "PUT",
          body: JSON.stringify(requestBody),
        }
      );

      if (response?.success) {
        toast.success("Customer profile updated successfully");
        handleEditCancel();
      } else {
        // Revert local state on error
        loadSelections();
        throw new Error(response?.message || "Failed to update customer profile");
      }
    } catch (err: any) {
      const errorMessage = err.message || "Failed to save changes";
      toast.error(errorMessage);
      console.error('Save error:', err);
    } finally {
      setIsSaving(false);
      loadSelections();
    }
  }, [
    projectId, 
    editingId, 
    editingLabel, 
    editingDescription, 
    editingEvidence, 
    existingSelections, 
    sanitizeInput, 
    makeRequest, 
    handleEditCancel, 
    availablePersonas,
    loadSelections
  ]);

  // Fixed: Persona selector with proper styling
  const PersonaSelector = ({ compact = false }: { compact?: boolean }) => {
    if (availablePersonas.length <= 1) return null;

    return (
      <div className={`flex justify-center ${compact ? 'mb-2' : 'mb-2'}`}>
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

  // Fixed: Render items with static Tailwind classes
  const renderItemsByType = (
    items: CustomerProfileItem[],
    type: "jtbd" | "pain" | "gain"
  ) => {
    const config = TYPE_CONFIG[type];
    const IconComponent = config.icon;

    return (
      <Card key={type}>
        <CardHeader className="flex flex-row items-center space-y-0">
          <div className={`p-2 rounded-lg ${config.bgColor} mr-3`}>
            <IconComponent className={`w-5 h-5 ${config.textColor}`} />
          </div>
          <CardTitle className={config.textColor}>
            {config.title}
          </CardTitle>
          <Badge variant="secondary" className="ml-auto">
            {items.length} items
          </Badge>
        </CardHeader>
        <CardContent className="space-y-2 -mt-2">
          {items.map((item, index) => {
            const isEditing = editingId === item.id;
            const uniqueKey = `${type}-${item.persona_id}-${item.id}-${index}`;
            const hasEnhancementRationale = !isEditing && item.enhancement_rationale;

            return (
              <motion.div
                key={uniqueKey}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className={`p-4 rounded-lg border ${config.borderColor} ${config.bgColor}`}
              >
                {/* Header with Label and Persona Badge */}
                <div className="flex justify-between items-center mb-4 border-b pb-2">
                  {isEditing ? (
                    <input
                      type="text"
                      value={editingLabel}
                      onChange={(e) => setEditingLabel(e.target.value)}
                      maxLength={200}
                      className="flex-1 font-semibold text-brand-500 dark:text-white text-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded px-2 py-1"
                      placeholder="Enter label..."
                    />
                  ) : (
                    <h4 className="font-semibold text-brand-500 dark:text-white text-lg">
                      {item.label}
                    </h4>
                  )}
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={config.badgeColor}
                    >
                      {getPersonaDisplayName(item.persona_id)}
                    </Badge>
                    {!isEditing && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleEditStart(item)}
                        className="h-8 w-8 p-0"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>

                {/* Main Content Grid */}
                <div className={`${hasEnhancementRationale ? 'md:grid md:grid-cols-2 md:gap-6' : ''}`}>
                  {/* Left Column: Main Content */}
                  <div className={hasEnhancementRationale ? 'space-y-4 ' : ''}>
                    {/* Description Section */}
                    <div>
                      <label className="block text-sm font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-300 mb-2">
                        Description
                      </label>
                      {isEditing ? (
                        <textarea
                          value={editingDescription}
                          onChange={(e) => setEditingDescription(e.target.value)}
                          maxLength={2000}
                          rows={4}
                          className="w-full text-gray-600 dark:text-gray-300 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded px-3 py-2"
                          placeholder="Enter description..."
                        />
                      ) : (
                        <div className="text-sm text-gray-600 dark:text-gray-400 bg-brand-25 dark:bg-brand-900/10 p-3 rounded-lg border border-brand-200 dark:border-brand-800">
                        <ClampedDescription
                          text={item.description}
                          itemId={item.id}
                        />
                        </div>
                      )}
                    </div>

                    {/* Evidence Section */}
                    {isEditing ? (
                      <div>
                        <div className="flex justify-between items-center mb-2">
                          <h5 className="text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-300">
                            Evidence
                          </h5>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleAddEvidence}
                            className="h-7 text-xs"
                          >
                            <Plus className="w-3 h-3 mr-1" />
                            Add Evidence
                          </Button>
                        </div>
                        <div className="space-y-2">
                          {editingEvidence.map((evidence, evidenceIndex) => (
                            <div
                              key={evidenceIndex}
                              className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-300 dark:border-gray-600 space-y-2"
                            >
                              <div className="flex justify-between items-start">
                                <label className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-400">
                                  Source
                                </label>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleRemoveEvidence(evidenceIndex)}
                                  className="h-6 w-6 p-0 text-red-600 hover:text-red-700"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </Button>
                              </div>
                              <input
                                type="text"
                                value={evidence.source}
                                onChange={(e) => handleEvidenceChange(evidenceIndex, 'source', e.target.value)}
                                className="w-full text-sm bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded px-2 py-1"
                                placeholder="Enter source..."
                              />
                              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-400 mt-2">
                                Quote
                              </label>
                              <textarea
                                value={evidence.quote}
                                onChange={(e) => handleEvidenceChange(evidenceIndex, 'quote', e.target.value)}
                                rows={2}
                                className="w-full text-sm bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded px-2 py-1"
                                placeholder="Enter quote..."
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      item.evidence && item.evidence.length > 0 && (
                        <div>
                          <h5 className="text-xs font-semibold uppercase tracking-wider text-brand-500 dark:text-gray-300 mb-2">
                            Evidence
                          </h5>
                          <div className="space-y-2">
                            {item.evidence.map((evidence, evidenceIndex) => (
                              <div
                                key={evidenceIndex}
                                className="text-sm text-gray-600 dark:text-gray-400 bg-brand-25 dark:bg-brand-900/10 p-3 rounded-lg border border-brand-200 dark:border-brand-800"
                              >
                                <div className="font-medium text-brand-500 dark:text-brand-300 mb-1">
                                  {evidence.source}:
                                </div>
                                <div className="italic">"{evidence.quote}"</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    )}
                  </div>

                  {/* Right Column: Enhancement Rationale (only when not editing) */}
                  {hasEnhancementRationale && (
                    <div className="border-l border-gray-200 dark:border-gray-700 pl-6 mt-6 md:mt-0">
                      <div className="sticky top-4">
                        <div className="flex items-center gap-2 mb-4">
                          
                          <h5 className="text-sm font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-300">
                            Enhancement Rationale
                          </h5>
                        </div>
                        
                        <div className="space-y-4">
                          {/* Original */}
                          {item.enhancement_rationale?.original && (
                            <div className="bg-white dark:bg-gray-800/50 p-4 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
                              <div className="flex items-center gap-2 mb-2">
                                <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                                <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                                  Original
                                </span>
                              </div>
                              <p className="text-sm text-gray-600 dark:text-gray-300">
                                {item.enhancement_rationale.original}
                              </p>
                            </div>
                          )}

                          {/* Evidence */}
                          {item.enhancement_rationale?.evidence && (
                            <div className="bg-white dark:bg-gray-800/50 p-4 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
                              <div className="flex items-center gap-2 mb-2">
                                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                                <span className="text-xs font-semibold uppercase tracking-wider text-green-600 dark:text-green-400">
                                  Evidence
                                </span>
                              </div>
                              <p className="text-sm text-gray-600 dark:text-gray-300">
                                {item.enhancement_rationale.evidence}
                              </p>
                            </div>
                          )}

                          {/* Reason */}
                          {item.enhancement_rationale?.reason && (
                            <div className="bg-white dark:bg-gray-800/50 p-4 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
                              <div className="flex items-center gap-2 mb-2">
                                <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                                <span className="text-xs font-semibold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                                  Reason
                                </span>
                              </div>
                              <p className="text-sm text-gray-600 dark:text-gray-300">
                                {item.enhancement_rationale.reason}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Edit Action Buttons */}
                {isEditing && (
                  <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleEditCancel}
                      disabled={isSaving}
                    >
                      <X className="w-4 h-4 mr-1" />
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleEditSave(item)}
                      disabled={isSaving}
                      className="bg-brand-600 hover:bg-brand-700"
                    >
                      {isSaving ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save className="w-4 h-4 mr-1" />
                          Save
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </motion.div>
            );
          })}
        </CardContent>
      </Card>
    );
  };

  // Render side-by-side comparison for a single item type
  const renderSideBySideSection = (
    type: "jtbd" | "pain" | "gain",
    originalItems: CustomerProfileItem[],
    finalItems: CustomerProfileItem[]
  ) => {
    const config = TYPE_CONFIG[type];
    const IconComponent = config.icon;
    const maxLength = Math.max(originalItems.length, finalItems.length);

    if (maxLength === 0) return null;

    return (
      <Card key={type} className="mb-4">
        <CardHeader className="pb-2">
          {/* Column Headers - at very top */}
          <div className="grid grid-cols-2 gap-4 pb-3 mb-3 border-b border-gray-200 dark:border-gray-700">
            <div className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              Original Profile
            </div>
            <div className="text-sm font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400">
              Enhanced Profile
            </div>
          </div>
          
          {/* Section Titles - duplicated on both sides */}
          <div className="grid grid-cols-2 gap-4">
            {/* Left: Original section title */}
            <div className="flex items-center">
              <div className={`p-2 rounded-lg bg-gray-100 dark:bg-gray-800 mr-3`}>
                <IconComponent className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              </div>
              <span className="text-lg font-semibold text-gray-600 dark:text-gray-400">
                {config.title}
              </span>
            </div>
            {/* Right: Enhanced section title */}
            <div className="flex items-center">
              <div className={`p-2 rounded-lg ${config.bgColor} mr-3`}>
                <IconComponent className={`w-5 h-5 ${config.textColor}`} />
              </div>
              <span className={`text-lg font-semibold ${config.textColor}`}>
                {config.title}
              </span>
              <Badge variant="secondary" className="ml-auto">
                {finalItems.length} items
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 -mt-2">
          {/* Items side by side */}
          {Array.from({ length: maxLength }).map((_, index) => {
            const originalItem = originalItems[index];
            const finalItem = finalItems[index];
            const uniqueKey = `${type}-comparison-${index}`;

            return (
              <div
                key={uniqueKey}
                className={`grid grid-cols-2 gap-4 p-4 rounded-lg border ${config.borderColor} ${config.bgColor}`}
              >
                {/* LEFT: Original Profile Item */}
                <div className="space-y-3 pr-4 border-r border-gray-200 dark:border-gray-700">
                  {originalItem ? (
                    <>
                      <h4 className="font-semibold text-gray-700 dark:text-gray-300 text-base">
                        {originalItem.label || "—"}
                      </h4>
                      <div className="text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                        <ClampedDescription
                          text={originalItem.description || "—"}
                          itemId={`original-${originalItem.id}`}
                        />
                      </div>
                      {originalItem.evidence && originalItem.evidence.length > 0 && (
                        <div>
                          {/* <h5 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
                            Evidence
                          </h5>
                          <div className="space-y-1">
                            {originalItem.evidence.map((ev, evIdx) => (
                              <div key={evIdx} className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 p-2 rounded border border-gray-200 dark:border-gray-700">
                                <span className="font-medium">{ev.source}:</span> "{ev.quote}"
                              </div>
                            ))}
                          </div> */}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-gray-400 dark:text-gray-500 italic text-sm">—</div>
                  )}
                </div>

                {/* RIGHT: Final/Enhanced Profile Item */}
                <div className="space-y-3 pl-2">
                  {finalItem ? (
                    <>
                      {editingId === finalItem.id ? (
                        /* EDIT MODE */
                        <div className="space-y-4">
                          {/* Label Input */}
                          <div>
                            <label className="block text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-300 mb-2">
                              Label
                            </label>
                            <input
                              type="text"
                              value={editingLabel}
                              onChange={(e) => setEditingLabel(e.target.value)}
                              maxLength={200}
                              className="w-full font-semibold text-brand-600 dark:text-white text-base bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded px-3 py-2"
                              placeholder="Enter label..."
                            />
                          </div>

                          {/* Description Textarea */}
                          <div>
                            <label className="block text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-300 mb-2">
                              Description
                            </label>
                            <textarea
                              value={editingDescription}
                              onChange={(e) => setEditingDescription(e.target.value)}
                              maxLength={2000}
                              rows={4}
                              className="w-full text-gray-600 dark:text-gray-300 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded px-3 py-2"
                              placeholder="Enter description..."
                            />
                          </div>

                          {/* Evidence Editor */}
                          <div>
                            <div className="flex justify-between items-center mb-2">
                              <label className="text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-300">
                                Evidence
                              </label>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={handleAddEvidence}
                                className="h-7 text-xs"
                              >
                                <Plus className="w-3 h-3 mr-1" />
                                Add Evidence
                              </Button>
                            </div>
                            <div className="space-y-2">
                              {editingEvidence.map((evidence, evidenceIndex) => (
                                <div
                                  key={evidenceIndex}
                                  className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-300 dark:border-gray-600 space-y-2"
                                >
                                  <div className="flex justify-between items-start">
                                    <label className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-400">
                                      Source
                                    </label>
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => handleRemoveEvidence(evidenceIndex)}
                                      className="h-6 w-6 p-0 text-red-600 hover:text-red-700"
                                    >
                                      <Trash2 className="w-3 h-3" />
                                    </Button>
                                  </div>
                                  <input
                                    type="text"
                                    value={evidence.source}
                                    onChange={(e) => handleEvidenceChange(evidenceIndex, 'source', e.target.value)}
                                    className="w-full text-sm bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded px-2 py-1"
                                    placeholder="Enter source..."
                                  />
                                  <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-400 mt-2">
                                    Quote
                                  </label>
                                  <textarea
                                    value={evidence.quote}
                                    onChange={(e) => handleEvidenceChange(evidenceIndex, 'quote', e.target.value)}
                                    rows={2}
                                    className="w-full text-sm bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded px-2 py-1"
                                    placeholder="Enter quote..."
                                  />
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Save/Cancel Buttons */}
                          <div className="flex justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={handleEditCancel}
                              disabled={isSaving}
                            >
                              <X className="w-4 h-4 mr-1" />
                              Cancel
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleEditSave(finalItem)}
                              disabled={isSaving}
                              className="bg-brand-600 hover:bg-brand-700"
                            >
                              {isSaving ? (
                                <>
                                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                                  Saving...
                                </>
                              ) : (
                                <>
                                  <Save className="w-4 h-4 mr-1" />
                                  Save
                                </>
                              )}
                            </Button>
                          </div>
                        </div>
                      ) : (
                        /* READ-ONLY MODE */
                        <>
                          <div className="flex justify-between items-start">
                            <h4 className="font-semibold text-brand-600 dark:text-brand-400 text-base">
                              {finalItem.label || "—"}
                            </h4>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleEditStart(finalItem)}
                              className="h-7 w-7 p-0"
                            >
                              <Edit className="w-3 h-3" />
                            </Button>
                          </div>
                          <div className="text-sm text-gray-600 dark:text-gray-300 bg-brand-25 dark:bg-brand-900/10 p-3 rounded-lg border border-brand-200 dark:border-brand-800">
                            <ClampedDescription
                              text={finalItem.description || "—" }
                              itemId={`enhanced-${finalItem.id}`}
                            />
                          </div>
                          {finalItem.evidence && finalItem.evidence.length > 0 && (
                            <div>
                              {/* <h5 className="text-xs font-semibold uppercase tracking-wider text-brand-500 dark:text-gray-400 mb-2">
                                Evidence
                              </h5>
                              <div className="space-y-1">
                                {finalItem.evidence.map((ev, evIdx) => (
                                  <div key={evIdx} className="text-xs text-gray-600 dark:text-gray-400 bg-brand-25 dark:bg-brand-900/10 p-2 rounded border border-brand-200 dark:border-brand-800">
                                    <span className="font-medium text-brand-600 dark:text-brand-400">{ev.source}:</span> "{ev.quote}"
                                  </div>
                                ))}
                              </div> */}
                            </div>
                          )}
                          {/* Enhancement Rationale for final item */}
                          {finalItem.enhancement_rationale && (
                            <div className="mt-3 pt-3 border-t border-brand-200 dark:border-brand-800">
                              <h5 className="text-xs font-semibold uppercase tracking-wider text-purple-600 dark:text-purple-400 mb-2">
                                Enhancement Rationale
                              </h5>
                              <div className="space-y-2">
                                {finalItem.enhancement_rationale.reason && (
                                  <div className="text-xs text-gray-600 dark:text-gray-400 bg-purple-50 dark:bg-purple-900/10 p-2 rounded border border-purple-200 dark:border-purple-800">
                                    <span className="font-medium text-purple-600 dark:text-purple-400">Reason:</span> {finalItem.enhancement_rationale.reason}
                                  </div>
                                )}
                                {finalItem.enhancement_rationale.evidence && (
                                  <div className="text-xs text-gray-600 dark:text-gray-400 bg-green-50 dark:bg-green-900/10 p-2 rounded border border-green-200 dark:border-green-800">
                                    <span className="font-medium text-green-600 dark:text-green-400">Evidence:</span> {finalItem.enhancement_rationale.evidence}
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </>
                  ) : (
                    <div className="text-gray-400 dark:text-gray-500 italic text-sm">—</div>
                  )}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    );
  };

  // Fixed: Add error state display
  if (error) {
    return (
      <div>
        <PageBreadcrumb pageTitle="Your Enhanced Customer Profile" titleSuffix={<CreditCostBadge cost={5} />} />
        <div className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-white/[0.03] p-2">
          <div className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
            <h3 className="text-lg font-medium text-red-600 dark:text-red-400 mb-2">
              Failed to Load Data
            </h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-md mb-6">
              {error}
            </p>
            <Button
              onClick={loadSelections}
              className="bg-brand-600 hover:bg-brand-700"
            >
              <Loader2 className="w-4 h-4 mr-2" />
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Main render
  return (
    <div>
      {/* <FeatureVideoOverlay
        featureId={FEATURE_IDS.CUSTOMER_PROFILE_V2}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      />       */}
      <PageBreadcrumb pageTitle="Your Enhanced Customer Profile" titleSuffix={<CreditCostBadge cost={5} />} />
      <div className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-white/[0.03] p-2">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col lg:flex-row items-start lg:items-center justify-between rounded-xl mb-2 px-4 py-3 border border-brand-200 dark:border-brand-700 bg-brand-50 dark:bg-brand-900/20"
        >
          <div className="mb-4 lg:mb-0">
            <p className="text-brand-500 dark:text-brand-100 text-sm">
              View your customer profile selections.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
            <Button
              onClick={handleBackToProject}
              variant="outline"
              className="text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Market Findings
            </Button>

            <Button
              onClick={generateCustomerProfile}
              disabled={isGenerating}
              className="bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                "Rebuild Customer Profile"
              )}
            </Button>

            <Button
              onClick={handleContinueToVPC}
              disabled={isContinuing || !hasSelections}
              className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600"
            >
              {isContinuing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Redirecting...
                </>
              ) : (
                <>
                  Continue to Value Maps
                  <ChevronRight className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>
          </div>
        </motion.div>

        {/* Loading State */}
        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center py-12"
          >
            <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-brand-500 dark:text-brand-400 mb-2">
              {isGenerating ? "Generating Selections..." : "Loading Selections..."}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-md">
              {isGenerating 
                ? "Creating customer profile selections from your market research data..."
                : "Fetching your existing customer profile selections..."}
            </p>
          </motion.div>
        )}

        {/* Content */}
        {!loading && !error && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {!hasSelections ? (
              <div className="text-center py-12">
                <Users className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  No Selections Found
                </h3>
                <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
                  No customer profile selections have been made for this project
                  yet.
                </p>
                <Button
                  onClick={generateCustomerProfile}
                  disabled={isGenerating}
                  className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Target className="w-4 h-4 mr-2" />
                      Build Customer Profile
                    </>
                  )}
                </Button>
              </div>
            ) : (
              <>
                {/* Persona Selector */}
                <PersonaSelector />

                {/* Customer Profile Content - Side-by-Side Comparison View */}
                <div className="space-y-4">
                  {/* Pains Section */}
                  {renderSideBySideSection(
                    "pain",
                    getFilteredOriginalSelections.pains,
                    getFilteredSelections.pains
                  )}

                  {/* Jobs to be Done Section */}
                  {renderSideBySideSection(
                    "jtbd",
                    getFilteredOriginalSelections.jobs_to_be_done,
                    getFilteredSelections.jobs_to_be_done
                  )}

                  {/* Gains Section */}
                  {renderSideBySideSection(
                    "gain",
                    getFilteredOriginalSelections.gains,
                    getFilteredSelections.gains
                  )}

                  {getFilteredSelections.jobs_to_be_done.length === 0 &&
                    getFilteredSelections.pains.length === 0 &&
                    getFilteredSelections.gains.length === 0 && (
                      <div className="text-center py-12">
                        <Users className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                        <p className="text-gray-500 dark:text-gray-400 text-sm">
                          No items for {getPersonaDisplayName(selectedPersona)}.
                        </p>
                      </div>
                    )}
                </div>
              </>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}