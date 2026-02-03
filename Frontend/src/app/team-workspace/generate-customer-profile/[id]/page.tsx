"use client";

import PageBreadcrumb from "@/components/common/module 2/PageBreadCrumb";
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
  Play,
  RefreshCw,
  Check,
  UserCircle2
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import toast from "react-hot-toast";
import { motion } from "framer-motion";

interface Evidence {
  source: string;
  quote: string;
}

interface CustomerProfileItem {
  id: string;
  type: 'jtbd' | 'pain' | 'gain';
  label: string;
  description: string;
  evidence: Evidence[];
  confidence: number;
  maps_to: string | null;
  persona_id: string;
}

interface CustomerProfile {
  jobs_to_be_done: CustomerProfileItem[];
  pains: CustomerProfileItem[];
  gains: CustomerProfileItem[];
}

interface GenerationMetadata {
  model_used: string;
  context_items_used: number;
  generation_time: string;
  generation_type: string;
}

interface ContextSummary {
  total_items: number;
  pv_items: number;
  insights_items: number;
  query: string;
  project_id: string;
  pv_report_id: string;
}

// Updated to match exact backend response format
interface CustomerProfileResponse {
  success: boolean;
  data: {
    customer_profile_candidates: {
      customer_profile: CustomerProfile;
      value_map: Record<string, any>;
      generation_metadata: GenerationMetadata;
    };
    generation_metadata: GenerationMetadata;
    context_summary: ContextSummary;
  };
  message: string;
  next_step: string;
}

interface ExistingCustomerProfileResponse {
  success: boolean;
  data: {
    project_id: string;
    customer_profile_candidates: {
      gains: CustomerProfileItem[];
      pains: CustomerProfileItem[];
      jobs_to_be_done: CustomerProfileItem[];
    };
    generation_metadata: Record<string, any>;
    generated_at: string;
  };
  message: string;
}

interface SelectionResponse {
  success: boolean;
  data: {
    project_id: string;
    personas_updated: string[];
    total_selections: number;
  };
  message: string;
  next_step: string;
}

interface PersonaSelections {
  [personaId: string]: {
    jtbd: string[];
    pain: string[];
    gain: string[];
  };
}

export default function GenerateCustomerProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { isAuthenticated, token } = useAuthStore();
  
  // Properly unwrap params using React.use() - MUST be declared first
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  
  // Feature video configuration
  const featureConfig = getFeatureVideoConfig(FEATURE_IDS.CUSTOMER_PROFILE);

  const [customerProfile, setCustomerProfile] = useState<CustomerProfile | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [contextSummary, setContextSummary] = useState<ContextSummary | null>(null);
  
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  
  const [savingSelections, setSavingSelections] = useState(false);
  
  // --- NEW State for Persona Toggle ---
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [availablePersonas, setAvailablePersonas] = useState<string[]>([]);
  
  // Memoized auth state check
  const isAuthReady = useMemo(() => 
    isAuthenticated && token && projectId,
    [isAuthenticated, token, projectId]
  );

  // Initialize personas and selected persona from cached data
  useEffect(() => {
    if (customerProfile && availablePersonas.length === 0) {
      const allItems = [
        ...(customerProfile.jobs_to_be_done || []),
        ...(customerProfile.pains || []),
        ...(customerProfile.gains || [])
      ];
      
      const personaIds = new Set<string>();
      allItems.forEach(item => {
        if (item.persona_id) {
          personaIds.add(item.persona_id);
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
  }, [customerProfile, availablePersonas.length, selectedPersona]);

  const fetchOrGenerateCustomerProfile = useCallback(async () => {
    if (!isAuthReady) {
      if (!isAuthenticated) {
        toast.error("Please sign in to access customer profile");
        router.push("/signin");
      }
      return;
    }

    try {
      setLoading(true);
      setError(null);

      if (process.env.NODE_ENV === 'development') {
        console.log('=== FETCH CUSTOMER PROFILE DEBUG ===');
        console.log('Project ID:', projectId);
        console.log('Token available:', !!token);
      }

      // Directly generate Regenerate Customer Profile candidates (removed check for existing)
      if (process.env.NODE_ENV === 'development') {
        console.log('Generating Regenerate Customer Profile candidates...');
      }

      const generateResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/vpc/step1/generate-customer-profile`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            creativity_level: 0.7,
            include_context_summary: true
          }),
        }
      );

      if (process.env.NODE_ENV === 'development') {
        console.log('Generate response status:', generateResponse.status);
      }

      if (!generateResponse.ok) {
        if (generateResponse.status === 401) {
          toast.error("Session expired. Please sign in again.");
          router.push("/signin");
          return;
        }
        throw new Error(`Failed to generate customer profile: ${generateResponse.status}`);
      }

      const generateData: CustomerProfileResponse = await generateResponse.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('Generated customer profile response:', generateData);
      }

      // Updated to match exact backend response structure
      if (generateData.success && generateData.data?.customer_profile_candidates?.customer_profile) {
        const profile = generateData.data.customer_profile_candidates.customer_profile;
        const context = generateData.data.context_summary;
        
        setCustomerProfile(profile);
        setContextSummary(context);
        
        // Extract available personas from the generated profile
        const allItems = [
          ...(profile.jobs_to_be_done || []),
          ...(profile.pains || []),
          ...(profile.gains || [])
        ];
        
        const personaIds = new Set<string>();
        allItems.forEach(item => {
          if (item.persona_id) {
            personaIds.add(item.persona_id);
          }
        });
        
        const personas = Array.from(personaIds).sort();
        setAvailablePersonas(personas);
        
        // Set first persona as default if available
        if (personas.length > 0 && !selectedPersona) {
          setSelectedPersona(personas[0]);
        }

        toast.success("Customer profile generated successfully!");
      } else {
        throw new Error(generateData.message || 'Failed to generate customer profile');
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Error generating customer profile:', err);
      }
      const errorMessage = err instanceof Error ? err.message : "An error occurred while generating customer profile";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [isAuthReady, isAuthenticated, token, projectId, router]);

  const handleRegenerateProfile = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Clear current data
      setCustomerProfile(null);
      setContextSummary(null);
      setSelectedItems(new Set());
      
      // Generate new profile
      await fetchOrGenerateCustomerProfile();
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Error regenerating profile:', err);
      }
      const errorMessage = err instanceof Error ? err.message : "An error occurred while regenerating customer profile";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [projectId, fetchOrGenerateCustomerProfile]);

  // Auto-fetch/generate customer profile when page loads
  useEffect(() => {
    if (isAuthReady && !customerProfile && !loading && !error) {
      fetchOrGenerateCustomerProfile();
    }
  }, [isAuthReady, customerProfile, loading, error, fetchOrGenerateCustomerProfile]);

  const handleBackToProject = useCallback(() => {
    router.push(`/team-workspace/personas/${projectId}`);
  }, [router, projectId]);

  // Get display name for persona
  const getPersonaDisplayName = (personaId: string | null) => {
    if (!personaId) return "All Personas";
    if (personaId === "all") return "All Personas";
    
    // Try to extract a meaningful name from persona ID
    if (personaId.includes('_')) {
      const parts = personaId.split('_');
      const lastPart = parts[parts.length - 1];
      if (!isNaN(Number(lastPart))) {
        return `Persona ${lastPart}`;
      }
    }
    
    return `Persona ${personaId}`;
  };

    const getPersonaDisplay = (personaId: string | null) => {
    if (!personaId) return "All Personas";
    if (personaId === "all") return "All Personas";
    
    // Try to extract a meaningful name from persona ID
    if (personaId.includes('_')) {
      const parts = personaId.split('_');
      const lastPart = parts[parts.length - 1];
      if (!isNaN(Number(lastPart))) {
        return `Persona ${lastPart}`;
      }
    }
    
    return `${personaId}`;
  };


  // Persona selector component
  const PersonaSelector = ({ compact = false }: { compact?: boolean }) => {
    if (availablePersonas.length <= 1) return null;

    return (
      <div className={`flex justify-center ${compact ? 'mb-4' : 'mb-4'}`}>
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

  const getItemsOfType = useCallback((type: 'jtbd' | 'pain' | 'gain'): CustomerProfileItem[] => {
    if (!customerProfile) return [];
    
    switch (type) {
      case 'jtbd':
        return customerProfile.jobs_to_be_done || [];
      case 'pain':
        return customerProfile.pains || [];
      case 'gain':
        return customerProfile.gains || [];
      default:
        return [];
    }
  }, [customerProfile]);

  const getSelectionCounts = useMemo(() => {
    if (!customerProfile) return {};
    
    const counts: Record<string, Record<string, number>> = {};
    
    // Get all unique personas
    const allItems = [
      ...(customerProfile.jobs_to_be_done || []),
      ...(customerProfile.pains || []),
      ...(customerProfile.gains || [])
    ];
    
    const personas = [...new Set(allItems.map(item => item.persona_id))];
    
    personas.forEach(personaId => {
      counts[personaId] = {
        jtbd: (customerProfile.jobs_to_be_done || []).filter(item => 
          item.persona_id === personaId && selectedItems.has(item.id)
        ).length,
        pain: (customerProfile.pains || []).filter(item => 
          item.persona_id === personaId && selectedItems.has(item.id)
        ).length,
        gain: (customerProfile.gains || []).filter(item => 
          item.persona_id === personaId && selectedItems.has(item.id)
        ).length
      };
    });
    
    return counts;
  }, [customerProfile, selectedItems]);

  const handleItemSelect = useCallback((item: CustomerProfileItem) => {
    setSelectedItems(prevSelected => {
      const newSelected = new Set(prevSelected);
      
      if (prevSelected.has(item.id)) {
        // Deselect item
        newSelected.delete(item.id);
      } else {
        // Check if we can select more items of this type for this persona
        const sameTypeItems = getItemsOfType(item.type).filter(i => i.persona_id === item.persona_id);
        const selectedSameType = sameTypeItems.filter(i => prevSelected.has(i.id));
        
        if (selectedSameType.length < 3) {
          newSelected.add(item.id);
        } else {
          toast.error(`You can only select 3 ${item.type} items per persona`);
          return prevSelected; // Return unchanged state
        }
      }
      
      return newSelected;
    });
  }, [getItemsOfType]);

  const canSaveSelections = useMemo(() => {
    const counts = getSelectionCounts;
    return Object.keys(counts).length > 0 && Object.values(counts).every(personaCounts => 
      personaCounts.jtbd === 3 && personaCounts.pain === 3 && personaCounts.gain === 3
    );
  }, [getSelectionCounts]);

  // Get validation message for persona selections
  const getPersonaValidationMessage = useMemo(() => {
    const counts = getSelectionCounts;
    const messages: string[] = [];
    
    availablePersonas.forEach(personaId => {
      const personaCounts = counts[personaId] || { jtbd: 0, pain: 0, gain: 0 };
      const incomplete: string[] = [];
      
      if (personaCounts.jtbd < 3) incomplete.push(`Jobs (${personaCounts.jtbd}/3)`);
      if (personaCounts.pain < 3) incomplete.push(`Pains (${personaCounts.pain}/3)`);
      if (personaCounts.gain < 3) incomplete.push(`Gains (${personaCounts.gain}/3)`);
      
      if (incomplete.length > 0) {
        messages.push(`${getPersonaDisplay(personaId)}: ${incomplete.join(', ')}`);
      }
    });
    
    return messages;
  }, [getSelectionCounts, availablePersonas, getPersonaDisplay]);

  const saveSelections = useCallback(async () => {
    if (!customerProfile) {
      toast.error("No customer profile available", { id: 'selection-validation' });
      return;
    }

    // Check if selections are complete and show detailed message if not
    if (!canSaveSelections) {
      const validationMessages = getPersonaValidationMessage;
      if (validationMessages.length > 0) {
        toast.error(
          <div className="text-left">
            <p className="font-semibold mb-2">Please complete your selections:</p>
            <ul className="text-sm space-y-1">
              {validationMessages.map((msg, idx) => (
                <li key={idx}>• {msg}</li>
              ))}
            </ul>
          </div>,
          { duration: 5000, id: 'selection-validation' }
        );
      } else {
        toast.error("Please select exactly 3 items from each category for all personas", { id: 'selection-validation' });
      }
      return;
    }

    try {
      setSavingSelections(true);

      // Build persona selections object
      const personaSelections: PersonaSelections = {};
      
      // Get all unique personas
      const allItems = [
        ...(customerProfile.jobs_to_be_done || []),
        ...(customerProfile.pains || []),
        ...(customerProfile.gains || [])
      ];
      
      const personas = [...new Set(allItems.map(item => item.persona_id))];
      
      personas.forEach(personaId => {
        personaSelections[personaId] = {
          jtbd: (customerProfile.jobs_to_be_done || [])
            .filter(item => item.persona_id === personaId && selectedItems.has(item.id))
            .map(item => item.id),
          pain: (customerProfile.pains || [])
            .filter(item => item.persona_id === personaId && selectedItems.has(item.id))
            .map(item => item.id),
          gain: (customerProfile.gains || [])
            .filter(item => item.persona_id === personaId && selectedItems.has(item.id))
            .map(item => item.id)
        };
      });

      if (process.env.NODE_ENV === 'development') {
        console.log('Saving persona selections:', personaSelections);
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/vpc/step1/select-customer-profile`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            persona_selections: personaSelections
          }),
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Session expired. Please sign in again.");
          router.push("/signin");
          return;
        }
        throw new Error(`Failed to save selections: ${response.status}`);
      }

      const data: SelectionResponse = await response.json();

      if (data.success) {
        toast.success(`Successfully saved ${data.data.total_selections} selections for ${data.data.personas_updated.length} personas!`);
        
        // Navigate to next step (value map)
        router.push(`/team-workspace/vpc/${projectId}`);
      } else {
        throw new Error(data.message || 'Failed to save selections');
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Error saving selections:', err);
      }
      const errorMessage = err instanceof Error ? err.message : "An error occurred while saving selections";
      toast.error(errorMessage);
    } finally {
      setSavingSelections(false);
    }
  }, [customerProfile, canSaveSelections, selectedItems, projectId, token, router, getPersonaValidationMessage]);

  const getConfidenceColor = useCallback((confidence: number) => {
    if (confidence >= 0.8) return "bg-green-500";
    if (confidence >= 0.6) return "bg-yellow-500";
    return "bg-red-500";
  }, []);

  const getConfidenceLabel = useCallback((confidence: number) => {
    if (confidence >= 0.8) return "High";
    if (confidence >= 0.6) return "Medium";
    return "Low";
  }, []);

  const renderProfileSection = useCallback((
    title: string,
    items: CustomerProfileItem[],
    icon: React.ReactNode,
    colorClass: string
  ) => {
    // ALWAYS filter items by selected persona - no fallback to show all
    if (!selectedPersona) {
      return (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="space-y-2"
        >
          <div className="flex items-center gap-2 mb-2">
            {icon}
            <h3 className="text-lg font-semibold text-brand-500 dark:text-white">
              {title} ({'Pick 3'})
            </h3>
          </div>
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            Select a persona to view items
          </div>
        </motion.div>
      );
    }

    const filteredItems = items.filter(item => item.persona_id === selectedPersona);
    const counts = getSelectionCounts;
    
    if (!filteredItems.length) {
      return (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="space-y-4"
        >
          <div className="flex items-center gap-2 mb-4">
            {icon}
            <h3 className="text-lg font-semibold text-brand-500 dark:text-white">
              {title} ({'Pick 3'})
            </h3>
          </div>
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No {title.toLowerCase()} items available for {getPersonaDisplayName(selectedPersona)}
          </div>
        </motion.div>
      );
    }

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="space-y-4 flex flex-col h-full"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            {icon}
            <h3 className="text-lg font-semibold text-brand-500 dark:text-white">
              {title} ({'Pick 3'})
            </h3>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {selectedPersona && counts[selectedPersona] && (
              <span>
                {getPersonaDisplay(selectedPersona)}: {counts[selectedPersona][filteredItems[0]?.type] || 0}/3
              </span>
            )}
          </div>
        </div>
        
        {/* Scrollable Container */}
        <div className="flex-1 overflow-hidden">
          <div 
            className="h-[350px] overflow-y-auto scrollbar-thin scrollbar-thumb-brand-300 dark:scrollbar-thumb-brand-600 scrollbar-track-gray-100 dark:scrollbar-track-gray-800 hover:scrollbar-thumb-brand-400 dark:hover:scrollbar-thumb-brand-500 pr-2"
            style={{
              scrollbarWidth: 'thin'
            }}
          >
            <div className="flex flex-col gap-4 p-4 bg-brand-25 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700">
              {filteredItems.map((item, index) => {
                const isSelected = selectedItems.has(item.id);
                const personaCounts = counts[item.persona_id] || { jtbd: 0, pain: 0, gain: 0 };
                const typeCount = personaCounts[item.type] || 0;
                const canSelect = typeCount < 3 || isSelected;
                
                return (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.3, delay: 0.1 * index }}
                  >
                    <Card 
                      className={`cursor-pointer transition-all duration-300 ${
                        isSelected 
                          ? 'bg-brand-100 dark:bg-brand-900/30 border-brand-500 dark:border-brand-400 border-2 shadow-lg' 
                          : canSelect
                            ? 'bg-brand-25 dark:bg-gray-800 border border-brand-200 dark:border-gray-700 hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-500'
                            : 'bg-gray-100 dark:bg-gray-700/50 border border-gray-300 dark:border-gray-600 opacity-50 cursor-not-allowed'
                      }`}
                      onClick={() => canSelect && handleItemSelect(item)}
                    >
                      <CardHeader>
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-2 flex-1">
                            {isSelected && (
                              <div className="flex-shrink-0 w-6 h-6 bg-brand-600 dark:bg-brand-500 rounded-full flex items-center justify-center mt-1">
                                <Check className="w-4 h-4 text-white" />
                              </div>
                            )}
                            <CardTitle className="text-md font-semibold line-clamp-2 flex-1 text-brand-500 dark:text-white">
                              {item.label}
                            </CardTitle>
                          </div>
                        </div>
                      </CardHeader>
                      
                      <CardContent className="space-y-2 -mt-4">
                        <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-4">
                          {item.description}
                        </p>
                        
                        {item.evidence?.length > 0 && (
                          <div>
                            <h5 className="text-xs font-medium text-green-500 dark:text-green-400 mb-2">Evidence:</h5>
                            <div className="space-y-2">
                              {item.evidence.slice(0, 2).map((evidence, idx) => (
                                <div key={idx} className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded text-xs border border-gray-100 dark:border-gray-600">
                                  <Badge variant="outline" className="text-xs mb-1 capitalize bg-white/50 dark:bg-gray-600/50 border-green-200 dark:border-green-600 text-green-700 dark:text-green-200 px-2 py-1">
                                    {evidence.source}
                                  </Badge>
                                  <p className="italic text-gray-600 dark:text-gray-400 line-clamp-2">
                                    "{evidence.quote}"
                                  </p>
                                </div>
                              ))}
                              {item.evidence.length > 2 && (
                                <p className="text-xs text-brand-500 dark:text-brand-400">
                                  +{item.evidence.length - 2} more evidence
                                </p>
                              )}
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      </motion.div>
    );
  }, [selectedItems, getSelectionCounts, handleItemSelect, selectedPersona]);

  return (
    <div>
      <FeatureVideoOverlay
        featureId={FEATURE_IDS.CUSTOMER_PROFILE}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      />
      <PageBreadcrumb pageTitle="Build Your Customer Profile" titleSuffix={<CreditCostBadge cost={10} />} />
      <div className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-white/[0.03] p-2">
        
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex items-center justify-between rounded-xl mb-2 border border-green-200 dark:border-green-700 px-4 py-3 bg-green-50 dark:bg-green-900/20"
        >
          <div>
            <p className="text-brand-500 dark:text-brand-100 text-sm">
              {/* We are generating a comprehensive customer profile for you. <br />  */}
              {availablePersonas.length > 1 
                ? `Select exactly 3 Customer Pains, 3 Customer Jobs, and 3 Customer Gains for EACH Persona.`
                : 'Select exactly 3 Customer Pains, 3 Customer Jobs, and 3 Customer Gains.'}
            </p>
            {!canSaveSelections && getPersonaValidationMessage.length > 0 && (
              <div className="mt-2 text-xs text-orange-600 dark:text-orange-400">
                <span className="font-semibold">Incomplete selections:</span> {getPersonaValidationMessage.join(' | ')}
              </div>
            )}
          </div>
          <div className="flex gap-3">
            <Button onClick={handleBackToProject} variant="outline" className="text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Personas
            </Button>
            {!customerProfile && (
              <Button 
                onClick={fetchOrGenerateCustomerProfile} 
                disabled={loading}
                className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin text-brand-600 dark:text-brand-400" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                Build Customer Profile
              </Button>
            )}
           
            {customerProfile && (
              <Button 
                onClick={handleRegenerateProfile} 
                disabled={loading}
                className="bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin text-green-600 dark:text-green-400" />
                ) : (
                  <RefreshCw className="w-4 h-4 mr-2" />
                )}
                Rebuild Customer Profile
              </Button>
            )}

            {customerProfile && (
              <Button 
                onClick={saveSelections} 
                disabled={savingSelections}
                className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Save and continue to VPC"
              >
                {savingSelections ? (
                  <div className="flex items-center">
                    <Loader2 className="w-4 h-4 mr-2 animate-spin text-brand-600 dark:text-brand-400" />
                    <motion.span
                      className="flex items-center gap-1 mr-2"
                      initial="start"
                      animate="end"
                      variants={{}}
                    >
                      <motion.span
                        className="w-1.5 h-1.5 rounded-full bg-white/90"
                        initial={{ opacity: 0.3, y: 0 }}
                        animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
                        transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut", delay: 0 }}
                      />
                      <motion.span
                        className="w-1.5 h-1.5 rounded-full bg-white/90"
                        initial={{ opacity: 0.3, y: 0 }}
                        animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
                        transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut", delay: 0.15 }}
                      />
                      <motion.span
                        className="w-1.5 h-1.5 rounded-full bg-white/90"
                        initial={{ opacity: 0.3, y: 0 }}
                        animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
                        transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut", delay: 0.3 }}
                      />
                    </motion.span>
                    <span>Saving...</span>
                  </div>
                ) : (
                  <>
                    <Check className="w-4 h-4 mr-2" />
                    Save All & Review
                  </>
                )}
              </Button>
            )}
          </div>
        </motion.div>

        {/* Loading State */}
        {loading && !customerProfile && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center py-12"
          >
                        <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-brand-500 dark:text-white">Building Your Customer Profile</h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-sm">
              Analyzing your project data to build comprehensive Customer Profiles, including Customer Pains, Customer Jobs, and Customer Gains...
            </p>
          </motion.div>
        )}

        {/* Error State */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center py-12"
          >
            <AlertCircle className="w-12 h-12 text-red-500 dark:text-red-400 mb-4" />
            <h3 className="text-lg font-semibold text-brand-500 dark:text-white mb-2">Generation Failed</h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md mb-4">{error}</p>
            <div className="flex gap-2">
              <Button onClick={fetchOrGenerateCustomerProfile} variant="outline" className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800">
                <RefreshCw className="w-4 h-4 mr-2" />
                Try Again
              </Button>
              <Button onClick={handleBackToProject} className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Personas
              </Button>
            </div>
          </motion.div>
        )}

        {/* Customer Profile Content */}
        {customerProfile && (
          <div className="py-1">
            {/* Persona Selector */}
            <PersonaSelector />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Pains */}
              {renderProfileSection(
                "Customer Pains",
                customerProfile.pains || [],
                <svg xmlns="http://www.w3.org/2000/svg" width="2em" height="2em" viewBox="0 0 16 16"><path fill="#E7000B" fillRule="evenodd" d="M13.293 0c.39 0 .707.317.707.707V2h1.293a.707.707 0 0 1 .5 1.207l-1.46 1.46A1.14 1.14 0 0 1 13.53 5h-1.47L8.53 8.53a.75.75 0 0 1-1.06-1.06L11 3.94V2.47c0-.301.12-.59.333-.804l1.46-1.46a.7.7 0 0 1 .5-.207M2.5 8a5.5 5.5 0 0 1 6.598-5.39a.75.75 0 0 0 .298-1.47A7 7 0 1 0 14.86 6.6a.75.75 0 0 0-1.47.299q.109.533.11 1.101a5.5 5.5 0 1 1-11 0m5.364-2.496a.75.75 0 0 0-.08-1.498A4 4 0 1 0 11.988 8.3a.75.75 0 0 0-1.496-.111a2.5 2.5 0 1 1-2.63-2.686" clipRule="evenodd"/></svg>,
                "border-l-red-500"
              )}

              {/* Jobs to be Done */}
              {renderProfileSection(
                "Customer Jobs",
                customerProfile.jobs_to_be_done || [],
                <Target className="w-6 h-6 text-blue-600 dark:text-blue-400" />,
                "border-l-blue-500"
              )}

              {/* Gains */}
              {renderProfileSection(
                "Customer Gains",
                customerProfile.gains || [],
                <TrendingUp className="w-6 h-6 text-green-600 dark:text-green-400" />,
                "border-l-green-500"
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}