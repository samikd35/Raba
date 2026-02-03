"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Target,
  AlertCircle,
  TrendingUp,
  Briefcase,
  UserCircle2,
  FileText,
  Lightbulb,
} from 'lucide-react';
import {
  VPCV2Data,
  VPCV2PersonaData,
  CustomerProfileV2Item,
} from '@/types/organization';

interface CustomerProfileV2SectionProps {
  vpcV2Data: VPCV2Data | null;
  readOnly?: boolean;
  embedded?: boolean;
}

const TYPE_CONFIG = {
  pain: {
    icon: AlertCircle,
    title: 'Customer Pains',
    textColor: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-red-200 dark:border-red-800',
    badgeColor: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  },
  gain: {
    icon: TrendingUp,
    title: 'Customer Gains',
    textColor: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    borderColor: 'border-green-200 dark:border-green-800',
    badgeColor: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  },
  jtbd: {
    icon: Briefcase,
    title: 'Jobs to be Done',
    textColor: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-blue-200 dark:border-blue-800',
    badgeColor: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  },
};

const CustomerProfileItemCard: React.FC<{
  item: CustomerProfileV2Item;
  type: 'pain' | 'gain' | 'jtbd';
  index: number;
}> = ({ item, type, index }) => {
  const config = TYPE_CONFIG[type];
  const hasEnhancementRationale = item.enhancement_rationale;

  return (
    <div className={`p-4 rounded-lg border ${config.borderColor} ${config.bgColor}`}>
      {/* Header with Label and Persona Badge */}
      <div className="flex justify-between items-start mb-4 border-b border-gray-200 dark:border-gray-700 pb-3">
        <h4 className="font-semibold text-brand-500 dark:text-white text-lg flex-1 pr-4">
          {item.label}
        </h4>
        <Badge variant="outline" className={config.badgeColor}>
          {item.persona_name || item.persona_id}
        </Badge>
      </div>

      {/* Main Content Grid */}
      <div className={`${hasEnhancementRationale ? 'md:grid md:grid-cols-2 md:gap-6' : ''}`}>
        {/* Left Column: Main Content */}
        <div className={hasEnhancementRationale ? 'space-y-4' : ''}>
          {/* Description Section */}
          <div>
            <label className="block text-sm font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-300 mb-2">
              Description
            </label>
            <div className="text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
              <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed">
                {item.description || item.text}
              </p>
            </div>
          </div>

          {/* Evidence Section */}
          {item.evidence && item.evidence.length > 0 && (
            <div>
              <label className="block text-sm font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-300 mb-2">
                Evidence
              </label>
              <div className="space-y-2">
                {item.evidence.map((evidence, evidenceIndex) => (
                  <div
                    key={evidenceIndex}
                    className="text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div className="font-medium text-brand-500 dark:text-brand-300 mb-1 flex items-center gap-2">
                      <FileText className="w-3 h-3" />
                      {evidence.source}:
                    </div>
                    <div className="italic text-gray-600 dark:text-gray-400">"{evidence.quote}"</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Enhancement Rationale */}
        {hasEnhancementRationale && (
          <div className="border-l border-gray-200 dark:border-gray-700 pl-6 mt-6 md:mt-0">
            <div className="sticky top-4">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="w-4 h-4 text-yellow-500" />
                <h5 className="text-sm font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-300">
                  Enhancement Rationale
                </h5>
              </div>

              <div className="space-y-4">
                {/* Original */}
                {item.enhancement_rationale?.original && (
                  <div className="bg-white dark:bg-gray-800/50 p-4 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                        Original
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      {item.enhancement_rationale.original}
                    </p>
                  </div>
                )}

                {/* Evidence */}
                {item.enhancement_rationale?.evidence && (
                  <div className="bg-white dark:bg-gray-800/50 p-4 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-green-500"></div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-green-600 dark:text-green-400">
                        Evidence
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      {item.enhancement_rationale.evidence}
                    </p>
                  </div>
                )}

                {/* Reason */}
                {item.enhancement_rationale?.reason && (
                  <div className="bg-white dark:bg-gray-800/50 p-4 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                        Reason
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      {item.enhancement_rationale.reason}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const CustomerProfileTypeSection: React.FC<{
  items: CustomerProfileV2Item[];
  type: 'pain' | 'gain' | 'jtbd';
}> = ({ items, type }) => {
  const config = TYPE_CONFIG[type];
  const IconComponent = config.icon;

  if (!items || items.length === 0) return null;

  return (
    <Card className="shadow-md border-gray-200 dark:border-gray-700">
      <CardHeader className="flex flex-row items-center space-y-0">
        <div className={`p-2 rounded-lg ${config.bgColor} mr-3`}>
          <IconComponent className={`w-5 h-5 ${config.textColor}`} />
        </div>
        <CardTitle className={config.textColor}>{config.title}</CardTitle>
        <Badge variant="secondary" className="ml-auto">
          {items.length} items
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4 -mt-2">
        {items.map((item, index) => (
          <CustomerProfileItemCard
            key={`${type}-${item.id}-${index}`}
            item={item}
            type={type}
            index={index}
          />
        ))}
      </CardContent>
    </Card>
  );
};

const PersonaCustomerProfile: React.FC<{
  personaData: VPCV2PersonaData;
  personaId: string;
}> = ({ personaData, personaId }) => {
  const customerProfile = personaData.customer_profile;
  const validationMetadata = personaData.validation_metadata;

  if (!customerProfile) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-lg font-medium">Customer Profile Not Available</p>
        <p className="text-sm">No customer profile data found for this persona.</p>
      </div>
    );
  }

  // Add persona info to each item
  const personaName = personaData.persona_name || personaId;
  const painsWithPersona = (customerProfile.pains || []).map(p => ({
    ...p,
    persona_id: personaId,
    persona_name: personaName,
    type: 'pain' as const,
  }));
  const gainsWithPersona = (customerProfile.gains || []).map(g => ({
    ...g,
    persona_id: personaId,
    persona_name: personaName,
    type: 'gain' as const,
  }));
  const jtbdWithPersona = (customerProfile.jobs_to_be_done || []).map(j => ({
    ...j,
    persona_id: personaId,
    persona_name: personaName,
    type: 'jtbd' as const,
  }));

  return (
    <div className="space-y-6">
      {/* Validation Metadata */}
      {validationMetadata?.generated_at && (
        <div className="flex items-start">
          <p className="text-sm text-brand-500 dark:text-gray-300 flex items-center gap-2 px-4 bg-brand-25 dark:bg-transparent border-gray-200 dark:border-gray-600 py-2 border rounded-lg">
            Generated on{' '}
            {new Date(validationMetadata.generated_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
            {validationMetadata.validation_status && (
              <Badge
                variant="outline"
                className={
                  validationMetadata.validation_status === 'validated'
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
                    : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300'
                }
              >
                {validationMetadata.validation_status}
              </Badge>
            )}
          </p>
        </div>
      )}

      {/* Customer Profile Sections */}
      <CustomerProfileTypeSection items={painsWithPersona} type="pain" />
      <CustomerProfileTypeSection items={gainsWithPersona} type="gain" />
      <CustomerProfileTypeSection items={jtbdWithPersona} type="jtbd" />

      {/* Empty State */}
      {painsWithPersona.length === 0 && gainsWithPersona.length === 0 && jtbdWithPersona.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <Target className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
          <p className="text-lg font-medium">No Customer Profile Items</p>
          <p className="text-sm">No pains, gains, or jobs to be done found for this persona.</p>
        </div>
      )}
    </div>
  );
};

export const CustomerProfileV2Section: React.FC<CustomerProfileV2SectionProps> = ({
  vpcV2Data,
  readOnly = true,
  embedded = true,
}) => {
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);

  if (!vpcV2Data) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Target className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">No Customer Profile v2 Available</p>
        <p className="text-sm">Enhanced customer profile data will appear here once generated.</p>
      </div>
    );
  }

  // Get persona keys (filter out non-persona keys)
  const personaKeys = Object.keys(vpcV2Data).filter(
    key => key.startsWith('P') && typeof vpcV2Data[key] === 'object' && vpcV2Data[key]?.customer_profile
  );

  if (personaKeys.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-lg font-medium">Customer Profile In Progress</p>
        <p className="text-sm">The enhanced customer profile is still being processed.</p>
      </div>
    );
  }

  // Set initial selected persona
  const currentPersona = selectedPersona || personaKeys[0];
  const currentPersonaData = vpcV2Data[currentPersona];

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
                    {vpcV2Data[personaKey]?.persona_name || personaKey}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>
        </div>
      )}

      {/* Customer Profile Content */}
      {currentPersonaData && (
        <PersonaCustomerProfile personaData={currentPersonaData} personaId={currentPersona} />
      )}
    </div>
  );
};

export default CustomerProfileV2Section;
