"use client";

import React from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { BarChart3, DollarSign, Activity, TrendingUp, Zap } from 'lucide-react';

const tokenNavItems = [
  {
    title: "Overview",
    url: "/admin/token-manager",
    icon: BarChart3,
  },
  {
    title: "Tenants",
    url: "/admin/token-manager/tenants",
    icon: TrendingUp,
  },
  {
    title: "Features",
    url: "/admin/token-manager/features",
    icon: Zap,
  },
  {
    title: "Models",
    url: "/admin/token-manager/models",
    icon: Activity,
  },
  {
    title: "Pricing",
    url: "/admin/token-manager/pricing",
    icon: DollarSign,
  },
];

export default function TokenManagerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="space-y-6">
      {/* Sub-navigation */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-2">
        <nav className="flex flex-wrap gap-2">
          {tokenNavItems.map((item) => (
            <Link
              key={item.url}
              href={item.url}
              className={`flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                pathname === item.url
                  ? 'bg-brand-500 text-white'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <item.icon className="w-4 h-4" />
              <span>{item.title}</span>
            </Link>
          ))}
        </nav>
      </div>

      {/* Page Content */}
      {children}
    </div>
  );
}
