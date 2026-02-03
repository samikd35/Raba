"use client";

import React from 'react';
import { SimpleAdminSidebar } from '@/components/admin/SimpleAdminSidebar';
import { SimpleAdminHeader } from '@/components/admin/SimpleAdminHeader';

export default function SimpleAdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen w-full">
      <SimpleAdminSidebar />
      <div className="flex-1 flex flex-col">
        <SimpleAdminHeader />
        <main className="flex-1 p-6 bg-gray-50 dark:bg-gray-900">
          {children}
        </main>
      </div>
    </div>
  );
}

