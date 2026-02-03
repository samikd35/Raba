"use client";

import React, { useState, useEffect } from 'react';
import { featureService, ModuleFeature, ResolvedFeatureCost, PlanType } from '@/lib/api/featureService';
import { toast } from 'react-hot-toast';
import { Calculator, ArrowRight, Database, Layers, User, Users, Building2, CheckCircle, Info } from 'lucide-react';

const PLAN_TYPES: PlanType[] = ['individual', 'team', 'organization'];

const PlanIcon = ({ planType }: { planType: PlanType }) => {
  switch (planType) {
    case 'organization':
      return <Building2 className="w-5 h-5" />;
    case 'team':
      return <Users className="w-5 h-5" />;
    default:
      return <User className="w-5 h-5" />;
  }
};

export default function ResolveCostPage() {
  const [features, setFeatures] = useState<ModuleFeature[]>([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(false);
  const [selectedFeatureId, setSelectedFeatureId] = useState<string>('');
  const [selectedPlanType, setSelectedPlanType] = useState<PlanType>('individual');
  const [asOfDate, setAsOfDate] = useState<string>('');
  const [result, setResult] = useState<ResolvedFeatureCost | null>(null);
  const [selectedFeature, setSelectedFeature] = useState<ModuleFeature | null>(null);

  useEffect(() => {
    fetchFeatures();
  }, []);

  useEffect(() => {
    if (selectedFeatureId) {
      const feature = features.find(f => f.id === selectedFeatureId);
      setSelectedFeature(feature || null);
    } else {
      setSelectedFeature(null);
    }
    setResult(null);
  }, [selectedFeatureId, features]);

  useEffect(() => {
    setResult(null);
  }, [selectedPlanType, asOfDate]);

  const fetchFeatures = async () => {
    try {
      setLoading(true);
      const data = await featureService.listFeatures({ is_active: true });
      setFeatures(data);
      if (data.length > 0) {
        setSelectedFeatureId(data[0].id);
      }
    } catch (error: any) {
      console.error('Failed to fetch features:', error);
      toast.error(error.message || 'Failed to load features');
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedFeatureId) {
      toast.error('Please select a feature');
      return;
    }

    try {
      setResolving(true);
      const resolved = await featureService.resolveCost(
        selectedFeatureId,
        selectedPlanType,
        asOfDate || undefined
      );
      setResult(resolved);
    } catch (error: any) {
      console.error('Failed to resolve cost:', error);
      toast.error(error.message || 'Failed to resolve cost');
    } finally {
      setResolving(false);
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
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Resolve Feature Cost
        </h2>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Check the effective credit cost for a feature and plan combination
        </p>
      </div>

      {/* Info Card */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex gap-3">
          <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800 dark:text-blue-200">
            <p className="font-medium mb-1">How cost resolution works:</p>
            <ol className="list-decimal list-inside space-y-1 text-blue-700 dark:text-blue-300">
              <li>First, the system checks for an active cost override for the specific feature + plan combination</li>
              <li>If an override exists and is within its effective date range, that cost is used</li>
              <li>If no override exists, the feature's base cost is used as fallback</li>
            </ol>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Form */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Resolution Parameters
          </h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Feature
              </label>
              <select
                value={selectedFeatureId}
                onChange={(e) => setSelectedFeatureId(e.target.value)}
                className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="">Select a feature</option>
                {features.map(feature => (
                  <option key={feature.id} value={feature.id}>
                    {feature.display_name}
                  </option>
                ))}
              </select>
            </div>

            {selectedFeature && (
              <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-md">
                <div className="flex items-center gap-2 mb-2">
                  <Layers className="w-4 h-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {selectedFeature.display_name}
                  </span>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
                  <p>Type: <span className="capitalize">{selectedFeature.feature_type}</span></p>
                  <p>Base Cost: <span className="font-medium">{selectedFeature.credit_cost} credits</span></p>
                  <p>Status: {selectedFeature.is_active ? 'Active' : 'Inactive'}</p>
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Plan Type
              </label>
              <div className="grid grid-cols-3 gap-2">
                {PLAN_TYPES.map(plan => (
                  <button
                    key={plan}
                    type="button"
                    onClick={() => setSelectedPlanType(plan)}
                    className={`flex flex-col items-center gap-1 p-3 rounded-md border transition-colors ${
                      selectedPlanType === plan
                        ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400'
                        : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    <PlanIcon planType={plan} />
                    <span className="text-xs font-medium capitalize">{plan}</span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                As Of Date (optional)
              </label>
              <input
                type="datetime-local"
                value={asOfDate}
                onChange={(e) => setAsOfDate(e.target.value)}
                className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Leave empty to use current time
              </p>
            </div>

            <button
              onClick={handleResolve}
              disabled={!selectedFeatureId || resolving}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {resolving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Resolving...
                </>
              ) : (
                <>
                  <Calculator className="w-4 h-4" />
                  Resolve Cost
                </>
              )}
            </button>
          </div>
        </div>

        {/* Result */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Resolution Result
          </h3>

          {!result ? (
            <div className="flex flex-col items-center justify-center h-64 text-gray-400">
              <Calculator className="w-12 h-12 mb-3" />
              <p className="text-sm">Select parameters and click "Resolve Cost"</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Resolved Cost */}
              <div className="text-center p-6 bg-gradient-to-br from-brand-50 to-purple-50 dark:from-brand-900/20 dark:to-purple-900/20 rounded-lg border border-brand-200 dark:border-brand-800">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Effective Credit Cost</p>
                <p className="text-5xl font-bold text-brand-600 dark:text-brand-400">
                  {result.credit_cost}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">credits</p>
              </div>

              {/* Source */}
              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-md">
                <div className="flex items-center gap-2 mb-3">
                  <Database className="w-4 h-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    Cost Source
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {result.source === 'feature_credit_costs' ? (
                    <>
                      <span className="px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400 rounded">
                        Override
                      </span>
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        Plan-specific pricing applied
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 rounded">
                        Base Cost
                      </span>
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        No override found, using feature default
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Details */}
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Feature ID</span>
                  <span className="text-sm font-mono text-gray-900 dark:text-white">{result.feature_id.slice(0, 8)}...</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Plan Type</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">{result.plan_type}</span>
                </div>
                {result.effective_from && (
                  <div className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Effective From</span>
                    <span className="text-sm text-gray-900 dark:text-white">
                      {new Date(result.effective_from).toLocaleString()}
                    </span>
                  </div>
                )}
                {result.effective_until && (
                  <div className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Effective Until</span>
                    <span className="text-sm text-gray-900 dark:text-white">
                      {new Date(result.effective_until).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>

              {/* Comparison with base cost */}
              {selectedFeature && result.source === 'feature_credit_costs' && (
                <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
                  <div className="flex items-center gap-2 text-green-800 dark:text-green-200">
                    <CheckCircle className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      {result.credit_cost < selectedFeature.credit_cost ? (
                        <>Saving {selectedFeature.credit_cost - result.credit_cost} credits compared to base cost</>
                      ) : result.credit_cost > selectedFeature.credit_cost ? (
                        <>{result.credit_cost - selectedFeature.credit_cost} credits more than base cost</>
                      ) : (
                        <>Same as base cost</>
                      )}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
