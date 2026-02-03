"use client";

import React, { useState, useEffect } from 'react';
import { tokenMonitoringService, ModelPricing, CreatePricingRequest } from '@/lib/api/tokenMonitoringService';
import { LoadingState } from '@/components/token-manager/LoadingState';
import { EmptyState } from '@/components/token-manager/EmptyState';
import { Plus, Edit, Trash2, X, DollarSign, CheckCircle, XCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function PricingPage() {
  const [pricings, setPricings] = useState<ModelPricing[]>([]);
  const [filteredPricings, setFilteredPricings] = useState<ModelPricing[]>([]);
  const [loading, setLoading] = useState(true);
  const [providerFilter, setProviderFilter] = useState('all');
  const [activeOnly, setActiveOnly] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingPricing, setEditingPricing] = useState<ModelPricing | null>(null);
  const [submitting, setSubmitting] = useState(false);
  
  const [formData, setFormData] = useState({
    provider: 'openai',
    model_name: '',
    input_price_per_1k_tokens: '',
    output_price_per_1k_tokens: '',
    embedding_price_per_1k_tokens: '',
    currency: 'USD',
    effective_from: new Date().toISOString().split('T')[0],
    effective_to: '',
    notes: '',
  });

  useEffect(() => {
    fetchPricings();
  }, [activeOnly]);

  useEffect(() => {
    // Filter pricings
    let filtered = pricings;
    
    if (providerFilter !== 'all') {
      filtered = filtered.filter(p => p.provider === providerFilter);
    }
    
    setFilteredPricings(filtered);
  }, [providerFilter, pricings]);

  const fetchPricings = async () => {
    try {
      setLoading(true);
      const data = await tokenMonitoringService.listPricing({
        active_only: activeOnly,
      });
      setPricings(data);
      setFilteredPricings(data);
    } catch (error: any) {
      console.error('Failed to fetch pricings:', error);
      toast.error(error.message || 'Failed to load pricing configurations');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (pricing?: ModelPricing) => {
    if (pricing) {
      setEditingPricing(pricing);
      setFormData({
        provider: pricing.provider,
        model_name: pricing.model_name,
        input_price_per_1k_tokens: pricing.input_price_per_1k_tokens,
        output_price_per_1k_tokens: pricing.output_price_per_1k_tokens,
        embedding_price_per_1k_tokens: pricing.embedding_price_per_1k_tokens || '',
        currency: pricing.currency,
        effective_from: pricing.effective_from.split('T')[0],
        effective_to: pricing.effective_to ? pricing.effective_to.split('T')[0] : '',
        notes: pricing.notes || '',
      });
    } else {
      setEditingPricing(null);
      setFormData({
        provider: 'openai',
        model_name: '',
        input_price_per_1k_tokens: '',
        output_price_per_1k_tokens: '',
        embedding_price_per_1k_tokens: '',
        currency: 'USD',
        effective_from: new Date().toISOString().split('T')[0],
        effective_to: '',
        notes: '',
      });
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingPricing(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.model_name || !formData.input_price_per_1k_tokens || !formData.output_price_per_1k_tokens) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setSubmitting(true);
      
      if (editingPricing) {
        // Update existing pricing
        const updated = await tokenMonitoringService.updatePricing(editingPricing.id, {
          input_price_per_1k_tokens: parseFloat(formData.input_price_per_1k_tokens),
          output_price_per_1k_tokens: parseFloat(formData.output_price_per_1k_tokens),
          embedding_price_per_1k_tokens: formData.embedding_price_per_1k_tokens ? parseFloat(formData.embedding_price_per_1k_tokens) : undefined,
          effective_to: formData.effective_to || undefined,
          notes: formData.notes || undefined,
        });
        
        setPricings(prev => prev.map(p => p.id === updated.id ? updated : p));
        toast.success('Pricing updated successfully');
      } else {
        // Create new pricing
        const newPricing: CreatePricingRequest = {
          provider: formData.provider,
          model_name: formData.model_name,
          input_price_per_1k_tokens: parseFloat(formData.input_price_per_1k_tokens),
          output_price_per_1k_tokens: parseFloat(formData.output_price_per_1k_tokens),
          embedding_price_per_1k_tokens: formData.embedding_price_per_1k_tokens ? parseFloat(formData.embedding_price_per_1k_tokens) : undefined,
          currency: formData.currency,
          effective_from: formData.effective_from,
          effective_to: formData.effective_to || undefined,
          notes: formData.notes || undefined,
        };
        
        const created = await tokenMonitoringService.createPricing(newPricing);
        setPricings(prev => [created, ...prev]);
        toast.success('Pricing created successfully');
      }
      
      handleCloseModal();
    } catch (error: any) {
      console.error('Failed to save pricing:', error);
      toast.error(error.message || 'Failed to save pricing');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string, modelName: string) => {
    if (!window.confirm(`Are you sure you want to delete pricing for "${modelName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await tokenMonitoringService.deletePricing(id);
      setPricings(prev => prev.filter(p => p.id !== id));
      toast.success('Pricing deleted successfully');
    } catch (error: any) {
      console.error('Failed to delete pricing:', error);
      toast.error(error.message || 'Failed to delete pricing');
    }
  };

  const uniqueProviders = ['all', ...Array.from(new Set(pricings.map(p => p.provider)))];

  if (loading) {
    return <LoadingState />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            AI Model Pricing
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Manage AI model pricing configurations
          </p>
        </div>
        <button
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add New Pricing
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Provider:
          </label>
          <select
            value={providerFilter}
            onChange={(e) => setProviderFilter(e.target.value)}
            className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {uniqueProviders.map(provider => (
              <option key={provider} value={provider}>
                {provider === 'all' ? 'All Providers' : provider}
              </option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => setActiveOnly(e.target.checked)}
            className="w-4 h-4 text-brand-500 border-gray-300 rounded focus:ring-brand-500"
          />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Active Only
          </span>
        </label>
      </div>

      {/* Table */}
      {filteredPricings.length === 0 ? (
        <EmptyState
          title="No pricing configurations"
          message="There are no pricing configurations matching your filters. Create one to get started."
          action={{
            label: 'Add New Pricing',
            onClick: () => handleOpenModal(),
          }}
        />
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Provider
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Model
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Input Price
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Output Price
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Embedding Price
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Effective From
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {filteredPricings.map((pricing) => (
                  <tr
                    key={pricing.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {pricing.provider}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {pricing.model_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      ${parseFloat(pricing.input_price_per_1k_tokens).toFixed(6)}/1K
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      ${parseFloat(pricing.output_price_per_1k_tokens).toFixed(6)}/1K
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {pricing.embedding_price_per_1k_tokens ? `$${parseFloat(pricing.embedding_price_per_1k_tokens).toFixed(6)}/1K` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {pricing.is_active ? (
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
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {new Date(pricing.effective_from).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-2">
                      <button
                        onClick={() => handleOpenModal(pricing)}
                        className="text-brand-500 hover:text-brand-600 dark:text-brand-400 dark:hover:text-brand-300 font-medium"
                      >
                        <Edit className="w-4 h-4 inline" />
                      </button>
                      <button
                        onClick={() => handleDelete(pricing.id, pricing.model_name)}
                        className="text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300 font-medium"
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
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  {editingPricing ? 'Edit Pricing' : 'Add New Pricing'}
                </h2>
                <button
                  onClick={handleCloseModal}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Provider *
                    </label>
                    <select
                      value={formData.provider}
                      onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                      disabled={!!editingPricing}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
                    >
                      <option value="openai">OpenAI</option>
                      <option value="azure_openai">Azure OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="google">Google</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Model Name *
                    </label>
                    <input
                      type="text"
                      value={formData.model_name}
                      onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                      disabled={!!editingPricing}
                      placeholder="gpt-4o"
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Input Price per 1K Tokens * ($)
                    </label>
                    <input
                      type="number"
                      step="0.000001"
                      value={formData.input_price_per_1k_tokens}
                      onChange={(e) => setFormData({ ...formData, input_price_per_1k_tokens: e.target.value })}
                      placeholder="0.005"
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Output Price per 1K Tokens * ($)
                    </label>
                    <input
                      type="number"
                      step="0.000001"
                      value={formData.output_price_per_1k_tokens}
                      onChange={(e) => setFormData({ ...formData, output_price_per_1k_tokens: e.target.value })}
                      placeholder="0.015"
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Embedding Price per 1K Tokens ($)
                  </label>
                  <input
                    type="number"
                    step="0.000001"
                    value={formData.embedding_price_per_1k_tokens}
                    onChange={(e) => setFormData({ ...formData, embedding_price_per_1k_tokens: e.target.value })}
                    placeholder="0.0001"
                    className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Effective From *
                    </label>
                    <input
                      type="date"
                      value={formData.effective_from}
                      onChange={(e) => setFormData({ ...formData, effective_from: e.target.value })}
                      disabled={!!editingPricing}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Effective To
                    </label>
                    <input
                      type="date"
                      value={formData.effective_to}
                      onChange={(e) => setFormData({ ...formData, effective_to: e.target.value })}
                      min={formData.effective_from}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Notes
                  </label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={3}
                    placeholder="Optional notes about this pricing configuration"
                    className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
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
                    {submitting ? 'Saving...' : (editingPricing ? 'Update Pricing' : 'Create Pricing')}
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
