"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { authService } from '@/services/authService';
import Link from 'next/link';
import { 
  Search, 
  Filter, 
  Eye, 
  CheckCircle, 
  XCircle, 
  ChevronDown,
  ArrowUpDown,
  RefreshCw,
  Loader2,
  ClipboardList,
  Inbox,
  ShieldAlert
} from 'lucide-react';

// Types - matches VBInterestSubmissionListItem from backend
interface VBInterestSubmission {
  id: string;
  full_name: string;
  work_email: string;
  primary_role: string;
  coaching_experience: string;
  support_areas: string[];
  industries_of_focus: string[];
  weekly_availability: string;
  hourly_rate_usd: number;
  status: 'pending' | 'approved' | 'invited' | 'rejected';
  created_at: string;
  // Optional fields that may be included in full response
  country?: string;
  city?: string;
  company_organization?: string;
}

interface ListResponse {
  items: VBInterestSubmission[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

// Error types for better state handling
type ErrorType = 'permission' | 'network' | 'server' | null;

interface FetchError {
  type: ErrorType;
  message: string;
  statusCode?: number;
}

// Enum label mappings
const COACHING_EXPERIENCE_LABELS: Record<string, string> = {
  'none': 'No formal experience',
  '1-2_years': '1-2 years',
  '3-5_years': '3-5 years',
  '5+_years': '5+ years',
};

const STATUS_COLORS: Record<string, string> = {
  'pending': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  'approved': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  'invited': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  'rejected': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

// Tab configuration - maps UI tabs to backend status values
const STATUS_TABS = [
  { id: 'all', label: 'All', filter: null },
  { id: 'pending', label: 'Pending', filter: 'pending' },
  { id: 'invited', label: 'Approved', filter: 'invited' },  // "Approved" tab shows invited status
  { id: 'rejected', label: 'Rejected', filter: 'rejected' },
];

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export default function VBInterestListPage() {
  const [submissions, setSubmissions] = useState<VBInterestSubmission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<FetchError | null>(null);
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'created_at' | 'full_name'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  
  // Modal states
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [selectedSubmission, setSelectedSubmission] = useState<VBInterestSubmission | null>(null);
  const [approveNotes, setApproveNotes] = useState('');
  const [sendInvitation, setSendInvitation] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectNotes, setRejectNotes] = useState('');
  const [sendNotification, setSendNotification] = useState(false);

  const fetchSubmissions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      // Map tab ID to backend status filter value
      const activeTab = STATUS_TABS.find(t => t.id === statusFilter);
      const backendStatus = activeTab?.filter;
      if (backendStatus) params.append('status', backendStatus);
      params.append('page', page.toString());
      params.append('page_size', '20');
      
      const token = authService.getCurrentToken();
      
      // Correct endpoint: GET /venture-builder/admin/interest
      const url = `${API_BASE_URL}/venture-builder/admin/interest?${params.toString()}`;
      console.log('[VB Interest] Fetching:', url);
      console.log('[VB Interest] Token present:', !!token);
      console.log('[VB Interest] API_BASE_URL:', API_BASE_URL);
      
      if (!API_BASE_URL) {
        console.error('[VB Interest] API_BASE_URL is not configured');
        throw { type: 'network', message: 'API URL is not configured. Check NEXT_PUBLIC_API_URL environment variable.' };
      }
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      // Log response details for debugging
      console.log('[VB Interest] Response status:', response.status);
      
      // Handle different status codes
      if (response.status === 401 || response.status === 403) {
        console.error('[VB Interest] Permission denied:', response.status);
        setError({
          type: 'permission',
          message: "You don't have permission to view VB Interest submissions.",
          statusCode: response.status
        });
        setSubmissions([]);
        return;
      }
      
      // 404 can mean "no submissions" - treat as empty state, not error
      if (response.status === 404) {
        console.log('[VB Interest] 404 response - treating as empty list');
        setSubmissions([]);
        setTotal(0);
        setTotalPages(1);
        setInitialLoadComplete(true);
        return;
      }
      
      // Server errors (5xx)
      if (response.status >= 500) {
        const errorText = await response.text().catch(() => 'Unknown server error');
        console.error('[VB Interest] Server error:', response.status, errorText);
        setError({
          type: 'server',
          message: 'The server encountered an error. Please try again later.',
          statusCode: response.status
        });
        return;
      }
      
      // Other non-OK responses
      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Request failed');
        console.error('[VB Interest] Request failed:', response.status, errorText);
        setError({
          type: 'network',
          message: `Request failed with status ${response.status}`,
          statusCode: response.status
        });
        return;
      }
      
      const result = await response.json();
      console.log('[VB Interest] Raw response:', JSON.stringify(result, null, 2));
      
      // Handle API response format
      let items: VBInterestSubmission[] = [];
      let totalCount = 0;
      let pages = 1;
      
      // Check for explicit failure
      if (result.success === false) {
        console.error('[VB Interest] API returned failure:', result.error || result.message);
        setError({
          type: 'server',
          message: result.error || result.message || 'Failed to fetch submissions'
        });
        return;
      }
      
      // Extract items from various possible response shapes
      // Try each possible format and log which one matched
      if (result.success === true && result.data) {
        // Format: { success: true, data: [...] } or { success: true, data: { items: [...] } }
        if (Array.isArray(result.data)) {
          console.log('[VB Interest] Matched format: { success, data: [...] }');
          items = result.data;
          totalCount = items.length;
        } else if (result.data.items) {
          console.log('[VB Interest] Matched format: { success, data: { items: [...] } }');
          items = result.data.items;
          totalCount = result.data.total || items.length;
          const pageSize = result.data.page_size || 20;
          pages = Math.ceil(totalCount / pageSize) || 1;
        }
      } else if (result.items) {
        // Format: { items: [...], total, page, page_size, has_next }
        console.log('[VB Interest] Matched format: { items: [...] }');
        items = result.items;
        totalCount = result.total || items.length;
        const pageSize = result.page_size || 20;
        pages = Math.ceil(totalCount / pageSize) || 1;
      } else if (Array.isArray(result.data)) {
        // Format: { data: [...] } without success flag
        console.log('[VB Interest] Matched format: { data: [...] }');
        items = result.data;
        totalCount = items.length;
      } else if (Array.isArray(result)) {
        // Format: direct array [...]
        console.log('[VB Interest] Matched format: direct array');
        items = result;
        totalCount = items.length;
      } else {
        // Unknown format - log it for debugging
        console.warn('[VB Interest] Unknown response format. Keys:', Object.keys(result));
      }
      
      console.log('[VB Interest] Parsed:', items.length, 'items, total:', totalCount);
      
      // Debug: Log first row to confirm field structure
      if (items.length > 0) {
        console.log('[VB Interest] Sample row:', JSON.stringify(items[0], null, 2));
        console.log('[VB Interest] Status values in response:', items.map((s: any) => s.status));
      }
      
      // Ensure items is always an array
      items = Array.isArray(items) ? items : [];
      
      // Client-side search filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        items = items.filter((s: VBInterestSubmission) => 
          s.full_name?.toLowerCase().includes(query) ||
          s.work_email?.toLowerCase().includes(query) ||
          s.country?.toLowerCase().includes(query) ||
          s.city?.toLowerCase().includes(query)
        );
      }
      
      // Client-side sorting
      items.sort((a: VBInterestSubmission, b: VBInterestSubmission) => {
        let comparison = 0;
        if (sortBy === 'created_at') {
          comparison = new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime();
        } else if (sortBy === 'full_name') {
          comparison = (a.full_name || '').localeCompare(b.full_name || '');
        }
        return sortOrder === 'desc' ? -comparison : comparison;
      });
      
      setSubmissions(items);
      setTotal(totalCount);
      setTotalPages(pages);
      setInitialLoadComplete(true);
      
    } catch (err: any) {
      // Handle network errors (fetch failed entirely)
      console.error('[VB Interest] Fetch error:', err);
      
      if (err.type) {
        // Already formatted error
        setError(err);
      } else if (err.name === 'TypeError' && err.message.includes('fetch')) {
        // Network error - couldn't reach server
        setError({
          type: 'network',
          message: 'Unable to connect to the server. Please check your internet connection.'
        });
      } else {
        setError({
          type: 'network',
          message: err.message || 'Failed to load submissions'
        });
      }
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page, searchQuery, sortBy, sortOrder]);

  useEffect(() => {
    fetchSubmissions();
  }, [fetchSubmissions]);

  const handleApprove = async (withInvitation: boolean = true) => {
    if (!selectedSubmission) return;
    
    // Use Next.js API route instead of calling backend directly
    const url = `/api/admin/vb-interest/${selectedSubmission.id}/approve`;
    const token = authService.getCurrentToken();
    const requestBody = {
      admin_notes: approveNotes?.trim() || null,
      send_invitation: withInvitation,
    };
    
    // Debug logging
    console.log('[VB Approve] URL:', url);
    console.log('[VB Approve] Method: POST');
    console.log('[VB Approve] Token present:', !!token);
    console.log('[VB Approve] Request body:', JSON.stringify(requestBody, null, 2));
    
    try {
      setActionLoading(selectedSubmission.id);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
      
      console.log('[VB Approve] Response status:', response.status);
      
      // Parse response - try JSON first, fallback to text
      let result: any;
      const responseText = await response.text();
      console.log('[VB Approve] Response body:', responseText);
      
      try {
        result = JSON.parse(responseText);
      } catch {
        result = { error: responseText || 'Unknown error' };
      }
      
      if (!response.ok) {
        const errorMsg = result.detail || result.error || result.message || `Server error (${response.status})`;
        console.error('[VB Approve] Error:', errorMsg);
        
        if (withInvitation && response.status === 500) {
          toast.error(
            `Approve failed (${response.status}): ${errorMsg}. Try approving without sending invitation.`,
            { duration: 8000 }
          );
        } else {
          toast.error(`Approve failed (${response.status}): ${errorMsg}`, { duration: 5000 });
        }
        return;
      }
      
      if (result.success) {
        toast.success(result.data?.message || 'Submission approved successfully');
        setShowApproveModal(false);
        setApproveNotes('');
        setSendInvitation(false);
        setSelectedSubmission(null);
        fetchSubmissions();
      } else {
        const errorMsg = result.error || result.message || 'Failed to approve submission';
        toast.error(`Approve failed: ${errorMsg}`, { duration: 5000 });
      }
    } catch (err: any) {
      console.error('[VB Approve] Exception:', err);
      toast.error(`Network error: ${err.message || 'Failed to connect to server'}`, { duration: 5000 });
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async () => {
    if (!selectedSubmission) return;
    
    // Use Next.js API route instead of calling backend directly
    const url = `/api/admin/vb-interest/${selectedSubmission.id}/reject`;
    const token = authService.getCurrentToken();
    const requestBody = {
      rejection_reason: rejectReason?.trim() || null,
      admin_notes: rejectNotes?.trim() || null,
      send_notification: sendNotification,
    };
    
    // Debug logging
    console.log('[VB Reject] URL:', url);
    console.log('[VB Reject] Method: POST');
    console.log('[VB Reject] Submission ID:', selectedSubmission.id);
    console.log('[VB Reject] Token present:', !!token);
    console.log('[VB Reject] Request body:', JSON.stringify(requestBody, null, 2));
    
    try {
      setActionLoading(selectedSubmission.id);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
      
      console.log('[VB Reject] Response status:', response.status);
      
      // Parse response - try JSON first, fallback to text
      let result: any;
      const responseText = await response.text();
      console.log('[VB Reject] Response body:', responseText);
      
      try {
        result = JSON.parse(responseText);
      } catch {
        result = { error: responseText || 'Unknown error' };
      }
      
      if (!response.ok) {
        const errorMsg = result.detail || result.error || result.message || `Server error (${response.status})`;
        console.error('[VB Reject] Error:', errorMsg);
        toast.error(`Reject failed (${response.status}): ${errorMsg}`, { duration: 5000 });
        return;
      }
      
      if (result.success) {
        toast.success(result.data?.message || 'Submission rejected successfully');
        setShowRejectModal(false);
        setRejectReason('');
        setRejectNotes('');
        setSendNotification(false);
        setSelectedSubmission(null);
        fetchSubmissions();
      } else {
        const errorMsg = result.error || result.message || 'Failed to reject submission';
        toast.error(`Reject failed: ${errorMsg}`, { duration: 5000 });
      }
    } catch (err: any) {
      console.error('[VB Reject] Exception:', err);
      toast.error(`Network error: ${err.message || 'Failed to connect to server'}`, { duration: 5000 });
    } finally {
      setActionLoading(null);
    }
  };

  const openApproveModal = (submission: VBInterestSubmission) => {
    setSelectedSubmission(submission);
    setApproveNotes('');
    setSendInvitation(false);
    setShowApproveModal(true);
  };

  const openRejectModal = (submission: VBInterestSubmission) => {
    setSelectedSubmission(submission);
    setRejectReason('');
    setRejectNotes('');
    setSendNotification(false);
    setShowRejectModal(true);
  };

  const toggleSort = (field: 'created_at' | 'full_name') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  // Loading state (only show on initial load)
  if (loading && !initialLoadComplete) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 animate-spin text-brand-500" />
          <span className="text-gray-500 dark:text-gray-400">Loading submissions...</span>
        </div>
      </div>
    );
  }

  // Permission error state
  if (error?.type === 'permission') {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <ClipboardList className="w-8 h-8 text-brand-500" />
            VB Interest Submissions
          </h1>
        </div>
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <ShieldAlert className="w-6 h-6 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-amber-800 dark:text-amber-200">Access Restricted</h3>
              <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">{error.message}</p>
              <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
                Please contact your administrator if you believe you should have access.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Server/Network error state
  if (error && !initialLoadComplete) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <ClipboardList className="w-8 h-8 text-brand-500" />
            VB Interest Submissions
          </h1>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <div className="text-red-800 dark:text-red-200">
            <h3 className="font-medium">
              {error.type === 'server' ? 'Server Error' : 'Connection Error'}
            </h3>
            <p className="mt-1 text-sm">{error.message}</p>
            {error.statusCode && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                Status code: {error.statusCode}
              </p>
            )}
            <button
              onClick={fetchSubmissions}
              disabled={loading}
              className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Empty state logic - different messages for different filters
  const showEmptyState = initialLoadComplete && submissions.length === 0 && !error && !searchQuery.trim();
  const getEmptyStateMessage = () => {
    if (statusFilter === 'invited') {
      return {
        title: 'No invited submissions yet',
        description: 'Approved submissions will appear here once an invitation has been sent.'
      };
    }
    if (statusFilter === 'pending') {
      return {
        title: 'No pending submissions',
        description: 'There are no submissions awaiting review at this time.'
      };
    }
    if (statusFilter === 'rejected') {
      return {
        title: 'No rejected submissions',
        description: 'There are no rejected submissions.'
      };
    }
    return {
      title: 'No submissions yet',
      description: 'Venture Builder interest applications will appear here.'
    };
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <ClipboardList className="w-8 h-8 text-brand-500" />
            VB Interest Submissions
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Review and manage Venture Builder expression of interest applications
          </p>
        </div>
        <button
          onClick={fetchSubmissions}
          disabled={loading}
          className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 flex items-center gap-2 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{total}</div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Total Submissions</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-yellow-600">{submissions.filter(s => s.status === 'pending').length}</div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Pending Review</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-green-600">{submissions.filter(s => s.status === 'invited').length}</div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Invited</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-2xl font-bold text-red-600">{submissions.filter(s => s.status === 'rejected').length}</div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Rejected</p>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search by name, email, location..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          </div>
          
          {/* Status Filter Tabs */}
          <div className="flex gap-2">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => { setStatusFilter(tab.id); setPage(1); }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  statusFilter === tab.id
                    ? 'bg-brand-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th 
                  className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => toggleSort('full_name')}
                >
                  <div className="flex items-center gap-2">
                    Name
                    <ArrowUpDown className="w-4 h-4 text-gray-400" />
                  </div>
                </th>
                <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Email</th>
                {/* <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Location</th> */}
                <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Experience</th>
                <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Status</th>
                <th 
                  className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => toggleSort('created_at')}
                >
                  <div className="flex items-center gap-2">
                    Created
                    <ArrowUpDown className="w-4 h-4 text-gray-400" />
                  </div>
                </th>
                <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Actions</th>
              </tr>
            </thead>
            <tbody>
              {submissions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-16 text-center">
                    {showEmptyState ? (
                      // Empty state with context-aware messaging
                      <div className="flex flex-col items-center gap-3">
                        <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                          <Inbox className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                        </div>
                        <div>
                          <h3 className="text-lg font-medium text-gray-900 dark:text-white">{getEmptyStateMessage().title}</h3>
                          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
                            {getEmptyStateMessage().description}
                          </p>
                        </div>
                        <button
                          onClick={fetchSubmissions}
                          disabled={loading}
                          className="mt-2 px-4 py-2 text-sm text-brand-600 hover:text-brand-700 flex items-center gap-2 disabled:opacity-50"
                        >
                          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                          Refresh
                        </button>
                      </div>
                    ) : (
                      // Search result empty state
                      <div className="flex flex-col items-center gap-2 text-gray-500 dark:text-gray-400">
                        <ClipboardList className="w-12 h-12 text-gray-300 dark:text-gray-600" />
                        <span>No submissions match your search</span>
                        {searchQuery.trim() && (
                          <button
                            onClick={() => { setSearchQuery(''); }}
                            className="text-brand-500 hover:underline text-sm"
                          >
                            Clear search
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ) : (
                submissions.map((submission) => (
                  <tr 
                    key={submission.id} 
                    className="border-t border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-brand-500 flex items-center justify-center">
                          <span className="text-white text-sm font-medium">
                            {submission.full_name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">{submission.full_name}</div>
                          <div className="text-xs text-gray-500">{submission.primary_role || '-'}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400 text-sm">
                      {submission.work_email}
                    </td>
                    {/* <td className="py-3 px-4 text-gray-600 dark:text-gray-400 text-sm">
                      {[submission.city, submission.country].filter(Boolean).join(', ') || '-'}
                    </td> */}
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400 text-sm">
                      {COACHING_EXPERIENCE_LABELS[submission.coaching_experience] || submission.coaching_experience || '-'}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[submission.status] || 'bg-gray-100 text-gray-800'}`}>
                        {submission.status?.charAt(0).toUpperCase() + submission.status?.slice(1)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400 text-sm">
                      {new Date(submission.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1">
                        <Link
                          href={`/admin/vb-interest/${submission.id}`}
                          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg text-gray-600 dark:text-gray-400 hover:text-brand-500"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                        {submission.status === 'pending' && (
                          <>
                            <button
                              onClick={() => openApproveModal(submission)}
                              disabled={actionLoading === submission.id}
                              className="p-2 hover:bg-green-100 dark:hover:bg-green-900/30 rounded-lg text-gray-600 dark:text-gray-400 hover:text-green-600 disabled:opacity-50"
                              title="Approve"
                            >
                              <CheckCircle className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => openRejectModal(submission)}
                              disabled={actionLoading === submission.id}
                              className="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg text-gray-600 dark:text-gray-400 hover:text-red-600 disabled:opacity-50"
                              title="Reject"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center justify-between">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Page {page} of {totalPages} ({total} total)
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Approve Modal */}
      {showApproveModal && selectedSubmission && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Approve Submission
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              You are about to approve <strong>{selectedSubmission.full_name}</strong>&apos;s application.
            </p>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Admin Notes (optional)
                </label>
                <textarea
                  value={approveNotes}
                  onChange={(e) => setApproveNotes(e.target.value)}
                  maxLength={2000}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  placeholder="Internal notes about this approval..."
                />
                <span className="text-xs text-gray-400">{approveNotes.length}/2000</span>
              </div>
              
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sendInvitation}
                  onChange={(e) => setSendInvitation(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Send invitation email</span>
              </label>
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => { setShowApproveModal(false); setSelectedSubmission(null); }}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={() => handleApprove(sendInvitation)}
                disabled={actionLoading === selectedSubmission.id}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {actionLoading === selectedSubmission.id && <Loader2 className="w-4 h-4 animate-spin" />}
                {sendInvitation ? 'Approve and invite' : 'Approve'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && selectedSubmission && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Reject Submission
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              You are about to reject <strong>{selectedSubmission.full_name}</strong>&apos;s application.
            </p>
            
            <div className="space-y-4">
              {/* <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Rejection Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  maxLength={1000}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  placeholder="This will be shown to the applicant..."
                />
                <span className="text-xs text-gray-400">{rejectReason.length}/1000</span>
              </div> */}
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Admin Notes (optional)
                </label>
                <textarea
                  value={rejectNotes}
                  onChange={(e) => setRejectNotes(e.target.value)}
                  maxLength={2000}
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  placeholder="Note that will be a part of the regret email."
                />
                <span className="text-xs text-gray-400">{rejectNotes.length}/2000</span>
              </div>
              
              {/* <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sendNotification}
                  onChange={(e) => setSendNotification(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Send rejection email</span>
              </label> */}
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => { setShowRejectModal(false); setSelectedSubmission(null); }}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={actionLoading === selectedSubmission.id || !rejectReason.trim()}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {actionLoading === selectedSubmission.id && <Loader2 className="w-4 h-4 animate-spin" />}
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
