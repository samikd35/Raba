'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Loader2,
  AlertCircle,
  Heart,
  User,
  Puzzle,
  X,
} from 'lucide-react';
import { cofounderAPI } from '@/lib/api/cofounderService';
import ProfileCard from './ProfileCard';
import ProfileDetailModal from './ProfileDetailModal';

export default function CofounderMatches() {
  const [profiles, setProfiles] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasAccess, setHasAccess] = useState<boolean | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const itemsPerPage = 15;

  useEffect(() => {
    checkAccessAndLoadMatches();
  }, []);

  useEffect(() => {
    if (hasAccess && profiles.length > 0) {
      setTotalPages(Math.ceil(profiles.length / itemsPerPage));
    }
  }, [profiles, hasAccess]);

  const checkAccessAndLoadMatches = async () => {
    try {
      setIsLoading(true);
      setError(null);
      setHasAccess(null);

      const approved = await cofounderAPI.profiles.hasApprovedProfile();
      setHasAccess(approved);

      if (!approved) {
        setError('You need an approved cofounder profile to see matches. Please create and submit your profile for review.');
        setIsLoading(false);
        return;
      }

      await loadMatches();
    } catch (err: any) {
      console.error('Failed to check access or load matches:', err);
      setHasAccess(false);
      setError(err.message || 'Failed to load matches');
    } finally {
      setIsLoading(false);
    }
  };

  const loadMatches = async () => {
    try {
      setIsLoading(true);
      const matchesData = await cofounderAPI.profiles.getMatchesByThreshold(40.0);
      console.log('[CofounderMatches] Fetched raw matches:', matchesData);

      const profilesWithUserId = matchesData.map((match: any) => {
        const versionId = match.version_id || match.candidate_version_id;

        console.log('=== COFOUNDER MATCH ===', match);

        return {
          ...match,
          user_id: match.user_id, // Use user_id directly from match data
          profile_id: match.candidate_profile_id,
          version_id: versionId,
          profile_picture_url: match.profile_picture_url,
          full_name: match.full_name,
          country: match.profile_country,
          // Add these for compatibility
          first_name: match.full_name?.split(' ')[0] || '',
          last_name: match.full_name?.split(' ').slice(1).join(' ') || '',
        };
      });

      console.log('[CofounderMatches] Transformed profiles with user_ids:', profilesWithUserId);

      setProfiles(profilesWithUserId);
      setTotalCount(profilesWithUserId.length);
      setTotalPages(Math.ceil(profilesWithUserId.length / itemsPerPage));
    } catch (err: any) {
      console.error('Failed to load matches:', err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const paginatedProfiles = profiles.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Finding your matches...</p>
        </div>
      </div>
    );
  }

  if (error) {
    const isAccessError = hasAccess === false;

    if (isAccessError) {
      return (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-16 text-center px-4"
        >
          <div className="relative mb-8">
            <div className="p-6 rounded-full bg-gradient-to-br from-brand-100 to-blue-100 dark:from-brand-900/30 dark:to-blue-900/30 border dark:border-brand-700/30">
              <Puzzle
               className="w-16 h-16 text-brand-600 dark:text-brand-400" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">Start Matching with Cofounders</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md leading-relaxed">
            Create your cofounder profile to discover and connect with potential cofounders who match your vision, skills, and commitment.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <button
              onClick={() => window.location.href = '/workspace/cofounder-matching'}
              className="inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-brand-600 to-brand-700 hover:from-brand-700 hover:to-brand-800 dark:from-brand-500 dark:to-brand-600 dark:hover:from-brand-600 dark:hover:to-brand-700 text-white rounded-lg shadow-lg hover:shadow-xl transition-all"
            >
              <User className="w-4 h-4 mr-2" />
              Create Your Profile
            </button>
          </div>
        </motion.div>
      );
    }

    // Error state for other errors
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center justify-center py-16 text-center px-4"
      >
        <div className="p-4 rounded-full bg-red-100 dark:bg-red-900/30 mb-6">
          <AlertCircle className="w-12 h-12 text-red-600 dark:text-red-400" />
        </div>
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">Failed to Load Matches</h3>
        <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md leading-relaxed">{error}</p>
        <button
          onClick={checkAccessAndLoadMatches}
          className="inline-flex items-center px-6 py-3 bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600 text-white rounded-lg transition-all"
        >
          <X className="w-4 h-4 mr-2 rotate-45" />
          Try Again
        </button>
      </motion.div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      <div className="flex-none p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <Puzzle className="w-8 h-8 text-brand-500 dark:text-brand-400" />
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Your Matches
            </h1>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            These are Cofounders with compatibility score based on your profile
          </p>
        </div>

        {/* Results Count */}
        <div className="mb-4 text-sm text-gray-600 dark:text-gray-400">
          Showing {(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, totalCount)} of {totalCount} matches
        </div>
      </div>

      {/* Scrollable Profile Grid */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto pb-6">
          {profiles.length === 0 ? (
            <div className="text-center py-12">
              <Puzzle className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                No Matches Found
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                We couldn't find any matching cofounders. Try browsing all profiles or update your preferences.
              </p>
              <a
                href="/workspace/cofounder-matching/browse"
                className="inline-block px-4 py-2 bg-brand-500 dark:bg-brand-400 text-white rounded-lg hover:bg-brand-600 dark:hover:bg-brand-500 transition-all"
              >
                Browse All Profiles
              </a>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {paginatedProfiles.map((match, index) => (
                  <motion.div
                    key={match.candidate_profile_id || `match-${index}`}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    whileHover={{ y: -4 }}
                    onClick={() => {
                      setSelectedVersionId(match.version_id || match.candidate_version_id);
                      setSelectedUserId(match.user_id || match.candidate_profile_id);
                    }}
                    className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg transition-all cursor-pointer"
                  >
                    <ProfileCard profile={match} matchScore={match.score} />
                  </motion.div>
                ))}
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

      {/* Profile Detail Modal */}
      {selectedVersionId && (
        <ProfileDetailModal
          versionId={selectedVersionId}
          userId={selectedUserId || undefined}
          onClose={() => {
            setSelectedVersionId(null);
            setSelectedUserId(null);
          }}
        />
      )}
    </div>
  );
}
