'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";

import CohortMembersList from './CohortMembersList';
import { Cohort } from './types';
import { CohortDetailLoading } from './CohortDetailLoading';
import { CohortHeader } from './CohortHeader';
import { CohortDetailsBar } from './CohortDetailsBar';
import { CohortEditModal } from './CohortEditModal';
import { CohortErrorState } from './CohortErrorState';
import { AddMembersModal } from './AddMembersModal';

// --- API ---
async function fetchCohortDetail(
    tenantId: string,
    cohortId: string,
    token: string,
    signal?: AbortSignal
): Promise<Cohort> {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/cohorts/${tenantId}/${cohortId}`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        signal,
    });

    if (!response.ok) {
        if (response.status === 401) throw new Error('Session expired');
        if (response.status === 404) throw new Error('Cohort not found');
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Failed to fetch cohort details`);
    }

    return response.json();
}

export default function CohortDetailComponent({ cohortId }: { cohortId: string }) {
    const { user, isInitialized, isAuthenticated, token } = useAuthStore();
    const [cohort, setCohort] = useState<Cohort | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [isAddMembersModalOpen, setIsAddMembersModalOpen] = useState(false);
    const [membersUpdateKey, setMembersUpdateKey] = useState(0);

    const fetchData = useCallback(async () => {
        if (!isInitialized) return;

        if (!isAuthenticated || !token || !user?.tenant_id) {
            setIsLoading(false);
            return;
        }

        if (abortControllerRef.current) abortControllerRef.current.abort();
        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            setIsLoading(true);
            setError(null);
            const data = await fetchCohortDetail(user.tenant_id, cohortId, token, controller.signal);
            setCohort(data);
        } catch (err: any) {
            if (err.name === 'AbortError') return;
            setError(err.message);
            toast.error(err.message);
        } finally {
            if (!controller.signal.aborted) {
                setIsLoading(false);
            }
        }
    }, [isInitialized, isAuthenticated, token, user?.tenant_id, cohortId]);

    useEffect(() => {
        fetchData();
        return () => abortControllerRef.current?.abort();
    }, [fetchData]);

    if (!isInitialized || (isLoading && !cohort)) {
        return <CohortDetailLoading />;
    }

    if (error || !cohort) {
        return <CohortErrorState error={error} onRetry={fetchData} />;
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
        >
            <CohortHeader
                cohort={cohort}
                onEditClick={() => setIsEditModalOpen(true)}
                onAddMembersClick={() => setIsAddMembersModalOpen(true)}
            />

            <CohortDetailsBar cohort={cohort} />

            <div className="space-y-6">
                {user?.tenant_id && token && (
                    <CohortMembersList
                        tenantId={user.tenant_id}
                        cohortId={cohortId}
                        token={token}
                        updateTrigger={membersUpdateKey}
                    />
                )}
            </div>

            {user?.tenant_id && token && (
                <>
                    <CohortEditModal
                        isOpen={isEditModalOpen}
                        onOpenChange={setIsEditModalOpen}
                        cohort={cohort}
                        tenantId={user.tenant_id}
                        token={token}
                        onSuccess={fetchData}
                    />
                    <AddMembersModal
                        isOpen={isAddMembersModalOpen}
                        onOpenChange={setIsAddMembersModalOpen}
                        tenantId={user.tenant_id}
                        cohortId={cohortId}
                        token={token}
                        onSuccess={() => {
                            setMembersUpdateKey(prev => prev + 1);
                            setIsAddMembersModalOpen(false);
                        }}
                    />
                </>
            )}
        </motion.div>
    );
}
