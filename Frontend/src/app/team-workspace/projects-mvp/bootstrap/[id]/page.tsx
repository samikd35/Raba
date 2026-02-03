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
  Lightbulb,
  Target,
  Users,
  Trash,
  CircleAlertIcon,
  TrendingUp,
  ExternalLink,
  DollarSign,
  Shield,
  Sword,
  Sparkles,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Crosshair,
  Calendar,
  Link2,
  CheckCircle2
} from 'lucide-react';
import PageBreadcrumb from "@/components/common/module 3/sub-module-1/PageBreadCrumb";
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

// Types based on the new bootstrap API response
interface ResearchSource {
  n: number;
  url: string;
  title: string;
  snippet: string;
  publisher: string;
  captured_at: string;
}

interface Research {
  sources: ResearchSource[];
  summary: string;
  market_context: string;
  adoption_factors: string;
  problem_validation: string;
  solution_landscape: string;
}

interface ProblemDetail {
  who: string;
  what: string;
  where: string;
  why_now: string;
}

interface BusinessModelSeeds {
  cost_drivers: string[];
  revenue_model: string;
  pricing_hypothesis: string;
}

interface AlternativesAndCompetition {
  direct_competitors: string[];
  indirect_alternatives: string[];
  differentiation_summary: string;
}

interface ContextData {
  IdeaSummary: string;
  CustomerSegments: string[];
  Problem: ProblemDetail;
  SolutionOverview: string;
  Differentiation: string[];
  BusinessModelSeeds: BusinessModelSeeds;
  AlternativesAndCompetition: AlternativesAndCompetition;
  ConstraintsAndRisks: string[];
  Research: Research;
}

interface Invariants {
  customer_segment: string;
  geography: string;
  core_problem: string;
  core_solution_type: string;
}

interface ContextMetadata {
  context_mode: string;
  invariants: Invariants;
  created_at: string;
  updated_at: string;
}

interface EnhancedContext {
  version: number;
  draft: ContextData;
  confirmed: ContextData;
  metadata: ContextMetadata;
}

interface BootstrapProjectResponse {
  success: boolean;
  project_id: string;
  context_status: string;
  enhanced_context: EnhancedContext;
  message: string;
}

// Helper to strip inline numeric citation markers like [1], [23] from text
const stripInlineCitations = (text: string | undefined | null): string => {
  if (!text) return '';
  return text.replace(/\s*\[\d+\]/g, '');
};

// API function to fetch bootstrap project enhanced context
async function fetchBootstrapProject(projectId: string): Promise<BootstrapProjectResponse> {
  const token = authService.getCurrentToken();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  const response = await fetch(`${apiUrl}/api/v2/mvp/bootstrap/projects/${projectId}/enhanced-context`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Project not found.');
    }
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.message || `HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Loading Component
const ProjectLoading = React.memo(() => (
  <div className="space-y-6 w-full ">
    <PageBreadcrumb pageTitle="Bootstrap Project" />
    <div className="rounded-2xl border border-brand-200 bg-white  py-8 dark:border-brand-800 dark:bg-brand-900/50 backdrop-blur-sm">
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-brand-600 dark:text-brand-400">Loading project context...</p>
        </div>
      </div>
    </div>
  </div>
));

ProjectLoading.displayName = 'ProjectLoading';

// Error Component
const ProjectError = React.memo(({ error, onRetry, onBack }: { error: string; onRetry: () => void; onBack: () => void }) => (
  <div className="space-y-6 w-full">
    <PageBreadcrumb pageTitle="Bootstrap Project" />
    <Card>
      <CardContent className="py-12">
        <div className="flex flex-col items-center justify-center text-center">
          <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
            <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-brand-900 dark:text-white mb-2">Failed to Load Project</h3>
          <p className="text-brand-600 dark:text-brand-400 mb-6 max-w-md">{error}</p>
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
      </CardContent>
    </Card>
  </div>
));

ProjectError.displayName = 'ProjectError';

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  
  const [bootstrapData, setBootstrapData] = useState<BootstrapProjectResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);

  const loadProject = useCallback(async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);

      const response = await fetchBootstrapProject(projectId);
      
      if (response.success) {
        setBootstrapData(response);
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

  // Load data on mount
  useEffect(() => {
    loadProject();
  }, [loadProject]);

  // Delete project function
  const deleteProject = useCallback(async () => {
    if (!projectId || isDeleting) return;

    const token = authService.getCurrentToken();

    try {
      setIsDeleting(true);
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(`${apiUrl}/api/v2/mvp/bootstrap/projects/${projectId}`, {
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
      'archived': 'bg-brand-100 text-brand-800 dark:bg-brand-900/20 dark:text-brand-400',
      'pending': 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400'
    };
    
    return colorMap[statusLower] || 'bg-brand-100 text-brand-800 dark:bg-brand-900/20 dark:text-brand-400';
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

  const handleNextPage = useCallback(() => {
    if (!projectId || isNavigating) return;
    try {
      setIsNavigating(true);
      router.push(`/team-workspace/vps/${projectId}`);
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Navigation error:', err);
      }
      setIsNavigating(false);
    }
  }, [projectId, router, isNavigating]);

  // Memoized derived data from bootstrap context
  const contextData = useMemo(() => 
    bootstrapData?.enhanced_context?.confirmed || bootstrapData?.enhanced_context?.draft || null,
    [bootstrapData]
  );

  const handleRetry = useCallback(() => {
    loadProject();
  }, [loadProject]);

  const handleBackToProjects = useCallback(() => {
    router.push('/team-workspace/projects-mvp');
  }, [router]);

  // Show loading while authentication is initializing or loading
  if (loading && !bootstrapData) {
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
  if (!bootstrapData && !loading && !error) {
    return (
      <div className="w-full">
        <PageBreadcrumb pageTitle="Project" />
        <div className="rounded-2xl border border-brand-200 bg-white  py-4 dark:border-brand-800 dark:bg-brand-900/50 xl:py-12 backdrop-blur-sm">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <AlertCircle className="w-12 h-12 text-red-500 dark:text-red-400 mb-4 mx-auto" />
              <h3 className="text-lg font-semibold text-brand-900 dark:text-white mb-2">Project Not Found</h3>
              <p className="text-brand-600 dark:text-brand-400 mb-4">The requested project could not be found.</p>
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

  // If no bootstrap data or context data, return null
  if (!bootstrapData || !contextData) return null;

  return (
<div className="relative min-h-screen w-full max-w-full overflow-x-hidden">
      {/* Main Content Container - Fix applied here */}
      <div className="mx-auto w-full max-w-[100vw]  mt-2">      
        <PageBreadcrumb pageTitle="Bootstrap Project" />
 <Card className="space-y-2 p-2">
{/* Header */}
          <div className="flex items-center justify-between">
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
                onClick={handleNextPage}
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
                    Continue to VPS
                  </>
                )}
              </Button>
            </div>
          </div>





<div className='flex flex-col gap-3 items-center justify-center -mt-6'>


 {/* Invariants Section */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <Card className="hover:shadow-sm transition-shadow duration-200">
          <CardHeader>
            <div className="flex items-center gap-3">
              <Target className="w-5 h-5 text-brand-600 dark:text-brand-400" />
              <div>
                <CardTitle>Core Invariants</CardTitle>
                <CardDescription>Foundational constraints that remain constant</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="group p-4 bg-brand-25 dark:bg-brand-800/50 rounded-lg border border-brand-200 dark:border-brand-700 hover:border-brand-200 dark:hover:border-brand-700 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  <span className="text-sm font-semibold text-brand-500 dark:text-brand-400 uppercase tracking-wide">Customer Segment</span>
                </div>
                <p className="text-sm font-medium text-gray-500 dark:text-white wrap-break-word">
                  {stripInlineCitations(bootstrapData.enhanced_context.metadata.invariants.customer_segment)}
                </p>
              </div>
              <div className="group p-4 bg-brand-25 dark:bg-brand-800/50 rounded-lg border border-brand-200 dark:border-brand-700 hover:border-brand-200 dark:hover:border-brand-700 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <Crosshair className="w-4 h-4 text-green-600 dark:text-green-400" />
                  <span className="text-sm font-semibold text-brand-500 dark:text-brand-400 uppercase tracking-wide">Geography</span>
                </div>
                <p className="text-sm font-medium text-gray-500 dark:text-white wrap-break-word">
                  {stripInlineCitations(bootstrapData.enhanced_context.metadata.invariants.geography)}
                </p>
              </div>
              <div className="group p-4 bg-brand-25 dark:bg-brand-800/50 rounded-lg border border-brand-200 dark:border-brand-700 hover:border-brand-200 dark:hover:border-brand-700 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <CircleAlertIcon className="w-4 h-4 text-red-600 dark:text-red-400" />
                  <span className="text-sm font-semibold text-brand-500 dark:text-brand-400 uppercase tracking-wide">Core Problem</span>
                </div>
                <p className="text-sm font-medium text-gray-500 dark:text-white wrap-break-word">
                  {stripInlineCitations(bootstrapData.enhanced_context.metadata.invariants.core_problem)}
                </p>
              </div>
              <div className="group p-4 bg-brand-25 dark:bg-brand-800/50 rounded-lg border border-brand-200 dark:border-brand-700 hover:border-brand-200 dark:hover:border-brand-700 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <Lightbulb className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                  <span className="text-sm font-semibold text-brand-500 dark:text-brand-400 uppercase tracking-wide">Solution Type</span>
                </div>
                <p className="text-sm font-medium text-gray-500 dark:text-white wrap-break-word">
                  {stripInlineCitations(bootstrapData.enhanced_context.metadata.invariants.core_solution_type)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>


      {/* Idea Summary */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
            >
        <Card className="hover:shadow-sm transition-shadow duration-200">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-amber-50 dark:bg-amber-900/30 rounded-lg border border-amber-200 dark:border-amber-700">
                <Lightbulb className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <CardTitle>Idea Summary</CardTitle>
                <CardDescription>Core concept and value proposition</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="bg-amber-50 dark:bg-amber-900/30 rounded-lg border border-amber-200 dark:border-amber-700 p-4">
              <p className="text-amber-700 dark:text-amber-300 leading-relaxed text-sm wrap-break-word">
                {stripInlineCitations(contextData.IdeaSummary)}
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>



        {/* Customer Segments */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <Card className="hover:shadow-lg transition-shadow duration-200">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-blue-50 dark:bg-blue-900/30 rounded-lg border border-blue-200 dark:border-blue-700">
                <Users className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <CardTitle>Customer Segments</CardTitle>
                <CardDescription>{contextData.CustomerSegments.length} segment(s) identified</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700 p-4">
              <div className="flex flex-col gap-2">
                {contextData.CustomerSegments.map((segment, idx) => (
                  // <Badge 
                  //   key={idx} 
                  //   className="bg-white dark:bg-blue-800/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-600 px-3 py-1.5 text-sm font-medium hover:bg-blue-100 dark:hover:bg-blue-800/70 transition-colors"
                  // >
                  //   <Users className="w-3 h-3 mr-1.5" />
                  //   {stripInlineCitations(segment)}
                  // </Badge>
                   <p className='p-2 bg-gray-50 text-sm rounded-lg text-brand-500'>{stripInlineCitations(segment)}</p>
                ))}
              </div>
              {contextData.CustomerSegments.length === 0 && (
                <div className="text-center py-8">
                  <Users className="w-12 h-12 text-blue-400 dark:text-blue-500 mx-auto mb-3 opacity-50" />
                  <p className="text-blue-600 dark:text-blue-400 text-sm">No customer segments identified yet</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>


      {/* Problem Detail */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <Card className="hover:shadow-lg transition-shadow duration-200">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-red-50 dark:bg-red-900/30 rounded-lg border border-red-200 dark:border-red-700">
                <CircleAlertIcon className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <CardTitle>Problem Detail</CardTitle>
                <CardDescription>Key aspects of the problem being solved</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="group p-4 bg-brand-25 dark:bg-brand-800/50 rounded-lg border border-brand-200 dark:border-brand-700 hover:border-brand-200 dark:hover:border-brand-700 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  <span className="text-sm font-semibold text-brand-500 dark:text-brand-400 uppercase tracking-wide">Who</span>
                </div>
                <p className="text-sm font-medium text-gray-500 dark:text-white wrap-break-word">
                  {stripInlineCitations(contextData.Problem.who)}
                </p>
              </div>
              <div className="group p-4 bg-brand-25 dark:bg-brand-800/50 rounded-lg border border-brand-200 dark:border-brand-700 hover:border-brand-200 dark:hover:border-brand-700 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <CircleAlertIcon className="w-4 h-4 text-red-600 dark:text-red-400" />
                  <span className="text-sm font-semibold text-brand-500 dark:text-brand-400 uppercase tracking-wide">What</span>
                </div>
                <p className="text-sm font-medium text-gray-500 dark:text-white wrap-break-word">
                  {stripInlineCitations(contextData.Problem.what)}
                </p>
              </div>
              <div className="group p-4 bg-brand-25 dark:bg-brand-800/50 rounded-lg border border-brand-200 dark:border-brand-700 hover:border-brand-200 dark:hover:border-brand-700 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <Crosshair className="w-4 h-4 text-green-600 dark:text-green-400" />
                  <span className="text-sm font-semibold text-brand-500 dark:text-brand-400 uppercase tracking-wide">Where</span>
                </div>
                <p className="text-sm font-medium text-gray-500 dark:text-white wrap-break-word">
                  {stripInlineCitations(contextData.Problem.where)}
                </p>
              </div>
              <div className="group p-4 bg-brand-25 dark:bg-brand-800/50 rounded-lg border border-brand-200 dark:border-brand-700 hover:border-brand-200 dark:hover:border-brand-700 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                  <span className="text-sm font-semibold text-brand-500 dark:text-brand-400 uppercase tracking-wide">Why Now</span>
                </div>
                <p className="text-sm font-medium text-gray-500 dark:text-white wrap-break-word">
                  {stripInlineCitations(contextData.Problem.why_now)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Solution Overview */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
      >
        <Card className="hover:shadow-lg transition-shadow duration-200">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-green-50 dark:bg-green-900/30 rounded-lg border border-green-200 dark:border-green-700">
                <Lightbulb className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <CardTitle>Solution Overview</CardTitle>
                <CardDescription>Core solution and key differentiators</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700 p-4">
                <p className="text-green-700 dark:text-green-300 leading-relaxed text-sm wrap-break-word">
                  {stripInlineCitations(contextData.SolutionOverview)}
                </p>
              </div>
              {contextData.Differentiation && contextData.Differentiation.length > 0 && (
                <div className="bg-brand-25 dark:bg-brand-900/10 rounded-lg border border-brand-100 dark:border-brand-800/50 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="w-4 h-4 text-brand-500" />
                    <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-300 uppercase tracking-wide">
                      Key Differentiators ({contextData.Differentiation.length})
                    </h4>
                  </div>
                  <div className="space-y-2">
                    {contextData.Differentiation.map((diff, idx) => (
                      <div key={idx} className="group p-3 bg-white dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700/50 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
                        <div className="flex items-start gap-2">
                          <div className="w-1.5 h-1.5 bg-brand-400 rounded-full mt-1.5 flex-shrink-0" />
                          <span className="text-sm text-brand-600 dark:text-brand-400 wrap-break-word">
                            {stripInlineCitations(diff)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>




{/* Business Model */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
      >
        <Card className="hover:shadow-lg transition-shadow duration-200">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-brand-50 dark:bg-brand-900/30 rounded-lg border border-brand-200 dark:border-brand-700">
                <TrendingUp className="w-5 h-5 text-brand-600 dark:text-brand-400" />
              </div>
              <div>
                <CardTitle>Business Model</CardTitle>
                <CardDescription>Revenue, pricing, and cost structure</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                  <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-300 uppercase tracking-wide">Revenue Model</h4>
                </div>
                <p className="text-sm text-brand-600 dark:text-brand-400 wrap-break-word">
                  {stripInlineCitations(contextData.BusinessModelSeeds.revenue_model)}
                </p>
              </div>
              <div className="bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                  <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-300 uppercase tracking-wide">Pricing Hypothesis</h4>
                </div>
                <p className="text-sm text-brand-600 dark:text-brand-400 wrap-break-word">
                  {stripInlineCitations(contextData.BusinessModelSeeds.pricing_hypothesis)}
                </p>
              </div>
              {contextData.BusinessModelSeeds.cost_drivers && contextData.BusinessModelSeeds.cost_drivers.length > 0 && (
                <div className="bg-brand-25 dark:bg-brand-900/10 rounded-lg border border-brand-100 dark:border-brand-800/50 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <DollarSign className="w-4 h-4 text-brand-500" />
                    <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-300 uppercase tracking-wide">
                      Cost Drivers ({contextData.BusinessModelSeeds.cost_drivers.length})
                    </h4>
                  </div>
                  <div className="space-y-2">
                    {contextData.BusinessModelSeeds.cost_drivers.map((driver, idx) => (
                      <div key={idx} className="group p-3 bg-white dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700/50 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
                        <div className="flex items-start gap-2">
                          <div className="w-1.5 h-1.5 bg-brand-400 rounded-full mt-1.5 flex-shrink-0" />
                          <span className="text-sm text-brand-600 dark:text-brand-400 wrap-break-word">
                            {stripInlineCitations(driver)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>



 {/* Competition & Alternatives */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
      >
        <Card className="hover:shadow-lg transition-shadow duration-200">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-purple-50 dark:bg-purple-900/30 rounded-lg border border-purple-200 dark:border-purple-700">
                <Target className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <CardTitle>Competition & Alternatives</CardTitle>
                <CardDescription>Market landscape and competitive positioning</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {contextData.AlternativesAndCompetition.direct_competitors && contextData.AlternativesAndCompetition.direct_competitors.length > 0 && (
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Target className="w-4 h-4 text-green-600 dark:text-green-400" />
                    <h4 className="text-sm font-semibold text-green-700 dark:text-green-300 uppercase tracking-wide">
                      Direct Competitors ({contextData.AlternativesAndCompetition.direct_competitors.length})
                    </h4>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {contextData.AlternativesAndCompetition.direct_competitors.map((comp, idx) => (
                      <Badge key={idx} variant="outline" className="bg-white dark:bg-green-900/20 text-green-700 dark:text-green-300 border-green-200 dark:border-green-700 hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors">
                        {stripInlineCitations(comp)}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {contextData.AlternativesAndCompetition.indirect_alternatives && contextData.AlternativesAndCompetition.indirect_alternatives.length > 0 && (
                <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-700 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Target className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                    <h4 className="text-sm font-semibold text-orange-700 dark:text-orange-300 uppercase tracking-wide">
                      Indirect Alternatives ({contextData.AlternativesAndCompetition.indirect_alternatives.length})
                    </h4>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {contextData.AlternativesAndCompetition.indirect_alternatives.map((alt, idx) => (
                      <Badge key={idx} variant="outline" className="bg-white dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 border-orange-200 dark:border-orange-700 hover:bg-orange-100 dark:hover:bg-orange-900/30 transition-colors">
                        {stripInlineCitations(alt)}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {contextData.AlternativesAndCompetition.differentiation_summary && (
                <div className="bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                    <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-300 uppercase tracking-wide">Differentiation Summary</h4>
                  </div>
                  <p className="text-sm text-brand-600 dark:text-brand-400 wrap-break-word">
                    {stripInlineCitations(contextData.AlternativesAndCompetition.differentiation_summary)}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>

   {/* Research Insights */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
      >
        <Card className="hover:shadow-lg transition-shadow duration-200">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-brand-50 dark:bg-brand-900/30 rounded-lg border border-brand-200 dark:border-brand-700">
                <FileText className="w-5 h-5 text-brand-600 dark:text-brand-400" />
              </div>
              <div>
                <CardTitle>Research Insights</CardTitle>
                <CardDescription>Market research and validation findings</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {contextData.Research.summary && (
                <div className="bg-brand-25 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                    <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-300 uppercase tracking-wide">Summary</h4>
                  </div>
                  <p className="text-sm text-brand-600 dark:text-brand-400 wrap-break-word">
                    {stripInlineCitations(contextData.Research.summary)}
                  </p>
                </div>
              )}
              {contextData.Research.market_context && (
                <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                    <h4 className="text-sm font-semibold text-amber-700 dark:text-amber-300 uppercase tracking-wide">Market Context</h4>
                  </div>
                  <p className="text-sm text-amber-600 dark:text-amber-400 wrap-break-word">
                    {stripInlineCitations(contextData.Research.market_context)}
                  </p>
                </div>
              )}
              {contextData.Research.problem_validation && (
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <CircleAlertIcon className="w-4 h-4 text-green-600 dark:text-green-400" />
                    <h4 className="text-sm font-semibold text-green-700 dark:text-green-300 uppercase tracking-wide">Problem Validation</h4>
                  </div>
                  <p className="text-sm text-green-600 dark:text-green-400 wrap-break-word">
                    {stripInlineCitations(contextData.Research.problem_validation)}
                  </p>
                </div>
              )}
              {contextData.Research.sources && contextData.Research.sources.length > 0 && (
                <div className="bg-brand-25 dark:bg-brand-900/10 rounded-lg border border-brand-100 dark:border-brand-800/50 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <FileText className="w-4 h-4 text-brand-500" />
                    <h4 className="text-sm font-semibold text-brand-700 dark:text-brand-300 uppercase tracking-wide">
                      Research Sources ({contextData.Research.sources.length})
                    </h4>
                  </div>
                  <div className="space-y-2 max-h-80 overflow-y-auto pr-2">
                    {contextData.Research.sources.map((source, idx) => (
                      <div key={idx} className="group p-3 bg-white dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700/50 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
                        <div className="flex items-start gap-2">
                          <Badge variant="outline" className="flex-shrink-0 bg-brand-50 dark:bg-brand-800/50 text-brand-600 dark:text-brand-400 border-brand-200 dark:border-brand-700">
                            {source.n}
                          </Badge>
                          <div className="flex-1 min-w-0">
                            <a 
                              href={source.url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-sm font-medium text-brand-600 dark:text-brand-400 hover:underline block truncate group-hover:text-brand-700 dark:group-hover:text-brand-300 transition-colors"
                            >
                              {source.title}
                            </a>
                            <p className="text-xs text-brand-500 dark:text-brand-400 mt-1 break-all">
                              {source.publisher}
                            </p>
                            <p className="text-xs text-brand-600 dark:text-brand-400 mt-1 line-clamp-2 wrap-break-word">
                              {source.snippet}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>



 {/* Constraints & Risks */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1 }}
        className="w-full"
      >
        <Card className="hover:shadow-lg transition-shadow duration-200 w-full">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-red-50 dark:bg-red-900/30 rounded-lg border border-red-200 dark:border-red-700">
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <CardTitle>Constraints & Risks</CardTitle>
                <CardDescription>Key limitations and potential challenges</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                  <h4 className="text-sm font-semibold text-red-700 dark:text-red-300 uppercase tracking-wide">
                    Risk Assessment ({contextData.ConstraintsAndRisks.length})
                  </h4>
                </div>
                <div className="space-y-2">
                  {contextData.ConstraintsAndRisks.map((risk, idx) => (
                    <div key={idx} className="group p-3 bg-white dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700/50 hover:border-red-300 dark:hover:border-red-600 transition-colors">
                      <div className="flex items-start gap-2">
                        <div className="w-1.5 h-1.5 bg-red-400 rounded-full mt-1.5 flex-shrink-0" />
                        <span className="text-sm text-red-600 dark:text-red-400 wrap-break-word">
                          {stripInlineCitations(risk)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>


</div>

              </Card>

    </div>
    </div>
  );
}