'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MoreHorizontal, ExternalLink, RefreshCw, AlertCircle, ChevronRight, Users, User, Building2, Loader2, Trash2, ArrowRightLeft } from "lucide-react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Tabs,
    TabsList,
    TabsTrigger,
} from "@/components/ui/tabs";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "react-hot-toast";
import { MoveMemberModal } from "./MoveMemberModal";
import { BulkMoveMemberModal } from "./BulkMoveMemberModal";
import { CohortMember } from "./types";

interface CohortMembersListProps {
    tenantId: string;
    cohortId: string;
    token: string;
    updateTrigger?: number;
}

// --- Helper Functions ---
const formatDate = (dateString: string) => {
    try {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(dateString));
    } catch {
        return 'N/A';
    }
};

export function CohortMembersList({ tenantId, cohortId, token, updateTrigger }: CohortMembersListProps) {
    const router = useRouter();
    const [members, setMembers] = useState<CohortMember[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [memberToRemove, setMemberToRemove] = useState<CohortMember | null>(null);
    const [isRemoving, setIsRemoving] = useState(false);
    const [memberToMove, setMemberToMove] = useState<CohortMember | null>(null);
    const [tenantTypeFilter, setTenantTypeFilter] = useState<'all' | 'team' | 'individual'>('all');
    const [viewingMemberId, setViewingMemberId] = useState<string | null>(null);
    const [selectedMemberIds, setSelectedMemberIds] = useState<string[]>([]);
    const [isBulkRemoving, setIsBulkRemoving] = useState(false);
    const [showBulkRemoveConfirm, setShowBulkRemoveConfirm] = useState(false);
    const [showBulkMoveModal, setShowBulkMoveModal] = useState(false);
    const [isBulkMoving, setIsBulkMoving] = useState(false);

    const fetchMembers = useCallback(async (isSilent = false) => {
        if (!tenantId || !cohortId || !token) return;

        try {
            if (!isSilent) setIsLoading(true);
            setError(null);
            // Matches: /api/cohorts/{tenant_id}/{cohort_id}/members?include_user_details=true
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/cohorts/${tenantId}/${cohortId}/members?include_user_details=true`,
                {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                }
            );



            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || 'Failed to fetch cohort members');
            }

            const data = await response.json();
            console.log("Members data:", data);

            if (Array.isArray(data)) {
                setMembers(data);
            } else if (data && typeof data === 'object' && Array.isArray(data.members)) {
                setMembers(data.members);
            } else if (data && typeof data === 'object' && Array.isArray(data.data)) {
                setMembers(data.data);
            } else {
                console.error("Unexpected response format for members:", data);
                setMembers([]);
            }
        } catch (err: any) {
            console.error(err);
            setError(err.message);
            toast.error("Could not load members list");
        } finally {
            setIsLoading(false);
        }
    }, [tenantId, cohortId, token]);

    const handleRemoveMember = async () => {
        if (!memberToRemove || !tenantId || !cohortId || !token) return;

        setIsRemoving(true);
        try {
            // Use member_tenant_id per new API spec
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/cohorts/${tenantId}/${cohortId}/members/${memberToRemove.member_tenant_id}`,
                {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'accept': 'application/json',
                    },
                }
            );

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || 'Failed to remove member from cohort');
            }

            toast.success(`${memberToRemove.user_name || memberToRemove.user_full_name || 'Member'} removed from cohort`);
            setMemberToRemove(null);
            setSelectedMemberIds(prev => prev.filter(id => id !== memberToRemove.member_tenant_id));
            fetchMembers(true); // Silent refresh
        } catch (err: any) {
            console.error(err);
            toast.error(err.message || 'Failed to remove member');
        } finally {
            setIsRemoving(false);
        }
    };

    const handleBulkRemove = async () => {
        if (selectedMemberIds.length === 0 || !tenantId || !cohortId || !token) return;

        setIsBulkRemoving(true);
        try {
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/cohorts/${tenantId}/${cohortId}/members/bulk`,
                {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                        'accept': 'application/json',
                    },
                    body: JSON.stringify({
                        member_tenant_ids: selectedMemberIds
                    })
                }
            );

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || 'Failed to remove members in bulk');
            }

            const data = await response.json();
            toast.success(`Successfully removed ${data.successful} members`);

            setSelectedMemberIds([]);
            setShowBulkRemoveConfirm(false);
            fetchMembers(true);
        } catch (err: any) {
            console.error(err);
            toast.error(err.message || 'Failed to remove members');
        } finally {
            setIsBulkRemoving(false);
        }
    };

    const toggleMemberSelection = (memberTenantId: string) => {
        setSelectedMemberIds(prev =>
            prev.includes(memberTenantId)
                ? prev.filter(id => id !== memberTenantId)
                : [...prev, memberTenantId]
        );
    };

    const toggleAllSelection = () => {
        if (selectedMemberIds.length === filteredMembers.length && filteredMembers.length > 0) {
            setSelectedMemberIds([]);
        } else {
            setSelectedMemberIds(filteredMembers.map(m => m.member_tenant_id));
        }
    };



    const filteredMembers = members.filter(member => {
        if (tenantTypeFilter === 'all') return true;
        return member.tenant_type === tenantTypeFilter;
    });

    useEffect(() => {
        // Use silent refresh if triggered by updateTrigger to avoid harsh skeleton flickers if already loaded
        const isSilent = updateTrigger !== undefined && updateTrigger > 0 && members.length > 0;
        fetchMembers(isSilent);
    }, [fetchMembers, updateTrigger]);

    if (isLoading) {
        return (
            <Card className="border border-gray-200 dark:border-gray-800">
                <CardHeader className="flex flex-row items-center justify-between px-6 border-b border-gray-100 dark:border-gray-800 bg-gray-50/30 dark:bg-gray-900/20">
                    <CardTitle className="text-lg font-semibold text-brand-500">Cohort Members</CardTitle>
                    <Skeleton className="h-8 w-24" />
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-hidden">
                        <Table className="border-collapse">
                            <TableHeader className="bg-gray-50/50 dark:bg-gray-900/50">
                                <TableRow className="hover:bg-transparent border-b border-gray-200 dark:border-gray-800">
                                    <TableHead className="w-[50px] pl-6 border-l border-gray-200 dark:border-gray-800">
                                        <Skeleton className="h-4 w-4 rounded" />
                                    </TableHead>
                                    <TableHead className="w-[60px] border-r border-gray-200 dark:border-gray-800">
                                        <Skeleton className="h-4 w-8" />
                                    </TableHead>
                                    <TableHead className="border-r border-gray-200 dark:border-gray-800">
                                        <Skeleton className="h-4 w-24" />
                                    </TableHead>
                                    <TableHead className="border-r border-gray-200 dark:border-gray-800">
                                        <Skeleton className="h-4 w-32" />
                                    </TableHead>
                                    <TableHead className="border-r border-gray-200 dark:border-gray-800">
                                        <Skeleton className="h-4 w-16" />
                                    </TableHead>
                                    <TableHead className="border-r border-gray-200 dark:border-gray-800">
                                        <Skeleton className="h-4 w-20" />
                                    </TableHead>
                                    <TableHead className="pr-6 border-r border-gray-200 dark:border-gray-800">
                                        <Skeleton className="h-4 w-12 ml-auto" />
                                    </TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {[1, 2, 3, 4, 5].map((i) => (
                                    <TableRow key={i} className="border-b border-gray-200 dark:border-gray-800">
                                        <TableCell className="pl-6 border-l border-gray-200 dark:border-gray-800">
                                            <Skeleton className="h-4 w-4 rounded" />
                                        </TableCell>
                                        <TableCell className="border-l border-r border-gray-200 dark:border-gray-800">
                                            <Skeleton className="h-5 w-6" />
                                        </TableCell>
                                        <TableCell className="border-r border-gray-200 dark:border-gray-800">
                                            <Skeleton className="h-5 w-40" />
                                        </TableCell>
                                        <TableCell className="border-r border-gray-200 dark:border-gray-800">
                                            <Skeleton className="h-5 w-48" />
                                        </TableCell>
                                        <TableCell className="border-r border-gray-200 dark:border-gray-800">
                                            <Skeleton className="h-6 w-20 rounded-full" />
                                        </TableCell>
                                        <TableCell className="border-r border-gray-200 dark:border-gray-800">
                                            <Skeleton className="h-5 w-24" />
                                        </TableCell>
                                        <TableCell className="pr-6 border-r border-gray-200 dark:border-gray-800">
                                            <div className="flex justify-end gap-2">
                                                <Skeleton className="h-8 w-24" />
                                                <Skeleton className="h-8 w-8" />
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (error) {
        return (
            <Card className="border-red-200 bg-red-50 dark:bg-red-900/10">
                <CardContent className="flex flex-col items-center justify-center py-10 text-red-600 dark:text-red-400">
                    <AlertCircle className="h-10 w-10 mb-2" />
                    <p className="font-medium">Failed to load members</p>
                    <p className="text-sm opacity-80 mb-4">{error}</p>
                    <Button variant="outline" size="sm" onClick={() => fetchMembers()} className="border-red-200 hover:bg-red-100 dark:border-red-800 dark:hover:bg-red-900/20">
                        <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} /> Try Again
                    </Button>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="border border-gray-200 dark:border-gray-800 transition-all hover:shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between px-6 border-b border-gray-100 dark:border-gray-800 bg-gray-50/30 dark:bg-gray-900/20">
                <CardTitle className="text-lg font-semibold text-brand-500 flex items-center gap-2">
                    Cohort Members
                    <Badge variant="outline" className="ml-2 bg-white dark:bg-gray-900 text-gray-500 border-gray-200 dark:border-gray-700 font-normal">
                        {filteredMembers.length}
                    </Badge>
                </CardTitle>

                <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-1 shadow-sm">
                    <Tabs
                        value={tenantTypeFilter}
                        onValueChange={(value: string) => setTenantTypeFilter(value as 'all' | 'team' | 'individual')}
                        className="w-full"
                    >
                        <TabsList className="grid w-[300px] grid-cols-3 h-8">
                            <TabsTrigger value="all" className="flex items-center gap-2 text-xs data-[state=active]:text-brand-600">
                                <Users className="w-3.5 h-3.5" />
                                All
                            </TabsTrigger>
                            <TabsTrigger value="team" className="flex items-center gap-2 text-xs data-[state=active]:text-brand-600">
                                <Building2 className="w-3.5 h-3.5" />
                                Teams
                            </TabsTrigger>
                            <TabsTrigger value="individual" className="flex items-center gap-2 text-xs data-[state=active]:text-brand-600">
                                <User className="w-3.5 h-3.5" />
                                Individuals
                            </TabsTrigger>
                        </TabsList>
                    </Tabs>
                </div>

                <div className="flex items-center gap-2">
                    {selectedMemberIds.length > 0 && (
                        <div className="flex items-center gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setShowBulkMoveModal(true)}
                                className="h-8 border-brand-200 text-brand-600 hover:bg-brand-50 hover:text-brand-700 shadow-sm"
                            >
                                <ArrowRightLeft className="mr-2 h-3.5 w-3.5" />
                                Move ({selectedMemberIds.length})
                            </Button>
                            <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => setShowBulkRemoveConfirm(true)}
                                className="h-8 bg-red-500 hover:bg-red-600 border-none shadow-sm"
                            >
                                <Trash2 className="mr-2 h-3.5 w-3.5" />
                                Remove ({selectedMemberIds.length})
                            </Button>
                        </div>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => fetchMembers()} disabled={isLoading} className="h-8 text-muted-foreground hover:text-brand-500 hover:bg-brand-50 dark:hover:bg-brand-900/20">
                        <RefreshCw className={`mr-2 h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                {filteredMembers.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                        <div className="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-full mb-3">
                            <AlertCircle className="h-6 w-6 text-gray-400" />
                        </div>
                        <p className="text-gray-900 dark:text-gray-100 font-medium mb-1">
                            {members.length === 0 ? "No members found" : `No ${tenantTypeFilter}s found`}
                        </p>
                        <p className="text-sm text-gray-500 max-w-sm">
                            {members.length === 0
                                ? "There are no members in this cohort yet. Add members to get started."
                                : `There are no ${tenantTypeFilter}s matching your filter in this cohort.`}
                        </p>
                    </div>
                ) : (
                    <div className="overflow-hidden border-t border-gray-200 dark:border-gray-800">
                        <Table className="border-collapse">
                            <TableHeader className="bg-gray-50/50 dark:bg-gray-900/50">
                                <TableRow className="hover:bg-transparent border-b border-gray-200 dark:border-gray-800">
                                    <TableHead className="w-[50px] pl-6 border-l border-gray-200 dark:border-gray-800">
                                        <Checkbox
                                            checked={filteredMembers.length > 0 && selectedMemberIds.length === filteredMembers.length}
                                            onCheckedChange={() => toggleAllSelection()}
                                            aria-label="Select all"
                                            className="translate-y-[2px]"
                                        />
                                    </TableHead>
                                    <TableHead className="w-[60px] font-semibold text-brand-500 dark:text-gray-400 border-r border-gray-200 dark:border-gray-800">NO</TableHead>
                                    <TableHead className="font-semibold text-brand-500 dark:text-gray-400 border-r border-gray-200 dark:border-gray-800">Full Name</TableHead>
                                    <TableHead className="font-semibold text-brand-500 dark:text-gray-400 border-r border-gray-200 dark:border-gray-800">Email</TableHead>
                                    <TableHead className="font-semibold text-brand-500 dark:text-gray-400 border-r border-gray-200 dark:border-gray-800">Role</TableHead>
                                    <TableHead className="font-semibold text-brand-500 dark:text-gray-400 border-r border-gray-200 dark:border-gray-800">Joined Date</TableHead>
                                    <TableHead className="text-right font-semibold text-brand-500 dark:text-gray-400 pr-6 border-r border-gray-200 dark:border-gray-800">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody className="[&_tr:last-child]:border-b">
                                {filteredMembers.map((member, index) => {
                                    const isRowRemoving = (isRemoving && memberToRemove?.member_tenant_id === member.member_tenant_id) ||
                                        (isBulkRemoving && selectedMemberIds.includes(member.member_tenant_id));

                                    const isRowMoving = isBulkMoving && selectedMemberIds.includes(member.member_tenant_id);

                                    const isProcessing = isRowRemoving || isRowMoving;

                                    return (
                                        <TableRow
                                            key={member.id}
                                            className={`hover:bg-brand-50/30 dark:hover:bg-brand-900/10 border-b border-gray-200 dark:border-gray-800 transition-colors ${selectedMemberIds.includes(member.member_tenant_id) ? 'bg-brand-50/20 dark:bg-brand-900/5' : ''} ${isProcessing ? 'opacity-50 cursor-not-allowed select-none' : ''}`}
                                        >
                                            <TableCell className="pl-6 border-l border-gray-200 dark:border-gray-800">
                                                {isProcessing ? (
                                                    <Loader2 className={`h-4 w-4 animate-spin ${isRowRemoving ? 'text-red-500' : 'text-brand-500'}`} />
                                                ) : (
                                                    <Checkbox
                                                        checked={selectedMemberIds.includes(member.member_tenant_id)}
                                                        onCheckedChange={() => toggleMemberSelection(member.member_tenant_id)}
                                                        aria-label={`Select ${member.user_name || 'member'}`}
                                                        className="translate-y-[2px]"
                                                    />
                                                )}
                                            </TableCell>
                                            <TableCell className="font-medium text-brand-500 border-l border-r border-gray-200 dark:border-gray-800">
                                                {(index + 1).toString().padStart(2, '0')}
                                            </TableCell>
                                            <TableCell className="border-r border-gray-200 dark:border-gray-800">
                                                <div className="flex items-center gap-2">
                                                    <div className="font-medium text-brand-500 dark:text-gray-100">
                                                        {member.user_name || member.user_full_name || 'Unknown'}
                                                    </div>
                                                    {isRowRemoving && (
                                                        <Badge variant="outline" className="text-[10px] h-4 px-1 bg-red-50 text-red-600 border-red-100 animate-pulse">
                                                            Removing...
                                                        </Badge>
                                                    )}
                                                    {isRowMoving && (
                                                        <Badge variant="outline" className="text-[10px] h-4 px-1 bg-brand-50 text-brand-600 border-brand-100 animate-pulse">
                                                            Moving...
                                                        </Badge>
                                                    )}
                                                </div>
                                            </TableCell>
                                            <TableCell className="border-r border-gray-200 dark:border-gray-800">
                                                <div className="text-gray-500 dark:text-gray-400 font-normal">
                                                    {member.user_email || 'No email'}
                                                </div>
                                            </TableCell>
                                            <TableCell className="border-r border-gray-200 dark:border-gray-800">
                                                <Badge
                                                    variant="secondary"
                                                    className={`capitalize shadow-none font-medium border flex items-center gap-1.5 px-2.5 py-0.5 transition-all duration-200 ${member.tenant_type === 'team'
                                                        ? "bg-blue-50 text-blue-700 border-blue-100 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800/50"
                                                        : "bg-teal-50 text-teal-700 border-teal-100 hover:bg-teal-100 dark:bg-teal-900/30 dark:text-teal-300 dark:border-teal-800/50"
                                                        }`}
                                                >
                                                    {member.tenant_type === 'team' ? (
                                                        <Building2 className="w-3 h-3" />
                                                    ) : (
                                                        <User className="w-3 h-3" />
                                                    )}
                                                    {member.tenant_type || 'member'}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-gray-500 text-sm border-r border-gray-200 dark:border-gray-800">
                                                {formatDate(member.created_at)}
                                            </TableCell>
                                            <TableCell className="text-right pr-6 border-r border-gray-200 dark:border-gray-800">
                                                <div className="flex items-center justify-end gap-2">
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        disabled={viewingMemberId === member.id || isProcessing}
                                                        onClick={() => {
                                                            setViewingMemberId(member.id);
                                                            router.push(`/organization/cohorts/${cohortId}/${member.member_tenant_id}`);
                                                        }}
                                                    >
                                                        {viewingMemberId === member.id ? (
                                                            <Loader2 className="w-4 h-4 animate-spin text-brand-500" />
                                                        ) : (
                                                            <>
                                                                <span className="text-sm text-brand-500">View Projects</span>
                                                                <ChevronRight className="w-4 h-4" />
                                                            </>
                                                        )}
                                                    </Button>
                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger asChild>
                                                            <Button
                                                                variant="ghost"
                                                                disabled={isProcessing}
                                                                className="h-8 w-8 p-0 text-gray-400 hover:text-brand-500 hover:bg-brand-50 dark:hover:bg-brand-900/20"
                                                            >
                                                                <span className="sr-only">Open menu</span>
                                                                <MoreHorizontal className="h-4 w-4" />
                                                            </Button>
                                                        </DropdownMenuTrigger>
                                                        <DropdownMenuContent align="end" className="w-48 border-gray-200 dark:border-gray-800">
                                                            <DropdownMenuLabel className="text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</DropdownMenuLabel>
                                                            <DropdownMenuSeparator className="bg-gray-100 dark:bg-gray-800" />
                                                            <DropdownMenuItem
                                                                className="text-gray-600 dark:text-gray-300 focus:text-brand-500 focus:bg-brand-50 dark:focus:bg-brand-900/20 cursor-pointer"
                                                                onClick={() => setMemberToMove(member)}
                                                            >
                                                                Move to another cohort
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem
                                                                className="text-red-500 focus:text-red-600 focus:bg-red-50 dark:focus:bg-red-900/10 cursor-pointer"
                                                                onClick={() => setMemberToRemove(member)}
                                                            >
                                                                Remove from Cohort
                                                            </DropdownMenuItem>
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    )
                                })}
                            </TableBody>
                        </Table>
                    </div>
                )}
            </CardContent>

            {/* Remove Member Confirmation Dialog */}
            <AlertDialog open={!!memberToRemove} onOpenChange={(open) => !open && setMemberToRemove(null)}>
                <AlertDialogContent className="sm:max-w-[425px]">
                    <AlertDialogHeader>
                        <AlertDialogTitle className="text-red-600">Remove Member from Cohort</AlertDialogTitle>
                        <AlertDialogDescription className="text-gray-600">
                            Are you sure you want to remove <span className="font-semibold text-gray-900">{memberToRemove?.user_name || memberToRemove?.user_full_name || 'this member'}</span> from this cohort?
                            This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={isRemoving} className="border-gray-200">
                            Cancel
                        </AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleRemoveMember}
                            disabled={isRemoving}
                            className="bg-red-500 hover:bg-red-600 text-white"
                        >
                            {isRemoving ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Removing...
                                </>
                            ) : 'Yes, Remove'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Bulk Remove Confirmation Dialog */}
            <AlertDialog open={showBulkRemoveConfirm} onOpenChange={setShowBulkRemoveConfirm}>
                <AlertDialogContent className="sm:max-w-[425px]">
                    <AlertDialogHeader>
                        <AlertDialogTitle className="text-red-600 flex items-center gap-2">
                            <Trash2 className="w-5 h-5" />
                            Bulk Remove Members
                        </AlertDialogTitle>
                        <AlertDialogDescription className="text-gray-600">
                            Are you sure you want to remove <span className="font-semibold text-gray-900">{selectedMemberIds.length} members</span> from this cohort?
                            This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={isBulkRemoving} className="border-gray-200">
                            Cancel
                        </AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleBulkRemove}
                            disabled={isBulkRemoving}
                            className="bg-red-500 hover:bg-red-600 text-white"
                        >
                            {isBulkRemoving ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Removing...
                                </>
                            ) : `Yes, Remove ${selectedMemberIds.length} Members`}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Move Member Modal */}
            <MoveMemberModal
                isOpen={!!memberToMove}
                onOpenChange={(open) => !open && setMemberToMove(null)}
                tenantId={tenantId}
                currentCohortId={cohortId}
                token={token}
                member={memberToMove ? {
                    user_id: memberToMove.user_id,
                    member_tenant_id: memberToMove.member_tenant_id,
                    name: memberToMove.user_name || memberToMove.user_full_name || 'Unknown',
                    email: memberToMove.user_email || '',
                } : null}
                onMove={async () => {
                    // Refresh members list after successful move
                    fetchMembers(true);
                    setMemberToMove(null);
                }}
            />

            {/* Bulk Move Modal */}
            <BulkMoveMemberModal
                isOpen={showBulkMoveModal}
                onOpenChange={setShowBulkMoveModal}
                tenantId={tenantId}
                currentCohortId={cohortId}
                token={token}
                selectedMemberIds={selectedMemberIds}
                onMove={async () => {
                    setIsBulkMoving(true);
                    setSelectedMemberIds([]);
                    // Wait a bit to show the "Moving..." state in the table before refreshing
                    setTimeout(() => {
                        fetchMembers(true);
                        setIsBulkMoving(false);
                    }, 1000);
                }}
            />
        </Card>
    );
}

export default CohortMembersList;
