import React, { useState } from 'react';
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Loader2 } from 'lucide-react';
import { toast } from "react-hot-toast";

interface CreateCohortModalProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    tenantId: string;
    token: string;
    onSuccess: () => void;
}

export const CreateCohortModal = ({
    isOpen,
    onOpenChange,
    tenantId,
    token,
    onSuccess,
}: CreateCohortModalProps) => {
    const [isCreating, setIsCreating] = useState(false);
    const [newCohort, setNewCohort] = useState({
        name: '',
        description: '',
        color: '#7D53DE',
    });

    const handleCreateCohort = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!tenantId || !token) return;

        if (!newCohort.name.trim()) {
            toast.error("Cohort name is required");
            return;
        }

        setIsCreating(true);
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/cohorts/${tenantId}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: newCohort.name,
                    description: newCohort.description,
                    color: newCohort.color,
                    settings: {}
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `Failed to create cohort`);
            }

            toast.success("Cohort created successfully!");
            onOpenChange(false);
            setNewCohort({ name: '', description: '', color: '#7D53DE' });
            onSuccess();
        } catch (err: any) {
            toast.error(err.message || "Failed to create cohort");
        } finally {
            setIsCreating(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader className="bg-brand-25 dark:bg-brand-950/30 px-6 py-4 border-b border-brand-100 dark:border-brand-900/50 -mx-6 -mt-6 mb-4 rounded-t-lg text-left">
                    <DialogTitle className="text-lg font-semibold text-brand-500 dark:text-white">
                        Create New Cohort
                    </DialogTitle>
                    <DialogDescription className="text-sm text-gray-600 dark:text-gray-400">
                        Add a new cohort to organize your users and analysis.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateCohort} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="name_modal" className="text-sm font-medium text-brand-500 dark:text-brand-400">Cohort Name</Label>
                        <Input
                            id="name_modal"
                            placeholder="Enter cohort name"
                            value={newCohort.name}
                            onChange={(e) => setNewCohort(prev => ({ ...prev, name: e.target.value }))}
                            required
                            className="h-10"
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="description_modal" className="text-sm font-medium text-brand-500 dark:text-brand-400">Description</Label>
                        <Textarea
                            id="description_modal"
                            placeholder="Describe the purpose of this cohort"
                            value={newCohort.description}
                            onChange={(e) => setNewCohort(prev => ({ ...prev, description: e.target.value }))}
                            className="min-h-[100px] resize-none"
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="color_modal" className="text-sm font-medium text-brand-500 dark:text-brand-400">Brand Color</Label>
                        <div className="flex items-center gap-3">
                            <Input
                                id="color_modal"
                                type="color"
                                value={newCohort.color}
                                onChange={(e) => setNewCohort(prev => ({ ...prev, color: e.target.value }))}
                                className="w-12 h-10 p-1 cursor-pointer border-gray-200 dark:border-gray-700"
                            />
                            <Input
                                type="text"
                                value={newCohort.color}
                                onChange={(e) => setNewCohort(prev => ({ ...prev, color: e.target.value }))}
                                placeholder="#000000"
                                className="font-mono uppercase h-10"
                            />
                        </div>
                    </div>
                    <DialogFooter className="sm:justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-800 mt-6">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={isCreating}
                            className="h-9 px-6"
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            disabled={isCreating}
                            className="h-9 bg-brand-500 hover:bg-brand-600 text-white px-6 shadow-sm hover:shadow transition-all"
                        >
                            {isCreating ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Creating...
                                </>
                            ) : (
                                'Create Cohort'
                            )}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};
