"use client";

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Package,
  Shield,
  TrendingUp,
  UserCircle2,
  Briefcase,
  Frown,
  Smile,
  LayoutGrid,
  AlertCircle,
} from 'lucide-react';
import {
  VPCV2Data,
  VPCV2PersonaData,
} from '@/types/organization';

interface VPCV2CanvasSectionProps {
  vpcV2Data: VPCV2Data | null;
  readOnly?: boolean;
  embedded?: boolean;
}

const VPCCanvasView: React.FC<{
  personaData: VPCV2PersonaData;
  personaId: string;
  personaName: string;
}> = ({ personaData, personaId, personaName }) => {
  const customerProfile = personaData.customer_profile;
  const valueMapSelections = personaData.value_map_selections;

  // Extract data
  const jobs = customerProfile?.jobs_to_be_done || [];
  const pains = customerProfile?.pains || [];
  const gains = customerProfile?.gains || [];
  const products = valueMapSelections?.products_services || [];
  const painRelievers = valueMapSelections?.pain_relievers || [];
  const gainCreators = valueMapSelections?.gain_creators || [];

  const hasCustomerProfile = jobs.length > 0 || pains.length > 0 || gains.length > 0;
  const hasValueMap = products.length > 0 || painRelievers.length > 0 || gainCreators.length > 0;

  if (!hasCustomerProfile && !hasValueMap) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <LayoutGrid className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">VPC Data Not Complete</p>
        <p className="text-sm">Complete both Customer Profile and Value Map to view the canvas.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
      {/* Value Map Side (Left) */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-gray-200 dark:border-gray-700">
          <Package className="w-5 h-5 text-indigo-600" />
          <h4 className="font-semibold text-gray-900 dark:text-white">Value Map</h4>
        </div>

        {/* Products & Services */}
        <Card className="p-4 border-2 border-green-200 dark:border-green-700 bg-green-50 dark:bg-green-900/10">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-green-200 dark:bg-green-800/30 rounded-lg">
              <Package className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <h5 className="font-bold text-green-700 dark:text-green-300">Products & Services</h5>
            {products.length > 0 && (
              <Badge className="bg-green-600 text-white ml-auto">{products.length}</Badge>
            )}
          </div>
          {products.length > 0 ? (
            <div className="space-y-2">
              {products.map((item, idx) => (
                <div key={item.id || idx} className="p-2 bg-white dark:bg-gray-800 rounded-lg border border-green-200 dark:border-green-700">
                  <p className="text-sm font-medium text-gray-800 dark:text-white">{item.label}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No products defined</p>
          )}
        </Card>

        {/* Pain Relievers */}
        <Card className="p-4 border-2 border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/10">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-red-200 dark:bg-red-800/30 rounded-lg">
              <Shield className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <h5 className="font-bold text-red-700 dark:text-red-300">Pain Relievers</h5>
            {painRelievers.length > 0 && (
              <Badge className="bg-red-600 text-white ml-auto">{painRelievers.length}</Badge>
            )}
          </div>
          {painRelievers.length > 0 ? (
            <div className="space-y-2">
              {painRelievers.map((item, idx) => (
                <div key={item.id || idx} className="p-2 bg-white dark:bg-gray-800 rounded-lg border border-red-200 dark:border-red-700">
                  <p className="text-sm font-medium text-gray-800 dark:text-white">{item.label}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No pain relievers defined</p>
          )}
        </Card>

        {/* Gain Creators */}
        <Card className="p-4 border-2 border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/10">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-200 dark:bg-blue-800/30 rounded-lg">
              <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <h5 className="font-bold text-blue-700 dark:text-blue-300">Gain Creators</h5>
            {gainCreators.length > 0 && (
              <Badge className="bg-blue-600 text-white ml-auto">{gainCreators.length}</Badge>
            )}
          </div>
          {gainCreators.length > 0 ? (
            <div className="space-y-2">
              {gainCreators.map((item, idx) => (
                <div key={item.id || idx} className="p-2 bg-white dark:bg-gray-800 rounded-lg border border-blue-200 dark:border-blue-700">
                  <p className="text-sm font-medium text-gray-800 dark:text-white">{item.label}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No gain creators defined</p>
          )}
        </Card>
      </div>

      {/* Customer Profile Side (Right) */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-gray-200 dark:border-gray-700">
          <UserCircle2 className="w-5 h-5 text-purple-600" />
          <h4 className="font-semibold text-gray-900 dark:text-white">Customer Profile</h4>
          <Badge variant="outline" className="ml-auto">{personaName}</Badge>
        </div>

        {/* Jobs to be Done */}
        <Card className="p-4 border-2 border-green-200 dark:border-green-700 bg-green-50 dark:bg-green-900/10">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-green-200 dark:bg-green-800/30 rounded-lg">
              <Briefcase className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <h5 className="font-bold text-green-700 dark:text-green-300">Jobs-to-be-Done</h5>
            {jobs.length > 0 && (
              <Badge className="bg-green-600 text-white ml-auto">{jobs.length}</Badge>
            )}
          </div>
          {jobs.length > 0 ? (
            <div className="space-y-2">
              {jobs.map((item, idx) => (
                <div key={item.id || idx} className="p-2 bg-white dark:bg-gray-800 rounded-lg border border-green-200 dark:border-green-700">
                  <p className="text-sm font-medium text-gray-800 dark:text-white">{item.label}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No jobs defined</p>
          )}
        </Card>

        {/* Pains */}
        <Card className="p-4 border-2 border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/10">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-red-200 dark:bg-red-800/30 rounded-lg">
              <Frown className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <h5 className="font-bold text-red-700 dark:text-red-300">Pains</h5>
            {pains.length > 0 && (
              <Badge className="bg-red-600 text-white ml-auto">{pains.length}</Badge>
            )}
          </div>
          {pains.length > 0 ? (
            <div className="space-y-2">
              {pains.map((item, idx) => (
                <div key={item.id || idx} className="p-2 bg-white dark:bg-gray-800 rounded-lg border border-red-200 dark:border-red-700">
                  <p className="text-sm font-medium text-gray-800 dark:text-white">{item.label}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No pains defined</p>
          )}
        </Card>

        {/* Gains */}
        <Card className="p-4 border-2 border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/10">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-200 dark:bg-blue-800/30 rounded-lg">
              <Smile className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <h5 className="font-bold text-blue-700 dark:text-blue-300">Gains</h5>
            {gains.length > 0 && (
              <Badge className="bg-blue-600 text-white ml-auto">{gains.length}</Badge>
            )}
          </div>
          {gains.length > 0 ? (
            <div className="space-y-2">
              {gains.map((item, idx) => (
                <div key={item.id || idx} className="p-2 bg-white dark:bg-gray-800 rounded-lg border border-blue-200 dark:border-blue-700">
                  <p className="text-sm font-medium text-gray-800 dark:text-white">{item.label}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No gains defined</p>
          )}
        </Card>
      </div>
    </div>
  );
};

export const VPCV2CanvasSection: React.FC<VPCV2CanvasSectionProps> = ({
  vpcV2Data,
  readOnly = true,
  embedded = true,
}) => {
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);

  if (!vpcV2Data) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <LayoutGrid className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">No VPC Data Available</p>
        <p className="text-sm">Value Proposition Canvas will appear here once completed.</p>
      </div>
    );
  }

  // Get persona keys that have both customer_profile and value_map_selections
  const personaKeys = Object.keys(vpcV2Data).filter(
    key => key.startsWith('P') && 
           typeof vpcV2Data[key] === 'object' && 
           (vpcV2Data[key]?.customer_profile || vpcV2Data[key]?.value_map_selections)
  );

  if (personaKeys.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-lg font-medium">VPC In Progress</p>
        <p className="text-sm">Complete Customer Profile v2 and Value Map selections to view the canvas.</p>
      </div>
    );
  }

  // Set initial selected persona
  const currentPersona = selectedPersona || personaKeys[0];
  const currentPersonaData = vpcV2Data[currentPersona];
  const personaName = currentPersonaData?.persona_name || 
                      currentPersonaData?.value_map_selections?.persona_name || 
                      currentPersona;

  return (
    <div className="space-y-4">
      {/* Persona Toggle (only show if multiple personas) */}
      {personaKeys.length > 1 && (
        <div className="flex justify-center mb-4">
          <div className="bg-white dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm">
            <Tabs
              value={currentPersona}
              onValueChange={(value) => setSelectedPersona(value)}
              className="w-full"
            >
              <TabsList
                className="grid w-full"
                style={{ gridTemplateColumns: `repeat(${personaKeys.length}, 1fr)` }}
              >
                {personaKeys.map((personaKey) => (
                  <TabsTrigger
                    key={personaKey}
                    value={personaKey}
                    className="flex items-center gap-2 text-brand-500 dark:text-gray-300"
                  >
                    <UserCircle2 className="w-4 h-4" />
                    {vpcV2Data[personaKey]?.persona_name ||
                      vpcV2Data[personaKey]?.value_map_selections?.persona_name ||
                      personaKey}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>
        </div>
      )}

      {/* VPC Canvas Content */}
      {currentPersonaData && (
        <VPCCanvasView 
          personaData={currentPersonaData} 
          personaId={currentPersona}
          personaName={personaName}
        />
      )}
    </div>
  );
};

export default VPCV2CanvasSection;
