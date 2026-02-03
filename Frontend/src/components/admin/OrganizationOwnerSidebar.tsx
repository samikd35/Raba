"use client";

import * as React from "react";
import { usePathname, useParams } from "next/navigation";
import { BarChart3, Building2, Mail, Users, Settings, CreditCard, UserPlus } from 'lucide-react';

export function OrganizationOwnerSidebar() {
  const pathname = usePathname();
  const params = useParams();
  
  // Extract organization ID from pathname if not in params
  const organizationId = (params.id as string) || pathname.match(/\/admin\/organizations\/([^\/]+)/)?.[1] || '';

  const orgNavItems = [
    {
      title: "Organization Dashboard",
      url: `/admin/organizations/${organizationId}`,
      icon: BarChart3,
    },
    {
      title: "Invite Members",
      url: `/admin/organizations/${organizationId}/invite-members`,
      icon: UserPlus,
    },
    {
      title: "Members",
      url: `/admin/organizations/${organizationId}/members`,
      icon: Users,
    },
    {
      title: "Teams",
      url: `/admin/organizations/${organizationId}/teams`,
      icon: Building2,
    },
    {
      title: "Credits & Billing",
      url: `/admin/organizations/${organizationId}/credits`,
      icon: CreditCard,
    },
    {
      title: "Settings",
      url: `/admin/organizations/${organizationId}/settings`,
      icon: Settings,
    },
  ];

  return (
    <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 h-screen">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <Building2 className="w-6 h-6 text-brand-500" />
          <span className="text-lg font-semibold text-gray-900 dark:text-white">
            Organization
          </span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Owner Dashboard
        </p>
      </div>

      {/* Navigation */}
      <nav className="p-4">
        <ul className="space-y-2">
          {orgNavItems.map((item) => (
            <li key={item.title}>
              <a
                href={item.url}
                className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  pathname === item.url
                    ? 'bg-brand-500 text-white'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span>{item.title}</span>
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className="absolute bottom-0 w-64 p-4 border-t border-gray-200 dark:border-gray-700">
        <a
          href="/admin/organizations"
          className="flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <Building2 className="w-5 h-5" />
          <span>All Organizations</span>
        </a>
      </div>
    </div>
  );
}
