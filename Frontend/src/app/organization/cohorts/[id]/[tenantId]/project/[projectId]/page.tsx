"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { MemberProjectDetailResponse, MemberProject, OwnerInfo, PVReport } from '@/types/organization';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/authStore';
import { toast } from 'sonner';
import {
  ArrowLeft,
  User,
  Building2,
  Calendar,
  Clock,
  GitBranch,
  Users,
  Lightbulb,
  Target,
  MessageSquare,
  MessageCircle,
  FileText,
  AlertCircle,
  RefreshCw,
  Mail,
  Crown,
  CheckCircle2,
  Info,
  Scroll,
  LayoutGrid,
  Sparkles,
  Briefcase,
  TrendingUp,
  BarChart3,
  Package,
  Loader2,
} from 'lucide-react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import { ProjectContentSectionOpen } from '@/components/organization/ProjectContentSection';
import {
  PersonaCard,
  HypothesisCard,
  AssumptionCard,
  QuestionnaireCard,
  CollapsibleSection,
} from '@/components/project';

// Dynamic imports for heavy components to reduce initial bundle size
const PVReportSection = dynamic(() => import('@/components/project').then(mod => mod.PVReportSection), { ssr: false });
const MarketResearchSection = dynamic(() => import('@/components/project').then(mod => mod.MarketResearchSection), { ssr: false });
const CustomerProfileV2Section = dynamic(() => import('@/components/project').then(mod => mod.CustomerProfileV2Section), { ssr: false });
const ValueMapV2Section = dynamic(() => import('@/components/project').then(mod => mod.ValueMapV2Section), { ssr: false });
const VPCV2CanvasSection = dynamic(() => import('@/components/project').then(mod => mod.VPCV2CanvasSection), { ssr: false });
const VPSSection = dynamic(() => import('@/components/project').then(mod => mod.VPSSection), { ssr: false });
const BMCSection = dynamic(() => import('@/components/project').then(mod => mod.BMCSection), { ssr: false });
const SolutionCritiqueSection = dynamic(() => import('@/components/project').then(mod => mod.SolutionCritiqueSection), { ssr: false });
const VPSv2Section = dynamic(() => import('@/components/project').then(mod => mod.VPSv2Section), { ssr: false });
const BMCv2Section = dynamic(() => import('@/components/project').then(mod => mod.BMCv2Section), { ssr: false });
const ProductRequirementSection = dynamic(() => import('@/components/project').then(mod => mod.ProductRequirementSection), { ssr: false });
const ChatDrawer = dynamic(() => import('@/features/member-project-chat/chat').then(mod => mod.ChatDrawer), { ssr: false });
import { getCachedProjectDetail, setCachedProjectDetail, clearProjectCache } from '@/lib/cache/projectCache';

const formatDate = (dateString: string) => {
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return 'N/A';
  }
};

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    active: 'border border-green-500 text-green-600 dark:border-green-400 dark:text-green-400 bg-transparent',
    completed: 'border border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400 bg-transparent',
    archived: 'border border-gray-400 text-gray-500 dark:border-gray-500 dark:text-gray-400 bg-transparent',
    draft: 'border border-yellow-500 text-yellow-600 dark:border-yellow-400 dark:text-yellow-400 bg-transparent',
  };
  return colors[status] || 'border border-gray-400 text-gray-500 dark:border-gray-500 dark:text-gray-400 bg-transparent';
};

const getStepColor = (step: string) => {
  const colors: Record<string, string> = {
    project_setup: 'border border-gray-400 text-gray-500 dark:border-gray-500 dark:text-gray-400 bg-transparent',
    vpc_composition: 'border border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400 bg-transparent',
    field_prep: 'border border-purple-500 text-purple-600 dark:border-purple-400 dark:text-purple-400 bg-transparent',
    data_collection: 'border border-green-500 text-green-600 dark:border-green-400 dark:text-green-400 bg-transparent',
    analysis: 'border border-orange-500 text-orange-600 dark:border-orange-400 dark:text-orange-400 bg-transparent',
    completed: 'border border-emerald-500 text-emerald-600 dark:border-emerald-400 dark:text-emerald-400 bg-transparent',
  };
  return colors[step] || 'border border-gray-400 text-gray-500 dark:border-gray-500 dark:text-gray-400 bg-transparent';
};

const formatStepName = (step: string) => {
  return step
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

// Local sub-component for Header to improve readability and performance
const ProjectHeader = React.memo(({ name, handleBack, handleRefresh, loading }: { name: string; handleBack: () => void; handleRefresh: () => void; loading: boolean }) => (
  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 px-1">
    <div className="flex items-center gap-4">
      <Button
        variant="outline"
        size="icon"
        onClick={handleBack}
        className="h-9 w-9 rounded-md border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
      >
        <ArrowLeft className="w-4 h-4 text-gray-600 dark:text-gray-400" />
      </Button>

      <div>
        <h1 className="text-xl font-bold text-brand-600 dark:text-white tracking-tight">
          {name}
        </h1>
      </div>
    </div>

    <div className="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={handleRefresh}
        disabled={loading}
        className="border-gray-200 dark:border-gray-700 h-9 px-3 rounded-md text-sm font-medium"
      >
        <RefreshCw className={`w-3.5 h-3.5 mr-2 ${loading ? 'animate-spin' : ''}`} />
        Refresh
      </Button>
    </div>
  </div>
));

// Local component for Overview Card to keep main render clean
const ProjectOverviewCard = React.memo(({ project, owner, OwnerIcon }: { project: MemberProject; owner: OwnerInfo; OwnerIcon: any }) => (
  <Card className="border border-brand-100 dark:border-brand-800 bg-brand-25 dark:bg-[#0c0c0c] shadow-sm overflow-hidden">
    <div className="grid grid-cols-1 lg:grid-cols-3 divide-y lg:divide-y-0 lg:divide-x divide-gray-100 dark:divide-gray-800">

      {/* Owner Profile */}
      <div className="p-6">
        <div className="flex items-center justify-center gap-4">
         
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-sm text-gray-400">Owner</span>
              <Badge
                variant="outline"
                className={`px-2 h-5 text-sm tracking-wider ${owner.member_type === 'team'
                  ? "border-purple-200 bg-purple-50/50 text-purple-700 dark:border-purple-800 dark:bg-purple-900/20 dark:text-purple-400"
                  : "border-blue-200 bg-blue-50/50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-400"
                  }`}
              >
                {owner.member_type === 'team' ? 'Team' : 'Individual'}
              </Badge>
            </div>
            <h3 className="font-bold text-lg text-brand-600 dark:text-white truncate">
              {owner.user_name || owner.team_name}
            </h3>
            <div className="flex items-center gap-1.5 text-xs text-gray-500 truncate">
              <Mail className="w-3 h-3" />
              {owner.user_email}
            </div>
          </div>
        </div>
      </div>

      {/* Progress & Status */}
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm text-gray-400">Status</span>
          <Badge variant="outline" className={`${getStatusColor(project.status)} rounded-md text-[10px] py-0 h-5 px-2`}>
            {project.status}
          </Badge>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Current Step</span>
            <span className="text-xs font-bold text-brand-600">{formatStepName(project.current_step)}</span>
          </div>
          <div className="h-1.5 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${project.current_step === 'completed' ? 'bg-emerald-500' :
                project.current_step === 'analysis' ? 'bg-amber-500' :
                  project.current_step === 'data_collection' ? 'bg-green-500' :
                    project.current_step === 'field_prep' ? 'bg-purple-500' : 'bg-brand-500'
                }`}
              style={{
                width: project.current_step === 'completed' ? '100%' :
                  project.current_step === 'analysis' ? '80%' :
                    project.current_step === 'data_collection' ? '60%' :
                      project.current_step === 'field_prep' ? '40%' :
                        project.current_step === 'vpc_composition' ? '20%' : '10%'
              }}
            />
          </div>
        </div>
      </div>

      {/* Dates */}
      <div className="p-6 flex flex-col justify-center items-center gap-3">
        <div className="flex items-center gap-3">
          <Calendar className="w-4 h-4 text-gray-400" />
          <div>
            <p className="text-xs text-gray-400 ">Created</p>
            <p className="text-sm font-bold text-brand-500 dark:text-gray-200">
              {new Date(project.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Clock className="w-4 h-4 text-gray-400" />
          <div>
            <p className="text-xs text-gray-400 ">Last Updated</p>
            <p className="text-sm font-bold text-brand-500 dark:text-gray-200">
              {new Date(project.updated_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
            </p>
          </div>
        </div>
      </div>
    </div>
  </Card>
));


export default function OrganizationMemberProjectDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuthStore();

  const organizationId = user?.tenant_id;
  const projectId = params.projectId as string;

  const [project, setProject] = useState<MemberProject | null>(null);
  const [owner, setOwner] = useState<OwnerInfo | null>(null);
  const [pvReport, setPvReport] = useState<PVReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

  const fetchProjectDetail = useCallback(async (forceRefresh = false) => {
    if (!organizationId || !projectId) {
      setError('Missing organization or project ID');
      setLoading(false);
      return;
    }

    // Try to load from cache first if not a force refresh
    if (!forceRefresh) {
      const cachedData = getCachedProjectDetail(projectId);
      if (cachedData) {
        setProject(cachedData.project);
        setOwner(cachedData.owner);
        setPvReport(cachedData.pv_report);
        setLoading(false);

        // Optionally fetch in background to refresh cache silently
        // fetchLatestInBackground();
        return;
      }
    }

    try {
      setLoading(true);
      setError(null);

      const response: MemberProjectDetailResponse = await organizationService.getMemberProjectDetail(
        organizationId,
        projectId
      );

      setProject(response.project);
      setOwner(response.owner);
      setPvReport(response.pv_report);

      // Save to cache
      setCachedProjectDetail(projectId, response);

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Project detail loaded:', {
          projectName: response.project.name,
          ownerName: response.owner.user_name,
          hasPvReport: !!response.pv_report,
          personaCount: response.project.vpc_data?.vpcs ? Object.keys(response.project.vpc_data.vpcs).length : 0,
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load project details';
      setError(message);
      toast.error(message);
      console.error('Failed to fetch project detail:', err);
    } finally {
      setLoading(false);
    }
  }, [organizationId, projectId]);

  useEffect(() => {
    fetchProjectDetail();
  }, [fetchProjectDetail]);

  const handleBack = () => {
    router.back();
  };

  const handleRefresh = () => {
    if (projectId) clearProjectCache(projectId);
    fetchProjectDetail(true);
  };


  // Extract personas from both sources:
  // 1. project.personas - The identified personas (from personas column)
  // 2. project.vpc_data.vpcs - VPC personas with customer profiles
  const projectPersonas = useMemo(() => project?.personas || [], [project?.personas]);
  const vpcPersonas = useMemo(
    () => (project?.vpc_data?.vpcs ? Object.values(project.vpc_data.vpcs) : []),
    [project?.vpc_data?.vpcs]
  );

  // Calculate statistics - use projectPersonas count, fallback to vpcPersonas
  const stats = useMemo(() => ({
    personaCount: projectPersonas.length > 0 ? projectPersonas.length : vpcPersonas.length,
    hypothesesCount: project?.field_prep_data?.hypotheses?.length || 0,
    assumptionsCount: project?.field_prep_data?.assumptions?.length || 0,
    questionnairesCount: project?.field_prep_data?.questionnaires?.length || 0,
  }), [projectPersonas.length, vpcPersonas.length, project?.field_prep_data]);

  const OwnerIcon = owner?.member_type === 'team' ? Building2 : User;

  // Loading State
  if (loading && !project) {
    return (
      <div className="container mx-auto min-h-[70vh] flex flex-col items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <div className="relative mb-6">
            <div className="w-16 h-16 border-4 border-brand-100 dark:border-brand-900/30 rounded-full mx-auto"></div>
            <div className="absolute top-0 left-1/2 -ml-8 w-16 h-16 border-4 border-t-brand-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
          </div>

          <h3 className="text-xl font-semibold text-brand-500 dark:text-white mb-2">
            Analyzing Project Insights
          </h3>
          <p className="text-gray-500 dark:text-gray-400 max-w-xs mx-auto text-sm">
            We're gathering all research data, canvases, and validation reports. This might take a moment...
          </p>


        </motion.div>
      </div>
    );
  }

  // Error State
  if (error && !project) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Button variant="ghost" onClick={handleBack} className="mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>

        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <div className="w-16 h-16 border-2 border-red-200 dark:border-red-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Failed to Load Project
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">{error}</p>
              <div className="flex items-center justify-center space-x-3">
                <Button variant="outline" onClick={handleBack}>
                  Go Back
                </Button>
                <Button onClick={handleRefresh} variant="outline" className="border-gray-200 dark:border-gray-700">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Try Again
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!project || !owner) return null;

  return (
    <div className="container mx-auto px-2 space-y-4">
      {/* Header */}
      <ProjectHeader
        name={project.name}
        handleBack={handleBack}
        handleRefresh={handleRefresh}
        loading={loading}
      />


      <ProjectOverviewCard
        project={project}
        owner={owner}
        OwnerIcon={OwnerIcon}
      />

      {/* Project Metrics & Metadata */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Personas */}
        <Card className="border border-gray-100 dark:border-gray-800 bg-white dark:bg-[#0c0c0c] shadow-none transition-all duration-200 hover:shadow-sm hover:border-gray-200 dark:hover:border-gray-700">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-sm text-gray-400">Personas</span>
              <div className="text-2xl font-bold text-brand-500 dark:text-white leading-none">
                {stats.personaCount}
              </div>
            </div>
            <Users className="w-5 h-5 text-brand-500 opacity-80" />
          </CardContent>
        </Card>

        {/* Hypotheses */}
        <Card className="border border-gray-100 dark:border-gray-800 bg-white dark:bg-[#0c0c0c] shadow-none transition-all duration-200 hover:shadow-sm hover:border-gray-200 dark:hover:border-gray-700">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-sm text-gray-400">Hypotheses</span>
              <div className="text-2xl font-bold text-brand-500 dark:text-white leading-none">
                {stats.hypothesesCount}
              </div>
            </div>
            <Lightbulb className="w-5 h-5 text-brand-500 opacity-80" />
          </CardContent>
        </Card>

        {/* Assumptions */}
        <Card className="border border-gray-100 dark:border-gray-800 bg-white dark:bg-[#0c0c0c] shadow-none transition-all duration-200 hover:shadow-sm hover:border-gray-200 dark:hover:border-gray-700">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-sm text-gray-400">Assumptions</span>
              <div className="text-2xl font-bold text-brand-500 dark:text-white leading-none">
                {stats.assumptionsCount}
              </div>
            </div>
            <Target className="w-5 h-5 text-emerald-500 opacity-80" />
          </CardContent>
        </Card>

        {/* Questionnaires */}
        <Card className="border border-gray-100 dark:border-gray-800 bg-white dark:bg-[#0c0c0c] shadow-none transition-all duration-200 hover:shadow-sm hover:border-gray-200 dark:hover:border-gray-700">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-sm text-gray-400">Questions</span>
              <div className="text-2xl font-bold text-brand-500 dark:text-white leading-none">
                {stats.questionnairesCount}
              </div>
            </div>
            <MessageSquare className="w-5 h-5 text-brand-500 opacity-80" />
          </CardContent>
        </Card>
      </div>

      <ChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        projectId={projectId}
        organizationId={organizationId}
        title={project?.name ? `Chat about ${project.name}` : 'Project Chat'}
      />

      <button
        onClick={() => setIsChatOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-brand-500 text-white shadow-lg transition-all duration-200 hover:bg-brand-600 hover:scale-110 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
        aria-label="Open chat"
      >
        <MessageCircle className="h-6 w-6" />
      </button>



      {/* Project Summary Section (Always Open) */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.15 }}
      >
        <ProjectContentSectionOpen
          title="Project Summary"
          icon={Info}
          description="Overview of the project goals and key information"
        >
          <div className="space-y-4">
            {/* Problem Statement */}
            {project.description && (
              <div>
                <h4 className="text-md font-semibold text-brand-500 dark:text-gray-300 mb-2 flex items-center space-x-2">
                  <Scroll className="w-4 h-4" />
                  <span>Problem Statement</span>
                </h4>
                <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
                  {project.description}
                </p>
              </div>
            )}

          </div>
        </ProjectContentSectionOpen>
      </motion.div>

      {/* Problem Validation Report - First collapsible section */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.15 }}
      >
        <CollapsibleSection
          title="Problem Validation Report"
          description={pvReport?.title || "View the complete problem validation report"}
          icon={FileText}
          iconColor="text-brand-600"
          badge={pvReport ? "Complete" : undefined}
          badgeVariant="success"
          defaultOpen={false}
        >
          <PVReportSection
            pvReport={pvReport}
            readOnly={true}
            embedded={true}
          />
        </CollapsibleSection>
      </motion.div>

      {/* Phase 6: Identified Personas Section */}
      {projectPersonas.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Identified Personas"
            description={`Target customer personas for this project`}
            icon={Users}
            iconColor="text-brand-600"
            badge={projectPersonas.length}
            defaultOpen={false}
          >
            <div className={`grid gap-4 ${projectPersonas.length === 1 ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
              {projectPersonas.map((persona, index) => (
                <div key={`persona-${persona.id}-${index}`} className="border border-gray-200 dark:border-gray-700 rounded-lg p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 border-2 border-brand-300 dark:border-brand-600 rounded-full flex items-center justify-center">
                        <User className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                      </div>
                      <div>
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                          {persona.name}
                        </h3>
                        <Badge variant="outline" className="text-xs mt-1 bg-transparent border-gray-300 dark:border-gray-600">
                          {persona.id}
                        </Badge>
                      </div>
                    </div>
                  </div>
                  {persona.description && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                      {persona.description}
                    </p>
                  )}
                  {persona.problem_relationship && (
                    <div className="text-sm text-gray-600 dark:text-gray-400 border border-blue-300 dark:border-blue-700 p-3 rounded-lg">
                      <span className="font-medium text-blue-600 dark:text-blue-400">Problem Relationship:</span> {persona.problem_relationship}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 7: Customer Profile Section */}
      {project.vpc_data?.customer_profile && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Customer Profile"
            description="Jobs to be done, pains, and gains"
            icon={User}
            iconColor="text-blue-600"
            defaultOpen={false}
          >
            <div className="space-y-6">
              {/* Jobs to be Done */}
              {project.vpc_data.customer_profile.jobs_to_be_done?.length > 0 && (
                <div>
                  <h4 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                    <Briefcase className="w-5 h-5 text-blue-500" />
                    Jobs to be Done ({project.vpc_data.customer_profile.jobs_to_be_done.length})
                  </h4>
                  <div className="space-y-2">
                    {project.vpc_data.customer_profile.jobs_to_be_done.map((job, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-blue-300 dark:border-blue-700">
                        <p className="font-medium text-gray-800 dark:text-gray-200">{job.label}</p>
                        {job.description && <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{job.description}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {/* Pains */}
              {project.vpc_data.customer_profile.pains?.length > 0 && (
                <div>
                  <h4 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-500" />
                    Pains ({project.vpc_data.customer_profile.pains.length})
                  </h4>
                  <div className="space-y-2">
                    {project.vpc_data.customer_profile.pains.map((pain, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-red-300 dark:border-red-700">
                        <p className="font-medium text-gray-800 dark:text-gray-200">{pain.label}</p>
                        {pain.description && <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{pain.description}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {/* Gains */}
              {project.vpc_data.customer_profile.gains?.length > 0 && (
                <div>
                  <h4 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-green-500" />
                    Gains ({project.vpc_data.customer_profile.gains.length})
                  </h4>
                  <div className="space-y-2">
                    {project.vpc_data.customer_profile.gains.map((gain, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-green-300 dark:border-green-700">
                        <p className="font-medium text-gray-800 dark:text-gray-200">{gain.label}</p>
                        {gain.description && <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{gain.description}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 8: Assumptions Section - NEW WORKFLOW: Assumptions before Hypotheses */}
      {project.field_prep_data?.assumptions && project.field_prep_data.assumptions.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Assumptions"
            description="Testable assumptions derived from personas"
            icon={Target}
            iconColor="text-green-600"
            badge={project.field_prep_data.assumptions.length}
            defaultOpen={false}
          >
            <div className="grid gap-6">
              {project.field_prep_data.assumptions.map((assumption, index) => (
                <AssumptionCard
                  key={`assumption-${assumption.id}-${index}`}
                  assumption={assumption}
                  index={index}
                  readOnly={true}
                  animationDelay={0}
                />
              ))}
            </div>
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 9: Hypotheses Section */}
      {project.field_prep_data?.hypotheses && project.field_prep_data.hypotheses.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Hypotheses"
            description="Market hypotheses synthesized from assumptions"
            icon={Lightbulb}
            iconColor="text-purple-600"
            badge={project.field_prep_data.hypotheses.length}
            defaultOpen={false}
          >
            <div className="grid gap-6">
              {project.field_prep_data.hypotheses.map((hypothesis, index) => (
                <HypothesisCard
                  key={`hypothesis-${hypothesis.id}-${index}`}
                  hypothesis={hypothesis}
                  index={index}
                  readOnly={true}
                  animationDelay={0}
                />
              ))}
            </div>
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 10: Questionnaires Section */}
      {project.field_prep_data?.questionnaires && project.field_prep_data.questionnaires.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Interview Questionnaires"
            description="Field research questions for customer interviews"
            icon={MessageSquare}
            iconColor="text-orange-600"
            badge={project.field_prep_data.questionnaires.length}
            defaultOpen={false}
          >
            <div className="grid gap-6">
              {project.field_prep_data.questionnaires.map((questionnaire, index) => (
                <QuestionnaireCard
                  key={`questionnaire-${questionnaire.id}-${index}`}
                  questionnaire={questionnaire}
                  index={index}
                  readOnly={true}
                  animationDelay={0}
                />
              ))}
            </div>
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 10.5: Market Research Analysis Section */}
      {project.analysis_data && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Market Research Analysis"
            description="AI-powered analysis of market validation research data"
            icon={BarChart3}
            iconColor="text-emerald-600"
            badge={project.analysis_status === 'completed' ? 'Complete' : project.analysis_status}
            defaultOpen={false}
          >
            <MarketResearchSection
              analysisData={project.analysis_data}
              readOnly={true}
              embedded={true}
            />
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 10.6: Customer Profile v2 Section */}
      {project.vpc_v2_data && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Enhanced Customer Profile"
            description="Research-validated customer pains, gains, and jobs to be done"
            icon={Target}
            iconColor="text-purple-600"
            badge="v2"
            defaultOpen={false}
          >
            <CustomerProfileV2Section
              vpcV2Data={project.vpc_v2_data}
              readOnly={true}
              embedded={true}
            />
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 10.7: Value Map V2 Section */}
      {project.vpc_v2_data && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Value Map Selections"
            description="Research-backed pain relievers, gain creators, and products/services"
            icon={Package}
            iconColor="text-cyan-600"
            badge="v2"
            defaultOpen={false}
          >
            <ValueMapV2Section
              vpcV2Data={project.vpc_v2_data}
              readOnly={true}
              embedded={true}
            />
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 11: VPC Section - Uses vpc_v2_data (Customer Profile v2 + Value Map) */}
      {project.vpc_v2_data && Object.keys(project.vpc_v2_data).some(
        key => key.startsWith('P') &&
          (project.vpc_v2_data![key]?.customer_profile || project.vpc_v2_data![key]?.value_map_selections)
      ) && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.15 }}
          >
            <CollapsibleSection
              title="Value Proposition Canvas"
              description="Combined customer profile and value map visualization"
              icon={LayoutGrid}
              iconColor="text-indigo-600"
              defaultOpen={false}
            >
              <VPCV2CanvasSection
                vpcV2Data={project.vpc_v2_data}
                readOnly={true}
                embedded={true}
              />
            </CollapsibleSection>
          </motion.div>
        )}

      {/* Phase 12: Value Proposition Statement */}
      {project.mvp_data && (project.mvp_data.vps_v1?.length || project.mvp_data.vps_v2?.length) && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Value Proposition Statement"
            description="AI-generated value proposition statement for your product"
            icon={FileText}
            iconColor="text-violet-600"
            badge={project.mvp_data.current_version?.vps?.toString() || undefined}
            defaultOpen={false}
          >
            <VPSSection
              mvpData={project.mvp_data}
              readOnly={true}
              embedded={true}
            />
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 13: Business Model Canvas */}
      {project.mvp_data && (project.mvp_data.bmc || project.mvp_data.bmc_v2) && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Business Model Canvas"
            description="AI-generated business model for your product"
            icon={LayoutGrid}
            iconColor="text-amber-600"
            badge={project.mvp_data.current_version?.bmc?.toString() || undefined}
            defaultOpen={false}
          >
            <BMCSection
              mvpData={project.mvp_data}
              readOnly={true}
              embedded={true}
            />
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 14: Solution Critique */}
      {project.soln_critique_data && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Solution Critique"
            description="AI-powered analysis of your solution across 6 dimensions"
            icon={Sparkles}
            iconColor="text-purple-600"
            badge={project.soln_critique_data.status === 'completed' ? 'Completed' : project.soln_critique_data.status?.toUpperCase()}
            defaultOpen={false}
          >
            <SolutionCritiqueSection
              critiqueData={project.soln_critique_data}
              readOnly={true}
              embedded={true}
            />
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 15: VPS v2 (Refined after critique) */}
      {project.mvp_data?.vps_v2 && project.mvp_data.vps_v2.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Value Proposition Statement v2"
            description="Refined value proposition statement based on solution critique"
            icon={FileText}
            iconColor="text-emerald-600"
            badge="V2"
            defaultOpen={false}
          >
            <VPSv2Section
              vpsData={project.mvp_data.vps_v2}
              readOnly={true}
              embedded={true}
            />
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 16: BMC v2 (Refined after critique) */}
      {project.mvp_data?.bmc_v2 && Object.keys(project.mvp_data.bmc_v2).length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <CollapsibleSection
            title="Business Model Canvas v2"
            description="Refined business model based on solution critique"
            icon={LayoutGrid}
            iconColor="text-emerald-600"
            badge="V2"
            defaultOpen={false}
          >
            <BMCv2Section
              bmcData={project.mvp_data.bmc_v2}
              readOnly={true}
              embedded={true}
            />
          </CollapsibleSection>
        </motion.div>
      )}

      {/* Phase 17: Product Requirement Document */}
      {(project.mvp_data as any)?.amrg?.current_prd && (
        <CollapsibleSection
          title="Product Requirement Document"
          description="Detailed product requirements and specifications"
          icon={FileText}
          iconColor="text-indigo-600"
          badge="PRD"
          defaultOpen={false}
        >
          <ProductRequirementSection
            prdData={{
              prd_json: (project.mvp_data as any).amrg.current_prd,
              version: (project.mvp_data as any).amrg.current_prd_version,
            }}
            readOnly={true}
            embedded={true}
          />
        </CollapsibleSection>
      )}
    </div>
  );
}
