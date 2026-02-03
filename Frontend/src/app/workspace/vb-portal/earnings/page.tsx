'use client';

import VBEarningsDashboard from '@/components/venture-builder/earnings/VBEarningsDashboard';

export default function VBPortalEarningsPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <VBEarningsDashboard />
      </div>
    </div>
  );
}
