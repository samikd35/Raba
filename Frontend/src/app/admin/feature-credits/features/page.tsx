"use client";

import React, { useState, useEffect } from 'react';
import { featureService, ModuleFeature, CreateFeatureRequest, FeatureType } from '@/lib/api/featureService';
import { toast } from 'react-hot-toast';
import { Plus, Edit, Trash2, X, CheckCircle, XCircle, Search, Power } from 'lucide-react';

const FEATURE_TYPES: FeatureType[] = ['generator', 'analyzer', 'validator', 'reporter'];

export default function FeaturesPage() {
  const [features, setFeatures] = useState<ModuleFeature[]>([]);
  const [filteredFeatures, setFilteredFeatures] = useState<ModuleFeature[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [showModal, setShowModal] = useState(false);
  const [editingFeature, setEditingFeature] = useState<ModuleFeature | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    feature_type: 'generator' as FeatureType,
    credit_cost: 1,
    is_active: true,
  });

  useEffect(() => {
    fetchFeatures();
  }, []);

  useEffect(() => {
    filterFeatures();
  }, [searchTerm, typeFilter, activeFilter, features]);

  const fetchFeatures = async () => {
    try {
      setLoading(true);
      const data = await featureService.listFeatures();
      setFeatures(data);
      setFilteredFeatures(data);
    } catch (error: any) {
      console.error('Failed to fetch features:', error);
      toast.error(error.message || 'Failed to load features');
    } finally {
      setLoading(false);
    }
  };

  const filterFeatures = () => {
    let filtered = features;

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        f =>
          f.name.toLowerCase().includes(term) ||
          f.display_name.toLowerCase().includes(term) ||
          f.description?.toLowerCase().includes(term)
      );
    }

    if (typeFilter !== 'all') {
      filtered = filtered.filter(f => f.feature_type === typeFilter);
    }

    if (activeFilter !== 'all') {
      filtered = filtered.filter(f => f.is_active === (activeFilter === 'active'));
    }

    setFilteredFeatures(filtered);
  };

  const handleOpenModal = (feature?: ModuleFeature) => {
    if (feature) {
      setEditingFeature(feature);
      setFormData({
        name: feature.name,
        display_name: feature.display_name,
        description: feature.description || '',
        feature_type: feature.feature_type,
        credit_cost: feature.credit_cost,
        is_active: feature.is_active,
      });
    } else {
      setEditingFeature(null);
      setFormData({
        name: '',
        display_name: '',
        description: '',
        feature_type: 'generator',
        credit_cost: 1,
        is_active: true,
      });
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingFeature(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name || !formData.display_name) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setSubmitting(true);

      if (editingFeature) {
        const updated = await featureService.updateFeature(editingFeature.id, {
          display_name: formData.display_name,
          description: formData.description || undefined,
          feature_type: formData.feature_type,
          credit_cost: formData.credit_cost,
          is_active: formData.is_active,
        });
        setFeatures(prev => prev.map(f => (f.id === updated.id ? updated : f)));
        toast.success('Feature updated successfully');
      } else {
        const created = await featureService.createFeature({
          name: formData.name,
          display_name: formData.display_name,
          description: formData.description || undefined,
          feature_type: formData.feature_type,
          credit_cost: formData.credit_cost,
          is_active: formData.is_active,
        });
        setFeatures(prev => [created, ...prev]);
        toast.success('Feature created successfully');
      }

      handleCloseModal();
    } catch (error: any) {
      console.error('Failed to save feature:', error);
      toast.error(error.message || 'Failed to save feature');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete "${name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await featureService.deleteFeature(id);
      setFeatures(prev => prev.filter(f => f.id !== id));
      toast.success('Feature deleted successfully');
    } catch (error: any) {
      console.error('Failed to delete feature:', error);
      toast.error(error.message || 'Failed to delete feature');
    }
  };

  const handleToggle = async (feature: ModuleFeature) => {
    try {
      const updated = await featureService.toggleFeature(feature.id, !feature.is_active);
      setFeatures(prev => prev.map(f => (f.id === updated.id ? updated : f)));
      toast.success(`Feature ${updated.is_active ? 'activated' : 'deactivated'} successfully`);
    } catch (error: any) {
      console.error('Failed to toggle feature:', error);
      toast.error(error.message || 'Failed to toggle feature');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Module Features
          </h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            {filteredFeatures.length} of {features.length} features
          </p>
        </div>
        <button
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Feature
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search features..."
            className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="all">All Types</option>
          {FEATURE_TYPES.map(type => (
            <option key={type} value={type} className="capitalize">
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </option>
          ))}
        </select>

        <select
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value)}
          className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="all">All Status</option>
          <option value="active">Active Only</option>
          <option value="inactive">Inactive Only</option>
        </select>
      </div>

      {/* Table */}
      {filteredFeatures.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            {features.length === 0 ? 'No features created yet.' : 'No features match your filters.'}
          </p>
          {features.length === 0 && (
            <button
              onClick={() => handleOpenModal()}
              className="mt-4 text-brand-500 hover:text-brand-600 font-medium"
            >
              Create your first feature
            </button>
          )}
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Feature
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Base Cost
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {filteredFeatures.map((feature) => (
                  <tr key={feature.id} className="hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {feature.display_name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                          {feature.name}
                        </p>
                        {feature.description && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-xs truncate">
                            {feature.description}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 rounded capitalize">
                        {feature.feature_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {feature.credit_cost} credits
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {feature.is_active ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                          <CheckCircle className="w-3 h-3" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400">
                          <XCircle className="w-3 h-3" />
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {new Date(feature.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-2">
                      <button
                        onClick={() => handleToggle(feature)}
                        className={`${
                          feature.is_active
                            ? 'text-amber-500 hover:text-amber-600'
                            : 'text-green-500 hover:text-green-600'
                        } font-medium`}
                        title={feature.is_active ? 'Deactivate' : 'Activate'}
                      >
                        <Power className="w-4 h-4 inline" />
                      </button>
                      <button
                        onClick={() => handleOpenModal(feature)}
                        className="text-brand-500 hover:text-brand-600 dark:text-brand-400 dark:hover:text-brand-300 font-medium"
                        title="Edit"
                      >
                        <Edit className="w-4 h-4 inline" />
                      </button>
                      <button
                        onClick={() => handleDelete(feature.id, feature.display_name)}
                        className="text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300 font-medium"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4 inline" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  {editingFeature ? 'Edit Feature' : 'Add New Feature'}
                </h2>
                <button
                  onClick={handleCloseModal}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Name (slug) *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
                    disabled={!!editingFeature}
                    placeholder="problem_generator"
                    className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50 font-mono"
                  />
                  <p className="text-xs text-gray-500 mt-1">Unique identifier, cannot be changed after creation</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Display Name *
                  </label>
                  <input
                    type="text"
                    value={formData.display_name}
                    onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                    placeholder="Problem Generator"
                    className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                    placeholder="Generates problem statements from user input..."
                    className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Feature Type *
                    </label>
                    <select
                      value={formData.feature_type}
                      onChange={(e) => setFormData({ ...formData, feature_type: e.target.value as FeatureType })}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    >
                      {FEATURE_TYPES.map(type => (
                        <option key={type} value={type}>
                          {type.charAt(0).toUpperCase() + type.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Base Credit Cost *
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={formData.credit_cost}
                      onChange={(e) => setFormData({ ...formData, credit_cost: parseInt(e.target.value) || 1 })}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="w-4 h-4 text-brand-500 border-gray-300 rounded focus:ring-brand-500"
                  />
                  <label htmlFor="is_active" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Active (feature is available for use)
                  </label>
                </div>

                <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <button
                    type="button"
                    onClick={handleCloseModal}
                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 text-sm font-medium text-white bg-brand-500 rounded-md hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {submitting ? 'Saving...' : editingFeature ? 'Update Feature' : 'Create Feature'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
