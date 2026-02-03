import React from 'react';
import { motion } from 'framer-motion';
import { Users } from 'lucide-react';

export const CohortsEmpty = React.memo(() => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center justify-center h-[50vh]"
    >
        <div className="bg-gray-100 dark:bg-gray-800 rounded-full p-6 w-24 h-24 flex items-center justify-center mb-6">
            <Users className="h-12 w-12 text-gray-500 dark:text-gray-400" />
        </div>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            No Cohorts Found
        </h3>
        <p className="text-gray-500 dark:text-gray-400 text-center max-w-md">
            There are no cohorts configured for your organization yet.
        </p>
    </motion.div>
));

CohortsEmpty.displayName = 'CohortsEmpty';
