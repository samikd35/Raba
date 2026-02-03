'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function BookSessionPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to VB browse page
    router.replace('/workspace/vb-browse');
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 dark:border-brand-400 mx-auto mb-4"></div>
        <p className="text-gray-600 dark:text-gray-400">Redirecting to browse venture builders...</p>
      </div>
    </div>
  );
}
