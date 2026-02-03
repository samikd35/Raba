"use client";
import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import NavigationLink from "@/components/NavigationLink";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useSidebar } from "../../context/SidebarContext";
import { toast } from "react-hot-toast";
import {
  PieChart,
  UserPlus,
  Building,
  CreditCard,
  Settings,
  Blocks,
  FolderKanban,
  FolderOpen
} from "lucide-react";
import { Separator } from "@/components/ui/separator";

type NavItem = {
  name: string;
  icon: React.ReactNode;
  path?: string;
  disabled?: boolean;
  comingSoon?: boolean;
  special?: boolean;
};

const navItems: NavItem[] = [
  {
    icon: <PieChart className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300" />,
    name: "Dashboard",
    path: "/organization",
  },
  {
    icon: <UserPlus className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300" />,
    name: "Invite Members",
    path: "/organization/invite-members",
  },
  {
    icon: <FolderOpen className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300" />,
    name: "Cohorts",
    path: "/organization/cohorts",
  },
  {
    icon: <Building className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300" />,
    name: "Teams Details",
    path: "/organization/teams",
  },
  {
    icon: <FolderKanban className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300" />,
    name: "Member Projects",
    path: "/organization/member-projects/cohorts",
  },
  {
    icon: <Blocks className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300" />,
    name: "Choose Workspaces",
    path: "/choose-workspace",
    special: true,
  },
  {
    icon: <CreditCard className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300" />,
    name: "Credits & Billing",
    path: "/organization/credits",
  },
  {
    icon: <Settings className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300" />,
    name: "Settings",
    path: "/organization/settings",
  },
];

const separatorIndices = [0, 4, 5, 6];

const AppSidebar: React.FC = () => {
  const { isExpanded, isMobileOpen, isHovered, setIsHovered } = useSidebar();
  const pathname = usePathname();

  const isActive = useCallback((path: string) => path === pathname, [pathname]);

  const handleComingSoonClick = useCallback((itemName: string) => {
    toast.success(`${itemName} - Coming Soon! 🚀`, {
      duration: 3000,
      position: "top-right",
    });
  }, []);

  return (
    <aside
      className={`fixed top-0 left-0 h-screen bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transition-all duration-300 ease-in-out z-50
        ${isExpanded || isMobileOpen || isHovered ? "w-[290px]" : "w-20"}
        ${isMobileOpen ? "translate-x-0" : "-translate-x-full"}
        lg:translate-x-0`}
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex flex-col h-full">
        {/* Sidebar Logo / Brand */}
        <div className="h-16 flex items-center px-4 border-b border-gray-200 dark:border-gray-800">
          <NavigationLink href="/">
            {isExpanded || isHovered || isMobileOpen ? (
              <>
                <Image
                  className="dark:hidden"
                  src="/images/logo/logo.svg"
                  alt="Logo"
                  width={110}
                  height={20}
                  priority
                />
                <Image
                  className="hidden dark:block"
                  src="/images/logo/logo-dark.png"
                  alt="Logo"
                  width={110}
                  height={20}
                  priority
                />
              </>
            ) : (
              <Image
                src="/images/logo/logo-icon.png"
                alt="Logo"
                width={32}
                height={32}
                className="mx-auto"
                priority
              />
            )}
          </NavigationLink>
        </div>

        {/* Navigation Menu */}
        <div className="flex-1 flex flex-col">
          <nav className="flex-1 overflow-y-auto p-3 space-y-4 [-ms-overflow-style:'none'] [scrollbar-width:'none'] [&::-webkit-scrollbar]:hidden">
            <ul className="flex flex-col gap-2">
              {navItems.map((nav, index) => (
                <li key={nav.name}>
                  {nav.comingSoon ? (
                    <button
                      onClick={() => handleComingSoonClick(nav.name)}
                      className={`menu-item group menu-item-inactive cursor-pointer relative ${!isExpanded && !isHovered && !isMobileOpen ? "justify-center" : ""}`}
                    >
                      <span className="menu-item-icon-inactive">{nav.icon}</span>
                      {(isExpanded || isHovered || isMobileOpen) && (
                        <>
                          <span className="menu-item-text">{nav.name}</span> 🚀
                        </>
                      )}
                    </button>
                  ) : nav.special && nav.path ? (
                    <NavigationLink
                      href={nav.path}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 bg-transparent border-2 border-brand-200 text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-950 hover:border-brand-600 dark:hover:border-brand-400 transform hover:scale-[1.02]
                        ${isActive(nav.path) ? "bg-brand-100 dark:bg-brand-900 border-brand-200 dark:border-brand-400 text-brand-700 dark:text-brand-300 ring-2 ring-brand-300 ring-offset-2 ring-offset-white dark:ring-offset-gray-900" : ""}
                        ${!isExpanded && !isHovered && !isMobileOpen ? "justify-center px-2 py-2.5" : ""}`}
                    >
                      <span className={`shrink-0 ${isActive(nav.path) ? "text-brand-700 dark:text-brand-300" : "text-brand-600 dark:text-brand-400"}`}>
                        {nav.icon}
                      </span>
                      {(isExpanded || isHovered || isMobileOpen) && (
                        <>
                          <span className="text-sm font-medium flex-1 text-left">{nav.name}</span>
                        </>
                      )}
                    </NavigationLink>
                  ) : (
                    nav.path && (
                      <NavigationLink
                        href={nav.path}
                        className={`menu-item group ${isActive(nav.path)
                          ? "menu-item-active"
                          : "menu-item-inactive"
                          } ${!isExpanded && !isHovered && !isMobileOpen ? "justify-center" : ""}`}
                      >
                        <span
                          className={`${isActive(nav.path)
                            ? "menu-item-icon-active"
                            : "menu-item-icon-inactive"
                            }`}
                        >
                          {nav.icon}
                        </span>
                        {(isExpanded || isHovered || isMobileOpen) && (
                          <span className="menu-item-text">{nav.name}</span>
                        )}
                      </NavigationLink>
                    )
                  )}

                  {separatorIndices.includes(index) && (
                    <div className="mt-2">
                      <Separator />
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </div>
    </aside>
  );
};

export default AppSidebar;
