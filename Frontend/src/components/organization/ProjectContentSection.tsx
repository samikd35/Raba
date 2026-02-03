"use client";

import React from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { LucideIcon } from 'lucide-react';

interface ProjectContentSectionProps {
  /**
   * Unique identifier for the accordion item
   */
  id: string;
  
  /**
   * Section title
   */
  title: string;
  
  /**
   * Icon component from lucide-react
   */
  icon: LucideIcon;
  
  /**
   * Optional badge to show count or status
   */
  badge?: number | string;
  
  /**
   * Badge color variant
   */
  badgeVariant?: 'default' | 'secondary' | 'destructive' | 'outline';
  
  /**
   * Content to display when expanded
   */
  children: React.ReactNode;
  
  /**
   * Whether the section should be open by default
   */
  defaultOpen?: boolean;
  
  /**
   * Optional description text below title
   */
  description?: string;
}

/**
 * Reusable collapsible section component for project detail page
 * Uses shadcn/ui Accordion for smooth animations and accessibility
 */
export default function ProjectContentSection({
  id,
  title,
  icon: Icon,
  badge,
  badgeVariant = 'secondary',
  children,
  defaultOpen = false,
  description,
}: ProjectContentSectionProps) {
  return (
    <Card className="overflow-hidden">
      <Accordion type="single" collapsible defaultValue={defaultOpen ? id : undefined}>
        <AccordionItem value={id} className="border-none">
          <AccordionTrigger className="px-6 py-4 hover:no-underline hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
            <div className="flex items-center justify-between w-full pr-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-brand-100 dark:bg-brand-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Icon className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                </div>
                <div className="text-left">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {title}
                    </h3>
                    {badge !== undefined && (
                      <Badge variant={badgeVariant} className="ml-2">
                        {typeof badge === 'number' ? `${badge}` : badge}
                      </Badge>
                    )}
                  </div>
                  {description && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {description}
                    </p>
                  )}
                </div>
              </div>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-6 pb-6 pt-2">
            {children}
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </Card>
  );
}

/**
 * Simplified version without accordion for always-open sections
 */
export function ProjectContentSectionOpen({
  title,
  icon: Icon,
  badge,
  badgeVariant = 'secondary',
  children,
  description,
}: Omit<ProjectContentSectionProps, 'id' | 'defaultOpen'>) {
  return (
    <Card>
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-brand-100 dark:bg-brand-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
            <Icon className="w-5 h-5 text-brand-600 dark:text-brand-400" />
          </div>
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {title}
              </h3>
              {badge !== undefined && (
                <Badge variant={badgeVariant}>
                  {typeof badge === 'number' ? `${badge}` : badge}
                </Badge>
              )}
            </div>
            {description && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {description}
              </p>
            )}
          </div>
        </div>
      </div>
      <div className="px-6 py-6">
        {children}
      </div>
    </Card>
  );
}
