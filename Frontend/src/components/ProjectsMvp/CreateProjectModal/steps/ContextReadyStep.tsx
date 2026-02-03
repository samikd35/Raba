'use client';

import React from 'react';
import {
  CheckCircle2,
  AlertCircle,
  Lightbulb,
  Users,
  Target,
  Sparkles,
  Shield,
  TrendingUp,
  BookOpen,
  ExternalLink,
  Globe,
} from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import type { EnhancedContext, EditableContext } from '../types';

interface ContextReadyStepProps {
  editableContext: EditableContext;
  enhancedContext: EnhancedContext | null;
  error: string | null;
  updateEditableContext: (field: string, value: string | string[]) => void;
  updateNestedEditableContext: (parent: 'problem' | 'businessModelSeeds', field: string, value: string | string[]) => void;
  updateArrayItem: (field: 'customerSegments' | 'differentiation' | 'constraintsAndRisks', index: number, value: string) => void;
  updateCostDriver: (index: number, value: string) => void;
}

export const ContextReadyStep: React.FC<ContextReadyStepProps> = ({
  editableContext,
  enhancedContext,
  error,
  updateEditableContext,
  updateNestedEditableContext,
  updateArrayItem,
  updateCostDriver,
}) => {
  return (
    <div className="py-2 space-y-4">
      {/* Success Banner */}
      <div className="flex items-center gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
        <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
        <div>
          <h4 className="text-sm font-semibold text-green-700 dark:text-green-300">
            Enhanced Context Generated! Review and edit below.
          </h4>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <AlertCircle className="h-5 w-5 text-red-500 shrink-0" />
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Idea Summary */}
      <div className="space-y-2">
        <Label className="flex items-center gap-2 text-sm font-medium text-brand-500 dark:text-gray-300">
          <Lightbulb className="h-4 w-4 text-yellow-500" />
          Idea Summary
        </Label>
        <Textarea
          value={editableContext.ideaSummary}
          onChange={(e) => updateEditableContext('ideaSummary', e.target.value)}
          className="w-full min-h-[100px] resize-y text-sm"
          placeholder="Describe your idea..."
        />
      </div>

      {/* Customer Segments */}
      <div className="space-y-2">
        <Label className="flex items-center gap-2 text-sm font-medium text-brand-500 dark:text-gray-300">
          <Users className="h-4 w-4 text-blue-500" />
          Customer Segments
        </Label>
        <div className="space-y-2">
          {editableContext.customerSegments.map((segment, index) => (
            <Textarea
              key={index}
              value={segment}
              onChange={(e) => updateArrayItem('customerSegments', index, e.target.value)}
              className="w-full min-h-[60px] resize-y text-sm"
              placeholder={`Customer segment ${index + 1}...`}
            />
          ))}
        </div>
      </div>

      {/* Problem */}
      <div className="space-y-2">
        <Label className="flex items-center gap-2 text-sm font-medium text-brand-500 dark:text-gray-300">
          <Target className="h-4 w-4 text-red-500" />
          Problem
        </Label>
        <div className="space-y-3 bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
          <div className="space-y-1">
            <Label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Who</Label>
            <Textarea
              value={editableContext.problem.who}
              onChange={(e) => updateNestedEditableContext('problem', 'who', e.target.value)}
              className="w-full min-h-[60px] resize-y text-sm"
              placeholder="Who experiences this problem..."
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">What</Label>
            <Textarea
              value={editableContext.problem.what}
              onChange={(e) => updateNestedEditableContext('problem', 'what', e.target.value)}
              className="w-full min-h-[60px] resize-y text-sm"
              placeholder="What is the problem..."
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Where</Label>
            <Textarea
              value={editableContext.problem.where}
              onChange={(e) => updateNestedEditableContext('problem', 'where', e.target.value)}
              className="w-full min-h-[60px] resize-y text-sm"
              placeholder="Where does this problem occur..."
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Why Now</Label>
            <Textarea
              value={editableContext.problem.why_now}
              onChange={(e) => updateNestedEditableContext('problem', 'why_now', e.target.value)}
              className="w-full min-h-[60px] resize-y text-sm"
              placeholder="Why is this problem urgent now..."
            />
          </div>
        </div>
      </div>

      {/* Solution Overview */}
      <div className="space-y-2">
        <Label className="flex items-center gap-2 text-sm font-medium text-brand-500 dark:text-gray-300">
          <Sparkles className="h-4 w-4 text-purple-500" />
          Solution Overview
        </Label>
        <Textarea
          value={editableContext.solutionOverview}
          onChange={(e) => updateEditableContext('solutionOverview', e.target.value)}
          className="w-full min-h-[100px] resize-y text-sm"
          placeholder="Describe your solution..."
        />
      </div>

      {/* Differentiation */}
      <div className="space-y-2">
        <Label className="flex items-center gap-2 text-sm font-medium text-brand-500 dark:text-gray-300">
          <Shield className="h-4 w-4 text-green-500" />
          Differentiation
        </Label>
        <div className="space-y-2">
          {editableContext.differentiation.map((item, index) => (
            <div key={index} className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0 mt-3" />
              <Textarea
                value={item}
                onChange={(e) => updateArrayItem('differentiation', index, e.target.value)}
                className="w-full min-h-[60px] resize-y text-sm"
                placeholder={`Differentiator ${index + 1}...`}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Business Model Seeds */}
      <div className="space-y-2">
        <Label className="flex items-center gap-2 text-sm font-medium text-brand-500 dark:text-gray-300">
          <TrendingUp className="h-4 w-4 text-orange-500" />
          Business Model Seeds
        </Label>
        <div className="space-y-3 bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
          <div className="space-y-1">
            <Label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Revenue Model</Label>
            <Textarea
              value={editableContext.businessModelSeeds.revenue_model}
              onChange={(e) => updateNestedEditableContext('businessModelSeeds', 'revenue_model', e.target.value)}
              className="w-full min-h-[60px] resize-y text-sm"
              placeholder="How will you generate revenue..."
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Pricing Hypothesis</Label>
            <Textarea
              value={editableContext.businessModelSeeds.pricing_hypothesis}
              onChange={(e) => updateNestedEditableContext('businessModelSeeds', 'pricing_hypothesis', e.target.value)}
              className="w-full min-h-[60px] resize-y text-sm"
              placeholder="Your pricing strategy..."
            />
          </div>
          {editableContext.businessModelSeeds.cost_drivers.length > 0 && (
            <div className="space-y-1">
              <Label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Cost Drivers</Label>
              <div className="space-y-2">
                {editableContext.businessModelSeeds.cost_drivers.map((driver, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-orange-500 shrink-0" />
                    <Input
                      value={driver}
                      onChange={(e) => updateCostDriver(index, e.target.value)}
                      className="w-full text-sm"
                      placeholder={`Cost driver ${index + 1}...`}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Constraints & Risks */}
      {editableContext.constraintsAndRisks.length > 0 && (
        <div className="space-y-2">
          <Label className="flex items-center gap-2 text-sm font-medium text-brand-500 dark:text-gray-300">
            <AlertCircle className="h-4 w-4 text-amber-500" />
            Constraints & Risks
          </Label>
          <div className="space-y-2">
            {editableContext.constraintsAndRisks.map((risk, index) => (
              <div key={index} className="flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-amber-500 shrink-0 mt-3" />
                <Textarea
                  value={risk}
                  onChange={(e) => updateArrayItem('constraintsAndRisks', index, e.target.value)}
                  className="w-full min-h-[60px] resize-y text-sm border-amber-200 dark:border-amber-800"
                  placeholder={`Risk ${index + 1}...`}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Research Summary (Read-only) */}
      {enhancedContext?.draft.Research && (
        <div className="space-y-2">
          <Label className="flex items-center gap-2 text-sm font-medium text-brand-500 dark:text-gray-300">
            <BookOpen className="h-4 w-4 text-indigo-500" />
            Research Insights
            <Badge variant="outline" className="text-xs">Read-only</Badge>
          </Label>
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg space-y-3 text-sm">
            {enhancedContext.draft.Research.summary && (
              <div>
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Summary</span>
                <p className="text-gray-700 dark:text-gray-300">{enhancedContext.draft.Research.summary}</p>
              </div>
            )}
            {enhancedContext.draft.Research.sources && enhancedContext.draft.Research.sources.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-2 block">
                  Sources ({enhancedContext.draft.Research.sources.length})
                </span>
                <div className="space-y-1 max-h-[150px] overflow-y-auto">
                  {enhancedContext.draft.Research.sources.map((source) => (
                    <a
                      key={source.n}
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-xs text-brand-500 hover:underline"
                    >
                      <Globe className="h-3 w-3" />
                      [{source.n}] {source.title}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
