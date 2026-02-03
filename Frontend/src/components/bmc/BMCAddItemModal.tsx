"use client";

import React, { useState, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { X, Plus, Loader2, Sparkles } from "lucide-react";
import { BMCBlockName } from "@/hooks/useBMC";
import { motion, AnimatePresence } from "framer-motion";

interface BMCAddItemModalProps {
  isOpen: boolean;
  blockName: BMCBlockName | null;
  onAdd: (blockName: BMCBlockName, label: string, description: string) => Promise<void>;
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

// Placeholder suggestions for each block type
const BLOCK_PLACEHOLDERS: Record<BMCBlockName, { label: string; description: string }> = {
  customer_segments: {
    label: 'e.g., Small Business Owners',
    description: 'e.g., Entrepreneurs running businesses with 1-50 employees...'
  },
  value_propositions: {
    label: 'e.g., Time-saving automation',
    description: 'e.g., Reduces manual work by 50% through intelligent automation...'
  },
  channels: {
    label: 'e.g., Social Media Marketing',
    description: 'e.g., Reach customers through targeted ads on LinkedIn and Facebook...'
  },
  customer_relationships: {
    label: 'e.g., Dedicated Account Manager',
    description: 'e.g., Personal support for enterprise customers...'
  },
  revenue_streams: {
    label: 'e.g., Monthly Subscription',
    description: 'e.g., Recurring revenue from SaaS subscriptions...'
  },
  key_resources: {
    label: 'e.g., Development Team',
    description: 'e.g., Skilled engineers for product development...'
  },
  key_activities: {
    label: 'e.g., Product Development',
    description: 'e.g., Continuous improvement of platform features...'
  },
  key_partnerships: {
    label: 'e.g., Cloud Provider',
    description: 'e.g., AWS partnership for infrastructure and scalability...'
  },
  cost_structure: {
    label: 'e.g., Server Infrastructure',
    description: 'e.g., Monthly cloud hosting and bandwidth costs...'
  }
};

export const BMCAddItemModal: React.FC<BMCAddItemModalProps> = ({
  isOpen,
  blockName,
  onAdd,
  onClose,
  isLoading
}) => {
  const [label, setLabel] = useState('');
  const [description, setDescription] = useState('');

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setLabel('');
      setDescription('');
    }
  }, [isOpen]);

  // Handle add
  const handleAdd = useCallback(async () => {
    if (!blockName || !label.trim() || !description.trim()) return;
    await onAdd(blockName, label.trim(), description.trim());
  }, [blockName, label, description, onAdd]);

  // Handle key press (Escape to close, Ctrl+Enter to submit)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) {
        onClose();
      }
      if (e.key === 'Enter' && e.ctrlKey && !isLoading && label.trim() && description.trim()) {
        handleAdd();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, isLoading, onClose, handleAdd, label, description]);

  if (!isOpen || !blockName) return null;

  const placeholders = BLOCK_PLACEHOLDERS[blockName];

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
            className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden border border-gray-200 dark:border-gray-700"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-green-50 to-emerald-100 dark:from-green-900/30 dark:to-emerald-800/30">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-brand-600 dark:text-white">
                  Add {BLOCK_DISPLAY_NAMES[blockName]}
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

            {/* AI Enhancement Notice */}
            <div className="px-6 py-3 bg-brand-25 dark:bg-brand-900/20 border-b border-brand-100 dark:border-brand-800/30">
              <p className="text-sm text-brand-600 dark:text-brand-300">
                <Sparkles className="w-4 h-4 inline mr-1" />
                Your input will be enhanced by AI to provide detailed, context-aware descriptions.
              </p>
            </div>

            {/* Form */}
            <div className="p-6 space-y-4">
              {/* Label/Name */}
              <div className="space-y-2">
                <Label htmlFor="label" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="label"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  placeholder={placeholders.label}
                  disabled={isLoading}
                  className="w-full"
                  autoFocus
                />
              </div>

              {/* Brief Description */}
              <div className="space-y-2">
                <Label htmlFor="description" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Brief Description <span className="text-red-500">*</span>
                </Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={placeholders.description}
                  disabled={isLoading}
                  rows={3}
                  className="w-full resize-none"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Provide a brief description. AI will enhance it with more details.
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
              
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  onClick={onClose}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleAdd}
                  disabled={isLoading || !label.trim() || !description.trim()}
                  className="bg-green-500 hover:bg-green-600"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4 mr-2" />
                      Add Item
                    </>
                  )}
                </Button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
