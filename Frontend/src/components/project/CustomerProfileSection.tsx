"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { VPCPersona, CustomerProfileItem, Evidence } from '@/types/organization';
import { 
  Briefcase, 
  AlertTriangle, 
  TrendingUp, 
  ChevronDown, 
  ChevronUp,
  Quote,
  User
} from 'lucide-react';

export interface CustomerProfileSectionProps {
  personas: VPCPersona[];
  readOnly?: boolean;
}

// Evidence Item Component with expandable quotes
interface EvidenceDisplayProps {
  evidence: Evidence[];
  itemId: string;
}

function EvidenceDisplay({ evidence, itemId }: EvidenceDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="mt-2">
      <Button
        variant="ghost"
        size="sm"
        className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <Quote className="w-3 h-3 mr-1" />
        {evidence.length} evidence quote{evidence.length > 1 ? 's' : ''}
        {isExpanded ? (
          <ChevronUp className="w-3 h-3 ml-1" />
        ) : (
          <ChevronDown className="w-3 h-3 ml-1" />
        )}
      </Button>
      
      {isExpanded && (
        <div className="mt-2 space-y-2 pl-4 border-l-2 border-gray-200 dark:border-gray-700">
          {evidence.map((ev, idx) => (
            <div 
              key={`${itemId}-evidence-${idx}`}
              className="text-xs text-gray-600 dark:text-gray-400 italic"
            >
              <p className="mb-1">"{ev.quote}"</p>
              {ev.source && (
                <p className="text-gray-400 dark:text-gray-500 not-italic">
                  — {ev.source}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Customer Profile Item Component
interface ProfileItemProps {
  item: CustomerProfileItem;
  type: 'jtbd' | 'pain' | 'gain';
  index: number;
}

function ProfileItem({ item, type, index }: ProfileItemProps) {
  const colorClasses = {
    jtbd: {
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      label: 'text-blue-900 dark:text-blue-300',
      text: 'text-blue-700 dark:text-blue-400',
      border: 'border-blue-200 dark:border-blue-800',
    },
    pain: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      label: 'text-red-900 dark:text-red-300',
      text: 'text-red-700 dark:text-red-400',
      border: 'border-red-200 dark:border-red-800',
    },
    gain: {
      bg: 'bg-green-50 dark:bg-green-900/20',
      label: 'text-green-900 dark:text-green-300',
      text: 'text-green-700 dark:text-green-400',
      border: 'border-green-200 dark:border-green-800',
    },
  };

  const colors = colorClasses[type];

  return (
    <div className={`p-4 rounded-lg ${colors.bg} border ${colors.border}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className={`font-medium ${colors.label} mb-1`}>
            {item.label}
          </div>
          {item.description && (
            <div className={`text-sm ${colors.text} mb-2`}>
              {item.description}
            </div>
          )}
        </div>
        <Badge variant="outline" className={`text-xs ${colors.text} shrink-0`}>
          {Math.round((item.confidence || 0) * 100)}%
        </Badge>
      </div>
      
      {/* Evidence quotes */}
      <EvidenceDisplay evidence={item.evidence} itemId={item.id} />
    </div>
  );
}

// Single Persona Profile View
interface PersonaProfileViewProps {
  persona: VPCPersona;
}

function PersonaProfileView({ persona }: PersonaProfileViewProps) {
  if (!persona.customer_profile) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        No customer profile data available for this persona.
      </div>
    );
  }

  const { jobs_to_be_done, pains, gains } = persona.customer_profile;

  return (
    <div className="space-y-6">
      {/* Jobs to be Done */}
      {jobs_to_be_done && jobs_to_be_done.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-blue-500" />
            Jobs to be Done
            <Badge variant="secondary" className="ml-2">
              {jobs_to_be_done.length}
            </Badge>
          </h4>
          <div className="space-y-3">
            {jobs_to_be_done.map((job, idx) => (
              <ProfileItem 
                key={`jtbd-${job.id}-${idx}`} 
                item={job} 
                type="jtbd" 
                index={idx} 
              />
            ))}
          </div>
        </div>
      )}

      {/* Pains */}
      {pains && pains.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            Pains
            <Badge variant="secondary" className="ml-2">
              {pains.length}
            </Badge>
          </h4>
          <div className="space-y-3">
            {pains.map((pain, idx) => (
              <ProfileItem 
                key={`pain-${pain.id}-${idx}`} 
                item={pain} 
                type="pain" 
                index={idx} 
              />
            ))}
          </div>
        </div>
      )}

      {/* Gains */}
      {gains && gains.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-500" />
            Gains
            <Badge variant="secondary" className="ml-2">
              {gains.length}
            </Badge>
          </h4>
          <div className="space-y-3">
            {gains.map((gain, idx) => (
              <ProfileItem 
                key={`gain-${gain.id}-${idx}`} 
                item={gain} 
                type="gain" 
                index={idx} 
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function CustomerProfileSection({ personas, readOnly = false }: CustomerProfileSectionProps) {
  const [activePersona, setActivePersona] = useState<string>(
    personas[0]?.persona_id || ''
  );

  if (!personas || personas.length === 0) {
    return null;
  }

  // Single persona - no tabs needed
  if (personas.length === 1) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <User className="w-5 h-5 text-brand-600" />
            Customer Profile
          </CardTitle>
          <CardDescription>
            {personas[0].persona_name} - Customer jobs, pains, and gains
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PersonaProfileView persona={personas[0]} />
        </CardContent>
      </Card>
    );
  }

  // Multiple personas - use tabs
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-bold flex items-center gap-2">
          <User className="w-5 h-5 text-brand-600" />
          Customer Profiles
        </CardTitle>
        <CardDescription>
          Customer jobs, pains, and gains for each persona
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={activePersona} onValueChange={setActivePersona}>
          <TabsList className="mb-4">
            {personas.map((persona) => (
              <TabsTrigger 
                key={persona.persona_id} 
                value={persona.persona_id}
                className="flex items-center gap-2"
              >
                <User className="w-4 h-4" />
                {persona.persona_name || `Persona ${persona.persona_id}`}
              </TabsTrigger>
            ))}
          </TabsList>
          
          {personas.map((persona) => (
            <TabsContent key={persona.persona_id} value={persona.persona_id}>
              <PersonaProfileView persona={persona} />
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}

export default CustomerProfileSection;
