"use client";

import React, { useState, useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Sparkles, Users } from 'lucide-react';
import MoreContext from '@/components/MoreContext';
import { VPSItem, VPSPrimaryStatement } from '@/types/organization';

interface VPSv2SectionProps {
  vpsData: VPSItem[];
  readOnly?: boolean;
  embedded?: boolean;
}

// Helper to extract statement fields from VPSItem
const getStatementFields = (item: VPSItem): VPSPrimaryStatement | null => {
  const statement = item.primary_statement;
  if (!statement) return null;
  
  // If it's already an object with the expected fields
  if (typeof statement === 'object') {
    return statement as VPSPrimaryStatement;
  }
  
  // If it's a string, we can't use it for the structured display
  return null;
};

/**
 * VPS v2 Section Component
 * Displays the refined Value Proposition Statement (v2) using the same layout
 * as the workspace page, but in read-only embedded mode.
 */
export const VPSv2Section: React.FC<VPSv2SectionProps> = ({
  vpsData,
  readOnly = true,
  embedded = true,
}) => {
  const [selectedPersonaId, setSelectedPersonaId] = useState<string | null>(
    vpsData && vpsData.length > 0 ? (vpsData[0].persona_id || 'default') : null
  );

  // Get current persona VPS data based on selection
  const currentVpsData = useMemo(() => {
    if (!selectedPersonaId || !vpsData || vpsData.length === 0) return null;
    return vpsData.find(vps => vps.persona_id === selectedPersonaId) || vpsData[0];
  }, [selectedPersonaId, vpsData]);

  // Handle empty/null state
  if (!vpsData || vpsData.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Sparkles className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">No VPS v2 Data Available</p>
        <p className="text-sm">Value Proposition Statement v2 will appear here once generated.</p>
      </div>
    );
  }

  const statement = currentVpsData ? getStatementFields(currentVpsData) : null;

  if (!statement) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Sparkles className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">Invalid VPS Data</p>
        <p className="text-sm">The VPS v2 data format is not recognized.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Persona Selector - only show if multiple personas */}
      {vpsData.length > 1 && (
        <div className="flex justify-center">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm">
            <Tabs 
              value={selectedPersonaId || 'default'} 
              onValueChange={(value) => setSelectedPersonaId(value)}
              className="w-full"
            >
              <TabsList className="grid grid-cols-2 w-full">
                {vpsData.map((vps, index) => (
                  <TabsTrigger 
                    key={vps.persona_id || `persona-${index}`} 
                    value={vps.persona_id || `persona-${index}`}
                    className="flex items-center gap-2 text-brand-500"
                  >
                    <Users className="w-4 h-4" />
                    <span className="truncate max-w-[120px]">
                      {vps.persona_name || `Persona ${index + 1}`}
                    </span>
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>
        </div>
      )}

      {/* VPS Primary Statement Display */}
      <Card className="border-gray-200 dark:border-gray-700">
        <CardContent className="px-4 py-6">
          <div className="bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-8 py-4 rounded-xl border border-gray-200 dark:border-gray-700">
            <div className="space-y-2 flex-col items-center justify-center">
              {/* Our */}
              <div className="flex items-center gap-2">
                <span className="text-brand-500 dark:text-gray-200 font-bold text-3xl md:text-4xl lg:text-5xl">Our</span>
                <div className="flex items-center gap-3 m-2">
                  <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-lg md:text-xl inline-block">
                    <div className="pr-36">
                      {statement.our}
                    </div>
                    <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                      Products and Services
                    </span>
                  </div>
                </div>
              </div>

              {/* Help */}
              <div className="flex items-center gap-4">
                <span className="text-brand-500 dark:text-gray-200 font-bold text-3xl md:text-4xl lg:text-5xl">Help</span>
                <div className="flex items-center gap-3 m-2">
                  <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-lg md:text-xl inline-block">
                    <div className="pr-32">
                      {statement.help}
                    </div>
                    <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                      Customer Segment
                    </span>
                  </div>
                </div>
              </div>

              {/* Who want to */}
              <div className="flex gap-4 justify-start items-center">
                <span className="text-brand-500 dark:text-gray-200 font-bold text-3xl md:text-4xl lg:text-5xl whitespace-nowrap">Who want to</span>
                <div className="flex items-center gap-3 m-2">
                  <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-lg md:text-xl inline-block">
                    <div className="pr-32">
                      {statement.who_want_to}
                    </div>
                    <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                      Jobs to be done
                    </span>
                  </div>
                </div>
              </div>

              {/* By */}
              <div className="flex items-center gap-4">
                <span className="text-brand-500 dark:text-gray-200 font-bold text-3xl md:text-4xl lg:text-5xl">By</span>
                <div className="flex items-center gap-3 m-2">
                  <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-lg md:text-xl inline-block">
                    <div className="pr-32">
                      {statement.by}
                    </div>
                    <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                      Customer pain
                    </span>
                  </div>
                </div>
              </div>

              {/* And */}
              <div className="flex items-center gap-2">
                <span className="text-brand-500 dark:text-gray-200 font-bold text-3xl md:text-4xl lg:text-5xl">And</span>
                <div className="flex items-center gap-3 m-2">
                  <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-lg md:text-xl inline-block">
                    <div className="pr-24">
                      {statement.and}
                    </div>
                    <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                      Customer gain
                    </span>
                  </div>
                </div>
              </div>

              {/* Unlike */}
              <div className="flex items-center gap-2">
                <span className="text-brand-500 dark:text-gray-200 font-bold text-3xl md:text-4xl lg:text-5xl">Unlike</span>
                <div className="flex items-center gap-3 m-2">
                  <div className="relative bg-gray-100 dark:bg-gray-700 backdrop-blur-sm px-4 py-2 rounded-lg text-brand-500 dark:text-gray-200 font-semibold border border-gray-300 dark:border-gray-600 text-lg md:text-xl inline-block">
                    <div className="pr-48">
                      {statement.unlike}
                    </div>
                    <span className="absolute top-2 right-2 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded-full backdrop-blur-sm">
                      Competing value proposition
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* More Context Section */}
            {currentVpsData?.more_context && (
              <MoreContext 
                title="More Context" 
                content={currentVpsData.more_context} 
              />
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default VPSv2Section;
