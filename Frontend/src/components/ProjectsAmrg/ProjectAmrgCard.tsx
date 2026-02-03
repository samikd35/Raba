'use client'
import React, { useCallback, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
    Calendar,
    Clock,
    ChevronRight,
    TrendingUp,
    CheckCircle2,
    PlayCircle,
    PauseCircle,
    FileText,
    Loader2,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from "@/components/ui/card";
import { Project } from './types';

interface ProjectCardProps {
    project: Project;
    index: number;
    onNavigate: (projectId: string) => void;
}

/**
 * Individual project card component - AMRG version
 */
export const ProjectAmrgCard = React.memo(({ project, index, onNavigate }: ProjectCardProps) => {
    const [isNavigating, setIsNavigating] = useState(false);

    const handleProjectClick = useCallback(() => {
        if (process.env.NODE_ENV === 'development') {
            console.log('Navigating to project:', project.id);
        }
        setIsNavigating(true);
        onNavigate(project.id);
    }, [project.id, onNavigate]);

    const formatDate = useCallback((dateString: string) => {
        try {
            const date = new Date(dateString);
            return new Intl.DateTimeFormat('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            }).format(date);
        } catch {
            return 'N/A';
        }
    }, []);

    const getStatusConfig = useCallback((status: string) => {
        const configs = {
            active: {
                color: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300 border-green-200 dark:border-green-800',
                icon: PlayCircle,
                label: 'Active',
            },
            completed: {
                color: 'bg-brand-100 text-brand-800 dark:bg-brand-900/40 dark:text-brand-300 border-brand-200 dark:border-brand-800',
                icon: CheckCircle2,
                label: 'Completed',
            },
            paused: {
                color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800',
                icon: PauseCircle,
                label: 'Paused',
            },
            archived: {
                color: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400 border-gray-200 dark:border-gray-700',
                icon: FileText,
                label: 'Archived',
            }
        };
        return configs[status.toLowerCase() as keyof typeof configs] || configs.active;
    }, []);

    const statusConfig = useMemo(() => getStatusConfig(project.status), [project.status, getStatusConfig]);
    const StatusIcon = statusConfig.icon;

    const amrgCompleted = project.amrg_completed ?? false;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: index * 0.1 }}
            className="group"
        >
            <Card
                className="h-full p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-500 hover:bg-gray-50 dark:hover:bg-gray-800 transition-all duration-200 cursor-pointer overflow-hidden relative"
                onClick={handleProjectClick}
            >
                <div className="relative space-y-4">
                    {/* Header */}
                    <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                            <h3 className="text-lg font-semibold text-brand-500 dark:text-white mb-1 truncate group-hover:text-brand-700 dark:group-hover:text-brand-400 transition-colors">
                                {project.name}
                            </h3>
                            <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
                                {project.problem_statement || 'No description provided'}
                            </p>
                        </div>
                        <Badge className={`${statusConfig.color} ml-2 flex items-center gap-1 shrink-0 border`}>
                            <StatusIcon className="h-3 w-3" />
                            {statusConfig.label}
                        </Badge>
                    </div>

                    {/* Statistics Grid */}
                    <div className="space-y-3">
                        {/* Progress Overview */}
                        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-2">
                                    <TrendingUp className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                                    <span className="text-sm font-semibold text-brand-500 dark:text-gray-200">MVP Requirements</span>
                                </div>
                                {amrgCompleted && (
                                    <Badge className="bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300 border-green-200 dark:border-green-800">
                                        <CheckCircle2 className="h-3 w-3 mr-1" />
                                        Completed
                                    </Badge>
                                )}
                            </div>
                            <div className="flex items-center gap-2">
                                <div className={`w-full h-2 rounded-full ${amrgCompleted ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'}`} />
                            </div>
                        </div>

                        {/* Action Button */}
                        <Button
                            className="w-full bg-brand-500 hover:bg-brand-600 text-white group/btn"
                            size="sm"
                            onClick={handleProjectClick}
                        >
                            <div className="flex items-center justify-center">
                                <span className="font-medium">Open Project</span>
                                <ChevronRight className="ml-2 h-4 w-4 transition-transform group-hover/btn:translate-x-1" />
                            </div>
                        </Button>
                    </div>

                    {/* Project Info */}
                    <div className="flex items-center gap-4 text-xs text-gray-600 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700 pt-2">
                        <div className="flex items-center gap-1">
                            <Calendar className="h-3.5 w-3.5" />
                            <span>{formatDate(project.created_at)}</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <Clock className="h-3.5 w-3.5" />
                            <span>Updated {formatDate(project.updated_at)}</span>
                        </div>
                    </div>

                    {/* Navigation Loading Overlay */}
                    {isNavigating && (
                        <div className="absolute inset-0 bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm flex items-center justify-center rounded-xl z-10">
                            <div className="flex flex-col items-center gap-2">
                                <Loader2 className="h-6 w-6 animate-spin text-brand-600 dark:text-brand-400" />
                                <span className="text-xs text-brand-500 dark:text-gray-300 font-medium">Opening project...</span>
                            </div>
                        </div>
                    )}
                </div>
            </Card>
        </motion.div>
    );
});

ProjectAmrgCard.displayName = 'ProjectAmrgCard';
