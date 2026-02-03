"use client";

import React from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  IconBell, 
  IconUser, 
  IconLogout,
  IconMoon,
  IconSun,
} from '@tabler/icons-react';
// import { useTheme } from 'next-themes';

export function AdminHeader() {
  // const { theme, setTheme } = useTheme();
  const theme = 'light'; // Temporary fix
  const setTheme = () => {}; // Temporary fix

  return (
    <header className="border-b bg-white dark:bg-gray-800 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
            Admin Portal
          </h1>
          <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
            Super Admin
          </Badge>
        </div>
        
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            {theme === 'dark' ? (
              <IconSun className="h-5 w-5" />
            ) : (
              <IconMoon className="h-5 w-5" />
            )}
          </Button>
          
          <Button variant="ghost" size="icon">
            <IconBell className="h-5 w-5" />
          </Button>
          
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-full bg-brand-500 flex items-center justify-center">
              <IconUser className="h-4 w-4 text-white" />
            </div>
            <div className="hidden md:block">
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                Admin User
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                admin@yuba.com
              </p>
            </div>
          </div>
          
          <Button variant="ghost" size="icon">
            <IconLogout className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
