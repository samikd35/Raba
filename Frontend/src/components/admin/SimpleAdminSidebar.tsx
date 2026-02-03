"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Building2, Mail, Users, Shield, Activity, UserCheck, Settings, Coins, ChevronDown, CreditCard, ClipboardList } from 'lucide-react';
import { url } from "inspector";
import { IconBriefcase } from "@tabler/icons-react";

const adminNavItems = [
  {
    title: "Dashboard",
    url: "/admin",
    icon: BarChart3,
  },
  {
    title: "Organizations",
    url: "/admin/organizations",
    icon: Building2,
  },
  {
    title: "Invite Organization",
    url: "/admin/invite",
    icon: Mail,
  },
  {
    title: "Members",
    url: "/admin/members",
    icon: Users,
  },
  {
    title: "User Monitoring",
    url: "/admin/user-monitoring",
    icon: Activity,
  },
  {
    title: "Token Manager",
    url: "/admin/token-manager",
    icon: Coins,
   },
   {
    title: "Feature Credits",
    url: "/admin/feature-credits",
    icon: CreditCard,
  },
   {
    title: "Venture Builders",
    url: "/admin/venture-builders",
    icon: IconBriefcase,
  },
  {
    title: "VB Interest",
    url: "/admin/vb-interest",
    icon: ClipboardList,
  },
  {
    title: "Cofounder Moderation",
    url: "/admin/cofounder-moderation",
    icon: UserCheck,
  }
];

const cofounderNavItems = [
  {
    title: "Cofounder",
    url: "/admin/cofounder-moderation",
    icon: UserCheck,
  },
];

export function SimpleAdminSidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 h-screen">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <Shield className="w-6 h-6 text-brand-500" />
          <span className="text-lg font-semibold text-gray-900 dark:text-white">
            Yuba Admin
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4">
        <ul className="space-y-2">
          {adminNavItems.map((item) => {
            const isActive = item.title === "Cofounder"
              ? pathname.includes('/admin/cofounder-') || pathname.includes('/admin/enums')
              : item.title === "Feature Credits"
              ? pathname.startsWith('/admin/feature-credits')
              : item.title === "Token Manager"
              ? pathname.startsWith('/admin/token-manager')
              : item.title === "VB Interest"
              ? pathname.startsWith('/admin/vb-interest')
              : pathname === item.url;

            return (
              <li key={item.title}>
                <Link
                  href={item.url}
                  className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-500 text-white'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.title}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="absolute bottom-0 w-64 p-4 border-t border-gray-200 dark:border-gray-700">
        <Link
          href="/"
          className="flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <Users className="w-5 h-5" />
          <span>Back to User Portal</span>
        </Link>
      </div>
    </div>
  );
}