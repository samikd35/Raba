"use client";

import React, { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useTeamStore } from "@/stores/teamStore";
import { useAuthStore } from "@/stores/authStore";
import { CreditRequestService, CreditRequest } from "@/lib/api/creditRequestService";
import { 
  CreditCard,
  Plus,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  X,
  Info,
  Ban,
  ChevronDown,
  ChevronUp,
  Filter,
  Search,
  RefreshCw,
  Calendar,
  User
} from "lucide-react";
import { useRouter } from "next/navigation";

// Live credits interfaces and hook (shared pattern with settings page)
interface CreditLot {
  id: string;
  credit_amount: number;
  valid_from: string;
  expires_at: string;
}

interface CreditsData {
  tenant_id: string;
  lots: CreditLot[];
  tenant_total_active_credits: number;
  user_total_consumed_in_tenant: number;
}

const useCreditsData = (currentTeam: { id: string } | null) => {
  const [creditsData, setCreditsData] = useState<CreditsData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { token, isInitialized, isAuthenticated } = useAuthStore();
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);
  const isFetchingRef = useRef(false);
  const lastFetchAtRef = useRef<number>(0);

  const fetchCreditsData = useCallback(async (forceRefresh = false) => {
    if (!isInitialized || !isAuthenticated || !currentTeam?.id || !token) {
      setCreditsData(null);
      setError(null);
      return;
    }

    if (isFetchingRef.current && !forceRefresh) return;

    const now = Date.now();
    if (!forceRefresh && now - lastFetchAtRef.current < 10000) return;

    try {
      setIsLoading(true);
      setError(null);
      isFetchingRef.current = true;

      if (abortControllerRef.current) abortControllerRef.current.abort();
      abortControllerRef.current = new AbortController();

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/me/credits`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        switch (response.status) {
          case 401: throw new Error('Authentication expired. Please sign in again.');
          case 403: throw new Error('Access forbidden. Check your permissions.');
          case 404: throw new Error('Credits endpoint not found.');
          case 429: throw new Error('Too many requests. Please try again later.');
          default: throw new Error(`Failed to fetch credits: ${response.status} ${response.statusText}`);
        }
      }

      const contentType = response.headers.get('content-type');
      if (!contentType?.includes('application/json')) {
        throw new Error('Invalid response format from credits API');
      }

      const data: CreditsData = await response.json();
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid data structure received from API');
      }

      const validated: CreditsData = {
        tenant_id: data.tenant_id || currentTeam.id,
        lots: Array.isArray(data.lots)
          ? data.lots.filter((lot: any) => lot?.id && typeof lot.credit_amount === 'number' && lot.valid_from && lot.expires_at)
          : [],
        tenant_total_active_credits: typeof data.tenant_total_active_credits === 'number' ? Math.max(0, data.tenant_total_active_credits) : 0,
        user_total_consumed_in_tenant: typeof data.user_total_consumed_in_tenant === 'number' ? Math.max(0, data.user_total_consumed_in_tenant) : 0,
      };

      if (isMountedRef.current) setCreditsData(validated);
    } catch (err: any) {
      if (err?.name === 'AbortError') return;
      if (isMountedRef.current) setError(err?.message || 'Failed to fetch credits data');
    } finally {
      if (isMountedRef.current) setIsLoading(false);
      lastFetchAtRef.current = Date.now();
      isFetchingRef.current = false;
    }
  }, [currentTeam?.id, token, isInitialized, isAuthenticated]);

  useEffect(() => {
    isMountedRef.current = true;
    isFetchingRef.current = false;
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, []);

  return { creditsData, isLoading, error, fetchCreditsData };
};

// Shadcn-style Modal Component
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
}

const Modal: React.FC<ModalProps> = ({ isOpen, onClose, children, className = "" }) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={handleBackdropClick}
    >
      <div
        ref={modalRef}
        className={`bg-white dark:bg-gray-900 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 max-w-md w-full mx-4 animate-in zoom-in-95 duration-200 ${className}`}
      >
        {children}
      </div>
    </div>
  );
};

export default function TeamWorkspaceCreditRequests() {
  const { currentTeam } = useTeamStore();
  const { user, isAuthenticated } = useAuthStore();
  const router = useRouter();

  const [requests, setRequests] = useState<CreditRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // New request form state
  const [showRequestForm, setShowRequestForm] = useState(false);
  const [requestedCredits, setRequestedCredits] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Enhanced UI state
  const [expandedRequest, setExpandedRequest] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "credits">("newest");

  // Refs for lifecycle safety
  const mountedRef = useRef(true);
  const successTimeoutRef = useRef<number | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // Live credits integration
  const { creditsData, isLoading: creditsLoading, error: creditsError, fetchCreditsData } = useCreditsData(currentTeam);
  const creditStats = useMemo(() => {
    if (creditsData) {
      const total = Math.max(creditsData.tenant_total_active_credits + creditsData.user_total_consumed_in_tenant, 1);
      const remaining = Math.max(creditsData.tenant_total_active_credits, 0);
      const used = Math.max(creditsData.user_total_consumed_in_tenant, 0);
      const percentage = total > 0 ? Math.round((remaining / total) * 100) : 0;
      const usedPercentage = total > 0 ? Math.round((used / total) * 100) : 0;
      return { total, remaining, used, percentage, usedPercentage };
    }
    const total = (currentTeam?.credit_pool_total || 0);
    const remaining = (currentTeam?.credit_pool_remaining || 0);
    const used = (currentTeam?.credit_pool_used || 0);
    const percentage = total > 0 ? Math.round((remaining / total) * 100) : 0;
    const usedPercentage = total > 0 ? Math.round((used / total) * 100) : 0;
    return { total, remaining, used, percentage, usedPercentage };
  }, [creditsData, currentTeam]);

  useEffect(() => {
    if (!currentTeam?.id) return;
    const t = setTimeout(() => fetchCreditsData(), 300);
    return () => clearTimeout(t);
  }, [currentTeam?.id, fetchCreditsData]);

  useEffect(() => {
    if (!currentTeam?.id) return;
    const interval = setInterval(() => fetchCreditsData(), 60000);
    return () => clearInterval(interval);
  }, [currentTeam?.id, fetchCreditsData]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (successTimeoutRef.current) {
        window.clearTimeout(successTimeoutRef.current);
        successTimeoutRef.current = null;
      }
    };
  }, []);

  const sanitizeReason = useCallback((text: string) => {
    const noTags = text.replace(/<[^>]*>/g, "");
    return noTags.slice(0, 1000);
  }, []);

  // Get organization ID from team context (NOT user.tenant_id which might be the team's tenant ID)
  const organizationId = currentTeam?.organization_id;

  const fetchRequests = useCallback(async () => {
    if (!organizationId) {
      if (mountedRef.current) {
        setLoading(false);
      }
      return;
    }

    try {
      if (mountedRef.current) {
        setLoading(true);
        setError(null);
      }
      // Use the new organization-based endpoint
      const data = await CreditRequestService.getMyCreditRequests(organizationId);
      const requestsArray = Array.isArray(data.requests) ? data.requests : [];
      if (mountedRef.current) {
        setRequests(requestsArray);
      }
    } catch (err: any) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Error fetching credit requests:', err);
      }
      const msg = typeof err?.message === 'string' ? err.message : 'Failed to load credit requests';
      if (/401|Unauthorized/i.test(msg)) {
        router.replace('/signin');
        return;
      }
      if (mountedRef.current) setError(msg);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [organizationId, router]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const handleOpenForm = useCallback(() => {
    setShowRequestForm(true);
    setError(null);
    setSuccess(null);
  }, []);

  const handleCloseForm = useCallback(() => {
    if (submitting) return;
    setShowRequestForm(false);
    setRequestedCredits("");
    setReason("");
    setError(null);
  }, [submitting]);

  const handleSubmitRequest = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isAuthenticated) {
      router.replace('/signin');
      return;
    }

    if (!organizationId) {
      setError("No organization context available");
      return;
    }

    if (!currentTeam?.id) {
      setError("No team selected");
      return;
    }

    const credits = Number.parseInt(requestedCredits, 10);
    if (!Number.isFinite(credits) || credits <= 0) {
      setError("Please enter a valid number of credits");
      return;
    }
    if (credits > 10000) {
      setError("Maximum request is 10,000 credits");
      return;
    }

    const cleanReason = sanitizeReason(reason).trim();

    try {
      if (submitting) return;
      setSubmitting(true);
      setError(null);
      setSuccess(null);

      // Use the new organization-based endpoint for team member requests
      await CreditRequestService.createTeamMemberCreditRequest(organizationId, {
        team_id: currentTeam.id,
        requested_amount: credits,
        reason: cleanReason || undefined,
      });

      if (mountedRef.current) {
        setSuccess(`Successfully requested ${credits.toLocaleString()} credits!`);
        setRequestedCredits("");
        setReason("");
        setShowRequestForm(false);
      }
      await fetchRequests();
      // Refresh credits after creating a request, in case it affects pool
      await fetchCreditsData(true);

      if (mountedRef.current) {
        successTimeoutRef.current = window.setTimeout(() => {
          if (mountedRef.current) setSuccess(null);
        }, 5000);
      }
    } catch (err: any) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Error creating credit request:', err);
      }
      const msg = typeof err?.message === 'string' ? err.message : 'Failed to create credit request';
      if (/401|Unauthorized/i.test(msg)) {
        router.replace('/signin');
        return;
      }
      setError(msg);
    } finally {
      if (mountedRef.current) setSubmitting(false);
    }
  };

  // Note: Cancel functionality is not available in the new API
  // Users cannot cancel their own requests - only org admins can reject them
  const handleCancelRequest = async (requestId: string) => {
    // Inform user that cancellation is not available
    setError('Credit requests cannot be cancelled. Please contact your organization administrator to reject this request.');
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />;
      case 'approved':
        return <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />;
      case 'rejected':
        return <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />;
      case 'cancelled':
        return <Ban className="w-4 h-4 text-gray-600 dark:text-gray-400" />;
      default:
        return <Clock className="w-4 h-4 text-gray-600 dark:text-gray-400" />;
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-800';
      case 'approved':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border border-green-200 dark:border-green-800';
      case 'rejected':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400 border border-gray-200 dark:border-gray-700';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400 border border-gray-200 dark:border-gray-700';
    }
  };

  const formatCredits = (credits: number) => new Intl.NumberFormat('en-US').format(credits);
  const formatDate = (date: string) => new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });

  // Filter and sort requests
  const filteredAndSortedRequests = requests
    .filter(request => {
      const matchesStatus = filterStatus === 'all' || request.status === filterStatus;
      const matchesSearch = searchQuery === '' || 
        request.reason?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (request.user_name || request.user_email || '').toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'oldest':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        case 'credits':
          return b.requested_amount - a.requested_amount;
        case 'newest':
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

  const pendingRequests = requests.filter(r => r.status === 'pending');
  const approvedRequests = requests.filter(r => r.status === 'approved');
  const rejectedRequests = requests.filter(r => r.status === 'rejected');

  if (!currentTeam) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">No team selected</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-[#101828] xl:px-10">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-brand-700 dark:text-white">
            Credit Requests
          </h1>
          <p className="text-brand-600 dark:text-brand-200 max-w-2xl text-sm mt-2">
            Request additional credits when your team pool is running low. Track your request status and history below.
          </p>
        </div>
        
        <button
          onClick={handleOpenForm}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold bg-brand-600 text-white rounded-xl hover:bg-brand-700 transition-all duration-200 shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 dark:bg-brand-500 dark:hover:bg-brand-600"
        >
          <Plus className="w-4 h-4" />
          New Request
        </button>
      </div>

      {/* Success Alert */}
      {success && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-4 flex items-start gap-3 animate-in fade-in duration-300 mb-6">
          <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-green-800 dark:text-green-200">Success</p>
            <p className="text-sm text-green-700 dark:text-green-300 mt-0.5">{success}</p>
          </div>
          <button 
            onClick={() => setSuccess(null)} 
            className="text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-200 transition-colors p-1 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/30"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex items-start gap-3 animate-in fade-in duration-300 mb-6">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-800 dark:text-red-200">Error</p>
            <p className="text-sm text-red-700 dark:text-red-300 mt-0.5">{error}</p>
          </div>
          <button 
            onClick={() => setError(null)} 
            className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 transition-colors p-1 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-200">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2.5 bg-brand-100 dark:bg-brand-800/50 rounded-lg">
              <CreditCard className="w-5 h-5 text-brand-600 dark:text-brand-400" />
            </div>
            <p className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wide">Available Credits</p>
          </div>
          <p className="text-2xl font-bold text-brand-700 dark:text-white mb-3">
            {formatCredits(creditStats.remaining)}
          </p>
          <div className="w-full bg-brand-100 dark:bg-brand-800/30 rounded-full h-2">
            <div 
              className="bg-brand-600 dark:bg-brand-500 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${creditStats.percentage}%` }}
            />
          </div>
        </div>
        
        <div className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-200">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2.5 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
              <Clock className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
            </div>
            <p className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wide">Pending</p>
          </div>
          <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400 mb-1">
            {pendingRequests.length}
          </p>
          <p className="text-xs text-brand-500 dark:text-brand-400">Awaiting review</p>
        </div>
        
        <div className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-200">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2.5 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <p className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wide">Approved</p>
          </div>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400 mb-1">
            {approvedRequests.length}
          </p>
          <p className="text-xs text-brand-500 dark:text-brand-400">Total approved</p>
        </div>
        
        <div className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-200">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2.5 bg-red-100 dark:bg-red-900/30 rounded-lg">
              <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <p className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wide">Rejected</p>
          </div>
          <p className="text-2xl font-bold text-red-600 dark:text-red-400 mb-1">
            {rejectedRequests.length}
          </p>
          <p className="text-xs text-brand-500 dark:text-brand-400">Not approved</p>
        </div>
      </div>

      {/* New Request Modal */}
      <Modal isOpen={showRequestForm} onClose={handleCloseForm}>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                New Credit Request
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Request additional credits for your team
              </p>
            </div>
            <button
              onClick={handleCloseForm}
              disabled={submitting}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <form ref={formRef} onSubmit={handleSubmitRequest} className="space-y-6">
            {/* Credits Input */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Credits Requested <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  type="number"
                  value={requestedCredits}
                  onChange={(e) => setRequestedCredits(e.target.value)}
                  placeholder="Enter number of credits"
                  min="1"
                  max="10000"
                  required
                  disabled={submitting}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors disabled:opacity-50 pr-20"
                />
                <div className="absolute inset-y-0 right-0 flex items-center pr-3">
                  <span className="text-gray-500 dark:text-gray-400 text-sm font-medium">credits</span>
                </div>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Enter a number between 1 and 10,000 credits
              </p>
            </div>

            {/* Reason Textarea */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Reason <span className="text-gray-500">(Optional)</span>
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Explain why you need additional credits. This helps administrators understand your request."
                rows={4}
                maxLength={1000}
                disabled={submitting}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none transition-colors disabled:opacity-50"
              />
              <div className="flex justify-between">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {reason.length}/1000 characters
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Optional but recommended
                </p>
              </div>
            </div>

            {/* Info Box */}
            <div className="bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-brand-600 dark:text-brand-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="text-sm font-medium text-brand-900 dark:text-brand-200">
                    Request Process
                  </p>
                  <p className="text-sm text-brand-800 dark:text-brand-300">
                    Your request will be sent to organization administrators for review. 
                    You'll receive a notification once it's processed, typically within 1-2 business days.
                  </p>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={handleCloseForm}
                disabled={submitting}
                className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition-colors font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || !requestedCredits}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium shadow-sm hover:shadow-md"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <CreditCard className="w-4 h-4" />
                    Submit Request
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </Modal>

      {/* Requests List Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-6 border-t border-gray-200 dark:border-gray-700">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Request History
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {filteredAndSortedRequests.length} of {requests.length} requests
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search requests..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm w-full sm:w-48 transition-colors"
            />
          </div>

          {/* Filter and Sort */}
          <div className="flex gap-2">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm transition-colors"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="cancelled">Cancelled</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="px-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm transition-colors"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="credits">Most Credits</option>
            </select>
          </div>
        </div>
      </div>

      {/* Requests List */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="text-center space-y-3">
            <Loader2 className="w-8 h-8 text-brand-600 dark:text-brand-400 animate-spin mx-auto" />
            <p className="text-gray-600 dark:text-gray-400">Loading credit requests...</p>
          </div>
        </div>
      ) : requests.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
          <CreditCard className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            No credit requests yet
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
            When your team needs additional credits, you can submit a request for administrator approval.
          </p>
          <button
            onClick={handleOpenForm}
            className="inline-flex items-center gap-2 px-6 py-3 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors shadow-sm hover:shadow-md font-medium"
          >
            <Plus className="w-4 h-4" />
            Create Your First Request
          </button>
        </div>
      ) : filteredAndSortedRequests.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center">
          <Filter className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            No matching requests
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Try adjusting your search or filter criteria
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredAndSortedRequests.map((request) => (
            <div
              key={request.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 hover:shadow-sm transition-all duration-200"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4 flex-1">
                  <div className="flex-shrink-0 mt-1">
                    {getStatusIcon(request.status)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        {formatCredits(request.requested_amount)} Credits
                      </h3>
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${getStatusBadgeColor(request.status)}`}>
                        {getStatusIcon(request.status)}
                        {request.status.charAt(0).toUpperCase() + request.status.slice(1)}
                      </span>
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-gray-600 dark:text-gray-400">
                      <div className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        <span>{request.user_name || request.user_email || 'Unknown'}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        <span>{formatDate(request.created_at)}</span>
                      </div>
                      {request.reason && (
                        <button
                          onClick={() => setExpandedRequest(
                            expandedRequest === request.id ? null : request.id
                          )}
                          className="text-brand-600 dark:text-brand-400 hover:text-brand-800 dark:hover:text-brand-300 transition-colors flex items-center gap-1 font-medium"
                        >
                          {expandedRequest === request.id ? (
                            <>Hide Details <ChevronUp className="w-3 h-3" />
                            </>
                          ) : (
                            <>Show Details <ChevronDown className="w-3 h-3" />
                            </>
                          )}
                        </button>
                      )}
                    </div>

                    {/* Expandable Reason */}
                    {expandedRequest === request.id && request.reason && (
                      <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Reason:</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap leading-relaxed">{request.reason}</p>
                      </div>
                    )}

                    {/* Status Details */}
                    {(request.status === 'approved' || request.status === 'rejected') && (
                      <div className={`mt-4 p-4 rounded-lg border ${
                        request.status === 'approved' 
                          ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                          : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                      }`}>
                        <div className="flex items-start gap-3">
                          {request.status === 'approved' ? (
                            <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                          ) : (
                            <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                          )}
                          <div className="space-y-1">
                            <p className="text-sm font-medium text-gray-900 dark:text-white">
                              {request.status === 'approved' ? 'Approved' : 'Rejected'} by {request.reviewed_by || 'Admin'}
                            </p>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {formatDate(request.reviewed_at!)}
                              {request.status === 'approved' && (
                                <> • {formatCredits(request.requested_amount)} credits approved</>
                              )}
                            </p>
                            {request.review_notes && (
                              <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                                <span className="font-medium">Note:</span> {request.review_notes}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Cancel Button */}
                {request.status === 'pending' && request.user_id === user?.id && (
                  <button
                    onClick={() => handleCancelRequest(request.id)}
                    className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 text-sm font-medium px-3 py-1.5 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors ml-2 flex-shrink-0 border border-red-200 dark:border-red-800"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}