import React from 'react';
import { Search, SortAsc, SortDesc, RefreshCw, Plus } from 'lucide-react';
import { Input } from "@/components/ui/input";
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export type SortOption = 'name' | 'created_at' | 'updated_at';
export type SortDirection = 'asc' | 'desc';
export type StatusFilter = 'all' | 'active' | 'inactive';

export interface FilterState {
    search: string;
    sortBy: SortOption;
    sortDirection: SortDirection;
}

interface CohortsFiltersProps {
    filters: FilterState;
    setFilters: React.Dispatch<React.SetStateAction<FilterState>>;
    onRefresh: () => void;
    onAddClick: () => void;
}

export const CohortsFilters = ({
    filters,
    setFilters,
    onRefresh,
    onAddClick
}: CohortsFiltersProps) => {
    return (
        <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                    placeholder="Search cohorts..."
                    value={filters.search}
                    onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                    className="pl-10 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
                />
            </div>


            <Button onClick={onAddClick}>
                <Plus className="h-4 w-4 mr-1" />
                Add Cohort
            </Button>

            <Button
                variant="outline"
                size="icon"
                onClick={() => setFilters(prev => ({
                    ...prev,
                    sortDirection: prev.sortDirection === 'asc' ? 'desc' : 'asc'
                }))}
                className="dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            >
                {filters.sortDirection === 'asc' ? (
                    <SortAsc className="h-4 w-4" />
                ) : (
                    <SortDesc className="h-4 w-4" />
                )}
            </Button>

            <Button
                onClick={onRefresh}
                variant="outline"
                className="dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
            </Button>
        </div>
    );
};
