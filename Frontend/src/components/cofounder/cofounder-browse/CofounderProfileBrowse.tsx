'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Filter,
  User,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { cofounderAPI } from '@/lib/api/cofounderService';
import ProfileCard from './ProfileCard';
import ReportsDashboard from '../../admin/ReportsDashboard';

export default function CofounderProfileBrowse() {
  const [viewMode, setViewMode] = useState<'matches' | 'all' | 'reports'>('matches');
  const [profiles, setProfiles] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasAccess, setHasAccess] = useState<boolean | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const itemsPerPage = 15;

  // Filter states
  const [filters, setFilters] = useState({
    industries: [] as string[],
    location: '',
    commitment: '',
    venture_stage: [] as string[],
  });

  // Enum options from API
  const [enumOptions, setEnumOptions] = useState<{
    industries: string[];
    commitments: string[];
    ventureStages: string[];
  }>({
    industries: [],
    commitments: [],
    ventureStages: [],
  });

  useEffect(() => {
    checkAccessAndLoadProfiles();
    loadEnums();
  }, []);

  useEffect(() => {
    if (hasAccess) {
      loadProfiles();
    }
  }, [viewMode, currentPage]);

  const loadEnums = async () => {
    try {
      const [industriesRes, commitmentsRes, ventureStagesRes] = await Promise.all([
        cofounderAPI.enums.listIndustries({ pageSize: 500 }),
        cofounderAPI.enums.listCommitment({ pageSize: 100 }),
        cofounderAPI.enums.listVentureStages({ pageSize: 100 }),
      ]);

      setEnumOptions({
        industries: industriesRes.data.map((item) => item.name),
        commitments: commitmentsRes.data.map((item) => item.name),
        ventureStages: ventureStagesRes.data.map((item) => item.name),
      });
    } catch (err) {
      console.error('Failed to load enums:', err);
      setEnumOptions({
        industries: [],
        commitments: ['Full-time', 'Part-time'],
        ventureStages: ['Idea Stage', 'MVP Built', 'Launched & Growing', 'Scaling'],
      });
    }
  };

  const checkAccessAndLoadProfiles = async () => {
    try {
      setIsLoading(true);
      setError(null);
      setHasAccess(null);

      const approved = await cofounderAPI.profiles.hasApprovedProfile();
      setHasAccess(approved);

      if (!approved) {
        setError('You need an approved cofounder profile to access the directory. Please create and submit your profile for review.');
        setIsLoading(false);
        return;
      }

      await loadProfiles();
    } catch (err: any) {
      console.error('Failed to check access or load profiles:', err);
      setHasAccess(false);
      setError(err.message || 'Failed to load profiles');
    } finally {
      setIsLoading(false);
    }
  };

  const loadProfiles = async () => {
    try {
      setIsLoading(true);

      if (viewMode === 'matches') {
        const matchesData = await cofounderAPI.profiles.getMatchesByThreshold(60.0);
        console.log('Fetched matches:', matchesData);
        setProfiles(matchesData);
        setTotalCount(matchesData.length);
        setTotalPages(Math.ceil(matchesData.length / itemsPerPage));
      } else {
        const searchFilters: any = {};

        if (filters.location) searchFilters.country = filters.location;
        if (filters.commitment) searchFilters.preferred_commitment = filters.commitment;
        if (filters.industries.length > 0) searchFilters.industries = filters.industries;
        if (filters.venture_stage.length > 0) searchFilters.preferred_venture_stage = filters.venture_stage;

        const response = await cofounderAPI.profiles.searchDirectory(searchFilters, currentPage, itemsPerPage);
        console.log('Fetched profiles:', response);
        setProfiles(response.items);
        setTotalCount(response.total);
        setTotalPages(response.total_pages);
      }
    } catch (err: any) {
      console.error('Failed to load profiles:', err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const applyServerFilters = async () => {
    if (hasAccess) {
      setCurrentPage(1); // Reset to first page
      try {
        await loadProfiles();
      } catch (err: any) {
        console.error('Failed to apply filters:', err);
        setError(err.message || 'Failed to apply filters');
      }
    }
  };

  const clearFilters = () => {
    setFilters({
      industries: [],
      location: '',
      commitment: '',
      venture_stage: [],
    });
    setSearchQuery('');
    if (hasAccess) {
      loadProfiles();
    }
  };

  const handleViewModeChange = (mode: 'matches' | 'all' | 'reports') => {
    setViewMode(mode);
    setCurrentPage(1);
  };

  const paginatedProfiles = viewMode === 'matches'
    ? profiles.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)
    : profiles;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading profiles...</p>
        </div>
      </div>
    );
  }

  if (error) {
    const isAccessError = hasAccess === false;
    return (
      <div className="p-8">
        <div className={`max-w-2xl mx-auto p-6 rounded-lg border ${
          isAccessError
            ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
            : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
        }`}>
          <div className="flex items-start gap-3">
            <AlertCircle className={`w-6 h-6 flex-shrink-0 mt-0.5 ${
              isAccessError
                ? 'text-blue-600 dark:text-blue-400'
                : 'text-red-600 dark:text-red-400'
            }`} />
            <div>
              <h3 className={`text-lg font-semibold mb-2 ${
                isAccessError
                  ? 'text-blue-900 dark:text-blue-200'
                  : 'text-red-900 dark:text-red-200'
              }`}>
                {isAccessError ? 'Access Restricted' : 'Error Loading Profiles'}
              </h3>
              <p className={`mb-4 ${
                isAccessError
                  ? 'text-blue-700 dark:text-blue-300'
                  : 'text-red-700 dark:text-red-300'
              }`}>{error}</p>
              {!isAccessError && (
                <button
                  onClick={checkAccessAndLoadProfiles}
                  className="px-4 py-2 bg-red-600 dark:bg-red-500 text-white rounded-lg hover:bg-red-700 dark:hover:bg-red-600 transition-all"
                >
                  Try Again
                </button>
              )}
              {isAccessError && (
                <a
                  href="/workspace/cofounder-matching"
                  className="inline-block px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-all"
                >
                  Create Your Profile
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (viewMode === 'reports') {
    return <ReportsDashboard />;
  }
  

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      <div className="flex-none p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Find Your Cofounder
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Browse profiles of potential cofounders looking to build something amazing
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="mb-6">
          <div className="inline-flex rounded-lg bg-white dark:bg-gray-800 p-1 gap-2">
            <button
              onClick={() => handleViewModeChange('matches')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all border-2 ${
                viewMode === 'matches'
                  ? 'bg-brand-500 dark:bg-brand-400 text-white shadow-sm border-brand-600 dark:border-brand-500'
                  : 'text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white border-gray-300 dark:border-gray-600'
              }`}
            >
              Best Match Score
            </button>
            <button
              onClick={() => handleViewModeChange('all')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all border-2 ${
                viewMode === 'all'
                  ? 'bg-brand-500 dark:bg-brand-400 text-white shadow-sm border-brand-600 dark:border-brand-500'
                  : 'text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white border-gray-300 dark:border-gray-600'
              }`}
            >
              Get All
            </button>
            <button
  onClick={() => handleViewModeChange('reports')}
  className="px-4 py-2 rounded-md text-sm font-medium transition-all border-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white border-gray-300 dark:border-gray-600"
>
  Admin Reports
</button>
          </div>
        </div>

        {/* Search and Filter Bar */}
        <div className="mb-6 flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name, background, or industry..."
              className="w-full pl-10 pr-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
            />
          </div>

          {/* Filter Button */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 px-6 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-all"
          >
            <Filter className="w-5 h-5" />
            Filters
            {(filters.industries.length > 0 ||
              filters.location ||
              filters.commitment) && (
              <span className="ml-1 px-2 py-0.5 bg-brand-500 dark:bg-brand-400 text-white text-xs rounded-full">
                {filters.industries.length +
                  (filters.location ? 1 : 0) +
                  (filters.commitment ? 1 : 0)}
              </span>
            )}
          </button>
        </div>

        {/* Filter Panel */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-6 overflow-hidden"
            >
              <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Filters
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={clearFilters}
                      className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                    >
                      Clear All
                    </button>
                    <button
                      onClick={applyServerFilters}
                      className="px-3 py-1 text-sm bg-brand-500 dark:bg-brand-400 text-white rounded hover:bg-brand-600 dark:hover:bg-brand-500 transition-all"
                    >
                      Apply Filters
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Location Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Location
                    </label>
                    <input
                      type="text"
                      value={filters.location}
                      onChange={(e) =>
                        setFilters({ ...filters, location: e.target.value })
                      }
                      placeholder="e.g., United States"
                      className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
                    />
                  </div>

                  {/* Commitment Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Commitment
                    </label>
                    <select
                      value={filters.commitment}
                      onChange={(e) =>
                        setFilters({ ...filters, commitment: e.target.value })
                      }
                      className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
                    >
                      <option value="">All</option>
                      {enumOptions.commitments.map((commitment) => (
                        <option key={commitment} value={commitment}>
                          {commitment}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Industry Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Industries
                    </label>
                    <select
                      multiple
                      value={filters.industries}
                      onChange={(e) => {
                        const selected = Array.from(e.target.selectedOptions, (option) => option.value);
                        setFilters({ ...filters, industries: selected });
                      }}
                      className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent"
                      size={4}
                    >
                      {enumOptions.industries.slice(0, 20).map((industry) => (
                        <option key={industry} value={industry}>
                          {industry}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple</p>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results Count */}
        <div className="mb-4 text-sm text-gray-600 dark:text-gray-400">
          {viewMode === 'matches'
            ? `Showing ${(currentPage - 1) * itemsPerPage + 1}-${Math.min(currentPage * itemsPerPage, totalCount)} of ${totalCount} matches (60%+ score)`
            : `Showing ${(currentPage - 1) * itemsPerPage + 1}-${Math.min(currentPage * itemsPerPage, totalCount)} of ${totalCount} profiles`}
        </div>
      </div>

      {/* Scrollable Profile Grid */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto pb-6">
          {profiles.length === 0 ? (
            <div className="text-center py-12">
              <User className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                No Profiles Found
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                {viewMode === 'matches'
                  ? 'No matches found with 60%+ score. Try "Get All" mode to see all profiles.'
                  : 'Try adjusting your filters or search query'}
              </p>
              <button
                onClick={clearFilters}
                className="px-4 py-2 bg-brand-500 dark:bg-brand-400 text-white rounded-lg hover:bg-brand-600 dark:hover:bg-brand-500 transition-all"
              >
                Clear Filters
              </button>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {paginatedProfiles.map((item, index) => {
                  // Extract profile from match object or use directly
                  const profile = viewMode === 'matches' ? item : item;
                  const matchScore = viewMode === 'matches' ? item.score : null;

                  return (
                    <motion.div
                      key={profile.candidate_profile_id || profile.profile_id || profile.id || `profile-${index}`}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      whileHover={{ y: -4 }}
                      className=" transition-all"
                    >
                      <ProfileCard profile={profile} matchScore={matchScore} />
                    </motion.div>
                  );
                })}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-8 flex items-center justify-between bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 px-6 py-4">
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Page {currentPage} of {totalPages}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                      disabled={currentPage === 1}
                      className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      Previous
                    </button>
                    <div className="flex items-center gap-2">
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum;
                        if (totalPages <= 5) {
                          pageNum = i + 1;
                        } else if (currentPage <= 3) {
                          pageNum = i + 1;
                        } else if (currentPage >= totalPages - 2) {
                          pageNum = totalPages - 4 + i;
                        } else {
                          pageNum = currentPage - 2 + i;
                        }
                        return (
                          <button
                            key={pageNum}
                            onClick={() => setCurrentPage(pageNum)}
                            className={`px-3 py-2 text-sm font-medium rounded-lg transition-all ${
                              currentPage === pageNum
                                ? 'bg-brand-500 dark:bg-brand-400 text-white'
                                : 'text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                            }`}
                          >
                            {pageNum}
                          </button>
                        );
                      })}
                    </div>
                    <button
                      onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                      disabled={currentPage === totalPages}
                      className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
