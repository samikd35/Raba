'use client';

import React from 'react';
import { AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from '@/components/ui/button';

interface CancelConfirmDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirmCancel: () => void;
  onContinueWorking: () => void;
}

export const CancelConfirmDialog: React.FC<CancelConfirmDialogProps> = ({
  isOpen,
  onOpenChange,
  onConfirmCancel,
  onContinueWorking,
}) => {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader className="bg-brand-25 dark:bg-brand-900/10 border-b border-brand-200 dark:border-brand-800 -m-6 mb-0 px-6 py-4">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl font-bold text-brand-500 dark:text-brand-300">
              Cancel Project Creation?
            </DialogTitle>
          </div>
        </DialogHeader>
        
        <div className="py-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-yellow-100 dark:bg-yellow-900/40 flex items-center justify-center shrink-0">
              <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div className="space-y-2">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                Are you sure you want to cancel? Your progress will not be saved.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          <Button
            variant="default"
            onClick={onContinueWorking}
            className="border-gray-300 dark:border-gray-600 hover:bg-brand-400 dark:hover:bg-brand-600"
          >
            Continue Working
          </Button>
          <Button
            onClick={onConfirmCancel}
            className="bg-red-500 hover:bg-red-600 text-white"
          >
            Yes, Cancel
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
