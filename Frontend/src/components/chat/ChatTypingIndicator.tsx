'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Bot } from 'lucide-react';

export default function ChatTypingIndicator() {
    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
            <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center">
                <Bot className="h-4 w-4 text-brand-600" />
            </div>
            <div className="bg-gray-200 dark:bg-gray-800 rounded-2xl px-4 py-3 flex items-center gap-1.5">
                <motion.span
                    className="w-1.5 h-1.5 bg-gray-500 rounded-full"
                    animate={{ y: [0, -5, 0] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                />
                <motion.span
                    className="w-1.5 h-1.5 bg-gray-500 rounded-full"
                    animate={{ y: [0, -5, 0] }}
                    transition={{ repeat: Infinity, duration: 1, delay: 0.1 }}
                />
                <motion.span
                    className="w-1.5 h-1.5 bg-gray-500 rounded-full"
                    animate={{ y: [0, -5, 0] }}
                    transition={{ repeat: Infinity, duration: 1, delay: 0.2 }}
                />
            </div>
        </motion.div>
    );
}
