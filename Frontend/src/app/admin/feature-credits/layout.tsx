"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Layers, DollarSign, Calculator } from 'lucide-react';

const tabs = [
  {
    name: 'Overview',
    href: '/admin/feature-credits',
    icon: LayoutDashboard,
  },
  {
    name: 'Features',
    href: '/admin/feature-credits/features',
    icon: Layers,
  },
  {
    name: 'Credit Costs',
    href: '/admin/feature-credits/credit-costs',
    icon: DollarSign,
  },
  {
    name: 'Resolve Cost',
    href: '/admin/feature-credits/resolve',
    icon: Calculator,
  },
];

export default function FeatureCreditsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Feature Credit Management
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Manage module features and their credit costs across different plan types
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const isActive = tab.href === '/admin/feature-credits'
              ? pathname === tab.href
              : pathname.startsWith(tab.href);

            return (
              <Link
                key={tab.name}
                href={tab.href}
                className={`flex items-center gap-2 py-4 px-1 border-b-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'border-brand-500 text-brand-600 dark:text-brand-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.name}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Page Content */}
      <div>{children}</div>
    </div>
  );
}
