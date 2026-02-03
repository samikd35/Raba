"use client";

import Link from "next/link";
import React from "react";
import { usePathname, useSearchParams, useRouter } from "next/navigation";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2 } from "lucide-react";

interface BreadcrumbProps {
  pageTitle: string;
  titleSuffix?: React.ReactNode;
}

const PageBreadcrumb: React.FC<BreadcrumbProps> = ({ pageTitle, titleSuffix }) => {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();

  // Extract project ID from URL: use the last non-empty segment (e.g., /team-workspace/market-research-analysis/<id>)
  const getProjectId = (): string | null => {
    const isUuid = (val: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(val);
    const segments = pathname.split('/').filter(Boolean);
    if (segments.length === 0) return null;
    const candidate = segments[segments.length - 1];
    return isUuid(candidate) ? candidate : candidate || null;
  };

  // Determine base path (team-workspace or workspace)
  const getBasePath = (): string => {
    return pathname.includes('/team-workspace') ? '/team-workspace' : '/workspace';
  };

  // Check if current page is VMP-related
  const isVMPPage = (): boolean => {
    const vmpPages = [
      'vps', 'bmc', 'solution-critic', 'vps-v2', 'bmc-v2', 'vpc-v2', 'projects-mvp'
    ];
    return vmpPages.some(page => pathname.includes(page));
  };

  // Get current active tab based on pathname
  const getCurrentTab = (): string => {
    if (pathname.includes('/projects-mvp')) return 'projects-mvp';
    if (pathname.includes('/vps-v2')) return 'vps-v2';
    if (pathname.includes('/bmc-v2')) return 'bmc-v2';
    if (pathname.includes('/vpc-v2')) return 'vpc-v2';
    if (pathname.includes('/vps')) return 'vps';
    if (pathname.includes('/bmc')) return 'bmc';
    if (pathname.includes('/solution-critic')) return 'solution-critic';
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
      id: 'projects-mvp',
      label: 'Project',
      shortLabel: 'Project',
      href: projectId ? `${basePath}/projects-mvp/${projectId}` : `${basePath}/projects-mvp`,
    },
    {
      id: 'vps',
      label: 'VPS',
      shortLabel: 'VPS',
      href: projectId ? `${basePath}/vps/${projectId}` : `${basePath}/vps/${projectId}`,
    },
    {
      id: 'bmc',
      label: 'BMC',
      shortLabel: 'BMC',
      href: projectId ? `${basePath}/bmc/${projectId}` : `${basePath}/bmc/${projectId}`,
    },
    {
      id: 'solution-critic',
      label: 'Solution Critique',
      shortLabel: 'Critic',
      href: projectId ? `${basePath}/solution-critic/${projectId}` : `${basePath}/solution-critic/${projectId}`,
    },
    {
      id: 'vps-v2',
      label: 'VPS v2',
      shortLabel: 'VPS v2',
      href: projectId ? `${basePath}/vps-v2/${projectId}` : `${basePath}/vps-v2/${projectId}`,
    },
    {
      id: 'bmc-v2',
      label: 'BMC v2',
      shortLabel: 'BMC v2',
      href: projectId ? `${basePath}/bmc-v2/${projectId}` : `${basePath}/bmc-v2/${projectId}`,
    },
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
        <div className="max-w-full ">
          <Tabs value={currentTab} className="w-full">
            <TabsList
              aria-label="VMP navigation"
              className="w-full h-11 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-lg shadow-sm px-1"
            >
              <div className="flex w-full items-center overflow-x-auto whitespace-nowrap scrollbar-thin scrollbar-track-transparent scrollbar-thumb-brand-200 dark:scrollbar-thumb-brand-700 py-1 gap-2">
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