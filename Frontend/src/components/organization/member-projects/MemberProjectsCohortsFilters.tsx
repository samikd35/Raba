import React from 'react';
import { Search, SortAsc, SortDesc, RefreshCw } from 'lucide-react';
import { Input } from "@/components/ui/input";
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export type SortOption = 'name' | 'created_at' | 'updated_at';
export type SortDirection = 'asc' | 'desc';

export interface FilterState {
    search: string;
    sortBy: SortOption;
    sortDirection: SortDirection;
}

interface MemberProjectsCohortsFiltersProps {
    filters: FilterState;
    setFilters: React.Dispatch<React.SetStateAction<FilterState>>;
    onRefresh: () => void;
}

export function MemberProjectsCohortsFilters({ filters, setFilters, onRefresh }: MemberProjectsCohortsFiltersProps) {
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

            <Select
                value={filters.sortBy}
                onValueChange={(value: SortOption) => setFilters(prev => ({ ...prev, sortBy: value }))}
            >
                <SelectTrigger className="w-full sm:w-40 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100">
                    <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="name">Name</SelectItem>
                    <SelectItem value="created_at">Created Date</SelectItem>
                    <SelectItem value="updated_at">Updated Date</SelectItem>
                </SelectContent>
            </Select>

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
                size="icon"
                className="dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            >
                <RefreshCw className="h-4 w-4" />
            </Button>
        </div>
    );
}
