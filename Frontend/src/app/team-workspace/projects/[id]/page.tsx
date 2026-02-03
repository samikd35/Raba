'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, 
  Clock, 
  FileText, 
  Loader2, 
  AlertCircle,
  Play,
  CheckCircle,
  Lightbulb,
  ChevronRight,
  Target,
  MessageSquare,
  Users,
  HelpCircle,
  Trash,
  CircleAlertIcon,
  Edit2,
  X,
  Save,
  UserCircle2,
  Frown,
  TrendingUp
} from 'lucide-react';
import PageBreadcrumb from "@/components/common/module 2/PageBreadCrumb";
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { authService } from '@/services/authService';
import { toast } from "react-hot-toast";

// Types based on the actual API response
interface Evidence {
  quote: string;
  source: string;
}

interface CustomerProfileItem {
  id: string;
  type: 'gain' | 'pain' | 'jtbd';
  label: string;
  maps_to: any;
  evidence: Evidence[];
  confidence: number;
  persona_id: string;
  description: string;
}

interface CustomerProfile {
  gains: CustomerProfileItem[];
  pains: CustomerProfileItem[];
  jobs_to_be_done: CustomerProfileItem[];
}

interface VPCPersona {
  status: string;
  value_map: any;
  created_at: string;
  persona_id: string;
  canvas_data: any;
  persona_name: string;
  customer_profile: CustomerProfile | null;
}

interface VPCData {
  vpcs: {
    [key: string]: VPCPersona;
  };
  vpc_status: string;
  primary_persona_id: string;
}

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
  generated_at: string;
  persona_name: string;
}

function isStructuredHypothesisText(text: HypothesisText | string): text is HypothesisText {
  return typeof text === 'object' && text !== null && 'we_believe_that' in text;
}

interface Assumption {
  id: string;
  text: string;
  evidence: string[];
  generated_at: string;
  persona_name: string;
  persona_id?: string;
  hypothesis_id: string;
  component_type?: 'jtbd' | 'pain' | 'gain';
}

interface Questionnaire {
  id: string;
  text: string;
  type: 'behavioral' | 'attitudinal' | 'contextual';
  generated_at: string;
  persona_name: string;
  assumption_id: string;
  hypothesis_id: string;
  component_type?: 'jtbd' | 'pain' | 'gain';
}

interface FieldPrepData {
  stage: string;
  hypotheses: Hypothesis[];
  assumptions: Assumption[];
  questionnaires: Questionnaire[];
  hypotheses_generated_at?: string;
  assumptions_generated_at?: string;
  questionnaires_generated_at?: string;
}

interface Project {
  id: string;
  tenant_id: string;
  user_id: string;
  name: string;
  description: string;
  pv_report_id: string;
  status: string;
  current_step: string;
  vpc_data: VPCData;
  field_prep_data: FieldPrepData;
  settings: any;
  created_at: string;
  updated_at: string;
  documents: {
    title: string;
  };
}

interface ProjectResponse {
  success: boolean;
  data: Project | null;
  message: string;
}

// Problem Statement Response Interface
interface ProblemStatementData {
  project_id: string;
  problem_statement: string;
  source: string;
  extraction_method: string;
}

interface ProblemStatementResponse {
  success: boolean;
  data: ProblemStatementData;
  message: string;
}

// Helper to strip inline numeric citation markers like [1], [23] from text
const stripInlineCitations = (text: string | undefined | null): string => {
  if (!text) return '';
  return text.replace(/\s*\[\d+\]/g, '');
};

// API function to fetch single project
async function fetchProject(projectId: string): Promise<ProjectResponse> {
  const token = authService.getCurrentToken();

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects/${projectId}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 404) {
      return {
        success: false,
        data: null,
        message: 'Project not found.'
      };
    }
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// API function to fetch problem statement
async function fetchProblemStatement(projectId: string): Promise<ProblemStatementResponse | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const token = authService.getCurrentToken();

  try {
    const response = await fetch(`${apiUrl}/api/v2/vmp/projects/${projectId}/problem-statement`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.message || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error: any) {
    throw error;
  }
}

// Loading Component
const ProjectLoading = React.memo(() => (
  <div>
    <PageBreadcrumb pageTitle="Project Detail" />
    <div className="rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-gray-900/50 xl:px-10 xl:py-12 backdrop-blur-sm">
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading project...</p>
        </div>
      </div>
    </div>
  </div>
));

ProjectLoading.displayName = 'ProjectLoading';

// Error Component
const ProjectError = React.memo(({ error, onRetry, onBack }: { error: string; onRetry: () => void; onBack: () => void }) => (
  <div>
    <PageBreadcrumb pageTitle="Project Detail" />
    <div className="rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-gray-900/50 xl:px-10 xl:py-12 backdrop-blur-sm">
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertCircle className="w-12 h-12 text-red-500 dark:text-red-400 mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Failed to Load Project</h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4 max-w-md">{error}</p>
        <div className="flex gap-3">
          <Button 
            onClick={onRetry} 
            variant="outline"
            className="border-brand-200 dark:border-brand-700/50 text-brand-600 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-900/20"
          >
            <AlertCircle className="w-4 h-4 mr-2" />
            Try Again
          </Button>
          <Button 
            onClick={onBack}
            className="bg-brand-500 hover:bg-brand-600 dark:bg-brand-500 dark:hover:bg-brand-600 text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Projects
          </Button>
        </div>
      </div>
    </div>
  </div>
));

ProjectError.displayName = 'ProjectError';

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  
  // Problem statement state
  const [problemStatement, setProblemStatement] = useState<string | null>(null);
  const [problemStatementLoading, setProblemStatementLoading] = useState(false);
  const [problemStatementError, setProblemStatementError] = useState<string | null>(null);
  const [isEditingProblemStatement, setIsEditingProblemStatement] = useState(false);
  const [editedProblemStatement, setEditedProblemStatement] = useState<string>('');
  const [isSavingProblemStatement, setIsSavingProblemStatement] = useState(false);

  // Load project data
  const loadProject = useCallback(async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);

      const response = await fetchProject(projectId);
      
      if (response.success && response.data) {
        setProject(response.data);
      } else {
        throw new Error(response.message || 'Failed to fetch project');
      }
    } catch (err: any) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load project';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  // Load problem statement
  const loadProblemStatement = useCallback(async () => {
    if (!projectId) return;

    try {
      setProblemStatementLoading(true);
      setProblemStatementError(null);

      const response = await fetchProblemStatement(projectId);
      
      if (response && response.success && response.data) {
        setProblemStatement(response.data.problem_statement);
      } else {
        setProblemStatement(null);
      }
    } catch (err: any) {
      setProblemStatementError(err instanceof Error ? err.message : 'Failed to load problem statement');
      setProblemStatement(null);
    } finally {
      setProblemStatementLoading(false);
    }
  }, [projectId]);

  // Load data on mount
  useEffect(() => {
    loadProject();
    loadProblemStatement();
  }, [loadProject, loadProblemStatement]);

  // Update problem statement function
  const updateProblemStatement = useCallback(async () => {
    if (!projectId || isSavingProblemStatement) return;

    const token = authService.getCurrentToken();
    const sanitizedStatement = editedProblemStatement.trim();
    
    if (!sanitizedStatement) {
      toast.error('Problem statement cannot be empty');
      return;
    }

    if (sanitizedStatement.length > 2000) {
      toast.error('Problem statement is too long (max 2000 characters)');
      return;
    }

    try {
      setIsSavingProblemStatement(true);
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(`${apiUrl}/api/v2/vmp/projects/${projectId}/problem-statement`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          problem_statement: sanitizedStatement
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success && data.data) {
        setProblemStatement(data.data.problem_statement);
        setIsEditingProblemStatement(false);
        toast.success('Problem statement updated successfully');
      } else {
        throw new Error(data.message || 'Failed to update problem statement');
      }
    } catch (err: any) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update problem statement';
      toast.error(errorMessage);
    } finally {
      setIsSavingProblemStatement(false);
    }
  }, [projectId, editedProblemStatement, isSavingProblemStatement]);

  const handleEditProblemStatement = useCallback(() => {
    setEditedProblemStatement(problemStatement || '');
    setIsEditingProblemStatement(true);
  }, [problemStatement]);

  const handleCancelEditProblemStatement = useCallback(() => {
    setIsEditingProblemStatement(false);
    setEditedProblemStatement('');
  }, []);

  // Delete project function
  const deleteProject = useCallback(async () => {
    if (!projectId || isDeleting) return;

    const token = authService.getCurrentToken();

    try {
      setIsDeleting(true);
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(`${apiUrl}/api/v2/vmp/projects/${projectId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }
      
      let data: any = null;
      if (response.status !== 204) {
        data = await response.json().catch(() => null);
      }
      
      if (!data || data.success) {
        toast.success('Project deleted successfully');
        router.push('/team-workspace/projects');
      } else {
        throw new Error(data.message || 'Failed to delete project');
      }
    } catch (err: any) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete project';
      toast.error(errorMessage);
    } finally {
      setIsDeleting(false);
    }
  }, [projectId, isDeleting, router]);

  const getStatusColor = useCallback((status: string) => {
    const statusLower = status.toLowerCase();
    const colorMap: Record<string, string> = {
      'active': 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
      'completed': 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
      'paused': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
      'archived': 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400',
      'pending': 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400'
    };
    
    return colorMap[statusLower] || 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
  }, []);

  const getStepLabel = useCallback((step: string) => {
    const stepMap: Record<string, string> = {
      'project_setup': 'Project Setup',
      'customer_profile': 'Customer Profile',
      'vpc_composition': 'VPC Composition',
      'field_prep': 'Field Preparation',
      'data_collection': 'Data Collection',
      'analysis': 'Analysis',
      'completed': 'Completed'
    };
    
    return stepMap[step] || step.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }, []);

  const formatDate = useCallback((dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Invalid date';
    }
  }, []);

  const getProgressPercentage = useCallback((currentStep: string) => {
    const steps = ['project_setup', 'customer_profile', 'vpc_composition', 'field_prep', 'data_collection', 'analysis', 'completed'];
    const currentIndex = steps.indexOf(currentStep);
    return currentIndex >= 0 ? Math.round(((currentIndex + 1) / steps.length) * 100) : 0;
  }, []);

  const handleContinueProject = useCallback(() => {
    if (!project) return;
    
    const stepRoutes: Record<string, string> = {
      'customer_profile': `/team-workspace/customer-profile?project_id=${project.id}`,
      'vpc_composition': `/team-workspace/vpc-composition?project_id=${project.id}`,
      'field_prep': `/team-workspace/field-prep?project_id=${project.id}`,
      'data_collection': `/team-workspace/data-collection?project_id=${project.id}`,
      'analysis': `/team-workspace/analysis?project_id=${project.id}`
    };
    
    const route = stepRoutes[project.current_step] || `/team-workspace/customer-profile?project_id=${project.id}`;
    router.push(route);
  }, [project, router]);

  const handleBackToProjects = useCallback(() => {
    router.push('/team-workspace/projects');
  }, [router]);

  const handleGeneratePersona = useCallback(() => {
    if (!projectId || isNavigating) return;
    try {
      setIsNavigating(true);
      router.push(`/team-workspace/personas/${projectId}`);
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Navigation error:', err);
      }
      setIsNavigating(false);
    }
  }, [projectId, router, isNavigating]);

  // Memoized derived data
  const progressPercentage = useMemo(() => 
    project ? getProgressPercentage(project.current_step) : 0,
    [project, getProgressPercentage]
  );

  const personas = useMemo(() => 
    project?.vpc_data?.vpcs ? Object.values(project.vpc_data.vpcs) : [],
    [project?.vpc_data?.vpcs]);

  // Helper: memoized question type icon selector
  const getQuestionTypeIcon = useCallback((type: string) => {
    switch (type?.toLowerCase()) {
      case 'behavioral':
        return Users;
      case 'attitudinal':
        return Target;
      case 'contextual':
        return HelpCircle;
      default:
        return MessageSquare;
    }
  }, []);

  // Helper function for component type badges
  const getComponentTypeInfo = useCallback((type: 'jtbd' | 'pain' | 'gain') => {
    switch (type) {
      case 'jtbd':
        return {
          icon: Target,
          color: 'text-green-600 dark:text-green-400',
          bgColor: 'bg-green-100 dark:bg-green-800/30',
          borderColor: 'border-green-200 dark:border-green-600',
          label: 'Customer JOBS-TO-BE-DONE'
        };
      case 'pain':
        return {
          icon: Frown,
          color: 'text-red-600 dark:text-red-400',
          bgColor: 'bg-red-100 dark:bg-red-800/30',
          borderColor: 'border-red-200 dark:border-red-600',
          label: 'Customer Pains'
        };
      case 'gain':
        return {
          icon: TrendingUp,
          color: 'text-blue-600 dark:text-blue-400',
          bgColor: 'bg-blue-100 dark:bg-blue-800/30',
          borderColor: 'border-blue-200 dark:border-blue-600',
          label: 'Customer Gains'
        };
    }
  }, []);

  // Enhanced retry function with cache clearing
  const handleRetry = useCallback(() => {
    loadProject();
    loadProblemStatement();
  }, [loadProject, loadProblemStatement]);

  // Show loading while authentication is initializing or loading
  if (loading && !project) {
    return <ProjectLoading />;
  }

  // Show error state
  if (error) {
    return (
      <ProjectError 
        error={error} 
        onRetry={handleRetry}
        onBack={handleBackToProjects}
      />
    );
  }

  // Show project not found
  if (!project && !loading && !error) {
    return (
      <div>
        <PageBreadcrumb pageTitle="Project Detail" />
        <div className="rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-gray-900/50 xl:px-10 xl:py-12 backdrop-blur-sm">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <AlertCircle className="w-12 h-12 text-red-500 dark:text-red-400 mb-4 mx-auto" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Project Not Found</h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">The requested project could not be found.</p>
              <Button 
                onClick={handleBackToProjects}
                className="bg-brand-500 hover:bg-brand-600 dark:bg-brand-500 dark:hover:bg-brand-600 text-white"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Projects
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!project) {
    return <ProjectLoading />;
  }

  return (
    <div>
      <PageBreadcrumb pageTitle="Project Detail" />
      <div className="rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-gray-900/50 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="max-w-7xl mx-auto"
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <Button 
              variant="ghost" 
              onClick={handleBackToProjects}
              className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800/50"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Projects
            </Button>
            
            <div className="flex gap-2 justify-end items-center">
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive" className='hover:bg-red-400 disabled:bg-red-200' disabled={isDeleting}>
                    <span className="flex items-center gap-2">
                      <Trash className="w-4 h-4 mr-2" />
                      Delete Project
                    </span>
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <div className="flex flex-col gap-2 max-sm:items-center sm:flex-row sm:gap-4">
                    <div
                      className="flex size-9 shrink-0 items-center justify-center rounded-full border"
                      aria-hidden="true"
                    >
                      <CircleAlertIcon className="opacity-80" size={16} />
                    </div>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                      <AlertDialogDescription>
                        Are you sure you want to delete your project? All your project data will
                        be removed.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                  </div>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction className='bg-red-600 hover:bg-red-700' onClick={deleteProject}>Confirm</AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
              
              <Button 
                onClick={handleGeneratePersona}
                disabled={isNavigating}
                aria-busy={isNavigating}
                className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600 text-white disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {isNavigating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Redirecting...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Generate User Persona
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Project Header Card */}
          <Card className="mb-4 border border-brand-100 bg-brand-25 dark:border-brand-700/50 dark:bg-gray-900/80 backdrop-blur-sm">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <CardTitle className="text-2xl font-semibold text-brand-600 dark:text-brand-300">
                      {project.name}
                    </CardTitle>
                    <Badge className={`text-sm px-3 py-1 rounded-full ${getStatusColor(project.status)}`}>
                      {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                    </Badge>
                  </div>
                  <CardDescription className="text-sm text-gray-600 dark:text-gray-300 mb-4">
                    {stripInlineCitations(project.description)}
                  </CardDescription>
                  
                  {/* Progress Section */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-300">
                      <span className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-brand-500 dark:text-brand-400" />
                        Current Step: <span className="text-brand-600 dark:text-brand-300">{getStepLabel(project.current_step)}</span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CardHeader>
          </Card>

          {/* Problem Statement Section */}
          {(problemStatement || problemStatementLoading) && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="mb-4"
            >
              <div className="p-6 bg-gradient-to-br from-brand-50 via-white to-brand-50 dark:from-brand-900/20 dark:via-[#101828] dark:to-brand-900/20 border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg dark:hover:shadow-brand-500/20 transition-all duration-300 group">
                <div className="flex items-start gap-4">
                  
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-brand-500 dark:text-brand-100 mb-2 group-hover:text-brand-700 dark:group-hover:text-white transition-colors duration-200">
                      Evolving Problem Statement
                    </h3>
                    {problemStatementLoading ? (
                      <div className="flex items-center gap-2 text-brand-600 dark:text-brand-400">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="text-sm">Loading problem statement...</span>
                      </div>
                    ) : isEditingProblemStatement ? (
                      <div className="flex flex-col gap-3">
                        <textarea 
                          value={editedProblemStatement}
                          onChange={(e) => setEditedProblemStatement(e.target.value)}
                          rows={4}
                          className="w-full p-3 text-sm text-brand-800 dark:text-brand-200 bg-white dark:bg-gray-800 border border-brand-300 dark:border-brand-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 resize-none"
                          placeholder="Enter problem statement..."
                        />
                        <div className="flex gap-2">
                          <Button 
                            onClick={updateProblemStatement}
                            disabled={isSavingProblemStatement}
                            className="bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600 text-white"
                          >
                            {isSavingProblemStatement ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                Saving...
                              </>
                            ) : (
                              <>
                                <Save className="w-4 h-4 mr-2" />
                                Save Changes
                              </>
                            )}
                          </Button>
                          <Button 
                            onClick={handleCancelEditProblemStatement}
                            disabled={isSavingProblemStatement}
                            variant="outline"
                            className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300"
                          >
                            <X className="w-4 h-4 mr-2" />
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : problemStatement ? (
                      <div className="flex flex-col gap-3">
                        <p className="text-brand-800 dark:text-brand-200 leading-relaxed text-sm group-hover:text-brand-500 dark:group-hover:text-brand-100 transition-colors duration-200">
                          {problemStatement}
                        </p>
                        <div>
                          <Button 
                            onClick={handleEditProblemStatement}
                            variant="outline"
                            size="sm"
                            className="border-brand-300 dark:border-brand-600 text-brand-700 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-900/20"
                          >
                            <Edit2 className="w-4 h-4 mr-2" />
                            Edit Evolving Problem Statement
                          </Button>
                        </div>
                      </div>
                    ) : problemStatementError ? (
                      <div className="flex items-center gap-2 text-brand-600 dark:text-brand-400">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-sm">Problem statement not available</span>
                      </div>
                    ) : null}
                    
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Project Overview Grid */}
          <div className="mb-4">
            {/* Validation Report */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
              className="p-6 bg-brand-25 dark:bg-gray-900/80 border border-brand-200 dark:border-brand-700/30 rounded-xl shadow-sm hover:shadow-lg dark:hover:shadow-brand-500/20 transition-all duration-300 col-span-2 backdrop-blur-md dark:backdrop-blur-lg group"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-brand-500 dark:bg-gradient-to-br dark:from-brand-500 dark:to-brand-600 rounded-lg shadow-sm dark:shadow-brand-500/20">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-brand-600 dark:text-brand-100 group-hover:dark:text-white transition-colors duration-200">
                  Validation Report
                </h3>
              </div>
              <div className="space-y-3">
                <p className="text-gray-600 dark:text-gray-200 leading-relaxed group-hover:dark:text-gray-100 transition-colors duration-200">
                  {project.documents?.title || 'No validation report available'}
                </p>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-brand-500 dark:bg-brand-300 rounded-full shadow-sm dark:shadow-brand-300/30"></div>
                  <span className="text-md text-brand-600 dark:text-brand-200 font-medium group-hover:dark:text-brand-100 transition-colors duration-200">
                    {project.field_prep_data?.hypotheses?.length || 0} Hypotheses
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-brand-500 dark:bg-brand-300 rounded-full shadow-sm dark:shadow-brand-300/30"></div>
                  <span className="text-md text-brand-600 dark:text-brand-200 font-medium group-hover:dark:text-brand-100 transition-colors duration-200">
                    {project.field_prep_data?.assumptions?.length || 0} Assumptions Generated
                  </span>
                </div>
              </div>
            </motion.div>

           
          </div>

          {/* VPC Personas Section */}
          {personas.length > 0 && (
            <Card className="mb-8">
              <CardHeader>
                <CardTitle className="text-xl font-bold">Value Proposition Canvas - Personas</CardTitle>
                <CardDescription>
                  Customer profiles and personas for this project
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {personas.map((persona, index) => (
                    <div key={`persona-${persona.persona_id}-${index}`} className="border rounded-lg p-6 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-brand-600 dark:text-white">
                          {persona.persona_name}
                        </h3>
                        <Badge className={`${getStatusColor(persona.status)}`}>
                          {persona.status.replace(/_/g, ' ')}
                        </Badge>
                      </div>
                      
                      {persona.customer_profile && (
                        <div className="space-y-4">
                          {/* Jobs to be Done */}
                          <div>
                            <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                              Jobs to be Done ({persona.customer_profile.jobs_to_be_done.length})
                            </h4>
                            <div className="space-y-2">
                              {persona.customer_profile.jobs_to_be_done.slice(0, 2).map((job, jobIndex) => (
                                <div key={`job-${persona.persona_id}-${job.id}-${jobIndex}`} className="text-sm p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                  <div className="font-medium text-blue-900 dark:text-blue-300 mb-1">
                                    {job.label}
                                  </div>
                                  <div className="text-blue-700 dark:text-blue-400 text-xs">
                                    Confidence: {Math.round(job.confidence * 100)}%
                                  </div>
                                </div>
                              ))}
                              {persona.customer_profile.jobs_to_be_done.length > 2 && (
                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                  +{persona.customer_profile.jobs_to_be_done.length - 2} more
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Pains */}
                          <div>
                            <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                              Pains ({persona.customer_profile.pains.length})
                            </h4>
                            <div className="space-y-2">
                              {persona.customer_profile.pains.slice(0, 2).map((pain, painIndex) => (
                                <div key={`pain-${persona.persona_id}-${pain.id}-${painIndex}`} className="text-sm p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                                  <div className="font-medium text-red-900 dark:text-red-300 mb-1">
                                    {pain.label}
                                  </div>
                                  <div className="text-red-700 dark:text-red-400 text-xs">
                                    Confidence: {Math.round(pain.confidence * 100)}%
                                  </div>
                                </div>
                              ))}
                              {persona.customer_profile.pains.length > 2 && (
                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                  +{persona.customer_profile.pains.length - 2} more
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Gains */}
                          <div>
                            <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                              Gains ({persona.customer_profile.gains.length})
                            </h4>
                            <div className="space-y-2">
                              {persona.customer_profile.gains.slice(0, 2).map((gain, gainIndex) => (
                                <div key={`gain-${persona.persona_id}-${gain.id}-${gainIndex}`} className="text-sm p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                                  <div className="font-medium text-green-900 dark:text-green-300 mb-1">
                                    {gain.label}
                                  </div>
                                  <div className="text-green-700 dark:text-green-400 text-xs">
                                    Confidence: {Math.round(gain.confidence * 100)}%
                                  </div>
                                </div>
                              ))}
                              {persona.customer_profile.gains.length > 2 && (
                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                  +{persona.customer_profile.gains.length - 2} more
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                      
                      <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
                        Created: {formatDate(persona.created_at)}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Field Preparation Data */}
          {project.field_prep_data && (
            <div className="space-y-8 mt-8">
              {/* Assumptions - NEW WORKFLOW: Assumptions before Hypotheses */}
              {project.field_prep_data.assumptions && project.field_prep_data.assumptions.length > 0 && (
                <div className="space-y-6">
                  <div className="flex items-center gap-2">
                    <Target className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                    <h2 className="text-lg font-semibold text-brand-700 dark:text-white">
                      Assumptions ({project.field_prep_data.assumptions.length})
                    </h2>
                  </div>
                  
                  <div className="grid gap-6">
                    {project.field_prep_data.assumptions.slice(0, 3).map((assumption, index) => {
                      const typeInfo = assumption.component_type ? getComponentTypeInfo(assumption.component_type) : null;
                      const TypeIcon = typeInfo?.icon;
                      
                      return (
                        <motion.div
                          key={`assumption-${assumption.id}-${index}`}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.4, delay: index * 0.1 }}
                          className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 group dark:hover:bg-brand-700/50 transition-all duration-200 relative"
                        >
                          {/* Header */}
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-2 gap-2">
                            <div className="flex items-center gap-3 flex-wrap">
                              <span className="text-sm text-brand-500 dark:text-brand-400">
                                Assumption #{index + 1}
                              </span>
                              {typeInfo && TypeIcon && (
                                <Badge 
                                  className={`${typeInfo.bgColor} ${typeInfo.color} border ${typeInfo.borderColor} px-2 py-0.5 text-xs font-medium flex items-center gap-1`}
                                >
                                  <TypeIcon className="w-3 h-3" />
                                  {typeInfo.label}
                                </Badge>
                              )}
                              <span className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium bg-brand-50 dark:bg-brand-800 text-brand-700 dark:text-brand-200 rounded-full">
                                <UserCircle2 className="w-3.5 h-3.5" />
                                {assumption.persona_name || `Persona ${assumption.persona_id}`}
                              </span>
                            </div>
                          </div>
                          
                          {/* Assumption Statement */}
                          <div className="mb-6">
                            <p className="text-brand-700 dark:text-brand-200 leading-relaxed text-md bg-brand-50 dark:bg-brand-800/50 p-4 rounded-lg border border-brand-200 dark:border-brand-700 transition-colors">
                              {assumption.text}
                            </p>
                          </div>
                          
                          {/* Supporting Evidence */}
                          {assumption.evidence && assumption.evidence.length > 0 && (
                            <div>
                              <h5 className="font-semibold text-brand-500 dark:text-brand-100 mb-3 text-base">
                                Supporting Evidence:
                              </h5>
                              <div className="grid gap-3">
                                {assumption.evidence.map((evidence, evidenceIndex) => (
                                  <div
                                    key={`assumption-evidence-${assumption.id}-${evidenceIndex}`}
                                    className="flex items-start gap-3 p-3 bg-brand-50 dark:bg-brand-800/30 rounded-lg group-hover:bg-brand-100 dark:group-hover:bg-brand-800/50 transition-colors"
                                  >
                                    <div className="shrink-0 w-6 h-6 bg-brand-500 text-white rounded-full flex items-center justify-center text-xs font-bold mt-0.5">
                                      {evidenceIndex + 1}
                                    </div>
                                    <p className="text-brand-600 dark:text-brand-200 leading-relaxed text-sm">
                                      {evidence}
                                    </p>
                                  </div>
                                ))}
                              </div>
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
                  
                  {project.field_prep_data.assumptions.length > 3 && (
                    <div className="text-center">
                      <p className="text-sm text-brand-500 dark:text-brand-400 mb-3">
                        Showing 3 of {project.field_prep_data.assumptions.length} assumptions
                      </p>
                      <Button
                        onClick={() => router.push(`/team-workspace/assumptions/${projectId}`)}
                        variant="outline"
                        className="dark:border-brand-600 dark:text-brand-300 dark:hover:bg-brand-800"
                      >
                        View All Assumptions
                        <ChevronRight className="w-4 h-4 ml-2" />
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* Hypotheses */}
              {project.field_prep_data.hypotheses && project.field_prep_data.hypotheses.length > 0 && (
                <div className="space-y-6">
                  <div className="flex items-center gap-2">
                    <Lightbulb className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                    <h2 className="text-lg font-semibold text-brand-700 dark:text-white">
                      Hypotheses ({project.field_prep_data.hypotheses.length})
                    </h2>
                  </div>
                  
                  <div className="grid gap-6">
                    {project.field_prep_data.hypotheses.slice(0, 3).map((hypothesis, index) => (
                      <motion.div
                        key={`hypothesis-${hypothesis.id}-${index}`}
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
                          <span 
                            className="inline-block px-3 py-1 text-sm font-semibold bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-200 rounded-full"
                          >
                            {hypothesis.persona_name}
                          </span>
                          <span className="text-xs text-brand-500 dark:text-brand-400">
                            Hypothesis #{index + 1}
                          </span>
                        </div>
                        
                        {/* Hypothesis Statement */}
                        <div className="mb-6">
                          <h4 className="text-lg font-semibold text-brand-500 dark:text-brand-100 mb-3">
                            Hypothesis Statement
                          </h4>
                          {isStructuredHypothesisText(hypothesis.text) ? (
                            <div className="bg-brand-50 dark:bg-brand-800/50 p-4 rounded-lg border border-brand-200 dark:border-brand-700 space-y-2">
                              <p className="text-brand-700 dark:text-brand-200 leading-relaxed">
                                <span className="font-bold text-brand-600 dark:text-brand-300 text-base">We believe that </span>
                                {hypothesis.text.we_believe_that}
                              </p>
                              <p className="text-brand-700 dark:text-brand-200 leading-relaxed">
                                <span className="font-bold text-brand-600 dark:text-brand-300 text-base">Are struggling with </span>
                                {hypothesis.text.are_struggling_with}
                              </p>
                              <p className="text-brand-700 dark:text-brand-200 leading-relaxed">
                                <span className="font-bold text-brand-600 dark:text-brand-300 text-base">Thus </span>
                                {hypothesis.text.thus}
                              </p>
                              <p className="text-brand-700 dark:text-brand-200 leading-relaxed">
                                <span className="font-bold text-brand-600 dark:text-brand-300 text-base">That guarantees </span>
                                {hypothesis.text.that_guarantees}
                              </p>
                            </div>
                          ) : (
                            <p className="text-brand-700 dark:text-brand-200 leading-relaxed text-md bg-brand-50 dark:bg-brand-800/50 p-4 rounded-lg border border-brand-200 dark:border-brand-700 transition-colors">
                              {hypothesis.text as string}
                            </p>
                          )}
                        </div>
                        
                        {/* Supporting Evidence */}
                        {hypothesis.evidence && hypothesis.evidence.length > 0 && (
                          <div>
                            <h5 className="font-semibold text-brand-500 dark:text-brand-100 mb-3 text-base">
                              Supporting Evidence:
                            </h5>
                            <div className="grid gap-3">
                              {hypothesis.evidence.map((evidence, evidenceIndex) => (
                                <div
                                  key={`hypothesis-evidence-${hypothesis.id}-${evidenceIndex}`}
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
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Generated timestamp */}
                        <div className="mt-4 pt-3 border-t border-brand-200 dark:border-brand-700">
                          <p className="text-xs text-brand-500 dark:text-brand-400">
                            Generated on {formatDate(hypothesis.generated_at)}
                          </p>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                  
                  {project.field_prep_data.hypotheses.length > 3 && (
                    <div className="text-center">
                      <p className="text-sm text-brand-500 dark:text-brand-400 mb-3">
                        Showing 3 of {project.field_prep_data.hypotheses.length} hypotheses
                      </p>
                      <Button
                        onClick={() => router.push(`/team-workspace/hypothesis/${projectId}`)}
                        variant="outline"
                        className="dark:border-brand-600 dark:text-brand-300 dark:hover:bg-brand-800"
                      >
                        View All Hypotheses
                        <ChevronRight className="w-4 h-4 ml-2" />
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* Questionnaires */}
              {project.field_prep_data.questionnaires && project.field_prep_data.questionnaires.length > 0 && (
                <div className="space-y-6">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                    <h2 className="text-lg font-semibold text-brand-700 dark:text-white">
                      Interview Questionnaires ({project.field_prep_data.questionnaires.length})
                    </h2>
                  </div>
                  
                  <div className="grid gap-6">
                    {project.field_prep_data.questionnaires.slice(0, 5).map((question, index) => {
                      const typeInfo = question.component_type ? getComponentTypeInfo(question.component_type) : null;
                      const ComponentTypeIcon = typeInfo?.icon;
                      
                      return (
                        <motion.div
                          key={`questionnaire-${question.id}-${index}`}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.4, delay: index * 0.1 }}
                          className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 group dark:hover:bg-brand-700/50 transition-all duration-200 relative"
                        >
                          {/* Header */}
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-2 gap-2">
                            <div className="flex items-center gap-3 flex-wrap">
                              <span className="text-xs text-brand-500 dark:text-brand-400">
                                Question #{index + 1}
                              </span>
                              {typeInfo && ComponentTypeIcon && (
                                <>
                                  <span className="text-xs text-brand-500 dark:text-brand-400">To validate</span>
                                  <Badge 
                                    className={`${typeInfo.bgColor} ${typeInfo.color} border ${typeInfo.borderColor} px-2 py-0.5 text-xs font-medium flex items-center gap-1`}
                                  >
                                    <ComponentTypeIcon className="w-3 h-3" />
                                    {typeInfo.label}
                                  </Badge>
                                </>
                              )}
                            </div>
                          </div>
                          
                          {/* Question Text */}
                          <div className="mb-6">
                            <p className="text-brand-700 dark:text-brand-200 leading-relaxed text-md p-5 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-lg transition-colors">
                              {question.text}
                            </p>
                          </div>

                          {/* Generated timestamp */}
                          <div className="mt-4 pt-3 border-t border-brand-200 dark:border-brand-700">
                            <p className="text-xs text-brand-500 dark:text-brand-400">
                              Generated on {formatDate(question.generated_at)}
                            </p>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                  
                  {project.field_prep_data.questionnaires.length > 5 && (
                    <div className="text-center">
                      <p className="text-sm text-brand-500 dark:text-brand-400 mb-3">
                        Showing 5 of {project.field_prep_data.questionnaires.length} questions
                      </p>
                      <Button
                        onClick={() => router.push(`/team-workspace/questionnaires/${projectId}`)}
                        variant="outline"
                        className="dark:border-brand-600 dark:text-brand-300 dark:hover:bg-brand-800"
                      >
                        View All Questions
                        <ChevronRight className="w-4 h-4 ml-2" />
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}