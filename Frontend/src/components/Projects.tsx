'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FolderOpen, 
  Calendar, 
  User, 
  TrendingUp, 
  Clock, 
  FileText, 
  Loader2, 
  AlertCircle,
  Plus,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  RefreshCw,
  ArrowRight,
  Sparkles,
  Target,
  BarChart3,
  Users,
  CheckCircle2,
  PlayCircle,
  PauseCircle,
  Search,
  Filter,
  X,
  SortAsc,
  SortDesc,
  CalendarDays
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuLabel } from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { authService } from '@/services/authService';
import toast from "react-hot-toast";

interface Project {
  id: string;
  tenant_id: string;
  user_id: string;
  name: string;
  description: string;
  problem_statement: string;
  status: string;
  current_step: string;
  created_at: string;
  updated_at: string;
  progress_percentage: number;
  artifact_count: number;

  // Optional computed / legacy fields that may still be populated elsewhere
  pv_report_title?: string;
  documents?: {
    title: string;
  };
}

interface ProjectsResponse {
  success: boolean;
  data: {
    projects: Project[];
    total_count: number;
    page: number;
    page_size: number;
    has_next: boolean;
  };
  message: string;
}

// Enhanced API function
async function fetchProjects(): Promise<ProjectsResponse> {
  const token = authService.getCurrentToken();

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/vmp/projects`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Enhanced Loading Component
const ProjectsLoading = React.memo(() => (
  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
    {[...Array(6)].map((_, i) => (
      <motion.div
        key={i}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: i * 0.1 }}
      >
        <Card className="h-full bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800 backdrop-blur-sm">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div className="space-y-2 flex-1">
                <div className="h-5 bg-gray-100 dark:bg-gray-700 rounded-lg w-3/4 animate-pulse"></div>
                <div className="h-3 bg-gray-50 dark:bg-gray-800 rounded w-1/2 animate-pulse"></div>
              </div>
              <div className="h-6 w-16 bg-gray-100 dark:bg-gray-700 rounded-full animate-pulse"></div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="h-2 bg-gray-50 dark:bg-gray-800 rounded-full animate-pulse"></div>
              <div className="flex justify-between">
                <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded w-20 animate-pulse"></div>
                <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded w-12 animate-pulse"></div>
              </div>
            </div>
            <div className="h-3 bg-gray-50 dark:bg-gray-800 rounded w-full animate-pulse"></div>
            <div className="h-8 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse"></div>
          </CardContent>
        </Card>
      </motion.div>
    ))}
  </div>
));

ProjectsLoading.displayName = 'ProjectsLoading';

// Enhanced Error Component
const ProjectsError = React.memo(({ error, onRetry }: { error: string; onRetry: () => void }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    className="flex flex-col items-center justify-center py-16 text-center"
  >
    <div className="p-4 rounded-full bg-red-100 dark:bg-red-900/30 mb-6">
      <AlertCircle className="w-12 h-12 text-red-600 dark:text-red-400" />
    </div>
    <h3 className="text-xl font-semibold text-brand-500 dark:text-gray-100 mb-3">Failed to Load Projects</h3>
    <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md leading-relaxed">{error}</p>
    <Button onClick={onRetry} className="bg-gray-600 hover:bg-gray-700 dark:bg-gray-600 dark:hover:bg-gray-700 text-white">
      <RefreshCw className="w-4 h-4 mr-2" />
      Try Again
    </Button>
  </motion.div>
));

ProjectsError.displayName = 'ProjectsError';

// Enhanced Empty State Component
const EmptyProjects = React.memo(() => {
  const router = useRouter();
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      <div className="relative mb-8">
        <div className="p-6 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 border dark:border-gray-600">
          <FolderOpen className="w-16 h-16 text-brand-600 dark:text-gray-400" />
        </div>
      </div>
      <h3 className="text-xl font-bold text-brand-500 dark:text-gray-100 mb-3">Discover more about the reality surrounding the problems you want to solve.</h3>
      {/* <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md leading-relaxed">
        Create your first project, pinpoint your customer persona, Craft a clear customer profile, extract the underlying hypotheses, and generate targeted interview questions to build a rock-solid foundation for your venture.
      </p> */}
      <div className="flex flex-col sm:flex-row gap-4">
        <Button 
          onClick={() => router.push('/team-workspace/problem-validator')}
          className="bg-gradient-to-r from-brand-600 to-brand-700 hover:from-brand-700 hover:to-brand-800 dark:from-brand-600 dark:to-brand-700 dark:hover:from-brand-700 dark:hover:to-brand-800 text-white shadow-lg hover:shadow-xl transition-all"
        >
          <Target className="w-4 h-4 mr-2" />
          Validate Problems 
        </Button>
        <Button 
          onClick={() => router.push('/team-workspace/problem-explorer')}
          variant="outline"
          className="border-gray-200 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:border-gray-500"
        >
          <Eye className="w-4 h-4 mr-2" />
          Explore More Problems
        </Button>
      </div>
    </motion.div>
  );
});

EmptyProjects.displayName = 'EmptyProjects';

// Enhanced Project Card Component
const ProjectCard = React.memo(({ project, index, onSelect, isNavigating = false }: { project: Project; index: number; onSelect: (project: Project) => void; isNavigating?: boolean }) => {
  const router = useRouter();

  const getStatusConfig = useCallback((status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return {
          color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
          icon: PlayCircle,
          gradient: 'from-green-500 to-emerald-500'
        };
      case 'completed':
        return {
          color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
          icon: CheckCircle2,
          gradient: 'from-blue-500 to-cyan-500'
        };
      case 'paused':
        return {
          color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
          icon: PauseCircle,
          gradient: 'from-yellow-500 to-orange-500'
        };
      case 'archived':
        return {
          color: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
          icon: FileText,
          gradient: 'from-gray-500 to-slate-500'
        };
      default:
        return {
          color: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
          icon: Target,
          gradient: 'from-gray-500 to-gray-500'
        };
    }
  }, []);

  const getStepLabel = useCallback((step: string) => {
    const stepMap: Record<string, string> = {
      'project_setup': 'Project Setup',
      'vpc_composition': 'VPC Composition',
      'field_prep': 'Field Preparation',
      'data_collection': 'Data Collection',
      'analysis': 'Analysis',
      'completed': 'Completed'
    };
    return stepMap[step] || step.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
  }, []);

  const formatDate = useCallback((dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }, []);

  const handleProjectClick = useCallback(() => {
    onSelect(project);
  }, [onSelect, project]);

  const statusConfig = getStatusConfig(project.status);
  const StatusIcon = statusConfig.icon;
  const progressPercentage = Math.max(0, Math.min(100, project.progress_percentage || 0));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="group"
    >
      <Card className="cursor-pointer h-full border-brand-100 dark:border-brand-700 backdrop-blur-sm hover:shadow-md transition-all" onClick={handleProjectClick}>
        <CardHeader className="pb-4 relative">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <CardTitle className="text-lg font-semibold text-brand-500 dark:text-gray-100 line-clamp-2 group-hover:text-brand-500 dark:group-hover:text-gray-100 transition-colors">
                {project.name}
              </CardTitle>
              <CardDescription className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mt-2 leading-relaxed">
                {project.description}
              </CardDescription>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition-all duration-200 hover:bg-gray-50 dark:hover:bg-gray-800">
                  <MoreVertical className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48 bg-white dark:bg-gray-900 border-gray-100 dark:border-gray-700 backdrop-blur-sm">
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleProjectClick(); }} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <Eye className="w-4 h-4 mr-2" />
                  View Details
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>

        <CardContent className="space-y-5 relative -mt-6">
          {/* Progress Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5 text-brand-600 dark:text-brand-400">
                <BarChart3 className="w-3 h-3" />
                <span className="font-medium">{getStepLabel(project.current_step)}</span>
              </div>
              <div className="flex items-center gap-1.5 text-brand-500 dark:text-brand-400">
                <FileText className="w-3 h-3" />
                <span>{project.artifact_count || 0} artifacts</span>
              </div>
            </div>
          </div>

          {/* PV Report Section */}
          <div className="p-3 rounded-lg bg-brand-25 dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-3.5 h-3.5 text-gray-600 dark:text-gray-400" />
              <span className="text-xs font-medium text-brand-600 dark:text-brand-400">Validation Report</span>
            </div>
            <p className="text-sm text-brand-600 dark:text-brand-400 line-clamp-2 leading-relaxed">
              {project.pv_report_title || 'No validation report linked'}
            </p>
          </div>

          {/* Dates */}
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-1.5">
              <Clock className="w-3 h-3" />
              <span>Updated {formatDate(project.updated_at)}</span>
            </div>
          </div>

          {/* In-card loading overlay */}
          {isNavigating && (
            <div className="absolute inset-0 z-10 bg-white/70 dark:bg-black/50 backdrop-blur-sm flex items-center justify-center rounded-xl">
              <div className="flex flex-col items-center gap-2 text-gray-700 dark:text-gray-300">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-xs">Opening project…</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
});

ProjectCard.displayName = 'ProjectCard';

// Filter and Sort Types
type SortOption = 'name' | 'created_at' | 'updated_at' | 'progress' | 'status';
type SortDirection = 'asc' | 'desc';
type StatusFilter = 'all' | 'active' | 'completed' | 'paused' | 'archived';
type StepFilter = 'all' | 'project_setup' | 'vpc_composition' | 'field_prep' | 'data_collection' | 'analysis' | 'completed';

interface FilterState {
  search: string;
  status: StatusFilter;
  step: StepFilter;
  sortBy: SortOption;
  sortDirection: SortDirection;
  dateRange: 'all' | 'today' | 'week' | 'month' | 'quarter';
}

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    search: '',
    status: 'all',
    step: 'all',
    sortBy: 'updated_at',
    sortDirection: 'desc',
    dateRange: 'all'
  });
  const [showFilters, setShowFilters] = useState(false);
  const [navigatingProjectId, setNavigatingProjectId] = useState<string | null>(null);
  
  const router = useRouter();

  // Load projects on component mount
  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetchProjects();
      
      if (response.success && response.data?.projects) {
        setProjects(response.data.projects);
      } else {
        throw new Error(response.message || 'Failed to fetch projects');
      }
    } catch (err: any) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load projects';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load projects on mount
  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Retry function
  const handleRetry = useCallback(() => {
    loadProjects();
  }, [loadProjects]);

  // Refresh function
  const handleRefresh = useCallback(() => {
    loadProjects();
  }, [loadProjects]);

  // Filter and sort projects
  const filteredAndSortedProjects = useMemo(() => {
    let filtered = [...projects];

    // Search filter
    if (filters.search.trim()) {
      const searchTerm = filters.search.toLowerCase().trim();
      filtered = filtered.filter(project => 
        project.name.toLowerCase().includes(searchTerm) ||
        project.description.toLowerCase().includes(searchTerm) ||
        project.pv_report_title?.toLowerCase().includes(searchTerm)
      );
    }

    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(project => 
        project.status.toLowerCase() === filters.status
      );
    }

    // Step filter
    if (filters.step !== 'all') {
      filtered = filtered.filter(project => 
        project.current_step === filters.step
      );
    }

    // Date range filter
    if (filters.dateRange !== 'all') {
      const now = new Date();
      const filterDate = new Date();
      
      switch (filters.dateRange) {
        case 'today':
          filterDate.setHours(0, 0, 0, 0);
          break;
        case 'week':
          filterDate.setDate(now.getDate() - 7);
          break;
        case 'month':
          filterDate.setMonth(now.getMonth() - 1);
          break;
        case 'quarter':
          filterDate.setMonth(now.getMonth() - 3);
          break;
      }
      
      filtered = filtered.filter(project => 
        new Date(project.updated_at) >= filterDate
      );
    }

    // Sort projects
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;
      
      switch (filters.sortBy) {
        case 'name':
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
          break;
        case 'created_at':
          aValue = new Date(a.created_at);
          bValue = new Date(b.created_at);
          break;
        case 'updated_at':
          aValue = new Date(a.updated_at);
          bValue = new Date(b.updated_at);
          break;
        case 'progress':
          aValue = a.progress_percentage || 0;
          bValue = b.progress_percentage || 0;
          break;
        case 'status':
          aValue = a.status.toLowerCase();
          bValue = b.status.toLowerCase();
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return filters.sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return filters.sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [projects, filters]);

  const handleFilterChange = useCallback((key: keyof FilterState, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({
      search: '',
      status: 'all',
      step: 'all',
      sortBy: 'updated_at',
      sortDirection: 'desc',
      dateRange: 'all'
    });
  }, []);

  const hasActiveFilters = useMemo(() => {
    return filters.search.trim() !== '' || 
           filters.status !== 'all' || 
           filters.step !== 'all' || 
           filters.dateRange !== 'all' ||
           filters.sortBy !== 'updated_at' ||
           filters.sortDirection !== 'desc';
  }, [filters]);

  const handleCreateProject = useCallback(() => {
    router.push('/team-workspace/problem-validator');
  }, [router]);

  const handleProjectSelect = useCallback((project: Project) => {
    // Show navigating state immediately for responsive UX
    setNavigatingProjectId(project.id);
    // Navigate to the project page
    router.push(`/team-workspace/projects/${project.id}`);
  }, [router]);

  const projectCards = useMemo(() => 
    filteredAndSortedProjects.map((project, index) => (
      <ProjectCard 
        key={project.id} 
        project={project} 
        index={index} 
        onSelect={handleProjectSelect}
        isNavigating={navigatingProjectId === project.id}
      />
    )), [filteredAndSortedProjects, handleProjectSelect, navigatingProjectId]
  );

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100 flex items-center gap-2">
              Recent Projects
            </h2>
          </div>
        </div>
        <ProjectsError error={error} onRetry={handleRetry} />
      </div>
    );
  }

  // Show loading skeleton while projects are being fetched to prevent flashing the empty state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100 flex items-center gap-2">
              Recent Projects
            </h2>
          </div>
        </div>
        <ProjectsLoading />
      </div>
    );
  }

  if (filteredAndSortedProjects.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="space-y-4"
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100 flex items-center gap-2">
                Recent Projects
              </h2>
            </div>
          </div>
          <EmptyProjects />
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      <Card className="px-4 bg-white dark:bg-gray-900 border-gray-100 dark:border-gray-700 backdrop-blur-sm">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-[1.2rem] font-bold text-brand-500 dark:text-gray-100 flex items-center gap-2">
                Recent Projects
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {filteredAndSortedProjects.length} of {projects.length} project{projects.length !== 1 ? 's' : ''}
                {hasActiveFilters && ' (filtered)'}
              </p>
            </div>
            
            <div className="w-full sm:w-auto flex flex-col-reverse sm:flex-row items-stretch sm:items-center gap-3">
              {/* Refresh Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={loading}
                className="border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>

              {/* Search and Filter Bar */}
              <div className="w-full sm:w-auto space-y-3">
                <div className="flex flex-col sm:flex-row gap-3 items-center justify-center">
                  {/* Search Input */}
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
                    <Input
                      placeholder="Search projects..."
                      value={filters.search}
                      onChange={(e) => handleFilterChange('search', e.target.value)}
                      className="w-full pl-10 pr-4 h-10 text-sm sm:text-base border-gray-200 focus:border-gray-500 dark:border-gray-600 dark:focus:border-gray-400 bg-white dark:bg-gray-900 text-brand-500 dark:text-gray-100"
                    />
                  </div>

                  {/* Filter Toggle */}
                  <Button
                    variant="outline"
                    onClick={() => setShowFilters(!showFilters)}
                    className={`flex-1 sm:flex-none justify-center border-gray-200 dark:border-gray-600 ${
                      showFilters ? 'bg-gray-50 text-gray-700 border-gray-300 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-500' : 'text-gray-600 dark:text-gray-400'
                    } hover:bg-gray-50 dark:hover:bg-gray-800`}
                  >
                    <Filter className="w-4 h-4 mr-2" />
                    <span className="sm:hidden">Filters</span>
                    {hasActiveFilters && (
                      <Badge variant="secondary" className="ml-2 bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                        {[
                          filters.status !== 'all',
                          filters.step !== 'all',
                          filters.dateRange !== 'all',
                          filters.sortBy !== 'updated_at',
                          filters.sortDirection !== 'desc'
                        ].filter(Boolean).length}
                      </Badge>
                    )}
                  </Button>
                </div>

                {/* Active Filters */}
                {hasActiveFilters && (
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={clearFilters}
                      className="h-8 px-2.5 text-xs sm:text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                      <X className="w-3.5 h-3.5 mr-1.5" />
                      Clear all
                    </Button>
                    {filters.status !== 'all' && (
                      <Badge variant="outline" className="text-xs sm:text-sm border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300">
                        {filters.status}
                      </Badge>
                    )}
                    {filters.step !== 'all' && (
                      <Badge variant="outline" className="text-xs sm:text-sm border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300">
                        {filters.step.replace('_', ' ')}
                      </Badge>
                    )}
                    {filters.dateRange !== 'all' && (
                      <Badge variant="outline" className="text-xs sm:text-sm border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300">
                        {filters.dateRange}
                      </Badge>
                    )}
                  </div>
                )}

                {/* Advanced Filters */}
                <AnimatePresence>
                  {showFilters && (
                    <motion.div
                      initial={{ opacity: 0, height: 0, overflow: 'hidden' }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                        {/* Status Filter */}
                        <div className="space-y-1.5">
                          <label className="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300">Status</label>
                          <Select value={filters.status} onValueChange={(value: StatusFilter) => handleFilterChange('status', value)}>
                            <SelectTrigger className="h-9 text-sm border-gray-200 focus:border-gray-500 dark:border-gray-600 dark:focus:border-gray-400 bg-white dark:bg-gray-900">
                              <SelectValue placeholder="Status" />
                            </SelectTrigger>
                            <SelectContent className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-600">
                              <SelectItem value="all">All Status</SelectItem>
                              <SelectItem value="active">Active</SelectItem>
                              <SelectItem value="completed">Completed</SelectItem>
                              <SelectItem value="paused">Paused</SelectItem>
                              <SelectItem value="archived">Archived</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Step Filter */}
                        <div className="space-y-1.5">
                          <label className="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300">Current Step</label>
                          <Select value={filters.step} onValueChange={(value: StepFilter) => handleFilterChange('step', value)}>
                            <SelectTrigger className="h-9 text-sm border-gray-200 focus:border-gray-500 dark:border-gray-600 dark:focus:border-gray-400 bg-white dark:bg-gray-900">
                              <SelectValue placeholder="Step" />
                            </SelectTrigger>
                            <SelectContent className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-600">
                              <SelectItem value="all">All Steps</SelectItem>
                              <SelectItem value="project_setup">Project Setup</SelectItem>
                              <SelectItem value="vpc_composition">VPC Composition</SelectItem>
                              <SelectItem value="field_prep">Field Prep</SelectItem>
                              <SelectItem value="data_collection">Data Collection</SelectItem>
                              <SelectItem value="analysis">Analysis</SelectItem>
                              <SelectItem value="completed">Completed</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Date Range Filter */}
                        <div className="space-y-1.5">
                          <label className="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300">Updated</label>
                          <Select value={filters.dateRange} onValueChange={(value: FilterState['dateRange']) => handleFilterChange('dateRange', value)}>
                            <SelectTrigger className="h-9 text-sm border-gray-200 focus:border-gray-500 dark:border-gray-600 dark:focus:border-gray-400 bg-white dark:bg-gray-900">
                              <SelectValue placeholder="Date range" />
                            </SelectTrigger>
                            <SelectContent className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-600">
                              <SelectItem value="all">All Time</SelectItem>
                              <SelectItem value="today">Today</SelectItem>
                              <SelectItem value="week">Past Week</SelectItem>
                              <SelectItem value="month">Past Month</SelectItem>
                              <SelectItem value="quarter">Past Quarter</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Sort By */}
                        <div className="space-y-1.5">
                          <label className="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300">Sort By</label>
                          <Select value={filters.sortBy} onValueChange={(value: SortOption) => handleFilterChange('sortBy', value)}>
                            <SelectTrigger className="h-9 text-sm border-gray-200 focus:border-gray-500 dark:border-gray-600 dark:focus:border-gray-400 bg-white dark:bg-gray-900">
                              <SelectValue placeholder="Sort by" />
                            </SelectTrigger>
                            <SelectContent className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-600">
                              <SelectItem value="updated_at">Last Updated</SelectItem>
                              <SelectItem value="created_at">Created Date</SelectItem>
                              <SelectItem value="name">Name</SelectItem>
                              <SelectItem value="progress">Progress</SelectItem>
                              <SelectItem value="status">Status</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Sort Direction */}
                        <div className="space-y-1.5">
                          <label className="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300">Order</label>
                          <Button
                            variant="outline"
                            onClick={() => handleFilterChange('sortDirection', filters.sortDirection === 'asc' ? 'desc' : 'asc')}
                            className="w-full h-9 justify-start text-sm border-gray-200 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
                          >
                            {filters.sortDirection === 'asc' ? (
                              <>
                                <SortAsc className="w-4 h-4 mr-2" />
                                <span className="sm:hidden">A-Z</span>
                                <span className="hidden sm:inline">Ascending</span>
                              </>
                            ) : (
                              <>
                                <SortDesc className="w-4 h-4 mr-2" />
                                <span className="sm:hidden">Z-A</span>
                                <span className="hidden sm:inline">Descending</span>
                              </>
                            )}
                          </Button>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* New Project Button */}
              <Button 
                onClick={handleCreateProject}
                className="w-full sm:w-auto bg-brand-500 hover:bg-brand-600 dark:bg-gray-600 dark:hover:bg-gray-700 text-white shadow-lg hover:shadow-xl transition-all"
              >
                <Plus className="w-4 h-4 mr-2" />
                <span>New Project</span>
              </Button>
            </div>
          </div>

          {/* Results */}
          {filteredAndSortedProjects.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-16 text-center"
            >
              <div className="p-4 rounded-full bg-gray-100 dark:bg-gray-800/50 mb-6">
                <Search className="w-12 h-12 text-gray-400 dark:text-gray-500" />
              </div>
              <h3 className="text-xl font-semibold text-brand-500 dark:text-gray-100 mb-3">No Projects Found</h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md leading-relaxed">
                No projects match your current search and filter criteria. Try adjusting your filters or search terms.
              </p>
              <Button onClick={clearFilters} variant="outline" className="border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800">
                Clear All Filters
              </Button>
            </motion.div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              <AnimatePresence>
                {projectCards}
              </AnimatePresence>
            </div>
          )}
        </div>
      </Card>
    </motion.div>
  );
}