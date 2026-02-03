import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from '@/components/ui/button';
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Loader2 } from 'lucide-react';
import { toast } from "react-hot-toast";
import { Cohort } from './types';

interface CohortEditModalProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    cohort: Cohort;
    tenantId: string;
    token: string;
    onSuccess: () => void;
}

export const CohortEditModal = ({
    isOpen,
    onOpenChange,
    cohort,
    tenantId,
    token,
    onSuccess,
}: CohortEditModalProps) => {
    const [isSaving, setIsSaving] = useState(false);
    const [editForm, setEditForm] = useState({
        name: '',
        description: '',
        color: '',
    });

    useEffect(() => {
        if (cohort) {
            setEditForm({
                name: cohort.name || '',
                description: cohort.description || '',
                color: cohort.color || '#7D53DE',
            });
        }
    }, [cohort]);

    const handleUpdateCohort = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!tenantId || !token || !cohort) return;

        if (!editForm.name.trim()) {
            toast.error("Cohort name is required");
            return;
        }

        setIsSaving(true);
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/cohorts/${tenantId}/${cohort.id}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...editForm,
                    settings: cohort.settings
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || 'Failed to update cohort');
            }

            toast.success("Cohort updated successfully");
            onOpenChange(false);
            onSuccess();
        } catch (err: any) {
            toast.error(err.message);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader className="bg-brand-25 border-b border-brand-100 p-4 -mx-6 -mt-6 rounded-t-lg">
                    <DialogTitle><span className="text-brand-500">Edit Cohort Details</span></DialogTitle>
                    <DialogDescription className="text-brand-400">
                        Make changes to the cohort here. Click save when you're done.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleUpdateCohort} className="space-y-4 pt-4">
                    <div className="space-y-2">
                        <Label htmlFor="name" className='text-brand-500'>Name</Label>
                        <Input
                            id="name"
                            value={editForm.name}
                            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                            placeholder="Cohort Name"
                            required
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="description" className='text-brand-500'>Description</Label>
                        <Textarea
                            id="description"
                            value={editForm.description}
                            onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                            placeholder="Description"
                            className="min-h-[100px]"
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="color" className='text-brand-500'>Color</Label>
                        <div className="flex items-center gap-2">
                            <Input
                                id="color"
                                type="color"
                                value={editForm.color}
                                onChange={(e) => setEditForm({ ...editForm, color: e.target.value })}
                                className="w-12 h-10 p-1 cursor-pointer"
                            />
                            <Input
                                value={editForm.color}
                                onChange={(e) => setEditForm({ ...editForm, color: e.target.value })}
                                placeholder="#000000"
                                className="font-mono"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSaving}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isSaving}>
                            {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                            Save Changes
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};
