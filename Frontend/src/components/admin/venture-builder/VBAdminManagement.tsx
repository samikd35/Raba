'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Users, DollarSign, RefreshCw, AlertTriangle, Star } from 'lucide-react';
import VBManagementList from './VBManagementList';
import VBDetailEdit from './VBDetailEdit';
import VBEarningsConfigPanel from './VBEarningsConfigPanel';
import VBReconciliationPanel from './VBReconciliationPanel';
import VBDisputesPanel from './VBDisputesPanel';
import VBExpertisePanel from './VBExpertisePanel';

type ViewMode = 'vbs' | 'detail' | 'earnings' | 'reconciliation' | 'disputes' | 'expertise';
type TabType = 'vbs' | 'earnings' | 'reconciliation' | 'disputes' | 'expertise';

const TAB_CONFIG: { id: TabType; label: string; shortLabel: string; icon: React.ElementType; description: string }[] = [
  { id: 'vbs', label: 'Venture Builders', shortLabel: 'VBs', icon: Users, description: 'Manage venture builder profiles and approvals' },
  { id: 'earnings', label: 'Earnings', shortLabel: 'Earnings', icon: DollarSign, description: 'Configure earnings and commission rates' },
  { id: 'reconciliation', label: 'Reconciliation', shortLabel: 'Recon', icon: RefreshCw, description: 'Manage payment reconciliations' },
  { id: 'disputes', label: 'Disputes', shortLabel: 'Disputes', icon: AlertTriangle, description: 'Review and resolve session disputes' },
  { id: 'expertise', label: 'Expertise', shortLabel: 'Expertise', icon: Star, description: 'Manage expertise areas' },
];

export default function VBAdminManagement() {
  const router = useRouter();
  const [viewMode, setViewMode] = useState<ViewMode>('vbs');
  const [selectedVBId, setSelectedVBId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('vbs');

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    setViewMode(tab);
    setSelectedVBId(null);
  };

  const handleBackFromDetail = () => {
    setSelectedVBId(null);
    setViewMode(activeTab);
  };

  const activeTabConfig = TAB_CONFIG.find(t => t.id === activeTab);

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] bg-gray-50 dark:bg-gray-900">
      {/* Header Section */}
      <div className="flex-none bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-theme-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {/* Title and Description */}
          <div className="mb-6">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
              Venture Builder Management
            </h1>
            <p className="mt-1 text-sm sm:text-base text-gray-600 dark:text-gray-400">
              {activeTabConfig?.description}
            </p>
          </div>

          {/* Tab Navigation */}
          <div className="flex gap-1 sm:gap-2 overflow-x-auto pb-1 -mx-4 px-4 sm:mx-0 sm:px-0 scrollbar-hide">
            {TAB_CONFIG.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all duration-200 ${
                    isActive
                      ? 'bg-brand-500 text-white shadow-md'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{tab.label}</span>
                  <span className="sm:hidden">{tab.shortLabel}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
          {viewMode === 'detail' && selectedVBId ? (
            <VBDetailEdit
              vbId={selectedVBId}
              onBack={handleBackFromDetail}
            />
          ) : viewMode === 'vbs' ? (
            <VBManagementList
              onViewEdit={(vbId) => {
                setSelectedVBId(vbId);
                setViewMode('detail');
              }}
            />
          ) : viewMode === 'earnings' ? (
            <VBEarningsConfigPanel />
          ) : viewMode === 'reconciliation' ? (
            <VBReconciliationPanel />
          ) : viewMode === 'disputes' ? (
            <VBDisputesPanel />
          ) : viewMode === 'expertise' ? (
            <VBExpertisePanel />
          ) : null}
        </div>
      </div>
    </div>
  );
}
