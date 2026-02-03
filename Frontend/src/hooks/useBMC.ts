import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { bmcService } from "@/services/bmcService";
import { BMCData } from "@/types/bmc";
import toast from "react-hot-toast";

// Valid block names for BMC
export const BMC_BLOCK_NAMES = [
  'customer_segments',
  'value_propositions', 
  'channels',
  'customer_relationships',
  'revenue_streams',
  'key_resources',
  'key_activities',
  'key_partnerships',
  'cost_structure'
] as const;

export type BMCBlockName = typeof BMC_BLOCK_NAMES[number];

// Item type for editing
export interface BMCEditItem {
  id: string;
  name: string;
  description: string;
  evidence?: string;
  [key: string]: any;
}

export const useBMC = (projectId: string) => {
  const router = useRouter();
  const { isAuthenticated, token } = useAuthStore();
  
  // State management
  const [bmcData, setBmcData] = useState<BMCData | null>(null);
  const [projectName, setProjectName] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isBackLoading, setIsBackLoading] = useState(false);
  const [isContinuing, setIsContinuing] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isAccessError, setIsAccessError] = useState(false);
  
  // Edit mode state
  const [isEditMode, setIsEditMode] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [editingBlock, setEditingBlock] = useState<BMCBlockName | null>(null);
  const [editingItem, setEditingItem] = useState<BMCEditItem | null>(null);
  const [addingToBlock, setAddingToBlock] = useState<BMCBlockName | null>(null);
  // Delete confirmation state
  const [deletingItem, setDeletingItem] = useState<{ blockName: BMCBlockName; itemId: string; itemName: string } | null>(null);

  // AbortController for cleanup
  const abortControllerRef = useRef<AbortController | null>(null);
  const isGeneratingRef = useRef(false);

  // Internal generate function to avoid circular dependency
  const generateBMCInternal = useCallback(async () => {
    if (!isAuthenticated || !token || !projectId || isGeneratingRef.current) return;

    try {
      isGeneratingRef.current = true;
      setIsGenerating(true);
      setError(null);

      await bmcService.generateBMC(projectId, token);
      
      // Refresh data after generation - call fetch directly to avoid circular dependency
      const data = await bmcService.fetchBMCData(
        projectId, 
        token, 
        abortControllerRef.current?.signal
      );
      setBmcData(data.bmc);

    } catch (error: any) {
      // Handle authentication errors
      if (error.message.includes('401') || error.message.includes('Authentication')) {
        toast.error('Authentication failed. Please sign in again.');
        router.push('/signin');
        return;
      }

      // Handle access errors (400, 403 or 500 access issues)
      if (error.message.includes('403') || 
          error.message.includes('400') ||
          error.message.includes('permission') || 
          error.message.includes('does not have access to project') ||
          error.message.includes('BMC generation failed') ||
          error.message.includes('access to project')) {
        setIsAccessError(true);
        const errorMessage = error.message || 'You do not have access to generate Business Model Canvas for this project.';
        setError(errorMessage);
        toast.error(errorMessage, { duration: 6000 });
        
        if (process.env.NODE_ENV === 'development') {
          console.error('🚫 Access error for BMC generation:', error);
        }
        return;
      }

      const errorMessage = error.message || 'Failed to generate BMC';
      setError(errorMessage);
      toast.error(errorMessage);
      
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error generating BMC:', error);
      }
    } finally {
      setIsGenerating(false);
      isGeneratingRef.current = false;
    }
  }, [isAuthenticated, token, projectId, router]);

  // API Functions
  const fetchBMCData = useCallback(async () => {
    if (!isAuthenticated || !token || !projectId) return;

    try {
      // Cancel previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();
      setLoading(true);
      setError(null);

      const data = await bmcService.fetchBMCData(
        projectId, 
        token, 
        abortControllerRef.current.signal
      );
      
      setBmcData(data.bmc);
      if (data.project_name) {
        setProjectName(data.project_name);
      }

    } catch (error: any) {
      if (error.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('🚫 BMC fetch aborted');
        }
        return;
      }

      // Handle authentication errors
      if (error.message.includes('401') || error.message.includes('Authentication')) {
        toast.error('Authentication failed. Please sign in again.');
        router.push('/signin');
        return;
      }

      // Handle access errors (400, 403 or 500 access issues)
      if (error.message.includes('403') || 
          error.message.includes('400') ||
          error.message.includes('permission') || 
          error.message.includes('does not have access to project') ||
          error.message.includes('BMC generation failed') ||
          error.message.includes('access to project')) {
        setIsAccessError(true);
        const errorMessage = error.message || 'You do not have access to this Business Model Canvas.';
        setError(errorMessage);
        toast.error(errorMessage, { duration: 6000 });
        
        if (process.env.NODE_ENV === 'development') {
          console.error('🚫 Access error for BMC:', error);
        }
        return;
      }

      // Handle BMC not found error - auto-generate
      if (error.message.includes('not found') || error.message.includes('404')) {
        if (process.env.NODE_ENV === 'development') {
          console.log('📋 BMC not found, auto-generating...');
        }
        
        // Auto-generate BMC
        await generateBMCInternal();
        return;
      }

      const errorMessage = error.message || 'Failed to load BMC data';
      setError(errorMessage);
      
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error fetching BMC data:', error);
      }
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, token, projectId, router, generateBMCInternal]);

  const generateBMC = useCallback(async () => {
    await generateBMCInternal();
  }, [generateBMCInternal]);

  // Event Handlers
  const handleBackToProject = useCallback(async () => {
    setIsBackLoading(true);
    router.push('/team-workspace/vps-v2/' + projectId);
  }, [router, projectId]);

  const handleRetry = useCallback(() => {
    setError(null);
    fetchBMCData();
  }, [fetchBMCData]);

  const handleContinue = useCallback(async () => {
    setIsContinuing(true);
    try {
      // Add a small delay to show loading state for better UX
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Navigate to Solution Critic as the next step after BMC completion
      router.push(`/team-workspace/solution-critic/${projectId}`);
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error in handleContinue:', error);
      }
    } finally {
      setIsContinuing(false);
    }
  }, [router, projectId]);

  // Toggle fullscreen mode
  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(prev => !prev);
  }, []);

  // Toggle edit mode
  const toggleEditMode = useCallback(() => {
    setIsEditMode(prev => !prev);
    // Reset editing states when exiting edit mode
    if (isEditMode) {
      setEditingBlock(null);
      setEditingItem(null);
      setAddingToBlock(null);
    }
  }, [isEditMode]);

  // Start editing an item
  const startEditItem = useCallback((blockName: BMCBlockName, item: BMCEditItem) => {
    setEditingBlock(blockName);
    setEditingItem(item);
  }, []);

  // Cancel editing
  const cancelEdit = useCallback(() => {
    setEditingBlock(null);
    setEditingItem(null);
  }, []);

  // Save edited item
  const saveEditItem = useCallback(async (blockName: BMCBlockName, updatedItem: BMCEditItem) => {
    if (!isAuthenticated || !token || !projectId || !bmcData) return;

    try {
      setIsEditing(true);

      // Get all items from the block and update the edited one
      const blockItems = getBlockItems(bmcData, blockName);
      const updatedItems = blockItems.map(item => 
        item.id === updatedItem.id ? updatedItem : item
      );

      const response = await bmcService.editBlock(projectId, token, blockName, updatedItems);
      
      if (response.bmc) {
        setBmcData(response.bmc);
      }

      toast.success('Item updated successfully!');
      cancelEdit();

    } catch (error: any) {
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error saving item:', error);
      }
      toast.error(error.message || 'Failed to save item');
    } finally {
      setIsEditing(false);
    }
  }, [isAuthenticated, token, projectId, bmcData, cancelEdit]);

  // Start adding an item
  const startAddItem = useCallback((blockName: BMCBlockName) => {
    setAddingToBlock(blockName);
  }, []);

  // Cancel adding
  const cancelAdd = useCallback(() => {
    setAddingToBlock(null);
  }, []);

  // Add new item (with AI enhancement)
  const addNewItem = useCallback(async (blockName: BMCBlockName, label: string, description: string) => {
    if (!isAuthenticated || !token || !projectId) return;

    try {
      setIsAdding(true);

      const response = await bmcService.addItem(projectId, token, blockName, label, description);
      
      if (response.bmc) {
        setBmcData(response.bmc);
      }

      toast.success('Item added successfully with AI enhancement!');
      cancelAdd();

    } catch (error: any) {
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error adding item:', error);
      }
      toast.error(error.message || 'Failed to add item');
    } finally {
      setIsAdding(false);
    }
  }, [isAuthenticated, token, projectId, cancelAdd]);

  // Start delete confirmation flow
  const startDeleteItem = useCallback((blockName: BMCBlockName, itemId: string, itemName: string) => {
    setDeletingItem({ blockName, itemId, itemName });
  }, []);

  // Cancel delete
  const cancelDelete = useCallback(() => {
    setDeletingItem(null);
  }, []);

  // Confirm and execute delete
  const confirmDeleteItem = useCallback(async () => {
    if (!isAuthenticated || !token || !projectId || !deletingItem) return;

    try {
      setIsDeleting(true);

      const response = await bmcService.deleteItem(projectId, token, deletingItem.blockName, deletingItem.itemId);
      
      if (response.bmc) {
        setBmcData(response.bmc);
      }

      toast.success('Item deleted successfully!');
      setDeletingItem(null);

    } catch (error: any) {
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error deleting item:', error);
      }
      toast.error(error.message || 'Failed to delete item');
    } finally {
      setIsDeleting(false);
    }
  }, [isAuthenticated, token, projectId, deletingItem]);

  // Direct delete an item (without confirmation - kept for backward compatibility)
  const deleteItem = useCallback(async (blockName: BMCBlockName, itemId: string) => {
    if (!isAuthenticated || !token || !projectId) return;

    try {
      setIsDeleting(true);

      const response = await bmcService.deleteItem(projectId, token, blockName, itemId);
      
      if (response.bmc) {
        setBmcData(response.bmc);
      }

      toast.success('Item deleted successfully!');

    } catch (error: any) {
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error deleting item:', error);
      }
      toast.error(error.message || 'Failed to delete item');
    } finally {
      setIsDeleting(false);
    }
  }, [isAuthenticated, token, projectId]);

  // Helper function to get items from a block
  const getBlockItems = (data: BMCData, blockName: BMCBlockName): BMCEditItem[] => {
    switch (blockName) {
      case 'customer_segments':
        return (data.customer_segments?.segments || data.customer_segments?.items || []).map(s => ({
          ...s,
          description: s.description,
          evidence: s.evidence_source
        }));
      case 'value_propositions':
        return (data.value_propositions?.propositions || data.value_propositions?.items || []).map(p => ({
          ...p,
          description: p.value_statement,
          evidence: p.evidence_source
        }));
      case 'channels':
        return (data.channels?.channels || data.channels?.items || []).map(c => ({
          ...c,
          evidence: c.evidence_source
        }));
      case 'customer_relationships':
        return (data.customer_relationships?.relationships || data.customer_relationships?.items || []).map(r => ({
          ...r,
          evidence: r.evidence_source
        }));
      case 'revenue_streams':
        return (data.revenue_streams?.revenue_streams || data.revenue_streams?.items || []).map(r => ({
          ...r,
          description: r.pricing_strategy,
          evidence: r.evidence_source
        }));
      case 'key_resources':
        return (data.key_resources?.resources || data.key_resources?.items || []).map(r => ({
          ...r,
          evidence: r.evidence_source
        }));
      case 'key_activities':
        return (data.key_activities?.activities || data.key_activities?.items || []).map(a => ({
          ...a,
          evidence: a.evidence_source
        }));
      case 'key_partnerships':
        return (data.key_partnerships?.partnerships || data.key_partnerships?.items || []).map(p => ({
          ...p,
          description: p.value_contribution,
          evidence: p.evidence_source
        }));
      case 'cost_structure':
        const costStruct = data.cost_structure?.cost_structure || data.cost_structure?.items;
        return (costStruct?.cost_categories || []).map(c => ({
          ...c,
          evidence: c.evidence_source
        }));
      default:
        return [];
    }
  };

  // Initialize data on mount
  useEffect(() => {
    fetchBMCData();

    // Cleanup on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchBMCData]);

  return {
    // State
    bmcData,
    projectName,
    loading,
    error,
    isGenerating,
    isBackLoading,
    isContinuing,
    isFullscreen,
    isAccessError,
    
    // Edit mode state
    isEditMode,
    isEditing,
    isAdding,
    isDeleting,
    editingBlock,
    editingItem,
    addingToBlock,
    deletingItem,
    
    // Actions
    fetchBMCData,
    generateBMC,
    handleBackToProject,
    handleRetry,
    handleContinue,
    toggleFullscreen,
    
    // Edit mode actions
    toggleEditMode,
    startEditItem,
    cancelEdit,
    saveEditItem,
    startAddItem,
    cancelAdd,
    addNewItem,
    deleteItem,
    // Delete confirmation flow
    startDeleteItem,
    cancelDelete,
    confirmDeleteItem,
    getBlockItems
  };
};
