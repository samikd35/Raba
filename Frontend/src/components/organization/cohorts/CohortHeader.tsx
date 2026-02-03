import React from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft, Settings, CheckCircle2, XCircle, UserPlus, Trash2, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import { Cohort } from './types';

interface CohortHeaderProps {
    cohort: Cohort;
    onEditClick: () => void;
    onAddMembersClick: () => void;
}

export const CohortHeader = ({ cohort, onEditClick, onAddMembersClick }: CohortHeaderProps) => {
    const router = useRouter();
    const { token } = useAuthStore();
    const [isDeleteDialogOpen, setIsDeleteDialogOpen] = React.useState(false);
    const [isDeleting, setIsDeleting] = React.useState(false);

    const handleDeleteCohort = async () => {
        if (!token || !cohort.tenant_id || !cohort.id) {
            toast.error("Missing required information to delete cohort");
            return;
        }

        setIsDeleting(true);
        try {
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/cohorts/${cohort.tenant_id}/${cohort.id}`,
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
                throw new Error(errorData.message || 'Failed to delete cohort');
            }

            toast.success(`Cohort "${cohort.name}" deleted successfully`);
            router.push('/organization/cohorts');
        } catch (err: any) {
            console.error(err);
            toast.error(err.message || 'Failed to delete cohort');
        } finally {
            setIsDeleting(false);
            setIsDeleteDialogOpen(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
        >
            <div
                className="flex items-center justify-between p-2 border rounded-lg"
                style={{
                    borderColor: cohort.color,
                    backgroundColor: `${cohort.color}10`
                }}
            >
                <div className="flex items-center gap-4">
                    <div className="text-brand-500 dark:text-gray-400 flex items-center gap-2 px-4 border-gray-200 dark:border-gray-600 py-2 border rounded-lg justify-center">
                        <div className="flex items-center gap-3">
                            <div
                                className="w-4 h-4 rounded-full"
                                style={{ backgroundColor: cohort.color }}
                            />
                            <h1 className="text-xl font-semibold text-brand-500 dark:text-gray-100">
                                {cohort.name}
                            </h1>
                        </div>
                        <Badge
                            variant="outline"
                            className={cohort.is_active
                                ? "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800"
                                : "bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-900/20 dark:text-gray-400 dark:border-gray-700"
                            }
                        >
                            {cohort.is_active ? (
                                <CheckCircle2 className="w-3 h-3 mr-1" />
                            ) : (
                                <XCircle className="w-3 h-3 mr-1" />
                            )}
                            {cohort.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                    </div>
                </div>

                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => router.back()} className='text-brand-500 dark:text-gray-400'>
                        <ArrowLeft className="h-4 w-4 mr-2" />  Back
                    </Button>
                    <Button
                        onClick={() => setIsDeleteDialogOpen(true)}
                        className="text-white bg-red-500 hover:bg-red-600 dark:hover:bg-red-900/20 px-3 flex items-center gap-2"
                    >
                        <Trash2 className="h-4 w-4" />
                        Delete
                    </Button>

                    <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
                        <AlertDialogContent className="sm:max-w-[425px]">
                            <AlertDialogHeader>
                                <AlertDialogTitle className="text-red-600 flex items-center gap-2">
                                    <Trash2 className="h-5 w-5" />
                                    Delete Cohort
                                </AlertDialogTitle>
                                <AlertDialogDescription className="text-gray-600 dark:text-gray-400">
                                    Are you sure you want to delete <span className="font-semibold text-gray-900 dark:text-gray-100">{cohort.name}</span>?
                                    This action will also deactivate all credit lots associated with this cohort.
                                    This action cannot be undone.
                                </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                                <AlertDialogCancel disabled={isDeleting} className="border-gray-200 dark:border-gray-800">
                                    Cancel
                                </AlertDialogCancel>
                                <AlertDialogAction
                                    onClick={(e) => {
                                        e.preventDefault();
                                        handleDeleteCohort();
                                    }}
                                    disabled={isDeleting}
                                    className="bg-red-500 hover:bg-red-600 text-white border-none"
                                >
                                    {isDeleting ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Deleting...
                                        </>
                                    ) : (
                                        'Delete Cohort'
                                    )}
                                </AlertDialogAction>
                            </AlertDialogFooter>
                        </AlertDialogContent>
                    </AlertDialog>

                    <Button onClick={onEditClick} variant="outline" className="text-brand-600 border-brand-200 bg-brand-50 hover:bg-brand-100">
                        <Settings className="h-4 w-4 mr-2" />
                        Edit Cohort
                    </Button>
                    <Button onClick={onAddMembersClick}>
                        <UserPlus className="h-4 w-4 mr-2" />
                        Add Members
                    </Button>
                </div>
            </div>
        </motion.div>
    );
};
