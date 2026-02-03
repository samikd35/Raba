'use client';

import React, { useEffect, useState } from 'react';
import { DollarSign, Percent, Loader2, AlertCircle, Save, RefreshCw, Calculator, Info } from 'lucide-react';
import { getEarningsConfig, updateEarningsConfig } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import type { EarningsConfig } from '@/types/ventureBuilder';

export default function VBEarningsConfigPanel() {
  const [config, setConfig] = useState<EarningsConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [creditToUsdRate, setCreditToUsdRate] = useState('1.0');
  const [commissionRate, setCommissionRate] = useState('0.15');

  const loadConfig = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const data = await getEarningsConfig(token);
      setConfig(data);
      setCreditToUsdRate(data.credit_to_usd_rate.toString());
      setCommissionRate(data.commission_rate.toString());
    } catch (error: any) {
      console.error('Error fetching earnings config:', error);
      setError(error.message || 'Failed to load earnings configuration');
      toast.error(error.message || 'Failed to load earnings configuration');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const rate = parseFloat(creditToUsdRate);
      const commission = parseFloat(commissionRate);

      if (isNaN(rate) || rate <= 0) {
        toast.error('Credit to USD rate must be a positive number');
        return;
      }

      if (isNaN(commission) || commission < 0 || commission > 1) {
        toast.error('Commission rate must be between 0 and 1');
        return;
      }

      const updated = await updateEarningsConfig({
        credit_to_usd_rate: rate,
        commission_rate: commission,
      }, token);

      setConfig(updated);
      toast.success('Earnings configuration updated successfully!');
    } catch (error: any) {
      console.error('Error updating earnings config:', error);
      toast.error(error.message || 'Failed to update earnings configuration');
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 dark:border-brand-400 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading earnings configuration...</p>
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
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-error-900 dark:text-error-200 mb-1">
              Error Loading Configuration
            </h3>
            <p className="text-error-700 dark:text-error-300 text-sm mb-4">{error}</p>
            <button
              onClick={loadConfig}
              className="px-4 py-2 bg-error-600 dark:bg-error-500 text-white rounded-lg hover:bg-error-700 dark:hover:bg-error-600 transition-all flex items-center gap-2 text-sm font-medium"
            >
              <RefreshCw className="w-4 h-4" />
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  const grossEarnings = 100 * parseFloat(creditToUsdRate || '1');
  const commissionAmount = grossEarnings * parseFloat(commissionRate || '0.15');
  const netEarnings = grossEarnings - commissionAmount;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
          Earnings Configuration
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Configure credit conversion rate and platform commission
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Form */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-theme-xs overflow-hidden">
          <div className="px-4 sm:px-6 py-4 border-b border-gray-100 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                <DollarSign className="w-4 h-4 text-brand-600 dark:text-brand-400" />
              </div>
              Rate Configuration
            </h3>
          </div>
          <div className="p-4 sm:p-6 space-y-6">
            {/* Credit to USD Rate */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                <span className="flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-gray-400" />
                  Credit to USD Conversion Rate
                </span>
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                How many USD equals 1 credit (e.g., 1.0 means 1 credit = $1.00)
              </p>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={creditToUsdRate}
                  onChange={(e) => setCreditToUsdRate(e.target.value)}
                  className="w-full max-w-[200px] px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                  placeholder="1.0"
                />
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Current: <span className="font-medium text-gray-900 dark:text-white">1 credit = ${config?.credit_to_usd_rate.toFixed(2)}</span>
                </span>
              </div>
            </div>

            {/* Commission Rate */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                <span className="flex items-center gap-2">
                  <Percent className="w-4 h-4 text-gray-400" />
                  Platform Commission Rate
                </span>
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                Platform commission as a decimal (e.g., 0.15 for 15%)
              </p>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={commissionRate}
                  onChange={(e) => setCommissionRate(e.target.value)}
                  className="w-full max-w-[200px] px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                  placeholder="0.15"
                />
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Current: <span className="font-medium text-gray-900 dark:text-white">{((config?.commission_rate || 0) * 100).toFixed(0)}%</span>
                </span>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-gray-100 dark:border-gray-700">
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-theme-sm"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Configuration
                  </>
                )}
              </button>
              <button
                onClick={loadConfig}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className="w-4 h-4" />
                Reset
              </button>
            </div>

            {/* Last Updated */}
            {config?.updated_at && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Last updated: {new Date(config.updated_at).toLocaleString('en-US', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            )}
          </div>
        </div>

        {/* Calculation Preview */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-theme-xs overflow-hidden h-fit">
          <div className="px-4 sm:px-6 py-4 border-b border-gray-100 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-success-100 dark:bg-success-900/30 flex items-center justify-center">
                <Calculator className="w-4 h-4 text-success-600 dark:text-success-400" />
              </div>
              Preview
            </h3>
          </div>
          <div className="p-4 sm:p-6">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-4 flex items-start gap-2">
              <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
              Example calculation for a 100 credit session
            </p>
            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-600 dark:text-gray-400">Session Price</span>
                <span className="font-medium text-gray-900 dark:text-white">100 credits</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-600 dark:text-gray-400">Gross Earnings</span>
                <span className="font-medium text-gray-900 dark:text-white">${grossEarnings.toFixed(2)}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-600 dark:text-gray-400">
                  Commission ({(parseFloat(commissionRate || '0.15') * 100).toFixed(0)}%)
                </span>
                <span className="font-medium text-error-600 dark:text-error-400">-${commissionAmount.toFixed(2)}</span>
              </div>
              <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-gray-900 dark:text-white">Net Earnings</span>
                  <span className="text-lg font-bold text-success-600 dark:text-success-400">${netEarnings.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
