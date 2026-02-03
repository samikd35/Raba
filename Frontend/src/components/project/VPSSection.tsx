"use client";

import React, { useState, useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  FileText,
  Users,
  Sparkles,
  AlertCircle,
} from 'lucide-react';
import MoreContext from '@/components/MoreContext';
import {
  MVPData,
  VPSItem,
  VPSPrimaryStatement,
} from '@/types/organization';

interface VPSSectionProps {
  mvpData: MVPData | null;
  readOnly?: boolean;
  embedded?: boolean;
}

// Helper to extract statement fields from VPSItem
const getStatementFields = (item: VPSItem): VPSPrimaryStatement | null => {
  const statement = item.primary_statement;
  if (!statement) return null;
  
  if (typeof statement === 'object') {
    return statement as VPSPrimaryStatement;
  }
  
  return null;
};

// Reusable VPS Statement Display Component (same as workspace page)
const VPSStatementDisplay: React.FC<{
  statement: VPSPrimaryStatement;
  moreContext?: string;
}> = ({ statement, moreContext }) => {
  return (
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
      {moreContext && (
        <MoreContext 
          title="More Context" 
          content={moreContext} 
        />
      )}
    </div>
  );
};

// Key Differentiators Component
const KeyDifferentiators: React.FC<{
  differentiators: VPSItem['key_differentiators'];
}> = ({ differentiators }) => {
  if (!differentiators || differentiators.length === 0) return null;
  
  return (
    <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <h4 className="text-sm font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-400 mb-3 flex items-center gap-2">
        <Sparkles className="w-4 h-4" />
        Key Differentiators
      </h4>
      <div className="space-y-3">
        {differentiators.map((diff, idx) => (
          <div key={idx} className="bg-white dark:bg-gray-700 p-3 rounded-lg border border-gray-200 dark:border-gray-600">
            <p className="font-medium text-gray-900 dark:text-white">{diff.title}</p>
            {diff.description && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{diff.description}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export const VPSSection: React.FC<VPSSectionProps> = ({
  mvpData,
  readOnly = true,
  embedded = true,
}) => {
  const [selectedVersion, setSelectedVersion] = useState<'v1' | 'v2' | null>(null);
  const [selectedPersonaIndex, setSelectedPersonaIndex] = useState(0);

  if (!mvpData) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">No VPS Data Available</p>
        <p className="text-sm">Value Proposition Statement will appear here once generated.</p>
      </div>
    );
  }

  const vpsV1 = mvpData.vps_v1 || [];
  const vpsV2 = mvpData.vps_v2 || [];
  const hasV1 = vpsV1.length > 0;
  const hasV2 = vpsV2.length > 0;

  if (!hasV1 && !hasV2) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-lg font-medium">VPS Not Generated</p>
        <p className="text-sm">Value Proposition Statement has not been generated yet.</p>
      </div>
    );
  }

  // Default to latest version
  const currentVersion = selectedVersion || (hasV2 ? 'v2' : 'v1');
  const currentVPS = currentVersion === 'v2' ? vpsV2 : vpsV1;
  const currentVpsItem = currentVPS[selectedPersonaIndex] || currentVPS[0];
  const statement = currentVpsItem ? getStatementFields(currentVpsItem) : null;

  return (
    <div className="space-y-4">
      {/* Version Toggle (if both v1 and v2 exist) */}
      {hasV1 && hasV2 && (
        <div className="flex justify-center mb-4">
          <div className="bg-white dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm">
            <Tabs
              value={currentVersion}
              onValueChange={(value) => {
                setSelectedVersion(value as 'v1' | 'v2');
                setSelectedPersonaIndex(0);
              }}
              className="w-full"
            >
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="v1" className="flex items-center gap-2">
                  VPS v1
                  <Badge variant="outline" className="text-xs">{vpsV1.length}</Badge>
                </TabsTrigger>
                <TabsTrigger value="v2" className="flex items-center gap-2">
                  VPS v2
                  <Badge variant="outline" className="text-xs">{vpsV2.length}</Badge>
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </div>
      )}

      {/* Persona Selector - only show if multiple personas */}
      {currentVPS.length > 1 && (
        <div className="flex justify-center">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm">
            <Tabs 
              value={String(selectedPersonaIndex)} 
              onValueChange={(value) => setSelectedPersonaIndex(Number(value))}
              className="w-full"
            >
              <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${currentVPS.length}, 1fr)` }}>
                {currentVPS.map((vps, index) => (
                  <TabsTrigger 
                    key={vps.persona_id || `persona-${index}`} 
                    value={String(index)}
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

      {/* VPS Statement Display - same layout as workspace page */}
      {statement ? (
        <Card className="border-gray-200 dark:border-gray-700">
          <CardContent className="px-4 py-6">
            <VPSStatementDisplay 
              statement={statement} 
              moreContext={currentVpsItem?.more_context} 
            />
            <KeyDifferentiators differentiators={currentVpsItem?.key_differentiators} />
          </CardContent>
        </Card>
      ) : (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
          <p className="text-lg font-medium">Invalid VPS Data</p>
          <p className="text-sm">The VPS data format is not recognized.</p>
        </div>
      )}
    </div>
  );
};

export default VPSSection;
