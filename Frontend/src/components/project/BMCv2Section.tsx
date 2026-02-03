"use client";

import React from 'react';
import { AlertCircle, Sparkles } from 'lucide-react';
import { BMCCanvas } from '@/components/bmc/BMCCanvas';

interface BMCv2SectionProps {
  bmcData: any;
  readOnly?: boolean;
  embedded?: boolean;
}

/**
 * BMC v2 Section Component
 * Displays the refined Business Model Canvas (v2) using the same BMCCanvas component
 * as the workspace page, but in read-only embedded mode.
 */
export const BMCv2Section: React.FC<BMCv2SectionProps> = ({
  bmcData,
  readOnly = true,
  embedded = true,
}) => {
  // Handle empty/null state
  if (!bmcData || Object.keys(bmcData).length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Sparkles className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">No BMC v2 Data Available</p>
        <p className="text-sm">Business Model Canvas v2 will appear here once generated.</p>
      </div>
    );
  }

  // Check if bmcData has the expected structure
  const hasValidData = bmcData.customer_segments || bmcData.value_propositions || bmcData.key_partners;
  
  if (!hasValidData) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-lg font-medium">Invalid BMC Data Structure</p>
        <p className="text-sm">The BMC v2 data format is not recognized.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* BMC Canvas - using the same component as workspace page */}
      <BMCCanvas 
        bmcData={bmcData} 
        compact={true}
        isEditMode={false}
      />
    </div>
  );
};

export default BMCv2Section;
