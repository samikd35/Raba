"use client";

import React from 'react';
import { Source } from '../types';

// ============================================
// Citation Rendering Utility
// ============================================

interface CitationRendererProps {
  text: string;
  sources: Source[];
  allSources: Source[];
  className?: string;
}

/**
 * Renders text with clickable citation links
 */
const renderTextWithCitations = (
  text: string, 
  critiqueSources: Source[], 
  allSources: Source[]
): React.ReactNode[] => {
  if (!text) return [];
  
  // Match citation patterns like [1], [2], [1,2], [1, 2, 3], etc.
  const citationRegex = /\[(\d+(?:\s*,\s*\d+)*)\]/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;
  let keyIndex = 0;

  while ((match = citationRegex.exec(text)) !== null) {
    // Add text before the citation
    if (match.index > lastIndex) {
      parts.push(
        <span key={`text-${keyIndex++}`}>
          {text.slice(lastIndex, match.index)}
        </span>
      );
    }

    // Parse citation numbers
    const citationNumbers = match[1].split(',').map(n => parseInt(n.trim(), 10));
    
    // Create clickable citation links
    const citationLinks = citationNumbers.map((num) => {
      // First try to find in critique sources, then in all sources
      const source = critiqueSources.find(s => s.id === num) || allSources.find(s => s.id === num);
      
      if (source?.url) {
        return (
          <a
            key={`cite-${keyIndex++}-${num}`}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors cursor-pointer"
            title={source.title || `Source ${num}`}
          >
            [{num}]
          </a>
        );
      } else {
        // Non-clickable citation (no URL available)
        return (
          <span
            key={`cite-${keyIndex++}-${num}`}
            className="text-xs font-bold text-gray-500 dark:text-gray-400"
            title={source?.title || `Source ${num}`}
          >
            [{num}]
          </span>
        );
      }
    });

    parts.push(...citationLinks);
    lastIndex = match.index + match[0].length;
  }

  // Add remaining text after last citation
  if (lastIndex < text.length) {
    parts.push(
      <span key={`text-${keyIndex++}`}>
        {text.slice(lastIndex)}
      </span>
    );
  }

  return parts.length > 0 ? parts : [<span key="full">{text}</span>];
};

/**
 * Citation Text Component for cleaner usage
 */
export const CitationText: React.FC<CitationRendererProps> = ({ 
  text, 
  sources, 
  allSources, 
  className 
}) => {
  return (
    <span className={className}>
      {renderTextWithCitations(text, sources, allSources)}
    </span>
  );
};

export default CitationText;
