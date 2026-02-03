'use client';

import Link from "next/link";
import React from "react";
import { usePathname, useRouter } from "next/navigation";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2 } from "lucide-react";

interface BreadcrumbProps {
  pageTitle: string;
  titleSuffix?: React.ReactNode;
}

const PageBreadcrumb: React.FC<BreadcrumbProps> = ({ pageTitle, titleSuffix }) => {
  const pathname = usePathname();
  const router = useRouter();

  // Extract project ID from URL: use the last non-empty segment (e.g., /workspace/market-research-analysis/<id>)
  const getProjectId = (): string | null => {
    const isUuid = (val: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(val);
    const segments = pathname.split('/').filter(Boolean);
    if (segments.length === 0) return null;
    const candidate = segments[segments.length - 1];
    return isUuid(candidate) ? candidate : candidate || null;
  };

  // Determine base path (team-workspace or workspace)
  const getBasePath = (): string => {
    return pathname.includes('/workspace') ? '/workspace' : '/workspace';
  };

  // Check if current page is VMP-related
  const isVMPPage = (): boolean => {
    const vmpPages = [
      'projects', 'personas', 'customer-profile', 'vpc', 
      'hypothesis', 'assumptions', 'questionnaires', 'generate-customer-profile'
    ];
    return vmpPages.some(page => pathname.includes(page));
  };

  // Get current active tab based on pathname
  const getCurrentTab = (): string => {
    if (pathname.includes('/projects/')) return 'projects';
    if (pathname.includes('/personas')) return 'personas';
    if (pathname.includes('/customer-profile') || pathname.includes('/generate-customer-profile')) return 'customer-profile';
    if (pathname.includes('/vpc')) return 'vpc';
    if (pathname.includes('/hypothesis')) return 'hypothesis';
    if (pathname.includes('/assumptions')) return 'assumptions';
    if (pathname.includes('/questionnaires')) return 'questionnaires';

    return 'projects';
  };

  const projectId = getProjectId();
  const basePath = getBasePath();
  const currentTab = getCurrentTab();

  // Micro-loading state for tab navigation
  const [navLoadingTab, setNavLoadingTab] = React.useState<string | null>(null);

  // VMP Navigation Tabs with professional labels (memoized for perf)
  const vmpTabs = React.useMemo(() => ([
    {
      id: 'projects',
      label: 'Project',
      shortLabel: 'Project',
      href: projectId ? `${basePath}/projects/${projectId}` : `${basePath}/projects/${projectId}`,
    },
    {
      id: 'personas',
      label: 'Personas',
      shortLabel: 'Personas',
      href: projectId ? `${basePath}/personas/${projectId}` : `${basePath}/personas/${projectId}`,
    },
    {
      id: 'customer-profile',
      label: 'Customer Profile',
      shortLabel: 'Profile',
      href: projectId ? `${basePath}/customer-profile/${projectId}` : `${basePath}/customer-profile/${projectId}`,
    },
    {
      id: 'vpc',
      label: 'VPC',
      shortLabel: 'VPC',
      href: projectId ? `${basePath}/vpc/${projectId}` : `${basePath}/vpc/${projectId}`,
    },
    {
      id: 'assumptions',
      label: 'Assumptions',
      shortLabel: 'Assumptions',
      href: projectId ? `${basePath}/assumptions/${projectId}` : `${basePath}/assumptions/${projectId}`,
    },
    {
      id: 'hypothesis',
      label: 'Value Hypothesis',
      shortLabel: 'Hypothesis',
      href: projectId ? `${basePath}/hypothesis/${projectId}` : `${basePath}/hypothesis/${projectId}`,
    },
    {
      id: 'questionnaires',
      label: 'Questionnaires',
      shortLabel: 'Questions',
      href: projectId ? `${basePath}/questionnaires/${projectId}` : `${basePath}/questionnaires/${projectId}`,
    }
  ]), [basePath, projectId]);

  return (
    <div className="sticky top-[65px] z-40 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 py-3 flex items-center justify-between mb-2 z-25 w-full -mt-2">
      {/* Page Title Section */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="hidden sm:block w-1 h-6 bg-brand-500 rounded-full" />
        <h2 className="text-lg sm:text-xl font-semibold text-brand-500 dark:text-white/95 tracking-tight truncate">
          {pageTitle}
        </h2>
        {titleSuffix}
      </div>

      {/* VMP Navigation Tabs */}
      {isVMPPage() && (
        <div className="max-w-full">
          <Tabs value={currentTab} className="w-full">
            <TabsList
              aria-label="VMP navigation"
              className="w-full h-11 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-lg shadow-sm px-1"
            >
              <div className="flex w-full items-center overflow-x-auto whitespace-nowrap scrollbar-thin scrollbar-track-transparent scrollbar-thumb-brand-200 dark:scrollbar-thumb-brand-700 py-1">
                {vmpTabs.map((tab) => {
                  return (
                    <TabsTrigger
                      key={tab.id}
                      value={tab.id}
                      asChild
                      className="data-[state=active]:bg-brand-600 data-[state=active]:text-white data-[state=active]:shadow-sm data-[state=active]:ring-1 data-[state=active]:ring-brand-300 dark:data-[state=active]:ring-brand-600 text-brand-700 dark:text-brand-200 hover:text-brand-700 dark:hover:text-brand-100 hover:bg-brand-50 dark:hover:bg-brand-800/40 transition-colors duration-200 font-medium rounded-md h-9 px-2 min-w-fit"
                    >
                      <Link
                        href={tab.href}
                        onClick={(e) => {
                          // If already on this tab, let default behavior happen
                          if (currentTab === tab.id) return;
                          // Set micro loading and proceed with client navigation
                          setNavLoadingTab(tab.id);
                          // Use router to ensure navigation triggers immediately
                          e.preventDefault();
                          router.push(tab.href);
                        }}
                        className={`flex items-center justify-center gap-2 w-full h-full focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-[#101828] rounded-md ${navLoadingTab === tab.id ? 'pointer-events-none opacity-80' : ''}`}
                        aria-busy={navLoadingTab === tab.id}
                      >
                        {navLoadingTab === tab.id && (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        )}
                        <span className="hidden lg:inline text-sm truncate">
                          {tab.label}
                        </span>
                        <span className="lg:hidden text-xs truncate">
                          {tab.shortLabel}
                        </span>
                      </Link>
                    </TabsTrigger>
                  );
                })}
              </div>
            </TabsList>
          </Tabs>
        </div>
      )}
    </div>
  );
};

export default PageBreadcrumb;