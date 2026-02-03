"use client";

import React, { useState, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { X, Save, Loader2 } from "lucide-react";
import { BMCBlockName, BMCEditItem } from "@/hooks/useBMC";
import { motion, AnimatePresence } from "framer-motion";

interface BMCEditModalProps {
  isOpen: boolean;
  blockName: BMCBlockName | null;
  item: BMCEditItem | null;
  onSave: (blockName: BMCBlockName, item: BMCEditItem) => Promise<void>;
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

export const BMCEditModal: React.FC<BMCEditModalProps> = ({
  isOpen,
  blockName,
  item,
  onSave,
  onClose,
  isLoading
}) => {
  // Default empty item for initial state
  const defaultItem: BMCEditItem = { id: '', name: '', description: '' };
  const [editedItem, setEditedItem] = useState<BMCEditItem>(item || defaultItem);

  // Reset form when item changes
  useEffect(() => {
    if (item) {
      setEditedItem(item);
    }
  }, [item]);

  // Handle input changes
  const handleChange = useCallback((field: string, value: string) => {
    setEditedItem(prev => ({
      ...prev,
      [field]: value
    }));
  }, []);

  // Handle save
  const handleSave = useCallback(async () => {
    if (!blockName) return;
    await onSave(blockName, editedItem);
  }, [blockName, editedItem, onSave]);

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

  if (!isOpen || !blockName || !item) return null;

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
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-brand-25 to-brand-50 dark:from-brand-900/30 dark:to-brand-800/30">
              <h2 className="text-lg font-semibold text-brand-500 dark:text-white">
                Edit {BLOCK_DISPLAY_NAMES[blockName]}
              </h2>
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

            {/* Form */}
            <div className="p-6 space-y-4">
              {/* Name */}
              <div className="space-y-2">
                <Label htmlFor="name" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Name
                </Label>
                <Input
                  id="name"
                  value={editedItem.name || ''}
                  onChange={(e) => handleChange('name', e.target.value)}
                  placeholder="Enter name..."
                  disabled={isLoading}
                  className="w-full"
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Description
                </Label>
                <Textarea
                  id="description"
                  value={editedItem.description || ''}
                  onChange={(e) => handleChange('description', e.target.value)}
                  placeholder="Enter description..."
                  disabled={isLoading}
                  rows={4}
                  className="w-full resize-none"
                />
              </div>

              {/* Evidence (optional) */}
              {/* <div className="space-y-2">
                <Label htmlFor="evidence" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Evidence Source <span className="text-gray-400">(optional)</span>
                </Label>
                <Input
                  id="evidence"
                  value={editedItem.evidence || ''}
                  onChange={(e) => handleChange('evidence', e.target.value)}
                  placeholder="Enter evidence source..."
                  disabled={isLoading}
                  className="w-full"
                />
              </div> */}
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
                onClick={handleSave}
                disabled={isLoading || !editedItem.name?.trim()}
                className="bg-brand-500 hover:bg-brand-600"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save Changes
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
