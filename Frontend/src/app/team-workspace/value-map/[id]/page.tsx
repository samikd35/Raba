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
  Play,
  RefreshCw,
  Check,
  UserCircle2,
  Package,
  Shield,
  Zap
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import toast from "react-hot-toast";
import { motion } from "framer-motion";

// Updated interfaces for the new backend structure
interface GainCreatorCandidate {
  id: string;
  text: string;
  label: string;
  value: string;
  evidence: string;
  priority: 'high' | 'medium' | 'low' | 'critical';
  creates_gain: string[];
}

interface PainRelieverCandidate {
  id: string;
  text: string;
  label: string;
  impact: string;
  evidence: string;
  priority: 'high' | 'medium' | 'low' | 'critical';
  addresses_pain: string[];
}

interface ProductServiceCandidate {
  id: string;
  text: string;
  label: string;
  evidence: string;
  priority: 'high' | 'medium' | 'low' | 'critical';
  addresses_jtbd: string[];
}

interface PersonaValueMapData {
  gain_creators_candidates: GainCreatorCandidate[];
  pain_relievers_candidates: PainRelieverCandidate[];
  products_services_candidates: ProductServiceCandidate[];
  persona_name: string;
}

interface ValueMapResponse {
  success: boolean;
  data: {
    project_id: string;
    value_map_candidates: {
      [personaId: string]: PersonaValueMapData;
    };
    personas_processed: string[];
    generated_at: string;
  };
  message: string;
}

interface ValueMapSelectionsRequest {
  persona_selections: {
    [personaId: string]: {
      selected_product_ids: string[];
      selected_pain_reliever_ids: string[];
      selected_gain_creator_ids: string[];
    };
  };
}

interface ValueMapSelectionsResponse {
  success: boolean;
  message: string;
}

export default function ValueMapPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { isAuthenticated, token } = useAuthStore();
  
  const featureConfig = getFeatureVideoConfig(FEATURE_IDS.VALUE_MAP);

  // Properly unwrap params using React.use()
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  const [valueMapData, setValueMapData] = useState<ValueMapResponse['data']['value_map_candidates'] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [availablePersonas, setAvailablePersonas] = useState<string[]>([]);
  
  // Selection state - Changed to persona-specific tracking
  const [selectedItemsByPersona, setSelectedItemsByPersona] = useState<{[personaId: string]: Set<string>}>({});
  const [savingSelections, setSavingSelections] = useState(false);

  // Local loading state for micro-animations on Regenerate action
  const [isGenerating, setIsGenerating] = useState(false);

  // Data normalization helper - updated for new format
  const normalizePersonaData = useCallback((personaData: PersonaValueMapData) => {
    return {
      products_services: personaData.products_services_candidates || [],
      pain_relievers: personaData.pain_relievers_candidates || [],
      gain_creators: personaData.gain_creators_candidates || [],
    };
  }, []);

  // Get current persona's selected items
  const currentPersonaSelectedItems = useMemo(() => {
    if (!selectedPersona) return new Set<string>();
    return selectedItemsByPersona[selectedPersona] || new Set<string>();
  }, [selectedItemsByPersona, selectedPersona]);

  // Get selection counts per persona and category
  const getSelectionCounts = useMemo(() => {
    if (!valueMapData || !selectedPersona) return { products_services: 0, pain_relievers: 0, gain_creators: 0 };
    
    const personaData = valueMapData[selectedPersona];
    if (!personaData) return { products_services: 0, pain_relievers: 0, gain_creators: 0 };
    
    const normalizedData = normalizePersonaData(personaData);
    const personaSelections = selectedItemsByPersona[selectedPersona] || new Set();
    
    const counts = {
      products_services: normalizedData.products_services?.filter(item => personaSelections.has(item.id)).length || 0,
      pain_relievers: normalizedData.pain_relievers?.filter(item => personaSelections.has(item.id)).length || 0,
      gain_creators: normalizedData.gain_creators?.filter(item => personaSelections.has(item.id)).length || 0,
    };
    
    return counts;
  }, [valueMapData, selectedPersona, selectedItemsByPersona, normalizePersonaData]);

  // Check if all personas have complete selections (3 items per category)
  const canSaveSelections = useMemo(() => {
    if (!valueMapData || availablePersonas.length === 0) return false;
    
    return availablePersonas.every(personaId => {
      const personaData = valueMapData[personaId];
      if (!personaData) return false;
      
      const normalizedData = normalizePersonaData(personaData);
      const personaSelections = selectedItemsByPersona[personaId] || new Set();
      
      const productCount = normalizedData.products_services?.filter(item => personaSelections.has(item.id)).length || 0;
      const painCount = normalizedData.pain_relievers?.filter(item => personaSelections.has(item.id)).length || 0;
      const gainCount = normalizedData.gain_creators?.filter(item => personaSelections.has(item.id)).length || 0;
      
      return productCount === 3 && painCount === 3 && gainCount === 3;
    });
  }, [valueMapData, availablePersonas, selectedItemsByPersona, normalizePersonaData]);

  // Get validation message for incomplete selections
  const getPersonaValidationMessage = useMemo(() => {
    if (!valueMapData || availablePersonas.length === 0) return [];
    
    const messages: string[] = [];
    
    availablePersonas.forEach(personaId => {
      const personaData = valueMapData[personaId];
      if (!personaData) return;
      
      const normalizedData = normalizePersonaData(personaData);
      const personaSelections = selectedItemsByPersona[personaId] || new Set();
      
      const productCount = normalizedData.products_services?.filter(item => personaSelections.has(item.id)).length || 0;
      const painCount = normalizedData.pain_relievers?.filter(item => personaSelections.has(item.id)).length || 0;
      const gainCount = normalizedData.gain_creators?.filter(item => personaSelections.has(item.id)).length || 0;
      
      const incomplete: string[] = [];
      if (productCount < 3) incomplete.push(`Products (${productCount}/3)`);
      if (painCount < 3) incomplete.push(`Pain Relievers (${painCount}/3)`);
      if (gainCount < 3) incomplete.push(`Gain Creators (${gainCount}/3)`);
      
      if (incomplete.length > 0) {
        const personaName = personaData.persona_name || `Persona ${personaId}`;
        messages.push(`${personaName}: ${incomplete.join(', ')}`);
      }
    });
    
    return messages;
  }, [valueMapData, availablePersonas, selectedItemsByPersona, normalizePersonaData]);

  // Handle item selection
  const handleItemSelect = useCallback((
    item: GainCreatorCandidate | PainRelieverCandidate | ProductServiceCandidate,
    category: 'products_services' | 'pain_relievers' | 'gain_creators'
  ) => {
    if (!selectedPersona || !valueMapData) return;
    
    setSelectedItemsByPersona(prevSelections => {
      const newSelections = { ...prevSelections };
      const currentPersonaSelections = newSelections[selectedPersona] || new Set();
      const updatedPersonaSelections = new Set(currentPersonaSelections);
      
      if (currentPersonaSelections.has(item.id)) {
        // Deselect item
        updatedPersonaSelections.delete(item.id);
      } else {
        // Check if we can select more items of this category for this persona
        const personaData = valueMapData[selectedPersona];
        let categoryItems: any[] = [];
        
        switch (category) {
          case 'products_services':
            categoryItems = personaData.products_services_candidates || [];
            break;
          case 'pain_relievers':
            categoryItems = personaData.pain_relievers_candidates || [];
            break;
          case 'gain_creators':
            categoryItems = personaData.gain_creators_candidates || [];
            break;
        }
        
        const selectedCategoryItems = categoryItems.filter(i => currentPersonaSelections.has(i.id));
        
        if (selectedCategoryItems.length < 3) {
          updatedPersonaSelections.add(item.id);
        } else {
          toast.error(`You can only select 3 ${category.replace('_', ' ')} items per persona`);
          return prevSelections;
        }
      }
      
      newSelections[selectedPersona] = updatedPersonaSelections;
      return newSelections;
    });
  }, [selectedPersona, valueMapData]);

  // Save selections
  const saveSelections = useCallback(async () => {
    if (!valueMapData) {
      toast.error("No value map data available", { id: 'selection-validation' });
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

      // Build persona selections object with correct backend format
      const personaSelections: ValueMapSelectionsRequest['persona_selections'] = {};
      
      availablePersonas.forEach(personaId => {
        const personaData = valueMapData[personaId];
        const personaSelectedItems = selectedItemsByPersona[personaId] || new Set();
        
        if (!personaData) return;
        
        const normalizedData = normalizePersonaData(personaData);
        
        personaSelections[personaId] = {
          selected_product_ids: normalizedData.products_services?.filter(item => personaSelectedItems.has(item.id)).map(item => item.id) || [],
          selected_pain_reliever_ids: normalizedData.pain_relievers?.filter(item => personaSelectedItems.has(item.id)).map(item => item.id) || [],
          selected_gain_creator_ids: normalizedData.gain_creators?.filter(item => personaSelectedItems.has(item.id)).map(item => item.id) || [],
        };
      });

      if (process.env.NODE_ENV === 'development') {
        console.log('Saving value map selections:', personaSelections);
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/vpc-v2/value-map-selections`,
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

      const data: ValueMapSelectionsResponse = await response.json();

      if (data.success) {
        const totalSelections = Object.values(personaSelections).reduce((total, persona) => 
          total + persona.selected_product_ids.length + persona.selected_pain_reliever_ids.length + persona.selected_gain_creator_ids.length, 0
        );
        
        toast.success(`Successfully saved ${totalSelections} selections for ${availablePersonas.length} personas!`);
        
        // Navigate to next step
        router.push(`/team-workspace/vpc-v2/${projectId}`);
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
  }, [valueMapData, canSaveSelections, selectedItemsByPersona, availablePersonas, projectId, token, router, normalizePersonaData, getPersonaValidationMessage]);

  // Memoized auth state check
  const isAuthReady = useMemo(() => 
    isAuthenticated && token && projectId,
    [isAuthenticated, token, projectId]
  );

  // Fetch value map data - updated endpoint and response handling
  const fetchValueMapData = useCallback(async () => {
    if (!isAuthReady) {
      if (!isAuthenticated) {
        toast.error("Please sign in to access value map");
        router.push("/signin");
      }
      return;
    }

    try {
      setLoading(true);
      setError(null);

      if (process.env.NODE_ENV === 'development') {
        console.log('=== FETCH VALUE MAP DEBUG ===');
        console.log('Project ID:', projectId);
        console.log('Token available:', !!token);
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/vpc-v2/value-map-candidates`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (process.env.NODE_ENV === 'development') {
        console.log('Value map response status:', response.status);
      }

      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Session expired. Please sign in again.");
          router.push("/signin");
          return;
        }
        if (response.status === 404) {
          // No value map candidates found, trigger generation
          if (process.env.NODE_ENV === 'development') {
            console.log('No value map candidates found, triggering generation...');
          }
          await generateValueMapCandidates();
          return;
        }
        throw new Error(`Failed to fetch value map: ${response.status}`);
      }

      const data: ValueMapResponse = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('Value map response:', data);
      }

      if (data.success && data.data && data.data.value_map_candidates) {
        setValueMapData(data.data.value_map_candidates);
        
        // Set available personas
        const personas = data.data.personas_processed || Object.keys(data.data.value_map_candidates);
        setAvailablePersonas(personas);
        
        // Set first persona as default
        if (personas.length > 0 && !selectedPersona) {
          setSelectedPersona(personas[0]);
        }

        toast.success("Value map candidates loaded successfully!");
      } else {
        throw new Error(data.message || 'Failed to load value map candidates');
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Error fetching value map:', err);
      }
      const errorMessage = err instanceof Error ? err.message : "An error occurred while loading value map";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [isAuthReady, isAuthenticated, token, projectId, router, selectedPersona]);

  /**
   * Generate value map candidates when none exist
   */
  const generateValueMapCandidates = useCallback(async () => {
    if (!isAuthReady || !isAuthenticated || !token) {
      toast.error("Please sign in to generate value map");
      router.push("/signin");
      return;
    }

    try {
      setIsGenerating(true);
      setLoading(true);
      setError(null);

      if (process.env.NODE_ENV === 'development') {
        console.log('=== GENERATE VALUE MAP DEBUG ===');
        console.log('Project ID:', projectId);
        console.log('Token available:', !!token);
      }

      // toast.info("Generating value map candidates... This may take a moment.");

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/vpc-v2/value-map/generate`,
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
        console.log('Generate value map response status:', response.status);
      }

      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Session expired. Please sign in again.");
          router.push("/signin");
          return;
        }
        if (response.status === 404) {
          throw new Error("Project not found or customer profile not completed yet.");
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Failed to generate value map: ${response.status}`);
      }

      const data = await response.json();

      console.log('Generated value map response:', data);

      if (process.env.NODE_ENV === 'development') {
        console.log('Generated value map response:', data);
      }

      if (data.success && data.value_map_candidates) {
        fetchValueMapData();

        toast.success(data.message || "Value map candidates generated successfully!");
      } else {
        throw new Error(data.message || 'Failed to generate value map candidates');
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Error generating value map:', err);
      }
      const errorMessage = err instanceof Error ? err.message : "An error occurred while generating value map";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsGenerating(false);
      setLoading(false);
    }
  }, [isAuthReady, isAuthenticated, token, projectId, router, selectedPersona, fetchValueMapData]);

  // Auto-fetch value map data when page loads
  useEffect(() => {
    if (isAuthReady && !valueMapData && !loading && !error) {
      fetchValueMapData();
    }
  }, [isAuthReady, valueMapData, loading, error, fetchValueMapData]);

  const handleBackToProject = useCallback(() => {
    router.push(`/team-workspace/customer-profile-v2/${projectId}`);
  }, [router, projectId]);

  const handleContinueToVPC = useCallback(() => {
    router.push(`/team-workspace/vpc-v2/${projectId}`);
  }, [router, projectId]);

  // Get display name for persona - updated to use persona_name
  const getPersonaDisplayName = (personaId: string | null) => {
    if (!personaId) return "All Personas";
    if (personaId === "all") return "All Personas";
    
    // Use persona_name if available
    if (valueMapData && valueMapData[personaId] && valueMapData[personaId].persona_name) {
      return valueMapData[personaId].persona_name;
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
  };

  // Get priority color
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
      case 'high':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
      case 'low':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300';
    }
  };

  // Persona selector component
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

  // Render value map section - updated for new format
  const renderValueMapSection = useCallback((
    title: string,
    items: (GainCreatorCandidate | PainRelieverCandidate | ProductServiceCandidate)[],
    icon: React.ReactNode,
    colorClass: string,
    type: 'gain_creators' | 'pain_relievers' | 'products_services'
  ) => {
    if (!items || items.length === 0) {
      return (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="flex items-center gap-2 mb-4">
            {icon}
            <h3 className="text-lg font-semibold text-brand-500 dark:text-white">
              {title} (0)
            </h3>
          </div>
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No {title.toLowerCase()} available
          </div>
        </motion.div>
      );
    }

    // Get selection count for this category
    const selectionCount = getSelectionCounts[type] || 0;
    const isComplete = selectionCount === 3;
    const canSelectMore = selectionCount < 3;

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="space-y-2 flex flex-col h-full"
      >
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {icon}
            <h3 className="text-lg font-semibold text-brand-500 dark:text-white">
              {title} ({'Pick 3'})
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <Badge 
              className={`text-xs ${isComplete 
                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' 
                : 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300'
              }`}
            >
              {selectionCount}/3 selected
            </Badge>
            {isComplete && <Check className="w-4 h-4 text-green-600 dark:text-green-400" />}
          </div>
        </div>
        
        {/* Scrollable Container */}
        <div className="flex-1 overflow-hidden">
          <div 
            className="h-[400px] overflow-y-auto scrollbar-thin scrollbar-thumb-brand-300 dark:scrollbar-thumb-brand-600 scrollbar-track-gray-100 dark:scrollbar-track-gray-800 hover:scrollbar-thumb-brand-400 dark:hover:scrollbar-thumb-brand-500 pr-2"
            style={{
              scrollbarWidth: 'thin',
              scrollbarColor: 'rgb(147 197 253) rgb(243 244 246)'
            }}
          >
            <div className={`flex flex-col gap-4 p-4 rounded-xl border border-gray-200 dark:border-gray-700 ${colorClass}`}>
              {items.map((item, index) => {
                const isSelected = currentPersonaSelectedItems.has(item.id);
                const isDisabled = !isSelected && !canSelectMore;
                
                return (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.3, delay: 0.1 * index }}
                  >
                    <Card 
                      className={`relative transition-all duration-300 cursor-pointer border border-gray-200 dark:border-gray-700 hover:shadow-lg ${
                        isSelected 
                          ? 'ring-2 ring-brand-500 dark:ring-brand-400 bg-brand-50 dark:bg-brand-900/20 border-brand-300 dark:border-brand-500' 
                          : isDisabled
                            ? 'opacity-50 cursor-not-allowed bg-gray-50 dark:bg-gray-800/50'
                            : 'bg-white dark:bg-gray-800 hover:border-brand-300 dark:hover:border-brand-500'
                      }`}
                      onClick={() => !isDisabled && handleItemSelect(item, type)}
                    >
                      <CardHeader>
                        <div className="flex items-start justify-between">
                          <CardTitle className="text-md font-semibold line-clamp-2 flex-1 text-brand-500 dark:text-white pr-8">
                            {item.label}
                          </CardTitle>
                          <div className="flex items-center gap-2">
                            <Badge className={`text-xs ${getPriorityColor(item.priority)}`}>
                              {item.priority}
                            </Badge>
                          </div>
                        </div>
                      </CardHeader>
                      
                      <CardContent className="space-y-3 -mt-4">
                        <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3">
                          {item.text}
                        </p>
                        
                        {/* Type-specific content */}
                        {'value' in item && (
                          <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-700">
                            <h5 className="text-xs font-medium text-green-600 dark:text-green-400 mb-1">Value:</h5>
                            <p className="text-xs text-green-700 dark:text-green-300">{item.value}</p>
                          </div>
                        )}
                        
                        {'impact' in item && (
                          <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-700">
                            <h5 className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">Impact:</h5>
                            <p className="text-xs text-red-700 dark:text-red-300">{item.impact}</p>
                          </div>
                        )}
                        
                        {/* Evidence */}
                        {item.evidence && (
                          <div className="p-2 bg-brand-50 dark:bg-brand-900/20 rounded border border-brand-200 dark:border-brand-700">
                            <h5 className="text-xs font-medium text-brand-600 dark:text-brand-400 mb-1">Evidence:</h5>
                            <p className="text-xs text-brand-700 dark:text-brand-300 italic line-clamp-2">
                              {item.evidence}
                            </p>
                          </div>
                        )}
                        
                       
                       
                      </CardContent>
                      
                      {/* Selection indicator */}
                      <div className="absolute top-2 right-2">
                        {isSelected ? (
                          <div className="w-6 h-6 bg-brand-600 dark:bg-brand-500 rounded-full flex items-center justify-center">
                            <Check className="w-4 h-4 text-white" />
                          </div>
                        ) : !isDisabled ? (
                          <div className="w-6 h-6 border-1 border-gray-300 dark:border-gray-600 rounded-full hover:border-brand-500 dark:hover:border-brand-400 transition-colors" />
                        ) : (
                          <div className="w-6 h-6 border-2 border-gray-200 dark:border-gray-700 rounded-full bg-gray-100 dark:bg-gray-800" />
                        )}
                      </div>
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      </motion.div>
    );
  }, [selectedItemsByPersona, handleItemSelect, getSelectionCounts, getPriorityColor, currentPersonaSelectedItems]);

  // Get current persona data
  const currentPersonaData = useMemo(() => {
    if (!valueMapData || !selectedPersona) return null;
    return valueMapData[selectedPersona] || null;
  }, [valueMapData, selectedPersona]);

  return (
    <div>
      <FeatureVideoOverlay
        featureId={FEATURE_IDS.VALUE_MAP}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      />
      <PageBreadcrumb pageTitle="Build Your Value Map" titleSuffix={<CreditCostBadge cost={10} />} />
      <div className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-white/[0.03] p-2">
        
        {/* Enhanced Header Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {/* Navigation and Actions Bar */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-4">

            <p className="text-sm text-brand-500 flex items-center gap-2 px-4 bg-brand-50 border-brand-200 py-2 border rounded-lg justify-center dark:bg-gray-900/20 dark:text-white dark:border-brand-700">
            <AlertCircle className="w-5 h-5" />


            Select exactly 3 items from each category for each persona to create your Value Proposition Canvas</p>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              {valueMapData && (
                <>
                   <Button 
                onClick={handleBackToProject} 
                variant="outline" 
                className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-150 active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed"
                disabled={loading || savingSelections || isGenerating}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Customer Profile
              </Button>

              <Button 
                variant="default" 
                className="bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 transition-all duration-150 active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed"
                onClick={generateValueMapCandidates}
                disabled={loading || isGenerating}
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>Regenerate</>
                )}
              </Button>
                  
                  {/* Save & Continue to VPC Button */}
                  <Button 
                    onClick={saveSelections}
                    disabled={savingSelections}
                    className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600 transition-all duration-150 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Save and continue to VPC"
                  >
                    {savingSelections ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Check className="w-4 h-4 mr-2" />
                        Save & Continue to VPC
                      </>
                    )}
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Title and Description */}
         
        </motion.div>

        {/* Loading State */}
        {loading && !valueMapData && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center py-12"
          >
            <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-brand-500 dark:text-white">Loading Value Map</h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-sm">
              Retrieving value map candidates including gain creators, pain relievers, and products/services...
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
            <AlertCircle className="w-12 h-12 text-red-500 dark:text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-brand-500 dark:text-white mb-2">Loading Failed</h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md">{error}</p>
            <div className="flex gap-2">
              <Button onClick={fetchValueMapData} variant="outline" className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800">
                <RefreshCw className="w-4 h-4 mr-2" />
                Try Again
              </Button>
              <Button onClick={handleBackToProject} className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Customer Profile
              </Button>
            </div>
          </motion.div>
        )}

        {/* Value Map Content */}
        {valueMapData && (
          <div>
            {/* Persona Selector */}
            <PersonaSelector />

            {/* Current Persona Info */}
            

            {currentPersonaData ? (
              <Card className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-4">
                {/* Products & Services */}
                {renderValueMapSection(
                  "Products & Services",
                  currentPersonaData.products_services_candidates || [],
                  <Package className="w-6 h-6 text-brand-600 dark:text-brand-400" />,
                  "border-l-brand-500 bg-brand-50 dark:bg-brand-900/30",
                  "products_services"
                )}

                {/* Pain Relievers */}
                {renderValueMapSection(
                  "Pain Relievers",
                  currentPersonaData.pain_relievers_candidates || [],
                  <Shield className="w-6 h-6 text-red-600 dark:text-red-400" />,
                  "border-l-red-500 bg-red-50 dark:bg-red-900/30",
                  "pain_relievers"
                )}

                {/* Gain Creators */}
                {renderValueMapSection(
                  "Gain Creators",
                  currentPersonaData.gain_creators_candidates || [],
                  <Zap className="w-6 h-6 text-green-600 dark:text-green-400" />,
                  "border-l-green-500 bg-green-50 dark:bg-green-900/30",
                  "gain_creators"
                )}
              </Card>
            ) : selectedPersona ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="text-center py-12"
              >
                <AlertCircle className="w-12 h-12 text-yellow-500 dark:text-yellow-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-brand-500 dark:text-white mb-2">
                  No Data Available
                </h3>
                <p className="text-gray-600 dark:text-gray-400 text-center max-w-md">
                  No value map data found for {getPersonaDisplayName(selectedPersona)}
                </p>
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="text-center py-12"
              >
                <Users className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-brand-500 dark:text-white mb-2">
                  Select a Persona
                </h3>
                <p className="text-gray-600 dark:text-gray-400 text-center max-w-md">
                  Choose a persona from the tabs above to view their value map data
                </p>
              </motion.div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}