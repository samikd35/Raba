import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from '@/components/ui/button';
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Calculator, CreditCard, ArrowRight, Pencil } from 'lucide-react';
import { toast } from "react-hot-toast";

interface CreditCalculatorModalProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    tenantId: string;
    token: string;
}

interface CalculationResult {
    tenant_id: string;
    member_count: number;
    credits_per_member: number;
    member_credits_total: number;
    admin_seats_count: number;
    admin_seat_price_credits: number;
    admin_seats_total: number;
    total_credits: number;
    total_amount: number;
    currency: string;
}

export const CreditCalculatorModal = ({
    isOpen,
    onOpenChange,
    tenantId,
    token,
}: CreditCalculatorModalProps) => {
    const [isLoading, setIsLoading] = useState(false);
    const [memberCount, setMemberCount] = useState<number>(10);
    const [calculation, setCalculation] = useState<CalculationResult | null>(null);
    const [editedTotalCredits, setEditedTotalCredits] = useState<number | null>(null);

    // Reset state when modal opens
    useEffect(() => {
        if (isOpen) {
            setCalculation(null);
            setEditedTotalCredits(null);
            setMemberCount(10);
        }
    }, [isOpen]);

    const handleCalculate = async () => {
        if (!tenantId || !token) return;

        setIsLoading(true);
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/billing/${tenantId}/calculate-credits`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    member_count: memberCount,
                    currency: "USD"
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || 'Failed to calculate credits');
            }

            const data = await response.json();
            setCalculation(data);
            setEditedTotalCredits(data.total_credits);
        } catch (err: any) {
            toast.error(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const handlePurchase = () => {
        toast.success("Proceeding to purchase... (Not implemented yet)");
        onOpenChange(false);
    };

    const displayedCredits = editedTotalCredits !== null ? editedTotalCredits : (calculation?.total_credits || 0);

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader className="bg-brand-25 border-b border-brand-100 p-5 -mx-6 -mt-6 rounded-t-lg">
                    <DialogTitle className="flex items-center gap-2 text-brand-500">
                        <Calculator className="h-5 w-5" />
                        Credit Calculator
                    </DialogTitle>
                    <DialogDescription className="text-brand-500/80">
                        Calculate the credits required based on your member count.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    <div className="grid gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="member_count" className="text-brand-700 font-medium">Number of Members</Label>
                            <div className="flex gap-2">
                                <Input
                                    id="member_count"
                                    type="number"
                                    min={1}
                                    value={memberCount}
                                    onChange={(e) => setMemberCount(parseInt(e.target.value) || 0)}
                                    className="font-medium"
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                            handleCalculate();
                                        }
                                    }}
                                />
                                <Button
                                    type="button"
                                    onClick={handleCalculate}
                                    disabled={isLoading}
                                    className="bg-brand-600 text-white"
                                >
                                    {isLoading && !calculation ? <Loader2 className="h-4 w-4 animate-spin" /> : "Calculate"}
                                </Button>
                            </div>
                            <p className="text-xs text-gray-500">
                                Enter the number of members to calculate required credits.
                            </p>
                        </div>

                        {calculation && (
                            <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-4 space-y-3 border border-slate-100 dark:border-slate-800 animate-in fade-in slide-in-from-top-2 duration-300">
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-600 dark:text-gray-400">Credits per member:</span>
                                    <span className="font-mono font-medium">{calculation.credits_per_member}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-600 dark:text-gray-400">Member credits subtotal:</span>
                                    <span className="font-mono font-medium">{calculation.member_credits_total}</span>
                                </div>
                                {calculation.admin_seats_count > 0 && (
                                    <>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600 dark:text-gray-400">Admin seats ({calculation.admin_seats_count}):</span>
                                            <span className="font-mono font-medium">{calculation.admin_seats_total}</span>
                                        </div>
                                    </>
                                )}
                                <div className="h-px bg-slate-200 dark:bg-slate-700 my-2" />
                                <div className="flex justify-between items-center">
                                    <span className="text-gray-900 dark:text-gray-100 font-semibold">Total Credits Needed</span>
                                    <div className="flex items-center gap-2 relative group">
                                        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 group-hover:text-brand-500 transition-colors pointer-events-none">
                                            <Pencil className="h-3.5 w-3.5" />
                                        </div>
                                        <Input
                                            type="number"
                                            className="w-40 text-right h-9 font-bold text-brand-600 pl-9 border-brand-200 focus:border-brand-500 focus:ring-brand-200 bg-white"
                                            value={displayedCredits}
                                            onChange={(e) => setEditedTotalCredits(parseInt(e.target.value) || 0)}
                                        />
                                    </div>
                                </div>

                                <div className="flex justify-between items-center pt-2 border-t border-slate-200 dark:border-slate-700 mt-2 text-brand-600">
                                    <span className="font-medium">Estimated Cost</span>
                                    <span className="text-sm font-bold">
                                        {new Intl.NumberFormat('en-US', { style: 'currency', currency: calculation.currency }).format(calculation.total_amount)}
                                    </span>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <DialogFooter className="gap-2 sm:gap-0 border-t border-brand-100 px-6 py-4 -mx-6 -mb-6 mt-4 bg-gray-50/50 rounded-b-lg flex-row-reverse">
                    {calculation && (
                        <Button
                            type="button"
                            onClick={handlePurchase}
                            disabled={isLoading}
                            className="bg-brand-600 hover:bg-brand-700 text-white animate-in zoom-in duration-300 ml-2"
                        >
                            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CreditCard className="mr-2 h-4 w-4" />}
                            Purchase Credits
                        </Button>
                    )}
                    <Button className='ml-2' type="button" variant="outline" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
