"use client";

import React, { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  LayoutGrid,
  AlertCircle,
} from 'lucide-react';
import { BMCCanvas } from '@/components/bmc/BMCCanvas';
import { MVPData } from '@/types/organization';

interface BMCSectionProps {
  mvpData: MVPData | null;
  readOnly?: boolean;
  embedded?: boolean;
}

export const BMCSection: React.FC<BMCSectionProps> = ({
  mvpData,
  readOnly = true,
  embedded = true,
}) => {
  const [selectedVersion, setSelectedVersion] = useState<'v1' | 'v2' | null>(null);

  if (!mvpData) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <LayoutGrid className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">No BMC Data Available</p>
        <p className="text-sm">Business Model Canvas will appear here once generated.</p>
      </div>
    );
  }

  const bmcV1 = mvpData.bmc;
  const bmcV2 = mvpData.bmc_v2;
  const hasV1 = bmcV1 && Object.keys(bmcV1).length > 0;
  const hasV2 = bmcV2 && Object.keys(bmcV2).length > 0;

  if (!hasV1 && !hasV2) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-lg font-medium">BMC Not Generated</p>
        <p className="text-sm">Business Model Canvas has not been generated yet.</p>
      </div>
    );
  }

  // Default to latest version
  const currentVersion = selectedVersion || (hasV2 ? 'v2' : 'v1');
  const currentBMC = currentVersion === 'v2' ? bmcV2 : bmcV1;

  return (
    <div className="space-y-4">
      {/* Version Toggle (if both v1 and v2 exist) */}
      {hasV1 && hasV2 && (
        <div className="flex justify-center mb-4">
          <div className="bg-white dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm">
            <Tabs
              value={currentVersion}
              onValueChange={(value) => setSelectedVersion(value as 'v1' | 'v2')}
              className="w-full"
            >
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="v1" className="flex items-center gap-2">
                  BMC v1
                </TabsTrigger>
                <TabsTrigger value="v2" className="flex items-center gap-2">
                  BMC v2
                  <Badge variant="outline" className="text-xs">Refined</Badge>
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </div>
      )}

      {/* BMC Canvas - using the same component as workspace page */}
      {currentBMC && (
        <BMCCanvas 
          bmcData={currentBMC as any} 
          compact={true}
          isEditMode={false}
        />
      )}
    </div>
  );
};

export default BMCSection;
