'use client';

import React, { useEffect, useState } from 'react';
import { Briefcase, CheckCircle2, Plus, ArrowRight } from 'lucide-react';
import { fetchTenantProjects } from '@/lib/api/venture-builder';
import { TenantProject } from '@/types/ventureBuilder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import { useRouter } from 'next/navigation';

interface Step1SelectProjectProps {
  selectedProjectId: string;
  onSelectProject: (projectId: string, projectName: string, tenantId: string) => void;
}

export default function Step1SelectProject({ selectedProjectId, onSelectProject }: Step1SelectProjectProps) {
  const router = useRouter();
  const [projects, setProjects] = useState<TenantProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setIsLoading(true);
        const token = authService.getCurrentToken();
        if (!token) {
          throw new Error('Authentication required');
        }
        const projectsData = await fetchTenantProjects(token);
        console.log('Step1SelectProject - Raw projects data:', projectsData);

        // Handle wrapped response format
        const projects = Array.isArray(projectsData) ? projectsData : (projectsData as any)?.data || [];
        console.log('Step1SelectProject - Extracted projects:', projects);

        setProjects(projects);
      } catch (error: any) {
        console.error('Error fetching projects:', error);
        toast.error(error.message || 'Failed to load projects');
        setProjects([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProjects();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Select Project
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Loading your projects...
          </p>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 dark:border-brand-400"></div>
        </div>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Select Project
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            No projects found in your workspace.
          </p>
        </div>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="w-16 h-16 bg-brand-100 dark:bg-brand-800/50 rounded-full flex items-center justify-center mb-4">
            <Briefcase className="w-8 h-8 text-brand-500 dark:text-brand-400" />
          </div>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            You need to create a project first before booking a session.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-3 w-full max-w-md">
            <button
              onClick={() => router.push('/problem-validator/results')}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium transition-colors"
            >
              <Plus className="w-5 h-5" />
              Create a Project
            </button>
            <button
              onClick={() => {
                // TODO: Implement workspace change functionality
                toast.info('Workspace selector coming soon');
              }}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <ArrowRight className="w-5 h-5" />
              Change Workspace
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Select Project
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Choose the project you'd like to discuss during this session.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {projects.map((project) => (
          <button
            key={project.id}
            onClick={() => onSelectProject(project.id, project.name, project.tenant_id)}
            className={`group relative p-6 rounded-xl border-2 transition-all duration-200 text-left ${
              selectedProjectId === project.id
                ? 'border-brand-500 dark:border-brand-400 bg-brand-50 dark:bg-brand-900/20 shadow-md'
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-sm'
            }`}
          >
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 ${
                selectedProjectId === project.id
                  ? 'bg-brand-500 dark:bg-brand-600'
                  : 'bg-brand-100 dark:bg-brand-800/50'
              }`}>
                <Briefcase className={`w-6 h-6 ${
                  selectedProjectId === project.id
                    ? 'text-white'
                    : 'text-brand-500 dark:text-brand-400'
                }`} />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className={`text-lg font-semibold mb-1 ${
                  selectedProjectId === project.id
                    ? 'text-brand-700 dark:text-brand-200'
                    : 'text-gray-900 dark:text-white'
                }`}>
                  {project.name}
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Project ID: {project.id.substring(0, 8)}...
                </p>
              </div>
              {selectedProjectId === project.id && (
                <CheckCircle2 className="w-6 h-6 text-brand-500 dark:text-brand-400 flex-shrink-0" />
              )}
            </div>
          </button>
        ))}
      </div>

      {selectedProjectId && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg">
          <p className="text-sm text-green-800 dark:text-green-300">
            <strong>Selected:</strong> {projects.find(p => p.id === selectedProjectId)?.name}
          </p>
        </div>
      )}
    </div>
  );
}
