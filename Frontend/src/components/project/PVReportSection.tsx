"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PVReport } from '@/types/organization';
import { 
  FileText, 
  ChevronDown, 
  ChevronUp,
  Download,
  BookOpen,
  Lightbulb,
  TrendingUp,
  Target,
  Users,
  BarChart3,
  AlertCircle,
  CheckCircle2,
  ExternalLink
} from 'lucide-react';
import { MarkdownRenderer } from '@/components/problem-validator/validation-results/MarkdownRenderer';

export interface PVReportSectionProps {
  pvReport: PVReport | null;
  readOnly?: boolean;
  embedded?: boolean; // If true, don't render Card wrapper (for use inside CollapsibleSection)
}

// Section component for report content
interface ReportSectionProps {
  title: string;
  icon: React.ElementType;
  content: any;
  defaultExpanded?: boolean;
}

function ReportSection({ title, icon: Icon, content, defaultExpanded = false }: ReportSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!content) return null;

  // Handle different content types
  const renderContent = () => {
    if (typeof content === 'string') {
      // Use MarkdownRenderer for proper markdown rendering with clickable citations
      return <MarkdownRenderer content={content} />;
    }

    if (Array.isArray(content)) {
      // Check if this is a sources array (items have source_url)
      const isSourcesArray = content.length > 0 && content[0]?.source_url;
      
      if (isSourcesArray) {
        return (
          <div className="space-y-3">
            {content.map((source: any, idx: number) => (
              <div 
                key={idx} 
                id={`source-${source.number || idx + 1}`}
                data-source-url={source.source_url}
                className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900 text-brand-600 dark:text-brand-400 text-xs font-bold flex items-center justify-center">
                  {source.number || idx + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <a 
                    href={source.source_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-brand-600 dark:text-brand-400 font-medium hover:underline flex items-center gap-1 text-sm"
                  >
                    {source.source_title || source.title || `Source ${source.number || idx + 1}`}
                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                  </a>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-1">
                    {source.source_url}
                  </p>
                </div>
              </div>
            ))}
          </div>
        );
      }
      
      return (
        <ul className="space-y-2">
          {content.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-gray-700 dark:text-gray-300">
              <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
              <span>{typeof item === 'string' ? item : JSON.stringify(item)}</span>
            </li>
          ))}
        </ul>
      );
    }

    if (typeof content === 'object') {
      return (
        <div className="space-y-3">
          {Object.entries(content).map(([key, value]) => (
            <div key={key} className="border-l-2 border-brand-200 dark:border-brand-700 pl-3">
              <h5 className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                {key.replace(/_/g, ' ')}
              </h5>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
              </p>
            </div>
          ))}
        </div>
      );
    }

    return <p className="text-gray-500 dark:text-gray-400">No content available</p>;
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-5 h-5 text-brand-600 dark:text-brand-400" />
          <span className="font-medium text-gray-900 dark:text-white">{title}</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-gray-500" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-500" />
        )}
      </button>
      {isExpanded && (
        <div className="p-4 bg-white dark:bg-gray-900">
          {renderContent()}
        </div>
      )}
    </div>
  );
}

// Main content renderer for structured report
function ReportContentRenderer({ content }: { content: Record<string, any> }) {
  // Common section mappings - ordered by display priority
  // Recommendations comes after Challenges Analysis
  const sectionConfig: Record<string, { icon: React.ElementType; title: string; priority: number }> = {
    executive_summary: { icon: BookOpen, title: 'Executive Summary', priority: 1 },
    summary: { icon: BookOpen, title: 'Summary', priority: 1 },
    key_insights: { icon: Lightbulb, title: 'Key Insights', priority: 2 },
    insights: { icon: Lightbulb, title: 'Insights', priority: 2 },
    industry_analysis: { icon: BarChart3, title: 'Industry Analysis', priority: 3 },
    market_analysis: { icon: BarChart3, title: 'Market Analysis', priority: 4 },
    market_size: { icon: TrendingUp, title: 'Market Size', priority: 5 },
    target_market: { icon: Target, title: 'Target Market', priority: 6 },
    target_audience: { icon: Users, title: 'Target Audience', priority: 6 },
    competitors: { icon: Users, title: 'Competitors', priority: 7 },
    competition: { icon: Users, title: 'Competition', priority: 7 },
    opportunities: { icon: TrendingUp, title: 'Opportunities', priority: 8 },
    challenges: { icon: AlertCircle, title: 'Challenges', priority: 9 },
    challenges_analysis: { icon: AlertCircle, title: 'Challenges Analysis', priority: 9 },
    risks: { icon: AlertCircle, title: 'Risks', priority: 9 },
    recommendations: { icon: CheckCircle2, title: 'Recommendations', priority: 10 }, // After challenges
    sources: { icon: FileText, title: 'Sources', priority: 11 },
    next_steps: { icon: Target, title: 'Next Steps', priority: 12 },
    conclusion: { icon: FileText, title: 'Conclusion', priority: 13 },
  };

  // Fields to exclude from display
  const excludedFields = ['title', 'id', 'created_at', 'updated_at', 'tenant_id'];

  // Sort sections by priority
  const sortedSections = Object.entries(content)
    .filter(([key]) => !excludedFields.includes(key))
    .sort(([keyA], [keyB]) => {
      const priorityA = sectionConfig[keyA.toLowerCase()]?.priority || 100;
      const priorityB = sectionConfig[keyB.toLowerCase()]?.priority || 100;
      return priorityA - priorityB;
    });

  if (sortedSections.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>No report content available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {sortedSections.map(([key, value]) => {
        const config = sectionConfig[key.toLowerCase()] || {
          icon: FileText,
          title: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          priority: 100,
        };

        return (
          <ReportSection
            key={key}
            title={config.title}
            icon={config.icon}
            content={value}
            defaultExpanded={config.priority <= 2} // Expand executive summary and key insights by default
          />
        );
      })}
    </div>
  );
}

export function PVReportSection({ pvReport, readOnly = false, embedded = false }: PVReportSectionProps) {
  const handleDownload = () => {
    if (!pvReport?.content) return;

    // Create a downloadable JSON file
    const blob = new Blob([JSON.stringify(pvReport.content, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${pvReport.title || 'pv-report'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // No PV Report available
  if (!pvReport) {
    const emptyContent = (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <FileText className="w-16 h-16 mx-auto mb-4 opacity-30" />
        <p className="mb-2">The Problem Validation Report has not been generated yet.</p>
        <p className="text-sm">Complete the problem validation workflow to generate this report.</p>
      </div>
    );

    if (embedded) return emptyContent;

    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <FileText className="w-5 h-5 text-brand-600" />
            Problem Validation Report
          </CardTitle>
          <CardDescription>
            No PV report available for this project
          </CardDescription>
        </CardHeader>
        <CardContent>{emptyContent}</CardContent>
      </Card>
    );
  }

  // PV Report exists but no content
  if (!pvReport.content || Object.keys(pvReport.content).length === 0) {
    const emptyReportContent = (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Report exists but contains no content.</p>
      </div>
    );

    if (embedded) return emptyReportContent;

    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <FileText className="w-5 h-5 text-brand-600" />
            Problem Validation Report
          </CardTitle>
          <CardDescription className="flex items-center gap-2">
            <span>{pvReport.title}</span>
            <Badge className="bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
              Empty
            </Badge>
          </CardDescription>
        </CardHeader>
        <CardContent>{emptyReportContent}</CardContent>
      </Card>
    );
  }

  // Full report content
  const reportContent = (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">{pvReport.title}</p>
        <Button
          variant="outline"
          size="sm"
          onClick={handleDownload}
          className="flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Export
        </Button>
      </div>
      <ReportContentRenderer content={pvReport.content} />
    </div>
  );

  if (embedded) return reportContent;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-xl font-bold flex items-center gap-2">
              <FileText className="w-5 h-5 text-brand-600" />
              Problem Validation Report
            </CardTitle>
            <CardDescription className="flex items-center gap-2 mt-1">
              <span>{pvReport.title}</span>
              <Badge className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                Complete
              </Badge>
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            className="flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <ReportContentRenderer content={pvReport.content} />
      </CardContent>
    </Card>
  );
}

export default PVReportSection;
