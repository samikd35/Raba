'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Bot } from 'lucide-react';

export default function ChatWelcome() {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mt-24 flex flex-col gap-2"
        >
            <div className="w-16 h-16 mx-auto bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center">
                <Bot className="w-8 h-8 text-brand-600 dark:text-brand-400" />
            </div>
            <h1 className="text-2xl font-bold text-brand-500 dark:text-white">
                Chat with your Project
            </h1>
            <p className="text-md text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                Ask questions about your project, get insights, and explore ideas with AI assistance.
            </p>
        </motion.div>
    );
}
