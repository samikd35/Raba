"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ProjectPersona } from '@/types/organization';
import { 
  User, 
  Users,
  Quote,
  Star,
  FileText
} from 'lucide-react';

export interface ProjectPersonasSectionProps {
  personas: ProjectPersona[];
  readOnly?: boolean;
}

// Single Persona Card
interface PersonaCardProps {
  persona: ProjectPersona;
  index: number;
}

function PersonaDisplayCard({ persona, index }: PersonaCardProps) {
  return (
    <div className="border rounded-lg p-6 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center">
            <User className="w-5 h-5 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {persona.name || `Persona ${index + 1}`}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="secondary" className="text-xs">
                {persona.id}
              </Badge>
              {persona.is_primary_payer && (
                <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 flex items-center gap-1">
                  <Star className="w-3 h-3" />
                  Primary Payer
                </Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Description */}
      {persona.description && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Description
          </h4>
          <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
            {persona.description}
          </p>
        </div>
      )}

      {/* Problem Relationship */}
      {persona.problem_relationship && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Problem Relationship
          </h4>
          <p className="text-sm text-gray-600 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg border border-blue-100 dark:border-blue-800">
            {persona.problem_relationship}
          </p>
        </div>
      )}

      {/* Evidence */}
      {persona.evidence && persona.evidence.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
            <Quote className="w-4 h-4" />
            Evidence ({persona.evidence.length})
          </h4>
          <div className="space-y-2">
            {persona.evidence.map((ev, idx) => (
              <div 
                key={idx}
                className="text-sm p-3 bg-gray-100 dark:bg-gray-800 rounded-lg border-l-2 border-brand-500"
              >
                <p className="text-gray-700 dark:text-gray-300 italic">"{ev.quote}"</p>
                {ev.source && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    — {ev.source}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function ProjectPersonasSection({ personas, readOnly = false }: ProjectPersonasSectionProps) {
  if (!personas || personas.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-bold flex items-center gap-2">
          <Users className="w-5 h-5 text-brand-600" />
          Identified Personas
        </CardTitle>
        <CardDescription>
          Target customer personas for this project ({personas.length} persona{personas.length > 1 ? 's' : ''})
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className={`grid gap-6 ${personas.length === 1 ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
          {personas.map((persona, index) => (
            <PersonaDisplayCard
              key={`persona-${persona.id}-${index}`}
              persona={persona}
              index={index}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default ProjectPersonasSection;
