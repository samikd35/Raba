'use client';

import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from '@/components/ui/button';
import { Input } from "@/components/ui/input";
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Search, FolderOpen, ArrowRightLeft, Users } from 'lucide-react';
import { toast } from "react-hot-toast";
import { Cohort } from "./types";

interface BulkMoveMemberModalProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    tenantId: string;
    currentCohortId: string;
    token: string;
    selectedMemberIds: string[];
    onMove: () => Promise<void>;
}

export const BulkMoveMemberModal = ({
    isOpen,
    onOpenChange,
    tenantId,
    currentCohortId,
    token,
    selectedMemberIds,
    onMove,
}: BulkMoveMemberModalProps) => {
    const [cohorts, setCohorts] = useState<Cohort[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCohortId, setSelectedCohortId] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (isOpen && tenantId && token) {
            fetchCohorts();
            setSelectedCohortId(null);
            setSearchQuery('');
        }
    }, [isOpen, tenantId, token]);

    const fetchCohorts = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/cohorts/${tenantId}?include_inactive=false`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Accept': 'application/json'
                    },
                }
            );

            if (!response.ok) {
                throw new Error('Failed to fetch cohorts');
            }

            const data = await response.json();
            let cohortsList: Cohort[] = [];
            if (Array.isArray(data)) {
                cohortsList = data;
            } else if (data && typeof data === 'object' && Array.isArray(data.cohorts)) {
                cohortsList = data.cohorts;
            } else if (data && typeof data === 'object' && Array.isArray(data.data)) {
                cohortsList = data.data;
            }

            const filteredCohorts = cohortsList.filter(
                (cohort: Cohort) => cohort.id !== currentCohortId
            );
            setCohorts(filteredCohorts);
        } catch (error) {
            console.error("Error fetching cohorts:", error);
            toast.error("Failed to load cohorts");
        } finally {
            setIsLoading(false);
        }
    };

    const handleBulkMove = async () => {
        if (!selectedCohortId || selectedMemberIds.length === 0) return;

        setIsSubmitting(true);
        try {
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/cohorts/${tenantId}/${currentCohortId}/members/bulk/move`,
                {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                    },
                    body: JSON.stringify({
                        member_tenant_ids: selectedMemberIds,
                        target_cohort_id: selectedCohortId
                    }),
                }
            );

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || 'Failed to move members');
            }

            const data = await response.json();
            toast.success(`Successfully moved ${data.successful} members to ${selectedCohort?.name}`);
            await onMove();
            onOpenChange(false);
        } catch (error: any) {
            console.error("Error moving members:", error);
            toast.error(error.message || "Failed to move members");
        } finally {
            setIsSubmitting(false);
        }
    };

    const filteredCohorts = cohorts.filter((cohort: Cohort) =>
        cohort.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        cohort.description?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const selectedCohort = cohorts.find(c => c.id === selectedCohortId);

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px] max-h-[70vh] flex flex-col p-0 gap-0 overflow-hidden">
                <DialogHeader className="bg-brand-25 border-b border-brand-100 p-4 shrink-0">
                    <DialogTitle>
                        <span className="text-brand-500 text-lg font-semibold">Bulk Move Members</span>
                    </DialogTitle>
                    <DialogDescription className="text-gray-600 text-sm">
                        Select a cohort to move <span className="font-medium text-brand-500">{selectedMemberIds.length} members</span> to.
                    </DialogDescription>
                </DialogHeader>

                <div className="p-4 shrink-0">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 select-none pointer-events-none" />
                        <Input
                            id="search-cohorts"
                            placeholder="Search cohorts..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-10 h-10 bg-white border-gray-200 focus:border-brand-300 transition-colors"
                        />
                    </div>
                </div>

                <div className="flex-1 overflow-hidden flex flex-col min-h-0 border-y border-gray-100">
                    <ScrollArea className="h-full overflow-y-auto bg-gray-50/10">
                        {isLoading ? (
                            <div className="flex justify-center items-center py-12">
                                <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
                            </div>
                        ) : filteredCohorts.length === 0 ? (
                            <div className="text-center py-12 text-gray-500 text-sm">
                                {searchQuery ? "No cohorts match your search" : "No other cohorts available"}
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-100">
                                {filteredCohorts.map((cohort: Cohort) => (
                                    <div
                                        key={cohort.id}
                                        className={`flex items-start gap-3 p-4 transition-colors cursor-pointer hover:bg-white ${selectedCohortId === cohort.id
                                            ? 'bg-brand-50/50 ring-1 ring-inset ring-brand-200'
                                            : ''
                                            }`}
                                        onClick={() => setSelectedCohortId(cohort.id)}
                                    >
                                        <div
                                            className="h-9 w-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5 shadow-sm"
                                            style={{ backgroundColor: cohort.color || '#7D53DE' }}
                                        >
                                            <FolderOpen className="h-4 w-4 text-white" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <p className="font-medium text-sm text-gray-900 truncate">{cohort.name}</p>
                                                {cohort.is_active ? (
                                                    <Badge
                                                        variant="outline"
                                                        className="text-[10px] h-4 bg-green-50 text-green-700 border-green-200 py-0"
                                                    >
                                                        Active
                                                    </Badge>
                                                ) : (
                                                    <Badge
                                                        variant="outline"
                                                        className="text-[10px] h-4 bg-gray-50 text-gray-500 border-gray-200 py-0"
                                                    >
                                                        Inactive
                                                    </Badge>
                                                )}
                                            </div>
                                            <p className="text-xs text-gray-500 truncate mt-0.5">
                                                {cohort.description || 'No description'}
                                            </p>
                                        </div>
                                        {/* Selection indicator */}
                                        <div className={`h-5 w-5 rounded-full border-2 flex items-center justify-center shrink-0 mt-1 transition-colors ${selectedCohortId === cohort.id
                                            ? 'border-brand-500 bg-brand-500'
                                            : 'border-gray-300 bg-white'
                                            }`}>
                                            {selectedCohortId === cohort.id && (
                                                <div className="h-2 w-2 rounded-full bg-white" />
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </ScrollArea>
                </div>

                <DialogFooter className="p-4 shrink-0 bg-white">
                    <div className="flex items-center justify-between w-full">
                        <div className="text-xs text-gray-500 font-medium truncate max-w-[150px]">
                            {selectedCohort ? (
                                <span className="truncate block">
                                    Moving to: <span className="text-brand-600">{selectedCohort.name}</span>
                                </span>
                            ) : (
                                "No cohort selected"
                            )}
                        </div>
                        <div className="flex gap-2">
                            <Button variant="outline" onClick={() => onOpenChange(false)} className="h-9 text-sm">
                                Cancel
                            </Button>
                            <Button
                                onClick={handleBulkMove}
                                disabled={!selectedCohortId || isSubmitting}
                                className="h-9 bg-brand-500 hover:bg-brand-600 transition-colors text-sm"
                            >
                                {isSubmitting ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Moving...
                                    </>
                                ) : (
                                    `Move ${selectedMemberIds.length} Members`
                                )}
                            </Button>
                        </div>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export default BulkMoveMemberModal;
