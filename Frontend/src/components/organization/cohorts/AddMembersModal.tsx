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
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Loader2, Search } from 'lucide-react';
import { toast } from "react-hot-toast";

interface Member {
    user_id: string;
    individual_tenant_id: string; // The tenant ID to use as member_tenant_id
    name: string;
    email: string;
    role: string;
    status: string;
    joined_at?: string;
    team_name?: string;
}

interface AddMembersModalProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    tenantId: string;
    cohortId: string;
    token: string;
    onSuccess: () => void;
}

export const AddMembersModal = ({
    isOpen,
    onOpenChange,
    tenantId,
    cohortId,
    token,
    onSuccess,
}: AddMembersModalProps) => {
    const [allMembers, setAllMembers] = useState<Member[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedMemberIds, setSelectedMemberIds] = useState<Set<string>>(new Set());
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        console.log('AddMembersModal useEffect', isOpen, tenantId, token);
        if (isOpen && tenantId && token) {
            fetchMembers();
            setSelectedMemberIds(new Set()); // Reset selection on open
        }
    }, [isOpen, tenantId, token]);

    const fetchMembers = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/organization/${tenantId}/member-projects?page=1&page_size=50&member_type=all`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json'
                },
            });

            console.log('Member projects response:', response);

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`Fetch failed with status ${response.status}: ${errorText}`);
                throw new Error(`Failed to fetch members: ${response.statusText} (${response.status})`);
            }

            const data = await response.json();
            const membersList = (data.members || []).map((m: any) => ({
                user_id: m.user_id || m.tenant_id, // Fallback to tenant_id if user_id is missing
                individual_tenant_id: m.tenant_id, // The ID needed for cohort assignment
                name: m.user_name || m.team_name || "Unknown",
                email: m.user_email || (m.team_admin_emails && m.team_admin_emails[0]) || "",
                role: m.member_type, // 'individual' or 'team'
                status: "Active", // Default status
                joined_at: new Date().toISOString(),
            }));

            setAllMembers(membersList);
        } catch (error) {
            console.error("Error fetching members:", error);
            toast.error("Failed to load organization members");
        } finally {
            setIsLoading(false);
        }
    };

    const toggleMember = (memberId: string) => {
        const newSelection = new Set(selectedMemberIds);
        if (newSelection.has(memberId)) {
            newSelection.delete(memberId);
        } else {
            newSelection.add(memberId);
        }
        setSelectedMemberIds(newSelection);
    };

    const toggleSelectAll = () => {
        if (selectedMemberIds.size === filteredMembers.length) {
            setSelectedMemberIds(new Set());
        } else {
            setSelectedMemberIds(new Set(filteredMembers.map(m => m.individual_tenant_id)));
        }
    };

    const handleAddMembers = async () => {
        if (!tenantId || !cohortId || !token || selectedMemberIds.size === 0) return;

        // Get all selected member tenant IDs
        const memberTenantIds = Array.from(selectedMemberIds);

        setIsSubmitting(true);
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/cohorts/${tenantId}/${cohortId}/members/bulk`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    'accept': 'application/json',
                },
                body: JSON.stringify({
                    member_tenant_ids: memberTenantIds
                }),
            });

            console.log("Bulk add response:", response);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || errorData.detail || 'Failed to assign members to cohort');
            }

            const result = await response.json();
            console.log("Bulk add result:", result);

            // Handle mixed results
            if (result.failed > 0 && result.successful > 0) {
                toast.success(`${result.successful} member(s) added successfully. ${result.failed} failed.`);
                // Show details for failed ones
                const failedResults = result.results?.filter((r: any) => !r.success) || [];
                failedResults.forEach((r: any) => {
                    if (r.error) {
                        toast.error(`Failed: ${r.error}`);
                    }
                });
            } else if (result.failed > 0) {
                // All failed
                const failedResults = result.results?.filter((r: any) => !r.success) || [];
                const errorMsg = failedResults[0]?.error || 'Failed to add members';
                throw new Error(errorMsg);
            } else {
                // All successful
                toast.success(`${result.successful} member(s) added to cohort successfully`);
            }

            onSuccess();
            onOpenChange(false);
        } catch (err: any) {
            console.error(err);
            toast.error(err.message || "Failed to add members");
        } finally {
            setIsSubmitting(false);
        }
    };

    const filteredMembers = allMembers.filter((member: Member) =>
        member.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        member.email.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px] max-h-[70vh] flex flex-col p-0 gap-0 overflow-hidden">
                <DialogHeader className="bg-brand-25 border-b border-brand-100 p-4 shrink-0">
                    <DialogTitle><span className="text-brand-500 text-lg font-semibold">Add Members to Cohort</span></DialogTitle>
                    <DialogDescription className="text-gray-600 text-sm">
                        Select one or more members from your organization to assign.
                    </DialogDescription>
                </DialogHeader>

                <div className="p-4 shrink-0">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 select-none pointer-events-none" />
                        <Input
                            id="search"
                            placeholder="Search by name or email..."
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
                        ) : filteredMembers.length === 0 ? (
                            <div className="text-center py-12 text-gray-500 text-sm">
                                {searchQuery ? "No members match your search" : "No organization members found"}
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-100">
                                {filteredMembers.map((member: Member) => (
                                    <div
                                        key={member.individual_tenant_id}
                                        className={`flex items-start gap-3 p-4 transition-colors cursor-pointer hover:bg-white ${selectedMemberIds.has(member.individual_tenant_id)
                                            ? 'bg-brand-50/30'
                                            : ''
                                            }`}
                                        onClick={() => toggleMember(member.individual_tenant_id)}
                                    >
                                        <Checkbox
                                            checked={selectedMemberIds.has(member.individual_tenant_id)}
                                            onCheckedChange={() => toggleMember(member.individual_tenant_id)}
                                            className="mt-1"
                                        />
                                        <Avatar className="h-9 w-9 border border-gray-100 shadow-sm mt-0.5">
                                            <AvatarImage src={`https://ui-avatars.com/api/?name=${encodeURIComponent(member.name)}&background=random`} />
                                            <AvatarFallback>{member.name.substring(0, 2).toUpperCase()}</AvatarFallback>
                                        </Avatar>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <p className="font-medium text-sm text-gray-900 truncate">{member.name}</p>
                                                {member.status === 'Active' ? (
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
                                                        {member.status}
                                                    </Badge>
                                                )}
                                            </div>
                                            <p className="text-xs text-gray-500 truncate">{member.email}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </ScrollArea>
                </div>

                <DialogFooter className="p-4 shrink-0 bg-white">
                    <div className="flex items-center justify-between w-full">
                        <div className="text-xs text-gray-500 font-medium">
                            {selectedMemberIds.size > 0
                                ? `${selectedMemberIds.size} member${selectedMemberIds.size > 1 ? 's' : ''} selected`
                                : "No selection"}
                        </div>
                        <div className="flex gap-2">
                            <Button variant="outline" onClick={() => onOpenChange(false)} className="h-9">
                                Cancel
                            </Button>
                            <Button
                                onClick={handleAddMembers}
                                disabled={selectedMemberIds.size === 0 || isSubmitting}
                                className="h-9 bg-brand-500 hover:bg-brand-600 transition-colors"
                            >
                                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Add to Cohort
                            </Button>
                        </div>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
