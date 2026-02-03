'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";

import { Cohort } from './types';
import { getCachedData, setCachedData } from './cohortsCache';
import { fetchCohorts } from './cohortsApi';
import { CohortsLoading } from './CohortsLoading';
import { CohortsError } from './CohortsError';
import { CohortsEmpty } from './CohortsEmpty';
import { CohortCard } from './CohortCard';
import { CreateCohortModal } from './CreateCohortModal';
import { CohortsFilters, FilterState } from './CohortsFilters';

type LoadStatus = 'loading' | 'success' | 'error' | 'empty';

export default function CohortsComponent({ path }: { path: string }) {
    const router = useRouter();
    const { user, isInitialized, isAuthenticated, token } = useAuthStore();
    const tenantId = user?.tenant_id;

    const [cohorts, setCohorts] = useState<Cohort[]>([]);
    const [status, setStatus] = useState<LoadStatus>('loading');
    const [error, setError] = useState<string | null>(null);
    const [filters, setFilters] = useState<FilterState>({
        search: '',
        sortBy: 'updated_at',
        sortDirection: 'desc'
    });

    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

    const isFetchingRef = useRef(false);
    const abortControllerRef = useRef<AbortController | null>(null);
    const hasInitialFetchedRef = useRef(false);

    const fetchData = useCallback(async (forceRefresh: boolean = false) => {
        // Skip if not initialized
        if (!isInitialized) return;

        console.log('CohortsComponent: fetchData triggered', { isAuthenticated, hasToken: !!token, hasTenant: !!tenantId, forceRefresh });

        if (!isAuthenticated || !token || !tenantId) {
            console.warn('CohortsComponent: Cannot fetch - missing auth data', { isAuthenticated, hasToken: !!token, hasTenant: !!tenantId });
            return;
        }

        // Abort any ongoing request before starting a new one
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const controller = new AbortController();
        abortControllerRef.current = controller;
        const signal = controller.signal;

        isFetchingRef.current = true;

        // 1. Initial Cache Load (Instant UI)
        // Only do this if we don't have cohorts yet or if forcing refresh from a fresh state
        if (!forceRefresh && !hasInitialFetchedRef.current) {
            const cached = getCachedData();
            if (cached && Array.isArray(cached) && cached.length > 0) {
                console.log('CohortsComponent: Showing initial data from cache', { count: cached.length });
                setCohorts(cached);
                setStatus('success');
                // We don't set hasInitialFetchedRef.current = true yet because we still want the network fetch to complete
            }
        }

        try {
            // Only show loader if we have no cohorts yet (either in state or cache)
            if (cohorts.length === 0 && !getCachedData()) {
                setStatus('loading');
            }

            console.log('CohortsComponent: Initiating API fetch...');
            const data = await fetchCohorts(tenantId, token, signal);

            if (signal.aborted) {
                console.log('CohortsComponent: Fetch completed but signal was aborted, ignoring results');
                return;
            }

            if (Array.isArray(data)) {
                setCohorts(data);
                setCachedData(data);
                setStatus(data.length > 0 ? 'success' : 'empty');
            } else {
                console.error('CohortsComponent: Unexpected API response format', data);
                // If we have cached data, keep it instead of showing empty
                setCohorts(prev => prev.length > 0 ? prev : []);
                setStatus(prev => prev === 'loading' ? 'empty' : prev);
            }
            hasInitialFetchedRef.current = true;
        } catch (err: any) {
            if (err.name === 'AbortError') {
                console.log('CohortsComponent: Fetch aborted officially');
                return;
            }

            console.error('CohortsComponent: API Error', err);
            const errorMessage = err.message || 'An unexpected error occurred';

            // If we already have cohorts (from cache or previous fetch), don't show the error screen, just toast it
            if (cohorts.length > 0) {
                toast.error(`Refresh failed: ${errorMessage}`);
                setStatus('success');
            } else {
                setError(errorMessage);
                setStatus('error');
                toast.error(errorMessage);
            }
        } finally {
            if (abortControllerRef.current === controller) {
                isFetchingRef.current = false;
            }
        }
    }, [isInitialized, isAuthenticated, token, tenantId]); // Removed cohorts.length to stabilize the callback

    // Initial fetch and cleanup
    useEffect(() => {
        if (isInitialized && isAuthenticated && token && tenantId && !hasInitialFetchedRef.current) {
            console.log('CohortsComponent: Executing initial fetch');
            fetchData();
        }

        return () => {
            // Only abort on unmount, not on every re-render
            // If critical deps change, a new fetchData will be created and called, which handles its own aborting
        };
    }, [isInitialized, isAuthenticated, token, tenantId, fetchData]);

    // Additional Cleanup Effect for unmounting correctly
    useEffect(() => {
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    // Safety timeout: If we're stuck in loading for too long while initialized, show an error
    useEffect(() => {
        if (isInitialized && status === 'loading') {
            const timer = setTimeout(() => {
                if (status === 'loading' && (!isAuthenticated || !tenantId)) {
                    setError("Loading is taking longer than expected. Please ensure you are logged in and have selected a workspace.");
                    setStatus('error');
                }
            }, 8000);
            return () => clearTimeout(timer);
        }
    }, [isInitialized, status, isAuthenticated, tenantId]);

    // Handle authentication redirect
    useEffect(() => {
        if (isInitialized && !isAuthenticated) {
            router.push('/signin');
        }
    }, [isInitialized, isAuthenticated, router]);

    const filteredAndSortedCohorts = useMemo(() => {
        if (!Array.isArray(cohorts)) return [];

        let filtered = [...cohorts];

        if (filters.search) {
            const searchLower = filters.search.toLowerCase();
            filtered = filtered.filter(cohort =>
                cohort.name.toLowerCase().includes(searchLower) ||
                cohort.description?.toLowerCase().includes(searchLower)
            );
        }

        filtered.sort((a, b) => {
            let comparison = 0;
            switch (filters.sortBy) {
                case 'name':
                    comparison = (a.name || '').localeCompare(b.name || '');
                    break;
                case 'created_at':
                    comparison = new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime();
                    break;
                case 'updated_at':
                    comparison = new Date(a.updated_at || 0).getTime() - new Date(b.updated_at || 0).getTime();
                    break;
            }
            return filters.sortDirection === 'asc' ? comparison : -comparison;
        });

        return filtered;
    }, [cohorts, filters]);

    const handleRetry = useCallback(() => fetchData(true), [fetchData]);

    // Render logic
    if (isInitialized && !isAuthenticated) {
        return null;
    }

    if (status === 'loading') {
        return <CohortsLoading />;
    }

    if (status === 'error') {
        return <CohortsError error={error || 'An error occurred'} onRetry={handleRetry} />;
    }

    if (status === 'empty' && !filters.search) {
        return (
            <div className="space-y-6">
                <div className="flex justify-end">
                    <Button onClick={() => setIsCreateModalOpen(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        Add Cohort
                    </Button>
                </div>

                {tenantId && token && (
                    <CreateCohortModal
                        isOpen={isCreateModalOpen}
                        onOpenChange={setIsCreateModalOpen}
                        tenantId={tenantId}
                        token={token}
                        onSuccess={() => fetchData(true)}
                    />
                )}

                <CohortsEmpty />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <CohortsFilters
                filters={filters}
                setFilters={setFilters}
                onRefresh={handleRetry}
                onAddClick={() => setIsCreateModalOpen(true)}
            />

            <div className="text-sm text-gray-500 dark:text-gray-400">
                Showing {filteredAndSortedCohorts.length} of {cohorts.length} cohorts
            </div>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
            >
                {filteredAndSortedCohorts.map((cohort, index) => (
                    <CohortCard
                        key={cohort.id}
                        cohort={cohort}
                        index={index}
                        path={path}
                    />
                ))}
            </motion.div>

            {filteredAndSortedCohorts.length === 0 && (
                <div className="text-center py-12 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-dashed border-gray-200 dark:border-gray-700">
                    <p className="text-gray-500 dark:text-gray-400">
                        No cohorts found matching your filters.
                    </p>
                    <Button
                        variant="link"
                        onClick={() => setFilters({ search: '', sortBy: 'updated_at', sortDirection: 'desc' })}
                    >
                        Clear filters
                    </Button>
                </div>
            )}

            {tenantId && token && (
                <CreateCohortModal
                    isOpen={isCreateModalOpen}
                    onOpenChange={setIsCreateModalOpen}
                    tenantId={tenantId}
                    token={token}
                    onSuccess={() => fetchData(true)}
                />
            )}
        </div>
    );
}
