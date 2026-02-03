"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { VPCData, VPCPersona, CustomerProfileItem } from '@/types/organization';
import { 
  User,
  Briefcase,
  AlertTriangle,
  TrendingUp,
  Package,
  Shield,
  Sparkles,
  LayoutGrid,
  CheckCircle2
} from 'lucide-react';

export interface VPCSectionProps {
  vpcData: VPCData;
  readOnly?: boolean;
  embedded?: boolean; // If true, don't render Card wrapper (for use inside CollapsibleSection)
}

// Status color mapping
const getStatusColor = (status: string): string => {
  const statusColors: Record<string, string> = {
    'completed': 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    'in_progress': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    'pending': 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    'not_started': 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    'customer_profile_selected': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    'value_map_generated': 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  };
  return statusColors[status] || 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
};

// Customer Profile Item Display
interface ProfileItemDisplayProps {
  items: CustomerProfileItem[];
  type: 'jtbd' | 'pain' | 'gain';
  icon: React.ElementType;
  title: string;
}

function ProfileItemDisplay({ items, type, icon: Icon, title }: ProfileItemDisplayProps) {
  const colorClasses = {
    jtbd: {
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      border: 'border-blue-200 dark:border-blue-800',
      text: 'text-blue-900 dark:text-blue-300',
      icon: 'text-blue-500',
    },
    pain: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-200 dark:border-red-800',
      text: 'text-red-900 dark:text-red-300',
      icon: 'text-red-500',
    },
    gain: {
      bg: 'bg-green-50 dark:bg-green-900/20',
      border: 'border-green-200 dark:border-green-800',
      text: 'text-green-900 dark:text-green-300',
      icon: 'text-green-500',
    },
  };

  const colors = colorClasses[type];

  if (!items || items.length === 0) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400 italic p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
        No {title.toLowerCase()} defined
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h4 className={`font-medium flex items-center gap-2 ${colors.text}`}>
        <Icon className={`w-4 h-4 ${colors.icon}`} />
        {title} ({items.length})
      </h4>
      <div className="space-y-2">
        {items.map((item, idx) => (
          <div 
            key={`${type}-${item.id}-${idx}`}
            className={`p-3 rounded-lg ${colors.bg} border ${colors.border}`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <p className={`font-medium text-sm ${colors.text}`}>{item.label}</p>
                {item.description && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    {item.description}
                  </p>
                )}
              </div>
              <Badge variant="outline" className="text-xs shrink-0">
                {Math.round((item.confidence || 0) * 100)}%
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Value Map Item Display
interface ValueMapItemDisplayProps {
  items: any[];
  type: 'products' | 'pain_relievers' | 'gain_creators';
  icon: React.ElementType;
  title: string;
}

function ValueMapItemDisplay({ items, type, icon: Icon, title }: ValueMapItemDisplayProps) {
  const colorClasses = {
    products: {
      bg: 'bg-indigo-50 dark:bg-indigo-900/20',
      border: 'border-indigo-200 dark:border-indigo-800',
      text: 'text-indigo-900 dark:text-indigo-300',
      icon: 'text-indigo-500',
    },
    pain_relievers: {
      bg: 'bg-orange-50 dark:bg-orange-900/20',
      border: 'border-orange-200 dark:border-orange-800',
      text: 'text-orange-900 dark:text-orange-300',
      icon: 'text-orange-500',
    },
    gain_creators: {
      bg: 'bg-emerald-50 dark:bg-emerald-900/20',
      border: 'border-emerald-200 dark:border-emerald-800',
      text: 'text-emerald-900 dark:text-emerald-300',
      icon: 'text-emerald-500',
    },
  };

  const colors = colorClasses[type];

  if (!items || items.length === 0) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400 italic p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
        No {title.toLowerCase()} defined
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h4 className={`font-medium flex items-center gap-2 ${colors.text}`}>
        <Icon className={`w-4 h-4 ${colors.icon}`} />
        {title} ({items.length})
      </h4>
      <div className="space-y-2">
        {items.map((item, idx) => (
          <div 
            key={`${type}-${item.id || idx}-${idx}`}
            className={`p-3 rounded-lg ${colors.bg} border ${colors.border}`}
          >
            <p className={`font-medium text-sm ${colors.text}`}>
              {item.label || item.name || item.text || 'Unnamed item'}
            </p>
            {item.description && (
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                {item.description}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Single Persona VPC View
interface PersonaVPCViewProps {
  persona: VPCPersona;
  isPrimary: boolean;
}

function PersonaVPCView({ persona, isPrimary }: PersonaVPCViewProps) {
  const hasCustomerProfile = persona.customer_profile && (
    persona.customer_profile.jobs_to_be_done?.length > 0 ||
    persona.customer_profile.pains?.length > 0 ||
    persona.customer_profile.gains?.length > 0
  );

  const hasValueMap = persona.value_map && (
    persona.value_map.products_services?.length > 0 ||
    persona.value_map.pain_relievers?.length > 0 ||
    persona.value_map.gain_creators?.length > 0
  );

  return (
    <div className="space-y-6">
      {/* Persona Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center">
            <User className="w-5 h-5 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {persona.persona_name || 'Unknown Persona'}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <Badge className={getStatusColor(persona.status)}>
                {persona.status?.replace(/_/g, ' ') || 'Unknown'}
              </Badge>
              {isPrimary && (
                <Badge className="bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">
                  Primary
                </Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* VPC Canvas Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Customer Profile Side */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-gray-200 dark:border-gray-700">
            <User className="w-5 h-5 text-blue-600" />
            <h4 className="font-semibold text-gray-900 dark:text-white">Customer Profile</h4>
          </div>
          
          {hasCustomerProfile ? (
            <div className="space-y-4">
              <ProfileItemDisplay
                items={persona.customer_profile?.jobs_to_be_done || []}
                type="jtbd"
                icon={Briefcase}
                title="Jobs to be Done"
              />
              <ProfileItemDisplay
                items={persona.customer_profile?.pains || []}
                type="pain"
                icon={AlertTriangle}
                title="Pains"
              />
              <ProfileItemDisplay
                items={persona.customer_profile?.gains || []}
                type="gain"
                icon={TrendingUp}
                title="Gains"
              />
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <User className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No customer profile data available</p>
            </div>
          )}
        </div>

        {/* Value Map Side */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-gray-200 dark:border-gray-700">
            <Package className="w-5 h-5 text-indigo-600" />
            <h4 className="font-semibold text-gray-900 dark:text-white">Value Map</h4>
          </div>
          
          {hasValueMap ? (
            <div className="space-y-4">
              <ValueMapItemDisplay
                items={persona.value_map?.products_services || []}
                type="products"
                icon={Package}
                title="Products & Services"
              />
              <ValueMapItemDisplay
                items={persona.value_map?.pain_relievers || []}
                type="pain_relievers"
                icon={Shield}
                title="Pain Relievers"
              />
              <ValueMapItemDisplay
                items={persona.value_map?.gain_creators || []}
                type="gain_creators"
                icon={Sparkles}
                title="Gain Creators"
              />
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <Package className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No value map data available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function VPCSection({ vpcData, readOnly = false, embedded = false }: VPCSectionProps) {
  const personas = vpcData?.vpcs ? Object.values(vpcData.vpcs) : [];
  const [activePersona, setActivePersona] = useState<string>(
    personas[0]?.persona_id || ''
  );

  // Empty state
  if (!vpcData || !vpcData.vpcs || personas.length === 0) {
    const emptyContent = (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <LayoutGrid className="w-16 h-16 mx-auto mb-4 opacity-30" />
        <p>The Value Proposition Canvas has not been created yet.</p>
      </div>
    );

    if (embedded) return emptyContent;

    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <LayoutGrid className="w-5 h-5 text-brand-600" />
            Value Proposition Canvas
          </CardTitle>
          <CardDescription>
            No VPC data available for this project
          </CardDescription>
        </CardHeader>
        <CardContent>{emptyContent}</CardContent>
      </Card>
    );
  }

  // Single persona - no tabs needed
  if (personas.length === 1) {
    const persona = personas[0];
    const content = (
      <PersonaVPCView 
        persona={persona} 
        isPrimary={persona.persona_id === vpcData.primary_persona_id}
      />
    );

    if (embedded) return content;

    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <LayoutGrid className="w-5 h-5 text-brand-600" />
            Value Proposition Canvas
          </CardTitle>
          <CardDescription className="flex items-center gap-2">
            <span>VPC for {persona.persona_name}</span>
            {vpcData.vpc_status && (
              <Badge className={getStatusColor(vpcData.vpc_status)}>
                {vpcData.vpc_status.replace(/_/g, ' ')}
              </Badge>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>{content}</CardContent>
      </Card>
    );
  }

  // Multiple personas - use tabs
  const tabsContent = (
    <Tabs value={activePersona} onValueChange={setActivePersona}>
      <TabsList className="mb-6">
        {personas.map((persona) => (
          <TabsTrigger 
            key={persona.persona_id} 
            value={persona.persona_id}
            className="flex items-center gap-2"
          >
            <User className="w-4 h-4" />
            {persona.persona_name || `Persona ${persona.persona_id}`}
            {persona.persona_id === vpcData.primary_persona_id && (
              <CheckCircle2 className="w-3 h-3 text-green-500" />
            )}
          </TabsTrigger>
        ))}
      </TabsList>
      
      {personas.map((persona) => (
        <TabsContent key={persona.persona_id} value={persona.persona_id}>
          <PersonaVPCView 
            persona={persona} 
            isPrimary={persona.persona_id === vpcData.primary_persona_id}
          />
        </TabsContent>
      ))}
    </Tabs>
  );

  if (embedded) return tabsContent;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-bold flex items-center gap-2">
          <LayoutGrid className="w-5 h-5 text-brand-600" />
          Value Proposition Canvas
        </CardTitle>
        <CardDescription className="flex items-center gap-2">
          <span>VPC data for {personas.length} personas</span>
          {vpcData.vpc_status && (
            <Badge className={getStatusColor(vpcData.vpc_status)}>
              {vpcData.vpc_status.replace(/_/g, ' ')}
            </Badge>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>{tabsContent}</CardContent>
    </Card>
  );
}

export default VPCSection;
