"use client";

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { VPCPersona } from '@/types/organization';
import { Calendar, Briefcase, AlertTriangle, TrendingUp } from 'lucide-react';

export interface PersonaCardProps {
  persona: VPCPersona;
  index: number;
  readOnly?: boolean;
  showFullDetails?: boolean; // Show all items instead of truncated
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

// Format date helper
const formatDate = (dateString: string): string => {
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return 'N/A';
  }
};

export function PersonaCard({ persona, index, readOnly = false, showFullDetails = false }: PersonaCardProps) {
  const maxItems = showFullDetails ? 100 : 2; // Show all if full details, otherwise 2

  return (
    <div className="border rounded-lg p-6 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-brand-600 dark:text-white">
          {persona.persona_name || `Persona ${index + 1}`}
        </h3>
        <Badge className={getStatusColor(persona.status)}>
          {persona.status?.replace(/_/g, ' ') || 'Unknown'}
        </Badge>
      </div>

      {/* Customer Profile Sections */}
      {persona.customer_profile && (
        <div className="space-y-4">
          {/* Jobs to be Done */}
          {persona.customer_profile.jobs_to_be_done && persona.customer_profile.jobs_to_be_done.length > 0 && (
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-blue-500" />
                Jobs to be Done ({persona.customer_profile.jobs_to_be_done.length})
              </h4>
              <div className="space-y-2">
                {persona.customer_profile.jobs_to_be_done.slice(0, maxItems).map((job, jobIndex) => (
                  <div 
                    key={`job-${persona.persona_id}-${job.id}-${jobIndex}`} 
                    className="text-sm p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg"
                  >
                    <div className="font-medium text-blue-900 dark:text-blue-300 mb-1">
                      {job.label}
                    </div>
                    {job.description && (
                      <div className="text-blue-700 dark:text-blue-400 text-xs mb-1">
                        {job.description}
                      </div>
                    )}
                    <div className="text-blue-700 dark:text-blue-400 text-xs">
                      Confidence: {Math.round((job.confidence || 0) * 100)}%
                    </div>
                  </div>
                ))}
                {!showFullDetails && persona.customer_profile.jobs_to_be_done.length > maxItems && (
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    +{persona.customer_profile.jobs_to_be_done.length - maxItems} more
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Pains */}
          {persona.customer_profile.pains && persona.customer_profile.pains.length > 0 && (
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                Pains ({persona.customer_profile.pains.length})
              </h4>
              <div className="space-y-2">
                {persona.customer_profile.pains.slice(0, maxItems).map((pain, painIndex) => (
                  <div 
                    key={`pain-${persona.persona_id}-${pain.id}-${painIndex}`} 
                    className="text-sm p-3 bg-red-50 dark:bg-red-900/20 rounded-lg"
                  >
                    <div className="font-medium text-red-900 dark:text-red-300 mb-1">
                      {pain.label}
                    </div>
                    {pain.description && (
                      <div className="text-red-700 dark:text-red-400 text-xs mb-1">
                        {pain.description}
                      </div>
                    )}
                    <div className="text-red-700 dark:text-red-400 text-xs">
                      Confidence: {Math.round((pain.confidence || 0) * 100)}%
                    </div>
                  </div>
                ))}
                {!showFullDetails && persona.customer_profile.pains.length > maxItems && (
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    +{persona.customer_profile.pains.length - maxItems} more
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Gains */}
          {persona.customer_profile.gains && persona.customer_profile.gains.length > 0 && (
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-green-500" />
                Gains ({persona.customer_profile.gains.length})
              </h4>
              <div className="space-y-2">
                {persona.customer_profile.gains.slice(0, maxItems).map((gain, gainIndex) => (
                  <div 
                    key={`gain-${persona.persona_id}-${gain.id}-${gainIndex}`} 
                    className="text-sm p-3 bg-green-50 dark:bg-green-900/20 rounded-lg"
                  >
                    <div className="font-medium text-green-900 dark:text-green-300 mb-1">
                      {gain.label}
                    </div>
                    {gain.description && (
                      <div className="text-green-700 dark:text-green-400 text-xs mb-1">
                        {gain.description}
                      </div>
                    )}
                    <div className="text-green-700 dark:text-green-400 text-xs">
                      Confidence: {Math.round((gain.confidence || 0) * 100)}%
                    </div>
                  </div>
                ))}
                {!showFullDetails && persona.customer_profile.gains.length > maxItems && (
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    +{persona.customer_profile.gains.length - maxItems} more
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* No Customer Profile Message */}
      {!persona.customer_profile && (
        <div className="text-sm text-gray-500 dark:text-gray-400 italic">
          No customer profile data available
        </div>
      )}

      {/* Created Date */}
      <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
        <Calendar className="w-3 h-3" />
        Created: {formatDate(persona.created_at)}
      </div>
    </div>
  );
}

export default PersonaCard;
