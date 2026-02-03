"use client";

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/authService';
import { useRouter } from 'next/navigation';
import { toast } from "react-hot-toast";
import { Bell, User, LogOut } from 'lucide-react';

export function SimpleAdminHeader() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [selectedRole, setSelectedRole] = useState<string>(user?.roles[0] || 'super_admin');

  const handleLogout = async () => {
    try {
      await authService.logout();
      toast.success('Logged out successfully');
      router.push('/');
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('Failed to logout');
      // Still redirect to home even if API call fails
      router.push('/');
    }
  };

  const handleRoleChange = (role: string) => {
    setSelectedRole(role);
    // In a real implementation, you would switch the user's context here
    toast.info(`Role switched to ${role}`);
  };

  const getUserInitials = (name: string) => {
    return name
      .split(' ')
      .map(part => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const userRoles = user?.roles || [];
  const userRole = userRoles.includes(selectedRole) ? selectedRole : userRoles[0] || 'user';

  return (
    <header className="border-b bg-white dark:bg-gray-800 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
            Admin Portal
          </h1>
          <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
            {userRole === 'super_admin' ? 'Super Admin' : userRole === 'admin' ? 'Admin' : 'User'}
          </Badge>
        </div>
        
        <div className="flex items-center space-x-4">
          {userRoles.length > 1 && (
            <div className="relative">
              <select 
                value={selectedRole}
                onChange={(e) => handleRoleChange(e.target.value)}
                className="bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {userRoles.map((role) => (
                  <option key={role} value={role}>
                    {role === 'super_admin' ? 'Super Admin' : role === 'admin' ? 'Admin' : role}
                  </option>
                ))}
              </select>
            </div>
          )}
          
          <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
            <Bell className="w-5 h-5" />
          </button>
          
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-full bg-brand-500 flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
            <div className="hidden md:block">
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {user?.full_name || 'User'}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {user?.email || 'user@example.com'}
              </p>
            </div>
          </div>
          
          <button 
            onClick={handleLogout}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            title="Logout"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  );
}