'use client';

import { Search, X } from 'lucide-react';

interface FilterPanelProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  expertiseAreas: any[];
  selectedExpertise: string[];
  onToggleExpertise: (id: string) => void;
  onClearAll: () => void;
  hasActiveFilters: boolean;
}

export default function FilterPanel({
  searchQuery,
  onSearchChange,
  expertiseAreas,
  selectedExpertise,
  onToggleExpertise,
  onClearAll,
  hasActiveFilters,
}: FilterPanelProps) {
  return (
    <div className="space-y-6">
      {/* Header with Clear All */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Filters
        </h3>
        {hasActiveFilters && (
          <button
            onClick={onClearAll}
            className="text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 font-medium flex items-center gap-1"
          >
            <X className="w-4 h-4" />
            Clear all
          </button>
        )}
      </div>

      {/* Search */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Search
        </label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search by name, expertise..."
            className="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
          />
        </div>
      </div>

      {/* Expertise Multi-Select */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Expertise Areas
        </label>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {expertiseAreas.map((area) => (
            <label
              key={area.id}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
            >
              <input
                type="checkbox"
                checked={selectedExpertise.includes(area.id)}
                onChange={() => onToggleExpertise(area.id)}
                className="w-4 h-4 text-brand-500 dark:text-brand-400 rounded border-gray-300 dark:border-gray-600 focus:ring-brand-500 dark:focus:ring-brand-400"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {area.name}
              </span>
            </label>
          ))}
          {expertiseAreas.length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
              No expertise areas available
            </p>
          )}
        </div>
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Active Filters
          </p>
          <div className="flex flex-wrap gap-2">
            {searchQuery && (
              <span className="inline-flex items-center gap-1 px-3 py-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-full text-xs font-medium">
                Search: {searchQuery}
                <button
                  onClick={() => onSearchChange('')}
                  className="hover:text-brand-900 dark:hover:text-brand-100"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {selectedExpertise.length > 0 && (
              <span className="inline-flex items-center gap-1 px-3 py-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-full text-xs font-medium">
                {selectedExpertise.length} expertise{selectedExpertise.length > 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
