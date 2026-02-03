import React, { useCallback } from 'react';
import { Search, SortAsc, SortDesc } from 'lucide-react';
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from '@/components/ui/button';
import { SortField, SortOrder, StatusFilter } from './types';

interface ProjectsFiltersProps {
    searchQuery: string;
    onSearchChange: (value: string) => void;
    sortField: SortField;
    onSortFieldChange: (value: SortField) => void;
    sortOrder: SortOrder;
    onSortOrderToggle: () => void;
    statusFilter: StatusFilter;
    onStatusFilterChange: (value: StatusFilter) => void;
}

/**
 * Filters and search component for projects
 */
export const ProjectsAmrgFilters = React.memo(({
    searchQuery,
    onSearchChange,
    sortField,
    onSortFieldChange,
    sortOrder,
    onSortOrderToggle,
    statusFilter,
    onStatusFilterChange,
}: ProjectsFiltersProps) => {
    const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        onSearchChange(e.target.value);
    }, [onSearchChange]);

    return (
        <div className="flex flex-col sm:flex-row gap-4 ">
            {/* Search */}
            <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-gray-500" />
                <Input
                    type="text"
                    placeholder="Search projects..."
                    value={searchQuery}
                    onChange={handleSearchChange}
                    className="pl-10 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 focus:border-brand-500 dark:focus:border-brand-500"
                />
            </div>

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={onStatusFilterChange}>
                <SelectTrigger className="w-full sm:w-[180px] bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600">
                    <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
            </Select>

            {/* Sort Field */}
            <Select value={sortField} onValueChange={onSortFieldChange}>
                <SelectTrigger className="w-full sm:w-[180px] bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600">
                    <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="name">Name</SelectItem>
                    <SelectItem value="created_at">Created Date</SelectItem>
                    <SelectItem value="updated_at">Updated Date</SelectItem>
                </SelectContent>
            </Select>

            {/* Sort Order Toggle */}
            <Button
                onClick={onSortOrderToggle}
                variant="outline"
                size="icon"
                className="border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700"
                title={sortOrder === 'asc' ? 'Sort Ascending' : 'Sort Descending'}
            >
                {sortOrder === 'asc' ? (
                    <SortAsc className="h-4 w-4" />
                ) : (
                    <SortDesc className="h-4 w-4" />
                )}
            </Button>
        </div>
    );
});

ProjectsAmrgFilters.displayName = 'ProjectsAmrgFilters';
