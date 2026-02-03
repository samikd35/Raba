'use client';

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { User, Loader2, Search, Filter, X, ChevronDown, Info } from 'lucide-react';
import { VBProfile } from '@/types/ventureBuilder';
import { fetchVentureBuilders, fetchExpertiseAreas } from '@/lib/api/venture-builder';
import { useAuthStore } from '@/stores/authStore';
import VentureBuilderCard from './VentureBuilderCard';
import VentureBuilderProfileModal from './VentureBuilderProfileModal';
import FilterPanel from './FilterPanel';
import { toast } from 'react-hot-toast';

export default function VentureBuilderDashboard() {
  const { user, token } = useAuthStore();
  const [builders, setBuilders] = useState<VBProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedBuilder, setSelectedBuilder] = useState<VBProfile | null>(null);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<VBProfile | null>(null);

  // Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedExpertise, setSelectedExpertise] = useState<string[]>([]);
  const [expertiseAreas, setExpertiseAreas] = useState<any[]>([]);
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);

  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const pageSize = 20;

  // Debounce search
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 500);

    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Load expertise areas
  useEffect(() => {
    const loadExpertise = async () => {
      try {
        const areas = await fetchExpertiseAreas();
        setExpertiseAreas(areas);
      } catch (error) {
        console.error('Error fetching expertise areas:', error);
      }
    };
    loadExpertise();
  }, []);

  // Load venture builders with filters
  useEffect(() => {
    const loadVentureBuilders = async () => {
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        const response = await fetchVentureBuilders({
          page: currentPage,
          page_size: pageSize,
          token: token,
          search_query: debouncedSearch || undefined,
          expertise_ids: selectedExpertise.length > 0 ? selectedExpertise : undefined,
        });
        setBuilders(response.items);
        setTotalItems(response.total);
        setTotalPages(Math.ceil(response.total / response.page_size));
      } catch (error: any) {
        console.error('Error fetching venture builders:', error);
        toast.error('Failed to load venture builders');
        setBuilders([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadVentureBuilders();
  }, [currentPage, token, debouncedSearch, selectedExpertise]);

  const validatedBuilders = useMemo(() => {
    const filtered = builders.filter(builder => {
      const hasId = !!builder?.id;
      const hasName = !!(builder?.full_name || (builder as any)?.name);
      const hasBiography = !!builder?.biography;
      const isActive = builder?.is_active !== false;

      console.log('VB Dashboard - Validating builder:', {
        id: builder?.id,
        name: builder?.full_name || (builder as any)?.name,
        hasId,
        hasName,
        hasBiography,
        isActive,
        passes: hasId && hasName && hasBiography && isActive
      });

      return hasId && hasName && hasBiography && isActive;
    });

    console.log('VB Dashboard - Filtered builders count:', filtered.length);
    return filtered;
  }, [builders]);

  const handleSelectBuilder = useCallback((builder: VBProfile) => {
    setSelectedBuilder(current =>
      current?.id === builder.id ? null : builder
    );
  }, []);

  const handleViewProfile = useCallback((builder: VBProfile) => {
    setSelectedProfile(builder);
    setIsProfileModalOpen(true);
  }, []);

  const closeProfileModal = useCallback(() => {
    setIsProfileModalOpen(false);
    setSelectedProfile(null);
  }, []);

  const handleToggleExpertise = useCallback((expertiseId: string) => {
    setSelectedExpertise(prev =>
      prev.includes(expertiseId)
        ? prev.filter(id => id !== expertiseId)
        : [...prev, expertiseId]
    );
    setCurrentPage(1); // Reset to first page when filtering
  }, []);

  const handleClearFilters = useCallback(() => {
    setSearchQuery('');
    setDebouncedSearch('');
    setSelectedExpertise([]);
    setCurrentPage(1);
  }, []);

  const hasActiveFilters = searchQuery.length > 0 || selectedExpertise.length > 0;

  if (isLoading) {
    return (
      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-gray-900/50 xl:px-10">
        <div className="max-w-7xl mx-auto">
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-brand-100 dark:bg-brand-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
              <Loader2 className="w-8 h-8 text-brand-500 dark:text-brand-400 animate-spin" />
            </div>
            <p className="text-brand-600 dark:text-brand-400">Loading venture builders...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900/50">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="px-4 py-6 xl:px-10 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Browse Venture Builders</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Connect with expert venture builders to help grow your business
              </p>
            </div>

            {/* Mobile Filter Toggle */}
            <button
              onClick={() => setIsMobileFilterOpen(true)}
              className="lg:hidden flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <Filter className="w-4 h-4" />
              Filters
              {hasActiveFilters && (
                <span className="w-2 h-2 bg-brand-500 rounded-full" />
              )}
            </button>
          </div>

          {/* Credibility Badge */}
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-blue-800 dark:text-blue-300">
                <strong>How Credits Work:</strong> Each venture builder sets their own credit price per hour.
                Credits are deducted from your workspace balance when you book a session.
                Sessions are 60 minutes long by default.
              </p>
            </div>
          </div>
        </div>

        {/* Main Content Area with Filter Dropdown */}
        <div className="px-4 py-6 xl:px-10">
          {/* Filter Button and Dropdown */}
          <div className="mb-6 relative">
            <div className="flex items-center gap-4">
              {/* Desktop Filter Dropdown */}
              <div className="relative">
                <button
                  onClick={() => setIsMobileFilterOpen(!isMobileFilterOpen)}
                  className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <Filter className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Filters
                  </span>
                  {hasActiveFilters && (
                    <span className="w-2 h-2 bg-brand-500 rounded-full"></span>
                  )}
                  <ChevronDown className={`w-4 h-4 text-gray-500 dark:text-gray-400 transition-transform ${isMobileFilterOpen ? 'rotate-180' : ''}`} />
                </button>

                {/* Dropdown Panel */}
                {isMobileFilterOpen && (
                  <>
                    {/* Backdrop */}
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setIsMobileFilterOpen(false)}
                    />
                    {/* Filter Panel Dropdown */}
                    <div className="absolute left-0 top-full mt-2 w-96 max-w-[calc(100vw-2rem)] bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl z-50 max-h-[70vh] overflow-y-auto">
                      <div className="p-6">
                        <FilterPanel
                          searchQuery={searchQuery}
                          onSearchChange={setSearchQuery}
                          expertiseAreas={expertiseAreas}
                          selectedExpertise={selectedExpertise}
                          onToggleExpertise={handleToggleExpertise}
                          onClearAll={handleClearFilters}
                          hasActiveFilters={hasActiveFilters}
                        />
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Active Filters Display */}
              {hasActiveFilters && (
                <div className="flex items-center gap-2 flex-wrap">
                  {searchQuery && (
                    <span className="inline-flex items-center gap-1 px-3 py-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-full text-xs font-medium">
                      Search: {searchQuery}
                      <button
                        onClick={() => setSearchQuery('')}
                        className="hover:text-brand-900 dark:hover:text-brand-100"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {selectedExpertise.length > 0 && (
                    <span className="inline-flex items-center gap-1 px-3 py-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-full text-xs font-medium">
                      {selectedExpertise.length} expertise area{selectedExpertise.length > 1 ? 's' : ''}
                      <button
                        onClick={() => setSelectedExpertise([])}
                        className="hover:text-brand-900 dark:hover:text-brand-100"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Main Content Grid */}
          <div className="w-full">
            {/* Venture Builders Grid */}
            {validatedBuilders.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {validatedBuilders.map((builder, index) => (
                  <VentureBuilderCard
                    key={builder.id}
                    builder={builder}
                    isSelected={selectedBuilder?.id === builder.id}
                    onSelect={handleSelectBuilder}
                    onViewProfile={handleViewProfile}
                    index={index}
                  />
                ))}
              </div>
            ) : (
              /* Empty States */
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-brand-100 dark:bg-brand-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                  {hasActiveFilters ? (
                    <Search className="w-8 h-8 text-brand-500 dark:text-brand-400" />
                  ) : (
                    <User className="w-8 h-8 text-brand-500 dark:text-brand-400" />
                  )}
                </div>
                <h3 className="text-lg font-semibold text-brand-700 dark:text-brand-300 mb-2">
                  {hasActiveFilters
                    ? 'No Matching Venture Builders'
                    : 'No Active Venture Builders'}
                </h3>
                <p className="text-brand-600 dark:text-brand-400 mb-4">
                  {hasActiveFilters
                    ? 'Try adjusting your filters to see more results.'
                    : 'Our expert venture builders will be available soon. Check back later!'}
                </p>
                {hasActiveFilters && (
                  <button
                    onClick={handleClearFilters}
                    className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Clear Filters
                  </button>
                )}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && validatedBuilders.length > 0 && (
              <div className="mt-8 flex items-center justify-between border-t border-gray-200 dark:border-gray-700 pt-6">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalItems)} of {totalItems} venture builders
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <div className="flex gap-1">
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter(page => {
                    // Show first page, last page, current page, and pages around current
                    return (
                      page === 1 ||
                      page === totalPages ||
                      Math.abs(page - currentPage) <= 1
                    );
                  })
                  .map((page, index, array) => {
                    // Add ellipsis if there's a gap
                    const prevPage = array[index - 1];
                    const showEllipsis = prevPage && page - prevPage > 1;

                    return (
                      <React.Fragment key={page}>
                        {showEllipsis && (
                          <span className="px-3 py-2 text-gray-500 dark:text-gray-400">...</span>
                        )}
                        <button
                          onClick={() => setCurrentPage(page)}
                          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                            currentPage === page
                              ? 'bg-brand-500 text-white'
                              : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                          }`}
                        >
                          {page}
                        </button>
                      </React.Fragment>
                    );
                  })}
              </div>
              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
            )}
          </div>
        </div>

        {/* Mobile Filter Drawer */}
        {isMobileFilterOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setIsMobileFilterOpen(false)}
            />

            {/* Drawer */}
            <div className="absolute right-0 top-0 h-full w-full max-w-sm bg-white dark:bg-gray-900 shadow-2xl overflow-y-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Filters
                  </h3>
                  <button
                    onClick={() => setIsMobileFilterOpen(false)}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                  >
                    <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  </button>
                </div>

                <FilterPanel
                  searchQuery={searchQuery}
                  onSearchChange={setSearchQuery}
                  expertiseAreas={expertiseAreas}
                  selectedExpertise={selectedExpertise}
                  onToggleExpertise={handleToggleExpertise}
                  onClearAll={handleClearFilters}
                  hasActiveFilters={hasActiveFilters}
                />

                <button
                  onClick={() => setIsMobileFilterOpen(false)}
                  className="w-full mt-6 px-4 py-3 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Apply Filters
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Profile Modal */}
      <VentureBuilderProfileModal
        isOpen={isProfileModalOpen}
        profile={selectedProfile}
        onClose={closeProfileModal}
      />
    </div>
  );
}
