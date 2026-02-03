"use client";

import PageBreadcrumb from "@/components/common/module 2/PageBreadCrumb";
import CreditCostBadge from "@/components/common/CreditCostBadge";
import FeatureVideoOverlay from "@/components/feature-videos/FeatureVideoOverlay";
import { FEATURE_IDS, getFeatureVideoConfig } from "@/lib/featureVideos";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { 
  Users, 
  ArrowLeft, 
  ChevronRight, 
  Target, 
  TrendingUp,
  FileText,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Edit,
  Save,
  X,
  UserPlus
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, use, useCallback } from "react";
import { authService } from "@/services/authService";
import { useAuthStore } from "@/stores/authStore";
import toast from "react-hot-toast";
import { motion } from "framer-motion";

interface Evidence {
  source: string;
  quote: string;
  relevance_score: number;
}

interface Persona {
  id: string;
  name: string;
  description: string;
  problem_relationship: string;
  evidence: Evidence[];
  is_primary_payer: boolean;
}

interface PersonasResponse {
  success: boolean;
  data: {
    project_id: string;
    personas: Persona[];
    total_personas: number;
    requires_multiple_vpcs: boolean;
  };
  message: string;
}

interface PersonasGenerateResponse {
  success: boolean;
  data: {
    project_id: string;
    personas: Persona[];
    total_personas: number;
    analysis_summary: string;
    requires_multiple_vpcs: boolean;
    personas_saved: boolean;
  };
  message: string;
  next_step: string;
}

interface EditPersonaFormData {
  name: string;
  description: string;
  problem_relationship: string;
  is_primary_payer: boolean;
}

interface AddPersonaFormData {
  name: string;
  description: string;
  problem_relationship: string;
  is_primary_payer: boolean;
}

interface AddPersonaResponse {
  success: boolean;
  data: {
    persona: Persona;
    project_id: string;
  };
  message: string;
  total_personas: number;
  requires_multiple_vpcs: boolean;
}

export default function PersonasPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
    const { isAuthenticated, token } = useAuthStore();
    const featureConfig = getFeatureVideoConfig(FEATURE_IDS.PERSONAS);
    const [personas, setPersonas] = useState<Persona[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [analysisSummary, setAnalysisSummary] = useState("");
    const [projectId, setProjectId] = useState<string>("");
    
    // Edit persona state
    const [editingPersona, setEditingPersona] = useState<Persona | null>(null);
    const [editFormData, setEditFormData] = useState<EditPersonaFormData>({
      name: "",
      description: "",
      problem_relationship: "",
      is_primary_payer: false
    });
    const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    // Add persona state
    const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
    const [addFormData, setAddFormData] = useState<AddPersonaFormData>({
      name: "",
      description: "",
      problem_relationship: "",
      is_primary_payer: false
    });
    const [isAdding, setIsAdding] = useState(false);
    const [isContinuing, setIsContinuing] = useState(false);
  
    // Properly unwrap params using React.use()
    const resolvedParams = use(params);
    useEffect(() => {
      setProjectId(resolvedParams.id);
    }, [resolvedParams]);

    // Memoized input sanitization function
    const sanitizeInput = useCallback((input: string, maxLength: number = 500): string => {
      if (typeof input !== 'string') return '';
      return input
        .replace(/<[^>]*>/g, '') // Remove HTML tags
        .slice(0, maxLength);
        // Removed .trim() to allow spaces within text
    }, []);

    // Memoized form validation
    const validateEditForm = useCallback((formData: EditPersonaFormData): string | null => {
      if (!formData.name) return "Name is required";
      if (!formData.description) return "Description is required";
      
      // Count words in description (minimum 30 words)
      const descriptionWords = formData.description.trim().split(/\s+/).filter(word => word.length > 0);
      if (descriptionWords.length < 30) {
        return `Description must be at least 30 words (currently ${descriptionWords.length} words)`;
      }
      
      if (formData.description.length > 1000) return "Description must be less than 1000 characters";
      if (!formData.problem_relationship) return "Problem relationship is required";
      if (formData.problem_relationship.length > 1000) return "Problem relationship must be less than 1000 characters";
      return null;
    }, []);

    // Validate add persona form
    const validateAddForm = useCallback((formData: AddPersonaFormData): string | null => {
      if (!formData.name || formData.name.trim().length < 1) return "Name must be at least 1 character";
      if (formData.name.length > 100) return "Name must be less than 100 characters";
      if (!formData.description || formData.description.trim().length < 30) return "Description must be at least 30 characters";
      if (formData.description.length > 1000) return "Description must be less than 1000 characters";
      if (formData.problem_relationship && formData.problem_relationship.length > 1000) {
        return "Problem relationship must be less than 1000 characters";
      }
      return null;
    }, []);

    // Handle edit persona click
    const handleEditPersona = useCallback((persona: Persona) => {
      setEditingPersona(persona);
      setEditFormData({
        name: persona.name,
        description: persona.description,
        problem_relationship: persona.problem_relationship,
        is_primary_payer: persona.is_primary_payer
      });
      setIsEditDialogOpen(true);
    }, []);

    // Handle form input changes
    const handleEditFormChange = useCallback((field: keyof EditPersonaFormData, value: string | boolean) => {
      setEditFormData(prev => {
        if (typeof value === 'string') {
          const maxLengths = {
            name: 100,
            description: 1000,
            problem_relationship: 1000
          };
          const sanitized = sanitizeInput(value, maxLengths[field as keyof typeof maxLengths]);
          return { ...prev, [field]: sanitized };
        }
        return { ...prev, [field]: value };
      });
    }, [sanitizeInput]);

    // Handle form input changes for add persona
    const handleAddFormChange = useCallback((field: keyof AddPersonaFormData, value: string | boolean) => {
      setAddFormData(prev => {
        if (typeof value === 'string') {
          const maxLengths = {
            name: 100,
            description: 1000,
            problem_relationship: 1000
          };
          const sanitized = sanitizeInput(value, maxLengths[field as keyof typeof maxLengths]);
          return { ...prev, [field]: sanitized };
        }
        return { ...prev, [field]: value };
      });
    }, [sanitizeInput]);

    // Save edited persona
    const handleSavePersona = useCallback(async () => {
      if (!editingPersona || !token) return;

      const validationError = validateEditForm(editFormData);
      if (validationError) {
        toast.error(validationError);
        return;
      }

      setIsSaving(true);
      
      try {
        if (process.env.NODE_ENV === 'development') {
          console.log('=== SAVE PERSONA DEBUG ===');
          console.log('Editing persona:', editingPersona.id);
          console.log('Form data:', editFormData);
        }

        // Create updated personas array
        const updatedPersonas = personas.map(persona => 
          persona.id === editingPersona.id 
            ? {
                ...persona,
                name: editFormData.name,
                description: editFormData.description,
                problem_relationship: editFormData.problem_relationship,
                is_primary_payer: editFormData.is_primary_payer
              }
            : persona
        );

        // Prepare API request body
        const requestBody = {
          personas: updatedPersonas
        };

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/personas`,
          {
            method: 'PUT',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
          }
        );

        if (process.env.NODE_ENV === 'development') {
          console.log('Save response status:', response.status);
        }

        if (!response.ok) {
          if (response.status === 401) {
            toast.error("Session expired. Please sign in again.");
            router.push("/signin");
            return;
          }
          if (response.status === 422) {
            const errorData = await response.json();
            const errorMessage = errorData.detail?.[0]?.msg || 'Validation error occurred';
            throw new Error(errorMessage);
          }
          throw new Error(`Failed to save persona: ${response.status}`);
        }

        const responseData = await response.json();
        
        if (process.env.NODE_ENV === 'development') {
          console.log('Save response data:', responseData);
        }

        if (responseData.success) {
          // Update local state
          setPersonas(updatedPersonas);
          setIsEditDialogOpen(false);
          setEditingPersona(null);
          toast.success("Persona updated successfully!");
        } else {
          throw new Error(responseData.message || 'Failed to save persona');
        }

      } catch (err) {
        if (process.env.NODE_ENV === 'development') {
          console.error('Error saving persona:', err);
        }
        const errorMessage = err instanceof Error ? err.message : "Failed to save persona";
        toast.error(errorMessage);
      } finally {
        setIsSaving(false);
      }
    }, [editingPersona, token, editFormData, validateEditForm, personas, projectId, router]);

    // Fetch personas (moved above usages to avoid TDZ)
    const fetchPersonas = useCallback(async () => {
      try {
        setLoading(true);
        setError(null);

        if (process.env.NODE_ENV === 'development') {
          console.log('=== FETCH PERSONAS DEBUG ===');
          console.log('Project ID:', projectId);
          console.log('Token available:', !!token);
        }

        // First, try to get existing personas
        if (process.env.NODE_ENV === 'development') {
          console.log('Checking for existing personas...');
        }
        const checkResponse = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/personas`,
          {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          }
        );

        if (process.env.NODE_ENV === 'development') {
          console.log('Check response status:', checkResponse.status);
        }

        if (checkResponse.ok) {
          // Personas already exist, use them
          const existingData: PersonasResponse = await checkResponse.json();
          if (process.env.NODE_ENV === 'development') {
            console.log('Found existing personas:', existingData);
          }

          if (existingData.success && existingData.data) {
            setPersonas(existingData.data.personas);
            setAnalysisSummary(''); // No analysis summary in existing data
            toast.success(`Loaded ${existingData.data.total_personas} existing personas`);
            return;
          }
        } else if (checkResponse.status === 404) {
          // Personas don't exist yet, generate them
          if (process.env.NODE_ENV === 'development') {
            console.log('No existing personas found, generating new ones...');
          }
          
          const generateResponse = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/identify-personas`,
            {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({}), // Empty body for POST request
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
            throw new Error(`Failed to generate personas: ${generateResponse.status}`);
          }

          const generateData: PersonasGenerateResponse = await generateResponse.json();
          if (process.env.NODE_ENV === 'development') {
            console.log('Generated personas response:', generateData);
          }

          if (generateData.success && generateData.data) {
            setPersonas(generateData.data.personas);
            setAnalysisSummary(generateData.data.analysis_summary || '');
            toast.success(`Successfully generated ${generateData.data.total_personas} personas`);
          } else {
            throw new Error(generateData.message || 'Failed to generate personas');
          }
        } else {
          // Other error occurred
          if (checkResponse.status === 401) {
            toast.error("Session expired. Please sign in again.");
            router.push("/signin");
            return;
          }
          throw new Error(`Failed to check personas: ${checkResponse.status}`);
        }
      } catch (err) {
        if (process.env.NODE_ENV === 'development') {
          console.error('Error fetching personas:', err);
        }
        const errorMessage = err instanceof Error ? err.message : "An error occurred while loading personas";
        setError(errorMessage);
        toast.error(errorMessage);
      } finally {
        setLoading(false);
      }
    }, [token, projectId, router, isAuthenticated]);

    // Handle add persona
    const handleAddPersona = useCallback(async () => {
      if (!token || !projectId) return;

      const validationError = validateAddForm(addFormData);
      if (validationError) {
        toast.error(validationError);
        return;
      }

      setIsAdding(true);
      
      try {
        if (process.env.NODE_ENV === 'development') {
          console.log('=== ADD PERSONA DEBUG ===');
          console.log('Project ID:', projectId);
          console.log('Form data:', addFormData);
        }

        // Prepare API request body
        const requestBody = {
          name: addFormData.name.trim(),
          description: addFormData.description.trim(),
          problem_relationship: addFormData.problem_relationship?.trim() || "Not specified - to be determined during customer profile analysis",
          is_primary_payer: addFormData.is_primary_payer
        };

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}/personas/add`,
          {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
          }
        );

        if (process.env.NODE_ENV === 'development') {
          console.log('Add persona response status:', response.status);
        }

        if (!response.ok) {
          if (response.status === 401) {
            toast.error("Session expired. Please sign in again.");
            router.push("/signin");
            return;
          }
          if (response.status === 422) {
            const errorData = await response.json();
            const errorMessage = errorData.detail?.[0]?.msg || 'Validation error occurred';
            throw new Error(errorMessage);
          }
          if (response.status === 400) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Maximum 2 personas allowed per project');
          }
          throw new Error(`Failed to add persona: ${response.status}`);
        }

        const responseData: AddPersonaResponse = await response.json();
        
        if (process.env.NODE_ENV === 'development') {
          console.log('Add persona response data:', responseData);
        }

        if (responseData.success && responseData.data) {
          // Always reload from source of truth using existing fetchPersonas()
          await fetchPersonas();
          
          setIsAddDialogOpen(false);
          
          // Reset form
          setAddFormData({
            name: "",
            description: "",
            problem_relationship: "",
            is_primary_payer: false
          });
          
          toast.success(responseData.message || "Persona added successfully!");
          
          // Show info about multi-persona VPC if applicable
          if (responseData.requires_multiple_vpcs) {
            toast.success("Multi-persona VPC workflow will be used for this project");
          }
        } else {
          throw new Error(responseData.message || 'Failed to add persona');
        }

      } catch (err) {
        if (process.env.NODE_ENV === 'development') {
          console.error('Error adding persona:', err);
        }
        const errorMessage = err instanceof Error ? err.message : "Failed to add persona";
        toast.error(errorMessage);
      } finally {
        setIsAdding(false);
      }
    }, [token, projectId, addFormData, validateAddForm, router, fetchPersonas]);

    // Close edit dialog
    const handleCloseEditDialog = useCallback(() => {
      setIsEditDialogOpen(false);
      setEditingPersona(null);
      setEditFormData({
        name: "",
        description: "",
        problem_relationship: "",
        is_primary_payer: false
      });
    }, []);

    // Close add dialog
    const handleCloseAddDialog = useCallback(() => {
      setIsAddDialogOpen(false);
      setAddFormData({
        name: "",
        description: "",
        problem_relationship: "",
        is_primary_payer: false
      });
    }, []);

    // Handle continue to Customer Profile with lightweight loading state
    const handleContinueToCustomerProfile = useCallback(async () => {
      if (!projectId) return;
      setIsContinuing(true);
      try {
        // Small delay so users can perceive the loading feedback
        await new Promise((r) => setTimeout(r, 300));
        router.push(`/team-workspace/customer-profile/${projectId}`);
      } catch (err) {
        if (process.env.NODE_ENV === 'development') {
          console.error('Continue navigation error:', err);
        }
      } finally {
        setIsContinuing(false);
      }
    }, [router, projectId]);

    useEffect(() => {
      if (!isAuthenticated || !token || !projectId) {
        if (!isAuthenticated) {
          toast.error("Please sign in to view personas");
          router.push("/signin");
        }
        return;
      }
  


      fetchPersonas();
    }, [isAuthenticated, token, projectId, router, fetchPersonas]);
  
    const getRelevanceColor = (score: number) => {
      if (score >= 0.8) return "bg-green-500";
      if (score >= 0.6) return "bg-yellow-500";
      return "bg-red-500";
    };
  
    const getRelevanceLabel = (score: number) => {
      if (score >= 0.8) return "High";
      if (score >= 0.6) return "Medium";
      return "Low";
    };
  

  
    const handleBackToProject = () => {
      router.push(`/team-workspace/projects/${projectId}`);
    };
  
    if (loading) {
      return (
        <div className="flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-brand-600 dark:text-brand-400" />
            <p className="text-muted-foreground dark:text-gray-400">Loading personas...</p>
          </div>
        </div>
      );
    }
  
    if (error) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center max-w-md">
            <AlertCircle className="w-12 h-12 text-red-500 dark:text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Error Loading Personas</h2>
            <p className="text-muted-foreground dark:text-gray-400 mb-4">{error}</p>
            <div className="flex gap-2 justify-center">
              <Button onClick={() => window.location.reload()} variant="outline" className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800">
                Try Again
              </Button>
              <Button onClick={handleBackToProject} className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Project
              </Button>
            </div>
          </div>
        </div>
      );
    }
  
  return (
    <div>
      <FeatureVideoOverlay
        featureId={FEATURE_IDS.PERSONAS}
        youtubeId={featureConfig.youtubeId}
        resourcesHref={featureConfig.resourcesHref}
        title={featureConfig.title}
      />
      <PageBreadcrumb pageTitle="Construct Your Persona" titleSuffix={<CreditCostBadge cost={5} />} />
     
      {/* Add Persona Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-brand-700 dark:text-brand-300">
              <UserPlus className="w-5 h-5" />
              Add New Persona
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-2">
            {/* Name Field */}
            <div className="space-y-2">
              <Label htmlFor="add-name" className="text-sm font-medium text-brand-600 dark:text-brand-400">
                Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="add-name"
                value={addFormData.name}
                onChange={(e) => handleAddFormChange('name', e.target.value)}
                placeholder="Enter persona name (e.g., Small Business Owner)"
                className="border-brand-200 dark:border-brand-700 focus:border-brand-500 dark:focus:border-brand-400 focus:ring-brand-500 dark:focus:ring-brand-400"
              />
            </div>

            {/* Description Field */}
            <div className="space-y-2">
              <Label htmlFor="add-description" className="text-sm font-medium text-brand-600 dark:text-brand-400">
                Description <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="add-description"
                value={addFormData.description}
                onChange={(e) => handleAddFormChange('description', e.target.value)}
                placeholder="Describe this persona in detail - their role, responsibilities, challenges, and goals"
                rows={5}
                maxLength={1000}
                className="border-brand-200 dark:border-brand-700 focus:border-brand-500 dark:focus:border-brand-400 focus:ring-brand-500 dark:focus:ring-brand-400 resize-none"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {addFormData.description.length}/1000 characters (minimum 30 words - currently {addFormData.description.trim().split(/\s+/).filter((w: string) => w.length > 0).length} words)
              </p>
            </div>

            {/* Problem Relationship Field */}
            <div className="space-y-2">
              <Label htmlFor="add-problem-relationship" className="text-sm font-medium text-brand-600 dark:text-brand-400">
                Problem Relationship <span className="text-gray-500">(Optional)</span>
              </Label>
              <Textarea
                id="add-problem-relationship"
                value={addFormData.problem_relationship}
                onChange={(e) => handleAddFormChange('problem_relationship', e.target.value)}
                placeholder="Describe how this persona relates to the problem you're solving (AI will enhance this with evidence)"
                rows={3}
                maxLength={1000}
                className="border-brand-200 dark:border-brand-700 focus:border-brand-500 dark:focus:border-brand-400 focus:ring-brand-500 dark:focus:ring-brand-400 resize-none"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {addFormData.problem_relationship.length}/1000 characters
              </p>
            </div>

            {/* Primary Payer Toggle */}
            <div className="flex items-center justify-between p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700">
              <div className="space-y-1">
                <Label htmlFor="add-primary-payer" className="text-sm font-medium text-brand-700 dark:text-brand-300">
                  Primary Payer
                </Label>
                <p className="text-xs text-brand-600 dark:text-brand-400">
                  Is this persona the primary decision maker or payer?
                </p>
              </div>
              <Switch
                id="add-primary-payer"
                checked={addFormData.is_primary_payer}
                onCheckedChange={(checked) => handleAddFormChange('is_primary_payer', checked)}
              />
            </div>

            {/* Info Box */}
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                <strong>Note:</strong> The AI will automatically enrich your persona with evidence from your problem validation report and actionable insights. Maximum 2 personas per project.
              </p>
            </div>
          </div>

          {/* Dialog Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              variant="outline"
              onClick={handleCloseAddDialog}
              disabled={isAdding}
              className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <X className="w-4 h-4 mr-2" />
              Cancel
            </Button>
            <Button
              onClick={handleAddPersona}
              disabled={isAdding || !addFormData.name || !addFormData.description || addFormData.description.trim().split(/\s+/).filter((w: string) => w.length > 0).length < 30}
              className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600"
            >
              {isAdding ? (
                <>
                              <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
                  Adding Persona...
                </>
              ) : (
                <>
                  <UserPlus className="w-4 h-4 mr-2" />
                  Add Persona
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit Persona Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-brand-700 dark:text-brand-300">
              <Edit className="w-5 h-5" />
              Edit Persona
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Name Field */}
            <div className="space-y-2">
              <Label htmlFor="edit-name" className="text-sm font-medium text-brand-600 dark:text-brand-400">
                Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="edit-name"
                value={editFormData.name}
                onChange={(e) => handleEditFormChange('name', e.target.value)}
                placeholder="Enter persona name"
                className="border-brand-200 dark:border-brand-700 focus:border-brand-500 dark:focus:border-brand-400 focus:ring-brand-500 dark:focus:ring-brand-400"
              />
            </div>

            {/* Description Field */}
            <div className="space-y-2">
              <Label htmlFor="edit-description" className="text-sm font-medium text-brand-600 dark:text-brand-400">
                Description <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="edit-description"
                value={editFormData.description}
                onChange={(e) => handleEditFormChange('description', e.target.value)}
                placeholder="Describe this persona in detail"
                rows={4}
                maxLength={1000}
                className="border-brand-200 dark:border-brand-700 focus:border-brand-500 dark:focus:border-brand-400 focus:ring-brand-500 dark:focus:ring-brand-400 resize-none"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {editFormData.description.length}/1000 characters (minimum 30 words - currently {editFormData.description.trim().split(/\s+/).filter((w: string) => w.length > 0).length} words)
              </p>
            </div>

            {/* Problem Relationship Field */}
            <div className="space-y-2">
              <Label htmlFor="edit-problem-relationship" className="text-sm font-medium text-brand-600 dark:text-brand-400">
                Problem Relationship <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="edit-problem-relationship"
                value={editFormData.problem_relationship}
                onChange={(e) => handleEditFormChange('problem_relationship', e.target.value)}
                placeholder="Describe how this persona relates to the problem"
                rows={3}
                maxLength={1000}
                className="border-brand-200 dark:border-brand-700 focus:border-brand-500 dark:focus:border-brand-400 focus:ring-brand-500 dark:focus:ring-brand-400 resize-none"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {editFormData.problem_relationship.length}/1000 characters
              </p>
            </div>

            {/* Primary Payer Toggle */}
            <div className="flex items-center justify-between p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700">
              <div className="space-y-1">
                <Label htmlFor="edit-primary-payer" className="text-sm font-medium text-brand-700 dark:text-brand-300">
                  Primary Payer
                </Label>
                <p className="text-xs text-brand-600 dark:text-brand-400">
                  Is this persona the primary decision maker or payer?
                </p>
              </div>
              <Switch
                id="edit-primary-payer"
                checked={editFormData.is_primary_payer}
                onCheckedChange={(checked) => handleEditFormChange('is_primary_payer', checked)}
              />
            </div>
          </div>

          {/* Dialog Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              variant="outline"
              onClick={handleCloseEditDialog}
              disabled={isSaving}
              className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <X className="w-4 h-4 mr-2" />
              Cancel
            </Button>
            <Button
              onClick={handleSavePersona}
              disabled={isSaving || !editFormData.name || !editFormData.description || !editFormData.problem_relationship}
              className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600"
            >
              {isSaving ? (
                <>
                              <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <div className="min-h-screen rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-white/[0.03] px-4 py-2">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex items-center justify-between mb-4 border-b border-gray-200 dark:border-gray-800 pb-2"
      >
        <div>
         
          <p className="text-brand-500 dark:text-brand-400">
            {personas.length} persona{personas.length !== 1 ? 's' : ''} identified for your project
          </p>
        </div>
        <div className="flex gap-3">
          <Button onClick={handleBackToProject} variant="outline" className="text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Project
          </Button>
          {/* Show Add Persona button only when there's exactly 1 persona */}
          {personas.length === 1 && (
            <Button 
              onClick={() => setIsAddDialogOpen(true)} 
              variant="outline"
              className="bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 border-brand-300 dark:border-brand-600 hover:bg-brand-100 dark:hover:bg-brand-800"
            >
              <UserPlus className="w-4 h-4 mr-2" />
              Add Another Persona
            </Button>
          )}
          {personas.length > 0 && (
           <Button
              onClick={handleContinueToCustomerProfile}
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
                  Continue to Customer Profile
                  <ChevronRight className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>
          )}
        </div>
      </motion.div>

     

      {/* Personas Grid */}
      {personas.length > 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-2 gap-4"
        >
          {personas.map((persona, index) => (
            <motion.div
              key={persona.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: 0.1 * index }}
            >
              <Card className="h-full overflow-hidden hover:shadow-lg transition-all duration-300 border-2 hover:border-brand-200 dark:hover:border-brand-700 bg-white dark:bg-gray-800">
                <CardHeader className="bg-gradient-to-r from-brand-50 to-brand-50 dark:from-brand-900/30 dark:to-brand-900/30 py-4">
                  <div className="flex items-start gap-3">
                    <Avatar className="h-12 w-12 border-1 border-brand-300 dark:border-gray-600 bg-brand-100 dark:bg-gray-700 shadow-sm flex items-center justify-center" >
                    <svg xmlns="http://www.w3.org/2000/svg" width="1.5em" height="1.5em" viewBox="0 0 24 24"><g fill="none" stroke="#244694" strokeWidth="2"><circle cx="12" cy="7" r="5"/><path strokeLinecap="round" strokeLinejoin="round" d="M17 14h.352a3 3 0 0 1 2.976 2.628l.391 3.124A2 2 0 0 1 18.734 22H5.266a2 2 0 0 1-1.985-2.248l.39-3.124A3 3 0 0 1 6.649 14H7"/></g></svg>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-lg text-gray-700 dark:text-white line-clamp-2 flex-1 mr-2">
                          Persona {index + 1} - <span className="text-brand-500 dark:text-brand-400">{persona.name}</span>
                        </CardTitle>
                        <Button
                          variant="ghost"
                          // size="sm"
                          onClick={() => handleEditPersona(persona)}
                          className="p-4 hover:bg-brand-100 dark:hover:bg-brand-800 text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300"
                          title="Edit persona"
                        >
                          <Edit className="w-8 h-8" />
                          <span className=" text-md">Edit</span>
                        </Button>
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        <Badge
                          variant={persona.is_primary_payer ? "default" : "secondary"}
                          className="text-xs"
                        >
                          {persona.is_primary_payer ? "Primary Payer" : "Secondary"}
                        </Badge>
                       
                      </div>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  {/* Description */}
                  <div>
                    <h4 className="text-sm font-medium text-brand-500 dark:text-brand-400 mb-2 flex items-center gap-1">
                      <Target className="w-3 h-3" />
                      Description
                    </h4>
                    <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3">
                      {persona.description}
                    </p>
                  </div>

                  {/* Problem Relationship */}
                  <div>
                    <h4 className="text-sm font-medium text-brand-500 dark:text-brand-400 mb-2 flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" />
                      Problem Relationship
                    </h4>
                    <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                      {persona.problem_relationship}
                    </p>
                  </div>

                  {/* Evidence Summary */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      Evidence ({persona.evidence.length})
                    </h4>
                    <div className="flex flex-wrap gap-1">
                      {persona.evidence.slice(0, 3).map((evidence, idx) => (
                        <span
                          key={idx}
                          className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${getRelevanceColor(
                            evidence.relevance_score
                          )} text-white`}
                        >
                          {getRelevanceLabel(evidence.relevance_score)}
                          <span className="text-xs">
                            {Math.round(evidence.relevance_score * 100)}%
                          </span>
                        </span>
                      ))}
                      {persona.evidence.length > 3 && (
                        <span className="text-xs text-gray-500 dark:text-gray-400 px-2 py-1">
                          +{persona.evidence.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>

           
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="text-center py-12"
        >
          <Users className="w-16 h-16 text-gray-400 dark:text-gray-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">No Personas Found</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            No personas have been identified for this project yet.
          </p>
          <Button onClick={handleBackToProject} variant="outline" className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Project
          </Button>
        </motion.div>
      )}

      {/* Next Steps */}
      {personas.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.4 }}
          className="mt-4"
        >
          <Card className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-200 dark:border-green-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-green-900 dark:text-green-100">
                <CheckCircle2 className="w-5 h-5" />
                Next Steps
              </CardTitle>
            </CardHeader>
            <CardContent className="-mt-4">
              <p className="text-green-800 dark:text-green-200 mb-4">
                Great! You've successfully identified {personas.length} persona{personas.length !== 1 ? 's' : ''} for your project. 
                The next step is to create Value Proposition Canvases for each persona.
              </p>
              <Button
                onClick={handleContinueToCustomerProfile}
                disabled={isContinuing}
                className="bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600"
              >
                {isContinuing ? (
                  <>
                                <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
                    Redirecting...
                  </>
                ) : (
                  <>
                    <TrendingUp className="w-4 h-4 mr-2" />
                    Continue to Customer Profile
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
    </div>
  );
}
