"use client";

import PageBreadcrumb from "@/components/common/module 3/sub-module-1/PageBreadCrumb";
import CreditCostBadge from "@/components/common/CreditCostBadge";
import FeatureVideoOverlay from "@/components/feature-videos/FeatureVideoOverlay";
import { FEATURE_IDS, getFeatureVideoConfig } from "@/lib/featureVideos";
import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import MoreContext from "@/components/MoreContext";
import { 
  ArrowLeft, 
  Loader2, 
  AlertCircle,
  Users,
  Play,
  RefreshCw,
  UserCircle2,
  Package,
  Shield,
  Zap,
  Heart,
  Briefcase,
  Edit2,
  Save,
  X,
  Check,
  Pencil,
  ChevronDown
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import toast from "react-hot-toast";
import { motion } from "framer-motion";

// TypeScript interfaces
interface PrimaryStatement {
  our: string;
  help: string;
  who_want_to: string;
  by: string;
  and: string;
  unlike: string;
}

interface KeyDifferentiator {
  id: string;
  title: string;
  description: string;
  evidence_source: string;
}

interface GenerationMetadata {
  generated_at: string;
  generated_by: string;
  model_used: string;
  confidence_score: number;
  version: string;
  context_sources?: string[];
  evidence_count?: number;
  context_completeness?: number;
  creativity_level?: number;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

// Single persona VPS data
interface PersonaVPSData {
  persona_id: string;
  persona_name: string;
  primary_statement: PrimaryStatement;
  extended_statement: string;
  key_differentiators: KeyDifferentiator[];
  generation_metadata: GenerationMetadata;
}

// Legacy single VPS data (for backward compatibility)
interface VPSData {
  primary_statement: PrimaryStatement;
  extended_statement: string;
  key_differentiators: KeyDifferentiator[];
  generation_metadata: GenerationMetadata;
}

// New response format with array of persona VPS
interface VPSResponse {
  success: boolean;
  vps_data?: PersonaVPSData[];  // Current backend format
  data?: {
    vps_v1: PersonaVPSData[];
    project_id: string;
    persona_count: number;
    vps_count: number;
    already_existed: boolean;
    message: string;
  };
  // Legacy format support
  vps_data_single?: VPSData;  // Renamed to avoid conflict
  project_id?: string;
  current_version?: string;
  message: string;
}

interface VPSUpdateResponse {
  success: boolean;
  message: string;
  vps_v1: PersonaVPSData;
}

// Define the exact structure for PUT request body - same as GET response
interface VPSUpdateRequest {
  success: boolean;
  vps_data: PersonaVPSData[];
  project_id: string;
  current_version: string;
  message: string;
}

export default function VPSPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { isAuthenticated, token } = useAuthStore();
  const featureConfig = getFeatureVideoConfig(FEATURE_IDS.VPS_V2);
  
  const resolvedParams = React.use(params);
  const projectId = resolvedParams.id;

  // State management
  const [vpsDataList, setVpsDataList] = useState<PersonaVPSData[]>([]);
  const [selectedPersonaId, setSelectedPersonaId] = useState<string | null>(null);
  const [availablePersonas, setAvailablePersonas] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isAutoGenerating, setIsAutoGenerating] = useState(false);
  const [isBackLoading, setIsBackLoading] = useState(false);
  const [isContinueLoading, setIsContinueLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editedStatement, setEditedStatement] = useState<PrimaryStatement | null>(null);
  const [isMoreContextOpen, setIsMoreContextOpen] = useState(false);
  const [newState1, setNewState1] = useState(false);
  const [newState2, setNewState2] = useState(false);
  const [newState3, setNewState3] = useState(false);
  const [creativityLevel, setCreativityLevel] = useState(0.7);

  // Get current persona VPS data based on selection
  const currentVpsData = useMemo(() => {
    if (!selectedPersonaId || vpsDataList.length === 0) return null;
    
    // First try to find by persona_id
    const foundByPersonaId = vpsDataList.find(vps => vps.persona_id === selectedPersonaId);
    if (foundByPersonaId) return foundByPersonaId;
    
    // If not found and selectedPersonaId is 'default', return the first item
    if (selectedPersonaId === 'default' && vpsDataList.length > 0) {
      return vpsDataList[0];
    }
    
    return null;
  }, [selectedPersonaId, vpsDataList]);

  // Get persona display name
  const getPersonaDisplayName = useCallback((personaId: string) => {
    if (personaId === 'default') {
      // For default persona, use the persona_name from the first item or fallback
      const firstVps = vpsDataList[0];
      if (firstVps?.persona_name) {
        return firstVps.persona_name;
      }
      return 'Default Persona';
    }
    
    const persona = vpsDataList.find(vps => vps.persona_id === personaId);
    return persona?.persona_name || personaId;
  }, [vpsDataList]);

  // Persona selector component
  const PersonaSelector = ({ compact = false }: { compact?: boolean }) => {
    if (availablePersonas.length <= 1) return null;

    return (
      <div className={`flex justify-center ${compact ? 'mt-2' : 'mt-2'}`}>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm">
          <Tabs 
            value={selectedPersonaId || "all"} 
            onValueChange={(value) => setSelectedPersonaId(value === "all" ? null : value)}
            className="w-full"
          >
            <TabsList className="grid grid-cols-2 w-full">
              {availablePersonas.map((personaId, index) => (
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

  // AbortController for cleanup
  const abortControllerRef = useRef<AbortController | null>(null);

  // Forward declaration for handleRegenerate
  const handleRegenerateRef = useRef<(() => Promise<void>) | null>(null);

  // Fetch VPS data
  const fetchVPSData = useCallback(async (forceRefresh = false) => {
    if (!isAuthenticated || !token || !projectId) return;

    try {
      // Cancel previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();
      setLoading(true);
      setError(null);

      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 Fetching VPS data for project:', projectId);
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/mvp/projects/${projectId}/vps/v2`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        if (response.status === 401) {
          toast.error('Authentication failed. Please sign in again.');
          router.push('/signin');
          return;
        }
        if (response.status === 404) {
          // Check if the project exists by trying to fetch project info
          try {
            const projectResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/mvp/projects/${projectId}`, {
              method: 'GET',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
            });

            if (!projectResponse.ok) {
              if (projectResponse.status === 404) {
                // Project doesn't exist - show error and redirect
                setError('Project not found. The project you are trying to access may have been deleted or you may not have the correct project ID.');
                toast.error('Project not found. Redirecting to project dashboard...', { duration: 4000 });
                setLoading(false);
                
                // Delay redirect to allow user to see the toast
                setTimeout(() => {
                  router.push('/team-workspace/projects-mvp');
                }, 2000);
                return;
              }
              throw new Error(`Failed to verify project: HTTP ${projectResponse.status}`);
            }
          } catch (projectError: any) {
            setError('Unable to verify project existence. Please check your connection and try again.');
            toast.error('Unable to verify project. Please check your internet connection and try again.', { duration: 6000 });
            setLoading(false);
            return;
          }

          // Project exists but VPS not found - proceed with auto-generation
          if (process.env.NODE_ENV === 'development') {
            console.log('🔄 VPS not found, automatically generating...');
          }
          toast.success('VPS not found. Generating VPS automatically...');
          
          // Call handleRegenerate to generate VPS
          if (handleRegenerateRef.current) {
            await handleRegenerateRef.current();
          }
          return;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: VPSResponse = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ VPS data loaded successfully:', data);
        console.log('🔍 Data structure analysis:');
        console.log('- data.success:', data.success);
        console.log('- data.data:', data.data);
        console.log('- data.data?.vps_v1:', data.data?.vps_v1);
        console.log('- data.vps_data:', data.vps_data);
        console.log('- Is vps_v1 array?:', Array.isArray(data.data?.vps_v1));
      }
      
      // Handle current backend format (vps_data as array)
      if (data.success && data.vps_data && Array.isArray(data.vps_data)) {
        const vpsList = data.vps_data;
        setVpsDataList(vpsList);
        
        // Extract available personas - handle null persona_id
        const personaIds = vpsList
          .map(vps => vps.persona_id)
          .filter(id => id !== null && id !== undefined) as string[];
        
        // If no valid persona IDs, create a default one
        if (personaIds.length === 0 && vpsList.length > 0) {
          const defaultPersonaId = 'default';
          setAvailablePersonas([defaultPersonaId]);
          setSelectedPersonaId(defaultPersonaId);
          setEditedStatement(vpsList[0].primary_statement);
          
          if (process.env.NODE_ENV === 'development') {
            console.log('✅ Using default persona for null persona_id');
            console.log('✅ Set edited statement:', vpsList[0].primary_statement);
          }
        } else {
          setAvailablePersonas(personaIds);
          
          // Auto-select first persona if none selected
          if (vpsList.length > 0) {
            const firstPersonaId = personaIds[0] || 'default';
            setSelectedPersonaId(firstPersonaId);
            setEditedStatement(vpsList[0].primary_statement);
            
            if (process.env.NODE_ENV === 'development') {
              console.log('✅ Selected persona:', firstPersonaId);
              console.log('✅ Set edited statement:', vpsList[0].primary_statement);
            }
          }
        }
        
        if (process.env.NODE_ENV === 'development') {
          console.log('✅ VPS data loaded for', vpsList.length, 'persona(s)');
        }
      } 
      // Handle alternative format (data.vps_v1)
      else if (data.success && data.data?.vps_v1 && Array.isArray(data.data.vps_v1)) {
        const vpsList = data.data.vps_v1;
        setVpsDataList(vpsList);
        
        // Extract available personas
        const personaIds = vpsList.map(vps => vps.persona_id);
        setAvailablePersonas(personaIds);
        
        // Auto-select first persona if none selected
        if (vpsList.length > 0) {
          const firstPersonaId = vpsList[0].persona_id;
          setSelectedPersonaId(firstPersonaId);
          setEditedStatement(vpsList[0].primary_statement);
          
          if (process.env.NODE_ENV === 'development') {
            console.log('✅ Selected persona (alt format):', firstPersonaId);
          }
        }
        
        if (process.env.NODE_ENV === 'development') {
          console.log('✅ VPS data loaded (alt format) for', vpsList.length, 'persona(s)');
        }
      } 
      // Handle legacy single VPS format
      else if (data.success && data.vps_data_single) {
        const legacyVps: PersonaVPSData = {
          persona_id: 'P1',
          persona_name: 'Primary Persona',
          ...data.vps_data_single
        };
        setVpsDataList([legacyVps]);
        setSelectedPersonaId('P1');
        setEditedStatement(data.vps_data_single.primary_statement);
        
        if (process.env.NODE_ENV === 'development') {
          console.log('✅ Legacy VPS data loaded successfully');
        }
      } else {
        // Check if the error is about VPS not found
        const errorMessage = data.message || 'Failed to load VPS data';
        if (process.env.NODE_ENV === 'development') {
          console.log('🔍 Response message:', errorMessage);
          console.log('🔍 Full response data:', JSON.stringify(data, null, 2));
        }
        
        if (errorMessage.includes('VPS v1 not found') || errorMessage.includes('Generate it first')) {
          if (process.env.NODE_ENV === 'development') {
            console.log('🔄 VPS not found in response, automatically generating...');
            console.log('🔄 Setting isAutoGenerating to true');
          }
          
          setIsAutoGenerating(true);
          setLoading(false); // Stop the initial loading
          toast.success('VPS not found. Generating VPS automatically...');
          
          // Call handleRegenerate to generate VPS
          if (handleRegenerateRef.current) {
            try {
              await handleRegenerateRef.current();
              // The handleRegenerate function will handle setting isAutoGenerating to false
            } catch (error) {
              setIsAutoGenerating(false);
              throw error;
            }
          }
          return;
        }
        
        throw new Error(errorMessage);
      }

    } catch (error: any) {
      if (error.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('🚫 VPS fetch aborted');
        }
        return;
      }

      const errorMessage = error.message || 'Failed to load VPS data';
      setError(errorMessage);
      toast.error(errorMessage);
      
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error fetching VPS data:', error);
      }
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, token, projectId, router]);

  // Initialize data on mount
  useEffect(() => {
    fetchVPSData();

    // Cleanup on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchVPSData]);

  // Reset edit state when currentVpsData changes
  useEffect(() => {
    if (currentVpsData) {
      setEditedStatement(currentVpsData.primary_statement);
      setIsEditing(false); // Exit edit mode when switching personas
    }
  }, [currentVpsData]);

  // Handle navigation functions
  const handleBackToProject = useCallback(async () => {
    setIsBackLoading(true);
    router.push(`/team-workspace/solution-critic/${projectId}`);
  }, [router, projectId]);

// Reusable VPS generation function
const generateVPS = useCallback(async (projectId: string, token: string, creativityLevel: number = 0.7) => {
  if (!projectId || !token) {
    throw new Error('Project ID and authentication token are required');
  }

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/mvp/projects/${projectId}/vps/v2/generate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      creativity_level: creativityLevel
    }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication failed. Please sign in again.');
    }
    if (response.status === 404) {
      throw new Error('Project not found or VPS generation endpoint unavailable.');
    }
    if (response.status === 400) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.message || 'Invalid request parameters.';
      
      // Handle specific invalid request parameter errors
      if (errorMessage.includes('Invalid request parameters') || 
          errorMessage.includes('invalid parameters') ||
          errorMessage.includes('missing project data')) {
        throw new Error('The request contains invalid parameters. This may be due to missing project data or incorrect configuration. Please ensure all required project steps are completed and try again.');
      }
      
      throw new Error(errorMessage);
    }
    if (response.status === 403) {
      throw new Error('You do not have permission to generate VPS for this project. Please check your project access or contact your team administrator.');
    }
    if (response.status === 500) {
      throw new Error('Server error occurred while generating VPS. Please try again later or contact support if the problem persists.');
    }
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.message || 'Failed to generate VPS');
  }

  return data;
}, []);

// Handle edit functionality
const handleEditToggle = useCallback(() => {
  if (isEditing) {
    // Cancel editing - reset to original data
    if (currentVpsData) {
      setEditedStatement(currentVpsData.primary_statement);
    }
    setIsEditing(false);
  } else {
    // Start editing
    setIsEditing(true);
  }
}, [isEditing, currentVpsData]);

// Handle save changes with exact format required by backend
const handleSaveChanges = useCallback(async () => {
  if (!isAuthenticated || !token || !projectId || !editedStatement || !selectedPersonaId || !currentVpsData) {
    toast.error('Missing required information');
    return;
  }

  // Validate all fields are filled
  const requiredFields: (keyof PrimaryStatement)[] = ['our', 'help', 'who_want_to', 'by', 'and', 'unlike'];
  const missingFields = requiredFields.filter(field => !editedStatement[field]?.trim());
  
  if (missingFields.length > 0) {
    toast.error(`Please fill in all fields: ${missingFields.join(', ')}`);
    return;
  }

  try {
    setIsSaving(true);

    // Create the exact structure required by backend - complete response format
    const updatedVpsData = vpsDataList.map(vps => 
      vps.persona_id === selectedPersonaId 
        ? {
            ...vps,
            primary_statement: {
              our: editedStatement.our.trim(),
              help: editedStatement.help.trim(),
              who_want_to: editedStatement.who_want_to.trim(),
              by: editedStatement.by.trim(),
              and: editedStatement.and.trim(),
              unlike: editedStatement.unlike.trim()
            }
          }
        : vps
    );

    const requestBody: VPSUpdateRequest = {
      success: true,
      vps_data: updatedVpsData,
      project_id: projectId,
      current_version: "v1",
      message: "VPS updated successfully"
    };

    if (process.env.NODE_ENV === 'development') {
      console.log('📤 Sending PUT request with body:', JSON.stringify(requestBody, null, 2));
    }

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/mvp/projects/${projectId}/vps/v2`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }
      if (response.status === 404) {
        throw new Error('Project not found or VPS generation endpoint unavailable.');
      }
      if (response.status === 400) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.message || 'Invalid request parameters.';
        
        // Handle specific invalid request parameter errors
        if (errorMessage.includes('Invalid request parameters') || 
            errorMessage.includes('invalid') ||
            errorMessage.includes('parameters')) {
          throw new Error('The request contains invalid parameters. This may be due to missing project data or incorrect configuration. Please ensure all required project steps are completed and try again.');
        }
        
        throw new Error(errorMessage);
      }
      if (response.status === 403) {
        throw new Error('You do not have permission to generate VPS for this project. Please check your project access or contact your team administrator.');
      }
      if (response.status === 500) {
        throw new Error('Server error occurred while generating VPS. Please try again later or contact support if the problem persists.');
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Fetch fresh data from backend instead of updating local state directly
    await fetchVPSData();

    toast.success('VPS updated successfully!');
    setIsEditing(false);
  } catch (error: any) {
    const errorMessage = error.message || 'Failed to save changes';
    toast.error(errorMessage);
    console.error('Error saving VPS:', error);
  } finally {
    setIsSaving(false);
  }
}, [isAuthenticated, token, projectId, editedStatement, selectedPersonaId, currentVpsData, vpsDataList, fetchVPSData]);

const handleRegenerate = useCallback(async () => {
  if (!isAuthenticated || !token || !projectId) {
    toast.error('Authentication required. Please sign in again.');
    return;
  }

  try {
    setIsRegenerating(true);
    setError(null);

    if (process.env.NODE_ENV === 'development') {
      console.log('🔄 Starting VPS regeneration for project:', projectId);
    }

    toast.success('VPS regeneration started... This may take a moment.');

    // Call the reusable generate function
    const result = await generateVPS(projectId, token, creativityLevel);

    if (process.env.NODE_ENV === 'development') {
      console.log('✅ VPS regenerated successfully:', result);
    }

    // Update the VPS data with the new generated data
    await fetchVPSData();
    setIsEditing(false); // Exit edit mode if active
    toast.success('VPS regenerated successfully!');

  } catch (error: any) {
    const errorMessage = error.message || 'Failed to regenerate VPS';
    setError(errorMessage);
    
    // Handle specific error types with better user guidance
    if (errorMessage.includes('Invalid request parameters') || 
        errorMessage.includes('invalid parameters') ||
        errorMessage.includes('missing project data')) {
      toast.error('Unable to generate VPS: The project may be missing required data. Please ensure all previous steps (Customer Profile and Value Map) are completed before generating VPS.', {
        duration: 8000,
      });
    } else if (errorMessage.includes('permission') || errorMessage.includes('403')) {
      toast.error('You do not have permission to generate VPS for this project. Please contact your team administrator.', {
        duration: 6000,
      });
    } else if (errorMessage.includes('Authentication failed')) {
      toast.error('Authentication failed. Please sign in again.');
      router.push('/signin');
    } else if (errorMessage.includes('Server error') || errorMessage.includes('500')) {
      toast.error('Server error occurred. Please try again later or contact support if the problem persists.', {
        duration: 6000,
      });
    } else {
      toast.error(errorMessage, { duration: 5000 });
    }
    
    if (process.env.NODE_ENV === 'development') {
      console.error('❌ Error regenerating VPS:', error);
    }
  } finally {
    setIsRegenerating(false);
    setIsAutoGenerating(false); // Also reset auto-generation state
  }
}, [isAuthenticated, token, projectId, router, generateVPS, selectedPersonaId, creativityLevel]);

  // Assign handleRegenerate to ref so it can be called from fetchVPSData
  useEffect(() => {
    handleRegenerateRef.current = handleRegenerate;
  }, [handleRegenerate]);

  const handleContinueToBMC = useCallback(async () => {
    setIsContinueLoading(true);
    router.push(`/team-workspace/bmc-v2/${projectId}`);
  }, [router, projectId]);

  // Handle input change for editable fields with validation
  const handleInputChange = useCallback((field: keyof PrimaryStatement, value: string) => {
    setEditedStatement(prev => {
      if (!prev) return null;
      return { ...prev, [field]: value };
    });
  }, []);

  // Loading state
  if (loading) {
    return (
      <div>
        <PageBreadcrumb pageTitle="Post Solution Critique Value Proposition Statement" titleSuffix={<CreditCostBadge cost={10} />} />
        <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-8">
          <div className="flex items-center justify-center min-h-[500px]">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="text-center max-w-md"
            >
              <div className="relative mb-6">
                <div className="w-16 h-16 mx-auto bg-brand-100 dark:bg-brand-700 rounded-full flex items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-600 dark:text-brand-400" />
                </div>
                <motion.div
                  initial={{ scale: 1, opacity: 0.3 }}
                  animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.6, 0.3] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="absolute inset-0 w-16 h-16 mx-auto bg-brand-200 dark:bg-brand-600 rounded-full opacity-20"
                />
              </div>
              
              <h3 className="text-lg font-semibold text-brand-500 dark:text-gray-200 mb-2">
                Loading Your Value Proposition
              </h3>
              
              <p className="text-gray-600 dark:text-gray-400 mb-4 text-sm leading-relaxed">
                Retrieving your project's VPS data and insights...
              </p>
              
              <div className="flex items-center justify-center space-x-1">
                <motion.div
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
                  className="w-1.5 h-1.5 bg-gray-500 dark:bg-gray-400 rounded-full"
                />
                <motion.div
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
                  className="w-1.5 h-1.5 bg-gray-500 dark:bg-gray-400 rounded-full"
                />
                <motion.div
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
                  className="w-1.5 h-1.5 bg-gray-500 dark:bg-gray-400 rounded-full"
                />
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    );
  }

  // Auto-generation loading state
  if (isAutoGenerating) {
    if (process.env.NODE_ENV === 'development') {
      console.log('🎨 Rendering auto-generation loading UI');
    }
    return (
      <div>
        <PageBreadcrumb pageTitle="VPS" />
        <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-8">
          <div className="flex items-center justify-center min-h-[500px]">
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="text-center max-w-md"
            >
              <div className="relative mb-6">
                <div className="w-20 h-20 mx-auto bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
                  <Loader2 className="w-10 h-10 animate-spin text-gray-600 dark:text-gray-400" />
                </div>
                <motion.div
                  initial={{ scale: 1 }}
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="absolute inset-0 w-20 h-20 mx-auto bg-gray-200 dark:bg-gray-600 rounded-full opacity-20"
                />
              </div>
              
              <h3 className="text-xl font-semibold text-brand-500 dark:text-gray-200 mb-3">
                Generating Your Value Proposition Statement
              </h3>
              
            </motion.div>
          </div>
        </div>
      </div>
    );
  }

  // Data loading state (when loading is false but no data yet)
  if (vpsDataList.length === 0 || !currentVpsData) {
    if (process.env.NODE_ENV === 'development') {
      console.log('🔍 Display condition check:');
      console.log('- vpsDataList.length:', vpsDataList.length);
      console.log('- selectedPersonaId:', selectedPersonaId);
      console.log('- currentVpsData:', currentVpsData);
      console.log('- loading:', loading);
      console.log('- error:', error);
      console.log('- vpsDataList:', vpsDataList);
    }
    return (
      <div>
        <PageBreadcrumb pageTitle="Post Solution Critique Value Proposition Statement" titleSuffix={<CreditCostBadge cost={10} />} />
        <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-8">
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <div className="w-12 h-12 border-4 border-gray-300 border-t-gray-500 rounded-full animate-spin"></div>
            <div className="text-center">
              <p className="text-lg font-medium text-brand-500 dark:text-gray-200">Loading Value Proposition Statement</p>
              <p className="text-sm text-muted-foreground">Preparing your statement data...</p>
              
            </div>
            
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    const isInvalidParameterError = error.includes('Invalid request parameters') || 
                                   error.includes('invalid parameters') ||
                                   error.includes('missing project data');
    const isProjectNotFoundError = error.includes('Project not found') || 
                                   error.includes('project may have been deleted') ||
                                   error.includes('correct project ID');
    
    return (
      <div>
        <PageBreadcrumb pageTitle="Post Solution Critique Value Proposition Statement" titleSuffix={<CreditCostBadge cost={10} />} />
        <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-8">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center max-w-md">
              <AlertCircle className={`w-12 h-12 mx-auto mb-4 ${
                isProjectNotFoundError ? 'text-red-600' : 
                isInvalidParameterError ? 'text-orange-500' : 'text-red-500'
              }`} />
              <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">
                {isProjectNotFoundError ? 'Project Not Found' : 
                 isInvalidParameterError ? 'Unable to Generate VPS' : 'Failed to Load VPS'}
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">{error}</p>
              
              {isProjectNotFoundError ? (
                <div className="space-y-4">
                  <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg p-4 text-sm text-red-800 dark:text-red-200 text-left">
                    <strong>What this means:</strong>
                    <ul className="mt-2 space-y-1">
                      <li>• The project you're trying to access doesn't exist</li>
                      <li>• The project may have been deleted</li>
                      <li>• You may have an incorrect or outdated project link</li>
                    </ul>
                    <div className="mt-3 pt-3 border-t border-red-200 dark:border-red-700">
                      <strong>Recommended actions:</strong>
                      <ul className="mt-2 space-y-1">
                        <li>• Go back to your project dashboard</li>
                        <li>• Select a different project from your list</li>
                        <li>• Check if you have the correct project URL</li>
                      </ul>
                    </div>
                  </div>
                  <div className="flex gap-3 justify-center">
                    <Button onClick={handleBackToProject} variant="outline">
                      <ArrowLeft className="w-4 h-4 mr-2" />
                      Back to Solution Critique
                    </Button>
                  </div>
                </div>
              ) : isInvalidParameterError ? (
                <div className="space-y-4">
                  <div className="bg-orange-50 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-700 rounded-lg p-4 text-sm text-orange-800 dark:text-orange-200 text-left">
                    <strong>What this means:</strong>
                    <ul className="mt-2 space-y-1">
                      <li>• The project may be missing required data</li>
                      <li>• Previous steps might not be completed</li>
                      <li>• The project configuration may be incomplete</li>
                    </ul>
                    <div className="mt-3 pt-3 border-t border-orange-200 dark:border-orange-600">
                      <strong>Recommended actions:</strong>
                      <ul className="mt-2 space-y-1">
                        <li>• Complete Customer Profile and Value Map</li>
                        <li>• Ensure all project data is properly filled</li>
                        <li>• Contact your team administrator if needed</li>
                      </ul>
                    </div>
                  </div>
                  <div className="flex gap-3 justify-center">
                    <Button onClick={() => fetchVPSData(true)} className="bg-gray-600 hover:bg-gray-700 dark:bg-gray-600 dark:hover:bg-gray-700">
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Retry
                    </Button>
                    <Button onClick={handleBackToProject} variant="outline">
                      <ArrowLeft className="w-4 h-4 mr-2" />
                      Back to Solution Critique
                    </Button>
                  </div>
                </div>
              ) : (
                <Button onClick={() => fetchVPSData(true)} className="bg-gray-600 hover:bg-gray-700 dark:bg-gray-600 dark:hover:bg-gray-700">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Retry
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <FeatureVideoOverlay
        featureId={FEATURE_IDS.VPS_V2}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      />
      <PageBreadcrumb pageTitle="Post Solution Critique Value Proposition Statement" titleSuffix={<CreditCostBadge cost={10} />} />
      <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-2">
        
        {/* Header Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <p className="text-sm text-brand-500 dark:text-gray-400 flex items-center gap-2 px-4 bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-600 py-2 border rounded-lg justify-center">
                <AlertCircle className="w-5 h-5" />
                Review your Value Proposition Statement
              </p>
              
     
            </div>

            <div className="flex items-center gap-3">
              <Button 
                onClick={handleBackToProject} 
                variant="outline" 
                disabled={isBackLoading}
                className="border-brand-300 dark:border-brand-600 text-brand-700 dark:text-brand-200 hover:bg-brand-50 dark:hover:bg-brand-800"
              >
                {isBackLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <ArrowLeft className="w-4 h-4 mr-2" />
                )}
                Back to Solution Critique
              </Button>

              {/* Edit/Save/Cancel Buttons */}
              {isEditing ? (
                <>
                  <Button 
                    onClick={handleSaveChanges}
                    disabled={isSaving}
                    className="bg-green-600 hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700"
                  >
                    {isSaving ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Check className="w-4 h-4 mr-2" />
                    )}
                    Save Changes
                  </Button>
                  <Button 
                    onClick={handleEditToggle}
                    variant="outline"
                    className="border-red-300 dark:border-red-600 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/40"
                  >
                    <X className="w-4 h-4 mr-2" />
                    Cancel
                  </Button>
                </>
              ) : (
                <Button 
                  onClick={handleEditToggle}
                  variant="outline"
                  disabled={isRegenerating}
                  className="border-brand-300 dark:border-brand-600 text-brand-600 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-800/50"
                >
                  <Pencil className="w-4 h-4 mr-2" />
                  Edit VPS
                </Button>
              )}

              <Button 
                onClick={handleRegenerate} 
                variant="default" 
                disabled={isRegenerating || isEditing}
                className="bg-green-600 hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isRegenerating ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4 mr-2" />
                )}
                Regenerate
              </Button>
              
              <Button 
                onClick={handleContinueToBMC}
                disabled={isContinueLoading || isEditing}
                className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-600 dark:hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isContinueLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <ArrowLeft className="w-4 h-4 mr-2 rotate-180" />
                )}
                Continue to BMC v2
              </Button>
            </div>
          </div>
        </motion.div>

                 {/* Persona Selector */}
              <PersonaSelector />

        {/* VPS Primary Statement Display/Edit */}
        {currentVpsData && editedStatement && (
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="my-2 w-auto mx-auto flex items-center justify-center"
          >
            <div>
              <CardContent className="px-4">
                {/* Edit mode notice */}
                {isEditing && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="mb-2 p-4 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg"
                  >
                    <div className="flex items-center gap-2 text-blue-600 dark:text-blue-300">
                      <Edit2 className="w-4 h-4" />
                      <p className="text-sm font-medium">Edit mode: Click on any field to modify your VPS statement</p>
                    </div>
                  </motion.div>
                )}

                <div className="bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-8 py-4 rounded-xl border border-gray-200 dark:border-gray-700 ">
                  <div className="space-y-2 flex-col item-center justify-center">
                    {/* Our */}
                    <div className="flex items-center gap-2">
                      <span className="text-brand-500 dark:text-gray-200 font-bold text-5xl">Our</span>
                      {isEditing ? (
                        <Input
                          value={editedStatement.our}
                          onChange={(e) => handleInputChange('our', e.target.value)}
                          className="bg-white dark:bg-gray-700 border-brand-300 dark:border-brand-600 text-gray-900 dark:text-white rounded-full px-4 py-2 font-medium focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                          placeholder="Enter your product/service..."
                        />
                      ) : (
                        <div className="flex items-center gap-3 m-2">
                          <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-xl inline-block">
                            <div className="pr-36">
                              {editedStatement.our}
                            </div>
                            <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                              Products and Services
                            </span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Help */}
                    <div className="flex items-center gap-4">
                      <span className="text-brand-500 dark:text-gray-200 font-bold text-5xl">Help</span>
                      {isEditing ? (
                        <Input
                          value={editedStatement.help}
                          onChange={(e) => handleInputChange('help', e.target.value)}
                          className="bg-white dark:bg-gray-700 border-brand-300 dark:border-brand-600 text-gray-900 dark:text-white rounded-full px-4 py-2 font-medium focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                          placeholder="Enter target customers..."
                        />
                      ) : (
                        <div className="flex items-center gap-3 m-2">
                          <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-xl inline-block">
                            <div className="pr-32">
                              {editedStatement.help}
                            </div>
                            <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                              Customer Segment
                            </span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Who want to */}
                    <div className="flex gap-4 justify-start items-center">
                      <span className="text-brand-500 dark:text-gray-200 font-bold text-5xl col-span-3 whitespace-nowrap">Who want to</span>
                      {isEditing ? (
                        <div className="col-span-7">
                          <Input
                            value={editedStatement.who_want_to}
                            onChange={(e) => handleInputChange('who_want_to', e.target.value)}
                            className="bg-white dark:bg-gray-700 border-brand-300 dark:border-brand-600 text-gray-900 dark:text-white rounded-full px-4 py-2 font-medium focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                            placeholder="Enter customer goals..."
                          />
                        </div>
                      ) : (
                        <div className="col-span-7 flex items-center gap-3 m-2">
                          <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-xl inline-block">
                            <div className="pr-32">
                              {editedStatement.who_want_to}
                            </div>
                            <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                              Jobs to be done
                            </span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* By */}
                    <div className="flex items-center gap-4">
                      <span className="text-brand-500 dark:text-gray-200 font-bold text-5xl">By</span>
                      {isEditing ? (
                        <Input
                          value={editedStatement.by}
                          onChange={(e) => handleInputChange('by', e.target.value)}
                          className="bg-white dark:bg-gray-800 border-brand-300 dark:border-brand-600 text-gray-900 dark:text-white rounded-full px-4 py-2 font-medium focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                          placeholder="Enter how you help..."
                        />
                      ) : (
                        <div className="flex items-center gap-3 m-2">
                          <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-xl inline-block">
                            <div className="pr-32">
                              {editedStatement.by}
                            </div>
                            <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                              Customer pain
                            </span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* And */}
                    <div className="flex items-center gap-2">
                      <span className="text-brand-500 dark:text-gray-200 font-bold text-5xl">And</span>
                      {isEditing ? (
                        <Input
                          value={editedStatement.and}
                          onChange={(e) => handleInputChange('and', e.target.value)}
                          className="bg-white dark:bg-gray-800 border-brand-300 dark:border-brand-600 text-gray-900 dark:text-white rounded-full px-4 py-2 font-medium focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                          placeholder="Enter additional benefits..."
                        />
                      ) : (
                        <div className="flex items-center gap-3 m-2">
                          <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-xl inline-block">
                            <div className="pr-24">
                              {editedStatement.and}
                            </div>
                            <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                              Customer gain
                            </span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Unlike */}
                    <div className="flex items-center gap-2">
                      <span className="text-brand-500 dark:text-gray-200 font-bold text-5xl">Unlike</span>
                      {isEditing ? (
                        <Input
                          value={editedStatement.unlike}
                          onChange={(e) => handleInputChange('unlike', e.target.value)}
                          className="bg-white dark:bg-gray-800 border-brand-300 dark:border-brand-600 text-gray-900 dark:text-white rounded-full px-4 py-2 font-medium focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                          placeholder="Enter competitive advantage..."
                        />
                      ) : (
                        <div className="flex items-center gap-3 m-2">
                          <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-xl inline-block">
                            <div className="pr-48">
                              {editedStatement.unlike}
                            </div>
                            <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                              competing value proposition
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Extended Statement Section - Moved outside padded container */}
                  <MoreContext 
                    title="More Context" 
                    content={currentVpsData.extended_statement} 
                  />
                  
                </div>
              </CardContent>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}