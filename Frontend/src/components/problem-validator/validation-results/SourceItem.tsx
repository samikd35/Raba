"use client";

import React, { useState, useCallback } from "react";
import { SourceItem as SourceItemType } from "./types";

interface SourceItemProps {
    source: SourceItemType;
    index: number;
}

export const SourceItem = React.memo(({
    source,
    index
}: SourceItemProps) => {
    const [isValidUrl, setIsValidUrl] = useState(true);

    const handleLinkError = useCallback(() => {
        setIsValidUrl(false);
    }, []);

    const formatUrl = useCallback((url: string) => {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname.replace('www.', '');
        } catch {
            return url.length > 30 ? url.substring(0, 30) + '...' : url;
        }
    }, []);

    const getCredibilityColor = useCallback((score?: number) => {
        if (!score) return 'text-brand-500';
        if (score >= 8) return 'text-green-500';
        if (score >= 6) return 'text-yellow-500';
        return 'text-red-500';
    }, []);

    return (
        <div
            id={`source-${index + 1}`}
            data-source-url={source.source_url}
            className="flex gap-3 p-3 bg-brand-50 dark:bg-brand-900/10 rounded-lg hover:bg-brand-100 dark:hover:bg-brand-900/20 transition-colors"
        >
            <div className="shrink-0 w-6 h-6 bg-brand-100 dark:bg-brand-900/20 rounded-full flex items-center justify-center text-xs font-medium text-brand-700 dark:text-brand-300">
                {source.number ?? index + 1}
            </div>
            <div className="flex-1 min-w-0">
                <a
                    href={isValidUrl ? source.source_url : '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 hover:underline block truncate"
                    onError={handleLinkError}
                    onClick={(e) => !isValidUrl && e.preventDefault()}
                >
                    {source.source_title || 'Untitled Source'}
                </a>
                <div className="flex items-center justify-between mt-1">
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate flex-1">
                        {formatUrl(source.source_url)}
                    </p>
                    {source.credibility_score && (
                        <span className={`text-xs font-medium ${getCredibilityColor(source.credibility_score)}`}>
                            Score: {source.credibility_score}/10
                        </span>
                    )}
                </div>
                {source.publication_date && (
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                        Published: {new Date(source.publication_date).toLocaleDateString()}
                    </p>
                )}
            </div>
        </div>
    );
});

SourceItem.displayName = 'SourceItem';
