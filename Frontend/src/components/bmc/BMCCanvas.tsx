"use client";

import React, { useMemo, useState, useCallback, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Building2,
  Handshake,
  Target,
  Zap,
  Heart,
  DollarSign,
  TrendingUp,
  Network,
  Users,
  ChevronDown,
  ChevronUp,
  Edit2,
  Trash2,
  Plus
} from "lucide-react";
import { BMCBlock } from "./BMCBlock";
import { BMCData } from "@/types/bmc";
import { BMCBlockName, BMCEditItem } from "@/hooks/useBMC";

// Correlation colors for matching Value Propositions with Customer Segments
// These are distinct, visually appealing colors that work well as backgrounds
const SEGMENT_CORRELATION_COLORS = [
  { bg: 'bg-yellow-100 dark:bg-yellow-700/20', border: 'border-yellow-400 dark:border-yellow-500' },
  { bg: 'bg-sky-100 dark:bg-green-800/30', border: 'border-sky-400 dark:border-green-600' },
  { bg: 'bg-amber-100 dark:bg-blue-700/25', border: 'border-amber-400 dark:border-blue-500' },
  { bg: 'bg-emerald-100 dark:bg-blue-900/40', border: 'border-emerald-400 dark:border-blue-700' },
  { bg: 'bg-orange-100 dark:bg-amber-700/20', border: 'border-orange-400 dark:border-amber-500' },
  { bg: 'bg-lime-100 dark:bg-blue-800/35', border: 'border-lime-400 dark:border-blue-600' },
  { bg: 'bg-cyan-100 dark:bg-yellow-600/15', border: 'border-cyan-400 dark:border-yellow-400' },
  { bg: 'bg-teal-100 dark:bg-amber-900/45', border: 'border-teal-400 dark:border-amber-700' },
];

interface BMCCanvasProps {
  bmcData: BMCData;
  compact?: boolean;
  fullscreen?: boolean;
  // Edit mode props
  isEditMode?: boolean;
  onEditItem?: (blockName: BMCBlockName, item: BMCEditItem) => void;
  onDeleteItem?: (blockName: BMCBlockName, itemId: string, itemName: string) => void;
  onAddItem?: (blockName: BMCBlockName) => void;
}

export const BMCCanvas: React.FC<BMCCanvasProps> = ({ 
  bmcData, 
  compact = false, 
  fullscreen = false,
  isEditMode = false,
  onEditItem,
  onDeleteItem,
  onAddItem
}) => {
  // State for managing expanded sections in fullscreen mode
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  // All section IDs for expanding/collapsing
  const allSectionIds = [
    'key-partners',
    'key-activities', 
    'key-resources',
    'value-propositions',
    'customer-relationships',
    'customer-segments',
    'channels',
    'cost-structure',
    'revenue-streams'
  ];

  // Auto-expand all sections when edit mode is enabled, collapse when disabled
  useEffect(() => {
    if (isEditMode) {
      const allExpanded: Record<string, boolean> = {};
      allSectionIds.forEach(id => {
        allExpanded[id] = true;
      });
      setExpandedSections(allExpanded);
    } else {
      // Collapse all sections when exiting edit mode
      setExpandedSections({});
    }
  }, [isEditMode]);

  // Defensive data extraction with fallbacks (handles both standard and 'items' field names from API)
  // Also normalizes v2 field names to v1 field names for consistency
  const rawPartnerships = bmcData?.key_partnerships?.partnerships || bmcData?.key_partnerships?.items || [];
  const rawActivities = bmcData?.key_activities?.activities || bmcData?.key_activities?.items || [];
  const rawPropositions = bmcData?.value_propositions?.propositions || bmcData?.value_propositions?.items || [];
  const rawRelationships = bmcData?.customer_relationships?.relationships || bmcData?.customer_relationships?.items || [];
  const rawSegments = bmcData?.customer_segments?.segments || bmcData?.customer_segments?.items || [];
  const rawResources = bmcData?.key_resources?.resources || bmcData?.key_resources?.items || [];
  const rawChannels = bmcData?.channels?.channels || bmcData?.channels?.items || [];
  const rawRevenueStreams = bmcData?.revenue_streams?.revenue_streams || bmcData?.revenue_streams?.items || [];
  
  // Handle both v1 and v2 cost structure formats:
  // v1: cost_structure.cost_structure.cost_categories (array of categories)
  // v2: cost_structure.items (array of cost items directly)
  const rawCostStructure: any = bmcData?.cost_structure?.cost_structure || bmcData?.cost_structure || {};
  const costStructure = {
    model_type: rawCostStructure?.model_type || '',
    economies_of_scale: rawCostStructure?.economies_of_scale || '',
    cost_categories: rawCostStructure?.cost_categories || []
  };
  // For v2, items array IS the cost categories (not nested)
  const rawCostCategories = (rawCostStructure as any)?.cost_categories || bmcData?.cost_structure?.items || [];
  
  // Normalize cost categories for consistent rendering
  const costCategories = rawCostCategories.map((c: any) => ({
    ...c,
    name: c.name || c.category_name || 'Unknown Cost',
    type: c.type || 'Fixed',
    description: c.description || ''
  }));

  // Normalize v2 field names to v1 field names for consistent rendering
  const segments = rawSegments.map((s: any) => ({
    ...s,
    name: s.name || s.segment_name || 'Unknown Segment',
    description: s.description || '',
    size_estimate: s.size_estimate || '',
    priority: s.priority || 'Medium'
  }));

  const propositions = rawPropositions.map((p: any) => ({
    ...p,
    name: p.name || p.proposition || 'Unknown Proposition',
    value_statement: p.value_statement || p.proposition || '',
    segment_ids: p.segment_ids || (p.customer_segment_id ? [p.customer_segment_id] : []),
    // v2 uses pain_relievers/gain_creators instead of key_benefits
    key_benefits: p.key_benefits || [...(p.pain_relievers || []), ...(p.gain_creators || [])]
  }));

  const partnerships = rawPartnerships.map((p: any) => ({
    ...p,
    name: p.name || p.partner_name || 'Unknown Partner',
    value_contribution: p.value_contribution || p.description || ''
  }));

  const activities = rawActivities.map((a: any) => ({
    ...a,
    name: a.name || a.activity_name || 'Unknown Activity',
    description: a.description || ''
  }));

  const relationships = rawRelationships.map((r: any) => ({
    ...r,
    name: r.name || r.relationship_type || 'Unknown Relationship',
    description: r.description || ''
  }));

  const resources = rawResources.map((r: any) => ({
    ...r,
    name: r.name || r.resource_name || 'Unknown Resource',
    description: r.description || ''
  }));

  const channels = rawChannels.map((c: any) => ({
    ...c,
    name: c.name || c.channel_name || 'Unknown Channel',
    description: c.description || ''
  }));

  const revenueStreams = rawRevenueStreams.map((r: any) => ({
    ...r,
    name: r.name || r.stream_name || 'Unknown Revenue Stream',
    pricing_strategy: r.pricing_strategy || r.description || ''
  }));

  // Create a mapping of segment IDs to colors
  const segmentColorMap = useMemo(() => {
    const map: Record<string, { bg: string; border: string }> = {};
    segments.forEach((segment, index) => {
      map[segment.id] = SEGMENT_CORRELATION_COLORS[index % SEGMENT_CORRELATION_COLORS.length];
    });
    return map;
  }, [segments]);

  // Get the correlation color for a Value Proposition based on its segment_ids
  // If VP targets multiple segments, use the first one's color
  const getVPCorrelationStyle = (segmentIds: string[] | undefined): { bg: string; border: string } | null => {
    if (!segmentIds || segmentIds.length === 0) return null;
    return segmentColorMap[segmentIds[0]] || null;
  };

  // Get the correlation color for a Customer Segment
  const getSegmentCorrelationStyle = (segmentId: string): { bg: string; border: string } | null => {
    return segmentColorMap[segmentId] || null;
  };

  // Toggle function for expanding/collapsing sections
  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionId]: !prev[sectionId]
    }));
    
    // Scroll to the section after a brief delay to allow DOM update
    setTimeout(() => {
      const element = document.getElementById(`section-${sectionId}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }, 100);
  };

  // Map section IDs to block names
  const sectionToBlockName: Record<string, BMCBlockName> = {
    'key-partners': 'key_partnerships',
    'key-activities': 'key_activities',
    'key-resources': 'key_resources',
    'value-propositions': 'value_propositions',
    'customer-relationships': 'customer_relationships',
    'customer-segments': 'customer_segments',
    'channels': 'channels',
    'cost-structure': 'cost_structure',
    'revenue-streams': 'revenue_streams'
  };

  // Tile-based component for fullscreen mode
  const TileSection: React.FC<{
    id: string;
    title: string;
    icon: React.ComponentType<any>;
    className: string;
    children: React.ReactNode;
    count: number;
  }> = ({ id, title, icon: Icon, className, children, count }) => {
    const isExpanded = expandedSections[id];
    const childrenArray = React.Children.toArray(children);
    const blockName = sectionToBlockName[id];
    
    return (
      <div 
        id={`section-${id}`}
        className={`rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow duration-200 p-4 h-full flex flex-col ${className} ${isEditMode ? 'ring-1 ring-green-400 dark:ring-green-600' : ''}`}
      >
        <div className="flex items-center gap-2 mb-4 pb-2 border-b border-brand-200 dark:border-gray-700">
          <div className="p-2 bg-gradient-to-br from-brand-50 to-brand-100 dark:from-brand-900/30 dark:to-brand-800/30 rounded-lg">
            <Icon className="w-5 h-5 text-brand-600 dark:text-brand-400" />
          </div>
          <h3 className="font-semibold text-brand-500 dark:text-white tracking-wide text-md flex-1">{title}</h3>
          <Badge variant="secondary" className="text-xs">
            {count}
          </Badge>
          {/* Add Item Button - only in edit mode */}
          {isEditMode && onAddItem && blockName && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onAddItem(blockName)}
              className="h-7 w-7 p-0 text-green-600 hover:text-green-700 hover:bg-green-100 dark:text-green-400 dark:hover:bg-green-900/30"
              title={`Add ${title.slice(0, -1)}`}
            >
              <Plus className="w-4 h-4" />
            </Button>
          )}
        </div>
        
        {isExpanded ? (
          <div className={`space-y-3 text-xs flex-1 ${!['key-partners', 'value-propositions', 'customer-segments'].includes(id) ? 'overflow-y-auto max-h-[500px] pr-2' : ''}`}>
            {children}
            
          </div>
        ) : (
          <div className="space-y-2 flex-1">
            {childrenArray.map((child, index) => {
              if (React.isValidElement(child)) {
                // Extract the name/title and styling from the child element
                const childProps = child.props as any;
                let childClassName = childProps.className || '';
                
                // If wrapped in EditableItemWrapper, look for the inner styled div
                const innerChildren = childProps.children;
                if (React.isValidElement(innerChildren)) {
                  const innerClassName = (innerChildren.props as any)?.className || '';
                  if (innerClassName) {
                    childClassName = innerClassName;
                  }
                } else if (Array.isArray(innerChildren)) {
                  // Find the first element with correlation styles
                  for (const innerChild of innerChildren) {
                    if (React.isValidElement(innerChild)) {
                      const innerClassName = (innerChild.props as any)?.className || '';
                      if (innerClassName && (innerClassName.includes('border-') || innerClassName.includes('bg-'))) {
                        childClassName = innerClassName;
                        break;
                      }
                    }
                  }
                }
                
                // Extract actual background color from the detailed card
                let itemBgColor = 'bg-white dark:bg-gray-800';
                let itemBorderColor = 'border-gray-300 dark:border-gray-600';
                
                // Try to extract correlation style from className
                const bgClasses = [
                  'bg-rose-100', 'bg-sky-100', 'bg-amber-100', 'bg-emerald-100',
                  'bg-violet-100', 'bg-fuchsia-100', 'bg-cyan-100', 'bg-lime-100',
                  'bg-blue-50', 'bg-green-50', 'bg-brand-50', 'bg-purple-50',
                  'bg-orange-50', 'bg-indigo-50', 'bg-teal-50', 'bg-red-50',
                  'bg-pink-50', 'bg-white'
                ];
                
                const darkBgClasses = [
                  'dark:bg-yellow-700/20', 'dark:bg-green-800/30', 'dark:bg-blue-700/25', 'dark:bg-blue-900/40',
                  'dark:bg-amber-700/20', 'dark:bg-blue-800/35', 'dark:bg-yellow-600/15', 'dark:bg-amber-900/45',
                  'dark:bg-blue-900/20', 'dark:bg-green-900/20', 'dark:bg-brand-900/30', 'dark:bg-purple-900/20',
                  'dark:bg-orange-900/20', 'dark:bg-indigo-900/20', 'dark:bg-teal-900/20', 'dark:bg-emerald-900/20',
                  'dark:bg-gray-800/80', 'dark:bg-gray-800'
                ];
                
                // Find and extract the background color classes
                const extractedBgClasses = bgClasses.filter(cls => childClassName.includes(cls));
                const extractedDarkBgClasses = darkBgClasses.filter(cls => childClassName.includes(cls));
                
                if (extractedBgClasses.length > 0) {
                  itemBgColor = extractedBgClasses.join(' ');
                }
                
                // Combine light and dark mode background classes
                if (extractedDarkBgClasses.length > 0) {
                  itemBgColor += ' ' + extractedDarkBgClasses.join(' ');
                }
                
                // Extract border color from the detailed card
                const borderClasses = [
                  'border-blue-500', 'border-green-500', 'border-brand-500', 'border-purple-500',
                  'border-orange-500', 'border-indigo-500', 'border-teal-500', 'border-red-500',
                  'border-emerald-500', 'border-rose-400', 'border-sky-400', 'border-amber-400',
                  'border-emerald-400', 'border-violet-400', 'border-fuchsia-400', 'border-cyan-400',
                  'border-lime-400'
                ];
                
                const darkBorderClasses = [
                  'dark:border-blue-600', 'dark:border-green-600', 'dark:border-brand-600', 'dark:border-purple-600',
                  'dark:border-orange-600', 'dark:border-indigo-600', 'dark:border-teal-600', 'dark:border-emerald-600',
                  'dark:border-yellow-500', 'dark:border-yellow-400', 'dark:border-blue-500', 'dark:border-blue-700',
                  'dark:border-amber-500', 'dark:border-amber-600', 'dark:border-amber-700', 'dark:border-gray-600'
                ];
                
                const extractedBorderClasses = borderClasses.filter(cls => childClassName.includes(cls));
                const extractedDarkBorderClasses = darkBorderClasses.filter(cls => childClassName.includes(cls));
                
                if (extractedBorderClasses.length > 0) {
                  itemBorderColor = extractedBorderClasses.join(' ');
                }
                
                if (extractedDarkBorderClasses.length > 0) {
                  itemBorderColor += ' ' + extractedDarkBorderClasses.join(' ');
                }
                
                // Safely extract name from children (could be array, single element, or wrapped)
                let name = `Item ${index + 1}`;
                const childrenToSearch = childProps.children;
                
                // Convert children to array for safe iteration
                const childrenArray = Array.isArray(childrenToSearch) 
                  ? childrenToSearch 
                  : childrenToSearch 
                    ? [childrenToSearch] 
                    : [];
                
                // Try to find the name element
                const nameElement = childrenArray.find((c: any) => 
                  React.isValidElement(c) && (
                    (c.props as any)?.className?.includes('font-semibold') || 
                    (c.props as any)?.className?.includes('font-bold')
                  )
                );
                
                if (nameElement) {
                  name = (nameElement.props as any)?.children || name;
                } else {
                  // If wrapped in EditableItemWrapper, look deeper
                  const firstChild = childrenArray[0];
                  if (React.isValidElement(firstChild)) {
                    const innerChildren = (firstChild.props as any)?.children;
                    const innerArray = Array.isArray(innerChildren) ? innerChildren : innerChildren ? [innerChildren] : [];
                    const innerNameElement = innerArray.find((c: any) =>
                      React.isValidElement(c) && (
                        (c.props as any)?.className?.includes('font-semibold') ||
                        (c.props as any)?.className?.includes('font-bold')
                      )
                    );
                    if (innerNameElement) {
                      name = (innerNameElement.props as any)?.children || name;
                    }
                  }
                }
                
                return (
                  <div 
                    key={index} 
                    className={`${itemBgColor} rounded-lg p-2 border ${itemBorderColor} hover:shadow-sm transition-all overflow-hidden`}
                  >
                    <div className="font-medium text-gray-900 dark:text-white text-sm truncate" title={name}>
                      {name}
                    </div>
                  </div>
                );
              }
              return null;
            })}
          </div>
        )}

        <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-600">
          <Button
            variant="outline"
            size="sm"
            onClick={() => toggleSection(id)}
            className="w-full bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:from-gray-100 hover:to-gray-200 dark:hover:from-gray-700 dark:hover:to-gray-600 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-gray-100 shadow-sm hover:shadow-md transition-all duration-200"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4 mr-2" />
                <span className="font-medium">Hide Details</span>
                <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">({count} items)</span>
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4 mr-2" />
                <span className="font-medium">View Details</span>
                <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">({count} items)</span>
              </>
            )}
          </Button>
        </div>
      </div>
    );
  };

  // Wrapper component for editable items in fullscreen mode
  const EditableItemWrapper: React.FC<{
    blockName: BMCBlockName;
    item: any;
    children: React.ReactNode;
    className?: string;
  }> = ({ blockName, item, children, className = '' }) => {
    const editItem: BMCEditItem = {
      id: item.id,
      name: item.name,
      description: item.description || item.value_contribution || item.value_statement || item.pricing_strategy || '',
      evidence: item.evidence_source,
      ...item
    };

    return (
      <div className={`relative group ${className}`}>
        {children}
        {/* Edit/Delete buttons overlay - only in edit mode */}
        {isEditMode && (
          <div className="absolute top-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {onEditItem && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onEditItem(blockName, editItem);
                }}
                className="h-6 w-6 p-0 bg-white/90 dark:bg-gray-800/90 text-blue-600 hover:text-blue-700 hover:bg-blue-100 dark:text-blue-400 dark:hover:bg-blue-900/30 shadow-sm"
                title="Edit"
              >
                <Edit2 className="w-3 h-3" />
              </Button>
            )}
            {onDeleteItem && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteItem(blockName, item.id, item.name);
                }}
                className="h-6 w-6 p-0 bg-white/90 dark:bg-gray-800/90 text-red-600 hover:text-red-700 hover:bg-red-100 dark:text-red-400 dark:hover:bg-red-900/30 shadow-sm"
                title="Delete"
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            )}
          </div>
        )}
      </div>
    );
  };

  if (fullscreen) {
    return (
      <div className="bg-gradient-to-br from-gray-50 to-white dark:from-gray-900 dark:to-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-lg p-4">
        <div className="grid grid-cols-5 gap-4">
          {/* Row 1 */}
          <TileSection
            id="key-partners"
            title="Key Partners"
            icon={Handshake}
            className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-700 row-span-2"
            count={partnerships.length}
          >
            {partnerships.map((partnership) => (
              <EditableItemWrapper key={partnership.id} blockName="key_partnerships" item={partnership}>
                <div 
                  className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-blue-500 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="font-semibold text-gray-900 dark:text-white text-sm mb-1 break-words">
                    {partnership.name}
                  </div>
                  <Badge variant="secondary" className="text-xs mb-2 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                    {partnership.partner_type}
                  </Badge>
                  <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed break-words">
                    {partnership.value_contribution}
                  </div>
                </div>
              </EditableItemWrapper>
            ))}
          </TileSection>

          <TileSection
            id="key-activities"
            title="Key Activities"
            icon={Zap}
            className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-700"
            count={activities.length}
          >
            {activities.map((activity) => (
              <EditableItemWrapper key={activity.id} blockName="key_activities" item={activity}>
                <div 
                  className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-blue-500 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words">
                    {activity.name}
                  </div>
                  <Badge variant="secondary" className="text-xs mb-2 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                    {activity.criticality}
                  </Badge>
                  <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed break-words">
                    {activity.description}
                  </div>
                </div>
              </EditableItemWrapper>
            ))}
          </TileSection>

          <TileSection
            id="value-propositions"
            title="Value Propositions"
            icon={Heart}
            className="bg-brand-50 border-brand-300 dark:bg-brand-900/30 dark:border-brand-600 row-span-2"
            count={propositions.length}
          >
            {propositions.map((vp) => {
              const correlationStyle = getVPCorrelationStyle(vp.segment_ids);
              return (
                <EditableItemWrapper key={vp.id} blockName="value_propositions" item={vp}>
                  <div 
                    className={`rounded-lg p-2 shadow-md hover:shadow-lg transition-shadow ${correlationStyle ? `${correlationStyle.bg} ${correlationStyle.border}` : 'bg-white border-brand-500'} border`}
                  >
                    <div className="font-bold text-gray-900 dark:text-white text-sm mb-2 break-words">
                      {vp.name}
                    </div>
                    <div className="text-gray-700 dark:text-gray-300 text-xs leading-relaxed mb-3 break-words">
                      {vp.value_statement}
                    </div>
                    <div className="space-y-2">
                      {vp.key_benefits.map((benefit, idx) => (
                        <div key={idx} className="text-xs bg-white/50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 rounded px-2 py-1 break-words">
                          {benefit}
                        </div>
                      ))}
                    </div>
                  </div>
                </EditableItemWrapper>
              );
            })}
          </TileSection>

          <TileSection
            id="customer-relationships"
            title="Customer Relationships"
            icon={Users}
            className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200 dark:border-purple-700"
            count={relationships.length}
          >
            {relationships.map((rel) => (
              <EditableItemWrapper key={rel.id} blockName="customer_relationships" item={rel}>
                <div 
                  className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-purple-500 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words">
                    {rel.name}
                  </div>
                  <Badge variant="secondary" className="text-xs mb-2 bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                    {rel.type}
                  </Badge>
                  <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed break-words">
                    {rel.description}
                  </div>
                </div>
              </EditableItemWrapper>
            ))}
          </TileSection>

          <TileSection
            id="customer-segments"
            title="Customer Segments"
            icon={Target}
            className="bg-orange-50 dark:bg-brand-900/30 border-orange-200 dark:border-brand-600 row-span-2"
            count={segments.length}
          >
            {segments.map((segment) => {
              const correlationStyle = getSegmentCorrelationStyle(segment.id);
              return (
                <EditableItemWrapper key={segment.id} blockName="customer_segments" item={segment}>
                  <div 
                    className={`rounded-lg p-2 shadow-sm hover:shadow-md transition-shadow ${correlationStyle ? `${correlationStyle.bg} ${correlationStyle.border}` : 'bg-white dark:bg-gray-800 border-brand-500'} border`}
                  >
                    <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words">
                      {segment.name}
                    </div>
                    <Badge variant="secondary" className="text-xs mb-2 bg-white/50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300">
                      {segment.priority}
                    </Badge>
                    <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed mb-2 break-words">
                      {segment.description}
                    </div>
                    <div className="text-gray-700 dark:text-gray-300 text-xs bg-white/50 dark:bg-gray-700/50 rounded px-2 py-1">
                      <span className="font-semibold">Size:</span> {segment.size_estimate}
                    </div>
                  </div>
                </EditableItemWrapper>
              );
            })}
          </TileSection>

          {/* Row 2 */}
          <TileSection
            id="key-resources"
            title="Key Resources"
            icon={Building2}
            className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-700"
            count={resources.length}
          >
            {resources.map((resource) => (
              <EditableItemWrapper key={resource.id} blockName="key_resources" item={resource}>
                <div 
                  className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-blue-500 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words">
                    {resource.name}
                  </div>
                  <div className="flex gap-1 mb-2">
                    <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                      {resource.type}
                    </Badge>
                    <Badge variant="outline" className="text-xs border-blue-300 text-blue-600 dark:border-blue-600 dark:text-blue-400">
                      {resource.criticality}
                    </Badge>
                  </div>
                  <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed break-words">
                    {resource.description}
                  </div>
                </div>
              </EditableItemWrapper>
            ))}
          </TileSection>

          <TileSection
            id="channels"
            title="Channels"
            icon={Network}
            className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200 dark:border-purple-700"
            count={channels.length}
          >
            {channels.map((channel) => (
              <EditableItemWrapper key={channel.id} blockName="channels" item={channel}>
                <div 
                  className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-purple-500 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words">
                    {channel.name}
                  </div>
                  <div className="flex gap-2 mb-3">
                    <Badge variant="secondary" className="text-xs bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                      {channel.type}
                    </Badge>
                    <Badge variant="outline" className="text-xs border-purple-300 text-purple-600 dark:border-purple-600 dark:text-purple-400">
                      {channel.cost_structure}
                    </Badge>
                  </div>
                  <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed mb-2 break-words">
                    {channel.description}
                  </div>
                  <div className="text-brand-500 dark:text-gray-500 text-xs bg-brand-50 dark:bg-gray-700 rounded px-2 py-1">
                    <span className="font-semibold">Reach:</span> {channel.reach_potential}
                  </div>
                </div>
              </EditableItemWrapper>
            ))}
          </TileSection>

          {/* Row 3 */}
          <TileSection
            id="cost-structure"
            title="Cost Structure"
            icon={TrendingUp}
            className="col-span-2 bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/20 dark:to-emerald-800/20 border-emerald-200 dark:border-emerald-700"
            count={costCategories.length + 1}
          >
            {/* <div className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-emerald-500 dark:border-emerald-600 shadow-sm hover:shadow-md transition-shadow">
              <div className="font-bold text-gray-900 dark:text-white mb-2 text-sm">
                Model Type
              </div>
              <Badge className="mb-2 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 text-xs">
                {costStructure?.model_type || ''}
              </Badge>
              <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed break-words">
                <span className="font-medium dark:text-gray-300">Economies of Scale:</span><br/>
                {costStructure?.economies_of_scale || ''}
              </div>
            </div> */}
            {costCategories.map((cost) => (
              <EditableItemWrapper key={cost.id} blockName="cost_structure" item={cost}>
                <div 
                  className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-emerald-500 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="font-semibold text-gray-900 dark:text-white text-xs mb-1 break-words">
                    {cost.name}
                  </div>
                  <Badge variant="secondary" className="text-xs mb-1 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                    {cost.type}
                  </Badge>
                  <div className="text-gray-700 dark:text-gray-300 text-xs font-medium mb-1">
                    {cost.cost_estimate}
                  </div>
                  <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed break-words">
                    {cost.description}
                  </div>
                </div>
              </EditableItemWrapper>
            ))}
          </TileSection>

          <TileSection
            id="revenue-streams"
            title="Revenue Streams"
            icon={DollarSign}
            className="col-span-3 bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/20 dark:to-emerald-800/20 border-emerald-200 dark:border-emerald-700"
            count={revenueStreams.length}
          >
            {revenueStreams.map((stream) => (
              <EditableItemWrapper key={stream.id} blockName="revenue_streams" item={stream}>
                <div 
                  className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-emerald-500 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words">
                    {stream.name}
                  </div>
                  <div className="flex gap-1 mb-2">
                    <Badge variant="secondary" className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                      {stream.type}
                    </Badge>
                    <Badge variant="outline" className="text-xs border-emerald-300 text-emerald-600 dark:border-emerald-600 dark:text-emerald-400">
                      {stream.pricing_mechanism}
                    </Badge>
                  </div>
                  <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed mb-2 break-words">
                    {stream.pricing_strategy}
                  </div>
                  <div className="text-brand-500 dark:text-brand-500 text-xs bg-brand-50 dark:bg-gray-700 rounded px-2 py-1">
                    <span className="font-semibold">Potential:</span> {stream.revenue_potential}
                  </div>
                </div>
              </EditableItemWrapper>
            ))}
          </TileSection>
        </div>
      </div>
    );
  }

  if (compact) {
    return (
      <div className="bg-gradient-to-br from-gray-50 to-white dark:from-gray-900 dark:to-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-lg p-2  overflow-hidden">
        <div className="grid grid-cols-5 gap-1 h-full text-xs">
          {/* Row 1 - Compact */}
          <BMCBlock title="Key Partners" icon={Handshake} className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-700 row-span-2 h-full" compact={true}>
            <div className="space-y-1">
              {partnerships.map((partnership) => (
                <div key={partnership.id} className="bg-white dark:bg-gray-800 rounded p-1 border border-blue-500 shadow-sm">
                  <div className="font-medium text-gray-900 dark:text-white text-xs truncate">
                    {partnership.name}
                  </div>
                </div>
              ))}
            </div>
          </BMCBlock>

          <BMCBlock title="Key Activities" icon={Zap} className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-700 h-full" compact={true}>
            <div className="space-y-1">
              {activities.map((activity) => (
                <div key={activity.id} className="bg-white dark:bg-gray-800 rounded p-1 border border-blue-500 shadow-sm">
                  <div className="font-medium text-gray-900 dark:text-white text-xs truncate">
                    {activity.name}
                  </div>
                </div>
              ))}
            </div>
          </BMCBlock>

          <BMCBlock title="Value Propositions" icon={Heart} className="bg-brand-50 border-brand-300 dark:bg-brand-900/30 dark:border-brand-600 row-span-2 h-full" compact={true}>
            <div className="space-y-1 ">
              {propositions.map((proposition) => {
                const correlationStyle = getVPCorrelationStyle(proposition.segment_ids);
                return (
                  <div 
                    key={proposition.id} 
                    className={`rounded p-1 shadow-md ${correlationStyle ? `${correlationStyle.bg} ${correlationStyle.border}` : 'bg-white dark:bg-gray-800/80 border-brand-500 dark:border-brand-600'} border`}
                  >
                    <div className="font-semibold text-gray-900 dark:text-white text-xs truncate">
                      {proposition.name}
                    </div>
                  </div>
                );
              })}
            </div>
          </BMCBlock>

          <BMCBlock title="Customer Relationships" icon={Users} className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200 dark:border-purple-700 h-full" compact={true}>
            <div className="space-y-1">
              {relationships.map((relationship) => (
                <div key={relationship.id} className="bg-white dark:bg-gray-800 rounded p-1 border border-purple-500 shadow-sm">
                  <div className="font-medium text-gray-900 dark:text-white text-xs truncate">
                    {relationship.name}
                  </div>
                </div>
              ))}
            </div>
          </BMCBlock>

          <BMCBlock title="Customer Segments" icon={Target} className="bg-orange-50 dark:bg-brand-900/30 border-orange-200 dark:border-brand-600 row-span-2 h-full" compact={true}>
            <div className="space-y-1">
              {segments.map((segment) => {
                const correlationStyle = getSegmentCorrelationStyle(segment.id);
                return (
                  <div 
                    key={segment.id} 
                    className={`rounded p-1 shadow-sm ${correlationStyle ? `${correlationStyle.bg} ${correlationStyle.border}` : 'bg-white dark:bg-gray-800 border-brand-500'} border`}
                  >
                    <div className="font-medium text-gray-900 dark:text-white text-xs truncate">
                      {segment.name}
                    </div>
                  </div>
                );
              })}
            </div>
          </BMCBlock>

          {/* Row 2 - Compact */}
          <BMCBlock title="Key Resources" icon={Building2} className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-700 h-full" compact={true}>
            <div className="space-y-1">
              {resources.map((resource) => (
                <div key={resource.id} className="bg-white dark:bg-gray-800 rounded p-1 border border-blue-500 shadow-sm">
                  <div className="font-medium text-gray-900 dark:text-white text-xs truncate">
                    {resource.name}
                  </div>
                </div>
              ))}
            </div>
          </BMCBlock>

          <BMCBlock title="Channels" icon={Network} className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200 dark:border-purple-700 h-full" compact={true}>
            <div className="space-y-1">
              {channels.map((channel) => (
                <div key={channel.id} className="bg-white dark:bg-gray-800 rounded p-1 border border-purple-500 shadow-sm">
                  <div className="font-medium text-gray-900 dark:text-white text-xs truncate">
                    {channel.name}
                  </div>
                </div>
              ))}
            </div>
          </BMCBlock>

          {/* Row 3 - Compact */}
          <BMCBlock title="Cost Structure" icon={TrendingUp} className="col-span-2 bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/20 dark:to-emerald-800/20 border-emerald-200 dark:border-emerald-700 h-full" compact={true}>
            <div className="space-y-1">
              {costStructure?.model_type && (
                <div className="bg-white dark:bg-gray-800 rounded p-1 border border-emerald-500 shadow-sm">
                  <div className="font-semibold text-gray-900 dark:text-white text-xs truncate">
                    {costStructure.model_type}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-1">
                {costCategories.map((category) => (
                  <div key={category.id} className="bg-white dark:bg-gray-800 rounded p-1 border border-emerald-500 shadow-sm">
                    <div className="font-medium text-gray-900 dark:text-white text-xs truncate">
                      {category.name}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </BMCBlock>

          <BMCBlock title="Revenue Streams" icon={DollarSign} className="col-span-3 bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/20 dark:to-emerald-800/20 border-emerald-200 dark:border-emerald-700 h-full" compact={true}>
            <div className="grid grid-cols-2 gap-1 h-full">
              {revenueStreams.map((stream) => (
                <div key={stream.id} className="bg-white dark:bg-gray-800 rounded p-1 border border-emerald-500 shadow-sm">
                  <div className="font-medium text-gray-900 dark:text-white text-xs truncate">
                    {stream.name}
                  </div>
                </div>
              ))}
            </div>
          </BMCBlock>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-gray-50 to-white dark:from-gray-900 dark:to-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-lg p-2">
   
      
      <div className="grid grid-cols-5 gap-2">
        {/* Row 1 */}
        <BMCBlock title="Key Partners" icon={Handshake} className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-700 row-span-2">
          {partnerships.map((partnership) => (
            <div 
              key={partnership.id} 
              className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-blue-500 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="font-semibold text-gray-900 dark:text-white text-sm mb-1 break-words line-clamp-2">
                {partnership.name}
              </div>
              <Badge variant="secondary" className="text-xs mb-2 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                {partnership.partner_type}
              </Badge>
              <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed break-words line-clamp-3">
                {fullscreen ? partnership.value_contribution : `${partnership.value_contribution.substring(0, 100)}...`}
              </div>
            </div>
          ))}
        </BMCBlock>

        <BMCBlock title="Key Activities" icon={Zap} className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-700">
          {activities.map((activity) => (
            <div 
              key={activity.id} 
              className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-blue-500 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words line-clamp-2">
                {activity.name}
              </div>
              <Badge variant="secondary" className="text-xs mb-2 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                {activity.criticality}
              </Badge>
              <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed break-words line-clamp-3">
                {fullscreen ? activity.description : `${activity.description.substring(0, 100)}...`}
              </div>
            </div>
          ))}
        </BMCBlock>

        <BMCBlock title="Value Propositions" icon={Heart} className="bg-brand-50 border-brand-300 dark:bg-brand-900/30 dark:border-brand-600 row-span-2">
          {propositions.map((vp) => {
            const correlationStyle = getVPCorrelationStyle(vp.segment_ids);
            return (
              <div 
                key={vp.id} 
                className={`rounded-lg p-2 shadow-md hover:shadow-lg transition-shadow ${correlationStyle ? `${correlationStyle.bg} ${correlationStyle.border}` : 'bg-white dark:bg-gray-800/80 border-brand-500 dark:border-brand-600'} border`}
              >
                <div className="font-bold text-gray-900 dark:text-white text-sm mb-2 break-words line-clamp-2">
                  {vp.name}
                </div>
                <div className="text-gray-700 dark:text-gray-300 text-xs leading-relaxed mb-3 break-words line-clamp-3">
                  {fullscreen ? vp.value_statement : `${vp.value_statement.substring(0, 120)}...`}
                </div>
                <div className={fullscreen ? "space-y-2" : "flex flex-wrap gap-1 max-w-full overflow-hidden"}>
                  {fullscreen ? (
                    vp.key_benefits.map((benefit, idx) => (
                      <div key={idx} className="text-xs bg-emerald-50 dark:bg-gray-800/50 text-emerald-700 dark:text-gray-300 border border-emerald-200 dark:border-gray-600 rounded px-2 py-1 break-words">
                        {benefit}
                      </div>
                    ))
                  ) : (
                    vp.key_benefits.slice(0, 2).map((benefit, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs bg-white/50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600 break-words max-w-fit">
                        {`${benefit.substring(0, 25)}...`}
                      </Badge>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </BMCBlock>

        <BMCBlock title="Customer Relationships" icon={Users} className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200 dark:border-purple-700">
          {relationships.map((rel) => (
            <div 
              key={rel.id} 
              className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-purple-500 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words line-clamp-2">
                {rel.name}
              </div>
              <Badge variant="secondary" className="text-xs mb-2 bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                {rel.type}
              </Badge>
              <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed break-words line-clamp-3">
                {fullscreen ? rel.description : `${rel.description.substring(0, 100)}...`}
              </div>
            </div>
          ))}
        </BMCBlock>

        <BMCBlock title="Customer Segments" icon={Target} className="bg-orange-50 dark:bg-brand-900/30 border-orange-200 dark:border-brand-600 row-span-2">
          {segments.map((segment) => {
            const correlationStyle = getSegmentCorrelationStyle(segment.id);
            return (
              <div 
                key={segment.id} 
                className={`rounded-lg p-2 shadow-sm hover:shadow-md transition-shadow ${correlationStyle ? `${correlationStyle.bg} ${correlationStyle.border}` : 'bg-white dark:bg-gray-800 border-brand-500'} border`}
              >
                <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words line-clamp-2">
                  {segment.name}
                </div>
                <Badge variant="secondary" className="text-xs mb-2 bg-white/50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300">
                  {segment.priority}
                </Badge>
                <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed mb-2">
                  {fullscreen ? segment.description : `${segment.description.substring(0, 100)}...`}
                </div>
                <div className="text-gray-700 dark:text-gray-300 text-xs bg-white/50 dark:bg-gray-700/50 rounded px-2 py-1">
                  <span className="font-semibold">Size:</span> {fullscreen ? segment.size_estimate : `${segment.size_estimate.substring(0, 50)}...`}
                </div>
              </div>
            );
          })}
        </BMCBlock>

        {/* Row 2 */}
        <BMCBlock title="Key Resources" icon={Building2} className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-700">
          {resources.map((resource) => (
            <div 
              key={resource.id} 
              className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-blue-500 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words line-clamp-2">
                {resource.name}
              </div>
              <div className="flex gap-1 mb-2">
                <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                  {resource.type}
                </Badge>
                <Badge variant="outline" className="text-xs border-indigo-300 text-indigo-600 dark:border-indigo-600 dark:text-indigo-400">
                  {resource.criticality}
                </Badge>
              </div>
              <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed break-words line-clamp-3">
                {fullscreen ? resource.description : `${resource.description.substring(0, 100)}...`}
              </div>
            </div>
          ))}
        </BMCBlock>

        <BMCBlock title="Channels" icon={Network} className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200 dark:border-purple-700">
          {channels.map((channel) => (
            <div 
              key={channel.id} 
              className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-purple-500 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words line-clamp-2">
                {channel.name}
              </div>
              <div className="flex gap-2 mb-3">
                <Badge variant="secondary" className="text-xs bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                  {channel.type}
                </Badge>
                <Badge variant="outline" className="text-xs border-teal-300 text-teal-600 dark:border-teal-600 dark:text-teal-400">
                  {channel.cost_structure}
                </Badge>
              </div>
              <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed mb-2 break-words line-clamp-3">
                {fullscreen ? channel.description : `${channel.description.substring(0, 120)}...`}
              </div>
              <div className="text-brand-500 dark:text-gray-500 text-xs bg-brand-50 dark:bg-gray-700 rounded px-2 py-1">
                <span className="font-semibold">Reach:</span> {fullscreen ? channel.reach_potential : `${channel.reach_potential.substring(0, 80)}...`}
              </div>
            </div>
          ))}
        </BMCBlock>

        {/* Row 3 */}
        <BMCBlock title="Cost Structure" icon={TrendingUp} className="col-span-2 bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/20 dark:to-emerald-800/20 border-emerald-200 dark:border-emerald-700">
          <div className="grid grid-cols-1 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-emerald-500 shadow-sm">
              <div className="font-bold text-gray-900 dark:text-white mb-2 text-sm">
                Model Type
              </div>
              <Badge className="mb-2 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 text-xs">
                {costStructure?.model_type || ''}
              </Badge>
              <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed">
                <span className="font-medium">Economies of Scale:</span><br/>
                {fullscreen ? (costStructure?.economies_of_scale || '') : `${(costStructure?.economies_of_scale || '').substring(0, 100)}...`}
              </div>
            </div>
            <div className="grid grid-cols-1 gap-3">
              {costCategories.map((cost) => (
                <div 
                  key={cost.id} 
                  className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-emerald-500 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="font-semibold text-gray-900 dark:text-white text-xs mb-1 break-words line-clamp-2">
                    {cost.name}
                  </div>
                  <Badge variant="secondary" className="text-xs mb-1 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                    {cost.type}
                  </Badge>
                  <div className="text-gray-700 dark:text-gray-300 text-xs font-medium mb-1">
                    {cost.cost_estimate}
                  </div>
                  <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed">
                    {fullscreen ? cost.description : `${cost.description.substring(0, 60)}...`}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </BMCBlock>

        <BMCBlock title="Revenue Streams" icon={DollarSign} className="col-span-3 bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/20 dark:to-emerald-800/20 border-emerald-200 dark:border-emerald-700">
          <div className="grid grid-cols-2 gap-3">
            {revenueStreams.map((stream) => (
              <div 
                key={stream.id} 
                className="bg-white dark:bg-gray-800 rounded-lg p-2 border border-emerald-500 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="font-semibold text-gray-900 dark:text-white text-sm mb-2 break-words line-clamp-2">
                  {stream.name}
                </div>
                <div className="flex gap-1 mb-2">
                  <Badge variant="secondary" className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                    {stream.type}
                  </Badge>
                  <Badge variant="outline" className="text-xs border-emerald-300 text-emerald-600 dark:border-emerald-600 dark:text-emerald-400">
                    {stream.pricing_mechanism}
                  </Badge>
                </div>
                <div className="text-gray-600 dark:text-gray-400 text-xs leading-relaxed mb-2 break-words line-clamp-3">
                  {fullscreen ? stream.pricing_strategy : `${stream.pricing_strategy.substring(0, 80)}...`}
                </div>
                <div className="text-brand-500 dark:text-brand-500 text-xs bg-brand-50 dark:bg-gray-700 rounded px-2 py-1">
                  <span className="font-semibold">Potential:</span> {fullscreen ? stream.revenue_potential : `${stream.revenue_potential.substring(0, 60)}...`}
                </div>
              </div>
            ))}
          </div>
        </BMCBlock>
      </div>
    </div>
  );
};
