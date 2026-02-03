"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { toast } from "react-hot-toast";
import { Plus, Search, Filter, Building2, Eye, Coins, Pause, X, ChevronLeft, ChevronRight } from 'lucide-react';

interface Organization {
  id: string;
  name: string;
  country: string;
  city: string;
  contact_email: string;
  phone_number: string;
  type?: 'prepay_org' | 'grant_org';
  monthly_credit_limit?: number;
  created_at: string;
  updated_at: string;
  status: 'active' | 'suspended' | 'frozen';
}

const PAGE_SIZE = 12; // 4 rows of 3 cards

export default function OrganizationsPage() {
  const router = useRouter();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<{
    total_organizations: number;
    active_organizations: number;
    inactive_organizations: number;
    total_members: number;
    total_teams: number;
    total_credits_allocated: number;
    total_credits_used: number;
  } | null>(null);

  // Search and Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'prepay_org' | 'grant_org'>('all');
  const [countryFilter, setCountryFilter] = useState<string>('all');
  
  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);

  // Grant Credits Modal State
  const [grantModalOpen, setGrantModalOpen] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [creditAmount, setCreditAmount] = useState<string>('');
  const [granting, setGranting] = useState(false);

  useEffect(() => {
    fetchOrganizations();
    fetchSummary();
  }, []);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, typeFilter, countryFilter]);

  const fetchOrganizations = async () => {
    try {
      setLoading(true);
      // Request larger page size to get all organizations (backend max is 100)
      const organizations = await organizationService.fetchOrganizations({ page_size: 100 });
      setOrganizations(organizations);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch organizations');
      toast.error(err.message || 'Failed to fetch organizations');
    } finally {
      setLoading(false);
    }
  };

  // Get unique countries for filter dropdown
  const uniqueCountries = useMemo(() => {
    const countries = new Set(organizations.map(org => org.country).filter(Boolean));
    return Array.from(countries).sort();
  }, [organizations]);

  // Filter and search organizations
  const filteredOrganizations = useMemo(() => {
    return organizations.filter(org => {
      // Search filter
      const searchLower = searchQuery.toLowerCase();
      const matchesSearch = !searchQuery || 
        org.name?.toLowerCase().includes(searchLower) ||
        org.city?.toLowerCase().includes(searchLower) ||
        org.country?.toLowerCase().includes(searchLower) ||
        org.contact_email?.toLowerCase().includes(searchLower);

      // Type filter
      const matchesType = typeFilter === 'all' || org.type === typeFilter;

      // Country filter
      const matchesCountry = countryFilter === 'all' || org.country === countryFilter;

      return matchesSearch && matchesType && matchesCountry;
    });
  }, [organizations, searchQuery, typeFilter, countryFilter]);

  // Pagination calculations
  const totalPages = Math.ceil(filteredOrganizations.length / PAGE_SIZE);
  const paginatedOrganizations = useMemo(() => {
    const startIndex = (currentPage - 1) * PAGE_SIZE;
    return filteredOrganizations.slice(startIndex, startIndex + PAGE_SIZE);
  }, [filteredOrganizations, currentPage]);

  const goToPage = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  };

  const fetchSummary = async () => {
    try {
      const summaryData = await organizationService.getOrganizationSummary();
      setSummary(summaryData);
    } catch (err: any) {
      console.error('Failed to fetch organization summary:', err);
    }
  };

  const handleInviteOrganization = () => {
    router.push('/admin/organizations/invite');
  };

  const openGrantModal = (org: Organization) => {
    console.log('[Organizations] Opening grant modal for org:', { id: org.id, name: org.name });
    setSelectedOrg(org);
    setCreditAmount('');
    setGrantModalOpen(true);
  };

  const closeGrantModal = () => {
    setGrantModalOpen(false);
    setSelectedOrg(null);
    setCreditAmount('');
  };

  const handleGrantCredits = async () => {
    if (!selectedOrg || !creditAmount) return;

    const amount = parseInt(creditAmount, 10);
    if (isNaN(amount) || amount < 1) {
      toast.error('Please enter a valid credit amount (minimum 1)');
      return;
    }

    try {
      setGranting(true);
      const result = await organizationService.grantCreditsToOrganization(
        selectedOrg.id,
        amount
      );
      
      // Show success message with email notification status
      let successMessage = `Successfully granted ${amount} credits to ${selectedOrg.name}`;
      if (result.email_sent) {
        successMessage += ` - Notification sent to ${result.email_recipient}`;
      } else if (result.email_recipient) {
        successMessage += ` - Email notification failed`;
      }
      toast.success(successMessage);
      
      closeGrantModal();
      // Refresh summary to show updated credit totals
      fetchSummary();
    } catch (err: any) {
      toast.error(err.message || 'Failed to grant credits');
    } finally {
      setGranting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <div className="text-red-800 dark:text-red-200">
          <h3 className="font-medium">Error loading organizations</h3>
          <p className="mt-1 text-sm">{error}</p>
          <button
            onClick={fetchOrganizations}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Organizations
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage all organizations on the platform
          </p>
        </div>
        <button 
          onClick={handleInviteOrganization}
          className="bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>Invite Organization</span>
        </button>
      </div>

      {/* Filters and Search */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search by name, city, country, or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          </div>
          <div className="flex gap-2">
            {/* Type Filter */}
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as 'all' | 'prepay_org' | 'grant_org')}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="all">All Types</option>
              <option value="grant_org">Grant</option>
              <option value="prepay_org">Prepay</option>
            </select>
            
            {/* Country Filter */}
            <select
              value={countryFilter}
              onChange={(e) => setCountryFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="all">All Countries</option>
              {uniqueCountries.map(country => (
                <option key={country} value={country}>{country}</option>
              ))}
            </select>

            {/* Clear Filters */}
            {(searchQuery || typeFilter !== 'all' || countryFilter !== 'all') && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setTypeFilter('all');
                  setCountryFilter('all');
                }}
                className="px-4 py-2 border border-red-300 dark:border-red-600 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center space-x-2"
              >
                <X className="w-4 h-4" />
                <span>Clear</span>
              </button>
            )}
          </div>
        </div>
        
        {/* Results count */}
        <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
          Showing {paginatedOrganizations.length} of {filteredOrganizations.length} organizations
          {filteredOrganizations.length !== organizations.length && (
            <span> (filtered from {organizations.length} total)</span>
          )}
        </div>
      </div>

      {/* Organizations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {paginatedOrganizations.map((org) => (
          <div key={org.id} className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-lg bg-brand-500 flex items-center justify-center">
                  <Building2 className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{org.name}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {org.city}, {org.country}
                  </p>
                </div>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                org.status === 'active' 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                  : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
              }`}>
                {org.status}
              </span>
            </div>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Type:</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  org.type === 'prepay_org' 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                    : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                }`}>
                  {org.type === 'prepay_org' ? 'Prepay' : 'Grant'}
                </span>
              </div>
              {org.monthly_credit_limit && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Monthly Limit:</span>
                  <span className="text-sm font-medium">{org.monthly_credit_limit.toLocaleString()}</span>
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Contact:</span>
                <span className="text-sm font-medium">{org.contact_email}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Created:</span>
                <span className="text-sm font-medium">
                  {new Date(org.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            
            <div className="flex items-center space-x-2 pt-4 mt-4 border-t border-gray-200 dark:border-gray-700">
              <button className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-sm flex items-center justify-center space-x-2">
                <Eye className="w-4 h-4" />
                <span>View</span>
              </button>
              <button 
                onClick={() => openGrantModal(org)}
                className="flex-1 px-3 py-2 border border-green-300 dark:border-green-600 text-green-700 dark:text-green-400 rounded-lg hover:bg-green-50 dark:hover:bg-green-900/20 text-sm flex items-center justify-center space-x-2"
              >
                <Coins className="w-4 h-4" />
                <span>Grant</span>
              </button>
              <button className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-sm">
                <Pause className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {paginatedOrganizations.length === 0 && (
        <div className="bg-white dark:bg-gray-800 p-12 rounded-lg border border-gray-200 dark:border-gray-700 text-center">
          <Building2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No organizations found
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            {searchQuery || typeFilter !== 'all' || countryFilter !== 'all'
              ? 'Try adjusting your search or filters'
              : 'No organizations have been created yet'}
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Page {currentPage} of {totalPages}
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Previous Button */}
            <button
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Previous</span>
            </button>

            {/* Page Numbers */}
            <div className="flex items-center space-x-1">
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter(page => {
                  // Show first page, last page, current page, and pages around current
                  return page === 1 || 
                         page === totalPages || 
                         Math.abs(page - currentPage) <= 1;
                })
                .map((page, index, array) => {
                  // Add ellipsis if there's a gap
                  const showEllipsisBefore = index > 0 && page - array[index - 1] > 1;
                  return (
                    <React.Fragment key={page}>
                      {showEllipsisBefore && (
                        <span className="px-2 text-gray-400">...</span>
                      )}
                      <button
                        onClick={() => goToPage(page)}
                        className={`px-3 py-2 rounded-lg text-sm font-medium ${
                          currentPage === page
                            ? 'bg-brand-500 text-white'
                            : 'border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                        }`}
                      >
                        {page}
                      </button>
                    </React.Fragment>
                  );
                })}
            </div>

            {/* Next Button */}
            <button
              onClick={() => goToPage(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
            >
              <span>Next</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {summary?.total_organizations ?? organizations.length}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Total Organizations</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {summary?.active_organizations ?? organizations.filter(org => org.status === 'active').length}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Active Organizations</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {summary?.total_members ?? 0}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Total Members</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {summary?.total_teams ?? 0}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Total Teams</p>
        </div>
      </div>

      {/* Grant Credits Modal */}
      {grantModalOpen && selectedOrg && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-lg bg-green-500 flex items-center justify-center">
                  <Coins className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Grant Credits</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{selectedOrg.name}</p>
                </div>
              </div>
              <button
                onClick={closeGrantModal}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Credit Amount
                </label>
                <input
                  type="number"
                  min="1"
                  value={creditAmount}
                  onChange={(e) => setCreditAmount(e.target.value)}
                  placeholder="Enter credit amount"
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-green-500 focus:border-transparent"
                />
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  Credits will expire in 60 days from the grant date.
                </p>
              </div>

              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Organization Details</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Type:</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      selectedOrg.type === 'prepay_org' 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                        : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                    }`}>
                      {selectedOrg.type === 'prepay_org' ? 'Prepay' : selectedOrg.type === 'grant_org' ? 'Grant' : 'Unknown'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Location:</span>
                    <span className="text-gray-900 dark:text-white">{selectedOrg.city}, {selectedOrg.country}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Contact:</span>
                    <span className="text-gray-900 dark:text-white">{selectedOrg.contact_email}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={closeGrantModal}
                disabled={granting}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-sm font-medium disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleGrantCredits}
                disabled={granting || !creditAmount}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {granting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Granting...</span>
                  </>
                ) : (
                  <>
                    <Coins className="w-4 h-4" />
                    <span>Grant Credits</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}