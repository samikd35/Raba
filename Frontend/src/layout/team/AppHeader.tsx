"use client";
import { ThemeToggleButton } from "@/components/common/ThemeToggleButton";
import UserDropdown from "@/components/header/UserDropdown";
import { useSidebar } from "@/context/SidebarContext";
import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import Rating from "@/components/Rating";
import { LayoutDashboard } from "lucide-react";
import { RefreshCw } from "lucide-react";

interface CreditLot {
  id: string;
  credit_amount: number;
  valid_from: string;
  expires_at: string;
}

interface CreditsData {
  tenant_id: string;
  lots: CreditLot[];
  tenant_total_active_credits: number;
  user_total_consumed_in_tenant: number;
}

const AppHeader: React.FC = () => {
  const [isApplicationMenuOpen, setApplicationMenuOpen] = useState(false);
  const { isMobileOpen, toggleSidebar, toggleMobileSidebar } = useSidebar();
  const [creditsData, setCreditsData] = useState<CreditsData | null>(null);
  const [isLoadingCredits, setIsLoadingCredits] = useState(false);
  const [creditsError, setCreditsError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const { token, user } = useAuthStore();
  const router = useRouter();

  const [isNavigating, setIsNavigating] = useState(false);

  // Calculate credit stats based on backend data
  const creditStats = useMemo(() => {
    if (!creditsData) {
      return { remaining: 0, total: 0, consumed: 0 };
    }

    const total = creditsData.tenant_total_active_credits + creditsData.user_total_consumed_in_tenant;
    const remaining = creditsData.tenant_total_active_credits;
    const consumed = creditsData.user_total_consumed_in_tenant;

    return { remaining, total, consumed };
  }, [creditsData]);

  // Memoized toggle handlers to prevent unnecessary re-renders
  const handleToggle = useCallback(() => {
    const isDesktop = window.innerWidth >= 1024;
    if (isDesktop) {
      toggleSidebar();
    } else {
      toggleMobileSidebar();
    }
  }, [toggleSidebar, toggleMobileSidebar]);

  const toggleApplicationMenu = useCallback(() => {
    setApplicationMenuOpen(prev => !prev);
  }, []);

  const handleChooseWorkspace = useCallback(() => {
    if (isNavigating) return;
    setIsNavigating(true);
    router.push("/choose-workspace");
  }, [isNavigating, router]);

  // Fetch credits data from API
  const fetchCreditsData = useCallback(async () => {
    try {
      setIsLoadingCredits(true);
      setCreditsError(null);

      // Cancel previous request if it exists
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new AbortController for this request
      abortControllerRef.current = new AbortController();

      if (!token) {
        throw new Error('No authentication token found');
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/me/credits`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication expired. Please sign in again.');
        }
        if (response.status === 403) {
          throw new Error('Access forbidden. Check your permissions.');
        }
        throw new Error(`Failed to fetch credits: ${response.status} ${response.statusText}`);
      }

      const data: CreditsData = await response.json();
      setCreditsData(data);

      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 Credits data fetched:', data);
      }

    } catch (error: any) {
      if (error.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') {
          console.log('🚫 Credits fetch aborted');
        }
        return;
      }

      const errorMessage = error.message || 'Failed to fetch credits data';
      setCreditsError(errorMessage);
      
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error fetching credits:', error);
      }
    } finally {
      setIsLoadingCredits(false);
    }
  }, [token]);

  // Fetch credits on component mount and when token changes
  useEffect(() => {
    if (token) {
      fetchCreditsData();
    }
  }, [fetchCreditsData, token]);

  // Auto-refresh credits every 30 seconds
  useEffect(() => {
    if (!token) return;

    const interval = setInterval(() => {
      fetchCreditsData();
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [fetchCreditsData, token]);

  const formatCredits = (credits: number) => {
    if (credits >= 1000000) {
      return `${(credits / 1000000).toFixed(1)}M`;
    }
    if (credits >= 1000) {
      return `${(credits / 1000).toFixed(1)}K`;
    }
    return credits.toLocaleString(undefined, { maximumFractionDigits: 0 });
  };

  // Memoized SVG components to prevent re-creation on every render
  const CloseIcon = useCallback(() => (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M6.21967 7.28131C5.92678 6.98841 5.92678 6.51354 6.21967 6.22065C6.51256 5.92775 6.98744 5.92775 7.28033 6.22065L11.999 10.9393L16.7176 6.22078C17.0105 5.92789 17.4854 5.92788 17.7782 6.22078C18.0711 6.51367 18.0711 6.98855 17.7782 7.28144L13.0597 12L17.7782 16.7186C18.0711 17.0115 18.0711 17.4863 17.7782 17.7792C17.4854 18.0721 17.0105 18.0721 16.7176 17.7792L11.999 13.0607L7.28033 17.7794C6.98744 18.0722 6.51256 18.0722 6.21967 17.7794C5.92678 17.4865 5.92678 17.0116 6.21967 16.7187L10.9384 12L6.21967 7.28131Z"
        fill="currentColor"
      />
    </svg>
  ), []);

  const MenuIcon = useCallback(() => (
    <svg
      width="16"
      height="12"
      viewBox="0 0 16 12"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M0.583252 1C0.583252 0.585788 0.919038 0.25 1.33325 0.25H14.6666C15.0808 0.25 15.4166 0.585786 15.4166 1C15.4166 1.41421 15.0808 1.75 14.6666 1.75L1.33325 1.75C0.919038 1.75 0.583252 1.41422 0.583252 1ZM0.583252 11C0.583252 10.5858 0.919038 10.25 1.33325 10.25L14.6666 10.25C15.0808 10.25 15.4166 10.5858 15.4166 11C15.4166 11.4142 15.0808 11.75 14.6666 11.75L1.33325 11.75C0.919038 11.75 0.583252 11.4142 0.583252 11ZM1.33325 5.25C0.919038 5.25 0.583252 5.58579 0.583252 6C0.583252 6.41421 0.919038 6.75 1.33325 6.75L7.99992 6.75C8.41413 6.75 8.74992 6.41421 8.74992 6C8.74992 5.58579 8.41413 5.25 7.99992 5.25L1.33325 5.25Z"
        fill="currentColor"
      />
    </svg>
  ), []);

  const SearchIcon = useCallback(() => (
    <svg
      className="fill-gray-500 dark:fill-gray-400"
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M3.04175 9.37363C3.04175 5.87693 5.87711 3.04199 9.37508 3.04199C12.8731 3.04199 15.7084 5.87693 15.7084 9.37363C15.7084 12.8703 12.8731 15.7053 9.37508 15.7053C5.87711 15.7053 3.04175 12.8703 3.04175 9.37363ZM9.37508 1.54199C5.04902 1.54199 1.54175 5.04817 1.54175 9.37363C1.54175 13.6991 5.04902 17.2053 9.37508 17.2053C11.2674 17.2053 13.003 16.5344 14.357 15.4176L17.177 18.238C17.4699 18.5309 17.9448 18.5309 18.2377 18.238C18.5306 17.9451 18.5306 17.4703 18.2377 17.1774L15.418 14.3573C16.5365 13.0033 17.2084 11.2669 17.2084 9.37363C17.2084 5.04817 13.7011 1.54199 9.37508 1.54199Z"
        fill=""
      />
    </svg>
  ), []);

  const DotsIcon = useCallback(() => (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M5.99902 10.4951C6.82745 10.4951 7.49902 11.1667 7.49902 11.9951V12.0051C7.49902 12.8335 6.82745 13.5051 5.99902 13.5051C5.1706 13.5051 4.49902 12.8335 4.49902 12.0051V11.9951C4.49902 11.1667 5.1706 10.4951 5.99902 10.4951ZM17.999 10.4951C18.8275 10.4951 19.499 11.1667 19.499 11.9951V12.0051C19.499 12.8335 18.8275 13.5051 17.999 13.5051C17.1706 13.5051 16.499 12.8335 16.499 12.0051V11.9951C16.499 11.1667 17.1706 10.4951 17.999 10.4951ZM13.499 11.9951C13.499 11.1667 12.8275 10.4951 11.999 10.4951C11.1706 10.4951 10.499 11.1667 10.499 11.9951V12.0051C10.499 12.8335 11.1706 13.5051 11.999 13.5051C12.8275 13.5051 13.499 12.8335 13.499 12.0051V11.9951Z"
        fill="currentColor"
      />
    </svg>
  ), []);

  return (
    <header className="sticky top-0 flex w-full bg-white border-gray-200 dark:border-gray-800 dark:bg-gray-900 lg:border-b z-50">
      <div className="flex flex-col items-center justify-between grow lg:flex-row lg:px-4 py-0.5">
        
        <div className="flex items-center justify-between w-full gap-2 border-b border-gray-200 dark:border-gray-800  lg:justify-normal lg:border-b-0 ">
          <button
            className="flex items-center justify-center w-10 h-10 text-gray-500 border-gray-200 rounded-lg z-99999 dark:border-gray-800 lg:h-11 lg:w-11 lg:border dark:text-gray-400"
            onClick={handleToggle}
            aria-label="Toggle Sidebar"
          >
            {isMobileOpen ? <CloseIcon /> : <MenuIcon />}
          </button>

          <button
            onClick={toggleApplicationMenu}
            className="flex items-center justify-center w-10 h-10 text-gray-700 rounded-lg z-99999 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 lg:hidden"
            aria-label="Application Menu"
          >
            <DotsIcon />
          </button>

         

          <div className="hidden lg:block">
            <div className="rounded-lg border border-amber-400/60 px-4 py-2 text-amber-800 cursor-pointer bg-gradient-to-r from-amber-50 to-amber-100 hover:from-amber-100 hover:to-amber-200 dark:from-amber-900/20 dark:to-amber-800/20 dark:text-amber-200 dark:border-amber-500/40 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="flex items-center gap-2">
                {isLoadingCredits ? (
                  <div className="w-2 h-2 bg-amber-500 rounded-full animate-spin"></div>
                ) : creditsError ? (
                  <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                ) : (
                  <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse"></div>
                )}
                <p className="text-sm font-medium">
                  {creditsError ? (
                    <span className="text-red-600 dark:text-red-400">Error loading credits</span>
                  ) : (
                    <>
                      <span className="font-bold">{formatCredits(creditStats.remaining)}</span>
                      {" "}of{" "}
                      <span className="font-bold">{formatCredits(creditStats.total)}</span>
                      {" "}credits remaining
                      {creditStats.consumed > 0 && (
                        <span className="text-xs ml-1 opacity-75">
                          ({formatCredits(creditStats.consumed)} used)
                        </span>
                      )}
                    </>
                  )}
                </p>
                {creditsError && (
                  <button
                    onClick={fetchCreditsData}
                    className="ml-2 text-xs text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300"
                    title="Retry loading credits"
                  >
                    Retry
                  </button>
                )}
              </div>
            </div>
            {/* {user && (
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium">
                  {user.tenant_name}
                </p>
              </div>
            )} */}
          </div>
        </div>
        
        <div
          className={`${
            isApplicationMenuOpen ? "flex" : "hidden"
          } items-center justify-between w-full gap-4 px-5 py-2 lg:flex shadow-theme-md lg:justify-end lg:px-0 lg:shadow-none`}
        >
          <div className="flex items-center gap-2">
             <div>
            
                                <Rating variant="dropdown" />
                      </div>
            <ThemeToggleButton />
          </div>
          <UserDropdown />
        </div>
      </div>
    </header>
  );
};

export default AppHeader;