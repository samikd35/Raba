'use client';

import { useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Error caught by error boundary:', error);
  }, [error]);

  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-6">
        <Alert variant="destructive">
          <AlertCircle className="h-5 w-5" />
          <AlertTitle>Something went wrong!</AlertTitle>
          <AlertDescription className="mt-2">
            {process.env.NODE_ENV === 'development'
              ? error.message
              : 'An unexpected error occurred. Please try again.'}
          </AlertDescription>
        </Alert>

        <div className="flex w-full flex-col space-y-2 sm:flex-row sm:justify-center sm:space-x-4 sm:space-y-0">
          <Button
            variant="outline"
            onClick={() => window.location.reload()}
            className="w-full sm:w-auto"
          >
            Refresh Page
          </Button>
          <Button
            onClick={reset}
            className="w-full sm:w-auto"
            variant="default"
          >
            Try Again
          </Button>
        </div>

  
      </div>
    </div>
  );
}
