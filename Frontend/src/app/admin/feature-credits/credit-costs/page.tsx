"use client";

import React, { useState, useEffect } from 'react';
import { featureService, ModuleFeature, FeatureCreditCost, CreateCreditCostRequest, PlanType } from '@/lib/api/featureService';
import { toast } from 'react-hot-toast';
import { Plus, Edit, Trash2, X, CheckCircle, XCircle, Search, Power, User, Users, Building2 } from 'lucide-react';

const PLAN_TYPES: PlanType[] = ['individual', 'team', 'organization'];

const PlanIcon = ({ planType }: { planType: PlanType }) => {
  switch (planType) {
    case 'organization':
      return <Building2 className="w-4 h-4" />;
    case 'team':
      return <Users className="w-4 h-4" />;
    default:
      return <User className="w-4 h-4" />;
  }
};

export default function CreditCostsPage() {
  const [creditCosts, setCreditCosts] = useState<FeatureCreditCost[]>([]);
  const [features, setFeatures] = useState<ModuleFeature[]>([]);
  const [filteredCosts, setFilteredCosts] = useState<FeatureCreditCost[]>([]);
  const [loading, setLoading] = useState(true);
  const [featureFilter, setFeatureFilter] = useState<string>('all');
  const [planFilter, setPlanFilter] = useState<string>('all');
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [showModal, setShowModal] = useState(false);
  const [editingCost, setEditingCost] = useState<FeatureCreditCost | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    feature_id: '',
    plan_type: 'individual' as PlanType,
    credit_cost: 0,
    is_active: true,
    effective_from: new Date().toISOString().split('T')[0],
    effective_until: '',
  });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    filterCosts();
  }, [featureFilter, planFilter, activeFilter, creditCosts]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [costsData, featuresData] = await Promise.all([
        featureService.listCreditCosts(),
        featureService.listFeatures(),
      ]);
      setCreditCosts(costsData);
      setFilteredCosts(costsData);
      setFeatures(featuresData);
    } catch (error: any) {
      console.error('Failed to fetch data:', error);
      toast.error(error.message || 'Failed to load credit costs');
    } finally {
      setLoading(false);
    }
  };

  const filterCosts = () => {
    let filtered = creditCosts;

    if (featureFilter !== 'all') {
      filtered = filtered.filter(c => c.feature_id === featureFilter);
    }

    if (planFilter !== 'all') {
      filtered = filtered.filter(c => c.plan_type === planFilter);
    }

    if (activeFilter !== 'all') {
      filtered = filtered.filter(c => c.is_active === (activeFilter === 'active'));
    }

    setFilteredCosts(filtered);
  };

  const getFeatureName = (featureId: string): string => {
    const feature = features.find(f => f.id === featureId);
    return feature?.display_name || feature?.name || featureId;
  };

  const getFeatureBaseCost = (featureId: string): number => {
    const feature = features.find(f => f.id === featureId);
    return feature?.credit_cost || 0;
  };

  const handleOpenModal = (cost?: FeatureCreditCost) => {
    if (cost) {
      setEditingCost(cost);
      setFormData({
        feature_id: cost.feature_id,
        plan_type: cost.plan_type,
        credit_cost: cost.credit_cost,
        is_active: cost.is_active,
        effective_from: cost.effective_from.split('T')[0],
        effective_until: cost.effective_until ? cost.effective_until.split('T')[0] : '',
      });
    } else {
      setEditingCost(null);
      setFormData({
        feature_id: features.length > 0 ? features[0].id : '',
        plan_type: 'individual',
        credit_cost: 0,
        is_active: true,
        effective_from: new Date().toISOString().split('T')[0],
        effective_until: '',
      });
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingCost(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.feature_id) {
      toast.error('Please select a feature');
      return;
    }

    try {
      setSubmitting(true);

      if (editingCost) {
        const updated = await featureService.updateCreditCost(editingCost.id, {
          plan_type: formData.plan_type,
          credit_cost: formData.credit_cost,
          is_active: formData.is_active,
          effective_from: formData.effective_from,
          effective_until: formData.effective_until || undefined,
        });
        setCreditCosts(prev => prev.map(c => (c.id === updated.id ? updated : c)));
        toast.success('Credit cost updated successfully');
      } else {
        const created = await featureService.createCreditCost({
          feature_id: formData.feature_id,
          plan_type: formData.plan_type,
          credit_cost: formData.credit_cost,
          is_active: formData.is_active,
          effective_from: formData.effective_from,
          effective_until: formData.effective_until || undefined,
        });
        setCreditCosts(prev => [created, ...prev]);
        toast.success('Credit cost created successfully');
      }

      handleCloseModal();
    } catch (error: any) {
      console.error('Failed to save credit cost:', error);
      toast.error(error.message || 'Failed to save credit cost');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this credit cost override? This action cannot be undone.')) {
      return;
    }

    try {
      await featureService.deleteCreditCost(id);
      setCreditCosts(prev => prev.filter(c => c.id !== id));
      toast.success('Credit cost deleted successfully');
    } catch (error: any) {
      console.error('Failed to delete credit cost:', error);
      toast.error(error.message || 'Failed to delete credit cost');
    }
  };

  const handleToggle = async (cost: FeatureCreditCost) => {
    try {
      const updated = await featureService.toggleCreditCost(cost.id, !cost.is_active);
      setCreditCosts(prev => prev.map(c => (c.id === updated.id ? updated : c)));
      toast.success(`Credit cost ${updated.is_active ? 'activated' : 'deactivated'} successfully`);
    } catch (error: any) {
      console.error('Failed to toggle credit cost:', error);
      toast.error(error.message || 'Failed to toggle credit cost');
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
            Credit Cost Overrides
          </h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            {filteredCosts.length} of {creditCosts.length} cost overrides
          </p>
        </div>
        <button
          onClick={() => handleOpenModal()}
          disabled={features.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="w-4 h-4" />
          Add Cost Override
        </button>
      </div>

      {features.length === 0 && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
          <p className="text-sm text-amber-800 dark:text-amber-200">
            No features exist yet. Please <a href="/admin/feature-credits/features" className="underline font-medium">create a feature</a> first before adding cost overrides.
          </p>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <select
          value={featureFilter}
          onChange={(e) => setFeatureFilter(e.target.value)}
          className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="all">All Features</option>
          {features.map(feature => (
            <option key={feature.id} value={feature.id}>
              {feature.display_name}
            </option>
          ))}
        </select>

        <select
          value={planFilter}
          onChange={(e) => setPlanFilter(e.target.value)}
          className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="all">All Plans</option>
          {PLAN_TYPES.map(plan => (
            <option key={plan} value={plan}>
              {plan.charAt(0).toUpperCase() + plan.slice(1)}
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
      {filteredCosts.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            {creditCosts.length === 0 ? 'No cost overrides created yet.' : 'No cost overrides match your filters.'}
          </p>
          {creditCosts.length === 0 && features.length > 0 && (
            <button
              onClick={() => handleOpenModal()}
              className="mt-4 text-brand-500 hover:text-brand-600 font-medium"
            >
              Create your first cost override
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
                    Plan Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Override Cost
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Base Cost
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Effective Period
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {filteredCosts.map((cost) => {
                  const baseCost = getFeatureBaseCost(cost.feature_id);
                  const savings = baseCost - cost.credit_cost;
                  
                  return (
                    <tr key={cost.id} className="hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {getFeatureName(cost.feature_id)}
                        </p>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400 rounded capitalize">
                          <PlanIcon planType={cost.plan_type} />
                          {cost.plan_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {cost.credit_cost} credits
                        </span>
                        {savings > 0 && (
                          <span className="ml-2 text-xs text-green-600 dark:text-green-400">
                            (-{savings})
                          </span>
                        )}
                        {savings < 0 && (
                          <span className="ml-2 text-xs text-red-600 dark:text-red-400">
                            (+{Math.abs(savings)})
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {baseCost} credits
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        <div>
                          <p>From: {new Date(cost.effective_from).toLocaleDateString()}</p>
                          {cost.effective_until && (
                            <p>Until: {new Date(cost.effective_until).toLocaleDateString()}</p>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {cost.is_active ? (
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
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-2">
                        <button
                          onClick={() => handleToggle(cost)}
                          className={`${
                            cost.is_active
                              ? 'text-amber-500 hover:text-amber-600'
                              : 'text-green-500 hover:text-green-600'
                          } font-medium`}
                          title={cost.is_active ? 'Deactivate' : 'Activate'}
                        >
                          <Power className="w-4 h-4 inline" />
                        </button>
                        <button
                          onClick={() => handleOpenModal(cost)}
                          className="text-brand-500 hover:text-brand-600 dark:text-brand-400 dark:hover:text-brand-300 font-medium"
                          title="Edit"
                        >
                          <Edit className="w-4 h-4 inline" />
                        </button>
                        <button
                          onClick={() => handleDelete(cost.id)}
                          className="text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300 font-medium"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4 inline" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
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
                  {editingCost ? 'Edit Cost Override' : 'Add Cost Override'}
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
                    Feature *
                  </label>
                  <select
                    value={formData.feature_id}
                    onChange={(e) => setFormData({ ...formData, feature_id: e.target.value })}
                    disabled={!!editingCost}
                    className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
                  >
                    <option value="">Select a feature</option>
                    {features.map(feature => (
                      <option key={feature.id} value={feature.id}>
                        {feature.display_name} (Base: {feature.credit_cost} credits)
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Plan Type *
                    </label>
                    <select
                      value={formData.plan_type}
                      onChange={(e) => setFormData({ ...formData, plan_type: e.target.value as PlanType })}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    >
                      {PLAN_TYPES.map(plan => (
                        <option key={plan} value={plan}>
                          {plan.charAt(0).toUpperCase() + plan.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Credit Cost *
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={formData.credit_cost}
                      onChange={(e) => setFormData({ ...formData, credit_cost: parseInt(e.target.value) || 0 })}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Use 0 for free access</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Effective From *
                    </label>
                    <input
                      type="date"
                      value={formData.effective_from}
                      onChange={(e) => setFormData({ ...formData, effective_from: e.target.value })}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Effective Until
                    </label>
                    <input
                      type="date"
                      value={formData.effective_until}
                      onChange={(e) => setFormData({ ...formData, effective_until: e.target.value })}
                      min={formData.effective_from}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Leave empty for indefinite</p>
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
                    Active (override is in effect)
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
                    {submitting ? 'Saving...' : editingCost ? 'Update Cost Override' : 'Create Cost Override'}
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
