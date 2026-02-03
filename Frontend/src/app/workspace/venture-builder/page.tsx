'use client';

import { useState } from 'react';
import { Calendar, DollarSign } from 'lucide-react';
import VBSettingsDropdown from '@/components/venture-builder/dashboard/VBSettingsDropdown';
import VBSessionsCalendarView from '@/components/venture-builder/dashboard/VBSessionsCalendarView';
import VBEarningsSection from '@/components/venture-builder/dashboard/VBEarningsSection';

type TabType = 'sessions' | 'earnings';

export default function VBDashboardPage() {
  const [activeTab, setActiveTab] = useState<TabType>('sessions');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Venture Builder Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage your coaching sessions and track your earnings
          </p>
        </div>
        <VBSettingsDropdown />
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-8">
          <button
            onClick={() => setActiveTab('sessions')}
            className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'sessions'
                ? 'border-brand-500 text-brand-600 dark:text-brand-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
          >
            <Calendar className="w-4 h-4" />
            Sessions
          </button>
          <button
            onClick={() => setActiveTab('earnings')}
            className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'earnings'
                ? 'border-brand-500 text-brand-600 dark:text-brand-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
          >
            <DollarSign className="w-4 h-4" />
            Earnings
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'sessions' && <VBSessionsCalendarView />}
        {activeTab === 'earnings' && <VBEarningsSection />}
      </div>
    </div>
  );
}
