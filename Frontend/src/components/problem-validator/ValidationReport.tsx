"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronDown, 
  ChevronRight, 
  Download, 
  Star, 
  TrendingUp,
  Users,
  Target,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ReportResponse, ReportSection } from '@/types/validation';

interface ValidationReportProps {
  report: ReportResponse;
  onDownload?: () => void;
}

interface CollapsibleSectionProps {
  title: string;
  content: string;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  subsections?: ReportSection[];
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  content,
  icon,
  defaultOpen = false,
  subsections
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-200 flex items-center justify-between text-left"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-3">
          {icon && <div className="text-brand-600 dark:text-brand-400">{icon}</div>}
          <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
        </div>
        <motion.div
          animate={{ rotate: isOpen ? 90 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronRight className="h-5 w-5 text-gray-500" />
        </motion.div>
      </button>
      
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-6 py-4 space-y-4">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <div dangerouslySetInnerHTML={{ __html: content.replace(/\n/g, '<br/>') }} />
              </div>
              
              {subsections && subsections.length > 0 && (
                <div className="space-y-3 mt-4">
                  {subsections.map((subsection, index) => (
                    <div key={index} className="border-l-4 border-brand-200 dark:border-brand-800 pl-4">
                      <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                        {subsection.title}
                      </h4>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        <div dangerouslySetInnerHTML={{ __html: subsection.content.replace(/\n/g, '<br/>') }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const ValidationReport: React.FC<ValidationReportProps> = ({ report, onDownload }) => {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400';
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getScoreIcon = (score: number) => {
    if (score >= 80) return <CheckCircle2 className="h-5 w-5" />;
    if (score >= 60) return <AlertCircle className="h-5 w-5" />;
    return <AlertCircle className="h-5 w-5" />;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="max-w-4xl mx-auto space-y-6"
    >
      {/* Header */}
      <div className="text-center space-y-4">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.3 }}
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-100 dark:bg-brand-900/30 rounded-full"
        >
          <Star className="h-5 w-5 text-brand-600 dark:text-brand-400" />
          <span className="text-sm font-medium text-brand-700 dark:text-brand-300">
            Market Validation Report
          </span>
        </motion.div>
        
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          {report.title}
        </h1>
        
        <p className="text-gray-600 dark:text-gray-400">
          Generated on {new Date(report.generated_at).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}
        </p>
      </div>

      {/* Validation Score */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3, duration: 0.3 }}
        className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6"
      >
        <div className="text-center space-y-4">
          <div className="flex items-center justify-center gap-2">
            <div className={getScoreColor(report.validation_score)}>
              {getScoreIcon(report.validation_score)}
            </div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Validation Score
            </h2>
          </div>
          
          <div className="space-y-2">
            <div className={`text-4xl font-bold ${getScoreColor(report.validation_score)}`}>
              {report.validation_score}/100
            </div>
            <Progress 
              value={report.validation_score} 
              className="w-full max-w-md mx-auto h-3"
            />
          </div>
          
          <p className="text-sm text-gray-600 dark:text-gray-400 max-w-md mx-auto">
            This score reflects the market viability and validation strength of your problem statement
          </p>
        </div>
      </motion.div>

      {/* Executive Summary */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.3 }}
      >
        <CollapsibleSection
          title="Executive Summary"
          content={report.executive_summary}
          icon={<Target className="h-5 w-5" />}
          defaultOpen={true}
        />
      </motion.div>

      {/* Report Sections */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5, duration: 0.3 }}
        className="space-y-4"
      >
        <CollapsibleSection
          title="Industry Analysis"
          content={report.industry_analysis.content}
          icon={<TrendingUp className="h-5 w-5" />}
          subsections={report.industry_analysis.subsections}
        />
        
        <CollapsibleSection
          title="Challenges Analysis"
          content={report.challenges_analysis.content}
          icon={<AlertCircle className="h-5 w-5" />}
          subsections={report.challenges_analysis.subsections}
        />
        
        <CollapsibleSection
          title="Market Size Analysis"
          content={report.market_size_analysis.content}
          icon={<TrendingUp className="h-5 w-5" />}
          subsections={report.market_size_analysis.subsections}
        />
        
        <CollapsibleSection
          title="Competitive Landscape"
          content={report.competitive_landscape.content}
          icon={<Users className="h-5 w-5" />}
          subsections={report.competitive_landscape.subsections}
        />
        
        <CollapsibleSection
          title="Customer Insights"
          content={report.customer_insights.content}
          icon={<Users className="h-5 w-5" />}
          subsections={report.customer_insights.subsections}
        />
      </motion.div>

      {/* Recommendations */}
      {report.recommendations && report.recommendations.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.3 }}
          className="bg-brand-50 dark:bg-brand-900/20 rounded-xl border border-brand-200 dark:border-brand-800 p-6"
        >
          <h3 className="text-lg font-semibold text-brand-900 dark:text-brand-100 mb-4 flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5" />
            Key Recommendations
          </h3>
          <ul className="space-y-2">
            {report.recommendations.map((recommendation, index) => (
              <motion.li
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.7 + index * 0.1, duration: 0.3 }}
                className="flex items-start gap-2 text-brand-800 dark:text-brand-200"
              >
                <ChevronRight className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <span className="text-sm">{recommendation}</span>
              </motion.li>
            ))}
          </ul>
        </motion.div>
      )}

      {/* Download Button */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8, duration: 0.3 }}
        className="flex justify-center pt-6"
      >
        <Button
          onClick={onDownload}
          variant="outline"
          size="lg"
          className="flex items-center gap-2"
        >
          <Download className="h-4 w-4" />
          Download Report
        </Button>
      </motion.div>
    </motion.div>
  );
};

export default ValidationReport;
