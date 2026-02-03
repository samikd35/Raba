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
  Save,
  Edit3,
  X,
  ChevronRight,
  UserCircle2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import toast from "react-hot-toast";
import { motion, AnimatePresence } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

// Local icon component for "Pains" using the provided SVG. Uses currentColor so Tailwind text- classes work.
const PainIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" {...props}>
    <path fillRule="evenodd" d="M13.293 0c.39 0 .707.317.707.707V2h1.293a.707.707 0 0 1 .5 1.207l-1.46 1.46A1.14 1.14 0 0 1 13.53 5h-1.47L8.53 8.53a.75.75 0 0 1-1.06-1.06L11 3.94V2.47c0-.301.12-.59.333-.804l1.46-1.46a.7.7 0 0 1 .5-.207M2.5 8a5.5 5.5 0 0 1 6.598-5.39a.75.75 0 0 0 .298-1.47A7 7 0 1 0 14.86 6.6a.75.75 0 0 0-1.47.299q.109.533.11 1.101a5.5 5.5 0 1 1-11 0m5.364-2.496a.75.75 0 0 0-.08-1.498A4 4 0 1 0 11.988 8.3a.75.75 0 0 0-1.496-.111a2.5 2.5 0 1 1-2.63-2.686" clipRule="evenodd" />
  </svg>
);

interface Evidence {
  quote: string;
  source: string;
}

interface CustomerProfileItem {
  id: string;
  type: "jtbd" | "pain" | "gain";
  label: string;
  description: string;
  evidence: Evidence[];
  confidence: number;
  persona_id: string;
  persona_name: string;
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

export default function CustomerProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const { isAuthenticated, token } = useAuthStore();

  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  const featureConfig = getFeatureVideoConfig(FEATURE_IDS.CUSTOMER_PROFILE);

  // State
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false); // Global saving state to disable buttons
  const [isContinuing, setIsContinuing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existingSelections, setExistingSelections] =
    useState<CustomerProfileSelections>(DEFAULT_SELECTIONS);
  const [editedSelections, setEditedSelections] =
    useState<CustomerProfileSelections>(DEFAULT_SELECTIONS);
  const [stats, setStats] = useState<{
    jtbd: number;
    pains: number;
    gains: number;
  } | null>(null);

  // --- NEW State for Persona Toggle ---
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [availablePersonas, setAvailablePersonas] = useState<string[]>([]);

  // --- NEW State for Per-Item Editing ---
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [currentItemData, setCurrentItemData] =
    useState<CustomerProfileItem | null>(null);

  // Computed values
  const isReady = isAuthenticated && token && projectId;

  const hasSelections = useMemo(() => {
    return (
      editedSelections.gains.length > 0 ||
      editedSelections.pains.length > 0 ||
      editedSelections.jobs_to_be_done.length > 0
    );
  }, [editedSelections]);

  const groupedDataByPersona = useMemo(() => {
    const grouped: { [key: string]: CustomerProfileSelections } = {};

    const allItems = [
      ...editedSelections.gains,
      ...editedSelections.pains,
      ...editedSelections.jobs_to_be_done,
    ];

    if (allItems.length === 0) {
      return grouped;
    }

    for (const item of allItems) {
      const personaId = item.persona_id;

      // Initialize object for this persona if it doesn't exist
      if (!grouped[personaId]) {
        grouped[personaId] = {
          gains: [],
          pains: [],
          jobs_to_be_done: [],
        };
      }

      // Add the item to the correct array based on its type
      if (item.type === "gain") {
        grouped[personaId].gains.push(item);
      } else if (item.type === "pain") {
        grouped[personaId].pains.push(item);
      } else if (item.type === "jtbd") {
        grouped[personaId].jobs_to_be_done.push(item);
      }
    }

    return grouped;
  }, [editedSelections]);

  // Get display name for persona
  const getPersonaDisplayName = (personaId: string | null) => {
    if (!personaId || personaId === "all") return "All Personas";

    // Find the first item matching this persona to extract its name
    const allItems = [
      ...editedSelections.gains,
      ...editedSelections.pains,
      ...editedSelections.jobs_to_be_done,
    ];
    const match = allItems.find(
      (item) => item.persona_id === personaId && (item as any).persona_name
    ) as (CustomerProfileItem & { persona_name?: string }) | undefined;
    if (match?.persona_name) return match.persona_name;

    // Fallbacks if name is not present in items
    if (personaId.includes("_")) {
      const parts = personaId.split("_");
      const lastPart = parts[parts.length - 1];
      if (!isNaN(Number(lastPart))) {
        return `Persona ${lastPart}`;
      }
    }

    return "Persona";
  };

  // Get filtered selections for the selected persona
  const getFilteredSelections = useMemo(() => {
    if (!selectedPersona || selectedPersona === "all") {
      return editedSelections;
    }

    return {
      gains: editedSelections.gains.filter(item => item.persona_id === selectedPersona),
      pains: editedSelections.pains.filter(item => item.persona_id === selectedPersona),
      jobs_to_be_done: editedSelections.jobs_to_be_done.filter(item => item.persona_id === selectedPersona),
    };
  }, [editedSelections, selectedPersona]);

  // Simple HTTP request function using native browser APIs
  const makeRequest = useCallback(
    async (endpoint: string, options: RequestInit = {}): Promise<any> => {
      const url = `${API_BASE_URL}${endpoint}`;
      const method = options.method || "GET";
      const body = options.body;
      const headers = {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
        ...options.headers,
      };

      const controller = new AbortController();
      const id = setTimeout(() => controller.abort(), 30000); // 30s timeout

      try {
        const response = await fetch(url, {
          method,
          headers,
          body,
          signal: controller.signal,
        });
        clearTimeout(id);

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
          // Handle cases where API returns successful empty response
          return responseText ? JSON.parse(responseText) : {};
        } catch (e) {
          // Response was OK but not JSON (e.g., status 204 or plain text success)
          return responseText;
        }
      } catch (error: any) {
        clearTimeout(id);
        if (error.name === "AbortError") {
          throw new Error("Request timeout");
        }
        throw error;
      }
    },
    [token]
  );

  // Helper to normalize items to API shape
  const normalizeItemForApi = (item: CustomerProfileItem & { maps_to?: string | null }) => ({
    id: item.id,
    type: item.type,
    label: item.label,
    // include maps_to for jtbd when present, null otherwise
    ...(item.type === 'jtbd' ? { maps_to: (item as any).maps_to ?? null } : {}),
    evidence: Array.isArray(item.evidence)
      ? item.evidence.map((e) => ({ quote: e.quote, source: e.source }))
      : [],
    confidence: typeof item.confidence === 'number' ? item.confidence : 0,
    persona_id: item.persona_id,
    persona_name: item.persona_name,
    description: item.description || ''
  });

  // Load existing selections
  const loadSelections = useCallback(async () => {
    if (!isReady) return;

    try {
      setLoading(true);
      setError(null);

      const data = await makeRequest(
        `/projects/${projectId}/vpc/step1/customer-profile-selections`
      );

      if (data?.success && data.data) {
        const selections =
          data.data.customer_profile_selections || DEFAULT_SELECTIONS;
        const normalizedSelections: CustomerProfileSelections = {
          gains: selections.gains || [],
          pains: selections.pains || [],
          jobs_to_be_done: selections.jobs_to_be_done || [],
        };

        setExistingSelections(normalizedSelections);
        setEditedSelections(normalizedSelections);
        setStats({
          jtbd: data.data.total_jtbd || 0,
          pains: data.data.total_pains || 0,
          gains: data.data.total_gains || 0,
        });

        // Extract available personas
        const personaIds = new Set<string>();
        ['gains', 'pains', 'jobs_to_be_done'].forEach(section => {
          const sectionData = normalizedSelections[section as keyof CustomerProfileSelections];
          sectionData.forEach((item: CustomerProfileItem) => {
            if (item.persona_id) {
              personaIds.add(item.persona_id);
            }
          });
        });
        
        const personas = Array.from(personaIds).sort();
        setAvailablePersonas(personas);
        
        // Set first persona as default if available
        if (personas.length > 0 && !selectedPersona) {
          setSelectedPersona(personas[0]);
        }

      } else {
        throw new Error(data?.message || "Failed to load selections");
      }
    } catch (err: any) {
      if (err.message.includes("404") || err.message.includes("not found")) {
        setExistingSelections(DEFAULT_SELECTIONS);
        setEditedSelections(DEFAULT_SELECTIONS);
        setStats(null);
        // toast.success("No existing selections found. You can create new ones.");
        router.push(`/team-workspace/generate-customer-profile/${projectId}`);
      } else {
        const errorMessage = err.message || "Failed to load selections";
        setError(errorMessage);
        // toast.error(errorMessage);
        router.push(`/team-workspace/generate-customer-profile/${projectId}`);
      }
    } finally {
      setLoading(false);
    }
  }, [isReady, projectId, makeRequest, router]);

  // Master save function: saves the *entire* selections object
  // This is called by handleSaveItem
  const saveAllSelections = useCallback(
    async (selectionsToSave: CustomerProfileSelections) => {
      if (!projectId) return false;

      setSaving(true);

      try {
        // Use direct format as specified in API docs
        const requestBody = {
          customer_profile_selections: {
            pains: (selectionsToSave.pains || []).map(normalizeItemForApi),
            gains: (selectionsToSave.gains || []).map(normalizeItemForApi),
            jobs_to_be_done: (selectionsToSave.jobs_to_be_done || []).map(normalizeItemForApi)
          }
        };

        const response = await makeRequest(
          `/projects/${projectId}/vpc/step1/customer-profile-selections`,
          {
            method: "PUT",
            body: JSON.stringify(requestBody),
          }
        );

        if (response?.success) {
          toast.success("Item updated successfully!");

          if (response.data?.customer_profile_selections) {
            const selections = response.data.customer_profile_selections;
            const normalizedSelections: CustomerProfileSelections = {
              gains: selections.gains || [],
              pains: selections.pains || [],
              jobs_to_be_done: selections.jobs_to_be_done || [],
            };

            setExistingSelections(normalizedSelections);
            setEditedSelections(normalizedSelections); // Sync both states
            setStats({
              jtbd:
                response.data.total_jtbd ||
                normalizedSelections.jobs_to_be_done.length,
              pains:
                response.data.total_pains || normalizedSelections.pains.length,
              gains:
                response.data.total_gains || normalizedSelections.gains.length,
            });
          }
          setEditingItemId(null); // Exit edit mode
          setCurrentItemData(null);
          return true; // Indicate success
        } else {
          throw new Error(response?.message || "Failed to update selections");
        }
      } catch (err: any) {
        const errorMessage = err.message || "Failed to save selections";
        // toast.error(errorMessage);
        // Cancel edit mode on error
        setEditingItemId(null);
        setCurrentItemData(null);
        return false; // Indicate failure
      } finally {
        setSaving(false);
      }
    },
    [projectId, makeRequest]
  );

  // --- NEW Item-level Edit Handlers ---

  const handleEditClick = (item: CustomerProfileItem) => {
    setEditingItemId(item.id);
    setCurrentItemData({ ...item }); // Store a *copy* to edit
  };

  const handleCancelItemEdit = () => {
    setEditingItemId(null);
    setCurrentItemData(null);
  };

  const handleItemChange = (field: "label" | "description", value: string) => {
    // Only update the temporary item state
    setCurrentItemData(
      (prev) => (prev ? { ...prev, [field]: value } : null)
    );
  };

  const handleSaveItem = async () => {
    if (!currentItemData) return;

    // Create a new version of the full 'editedSelections' state
    const newEditedSelections = { ...editedSelections };
    const itemType =
      currentItemData.type === "jtbd"
        ? "jobs_to_be_done"
        : currentItemData.type === "pain"
        ? "pains"
        : "gains";

    const itemIndex = newEditedSelections[itemType].findIndex(
      (item) => item.id === currentItemData.id
    );

    if (itemIndex > -1) {
      // Create a new array for the specific type
      const updatedItems = [...newEditedSelections[itemType]];
      updatedItems[itemIndex] = currentItemData; // Replace the old item with the edited one

      // Assign the new array back
      newEditedSelections[itemType] = updatedItems;

      // Call the master save function with this new state
      const success = await saveAllSelections(newEditedSelections);

      if (!success) {
        // Reload selections from server on failure to reset state
        await loadSelections();
      }
    }
  };

  // --- Original Handlers ---

  const handleBackToProject = () => {
    router.push(`/team-workspace/personas/${projectId}`);
  };

  const handleNewCustomerProfile = () => {
    router.push(`/team-workspace/generate-customer-profile/${projectId}`);
  };

  // Continue to VPC with a lightweight loading state
  const handleContinueToVPC = useCallback(async () => {
    if (!projectId) return;
    setIsContinuing(true);
    try {
      // Small delay so users can perceive the loading feedback
      await new Promise((r) => setTimeout(r, 300));
      router.push(`/team-workspace/vpc/${projectId}`);
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Continue to VPC navigation error:', err);
      }
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

  // Render items by type
  const renderItemsByType = (
    items: CustomerProfileItem[],
    type: "jtbd" | "pain" | "gain"
  ) => {
    const typeConfig = {
      jtbd: {
        title: "Customer Jobs",
        color: "brand",
        icon: Target,
        key: "jobs_to_be_done" as const,
      },
      pain: {
        title: "Customer Pains",
        color: "red",
        icon: PainIcon,
        key: "pains" as const,
      },
      gain: {
        title: "Customer Gains",
        color: "green",
        icon: TrendingUp,
        key: "gains" as const,
      },
    };

    const config = typeConfig[type];
    const IconComponent = config.icon;

    return (
      <Card key={type}>
        <CardHeader className="flex flex-row items-center space-y-0">
          <div
            className={`p-2 rounded-lg bg-${config.color}-100 dark:bg-${config.color}-900/20 mr-3`}
          >
            <IconComponent
              className={`w-5 h-5 text-${config.color}-600 dark:text-${config.color}-400`}
            />
          </div>
          <CardTitle
            className={`text-${config.color}-600 dark:text-${config.color}-400`}
          >
            {config.title}
          </CardTitle>
          <Badge variant="secondary" className="ml-auto">
            {items.length} items
          </Badge>
        </CardHeader>
        <CardContent className="space-y-2 -mt-2">
          {items.map((item, index) => {
            const isEditing = editingItemId === item.id;

            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className={`p-4 rounded-lg border border-${config.color}-200 dark:border-${config.color}-800 transition-all ${
                  isEditing
                    ? `ring-2 ring-offset-2 ring-offset-white dark:ring-offset-gray-900 ring-brand-500 shadow-md bg-${config.color}-100/50 dark:bg-${config.color}-900/30`
                    : `bg-${config.color}-50 dark:bg-${config.color}-900/10`
                }`}
              >
                <div className="flex justify-between items-center">
                  {/* Label Field */}
                <div>
                  {isEditing ? (
                    <Input
                      value={currentItemData?.label || ""}
                      onChange={(e) => handleItemChange("label", e.target.value)}
                      className="w-full bg-white dark:bg-gray-900"
                    />
                  ) : (
                    <h4 className="font-semibold text-brand-500 dark:text-white text-lg">
                      {item.label}
                    </h4>
                  )}
                </div>


                <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={`text-${config.color}-700 dark:text-${config.color}-300 border-${config.color}-300 dark:border-${config.color}-700`}
                    >
                      {item.persona_id}
                    </Badge>

                    {isEditing ? (
                      <AnimatePresence>
                        <motion.div
                          initial={{ opacity: 0, width: 0 }}
                          animate={{ opacity: 1, width: "auto" }}
                          exit={{ opacity: 0, width: 0 }}
                          className="flex gap-2"
                        >
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleCancelItemEdit}
                            disabled={saving}
                          >
                            <X className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            onClick={handleSaveItem}
                            disabled={saving}
                            className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600"
                          >
                            {saving ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <span className="flex items-center gap-2">
                                <p>Save</p> <Save className="w-4 h-4" />
                              </span>
                            )}
                          </Button>
                        </motion.div>
                      </AnimatePresence>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleEditClick(item)}
                        disabled={saving || editingItemId !== null} // Disable if saving or *any* item is being edited
                        className="text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600"
                      >
                        <Edit3 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>

                </div>

                {/* Description Field */}
                <div className="my-2">
                  <label className="block text-sm font-medium text-brand-600 dark:text-gray-300 mb-2">
                    Description
                  </label>
                  {isEditing ? (
                    <Textarea
                      value={currentItemData?.description || ""}
                      onChange={(e) =>
                        handleItemChange("description", e.target.value)
                      }
                      className="w-full min-h-[80px] bg-white dark:bg-gray-900 text-sm"
                    />
                  ) : (
                    <p className="text-gray-600 dark:text-gray-300 text-sm">
                      {item.description}
                    </p>
                  )}
                </div>

                {/* Evidence (Read-only) */}
                {item.evidence && item.evidence.length > 0 && (
                  <div className="mt-4">
                    <h5 className="text-sm font-medium text-brand-600 dark:text-gray-300 mb-2">
                      Evidence:
                    </h5>
                    <div className="space-y-2">
                      {item.evidence.map((evidence, evidenceIndex) => (
                        <div
                          key={evidenceIndex}
                          className="text-sm text-gray-600 dark:text-gray-400 bg-brand-25 dark:bg-brand-900/10 p-3 rounded-lg border border-brand-200 dark:border-brand-800"
                        >
                          <span className="font-medium text-gray-700 dark:text-gray-300">
                            {evidence.source}:
                          </span>
                          <span className="ml-1">"{evidence.quote}"</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Metadata & Edit Controls */}
                <div className="flex justify-between items-center mt-4 border-gray-200 dark:border-gray-700">
                 

                  
                </div>
              </motion.div>
            );
          })}
        </CardContent>
      </Card>
    );
  };

  // Main render
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
          className="flex flex-col lg:flex-row items-start lg:items-center justify-between rounded-xl mb-2 px-4 py-3 border border-brand-200 dark:border-brand-700 bg-brand-50 dark:bg-brand-900/20"
        >
          <div className="mb-4 lg:mb-0">
            <p className="text-brand-500 dark:text-brand-100 text-sm">
              Manage your customer profile selections. Click the{" "}
              <Edit3 className="w-3 h-3 inline-block -mt-1" /> icon on an item
              to edit.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
            <Button
              onClick={handleBackToProject}
              variant="outline"
              className="text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Personas
            </Button>

            <Button
              onClick={handleNewCustomerProfile}
              className="bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600"
            >
              Rebuild Customer Profile
            </Button>

            <Button
              onClick={handleContinueToVPC}
              disabled={isContinuing}
              className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600"
            >
              {isContinuing ? (
                <>
                              <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
                  Redirecting...
                </>
              ) : (
                <>
                  Continue to VPC
                  <ChevronRight className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>

            {/* Global Edit/Save/Cancel buttons removed for per-item editing */}
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
              Loading Selections...
            </h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md text-md">
              Fetching your existing customer profile selections...
            </p>
          </motion.div>
        )}

        {/* Error State */}
        {/* {error && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center py-12"
          >
            <AlertCircle className="w-12 h-12 text-red-500 dark:text-red-400 mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Error Loading Selections
            </h3>
            <p className="text-gray-600 dark:text-gray-400 text-center max-w-md mb-4">
              {error}
            </p>
            <div className="flex gap-2">
              <Button
                onClick={loadSelections}
                variant="outline"
                className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
                Retry
              </Button>
              <Button
                onClick={handleBackToProject}
                className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Generate Customer Profile
              </Button>
            </div>
          </motion.div>
        )} */}

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
                  onClick={() =>
                    router.push(
                      `/team-workspace/generate-customer-profile/${projectId}`
                    )
                  }
                  className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600"
                >
                  <Target className="w-4 h-4 mr-2" />
                  Create Selections
                </Button>
              </div>
            ) : (
              <>
                {/* Persona Selector */}
                <PersonaSelector />

                {/* Customer Profile Content - Single Persona View */}
                <div className="space-y-2">
           

                  {/* Display order: Pains, Gains, Jobs to be Done */}
                  {getFilteredSelections.pains.length > 0 &&
                    renderItemsByType(getFilteredSelections.pains, "pain")}
                  {getFilteredSelections.jobs_to_be_done.length > 0 &&
                    renderItemsByType(getFilteredSelections.jobs_to_be_done, "jtbd")}
                  {getFilteredSelections.gains.length > 0 &&
                    renderItemsByType(getFilteredSelections.gains, "gain")}

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