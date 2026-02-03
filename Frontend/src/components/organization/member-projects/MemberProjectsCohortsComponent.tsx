'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";

import { Cohort } from '@/components/organization/cohorts/types';
import { getCachedData, setCachedData } from '@/components/organization/cohorts/cohortsCache';
import { fetchCohorts } from '@/components/organization/cohorts/cohortsApi';
import { MemberProjectsCohortsLoading } from './MemberProjectsCohortsLoading';
import { MemberProjectsCohortsError } from './MemberProjectsCohortsError';
import { MemberProjectsCohortsEmpty } from './MemberProjectsCohortsEmpty';
import { MemberProjectsCohortCard } from './MemberProjectsCohortCard';
import { MemberProjectsCohortsFilters, FilterState } from './MemberProjectsCohortsFilters';
import { Card } from '@/components/ui/card';

type LoadStatus = 'loading' | 'success' | 'error' | 'empty';

export default function MemberProjectsCohortsComponent() {
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

    const isFetchingRef = useRef(false);
    const abortControllerRef = useRef<AbortController | null>(null);
    const hasInitialFetchedRef = useRef(false);

    const fetchData = useCallback(async (forceRefresh: boolean = false) => {
        if (!isInitialized) return;

        if (!isAuthenticated || !token || !tenantId) {
            console.warn('MemberProjectsCohortsComponent: Cannot fetch - missing auth data');
            return;
        }

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const controller = new AbortController();
        abortControllerRef.current = controller;
        const signal = controller.signal;

        isFetchingRef.current = true;

        if (!forceRefresh && !hasInitialFetchedRef.current) {
            const cached = getCachedData();
            if (cached && Array.isArray(cached) && cached.length > 0) {
                setCohorts(cached);
                setStatus('success');
            }
        }

        try {
            if (cohorts.length === 0 && !getCachedData()) {
                setStatus('loading');
            }

            const data = await fetchCohorts(tenantId, token, signal);

            if (signal.aborted) {
                return;
            }

            if (Array.isArray(data)) {
                setCohorts(data);
                setCachedData(data);
                setStatus(data.length > 0 ? 'success' : 'empty');
            } else {
                setCohorts(prev => prev.length > 0 ? prev : []);
                setStatus(prev => prev === 'loading' ? 'empty' : prev);
            }
            hasInitialFetchedRef.current = true;
        } catch (err: any) {
            if (err.name === 'AbortError') {
                return;
            }

            const errorMessage = err.message || 'An unexpected error occurred';

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
    }, [isInitialized, isAuthenticated, token, tenantId]);

    useEffect(() => {
        if (isInitialized && isAuthenticated && token && tenantId && !hasInitialFetchedRef.current) {
            fetchData();
        }
    }, [isInitialized, isAuthenticated, token, tenantId, fetchData]);

    useEffect(() => {
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    useEffect(() => {
        if (isInitialized && status === 'loading') {
            const timer = setTimeout(() => {
                if (status === 'loading' && (!isAuthenticated || !tenantId)) {
                    setError("Loading is taking longer than expected. Please ensure you are logged in.");
                    setStatus('error');
                }
            }, 8000);
            return () => clearTimeout(timer);
        }
    }, [isInitialized, status, isAuthenticated, tenantId]);

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

    if (isInitialized && !isAuthenticated) {
        return null;
    }

    if (status === 'loading') {
        return <MemberProjectsCohortsLoading />;
    }

    if (status === 'error') {
        return <MemberProjectsCohortsError error={error || 'An error occurred'} onRetry={handleRetry} />;
    }

    if (status === 'empty' && !filters.search) {
        return <MemberProjectsCohortsEmpty />;
    }

    return (
        <Card className='p-4'>
            <MemberProjectsCohortsFilters
                filters={filters}
                setFilters={setFilters}
                onRefresh={handleRetry}
            />

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
            >
                {filteredAndSortedCohorts.map((cohort, index) => (
                    <MemberProjectsCohortCard
                        key={cohort.id}
                        cohort={cohort}
                        index={index}
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
        </Card>
    );
}
