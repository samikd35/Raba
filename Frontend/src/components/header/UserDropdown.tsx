"use client";
import React, { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useUser, useLogout } from "@/stores/authStore";
import { Dropdown } from "../ui/dropdown/Dropdown";
import { DropdownItem } from "../ui/dropdown/DropdownItem";
import TermsAndConditions from "../TermsAndConditions";
import Rating from "../Rating";
import { cn } from "@/lib/utils";

// Icons using lucide-react style
const UserIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const BuildingIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M3 21h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M9 8h1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M9 12h1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M9 16h1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M14 8h1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M14 12h1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M14 16h1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const LogOutIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="m16 17 5-5-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M21 12H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const ChevronDownIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const LoaderIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M21 12a9 9 0 1 1-6.219-8.56" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

const UserDropdownContent = React.memo(({ 
  user, 
  onLogout, 
  onClose 
}: { 
  user: any;
  onLogout: () => void;
  onClose: () => void;
}) => {
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const router = useRouter();

  useEffect(() => {
    try {
      router.prefetch?.('/signin');
    } catch {}
  }, [router]);

  const handleLogout = useCallback(() => {
    setIsLoggingOut(true);
    onClose();

    Promise.resolve(onLogout()).catch((error) => {
      if (process.env.NODE_ENV === 'development') {
        console.error('Logout error (background):', error);
      }
    });

    router.replace('/signin');

    const fallback = setTimeout(() => {
      if (typeof window !== 'undefined' && window.location.pathname !== '/signin') {
        window.location.href = '/signin';
      }
    }, 1500);

    try {
      Promise.resolve().then(() => clearTimeout(fallback));
    } catch {}
  }, [onLogout, onClose, router]);

  const userDisplayInfo = useMemo(() => {
    const displayName = user?.full_name || 
                       (typeof user?.sub === 'string' ? user.sub : null) || 
                       'User';
    const userEmail = user?.email || 
                     (typeof user?.sub === 'string' ? user.sub : null) || 
                     'user@example.com';
    
    return { displayName, userEmail };
  }, [user?.full_name, user?.sub, user?.email]);

  const menuItems = [
    {
      icon: UserIcon,
      label: "Profile",
      onClick: () => {
        // Check if we're in team workspace or regular workspace
        const currentPath = window.location.pathname;
        const profilePath = currentPath.startsWith('/team-workspace') ? '/team-workspace/profile' : '/workspace/profile';
        router.push(profilePath);
        onClose();
      }
    },
    {
      icon: BuildingIcon,
      label: "Workspaces",
      onClick: () => {
        router.push('/choose-workspace');
        onClose();
      }
    }
  ];

  return (
    <div className="w-full">
      {/* User Info */}
      <div className="flex items-start gap-3 p-4 pb-3">
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-brand-25 dark:bg-brand-900/30 border border-primary/20 dark:border-brand-800 flex items-center justify-center">
          <span className="text-sm font-medium text-brand-500 dark:text-brand-400">
            {userDisplayInfo.displayName.charAt(0).toUpperCase()}
          </span>
        </div>
        <div className="flex-1 min-w-0 space-y-1">
          <p className="text-sm font-medium text-brand-500 dark:text-brand-400 truncate">
            {userDisplayInfo.displayName}
          </p>
          <p className="text-xs text-muted-foreground dark:text-gray-400 truncate">
            {userDisplayInfo.userEmail}
          </p>
        </div>
      </div>

      {/* Menu Items */}
      <div className="p-2 space-y-1">
        {menuItems.map((item, index) => (
          <button
            key={index}
            onClick={item.onClick}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors focus:outline-none 
                       hover:bg-brand-25 hover:text-brand-500 focus:bg-brand-25 focus:text-brand-500 
                       dark:hover:bg-gray-800/60 dark:focus:bg-gray-800/60 dark:text-gray-200 dark:hover:text-brand-400 dark:focus:text-brand-400"
          >
            <item.icon className="w-4 h-4 text-muted-foreground dark:text-gray-400" />
            <span>{item.label}</span>
          </button>
        ))}
      </div>

      {/* Additional Components */}
      <div className="p-2 border-t border-border dark:border-gray-800">
        <TermsAndConditions />
        <div className="px-1">
          <Rating variant="dropdown" />
        </div>
      </div>

      {/* Logout Button */}
      <div className="p-2 border-t border-border dark:border-gray-800">
        <button
          onClick={handleLogout}
          disabled={isLoggingOut}
          className={cn(
            "w-full flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors focus:outline-none",
            "hover:bg-destructive/10 hover:text-destructive focus:bg-destructive/10 focus:text-destructive",
            "dark:hover:bg-red-900/20 dark:text-gray-200 dark:hover:text-red-400 dark:focus:text-red-400",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {isLoggingOut ? (
            <LoaderIcon className="w-4 h-4 animate-spin text-muted-foreground dark:text-gray-400" />
          ) : (
            <LogOutIcon className="w-4 h-4 text-muted-foreground dark:text-gray-300" />
          )}
          <span>{isLoggingOut ? "Signing out..." : "Sign out"}</span>
        </button>
      </div>
    </div>
  );
});

UserDropdownContent.displayName = 'UserDropdownContent';

export default function UserDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const user = useUser();
  const logout = useLogout();
  const router = useRouter();
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    router.prefetch('/signin');
  }, [router]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const toggleDropdown = useCallback((e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    e.stopPropagation();
    setIsOpen(prev => !prev);
  }, []);

  const closeDropdown = useCallback(() => {
    setIsOpen(false);
  }, []);

  const handleLogout = useCallback(() => {
    try {
      setIsOpen(false);
      void logout();
      router.replace('/signin');
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Logout flow error:', error);
      }
    }
  }, [logout, router]);

  if (!user) {
    return null;
  }

  const displayName = user?.full_name || 
                     (typeof user?.sub === 'string' ? user.sub : null) || 
                     'User';

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={toggleDropdown}
        className={cn(
          "flex items-center gap-2 h-10 p-4 text-sm rounded-lg border border-input bg-background shadow-sm transition-colors",
          "hover:bg-brand-25 hover:text-brand-500 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
          "dark:border-gray-800 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800",
          isOpen && "bg-brand-25 text-brand-500 dark:bg-gray-800 dark:text-brand-400"
         )}
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label="User menu"
      >
        <div className="w-6 h-6 rounded-sm bg-brand-25 dark:bg-brand-900/30 border border-primary/20 dark:border-brand-800 flex items-center justify-center">
          <span className="text-xs font-medium text-brand-500 dark:text-brand-400">
            {displayName.charAt(0).toUpperCase()}
          </span>
        </div>
        
        <span className="font-medium max-w-[120px] truncate text-brand-500 dark:text-brand-400">
          {displayName}
        </span>

        <ChevronDownIcon className={cn(
          "w-4 h-4 text-muted-foreground dark:text-gray-400 transition-transform duration-200",
          isOpen && "rotate-180"
        )} />
      </button>

      <Dropdown
        isOpen={isOpen}
        onClose={closeDropdown}
        className={cn(
          "absolute right-0 mt-2 w-64 rounded-md border bg-popover text-popover-foreground shadow-md",
          "dark:bg-gray-900 dark:text-gray-200 dark:border-gray-800",
           "animate-in fade-in-0 zoom-in-95",
           "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
           "data-[side=bottom]:slide-in-from-top-2",
           "z-50"
         )}
      >
        <UserDropdownContent 
          user={user} 
          onLogout={handleLogout} 
          onClose={closeDropdown} 
        />
      </Dropdown>
    </div>
  );
}