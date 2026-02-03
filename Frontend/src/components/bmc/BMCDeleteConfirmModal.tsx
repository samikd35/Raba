"use client";

import React, { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { X, Trash2, Loader2, AlertTriangle } from "lucide-react";
import { BMCBlockName } from "@/hooks/useBMC";
import { motion, AnimatePresence } from "framer-motion";

interface BMCDeleteConfirmModalProps {
  isOpen: boolean;
  blockName: BMCBlockName | null;
  itemName: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
  isLoading: boolean;
}

// Block display names
const BLOCK_DISPLAY_NAMES: Record<BMCBlockName, string> = {
  customer_segments: 'Customer Segment',
  value_propositions: 'Value Proposition',
  channels: 'Channel',
  customer_relationships: 'Customer Relationship',
  revenue_streams: 'Revenue Stream',
  key_resources: 'Key Resource',
  key_activities: 'Key Activity',
  key_partnerships: 'Key Partnership',
  cost_structure: 'Cost Category'
};

export const BMCDeleteConfirmModal: React.FC<BMCDeleteConfirmModalProps> = ({
  isOpen,
  blockName,
  itemName,
  onConfirm,
  onClose,
  isLoading
}) => {
  // Handle key press (Escape to close)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, isLoading, onClose]);

  if (!isOpen || !blockName) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={(e) => {
            if (e.target === e.currentTarget && !isLoading) {
              onClose();
            }
          }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden border border-gray-200 dark:border-gray-700"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-red-50 to-red-100 dark:from-red-900/30 dark:to-red-800/30">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Delete {BLOCK_DISPLAY_NAMES[blockName]}
                </h2>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                disabled={isLoading}
                className="h-8 w-8 p-0 hover:bg-gray-200 dark:hover:bg-gray-700"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Content */}
            <div className="p-6">
              <p className="text-gray-700 dark:text-gray-300 mb-4">
                Are you sure you want to delete this {BLOCK_DISPLAY_NAMES[blockName].toLowerCase()}?
              </p>
              <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <p className="font-medium text-gray-900 dark:text-white">
                  {itemName}
                </p>
              </div>
              <p className="mt-4 text-sm text-red-600 dark:text-red-400">
                This action cannot be undone.
              </p>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
              <Button
                variant="outline"
                onClick={onClose}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                onClick={onConfirm}
                disabled={isLoading}
                className="bg-red-500 hover:bg-red-600"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </>
                )}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
