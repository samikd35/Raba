"use client";

import PageBreadcrumb from "@/components/common/module 2/sub-module-2/PageBreadCrumb";
import CreditCostBadge from "@/components/common/CreditCostBadge";
import FeatureVideoOverlay from "@/components/feature-videos/FeatureVideoOverlay";
import { FEATURE_IDS, getFeatureVideoConfig } from "@/lib/featureVideos";
import React, { useState, useEffect, use, useCallback, useMemo, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
  X
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import toast from "react-hot-toast";
import { motion } from "framer-motion";

// Updated interfaces for the backend structure

// Value Map Items (for P2-style data with gain_creators, pain_relievers, products_services)
interface GainCreator {
  id: string;
  text: string;
  label: string;
  value: string;
  evidence: string;
  priority: string;
  creates_gain: string[];
}

interface PainReliever {
  id: string;
  text: string;
  label: string;
  impact: string;
  evidence: string;
  priority: string;
  addresses_pain: string[];
}

interface ProductService {
  id: string;
  text: string;
  label: string;
  evidence: string;
  priority: string;
  addresses_jtbd: string[];
}


interface ValueMapData {
  gain_creators: GainCreator[];
  pain_relievers: PainReliever[];
  products_services: ProductService[];
  persona_name: string;
}

interface ValueMapSelectionsResponse {
  success: boolean;
  data: {
    project_id: string;
    value_map_selections: {
      [personaId: string]: ValueMapData; // Each persona directly contains ValueMapData
    };
    personas_processed: string[];
    format: string;
    selected_at: string;
  };
  message: string;
}

// Helper function to get persona data
const getPersonaData = (responseData: ValueMapSelectionsResponse['data'], personaId: string): ValueMapData | null => {
  return responseData?.value_map_selections?.[personaId] || null;
};

export default function ValueMapSelectionsPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { isAuthenticated, token } = useAuthStore();
  
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  // const featureConfig = getFeatureVideoConfig(FEATURE_IDS.VALUE_MAP);
  const [responseData, setResponseData] = useState<ValueMapSelectionsResponse['data'] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [availablePersonas, setAvailablePersonas] = useState<string[]>([]);
  const [hasShownSuccessToast, setHasShownSuccessToast] = useState(false);
  const hasNotFoundRedirectedRef = useRef(false);
  
  // Per-button micro-loading states
  const [isBackLoading, setIsBackLoading] = useState(false);
  const [isReselectLoading, setIsReselectLoading] = useState(false);
  const [isContinueLoading, setIsContinueLoading] = useState(false);
  
  // Edit state management
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingData, setEditingData] = useState<any>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Memoized auth state check
  const isAuthReady = useMemo(() => 
    isAuthenticated && token && projectId,
    [isAuthenticated, token, projectId]
  );

  // Fetch value map selections data
  const fetchValueMapSelections = useCallback(async () => {
    if (!isAuthReady) {
      if (!isAuthenticated) {
        toast.error("Please sign in to access value map selections", { id: 'auth-error' });
        router.push("/signin");
      }
      return;
    }

    try {
      setLoading(true);
      setError(null);

      if (process.env.NODE_ENV === 'development') {
        console.log('=== FETCH VALUE MAP SELECTIONS DEBUG ===');
        console.log('Project ID:', projectId);
        console.log('Token available:', !!token);
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/vpc-v2/value-map-selections`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (process.env.NODE_ENV === 'development') {
        console.log('Value map selections response status:', response.status);
      }

      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Session expired. Please sign in again.", { id: 'session-expired' });
          router.push("/signin");
          return;
        }
        if (response.status === 404) {
          if (!hasNotFoundRedirectedRef.current) {
            hasNotFoundRedirectedRef.current = true;
            toast.error("Value map selections not found. Please generate them first.", { id: 'not-found-error' });
            router.push(`/team-workspace/value-map/${projectId}`);
          }
          return;
        }
        throw new Error(`Failed to fetch value map selections: ${response.status}`);
      }

      const data: ValueMapSelectionsResponse = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('Value map selections response:', data);
      }

      if (data.success && data.data) {
        setResponseData(data.data);
        
        // Set available personas from personas_processed or value_map_selections keys
        const personas = data.data.personas_processed || Object.keys(data.data.value_map_selections || {});
        setAvailablePersonas(personas);
        
        // Set first persona as default
        if (personas.length > 0 && !selectedPersona) {
          setSelectedPersona(personas[0]);
        }

        if (!hasShownSuccessToast) {
          setHasShownSuccessToast(true);
          toast.success("Value map selections loaded successfully!", { id: 'load-success' });
        }
      } else {
        throw new Error(data.message || 'Failed to load value map selections');
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Error fetching value map selections:', err);
      }
      const errorMessage = err instanceof Error ? err.message : "An error occurred while loading value map selections";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [isAuthReady, isAuthenticated, token, projectId, router, selectedPersona]);

  // Auto-fetch data when page loads
  useEffect(() => {
    if (isAuthReady && !responseData && !loading && !error) {
      fetchValueMapSelections();
    }
  }, [isAuthReady, responseData, loading, error, fetchValueMapSelections]);

  const handleBackToProject = useCallback(() => {
    if (isBackLoading) return;
    setIsBackLoading(true);
    router.push(`/team-workspace/customer-profile-v2/${projectId}`);
  }, [router, projectId, isBackLoading]);

  const handleReselect = useCallback(() => {
    if (isReselectLoading) return;
    setIsReselectLoading(true);
    router.push(`/team-workspace/value-map/${projectId}`);
  }, [router, projectId, isReselectLoading]);

  const handleContinueToVPC = useCallback(() => {
    if (isContinueLoading) return;
    setIsContinueLoading(true);
    router.push(`/team-workspace/vpc-v2/${projectId}`);
  }, [router, projectId, isContinueLoading]);

  // Edit handlers
  const handleEdit = useCallback((item: any, itemType: string) => {
    setEditingId(item.id);
    setEditingData({ ...item, itemType });
  }, []);

  const handleCancelEdit = useCallback(() => {
    setEditingId(null);
    setEditingData(null);
  }, []);

  const handleSave = useCallback(async () => {
    if (!editingData || !selectedPersona || !responseData) return;

    try {
      setIsSaving(true);
      
      // Create a deep copy of ALL value map selections to maintain complete structure
      const allValueMapSelections = JSON.parse(JSON.stringify(responseData.value_map_selections));
      
      // Update the specific item in the selected persona
      const updatedPersonaData = allValueMapSelections[selectedPersona];
      
      if (editingData.itemType === 'gain_creator') {
        updatedPersonaData.gain_creators = updatedPersonaData.gain_creators.map((item: GainCreator) => 
          item.id === editingData.id ? {
            ...item,
            text: editingData.text,
            label: editingData.label,
            value: editingData.value,
            evidence: editingData.evidence,
            priority: editingData.priority,
            creates_gain: editingData.creates_gain
          } : item
        );
      } else if (editingData.itemType === 'pain_reliever') {
        updatedPersonaData.pain_relievers = updatedPersonaData.pain_relievers.map((item: PainReliever) => 
          item.id === editingData.id ? {
            ...item,
            text: editingData.text,
            label: editingData.label,
            impact: editingData.impact,
            evidence: editingData.evidence,
            priority: editingData.priority,
            addresses_pain: editingData.addresses_pain
          } : item
        );
      } else if (editingData.itemType === 'product_service') {
        updatedPersonaData.products_services = updatedPersonaData.products_services.map((item: ProductService) => 
          item.id === editingData.id ? {
            ...item,
            text: editingData.text,
            label: editingData.label,
            evidence: editingData.evidence,
            priority: editingData.priority,
            addresses_jtbd: editingData.addresses_jtbd
          } : item
        );
      }

      // Prepare the API payload - exact format matching GET response
      const payload = {
        project_id: projectId,
        value_map_selections: allValueMapSelections, // Send all personas, not just the edited one
        personas_processed: availablePersonas,
        format: responseData.format || "multi_persona",
        selected_at: new Date().toISOString()
      };

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/vpc-v2/value-map`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload)
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update value map: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success) {
        // Update local state
        fetchValueMapSelections();
        
        toast.success('Item updated successfully!', { id: 'save-success' });
        setEditingId(null);
        setEditingData(null);
      } else {
        throw new Error(result.message || 'Failed to update item');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save changes';
      toast.error(errorMessage);
      console.error('Error saving item:', err);
    } finally {
      setIsSaving(false);
    }
  }, [editingData, selectedPersona, responseData, projectId, token]);

  // Get display name for persona
  const getPersonaDisplayName = useCallback((personaId: string | null) => {
    if (!personaId) return "All Personas";
    if (personaId === "all") return "All Personas";
    
    // Try to get persona_name from the value_map_selections
    if (responseData?.value_map_selections?.[personaId]) {
      const personaData = responseData.value_map_selections[personaId];
      if (personaData.persona_name) {
        return personaData.persona_name;
      }
    }
    
    return `Persona ${personaId}`;
  }, [responseData]);

  // Get priority color
  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
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

  // Get confidence color
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) {
      return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
    } else if (confidence >= 0.8) {
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
    } else if (confidence >= 0.7) {
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
    } else {
      return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
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

  // Get current persona's selection data
  const currentPersonaData = useMemo(() => {
    if (!responseData?.value_map_selections || !selectedPersona) return null;
    return responseData.value_map_selections[selectedPersona] || null;
  }, [responseData, selectedPersona]);

  // Extract value map items
  const getValueMapItems = useCallback(<T extends GainCreator | PainReliever | ProductService>(
    type: 'gain_creators' | 'pain_relievers' | 'products_services'
  ): T[] => {
    if (!currentPersonaData) return [];
    return (currentPersonaData[type] as T[]) || [];
  }, [currentPersonaData]);

  // Calculate totals for summary stats
  const totals = useMemo(() => {
    if (!responseData?.value_map_selections) {
      return { painRelievers: 0, gainCreators: 0, productsServices: 0 };
    }

    let painRelievers = 0;
    let gainCreators = 0;
    let productsServices = 0;

    Object.values(responseData.value_map_selections).forEach((personaData) => {
      painRelievers += personaData.pain_relievers?.length || 0;
      gainCreators += personaData.gain_creators?.length || 0;
      productsServices += personaData.products_services?.length || 0;
    });

    return { painRelievers, gainCreators, productsServices };
  }, [responseData]);

  // Render Gain Creator (for P2-style data)
  const renderGainCreator = (item: GainCreator, index: number) => {
    const isEditing = editingId === item.id;
    
    return (
      <motion.div
        key={`gc-${item.id}-${index}`}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: index * 0.1 }}
        className="group p-4 rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20"
      >
        <div className="flex justify-between items-center mb-2">
          {isEditing ? (
            <Input
              value={editingData?.label || ''}
              onChange={(e) => setEditingData((prev: any) => ({ ...prev, label: e.target.value }))}
              className="font-semibold text-lg flex-1 mr-2"
              placeholder="Label"
            />
          ) : (
            <h4 className="font-semibold text-brand-500 dark:text-white text-lg">
              {item.label}
            </h4>
          )}
          
          <div className="flex items-center gap-2">
            {/* {isEditing ? (
              <Select
                value={editingData?.priority || item.priority}
                onValueChange={(value) => setEditingData(prev => ({ ...prev, priority: value }))}
              >
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            ) : (
              <Badge variant="outline" className={getPriorityColor(item.priority)}>
                {item.priority}
              </Badge>
            )} */}
            
            {isEditing ? (
              <div className="flex gap-1">
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={isSaving}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <span className="inline-flex items-center gap-1">
                      <span>Save</span>
                      
                    </span>}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  <X className="w-3 h-3" />
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleEdit(item, 'gain_creator')}
                className="opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Edit2 className="w-3 h-3" />
              </Button>
            )}
          </div>
        </div>

        {isEditing ? (
          <Textarea
            value={editingData?.text || ''}
            onChange={(e) => setEditingData((prev: any) => ({ ...prev, text: e.target.value }))}
            className="text-sm mb-3"
            placeholder="Description"
            rows={2}
          />
        ) : (
          <p className="text-gray-600 dark:text-gray-300 text-sm mb-3">
            {item.text}
          </p>
        )}

        <div className="bg-green-100/50 dark:bg-green-900/30 p-3 rounded-lg mb-3">
          <p className="text-sm font-medium text-green-700 dark:text-green-300">Value:</p>
          {isEditing ? (
            <Textarea
              value={editingData?.value || ''}
              onChange={(e) => setEditingData((prev: any) => ({ ...prev, value: e.target.value }))}
              className="text-sm mt-1"
              placeholder="Value description"
              rows={2}
            />
          ) : (
            <p className="text-sm text-gray-600 dark:text-gray-400">{item.value}</p>
          )}
        </div>

        {(item.evidence || isEditing) && (
          <div className="bg-white/50 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Evidence:</p>
            {isEditing ? (
              <Textarea
                value={editingData?.evidence || ''}
                onChange={(e) => setEditingData((prev: any) => ({ ...prev, evidence: e.target.value }))}
                className="text-sm mt-1"
                placeholder="Evidence description"
                rows={2}
              />
            ) : (
              <p className="text-sm text-gray-600 dark:text-gray-400">{item.evidence}</p>
            )}
          </div>
        )}
      </motion.div>
    );
  };

  // Render Pain Reliever (for P2-style data)
  const renderPainReliever = (item: PainReliever, index: number) => {
    const isEditing = editingId === item.id;
    
    return (
      <motion.div
        key={`pr-${item.id}-${index}`}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: index * 0.1 }}
        className="group p-4 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20"
      >
        <div className="flex justify-between items-center mb-2">
          {isEditing ? (
            <Input
              value={editingData?.label || ''}
              onChange={(e) => setEditingData((prev: any) => ({ ...prev, label: e.target.value }))}
              className="font-semibold text-lg flex-1 mr-2"
              placeholder="Label"
            />
          ) : (
            <h4 className="font-semibold text-brand-500 dark:text-white text-lg">
              {item.label}
            </h4>
          )}
          
          <div className="flex items-center gap-2">
            {/* {isEditing ? (
              <Select
                value={editingData?.priority || item.priority}
                onValueChange={(value) => setEditingData(prev => ({ ...prev, priority: value }))}
              >
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            ) : (
              <Badge variant="outline" className={getPriorityColor(item.priority)}>
                {item.priority}
              </Badge>
            )} */}
            
            {isEditing ? (
              <div className="flex gap-1">
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={isSaving}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <span className="inline-flex items-center gap-1">
                      <span>Save</span>
                      
                    </span>}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  <X className="w-3 h-3" />
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleEdit(item, 'pain_reliever')}
                className="opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Edit2 className="w-3 h-3" />
              </Button>
            )}
          </div>
        </div>

        {isEditing ? (
          <Textarea
            value={editingData?.text || ''}
            onChange={(e) => setEditingData((prev: any) => ({ ...prev, text: e.target.value }))}
            className="text-sm mb-3"
            placeholder="Description"
            rows={2}
          />
        ) : (
          <p className="text-gray-600 dark:text-gray-300 text-sm mb-3">
            {item.text}
          </p>
        )}

        <div className="bg-red-100/50 dark:bg-red-900/30 p-3 rounded-lg mb-3">
          <p className="text-sm font-medium text-red-700 dark:text-red-300">Impact:</p>
          {isEditing ? (
            <Textarea
              value={editingData?.impact || ''}
              onChange={(e) => setEditingData((prev: any) => ({ ...prev, impact: e.target.value }))}
              className="text-sm mt-1"
              placeholder="Impact description"
              rows={2}
            />
          ) : (
            <p className="text-sm text-gray-600 dark:text-gray-400">{item.impact}</p>
          )}
        </div>

        {(item.evidence || isEditing) && (
          <div className="bg-white/50 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Evidence:</p>
            {isEditing ? (
              <Textarea
                value={editingData?.evidence || ''}
                onChange={(e) => setEditingData((prev: any) => ({ ...prev, evidence: e.target.value }))}
                className="text-sm mt-1"
                placeholder="Evidence description"
                rows={2}
              />
            ) : (
              <p className="text-sm text-gray-600 dark:text-gray-400">{item.evidence}</p>
            )}
          </div>
        )}
      </motion.div>
    );
  };

  // Render Product/Service (for P2-style data)
  const renderProductService = (item: ProductService, index: number) => {
    const isEditing = editingId === item.id;
    
    return (
      <motion.div
        key={`ps-${item.id}-${index}`}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: index * 0.1 }}
        className="group p-4 rounded-lg border border-brand-200 dark:border-brand-800 bg-brand-50 dark:bg-brand-900/20"
      >
        <div className="flex justify-between items-center mb-2">
          {isEditing ? (
            <Input
              value={editingData?.label || ''}
              onChange={(e) => setEditingData((prev: any) => ({ ...prev, label: e.target.value }))}
              className="font-semibold text-lg flex-1 mr-2"
              placeholder="Label"
            />
          ) : (
            <h4 className="font-semibold text-brand-500 dark:text-white text-lg">
              {item.label}
            </h4>
          )}
          
          {/* <div className="flex items-center gap-2">
            {isEditing ? (
              <Select
                value={editingData?.priority || item.priority}
                onValueChange={(value) => setEditingData(prev => ({ ...prev, priority: value }))}
              >
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            ) : (
              <Badge variant="outline" className={getPriorityColor(item.priority)}>
                {item.priority}
              </Badge>
            )}
            
            {isEditing ? (
              <div className="flex gap-1">
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={isSaving}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {isSaving ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <span className="inline-flex items-center gap-1">
                      <span>Save</span>
                      
                    </span>
                  )}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  <X className="w-3 h-3" />
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleEdit(item, 'product_service')}
                className="opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Edit2 className="w-3 h-3" />
              </Button>
            )}
          </div> */}
        </div>

        {isEditing ? (
          <Textarea
            value={editingData?.text || ''}
            onChange={(e) => setEditingData((prev: any) => ({ ...prev, text: e.target.value }))}
            className="text-sm mb-3"
            placeholder="Description"
            rows={2}
          />
        ) : (
          <p className="text-gray-600 dark:text-gray-300 text-sm mb-3">
            {item.text}
          </p>
        )}

        {(item.evidence || isEditing) && (
          <div className="bg-white/50 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Evidence:</p>
            {isEditing ? (
              <Textarea
                value={editingData?.evidence || ''}
                onChange={(e) => setEditingData((prev: any) => ({ ...prev, evidence: e.target.value }))}
                className="text-sm mt-1"
                placeholder="Evidence description"
                rows={2}
              />
            ) : (
              <p className="text-sm text-gray-600 dark:text-gray-400">{item.evidence}</p>
            )}
          </div>
        )}
      </motion.div>
    );
  };

  return (
    <div>
      {/* <FeatureVideoOverlay
        featureId={FEATURE_IDS.VALUE_MAP}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      /> */}
      <PageBreadcrumb pageTitle="Value Map Selections" titleSuffix={<CreditCostBadge cost={10} />} />
      <div className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-white/[0.03] p-2">
        
        {/* Header Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-4">
              <p className="text-sm text-brand-500 flex items-center gap-2 px-4 bg-brand-50 border-brand-200 py-2 border rounded-lg justify-center dark:bg-gray-900/20 dark:text-white dark:border-brand-700">
                <AlertCircle className="w-5 h-5" />
                Review your value map selections for each persona
              </p>
            </div>

            <div className="flex items-center gap-3">
              {responseData && (
                <>
                  <Button 
                    onClick={handleBackToProject} 
                    variant="outline" 
                    disabled={isBackLoading}
                    className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
                  >
                    {isBackLoading ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <ArrowLeft className="w-4 h-4 mr-2" />
                    )}
                    Back to Customer Profile
                  </Button>

                  <Button 
                    onClick={handleReselect} 
                    variant="default" 
                    disabled={isReselectLoading}
                    className="bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600"
                  >
                    {isReselectLoading ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4 mr-2" />
                    )}
                    Reselect Value Map
                  </Button>
                  
                  <Button 
                    onClick={handleContinueToVPC}
                    disabled={isContinueLoading}
                    className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600"
                  >
                    {isContinueLoading ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4 mr-2" />
                    )}
                    Continue to VPC
                  </Button>
                </>
              )}
            </div>
          </div>
        </motion.div>

        {/* Loading State */}
        {loading && !responseData && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center py-12"
          >
            <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-brand-500 dark:text-white">Loading Value Map Selections</h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-sm">
              Retrieving value map selections including pain relievers, gain creators, and products & services...
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
            <h3 className="text-lg font-semibold text-brand-500 dark:text-white mb-2">Loading Failed</h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md">{error}</p>
            <div className="flex gap-2 mt-4">
              <Button onClick={fetchValueMapSelections} variant="outline" className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800">
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

        {/* Main Content */}
        {responseData && (
          <div>
            {/* Persona Selector */}
            <PersonaSelector />

            {/* Summary Stats */}
            {!selectedPersona && (
              <div className="mb-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="p-4 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700">
                  <div className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-red-600 dark:text-red-400" />
                    <div>
                      <p className="text-sm font-medium text-red-600 dark:text-red-400">Pain Relievers</p>
                      <p className="text-lg font-bold text-red-700 dark:text-red-300">{totals.painRelievers}</p>
                    </div>
                  </div>
                </Card>
                <Card className="p-4 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700">
                  <div className="flex items-center gap-2">
                    <Zap className="w-5 h-5 text-green-600 dark:text-green-400" />
                    <div>
                      <p className="text-sm font-medium text-green-600 dark:text-green-400">Gain Creators</p>
                      <p className="text-lg font-bold text-green-700 dark:text-green-300">{totals.gainCreators}</p>
                    </div>
                  </div>
                </Card>
                <Card className="p-4 bg-brand-50 dark:bg-brand-900/20 border-brand-200 dark:border-brand-700">
                  <div className="flex items-center gap-2">
                    <Package className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                    <div>
                      <p className="text-sm font-medium text-brand-600 dark:text-brand-400">Products & Services</p>
                      <p className="text-lg font-bold text-brand-700 dark:text-brand-300">{totals.productsServices}</p>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            <div className="space-y-2">
              {/* Value Map Data */}
              {currentPersonaData && (
                <>
                  {/* Pain Relievers */}
                  {getValueMapItems<PainReliever>('pain_relievers').length > 0 && (
                    <Card>
                      <CardHeader className="flex flex-row items-center space-y-0">
                        <div className="p-2 rounded-lg bg-red-50 dark:bg-red-900/20 mr-3">
                          <Shield className="w-5 h-5 text-red-600 dark:text-red-400" />
                        </div>
                        <CardTitle className="text-red-600 dark:text-red-400">
                          Pain Relievers
                        </CardTitle>
                        <Badge variant="secondary" className="ml-auto">
                          {getValueMapItems<PainReliever>('pain_relievers').length} items
                        </Badge>
                      </CardHeader>
                      <CardContent className="space-y-2 -mt-2">
                        {getValueMapItems<PainReliever>('pain_relievers').map((item, index) => 
                          renderPainReliever(item, index)
                        )}
                      </CardContent>
                    </Card>
                  )}

                  {/* Gain Creators */}
                  {getValueMapItems<GainCreator>('gain_creators').length > 0 && (
                    <Card>
                      <CardHeader className="flex flex-row items-center space-y-0">
                        <div className="p-2 rounded-lg bg-green-50 dark:bg-green-900/20 mr-3">
                          <Zap className="w-5 h-5 text-green-600 dark:text-green-400" />
                        </div>
                        <CardTitle className="text-green-600 dark:text-green-400">
                          Gain Creators
                        </CardTitle>
                        <Badge variant="secondary" className="ml-auto">
                          {getValueMapItems<GainCreator>('gain_creators').length} items
                        </Badge>
                      </CardHeader>
                      <CardContent className="space-y-2 -mt-2">
                        {getValueMapItems<GainCreator>('gain_creators').map((item, index) => 
                          renderGainCreator(item, index)
                        )}
                      </CardContent>
                    </Card>
                  )}

                  {/* Products & Services */}
                  {getValueMapItems<ProductService>('products_services').length > 0 && (
                    <Card>
                      <CardHeader className="flex flex-row items-center space-y-0">
                        <div className="p-2 rounded-lg bg-brand-50 dark:bg-brand-900/20 mr-3">
                          <Package className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                        </div>
                        <CardTitle className="text-brand-600 dark:text-brand-400">
                          Products & Services
                        </CardTitle>
                        <Badge variant="secondary" className="ml-auto">
                          {getValueMapItems<ProductService>('products_services').length} items
                        </Badge>
                      </CardHeader>
                      <CardContent className="space-y-2 -mt-2">
                        {getValueMapItems<ProductService>('products_services').map((item, index) => 
                          renderProductService(item, index)
                        )}
                      </CardContent>
                    </Card>
                  )}
                </>
              )}


              {/* Empty State */}
              {!currentPersonaData && (
                <div className="text-center py-12">
                  <Users className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                  <p className="text-gray-500 dark:text-gray-400 text-sm">
                    No items for {selectedPersona ? getPersonaDisplayName(selectedPersona) : "selected persona"}.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
