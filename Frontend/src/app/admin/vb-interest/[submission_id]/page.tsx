"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { authService } from '@/services/authService';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { 
  ArrowLeft,
  User,
  Briefcase,
  Building2,
  MapPin,
  Phone,
  Mail,
  Globe,
  Linkedin,
  CheckCircle,
  XCircle,
  Clock,
  Calendar,
  DollarSign,
  Languages,
  Target,
  Users,
  Loader2,
  Save,
  RefreshCw,
  ExternalLink
} from 'lucide-react';

// Helper to safely format optional values
const formatValue = (value: string | null | undefined): string | null => {
  if (value === undefined || value === null || value === '' || value === 'undefined') {
    return null;
  }
  return value;
};

// Helper to format phone number safely
const formatPhone = (countryCode: string | null | undefined, phoneNumber: string | null | undefined): string | null => {
  const safePhone = formatValue(phoneNumber);
  if (!safePhone) return null;
  
  const safeCountryCode = formatValue(countryCode);
  if (safeCountryCode) {
    return `${safeCountryCode} ${safePhone}`;
  }
  return safePhone;
};

// Types
interface VBInterestDetail {
  id: string;
  full_name: string;
  work_email: string;
  country_code?: string;
  phone_country_code?: string;
  phone_number: string;
  country_of_residence?: string;
  country?: string;
  city: string;
  current_role?: string;
  primary_role?: string;
  company_organization: string;
  linkedin_url: string;
  personal_website: string | null;
  has_founded_venture: boolean;
  ventures_founded_count: number | null;
  ventures_stage_reached: string | null;
  ventures_outcome: string | null;
  coaching_experience: string;
  programs_worked_with: string | null;
  support_areas: string[];
  support_areas_other: string | null;
  industries_of_focus: string[];
  industries_other: string | null;
  founder_stages: string[];
  founder_stages_other: string | null;
  geographies: string[];
  geographies_specific_countries: string | null;
  languages: string[];
  languages_other: string | null;
  weekly_availability: string;
  weekly_availability_other: string | null;
  hourly_rate_usd: number;
  status: 'pending' | 'invited' | 'rejected' | 'invited';
  admin_notes: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  invitation_sent_at: string | null;
  created_at: string;
  updated_at: string;
}

// Enum label mappings
const COACHING_EXPERIENCE_LABELS: Record<string, string> = {
  'no_experience': 'No formal experience',
  'none': 'No formal experience',
  'less_than_1_year': 'Less than 1 year',
  '1-2_years': '1-2 years',
  '3-5_years': '3-5 years',
  '5_plus_years': '5+ years',
};

const WEEKLY_AVAILABILITY_LABELS: Record<string, string> = {
  '2_hrs': 'Up to 2 hours',
  '4_hrs': 'Up to 4 hours',
  '6_hrs': 'Up to 6 hours',
  '10_hrs': 'Up to 10 hours',
  '10_plus_hrs': '10+ hours',
  'other': 'Other',
};

const SUPPORT_AREAS_LABELS: Record<string, string> = {
  'product_development': 'Product Development',
  'fundraising': 'Fundraising',
  'strategy': 'Strategy',
  'go_to_market': 'Go-to-Market',
  'sales': 'Sales',
  'marketing': 'Marketing',
  'operations': 'Operations',
  'finance': 'Finance',
  'legal': 'Legal',
  'hr_talent': 'HR & Talent',
  'technology': 'Technology',
  'leadership': 'Leadership',
  'other': 'Other',
};

const INDUSTRIES_LABELS: Record<string, string> = {
  'fintech': 'Fintech',
  'healthtech': 'Healthtech',
  'edtech': 'Edtech',
  'agritech': 'Agritech',
  'cleantech': 'Cleantech',
  'logistics': 'Logistics',
  'ecommerce': 'E-commerce',
  'saas': 'SaaS',
  'marketplace': 'Marketplace',
  'media_entertainment': 'Media & Entertainment',
  'real_estate': 'Real Estate',
  'insurance': 'Insurance',
  'manufacturing': 'Manufacturing',
  'financial_systems': 'Financial Systems',
  'agriculture': 'Agriculture',
  'other': 'Other',
};

const FOUNDER_STAGES_LABELS: Record<string, string> = {
  'ideation': 'Ideation',
  'early_stage': 'Early Stage (Pre-revenue)',
  'post_pmf': 'Post Product-Market Fit',
  'scaling': 'Scaling',
  'mature': 'Mature/Growth',
  'growth': 'Growth',
  'exit': 'Exit',
  'other': 'Other',
};

const GEOGRAPHIES_LABELS: Record<string, string> = {
  'east_africa': 'East Africa',
  'west_africa': 'West Africa',
  'north_africa': 'North Africa',
  'southern_africa': 'Southern Africa',
  'central_africa': 'Central Africa',
  'global': 'Global',
  'other': 'Other',
};

const LANGUAGES_LABELS: Record<string, string> = {
  'english': 'English',
  'french': 'French',
  'arabic': 'Arabic',
  'swahili': 'Swahili',
  'portuguese': 'Portuguese',
  'amharic': 'Amharic',
  'other': 'Other',
};

const STATUS_COLORS: Record<string, string> = {
  'pending': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  'invited': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  'rejected': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

function InfoItem({ label, value, icon: Icon }: { label: string; value: React.ReactNode; icon?: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="flex items-start gap-3 py-2">
      {Icon && <Icon className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />}
      <div className="flex-1 min-w-0">
        <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</div>
        <div className="text-sm text-gray-900 dark:text-white mt-0.5">{value || <span className="text-gray-400 italic">Not provided</span>}</div>
      </div>
    </div>
  );
}

function TagList({ items, labels, otherValue }: { items: string[]; labels: Record<string, string>; otherValue?: string | null }) {
  const safeItems = Array.isArray(items) ? items : [];
  if (safeItems.length === 0) return <span className="text-gray-400 italic">None selected</span>;
  
  return (
    <div className="flex flex-wrap gap-2">
      {safeItems.map((item) => (
        <span 
          key={item} 
          className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-700 dark:text-gray-300"
        >
          {labels[item] || item}
        </span>
      ))}
      {otherValue && (
        <span className="px-2 py-1 bg-brand-100 dark:bg-brand-900/30 rounded text-xs text-brand-700 dark:text-brand-300">
          {otherValue}
        </span>
      )}
    </div>
  );
}

function Section({ title, icon: Icon, children }: { title: string; icon: React.ComponentType<{ className?: string }>; children: React.ReactNode }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
        <Icon className="w-4 h-4 text-brand-500" />
        <h3 className="font-medium text-gray-900 dark:text-white">{title}</h3>
      </div>
      <div className="p-4">
        {children}
      </div>
    </div>
  );
}

export default function VBInterestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const submissionId = params.submission_id as string;
  
  const [submission, setSubmission] = useState<VBInterestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adminNotes, setAdminNotes] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  
  // Modal states
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [approveNotes, setApproveNotes] = useState('');
  const [sendInvitation, setSendInvitation] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectNotes, setRejectNotes] = useState('');
  const [sendNotification, setSendNotification] = useState(false);

  const fetchSubmission = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const token = authService.getCurrentToken();
      const response = await fetch(`${API_BASE_URL}/venture-builder/admin/interest/${submissionId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.status === 404) {
        setError('Submission not found');
        return;
      }
      
      if (!response.ok) {
        throw new Error('Failed to fetch submission details');
      }
      
      const result = await response.json();
      if (result.success) {
        setSubmission(result.data);
        setAdminNotes(result.data.admin_notes || '');
      } else {
        throw new Error(result.error || 'Failed to fetch submission');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load submission');
      toast.error(err.message || 'Failed to load submission');
    } finally {
      setLoading(false);
    }
  }, [submissionId]);

  useEffect(() => {
    if (submissionId) {
      fetchSubmission();
    }
  }, [fetchSubmission, submissionId]);

  const handleSaveNotes = async () => {
    try {
      setSavingNotes(true);
      const token = authService.getCurrentToken();
      
      const response = await fetch(`${API_BASE_URL}/venture-builder/admin/interest/${submissionId}/notes`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ admin_notes: adminNotes }),
      });
      
      const result = await response.json();
      if (result.success) {
        toast.success('Notes saved successfully');
        if (submission) {
          setSubmission({ ...submission, admin_notes: adminNotes });
        }
      } else {
        throw new Error(result.error || 'Failed to save notes');
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to save notes');
    } finally {
      setSavingNotes(false);
    }
  };

  const handleApprove = async (withInvitation: boolean = true) => {
    // Use Next.js API route instead of calling backend directly
    const url = `/api/admin/vb-interest/${submissionId}/approve`;
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
      setActionLoading(true);
      
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
        // Extract error message from various possible formats
        const errorMsg = result.detail || result.error || result.message || `Server error (${response.status})`;
        console.error('[VB Approve] Error:', errorMsg);
        
        // If invitation sending failed, offer to retry without invitation
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
        // Refetch to update status, reviewed_at, reviewed_by, etc.
        fetchSubmission();
      } else {
        const errorMsg = result.error || result.message || 'Failed to approve submission';
        toast.error(`Approve failed: ${errorMsg}`, { duration: 5000 });
      }
    } catch (err: any) {
      console.error('[VB Approve] Exception:', err);
      toast.error(`Network error: ${err.message || 'Failed to connect to server'}`, { duration: 5000 });
    } finally {
      setActionLoading(false);
    }
  };
  
  // Helper to approve without invitation (fallback)
  const handleApproveWithoutInvitation = () => {
    handleApprove(false);
  };

  const handleReject = async () => {
    // Use Next.js API route instead of calling backend directly
    const url = `/api/admin/vb-interest/${submissionId}/reject`;
    const token = authService.getCurrentToken();
    const requestBody = {
      rejection_reason: rejectReason?.trim() || null,
      admin_notes: rejectNotes?.trim() || null,
      send_notification: sendNotification,
    };
    
    // Debug logging
    console.log('[VB Reject] URL:', url);
    console.log('[VB Reject] Method: POST');
    console.log('[VB Reject] Submission ID:', submissionId);
    console.log('[VB Reject] Token present:', !!token);
    console.log('[VB Reject] Request body:', JSON.stringify(requestBody, null, 2));
    
    try {
      setActionLoading(true);
      
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
        // Refetch to update status, reviewed_at, reviewed_by, rejection_reason
        fetchSubmission();
      } else {
        const errorMsg = result.error || result.message || 'Failed to reject submission';
        toast.error(`Reject failed: ${errorMsg}`, { duration: 5000 });
      }
    } catch (err: any) {
      console.error('[VB Reject] Exception:', err);
      toast.error(`Network error: ${err.message || 'Failed to connect to server'}`, { duration: 5000 });
    } finally {
      setActionLoading(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 animate-spin text-brand-500" />
          <span className="text-gray-500 dark:text-gray-400">Loading submission details...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-4">
        <Link 
          href="/admin/vb-interest"
          className="inline-flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-brand-500"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to List
        </Link>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <div className="text-red-800 dark:text-red-200">
            <h3 className="font-medium">{error === 'Submission not found' ? 'Submission Not Found' : 'Error loading submission'}</h3>
            <p className="mt-1 text-sm">{error}</p>
            <div className="flex gap-3 mt-3">
              <button
                onClick={() => router.push('/admin/vb-interest')}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm"
              >
                Go Back
              </button>
              {error !== 'Submission not found' && (
                <button
                  onClick={fetchSubmission}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Retry
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!submission) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link 
            href="/admin/vb-interest"
            className="inline-flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-brand-500 mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to List
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            {submission.full_name}
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[submission.status]}`}>
              {submission.status.charAt(0).toUpperCase() + submission.status.slice(1)}
            </span>
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            {formatValue(submission.primary_role || submission.current_role) || 'Role not specified'} at {formatValue(submission.company_organization) || 'Organization not specified'}
          </p>
        </div>
        
        {submission.status === 'pending' && (
          <div className="flex gap-3">
            <button
              onClick={() => {
                setApproveNotes('');
                setSendInvitation(false);
                setShowApproveModal(true);
              }}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
            >
              <CheckCircle className="w-4 h-4" />
              Approve
            </button>
            <button
              onClick={() => {
                setRejectReason('');
                setRejectNotes('');
                setSendNotification(false);
                setShowRejectModal(true);
              }}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2"
            >
              <XCircle className="w-4 h-4" />
              Reject
            </button>
          </div>
        )}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Personal Information */}
          <Section title="Personal Information" icon={User}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoItem label="Full Name" value={submission.full_name} icon={User} />
              <InfoItem label="Work Email" value={submission.work_email} icon={Mail} />
              <InfoItem label="Phone" value={formatPhone(submission.phone_country_code || submission.country_code, submission.phone_number)} icon={Phone} />
              <InfoItem label="Location" value={[formatValue(submission.city), formatValue(submission.country || submission.country_of_residence)].filter(Boolean).join(', ') || null} icon={MapPin} />
            </div>
          </Section>

          {/* Professional Profile */}
          <Section title="Professional Profile" icon={Briefcase}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoItem label="Current Role" value={formatValue(submission.primary_role || submission.current_role)} icon={Briefcase} />
              <InfoItem label="Company/Organization" value={submission.company_organization} icon={Building2} />
              <InfoItem 
                label="LinkedIn" 
                value={submission.linkedin_url ? (
                  <a href={submission.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-brand-500 hover:underline flex items-center gap-1">
                    View Profile <ExternalLink className="w-3 h-3" />
                  </a>
                ) : null} 
                icon={Linkedin} 
              />
              <InfoItem 
                label="Personal Website" 
                value={submission.personal_website ? (
                  <a href={submission.personal_website} target="_blank" rel="noopener noreferrer" className="text-brand-500 hover:underline flex items-center gap-1">
                    {submission.personal_website.replace(/^https?:\/\//, '')} <ExternalLink className="w-3 h-3" />
                  </a>
                ) : null} 
                icon={Globe} 
              />
            </div>
          </Section>

          {/* Venture Building Experience */}
          <Section title="Venture Building Experience" icon={Target}>
            <div className="space-y-4">
              <InfoItem 
                label="Has Founded Venture" 
                value={submission.has_founded_venture ? 'Yes' : 'No'} 
              />
              {submission.has_founded_venture && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pl-7">
                  <InfoItem label="Ventures Founded" value={submission.ventures_founded_count} />
                  <InfoItem label="Stage Reached" value={submission.ventures_stage_reached} />
                  <InfoItem label="Outcome" value={submission.ventures_outcome} />
                </div>
              )}
              <InfoItem 
                label="Coaching Experience" 
                value={COACHING_EXPERIENCE_LABELS[submission.coaching_experience] || submission.coaching_experience} 
              />
              <InfoItem label="Programs Worked With" value={submission.programs_worked_with} />
            </div>
          </Section>

          {/* Expertise & Coverage */}
          <Section title="Expertise & Coverage" icon={Users}>
            <div className="space-y-4">
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Support Areas</div>
                <TagList items={submission.support_areas} labels={SUPPORT_AREAS_LABELS} otherValue={submission.support_areas_other} />
              </div>
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Industries of Focus</div>
                <TagList items={submission.industries_of_focus} labels={INDUSTRIES_LABELS} otherValue={submission.industries_other} />
              </div>
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Founder Stages</div>
                <TagList items={submission.founder_stages} labels={FOUNDER_STAGES_LABELS} otherValue={submission.founder_stages_other} />
              </div>
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Geographies</div>
                <TagList items={submission.geographies} labels={GEOGRAPHIES_LABELS} />
                {submission.geographies_specific_countries && (
                  <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    Specific countries: {submission.geographies_specific_countries}
                  </div>
                )}
              </div>
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Languages</div>
                <TagList items={submission.languages} labels={LANGUAGES_LABELS} otherValue={submission.languages_other} />
              </div>
            </div>
          </Section>

          {/* Availability & Rate */}
          <Section title="Availability & Rate" icon={Clock}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoItem 
                label="Weekly Availability" 
                value={
                  submission.weekly_availability === 'other' && submission.weekly_availability_other
                    ? submission.weekly_availability_other
                    : WEEKLY_AVAILABILITY_LABELS[submission.weekly_availability] || submission.weekly_availability
                } 
                icon={Clock} 
              />
              <InfoItem 
                label="Hourly Rate" 
                value={submission.hourly_rate_usd ? `$${submission.hourly_rate_usd}/hr` : null} 
                icon={DollarSign} 
              />
            </div>
          </Section>
        </div>

        {/* Right Column - Metadata & Admin Notes */}
        <div className="space-y-6">
          {/* Review Metadata */}
          <Section title="Review Metadata" icon={Calendar}>
            <div className="space-y-3">
              <InfoItem label="Status" value={
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[submission.status]}`}>
                  {submission.status.charAt(0).toUpperCase() + submission.status.slice(1)}
                </span>
              } />
              <InfoItem label="Created At" value={new Date(submission.created_at).toLocaleString()} />
              <InfoItem label="Updated At" value={new Date(submission.updated_at).toLocaleString()} />
              {submission.reviewed_at && (
                <InfoItem label="Reviewed At" value={new Date(submission.reviewed_at).toLocaleString()} />
              )}
              {submission.reviewed_by && (
                <InfoItem label="Reviewed By" value={submission.reviewed_by} />
              )}
              {submission.rejection_reason && (
                <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <div className="text-xs text-red-600 dark:text-red-400 uppercase tracking-wide mb-1">Rejection Reason</div>
                  <div className="text-sm text-red-800 dark:text-red-200">{submission.rejection_reason}</div>
                </div>
              )}
              {submission.invitation_sent_at && (
                <InfoItem label="Invitation Sent" value={new Date(submission.invitation_sent_at).toLocaleString()} />
              )}
            </div>
          </Section>

          {/* Admin Notes */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h3 className="font-medium text-gray-900 dark:text-white">Admin Notes</h3>
              <span className="text-xs text-gray-400">{adminNotes.length}/2000</span>
            </div>
            <div className="p-4">
              <textarea
                value={adminNotes}
                onChange={(e) => setAdminNotes(e.target.value)}
                maxLength={2000}
                rows={6}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm resize-none"
                placeholder="Add internal notes about this submission..."
              />
              <button
                onClick={handleSaveNotes}
                disabled={savingNotes || adminNotes === (submission.admin_notes || '')}
                className="mt-3 w-full px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {savingNotes ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save Notes
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Approve Modal */}
      {showApproveModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Approve Submission
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              You are about to approve <strong>{submission.full_name}</strong>&apos;s application.
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
                onClick={() => setShowApproveModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={() => handleApprove(sendInvitation)}
                disabled={actionLoading}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {actionLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                {sendInvitation ? 'Approve and invite' : 'Approve'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Reject Submission
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              You are about to reject <strong>{submission.full_name}</strong>&apos;s application.
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
                onClick={() => setShowRejectModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                // disabled={actionLoading || !rejectReason.trim()}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {actionLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
