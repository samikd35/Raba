'use client';

import React, { useEffect, useState } from 'react';
import { Plus, Edit2, Trash2, Save, X, Loader2, AlertCircle, Eye, EyeOff, Star, GripVertical } from 'lucide-react';
import { getAllExpertiseAreasAdmin, createExpertiseArea, updateExpertiseArea, deleteExpertiseArea } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import type { ExpertiseArea, CreateExpertiseAreaPayload, UpdateExpertiseAreaPayload } from '@/types/ventureBuilder';

export default function VBExpertisePanel() {
  const [expertiseAreas, setExpertiseAreas] = useState<ExpertiseArea[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);

  const [formData, setFormData] = useState<CreateExpertiseAreaPayload>({
    name: '',
    description: '',
    display_order: 1,
  });

  const loadExpertiseAreas = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const data = await getAllExpertiseAreasAdmin(token, showInactive);
      setExpertiseAreas(data);
    } catch (error: any) {
      console.error('Error fetching expertise areas:', error);
      setError(error.message || 'Failed to load expertise areas');
      toast.error(error.message || 'Failed to load expertise areas');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadExpertiseAreas();
  }, [showInactive]);

  const handleCreate = async () => {
    try {
      const token = authService.getCurrentToken();
      if (!token) throw new Error('Authentication required');

      if (!formData.name.trim()) {
        toast.error('Name is required');
        return;
      }

      await createExpertiseArea(formData, token);
      toast.success('Expertise area created successfully!');
      setShowAddForm(false);
      setFormData({ name: '', description: '', display_order: 1 });
      loadExpertiseAreas();
    } catch (error: any) {
      console.error('Error creating expertise area:', error);
      toast.error(error.message || 'Failed to create expertise area');
    }
  };

  const handleUpdate = async (id: string, updates: UpdateExpertiseAreaPayload) => {
    try {
      const token = authService.getCurrentToken();
      if (!token) throw new Error('Authentication required');

      await updateExpertiseArea(id, updates, token);
      toast.success('Expertise area updated successfully!');
      setEditingId(null);
      loadExpertiseAreas();
    } catch (error: any) {
      console.error('Error updating expertise area:', error);
      toast.error(error.message || 'Failed to update expertise area');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this expertise area? This action cannot be undone.')) {
      return;
    }

    try {
      const token = authService.getCurrentToken();
      if (!token) throw new Error('Authentication required');

      await deleteExpertiseArea(id, token);
      toast.success('Expertise area deleted successfully!');
      loadExpertiseAreas();
    } catch (error: any) {
      console.error('Error deleting expertise area:', error);
      toast.error(error.message || 'Failed to delete expertise area');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 dark:border-brand-400 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading expertise areas...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-xl">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-full bg-error-100 dark:bg-error-900/30 flex items-center justify-center flex-shrink-0">
            <AlertCircle className="w-5 h-5 text-error-600 dark:text-error-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-error-900 dark:text-error-200 mb-1">
              Error Loading Expertise Areas
            </h3>
            <p className="text-error-700 dark:text-error-300 text-sm">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            Expertise Areas
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Manage expertise categories for venture builders
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <button
            onClick={() => setShowInactive(!showInactive)}
            className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-all shadow-theme-xs"
          >
            {showInactive ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            <span className="hidden sm:inline">{showInactive ? 'Hide Inactive' : 'Show Inactive'}</span>
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium transition-all shadow-theme-sm hover:shadow-theme-md"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">Add Expertise</span>
          </button>
        </div>
      </div>

      {/* Add Form */}
      {showAddForm && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-theme-sm overflow-hidden">
          <div className="px-4 sm:px-6 py-4 border-b border-gray-100 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                <Star className="w-4 h-4 text-brand-600 dark:text-brand-400" />
              </div>
              Add New Expertise Area
            </h3>
          </div>
          <div className="p-4 sm:p-6 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Name <span className="text-error-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
                  placeholder="e.g., Product Strategy"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Display Order
                </label>
                <input
                  type="number"
                  value={formData.display_order}
                  onChange={(e) => setFormData({ ...formData, display_order: parseInt(e.target.value) })}
                  className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
                  min="1"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all resize-none"
                rows={3}
                placeholder="Describe this expertise area..."
              />
            </div>
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                onClick={handleCreate}
                className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium transition-colors"
              >
                <Save className="w-4 h-4" />
                Create
              </button>
              <button
                onClick={() => {
                  setShowAddForm(false);
                  setFormData({ name: '', description: '', display_order: 1 });
                }}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors"
              >
                <X className="w-4 h-4" />
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Expertise Areas List */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-theme-xs overflow-hidden">
        {expertiseAreas.length === 0 ? (
          <div className="text-center py-16 px-4">
            <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <Star className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              No expertise areas found
            </h3>
            <p className="text-gray-600 dark:text-gray-400 max-w-sm mx-auto">
              {showInactive ? 'No expertise areas exist yet' : 'No active expertise areas. Try showing inactive ones.'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {expertiseAreas.map((area) => (
              <div
                key={area.id}
                className="p-4 sm:p-5 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="hidden sm:flex w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-700 items-center justify-center flex-shrink-0 text-gray-400">
                      <GripVertical className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                          {area.name}
                        </h3>
                        <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                          area.is_active
                            ? 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                        }`}>
                          {area.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                          Order: {area.display_order}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {area.description || 'No description provided'}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                        Created {new Date(area.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => handleUpdate(area.id, { is_active: !area.is_active })}
                      className={`p-2 rounded-lg transition-colors ${
                        area.is_active
                          ? 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300 hover:bg-warning-200 dark:hover:bg-warning-900/50'
                          : 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300 hover:bg-success-200 dark:hover:bg-success-900/50'
                      }`}
                      title={area.is_active ? 'Deactivate' : 'Activate'}
                    >
                      {area.is_active ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => handleDelete(area.id)}
                      className="p-2 bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-300 rounded-lg hover:bg-error-200 dark:hover:bg-error-900/50 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
