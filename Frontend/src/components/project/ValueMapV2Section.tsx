"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Package,
  Shield,
  TrendingUp,
  UserCircle2,
  FileText,
  Zap,
  AlertCircle,
} from 'lucide-react';
import {
  VPCV2Data,
  VPCV2PersonaData,
  ValueMapItem,
  ValueMapSelections,
} from '@/types/organization';

interface ValueMapV2SectionProps {
  vpcV2Data: VPCV2Data | null;
  readOnly?: boolean;
  embedded?: boolean;
}

const TYPE_CONFIG = {
  pain_relievers: {
    icon: Shield,
    title: 'Pain Relievers',
    textColor: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-red-200 dark:border-red-800',
    badgeColor: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  },
  gain_creators: {
    icon: TrendingUp,
    title: 'Gain Creators',
    textColor: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    borderColor: 'border-green-200 dark:border-green-800',
    badgeColor: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  },
  products_services: {
    icon: Package,
    title: 'Products & Services',
    textColor: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-blue-200 dark:border-blue-800',
    badgeColor: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  },
};

const ValueMapItemCard: React.FC<{
  item: ValueMapItem;
  type: 'pain_relievers' | 'gain_creators' | 'products_services';
  index: number;
}> = ({ item, type, index }) => {
  const config = TYPE_CONFIG[type];

  return (
    <div className={`p-4 rounded-lg border ${config.borderColor} ${config.bgColor}`}>
      {/* Header with Label */}
      <div className="flex justify-between items-start mb-3 border-b border-gray-200 dark:border-gray-700 pb-3">
        <h4 className="font-semibold text-brand-500 dark:text-white text-lg flex-1 pr-4">
          {item.label}
        </h4>
        {item.priority && (
          <Badge
            variant="outline"
            className={
              item.priority === 'critical'
                ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
                : item.priority === 'high'
                ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
            }
          >
            {item.priority}
          </Badge>
        )}
      </div>

      {/* Description */}
      <div className="mb-3">
        <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
          {item.text}
        </p>
      </div>

      {/* Impact or Value */}
      {(item.impact || item.value) && (
        <div className="mb-3">
          <label className="block text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-400 mb-1">
            <Zap className="w-3 h-3 inline mr-1" />
            {item.impact ? 'Impact' : 'Value'}
          </label>
          <div className="text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
            {item.impact || item.value}
          </div>
        </div>
      )}

      {/* Evidence */}
      {item.evidence && (
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-gray-400 mb-1">
            <FileText className="w-3 h-3 inline mr-1" />
            Evidence
          </label>
          <div className="text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700 italic">
            "{item.evidence}"
          </div>
        </div>
      )}
    </div>
  );
};

const ValueMapTypeSection: React.FC<{
  items: ValueMapItem[];
  type: 'pain_relievers' | 'gain_creators' | 'products_services';
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
          <ValueMapItemCard
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

const PersonaValueMap: React.FC<{
  personaData: VPCV2PersonaData;
  personaId: string;
}> = ({ personaData, personaId }) => {
  const valueMapSelections = personaData.value_map_selections;

  if (!valueMapSelections) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-lg font-medium">Value Map Not Available</p>
        <p className="text-sm">No value map selections found for this persona.</p>
      </div>
    );
  }

  const painRelievers = valueMapSelections.pain_relievers || [];
  const gainCreators = valueMapSelections.gain_creators || [];
  const productsServices = valueMapSelections.products_services || [];

  return (
    <div className="space-y-6">
      {/* Selections Made Date */}
      {personaData.selections_made_at && (
        <div className="flex items-start">
          <p className="text-sm text-brand-500 dark:text-gray-300 flex items-center gap-2 px-4 bg-brand-25 dark:bg-transparent border-gray-200 dark:border-gray-600 py-2 border rounded-lg">
            Selections made on{' '}
            {new Date(personaData.selections_made_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>
      )}

      {/* Value Map Sections */}
      <ValueMapTypeSection items={painRelievers} type="pain_relievers" />
      <ValueMapTypeSection items={gainCreators} type="gain_creators" />
      <ValueMapTypeSection items={productsServices} type="products_services" />

      {/* Empty State */}
      {painRelievers.length === 0 && gainCreators.length === 0 && productsServices.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <Package className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
          <p className="text-lg font-medium">No Value Map Items</p>
          <p className="text-sm">No pain relievers, gain creators, or products found.</p>
        </div>
      )}
    </div>
  );
};

export const ValueMapV2Section: React.FC<ValueMapV2SectionProps> = ({
  vpcV2Data,
  readOnly = true,
  embedded = true,
}) => {
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);

  if (!vpcV2Data) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Package className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">No Value Map Available</p>
        <p className="text-sm">Value map selections will appear here once completed.</p>
      </div>
    );
  }

  // Get persona keys that have value_map_selections
  const personaKeys = Object.keys(vpcV2Data).filter(
    key => key.startsWith('P') && typeof vpcV2Data[key] === 'object' && vpcV2Data[key]?.value_map_selections
  );

  if (personaKeys.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-lg font-medium">Value Map In Progress</p>
        <p className="text-sm">The value map selections are still being processed.</p>
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

      {/* Value Map Content */}
      {currentPersonaData && (
        <PersonaValueMap personaData={currentPersonaData} personaId={currentPersona} />
      )}
    </div>
  );
};

export default ValueMapV2Section;
