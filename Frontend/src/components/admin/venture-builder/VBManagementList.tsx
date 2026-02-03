'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Search, User, Mail, DollarSign, Calendar, Eye, Filter, UserPlus, Clock, X, ChevronRight } from 'lucide-react';
import { VBProfile } from '@/types/ventureBuilder';
import { fetchAllVBsAdmin } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import VBInviteForm from './VBInviteForm';

interface VBManagementListProps {
  onViewEdit: (vbId: string) => void;
}

export default function VBManagementList({ onViewEdit }: VBManagementListProps) {
  const [vbs, setVbs] = useState<VBProfile[]>([]);
  const [filteredVbs, setFilteredVbs] = useState<VBProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showAllVBs, setShowAllVBs] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  const loadVBs = useCallback(async () => {
    try {
      setIsLoading(true);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const pendingData = await fetchAllVBsAdmin(token, 'pending_admin_review');
      setPendingCount(pendingData.length);

      let allData: VBProfile[];
      if (showAllVBs) {
        allData = await fetchAllVBsAdmin(token);
      } else {
        allData = pendingData;
      }

      setVbs(allData);
      setFilteredVbs(allData);
    } catch (error: any) {
      console.error('Error fetching VBs:', error);
      toast.error(error.message || 'Failed to load venture builders');
      setVbs([]);
      setFilteredVbs([]);
    } finally {
      setIsLoading(false);
    }
  }, [showAllVBs]);

  useEffect(() => {
    loadVBs();
  }, [loadVBs]);

  useEffect(() => {
    let filtered = vbs;

    if (showAllVBs && statusFilter !== 'all') {
      filtered = filtered.filter((vb) => vb.status === statusFilter);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (vb) => {
          const name = vb.full_name || vb.name || '';
          return (
            name.toLowerCase().includes(query) ||
            vb.contact_email?.toLowerCase().includes(query)
          );
        }
      );
    }

    setFilteredVbs(filtered);
  }, [searchQuery, statusFilter, vbs, showAllVBs]);

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; className: string }> = {
      pending_profile: {
        label: 'Pending Profile',
        className: 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300 border-warning-200 dark:border-warning-700',
      },
      pending_admin_review: {
        label: 'Pending Review',
        className: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 border-orange-200 dark:border-orange-700',
      },
      active: {
        label: 'Active',
        className: 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300 border-success-200 dark:border-success-700',
      },
      inactive: {
        label: 'Inactive',
        className: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-600',
      },
    };

    const config = statusConfig[status] || statusConfig.inactive;

    return (
      <span className={`inline-flex px-2.5 py-1 text-xs font-medium rounded-full border ${config.className}`}>
        {config.label}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 dark:border-brand-400 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading venture builders...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
              {showAllVBs ? 'All Venture Builders' : 'Pending Approvals'}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {showAllVBs ? 'Manage all venture builder profiles' : 'Review and approve applications'}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <span className="text-sm text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-3 py-1.5 rounded-lg">
              <span className="font-semibold text-gray-900 dark:text-white">{filteredVbs.length}</span> {showAllVBs ? 'total' : 'pending'}
            </span>
            <button
              onClick={() => setShowAllVBs(!showAllVBs)}
              className="relative flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-all shadow-theme-xs"
            >
              {showAllVBs ? (
                <>
                  <Clock className="w-4 h-4" />
                  <span className="hidden sm:inline">Pending</span>
                  {pendingCount > 0 && (
                    <span className="absolute -top-2 -right-2 w-5 h-5 bg-error-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                      {pendingCount}
                    </span>
                  )}
                </>
              ) : (
                <>
                  <User className="w-4 h-4" />
                  <span className="hidden sm:inline">All VBs</span>
                </>
              )}
            </button>
            <button
              onClick={() => setShowInviteModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium transition-all shadow-theme-sm hover:shadow-theme-md"
            >
              <UserPlus className="w-4 h-4" />
              <span className="hidden sm:inline">Invite VB</span>
            </button>
          </div>
        </div>
      </div>

      {/* Search and Filter Card */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-theme-xs overflow-hidden">
        <div className="p-4 sm:p-6 border-b border-gray-100 dark:border-gray-700">
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
              />
            </div>
            {showAllVBs && (
              <div className="flex items-center gap-2 sm:w-auto">
                <Filter className="w-4 h-4 text-gray-400 hidden sm:block" />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full sm:w-auto px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
                >
                  <option value="all">All Status</option>
                  <option value="pending_profile">Pending Profile</option>
                  <option value="pending_admin_review">Pending Review</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Content */}
        {filteredVbs.length === 0 ? (
          <div className="text-center py-16 px-4">
            <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <User className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              No venture builders found
            </h3>
            <p className="text-gray-600 dark:text-gray-400 max-w-sm mx-auto">
              {searchQuery || statusFilter !== 'all'
                ? 'Try adjusting your search or filter criteria'
                : 'No venture builders yet. Invite someone to get started!'}
            </p>
          </div>
        ) : (
          <>
            {/* Desktop Table */}
            <div className="hidden lg:block overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-900/50">
                    <th className="text-left py-3 px-6 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Venture Builder
                    </th>
                    <th className="text-left py-3 px-6 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Contact
                    </th>
                    <th className="text-left py-3 px-6 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="text-left py-3 px-6 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Price
                    </th>
                    <th className="text-left py-3 px-6 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Updated
                    </th>
                    <th className="text-center py-3 px-6 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {filteredVbs.map((vb) => (
                    <tr
                      key={vb.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-gray-200 dark:border-gray-600 flex-shrink-0 bg-gray-100 dark:bg-gray-700">
                            <img
                              src={vb.profile_picture_url}
                              alt={vb.full_name || vb.name || 'VB'}
                              className="w-full h-full object-cover"
                            />
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium text-gray-900 dark:text-white truncate">
                              {vb.full_name || vb.name || 'N/A'}
                            </p>
                            {vb.expertise_areas && vb.expertise_areas.length > 0 && (
                              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                {vb.expertise_areas[0].name}
                              </p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                          <Mail className="w-4 h-4 flex-shrink-0" />
                          <span className="truncate max-w-[200px]">{vb.contact_email}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6">{getStatusBadge(vb.status)}</td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-1 text-sm">
                          {vb.credit_price_per_hour ? (
                            <span className="font-medium text-gray-900 dark:text-white">
                              {vb.credit_price_per_hour} <span className="text-gray-500 dark:text-gray-400">cr/hr</span>
                            </span>
                          ) : (
                            <span className="text-gray-400">Not set</span>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {new Date(vb.updated_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                          })}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-center">
                        <button
                          onClick={() => onViewEdit(vb.id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-brand-50 dark:bg-brand-900/30 hover:bg-brand-100 dark:hover:bg-brand-900/50 text-brand-600 dark:text-brand-400 rounded-lg text-sm font-medium transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="lg:hidden divide-y divide-gray-100 dark:divide-gray-700">
              {filteredVbs.map((vb) => (
                <button
                  key={vb.id}
                  onClick={() => onViewEdit(vb.id)}
                  className="w-full p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full overflow-hidden border-2 border-gray-200 dark:border-gray-600 flex-shrink-0 bg-gray-100 dark:bg-gray-700">
                      <img
                        src={vb.profile_picture_url}
                        alt={vb.full_name || vb.name || 'VB'}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-semibold text-gray-900 dark:text-white truncate">
                          {vb.full_name || vb.name || 'N/A'}
                        </p>
                        {getStatusBadge(vb.status)}
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 truncate mt-0.5">
                        {vb.contact_email}
                      </p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400">
                        {vb.credit_price_per_hour && (
                          <span className="flex items-center gap-1">
                            <DollarSign className="w-3 h-3" />
                            {vb.credit_price_per_hour} cr/hr
                          </span>
                        )}
                        {vb.expertise_areas && vb.expertise_areas.length > 0 && (
                          <span className="truncate">{vb.expertise_areas[0].name}</span>
                        )}
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Invite Venture Builder
              </h3>
              <button
                onClick={() => setShowInviteModal(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
            <div className="p-6">
              <VBInviteForm />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
