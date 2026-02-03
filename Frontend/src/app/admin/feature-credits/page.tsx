"use client";

import React, { useState, useEffect } from 'react';
import { featureService, ModuleFeature, FeatureCreditCost } from '@/lib/api/featureService';
import { toast } from 'react-hot-toast';
import { Layers, DollarSign, CheckCircle, XCircle, Zap, Users, Building2, User } from 'lucide-react';
import Link from 'next/link';

interface FeatureStats {
  total: number;
  active: number;
  inactive: number;
  byType: Record<string, number>;
}

interface CostStats {
  total: number;
  active: number;
  byPlan: Record<string, number>;
}

export default function FeatureCreditsOverview() {
  const [features, setFeatures] = useState<ModuleFeature[]>([]);
  const [creditCosts, setCreditCosts] = useState<FeatureCreditCost[]>([]);
  const [loading, setLoading] = useState(true);
  const [featureStats, setFeatureStats] = useState<FeatureStats>({
    total: 0,
    active: 0,
    inactive: 0,
    byType: {},
  });
  const [costStats, setCostStats] = useState<CostStats>({
    total: 0,
    active: 0,
    byPlan: {},
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [featuresData, costsData] = await Promise.all([
        featureService.listFeatures(),
        featureService.listCreditCosts(),
      ]);

      setFeatures(featuresData);
      setCreditCosts(costsData);

      // Calculate feature stats
      const fStats: FeatureStats = {
        total: featuresData.length,
        active: featuresData.filter(f => f.is_active).length,
        inactive: featuresData.filter(f => !f.is_active).length,
        byType: {},
      };
      featuresData.forEach(f => {
        fStats.byType[f.feature_type] = (fStats.byType[f.feature_type] || 0) + 1;
      });
      setFeatureStats(fStats);

      // Calculate cost stats
      const cStats: CostStats = {
        total: costsData.length,
        active: costsData.filter(c => c.is_active).length,
        byPlan: {},
      };
      costsData.forEach(c => {
        cStats.byPlan[c.plan_type] = (cStats.byPlan[c.plan_type] || 0) + 1;
      });
      setCostStats(cStats);
    } catch (error: any) {
      console.error('Failed to fetch data:', error);
      toast.error(error.message || 'Failed to load feature data');
    } finally {
      setLoading(false);
    }
  };

  const MetricCard = ({
    title,
    value,
    subtitle,
    icon: Icon,
    iconColor,
  }: {
    title: string;
    value: string | number;
    subtitle: string;
    icon: React.ElementType;
    iconColor: string;
  }) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">{value}</p>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>
        </div>
        <div className={`p-3 rounded-full bg-gray-100 dark:bg-gray-700 ${iconColor}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Features"
          value={featureStats.total}
          subtitle="Module features defined"
          icon={Layers}
          iconColor="text-blue-500"
        />
        <MetricCard
          title="Active Features"
          value={featureStats.active}
          subtitle={`${featureStats.inactive} inactive`}
          icon={CheckCircle}
          iconColor="text-green-500"
        />
        <MetricCard
          title="Cost Overrides"
          value={costStats.total}
          subtitle={`${costStats.active} active`}
          icon={DollarSign}
          iconColor="text-purple-500"
        />
        <MetricCard
          title="Plan Types"
          value={Object.keys(costStats.byPlan).length}
          subtitle="With custom pricing"
          icon={Users}
          iconColor="text-amber-500"
        />
      </div>

      {/* Feature Types Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Features by Type
          </h3>
          <div className="space-y-4">
            {Object.entries(featureStats.byType).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Zap className="w-5 h-5 text-gray-400" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                    {type}
                  </span>
                </div>
                <span className="px-3 py-1 text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-full">
                  {count}
                </span>
              </div>
            ))}
            {Object.keys(featureStats.byType).length === 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400">No features created yet</p>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Cost Overrides by Plan
          </h3>
          <div className="space-y-4">
            {Object.entries(costStats.byPlan).map(([plan, count]) => {
              const Icon = plan === 'organization' ? Building2 : plan === 'team' ? Users : User;
              return (
                <div key={plan} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Icon className="w-5 h-5 text-gray-400" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                      {plan}
                    </span>
                  </div>
                  <span className="px-3 py-1 text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-full">
                    {count}
                  </span>
                </div>
              );
            })}
            {Object.keys(costStats.byPlan).length === 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400">No cost overrides created yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/admin/feature-credits/features"
          className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
        >
          <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
            Manage Features
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Create, edit, and toggle module features
          </p>
        </Link>

        <Link
          href="/admin/feature-credits/credit-costs"
          className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
        >
          <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
            Manage Credit Costs
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Set plan-specific pricing overrides
          </p>
        </Link>

        <Link
          href="/admin/feature-credits/resolve"
          className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
        >
          <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
            Resolve Cost
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Check effective cost for feature + plan
          </p>
        </Link>
      </div>

      {/* Recent Features Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Features
            </h3>
            <Link
              href="/admin/feature-credits/features"
              className="text-sm text-brand-500 hover:text-brand-600 font-medium"
            >
              View All →
            </Link>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Name
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
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {features.slice(0, 5).map((feature) => (
                <tr key={feature.id} className="hover:bg-gray-50 dark:hover:bg-gray-900">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {feature.display_name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {feature.name}
                      </p>
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
                </tr>
              ))}
              {features.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                    No features created yet.{' '}
                    <Link href="/admin/feature-credits/features" className="text-brand-500 hover:underline">
                      Create your first feature
                    </Link>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
