'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface ChatFollowUpSuggestionsProps {
    suggestions: string[];
    onSuggestionClick: (suggestion: string) => void;
}

export default function ChatFollowUpSuggestions({
    suggestions,
    onSuggestionClick,
}: ChatFollowUpSuggestionsProps) {
    if (suggestions.length === 0) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-wrap gap-2 mt-4"
        >
            <span className="text-xs text-gray-500 dark:text-gray-400 w-full mb-1">
                Suggested follow-ups:
            </span>
            {suggestions.map((suggestion, index) => (
                <motion.button
                    key={index}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.1 }}
                    onClick={() => onSuggestionClick(suggestion)}
                    className="px-3 py-1.5 text-sm bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-300 rounded-full border border-brand-200 dark:border-brand-700 hover:bg-brand-100 dark:hover:bg-brand-900/50 transition-colors cursor-pointer"
                >
                    {suggestion}
                </motion.button>
            ))}
        </motion.div>
    );
}
