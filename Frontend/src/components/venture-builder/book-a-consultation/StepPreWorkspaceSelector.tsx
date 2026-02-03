'use client';

import React, { useState, useEffect } from 'react';
import { Building2, CheckCircle2 } from 'lucide-react';

interface Workspace {
  id: string;
  name: string;
  tenant_id: string;
}

interface StepPreWorkspaceSelectorProps {
  onWorkspaceSelected: (tenantId: string, workspaceName: string) => void;
}

export default function StepPreWorkspaceSelector({ onWorkspaceSelected }: StepPreWorkspaceSelectorProps) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // TODO: Fetch user's workspaces from API
    // For now, using mock data
    const fetchWorkspaces = async () => {
      try {
        setIsLoading(true);
        // Mock workspaces - replace with actual API call
        const mockWorkspaces: Workspace[] = [
          { id: '1', name: 'My Primary Workspace', tenant_id: 'tenant-1' },
          { id: '2', name: 'Startup Ventures', tenant_id: 'tenant-2' },
        ];
        setWorkspaces(mockWorkspaces);
      } catch (error) {
        console.error('Error fetching workspaces:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchWorkspaces();
  }, []);

  const handleSelectWorkspace = (workspace: Workspace) => {
    setSelectedWorkspace(workspace.id);
    onWorkspaceSelected(workspace.tenant_id, workspace.name);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Select Workspace
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Loading your workspaces...
          </p>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 dark:border-brand-400"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Select Workspace
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Choose the workspace where you want to book this session.
        </p>
      </div>

      {workspaces.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="w-16 h-16 bg-brand-100 dark:bg-brand-800/50 rounded-full flex items-center justify-center mb-4">
            <Building2 className="w-8 h-8 text-brand-500 dark:text-brand-400" />
          </div>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            No workspaces found. Please create a workspace to continue.
          </p>
          <button className="px-6 py-3 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium transition-colors">
            Create Workspace
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {workspaces.map((workspace) => (
            <button
              key={workspace.id}
              onClick={() => handleSelectWorkspace(workspace)}
              className={`group relative p-6 rounded-xl border-2 transition-all duration-200 text-left ${
                selectedWorkspace === workspace.id
                  ? 'border-brand-500 dark:border-brand-400 bg-brand-50 dark:bg-brand-900/20 shadow-md'
                  : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-sm'
              }`}
            >
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  selectedWorkspace === workspace.id
                    ? 'bg-brand-500 dark:bg-brand-600'
                    : 'bg-brand-100 dark:bg-brand-800/50'
                }`}>
                  <Building2 className={`w-6 h-6 ${
                    selectedWorkspace === workspace.id
                      ? 'text-white'
                      : 'text-brand-500 dark:text-brand-400'
                  }`} />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className={`text-lg font-semibold mb-1 ${
                    selectedWorkspace === workspace.id
                      ? 'text-brand-700 dark:text-brand-200'
                      : 'text-gray-900 dark:text-white'
                  }`}>
                    {workspace.name}
                  </h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Tenant ID: {workspace.tenant_id}
                  </p>
                </div>
                {selectedWorkspace === workspace.id && (
                  <CheckCircle2 className="w-6 h-6 text-brand-500 dark:text-brand-400 flex-shrink-0" />
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {selectedWorkspace && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg">
          <p className="text-sm text-green-800 dark:text-green-300">
            <strong>Selected:</strong> {workspaces.find(w => w.id === selectedWorkspace)?.name}
          </p>
        </div>
      )}
    </div>
  );
}
