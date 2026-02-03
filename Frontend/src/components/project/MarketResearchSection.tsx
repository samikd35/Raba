"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Award,
  BarChart3,
  Lightbulb,
  Target,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
  UserCircle2,
} from 'lucide-react';
import {
  AnalysisData,
  StructuredReport,
  AssumptionAnalysis,
  DimensionAnalysis,
  AnalysisEvidence,
} from '@/types/organization';

interface MarketResearchSectionProps {
  analysisData: AnalysisData | null;
  readOnly?: boolean;
  embedded?: boolean;
}

const getValidationStatusBadge = (status: string) => {
  switch (status?.toLowerCase()) {
    case 'validated':
      return (
        <Badge className="bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300">
          <CheckCircle2 className="w-3 h-3 mr-1" />
          Validated
        </Badge>
      );
    case 'partially_validated':
      return (
        <Badge className="bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300">
          <AlertTriangle className="w-3 h-3 mr-1" />
          Partially Validated
        </Badge>
      );
    case 'invalidated':
      return (
        <Badge className="bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300">
          <AlertCircle className="w-3 h-3 mr-1" />
          Invalidated
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="text-gray-600 dark:text-gray-400">
          {status || 'Unknown'}
        </Badge>
      );
  }
};

const getConfidenceBadgeColor = (score: number) => {
  if (score >= 0.7) return 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300';
  if (score >= 0.4) return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300';
  return 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300';
};

const EvidenceItem: React.FC<{ evidence: AnalysisEvidence; index: number; type: 'supporting' | 'counter' }> = ({
  evidence,
  index,
  type,
}) => {
  const isSupporting = type === 'supporting';
  const bgColor = isSupporting
    ? 'bg-gray-50 dark:bg-transparent border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
    : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/30';
  const badgeColor = isSupporting
    ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
    : 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300';
  const numberBg = isSupporting ? 'bg-brand-500' : 'bg-red-500';

  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${bgColor} transition-colors`}>
      <div className={`flex-shrink-0 w-5 h-5 rounded-full ${numberBg} text-white flex items-center justify-center text-xs font-bold mt-0.5`}>
        {index + 1}
      </div>
      <p className="text-sm text-gray-700 dark:text-gray-300 flex-1">{evidence.text}</p>
      {evidence.confidence !== null && (
        <Badge className={`${badgeColor} text-xs`}>
          {Math.round(evidence.confidence * 100)}%
        </Badge>
      )}
    </div>
  );
};

const DimensionAnalysisCard: React.FC<{ analysis: DimensionAnalysis; index: number }> = ({ analysis, index }) => {
  return (
    <div className="space-y-4 p-5 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-transparent">
      {/* Dimension Header */}
      <div className="flex items-center justify-between pb-3 border-b border-gray-200 dark:border-gray-700">
        <h5 className="font-semibold text-base text-brand-500 dark:text-gray-100 capitalize flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-gray-700 dark:text-gray-300 font-bold text-sm">
            {index + 1}
          </div>
          {analysis.dimension_type.replace(/_/g, ' ')}
        </h5>
        <div className="flex items-center gap-2">
          <Badge className={getConfidenceBadgeColor(analysis.confidence_score)}>
            {Math.round(analysis.confidence_score * 100)}% Confidence
          </Badge>
          <Badge variant="outline" className="capitalize">
            {analysis.accuracy_level} Accuracy
          </Badge>
        </div>
      </div>

      {/* Primary Insight */}
      <div className="p-4 bg-white dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700">
        <h6 className="font-medium text-brand-500 dark:text-gray-100 mb-2 flex items-center gap-2">
          <Target className="w-4 h-4 text-brand-500 dark:text-gray-400" />
          Primary Insight
        </h6>
        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{analysis.primary_insight}</p>
      </div>

      {/* Supporting Evidence */}
      {analysis.supporting_evidence.length > 0 && (
        <div className="space-y-3">
          <h6 className="font-medium text-brand-500 dark:text-gray-100 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400" />
            Supporting Evidence ({analysis.supporting_evidence.length})
          </h6>
          <div className="grid gap-2">
            {analysis.supporting_evidence.map((evidence, idx) => (
              <EvidenceItem key={idx} evidence={evidence} index={idx} type="supporting" />
            ))}
          </div>
        </div>
      )}

      {/* Counter Evidence */}
      {analysis.counter_evidence.length > 0 && (
        <div className="space-y-3">
          <h6 className="font-medium text-red-700 dark:text-red-400 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            Counter Evidence ({analysis.counter_evidence.length})
          </h6>
          <div className="grid gap-2">
            {analysis.counter_evidence.map((evidence, idx) => (
              <EvidenceItem key={idx} evidence={evidence} index={idx} type="counter" />
            ))}
          </div>
        </div>
      )}

      {/* Data Limitations */}
      {analysis.data_limitations && (
        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <div>
              <h6 className="font-medium text-yellow-800 dark:text-yellow-300 text-sm mb-1">Data Limitations</h6>
              <p className="text-xs text-yellow-700 dark:text-yellow-400">{analysis.data_limitations}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const AssumptionAnalysisCard: React.FC<{ assumption: AssumptionAnalysis; index: number }> = ({ assumption, index }) => {
  return (
    <Card className="shadow-md border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Assumption Header */}
      <div className="bg-gray-50 dark:bg-transparent p-4">
        <div className="space-y-4">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className="bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 text-sm px-3 py-1">
              Assumption #{index + 1}
            </Badge>
            {getValidationStatusBadge(assumption.validation_status)}
          </div>
          <h3 className="text-md font-semibold text-brand-500 dark:text-gray-100 leading-tight">
            {assumption.assumption_text}
          </h3>
        </div>
      </div>

      <CardContent className="p-4 space-y-4 -mt-6">
        {/* Recommendation */}
        <div className="p-4 bg-gray-50 dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-gray-600 dark:text-gray-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-brand-500 dark:text-gray-100 mb-2">Recommendation</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{assumption.recommendation}</p>
            </div>
          </div>
        </div>

        {/* Dimension Analyses */}
        <div className="space-y-4">
          {assumption.analyses.map((analysis, analysisIdx) => (
            <DimensionAnalysisCard key={analysis.dimension_type} analysis={analysis} index={analysisIdx} />
          ))}
        </div>

        {/* Key Findings */}
        {assumption.key_findings.length > 0 && (
          <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <h5 className="font-semibold text-lg flex items-center gap-2 text-brand-500 dark:text-gray-100">
              <Lightbulb className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              Key Findings for This Assumption ({assumption.key_findings.length})
            </h5>
            <div className="grid gap-2">
              {assumption.key_findings.map((finding, idx) => (
                <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                  <div className="flex-shrink-0 w-5 h-5 rounded-full bg-brand-500 text-white flex items-center justify-center text-xs font-bold mt-0.5">
                    {idx + 1}
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 flex-1">{finding}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

const PersonaReport: React.FC<{ report: StructuredReport }> = ({ report }) => {
  const { executive_summary, assumptions, metadata } = report;

  return (
    <div className="space-y-6">
      {/* Generation Date */}
      <div className="flex items-start">
        <p className="text-sm text-brand-500 dark:text-gray-300 flex items-center gap-2 px-4 bg-brand-25 dark:bg-transparent border-gray-200 dark:border-gray-600 py-2 border rounded-lg">
          Generated on {new Date(metadata.generated_at).toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </p>
      </div>

      {/* Executive Summary */}
      <Card className="shadow-md border-gray-200 dark:border-gray-700">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Award className="w-6 h-6 text-brand-500 dark:text-gray-400" />
            <CardTitle className="text-xl text-brand-500 dark:text-gray-100">Executive Summary</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 -mt-4">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line text-sm">
              {executive_summary.content.replace(/^Executive Summary:\s*/i, '')}
            </p>
          </div>

          {executive_summary.key_insights.length > 0 && (
            <div className="space-y-4 pt-6 border-t border-gray-200 dark:border-gray-700">
              <h4 className="font-semibold text-lg flex items-center gap-2 text-brand-500 dark:text-gray-100">
                <Lightbulb className="w-5 h-5 text-brand-500 dark:text-gray-400" />
                Key Insights
              </h4>
              <div className="grid gap-3">
                {executive_summary.key_insights.map((insight, idx) => (
                  <div key={idx} className="flex items-start gap-3 p-4 rounded-lg bg-gray-50 dark:bg-transparent border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500 text-white flex items-center justify-center text-xs font-bold mt-0.5">
                      {idx + 1}
                    </div>
                    <p className="text-sm text-gray-700 dark:text-gray-300 flex-1">{insight}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Assumption Analyses */}
      {assumptions.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 px-2">
            <BarChart3 className="w-6 h-6 text-gray-600 dark:text-gray-400" />
            <h3 className="text-xl font-semibold text-brand-500 dark:text-gray-100">Assumption Analyses</h3>
            <Badge variant="outline" className="px-2 text-sm border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300">
              {assumptions.length} Total
            </Badge>
          </div>

          {assumptions.map((assumption, index) => (
            <AssumptionAnalysisCard key={assumption.assumption_id} assumption={assumption} index={index} />
          ))}
        </div>
      )}
    </div>
  );
};

export const MarketResearchSection: React.FC<MarketResearchSectionProps> = ({
  analysisData,
  readOnly = true,
  embedded = true,
}) => {
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);

  if (!analysisData) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <BarChart3 className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">No Market Research Analysis Available</p>
        <p className="text-sm">Analysis data will appear here once completed.</p>
      </div>
    );
  }

  // Check if it's multi-persona format
  const hasPersonas = analysisData.personas && Object.keys(analysisData.personas).length > 0;
  
  // Get structured report (either from personas or direct)
  let structuredReport: StructuredReport | null = null;
  let personaKeys: string[] = [];
  
  if (hasPersonas) {
    personaKeys = Object.keys(analysisData.personas!);
    const currentPersona = selectedPersona || personaKeys[0];
    structuredReport = analysisData.personas![currentPersona]?.structured_report || null;
    
    // Set initial selected persona
    if (!selectedPersona && personaKeys.length > 0) {
      setSelectedPersona(personaKeys[0]);
    }
  } else if (analysisData.structured_report) {
    structuredReport = analysisData.structured_report;
  }

  if (!structuredReport) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-lg font-medium">Analysis In Progress</p>
        <p className="text-sm">The market research analysis is still being processed.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Persona Toggle (only show if multiple personas) */}
      {hasPersonas && personaKeys.length > 1 && (
        <div className="flex justify-center mb-4">
          <div className="bg-white dark:bg-transparent rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm">
            <Tabs
              value={selectedPersona || personaKeys[0]}
              onValueChange={(value) => setSelectedPersona(value)}
              className="w-full"
            >
              <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${personaKeys.length}, 1fr)` }}>
                {personaKeys.map((personaKey) => (
                  <TabsTrigger
                    key={personaKey}
                    value={personaKey}
                    className="flex items-center gap-2 text-brand-500 dark:text-gray-300"
                  >
                    <UserCircle2 className="w-4 h-4" />
                    {analysisData.personas![personaKey]?.persona_name || personaKey}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>
        </div>
      )}

      {/* Report Content */}
      <PersonaReport report={structuredReport} />
    </div>
  );
};

export default MarketResearchSection;
