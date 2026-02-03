'use client';

import React, { useState, useMemo } from 'react';
import { z } from 'zod';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from "react-hot-toast";
import { organizationService } from '@/lib/api/organizationService';
import { fetchCohorts } from '@/components/organization/cohorts/cohortsApi';
import { Cohort } from '@/components/organization/cohorts/types';
import { CreateCohortModal } from '@/components/organization/cohorts/CreateCohortModal';
import { authService } from '@/services/authService';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Loader2,
  CheckCircle,
  AlertCircle,
  Mail,
  Users,
  Crown,
  X,
  Upload,
  Send,
  Trash2,
  AlertTriangle,
  Download,
  FileText,
  Plus,
  Sparkles,
  SkipForward,
  FolderOpen,
  Check,
  ShieldCheck,
} from 'lucide-react';
import { useCurrentOrganization, useOrganizationMetrics } from '@/stores/organizationStore';

// Package options
const INDIVIDUAL_PACKAGES = [100, 200, 300, 400, 500, 600, 700, 800];
const TEAM_LEADER_PACKAGES = [200, 300, 400, 500, 600, 700, 800];

// Validation schema
const memberInviteSchema = z.object({
  individual_members: z.array(z.object({
    email: z.string().email('Invalid email'),
    credits: z.number().int().positive('Must be greater than 0'),
    can_skip_modules: z.boolean().default(false),
  })),
  team_leaders: z.array(z.object({
    email: z.string().email('Invalid email'),
    credits: z.number().int().positive('Must be greater than 0'),
    can_skip_modules: z.boolean().default(false),
  })),
  organization_admins: z.array(z.object({
    email: z.string().email('Invalid email'),

  })),
}).refine(
  (data) => {
    const totalEmails = data.individual_members.length + data.team_leaders.length + data.organization_admins.length;
    return totalEmails > 0;
  },
  {
    message: 'At least one email is required',
    path: ['individual_members'],
  }
);

type FormData = z.infer<typeof memberInviteSchema>;

interface MemberInviteFormProps {
  organizationId: string;
  organizationName?: string;
  onInviteSuccess?: () => void;
}

export const MemberInviteForm: React.FC<MemberInviteFormProps> = ({
  organizationId,
  organizationName,
  onInviteSuccess
}) => {
  const currentOrganization = useCurrentOrganization();
  const metrics = useOrganizationMetrics();
  const router = useRouter();

  // Form state
  const [formData, setFormData] = useState<FormData>({
    individual_members: [],
    team_leaders: [],
    organization_admins: [],
  });

  // Default credit packages
  const [defaultIndividualCredits, setDefaultIndividualCredits] = useState(200);
  const [defaultTeamLeaderCredits, setDefaultTeamLeaderCredits] = useState(200);

  // UI state
  const [individualEmailInput, setIndividualEmailInput] = useState('');
  const [teamLeaderEmailInput, setTeamLeaderEmailInput] = useState('');
  const [orgAdminEmailInput, setOrgAdminEmailInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [sentInvitations, setSentInvitations] = useState<Array<{ email: string; is_admin: boolean; is_team_leader: boolean; credits: number }>>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [activeSection, setActiveSection] = useState<'individual' | 'team_leader' | 'org_admin'>('individual');
  const [isInsufficientCreditsModalOpen, setIsInsufficientCreditsModalOpen] = useState(false);
  const [insufficientCreditsError, setInsufficientCreditsError] = useState<{
    code: string;
    message: string;
  } | null>(null);

  // Cohort selection state
  const [isCohortModalOpen, setIsCohortModalOpen] = useState(false);
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [selectedCohort, setSelectedCohort] = useState<Cohort | null>(null);
  const [isLoadingCohorts, setIsLoadingCohorts] = useState(false);
  const [isCreateCohortModalOpen, setIsCreateCohortModalOpen] = useState(false);

  // Calculate total credits required
  const totalCreditsRequired = useMemo(() => {
    const individualTotal = formData.individual_members.reduce((sum, member) => sum + member.credits, 0);
    const teamLeaderTotal = formData.team_leaders.reduce((sum, leader) => sum + leader.credits, 0);
    return individualTotal + teamLeaderTotal;
  }, [formData]);

  // Check if limit would be exceeded (for grant_org)
  const isLimitExceeded = useMemo(() => {
    if (currentOrganization?.type !== 'grant_org') return false;
    if (!currentOrganization.monthly_credit_limit) return false;

    const currentUsage = metrics?.credits?.used || 0;
    const monthlyLimit = currentOrganization.monthly_credit_limit;

    return (currentUsage + totalCreditsRequired) > monthlyLimit;
  }, [currentOrganization, metrics, totalCreditsRequired]);

  // Calculate remaining credits
  const remainingCredits = useMemo(() => {
    if (currentOrganization?.type !== 'grant_org' || !currentOrganization.monthly_credit_limit) return null;
    return currentOrganization.monthly_credit_limit - (metrics?.credits?.used || 0) - totalCreditsRequired;
  }, [currentOrganization, metrics, totalCreditsRequired]);

  // Credit usage percentage
  const creditUsagePercentage = useMemo(() => {
    if (currentOrganization?.type !== 'grant_org' || !currentOrganization.monthly_credit_limit) return 0;
    const currentUsage = metrics?.credits?.used || 0;
    return Math.min(100, ((currentUsage + totalCreditsRequired) / currentOrganization.monthly_credit_limit) * 100);
  }, [currentOrganization, metrics, totalCreditsRequired]);

  // Add email to individual members (supports bulk input)
  const handleAddIndividualEmail = () => {
    const input = individualEmailInput.trim();
    if (!input) return;

    // Split by comma or space
    const emailList = input.split(/[,\s]+/).map(e => e.trim()).filter(e => e);

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const validEmails: string[] = [];
    const invalidEmails: string[] = [];
    const duplicateEmails: string[] = [];

    const existingIndividualEmails = formData.individual_members.map(m => m.email);
    const existingTeamLeaderEmails = formData.team_leaders.map(l => l.email);

    emailList.forEach(email => {
      if (!emailRegex.test(email)) {
        invalidEmails.push(email);
      } else if (existingIndividualEmails.includes(email) || existingTeamLeaderEmails.includes(email)) {
        duplicateEmails.push(email);
      } else {
        validEmails.push(email);
      }
    });

    // Show feedback
    if (invalidEmails.length > 0) {
      toast.error(`Invalid email format: ${invalidEmails.slice(0, 3).join(', ')}${invalidEmails.length > 3 ? '...' : ''}`);
    }
    if (duplicateEmails.length > 0) {
      toast.error(`Already added: ${duplicateEmails.slice(0, 3).join(', ')}${duplicateEmails.length > 3 ? '...' : ''}`);
    }
    if (validEmails.length > 0) {
      const newMembers = validEmails.map(email => ({
        email,
        credits: defaultIndividualCredits,
        can_skip_modules: false,
      }));
      setFormData(prev => ({
        ...prev,
        individual_members: [...prev.individual_members, ...newMembers],
      }));
      toast.success(`Added ${validEmails.length} individual member(s)`);
      setIndividualEmailInput('');
      setErrors(prev => ({ ...prev, individual_emails: '' }));
    }
  };

  // Remove email from individual members
  const handleRemoveIndividualEmail = (email: string) => {
    setFormData(prev => ({
      ...prev,
      individual_members: prev.individual_members.filter(m => m.email !== email),
    }));
    toast.success('Member removed');
  };

  // Update credits for individual member
  const handleUpdateIndividualCredits = (email: string, credits: number) => {
    setFormData(prev => ({
      ...prev,
      individual_members: prev.individual_members.map(m =>
        m.email === email ? { ...m, credits } : m
      ),
    }));
  };

  // Update can_skip_modules for individual member
  const handleUpdateIndividualSkip = (email: string, can_skip_modules: boolean) => {
    setFormData(prev => ({
      ...prev,
      individual_members: prev.individual_members.map(m =>
        m.email === email ? { ...m, can_skip_modules } : m
      ),
    }));
  };

  // Add email to team leaders (supports bulk input)
  const handleAddTeamLeaderEmail = () => {
    const input = teamLeaderEmailInput.trim();
    if (!input) return;

    // Split by comma or space
    const emailList = input.split(/[,\s]+/).map(e => e.trim()).filter(e => e);

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const validEmails: string[] = [];
    const invalidEmails: string[] = [];
    const duplicateEmails: string[] = [];

    const existingIndividualEmails = formData.individual_members.map(m => m.email);
    const existingTeamLeaderEmails = formData.team_leaders.map(l => l.email);
    const existingAdminEmails = formData.organization_admins.map(a => a.email);

    emailList.forEach(email => {
      if (!emailRegex.test(email)) {
        invalidEmails.push(email);
      } else if (existingTeamLeaderEmails.includes(email) || existingIndividualEmails.includes(email) || existingAdminEmails.includes(email)) {
        duplicateEmails.push(email);
      } else {
        validEmails.push(email);
      }
    });

    // Show feedback
    if (invalidEmails.length > 0) {
      toast.error(`Invalid email format: ${invalidEmails.slice(0, 3).join(', ')}${invalidEmails.length > 3 ? '...' : ''}`);
    }
    if (duplicateEmails.length > 0) {
      toast.error(`Already added: ${duplicateEmails.slice(0, 3).join(', ')}${duplicateEmails.length > 3 ? '...' : ''}`);
    }
    if (validEmails.length > 0) {
      const newLeaders = validEmails.map(email => ({
        email,
        credits: defaultTeamLeaderCredits,
        can_skip_modules: false,
      }));
      setFormData(prev => ({
        ...prev,
        team_leaders: [...prev.team_leaders, ...newLeaders],
      }));
      toast.success(`Added ${validEmails.length} team leader(s)`);
      setTeamLeaderEmailInput('');
      setErrors(prev => ({ ...prev, team_leader_emails: '' }));
    }
  };

  // Add email to organization admins (supports bulk input)
  const handleAddOrgAdminEmail = () => {
    const input = orgAdminEmailInput.trim();
    if (!input) return;

    // Split by comma or space
    const emailList = input.split(/[,\s]+/).map(e => e.trim()).filter(e => e);

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const validEmails: string[] = [];
    const invalidEmails: string[] = [];
    const duplicateEmails: string[] = [];

    const existingIndividualEmails = formData.individual_members.map(m => m.email);
    const existingTeamLeaderEmails = formData.team_leaders.map(l => l.email);
    const existingAdminEmails = formData.organization_admins.map(a => a.email);

    emailList.forEach(email => {
      if (!emailRegex.test(email)) {
        invalidEmails.push(email);
      } else if (existingAdminEmails.includes(email) || existingIndividualEmails.includes(email) || existingTeamLeaderEmails.includes(email)) {
        duplicateEmails.push(email);
      } else {
        validEmails.push(email);
      }
    });

    // Show feedback
    if (invalidEmails.length > 0) {
      toast.error(`Invalid email format: ${invalidEmails.slice(0, 3).join(', ')}${invalidEmails.length > 3 ? '...' : ''}`);
    }
    if (duplicateEmails.length > 0) {
      toast.error(`Already added: ${duplicateEmails.slice(0, 3).join(', ')}${duplicateEmails.length > 3 ? '...' : ''}`);
    }
    if (validEmails.length > 0) {
      const newAdmins = validEmails.map(email => ({
        email,
      }));
      setFormData(prev => ({
        ...prev,
        organization_admins: [...prev.organization_admins, ...newAdmins],
      }));
      toast.success(`Added ${validEmails.length} admin(s)`);
      setOrgAdminEmailInput('');
      setErrors(prev => ({ ...prev, admin_emails: '' }));
    }
  };

  // Remove email from organization admins
  const handleRemoveOrgAdminEmail = (email: string) => {
    setFormData(prev => ({
      ...prev,
      organization_admins: prev.organization_admins.filter(a => a.email !== email),
    }));
    toast.success('Admin removed');
  };

  // Remove email from team leaders
  const handleRemoveTeamLeaderEmail = (email: string) => {
    setFormData(prev => ({
      ...prev,
      team_leaders: prev.team_leaders.filter(l => l.email !== email),
    }));
    toast.success('Team leader removed');
  };

  // Update credits for team leader
  const handleUpdateTeamLeaderCredits = (email: string, credits: number) => {
    setFormData(prev => ({
      ...prev,
      team_leaders: prev.team_leaders.map(l =>
        l.email === email ? { ...l, credits } : l
      ),
    }));
  };

  // Update can_skip_modules for team leader
  const handleUpdateTeamLeaderSkip = (email: string, can_skip_modules: boolean) => {
    setFormData(prev => ({
      ...prev,
      team_leaders: prev.team_leaders.map(l =>
        l.email === email ? { ...l, can_skip_modules } : l
      ),
    }));
  };

  // Download CSV template
  const handleDownloadTemplate = (type: 'individual' | 'team_leader' | 'org_admin') => {
    let csvContent = '';
    if (type === 'org_admin') {
      csvContent = `Email\nadmin1@company.com\nadmin2@company.com`;
    } else {
      csvContent = `Email,Credits\nexample1@company.com,${type === 'individual' ? '150' : '300'}\nexample2@company.com,${type === 'individual' ? '200' : '350'}\nexample3@company.com,${type === 'individual' ? '250' : '400'}`;
    }

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', `${type}_invitation_template.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    toast.success('Template downloaded successfully');
  };

  // Handle CSV upload with Email,Credits format
  const handleCSVUpload = (event: React.ChangeEvent<HTMLInputElement>, type: 'individual' | 'team_leader' | 'org_admin') => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const lines = text.split('\n').map(line => line.trim()).filter(line => line);

        // Skip header row if present
        const dataLines = lines[0].toLowerCase().includes('email') ? lines.slice(1) : lines;

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const existingIndividualEmails = formData.individual_members.map(m => m.email);
        const existingTeamLeaderEmails = formData.team_leaders.map(l => l.email);
        const existingAdminEmails = formData.organization_admins.map(a => a.email);
        const existingEmails = [...existingIndividualEmails, ...existingTeamLeaderEmails, ...existingAdminEmails];

        const newMembers: Array<{ email: string; credits: number; is_admin?: boolean }> = [];
        const newAdmins: Array<{ email: string }> = [];
        const errors: string[] = [];

        dataLines.forEach((line, index) => {
          const parts = line.split(',').map(p => p.trim());

          if (parts.length >= 2 && type !== 'org_admin') {
            const email = parts[0];
            const creditsStr = parts[1];

            // Validate email
            if (!emailRegex.test(email)) {
              errors.push(`Line ${index + 2}: Invalid email format`);
              return;
            }

            // Check for duplicates
            if (existingEmails.includes(email) || newMembers.some(m => m.email === email)) {
              errors.push(`Line ${index + 2}: Duplicate email ${email}`);
              return;
            }

            // Parse credits
            const credits = parseInt(creditsStr, 10);
            if (isNaN(credits) || credits <= 0) {
              errors.push(`Line ${index + 2}: Invalid credits value`);
              return;
            }

            newMembers.push({ email, credits, can_skip_modules: false });
          } else if (parts.length >= 1 && parts[0]) {
            // Support single email column
            const email = parts[0];
            if (!emailRegex.test(email)) {
              errors.push(`Line ${index + 2}: Invalid email format`);
              return;
            }

            if (existingEmails.includes(email) || newMembers.some(m => m.email === email) || newAdmins.some(a => a.email === email)) {
              errors.push(`Line ${index + 2}: Duplicate email ${email}`);
              return;
            }

            if (type === 'org_admin') {
              newAdmins.push({ email });
            } else {
              const defaultCredits = type === 'individual' ? defaultIndividualCredits : defaultTeamLeaderCredits;
              newMembers.push({ email, credits: defaultCredits, can_skip_modules: false });
            }
          }
        });

        if (errors.length > 0) {
          toast.error(`CSV parsing errors: ${errors.slice(0, 3).join(', ')}${errors.length > 3 ? '...' : ''}`);
        }

        if (newMembers.length === 0 && newAdmins.length === 0) {
          toast.error('No valid entries found in CSV');
          return;
        }

        if (type === 'individual') {
          setFormData(prev => ({
            ...prev,
            individual_members: [...prev.individual_members, ...newMembers],
          }));
        } else if (type === 'team_leader') {
          setFormData(prev => ({
            ...prev,
            team_leaders: [...prev.team_leaders, ...newMembers],
          }));
        } else {
          setFormData(prev => ({
            ...prev,
            organization_admins: [...prev.organization_admins, ...newAdmins],
          }));
        }

        toast.success(`Added ${type === 'org_admin' ? newAdmins.length : newMembers.length} ${type === 'org_admin' ? 'admin(s)' : (type === 'individual' ? 'member(s)' : 'team leader(s)')} from CSV${errors.length > 0 ? ` (${errors.length} errors)` : ''}`);
      } catch (error) {
        console.error('Error parsing CSV:', error);
        toast.error('Failed to parse CSV file');
      }
    };
    reader.readAsText(file);

    // Reset file input
    event.target.value = '';
  };

  // Validate form
  const validateForm = (): boolean => {
    try {
      memberInviteSchema.parse(formData);
      setErrors({});
      return true;
    } catch (error) {
      if (error instanceof z.ZodError) {
        const newErrors: Record<string, string> = {};
        error.issues.forEach(issue => {
          const path = issue.path.join('.');
          newErrors[path] = issue.message;
        });
        setErrors(newErrors);
      }
      return false;
    }
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate form
    if (!validateForm()) {
      toast.error('Please fix the validation errors');
      return;
    }

    // Check if any emails are added
    const totalEmails = formData.individual_members.length + formData.team_leaders.length + formData.organization_admins.length;
    if (totalEmails === 0) {
      toast.error('Please add at least one email');
      return;
    }

    // Check if cohort is selected (required field - only if we have members/leaders)
    if ((formData.individual_members.length > 0 || formData.team_leaders.length > 0) && !selectedCohort) {
      toast.error('Please select a cohort');
      setErrors(prev => ({ ...prev, cohort: 'Cohort selection is required' }));
      return;
    }

    // Check limit for grant_org
    if (isLimitExceeded) {
      toast.error('Total credits exceed monthly limit');
      return;
    }

    // Validate credit allocations against organization limits
    if (currentOrganization?.type === 'grant_org' && currentOrganization.monthly_credit_limit) {
      const currentUsage = metrics?.credits?.used || 0;
      const monthlyLimit = currentOrganization.monthly_credit_limit;

      if ((currentUsage + totalCreditsRequired) > monthlyLimit) {
        toast.error('Total credits exceed monthly limit. Please reduce credit allocations or number of invites.');
        return;
      }
    }

    setIsLoading(true);

    try {
      // Add cohort_id to all members before sending
      const dataWithOptions = {
        individual_members: formData.individual_members.map(m => ({
          ...m,
          // can_skip_modules uses per-member setting
          cohort_id: selectedCohort?.id,
        })),
        team_leaders: formData.team_leaders.map(l => ({
          ...l,
          // can_skip_modules uses per-member setting
          cohort_id: selectedCohort?.id,
        })),
        // Add organization admins with required constants
        organization_admins: formData.organization_admins.map(a => ({
          email: a.email,
          credits: 0,
          is_admin: true,
          cohort_id: null,
          can_skip_modules: false
        }))
      };

      const response = await organizationService.inviteUsersToOrganization(organizationId, dataWithOptions as any);

      setSentInvitations(response.invites);
      setShowSuccess(true);

      // Debug logging to check invitation data
      if (process.env.NODE_ENV === 'development') {
        console.log('🎯 Sent invitations data:', response.invites);
        console.log('📊 Individual members count:', response.invites.filter(i => !i.is_team_leader && !i.is_admin).length);
        console.log('👑 Team leaders count:', response.invites.filter(i => i.is_team_leader).length);
        console.log('🛡️ Organization admins count:', response.invites.filter(i => i.is_admin).length);
        console.log('💰 Total credits:', response.invites.reduce((sum, i) => sum + i.credits, 0));
      }

      // Display separate success messages for each invite type
      const individualCount = formData.individual_members.length;
      const teamLeaderCount = formData.team_leaders.length;
      const adminCount = formData.organization_admins.length;

      const counts = [];
      if (individualCount > 0) counts.push(`${individualCount} member(s)`);
      if (teamLeaderCount > 0) counts.push(`${teamLeaderCount} team leader(s)`);
      if (adminCount > 0) counts.push(`${adminCount} admin(s)`);

      if (counts.length > 0) {
        toast.success(`Successfully invited ${counts.join(', ')}`);
      }

      // Call success callback if provided
      if (onInviteSuccess) {
        onInviteSuccess();
      }
    } catch (error) {
      console.error('Error inviting users:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to send invitations';

      // Handle insufficient credits error
      try {
        const errorData = JSON.parse(errorMessage);
        if (errorData.code === 'insufficient_credits') {
          setInsufficientCreditsError(errorData);
          setIsInsufficientCreditsModalOpen(true);
          return;
        }
      } catch (e) {
        // Not a JSON error or doesn't have the expected format
      }

      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Clear all inputs
  const handleClearInputs = () => {
    setFormData({
      individual_members: [],
      team_leaders: [],
      organization_admins: [],
    });
    setIndividualEmailInput('');
    setTeamLeaderEmailInput('');
    setOrgAdminEmailInput('');
    setErrors({});
    setShowSuccess(false);
    setSentInvitations([]);
    toast.success('Form cleared');
  };

  // Handle key press for email inputs
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>, type: 'individual' | 'team_leader' | 'org_admin') => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (type === 'individual') {
        handleAddIndividualEmail();
      } else if (type === 'team_leader') {
        handleAddTeamLeaderEmail();
      } else {
        handleAddOrgAdminEmail();
      }
    }
  };

  // Clear all emails of a type
  const handleClearAll = (type: 'individual' | 'team_leader' | 'org_admin') => {
    if (type === 'individual') {
      setFormData(prev => ({ ...prev, individual_members: [] }));
      toast.success('All individual members cleared');
    } else if (type === 'team_leader') {
      setFormData(prev => ({ ...prev, team_leaders: [] }));
      toast.success('All team leaders cleared');
    } else {
      setFormData(prev => ({ ...prev, organization_admins: [] }));
      toast.success('All organization admins cleared');
    }
  };

  // Open cohort modal and fetch cohorts
  const handleOpenCohortModal = async () => {
    setIsCohortModalOpen(true);
    setIsLoadingCohorts(true);

    try {
      const token = authService.getCurrentToken();
      if (!token) {
        toast.error('Authentication required');
        return;
      }

      const fetchedCohorts = await fetchCohorts(organizationId, token);
      setCohorts(fetchedCohorts.filter(c => c.is_active));
    } catch (error) {
      console.error('Error fetching cohorts:', error);
      toast.error('Failed to load cohorts');
    } finally {
      setIsLoadingCohorts(false);
    }
  };

  // Handle cohort selection
  const handleSelectCohort = (cohort: Cohort) => {
    setSelectedCohort(cohort);
    setIsCohortModalOpen(false);
    toast.success(`Selected cohort: ${cohort.name}`);
  };

  // Clear selected cohort
  const handleClearCohort = () => {
    setSelectedCohort(null);
    toast.success('Cohort selection cleared');
  };

  // Handle cohort creation success - refresh cohorts list
  const handleCohortCreated = async () => {
    try {
      const token = authService.getCurrentToken();
      if (!token) return;

      const fetchedCohorts = await fetchCohorts(organizationId, token);
      const activeCohorts = fetchedCohorts.filter(c => c.is_active);
      setCohorts(activeCohorts);

      // Auto-select the newly created cohort (most recent one)
      if (activeCohorts.length > 0) {
        const newestCohort = activeCohorts[activeCohorts.length - 1];
        setSelectedCohort(newestCohort);
        toast.success(`Cohort "${newestCohort.name}" selected`);
      }
    } catch (error) {
      console.error('Error refreshing cohorts:', error);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <AnimatePresence mode="wait">
        {!showSuccess ? (
          <motion.div
            key="form"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="border-gray-200 dark:border-gray-800 shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden">
              {/* Header with gradient accent */}
              <div className="bg-gradient-to-r from-brand-50 to-brand-50 dark:from-brand-950/30 dark:to-brand-950/30 border-y border-brand-100 dark:border-brand-900/50 px-4 py-2">
                <div className="flex items-center justify-between">
                  <Badge variant="outline" className="font-medium text-brand-500 dark:text-brand-400 bg-brand-25 dark:bg-brand-800/50 py-1 px-8 border-brand-100 dark:border-brand-800 text-sm">
                    Add members and team leaders to {organizationName || 'your organization'}
                  </Badge>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="font-medium text-brand-600 dark:text-brand-400 bg-white dark:bg-gray-800 py-1.5 px-3 border-brand-200 dark:border-brand-700">
                      <FileText className="w-3.5 h-3.5 mr-1.5" />
                      {totalCreditsRequired.toLocaleString()} Credits
                    </Badge>
                    <Badge variant="outline" className="font-medium text-brand-600 dark:text-brand-400 bg-white dark:bg-gray-800 py-1.5 px-3 border-brand-200 dark:border-brand-700">
                      <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                      {formData.individual_members.length + formData.team_leaders.length + formData.organization_admins.length} Pending
                    </Badge>
                  </div>
                </div>
              </div>

              <CardContent className="px-6 -mt-2">
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* Compact Credit Summary - Only shown for grant_org */}
                  {currentOrganization?.type === 'grant_org' && currentOrganization.monthly_credit_limit && (
                    <div className="flex items-center gap-4 p-3 bg-gradient-to-r from-brand-50/50 to-brand-50/50 dark:from-brand-950/20 dark:to-brand-950/20 rounded-xl border border-brand-100 dark:border-brand-900/30">
                      <div className="flex-1 flex items-center gap-6">
                        <div className="flex items-center gap-4">
                          <div>
                            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Used</p>
                            <p className="text-base font-semibold text-gray-700 dark:text-gray-300">{(metrics?.credits?.used || 0).toLocaleString()}</p>
                          </div>
                          <div className="h-8 w-px bg-gray-200 dark:bg-gray-700" />
                          <div>
                            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Remaining</p>
                            <p className={`text-base font-semibold ${remainingCredits && remainingCredits < 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                              {remainingCredits ? remainingCredits.toLocaleString() : 'N/A'}
                            </p>
                          </div>
                        </div>
                        <div className="flex-1 max-w-[180px]">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-gray-500 dark:text-gray-400">Usage</span>
                            <span className={`font-medium ${creditUsagePercentage > 90 ? 'text-red-600' : creditUsagePercentage > 75 ? 'text-amber-600' : 'text-green-600'}`}>
                              {creditUsagePercentage.toFixed(0)}%
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full transition-all duration-500 ${creditUsagePercentage > 90 ? 'bg-red-500' : creditUsagePercentage > 75 ? 'bg-amber-500' : 'bg-green-500'}`}
                              style={{ width: `${Math.min(creditUsagePercentage, 100)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Warning for limit exceeded */}
                  <AnimatePresence>
                    {isLimitExceeded && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl"
                      >
                        <div className="flex items-start gap-3">
                          <div className="p-1.5 bg-red-100 dark:bg-red-900/50 rounded-lg">
                            <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-semibold text-red-700 dark:text-red-400">Credit Limit Exceeded</h4>
                            <p className="text-sm text-red-600 dark:text-red-300 mt-0.5">
                              Total credits ({totalCreditsRequired.toLocaleString()}) exceed your remaining monthly limit. Reduce invitees or adjust allocations.
                            </p>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>


                  {/* Enhanced Tab Navigation */}
                  <div className="relative">
                    <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800/80 rounded-xl">
                      <button
                        type="button"
                        onClick={() => setActiveSection('individual')}
                        className={`relative flex items-center justify-center gap-2 flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${activeSection === 'individual'
                          ? 'bg-white dark:bg-gray-700 text-brand-600 dark:text-brand-400 shadow-sm'
                          : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-white/50 dark:hover:bg-gray-700/50'
                          }`}
                      >
                        <Users className={`w-4 h-4 ${activeSection === 'individual' ? 'text-brand-500' : ''}`} />
                        <span>Individual Members</span>
                        {formData.individual_members.length > 0 && (
                          <Badge
                            variant={activeSection === 'individual' ? 'default' : 'secondary'}
                            className={`ml-1 ${activeSection === 'individual' ? 'bg-brand-500 text-white' : ''}`}
                          >
                            {formData.individual_members.length}
                          </Badge>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => setActiveSection('team_leader')}
                        className={`relative flex items-center justify-center gap-2 flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${activeSection === 'team_leader'
                          ? 'bg-white dark:bg-gray-700 text-amber-600 dark:text-amber-400 shadow-sm'
                          : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-white/50 dark:hover:bg-gray-700/50'
                          }`}
                      >
                        <Crown className={`w-4 h-4 ${activeSection === 'team_leader' ? 'text-amber-500' : ''}`} />
                        <span>Team Leaders</span>
                        {formData.team_leaders.length > 0 && (
                          <Badge
                            variant={activeSection === 'team_leader' ? 'default' : 'secondary'}
                            className={`ml-1 ${activeSection === 'team_leader' ? 'bg-amber-500 text-white' : ''}`}
                          >
                            {formData.team_leaders.length}
                          </Badge>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => setActiveSection('org_admin')}
                        className={`relative flex items-center justify-center gap-2 flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${activeSection === 'org_admin'
                          ? 'bg-white dark:bg-gray-700 text-rose-600 dark:text-rose-400 shadow-sm'
                          : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-white/50 dark:hover:bg-gray-700/50'
                          }`}
                      >
                        <ShieldCheck className={`w-4 h-4 ${activeSection === 'org_admin' ? 'text-rose-500' : ''}`} />
                        <span>Org Admins</span>
                        {formData.organization_admins.length > 0 && (
                          <Badge
                            variant={activeSection === 'org_admin' ? 'default' : 'secondary'}
                            className={`ml-1 ${activeSection === 'org_admin' ? 'bg-rose-500 text-white' : ''}`}
                          >
                            {formData.organization_admins.length}
                          </Badge>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Individual Members Section */}
                  <AnimatePresence mode="wait">
                    {activeSection === 'individual' && (
                      <motion.div
                        key="individual"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                        className="space-y-4"
                      >
                        {/* Input Section Card */}
                        <div className="p-4 bg-gray-50/50 dark:bg-gray-800/30 rounded-xl border border-gray-100 dark:border-gray-800">
                          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                            {/* Email Input - Takes more space */}
                            <div className="lg:col-span-3 space-y-1.5">
                              <Label htmlFor="individual-email" className="text-sm text-brand-500 dark:text-brand-400 font-medium flex items-center gap-2">
                                <Mail className="w-3.5 h-3.5 text-brand-400" />
                                Email Addresses
                              </Label>
                              <div className="flex gap-2">
                                <Input
                                  id="individual-email"
                                  type="text"
                                  placeholder="Enter emails..."
                                  value={individualEmailInput}
                                  onChange={(e) => setIndividualEmailInput(e.target.value)}
                                  onKeyPress={(e) => handleKeyPress(e, 'individual')}
                                  disabled={isLoading}
                                  className="flex-1 bg-white dark:bg-gray-800"
                                />
                                <Button
                                  type="button"
                                  onClick={handleAddIndividualEmail}
                                  disabled={isLoading || !individualEmailInput.trim()}
                                  size="default"
                                >
                                  <Plus className="w-4 h-4 mr-1" />
                                  Add
                                </Button>
                              </div>
                            </div>

                            {/* Default Package */}
                            <div className="lg:col-span-2 space-y-1.5">
                              <Label htmlFor="individual-package" className="text-sm text-brand-500 dark:text-brand-400 font-medium flex items-center gap-2">
                                <FileText className="w-3.5 h-3.5 text-brand-400" />
                                Default Package
                              </Label>
                              <Select
                                value={defaultIndividualCredits.toString()}
                                onValueChange={(value) => setDefaultIndividualCredits(parseInt(value, 10))}
                                disabled={isLoading}
                              >
                                <SelectTrigger id="individual-package" className="w-full bg-white dark:bg-gray-800">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {INDIVIDUAL_PACKAGES.map(credits => (
                                    <SelectItem key={credits} value={credits.toString()}>
                                      {credits} credits
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                          </div>

                          {/* CSV Actions - Inline */}
                          <div className="flex items-center gap-3 mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                            <span className="text-xs text-gray-500 dark:text-gray-400">Bulk Import:</span>
                            <Label
                              htmlFor="individual-csv"
                              className="cursor-pointer flex items-center gap-1.5 text-xs text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-medium transition-colors"
                            >
                              <Upload className="w-3.5 h-3.5" />
                              Upload CSV
                            </Label>
                            <input
                              id="individual-csv"
                              type="file"
                              accept=".csv"
                              onChange={(e) => handleCSVUpload(e, 'individual')}
                              className="hidden"
                              disabled={isLoading}
                            />
                            <span className="text-gray-300 dark:text-gray-600">|</span>
                            <button
                              type="button"
                              onClick={() => handleDownloadTemplate('individual')}
                              className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 font-medium transition-colors"
                              disabled={isLoading}
                            >
                              <Download className="w-3.5 h-3.5" />
                              Template
                            </button>
                            {formData.individual_members.length > 0 && (
                              <>
                                <span className="text-gray-300 dark:text-gray-600">|</span>
                                <button
                                  type="button"
                                  onClick={() => handleClearAll('individual')}
                                  className="flex items-center gap-1.5 text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium transition-colors"
                                  disabled={isLoading}
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                  Clear All
                                </button>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Email List - Table Style */}
                        {formData.individual_members.length > 0 ? (
                          <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                            {/* Table Header */}
                            <div className="flex items-center gap-3 px-4 py-2.5 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700 text-xs font-medium text-brand-500 dark:text-brand-400 uppercase tracking-wide">
                              <div className="flex-1">Email Address</div>
                              <div className="w-32 text-center">Can Skip Module 3</div>
                              <div className="w-32 text-center">Credits</div>
                              <div className="w-10"></div>
                            </div>
                            {/* Table Body */}
                            <div className="divide-y divide-gray-100 dark:divide-gray-800 max-h-[280px] overflow-y-auto">
                              {formData.individual_members.map((member, index) => (
                                <motion.div
                                  key={member.email}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: index * 0.03 }}
                                  className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-900/50 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group"
                                >
                                  <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/50 flex items-center justify-center flex-shrink-0">
                                      <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase">
                                        {member.email.charAt(0)}
                                      </span>
                                    </div>
                                    <span className="text-sm text-gray-900 dark:text-gray-100 truncate">{member.email}</span>
                                  </div>
                                  <div className="w-32 flex justify-center">
                                    <Switch
                                      checked={member.can_skip_modules}
                                      onCheckedChange={(checked) => handleUpdateIndividualSkip(member.email, checked)}
                                      disabled={isLoading}
                                      className="scale-90"
                                    />
                                  </div>
                                  <Select
                                    value={member.credits.toString()}
                                    onValueChange={(value) => handleUpdateIndividualCredits(member.email, parseInt(value, 10))}
                                    disabled={isLoading}
                                  >
                                    <SelectTrigger className="w-32 h-8 text-sm">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {INDIVIDUAL_PACKAGES.map(credits => (
                                        <SelectItem key={credits} value={credits.toString()}>
                                          {credits} credits
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handleRemoveIndividualEmail(member.email)}
                                    className="h-8 w-8 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-opacity"
                                    disabled={isLoading}
                                  >
                                    <X className="w-4 h-4" />
                                  </Button>
                                </motion.div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center justify-center py-12 text-center border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-xl">
                            <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-full mb-3">
                              <Users className="w-6 h-6 text-gray-400" />
                            </div>
                            <p className="text-sm font-medium text-brand-500 dark:text-gray-100">No members added yet</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Enter email addresses above or upload a CSV file</p>
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Team Leaders Section */}
                  <AnimatePresence mode="wait">
                    {activeSection === 'team_leader' && (
                      <motion.div
                        key="team_leader"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                        className="space-y-4"
                      >
                        {/* Input Section Card */}
                        <div className="p-4 bg-amber-50/50 dark:bg-amber-900/10 rounded-xl border border-amber-100 dark:border-amber-900/30">
                          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                            {/* Email Input - Takes more space */}
                            <div className="lg:col-span-3 space-y-1.5">
                              <Label htmlFor="team-leader-email" className="text-sm font-medium flex items-center gap-2">
                                <Mail className="w-3.5 h-3.5 text-gray-400" />
                                Email Addresses
                              </Label>
                              <div className="flex gap-2">
                                <Input
                                  id="team-leader-email"
                                  type="text"
                                  placeholder="Enter emails..."
                                  value={teamLeaderEmailInput}
                                  onChange={(e) => setTeamLeaderEmailInput(e.target.value)}
                                  onKeyPress={(e) => handleKeyPress(e, 'team_leader')}
                                  disabled={isLoading}
                                  className="flex-1 bg-white dark:bg-gray-800"
                                />
                                <Button
                                  type="button"
                                  onClick={handleAddTeamLeaderEmail}
                                  disabled={isLoading || !teamLeaderEmailInput.trim()}
                                  size="default"
                                  className="bg-amber-600 hover:bg-amber-700"
                                >
                                  <Plus className="w-4 h-4 mr-1" />
                                  Add
                                </Button>
                              </div>
                            </div>

                            {/* Default Package */}
                            <div className="lg:col-span-2 space-y-1.5">
                              <Label htmlFor="team-leader-package" className="text-sm font-medium flex items-center gap-2">
                                <FileText className="w-3.5 h-3.5 text-gray-400" />
                                Default Package
                              </Label>
                              <Select
                                value={defaultTeamLeaderCredits.toString()}
                                onValueChange={(value) => setDefaultTeamLeaderCredits(parseInt(value, 10))}
                                disabled={isLoading}
                              >
                                <SelectTrigger id="team-leader-package" className="w-full bg-white dark:bg-gray-800">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {TEAM_LEADER_PACKAGES.map(credits => (
                                    <SelectItem key={credits} value={credits.toString()}>
                                      {credits} credits
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                          </div>

                          {/* CSV Actions - Inline */}
                          <div className="flex items-center gap-3 mt-3 pt-3 border-t border-amber-200 dark:border-amber-800/30">
                            <span className="text-xs text-gray-500 dark:text-gray-400">Bulk Import:</span>
                            <Label
                              htmlFor="team-leader-csv"
                              className="cursor-pointer flex items-center gap-1.5 text-xs text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300 font-medium transition-colors"
                            >
                              <Upload className="w-3.5 h-3.5" />
                              Upload CSV
                            </Label>
                            <input
                              id="team-leader-csv"
                              type="file"
                              accept=".csv"
                              onChange={(e) => handleCSVUpload(e, 'team_leader')}
                              className="hidden"
                              disabled={isLoading}
                            />
                            <span className="text-gray-300 dark:text-gray-600">|</span>
                            <button
                              type="button"
                              onClick={() => handleDownloadTemplate('team_leader')}
                              className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 font-medium transition-colors"
                              disabled={isLoading}
                            >
                              <Download className="w-3.5 h-3.5" />
                              Template
                            </button>
                            {formData.team_leaders.length > 0 && (
                              <>
                                <span className="text-gray-300 dark:text-gray-600">|</span>
                                <button
                                  type="button"
                                  onClick={() => handleClearAll('team_leader')}
                                  className="flex items-center gap-1.5 text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium transition-colors"
                                  disabled={isLoading}
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                  Clear All
                                </button>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Email List - Table Style */}
                        {formData.team_leaders.length > 0 ? (
                          <div className="border border-amber-200 dark:border-amber-800/30 rounded-xl overflow-hidden">
                            {/* Table Header */}
                            <div className="flex items-center gap-3 px-4 py-2.5 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800/30 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                              <div className="flex-1">Email Address</div>
                              <div className="w-32 text-center">Can Skip Module 3</div>
                              <div className="w-32 text-center">Credits</div>
                              <div className="w-10"></div>
                            </div>
                            {/* Table Body */}
                            <div className="divide-y divide-amber-100 dark:divide-amber-900/20 max-h-[280px] overflow-y-auto">
                              {formData.team_leaders.map((leader, index) => (
                                <motion.div
                                  key={leader.email}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: index * 0.03 }}
                                  className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-900/50 hover:bg-amber-50/50 dark:hover:bg-amber-900/10 transition-colors group"
                                >
                                  <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <div className="w-8 h-8 rounded-full bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center flex-shrink-0">
                                      <Crown className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                                    </div>
                                    <span className="text-sm text-gray-900 dark:text-gray-100 truncate">{leader.email}</span>
                                  </div>
                                  <div className="w-32 flex justify-center">
                                    <Switch
                                      checked={leader.can_skip_modules}
                                      onCheckedChange={(checked) => handleUpdateTeamLeaderSkip(leader.email, checked)}
                                      disabled={isLoading}
                                      className="scale-90 data-[state=checked]:bg-amber-600"
                                    />
                                  </div>
                                  <Select
                                    value={leader.credits.toString()}
                                    onValueChange={(value) => handleUpdateTeamLeaderCredits(leader.email, parseInt(value, 10))}
                                    disabled={isLoading}
                                  >
                                    <SelectTrigger className="w-32 h-8 text-sm">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {TEAM_LEADER_PACKAGES.map(credits => (
                                        <SelectItem key={credits} value={credits.toString()}>
                                          {credits} credits
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handleRemoveTeamLeaderEmail(leader.email)}
                                    className="h-8 w-8 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-opacity"
                                    disabled={isLoading}
                                  >
                                    <X className="w-4 h-4" />
                                  </Button>
                                </motion.div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center justify-center py-12 text-center border-2 border-dashed border-amber-200 dark:border-amber-800/30 rounded-xl">
                            <div className="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-full mb-3">
                              <Crown className="w-6 h-6 text-amber-500" />
                            </div>
                            <p className="text-sm font-medium text-brand-500 dark:text-gray-100">No team leaders added yet</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Enter email addresses above or upload a CSV file</p>
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Organization Admins Section */}
                  <AnimatePresence mode="wait">
                    {activeSection === 'org_admin' && (
                      <motion.div
                        key="org_admin"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                        className="space-y-4"
                      >
                        {/* Input Section Card */}
                        <div className="p-4 bg-rose-50/50 dark:bg-rose-900/10 rounded-xl border border-rose-100 dark:border-rose-900/30">
                          <div className="grid grid-cols-1 gap-4">
                            <div className="space-y-1.5">
                              <Label htmlFor="org-admin-email" className="text-sm font-medium flex items-center gap-2 text-rose-600 dark:text-rose-400">
                                <Mail className="w-3.5 h-3.5" />
                                Admin Email Addresses
                              </Label>
                              <div className="flex gap-2">
                                <Input
                                  id="org-admin-email"
                                  type="text"
                                  placeholder="Enter admin emails..."
                                  value={orgAdminEmailInput}
                                  onChange={(e) => setOrgAdminEmailInput(e.target.value)}
                                  onKeyPress={(e) => handleKeyPress(e, 'org_admin')}
                                  disabled={isLoading}
                                  className="flex-1 bg-white dark:bg-gray-800"
                                />
                                <Button
                                  type="button"
                                  onClick={handleAddOrgAdminEmail}
                                  disabled={isLoading || !orgAdminEmailInput.trim()}
                                  size="default"
                                  className="bg-rose-600 hover:bg-rose-700"
                                >
                                  <Plus className="w-4 h-4 mr-1" />
                                  Add
                                </Button>
                              </div>
                            </div>
                          </div>

                          {/* CSV Actions - Inline */}
                          <div className="flex items-center gap-3 mt-3 pt-3 border-t border-rose-200 dark:border-rose-800/30">
                            <span className="text-xs text-gray-500 dark:text-gray-400">Bulk Import:</span>
                            <Label
                              htmlFor="org-admin-csv"
                              className="cursor-pointer flex items-center gap-1.5 text-xs text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300 font-medium transition-colors"
                            >
                              <Upload className="w-3.5 h-3.5" />
                              Upload CSV
                            </Label>
                            <input
                              id="org-admin-csv"
                              type="file"
                              accept=".csv"
                              onChange={(e) => handleCSVUpload(e, 'org_admin')}
                              className="hidden"
                              disabled={isLoading}
                            />
                            <span className="text-gray-300 dark:text-gray-600">|</span>
                            <button
                              type="button"
                              onClick={() => handleDownloadTemplate('org_admin')}
                              className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 font-medium transition-colors"
                              disabled={isLoading}
                            >
                              <Download className="w-3.5 h-3.5" />
                              Template
                            </button>
                            {formData.organization_admins.length > 0 && (
                              <>
                                <span className="text-gray-300 dark:text-gray-600">|</span>
                                <button
                                  type="button"
                                  onClick={() => handleClearAll('org_admin')}
                                  className="flex items-center gap-1.5 text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium transition-colors"
                                  disabled={isLoading}
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                  Clear All
                                </button>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Email List - Table Style */}
                        {formData.organization_admins.length > 0 ? (
                          <div className="border border-rose-200 dark:border-rose-800/30 rounded-xl overflow-hidden">
                            {/* Table Header */}
                            <div className="flex items-center gap-3 px-4 py-2.5 bg-rose-50 dark:bg-rose-900/20 border-b border-rose-200 dark:border-rose-800/30 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                              <div className="flex-1">Email Address</div>
                              <div className="w-32 text-center">Role</div>
                              <div className="w-10"></div>
                            </div>
                            {/* Table Body */}
                            <div className="divide-y divide-rose-100 dark:divide-rose-900/20 max-h-[280px] overflow-y-auto">
                              {formData.organization_admins.map((admin, index) => (
                                <motion.div
                                  key={admin.email}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: index * 0.03 }}
                                  className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-900/50 hover:bg-rose-50/50 dark:hover:bg-rose-900/10 transition-colors group"
                                >
                                  <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <div className="w-8 h-8 rounded-full bg-rose-100 dark:bg-rose-900/50 flex items-center justify-center flex-shrink-0">
                                      <ShieldCheck className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                                    </div>
                                    <span className="text-sm text-gray-900 dark:text-gray-100 truncate">{admin.email}</span>
                                  </div>
                                  <div className="w-32 flex justify-center">
                                    <Badge variant="outline" className="text-rose-600 border-rose-200">Admin</Badge>
                                  </div>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handleRemoveOrgAdminEmail(admin.email)}
                                    className="h-8 w-8 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-opacity"
                                    disabled={isLoading}
                                  >
                                    <X className="w-4 h-4" />
                                  </Button>
                                </motion.div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center justify-center py-12 text-center border-2 border-dashed border-rose-200 dark:border-rose-800/30 rounded-xl">
                            <div className="p-3 bg-rose-100 dark:bg-rose-900/30 rounded-full mb-3">
                              <ShieldCheck className="w-6 h-6 text-rose-500" />
                            </div>
                            <p className="text-sm font-medium text-brand-500 dark:text-gray-100">No admins added yet</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Enter admin email addresses above or upload a CSV file</p>
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>



                  {/* Cohort Selector - Only show if not just inviting admins */}
                  {(activeSection !== 'org_admin' || formData.individual_members.length > 0 || formData.team_leaders.length > 0) && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="flex items-center justify-between p-3 bg-gray-50/80 dark:bg-gray-800/40 rounded-xl border border-gray-100 dark:border-gray-800"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-emerald-100 dark:bg-emerald-900/50 rounded-lg">
                          <FolderOpen className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                        </div>
                        <div>
                          <Label className="text-sm font-medium text-brand-500 dark:text-gray-100">
                            Assign to Cohort {(formData.individual_members.length > 0 || formData.team_leaders.length > 0) && <span className="text-red-500">*</span>}
                          </Label>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {selectedCohort
                              ? `Non-admin invitees will be added to "${selectedCohort.name}"`
                              : 'Select a cohort for members and team leaders'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {selectedCohort && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={handleClearCohort}
                            className="h-8 px-2 text-gray-400 hover:text-red-600"
                            disabled={isLoading}
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        )}
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleOpenCohortModal}
                          disabled={isLoading}
                          className="h-9 text-brand-500"
                        >
                          {selectedCohort ? (
                            <div className="flex items-center gap-2">
                              <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: selectedCohort.color || '#10b981' }}
                              />
                              <span className="max-w-[120px] truncate">{selectedCohort.name}</span>
                            </div>
                          ) : (
                            <>
                              <FolderOpen className="w-4 h-4 mr-1.5" />
                              Select Cohort
                            </>
                          )}
                        </Button>
                      </div>
                    </motion.div>
                  )}

                  {/* Enhanced Action Footer */}
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-5 mt-2 border-t border-gray-200 dark:border-gray-700">
                    {/* Summary Stats */}
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-50 dark:bg-brand-900/30 rounded-lg">
                          <Users className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                          <span className="text-sm font-medium text-brand-700 dark:text-brand-300">{formData.individual_members.length}</span>
                        </div>
                        <span className="text-gray-400">+</span>
                        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/30 rounded-lg">
                          <Crown className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                          <span className="text-sm font-medium text-amber-700 dark:text-brand-300">{formData.team_leaders.length}</span>
                        </div>
                        <span className="text-gray-400">+</span>
                        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 dark:bg-rose-900/30 rounded-lg">
                          <ShieldCheck className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                          <span className="text-sm font-medium text-rose-700 dark:text-brand-300">{formData.organization_admins.length}</span>
                        </div>
                        <span className="text-gray-400">=</span>
                        <div className="text-sm font-semibold text-gray-900 dark:text-white">
                          {formData.individual_members.length + formData.team_leaders.length + formData.organization_admins.length} invites
                        </div>
                      </div>
                      <div className="h-5 w-px bg-gray-200 dark:bg-gray-700 hidden sm:block" />
                      <div className="text-sm text-gray-600 dark:text-gray-400 hidden sm:block">
                        <span className="font-semibold text-gray-900 dark:text-white">{totalCreditsRequired.toLocaleString()}</span> credits total
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3">
                      <Button
                        type="button"
                        variant="outline"
                        size="default"
                        onClick={handleClearInputs}
                        disabled={isLoading || (formData.individual_members.length === 0 && formData.team_leaders.length === 0 && formData.organization_admins.length === 0)}
                        className="text-gray-600 hover:text-gray-900"
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Reset
                      </Button>
                      <Button
                        type="submit"
                        size="default"
                        disabled={isLoading || isLimitExceeded || (formData.individual_members.length === 0 && formData.team_leaders.length === 0 && formData.organization_admins.length === 0)}
                        className="min-w-[160px] bg-brand-500 hover:bg-brand-600"
                      >
                        {isLoading ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Sending...
                          </>
                        ) : (
                          <>
                            <Send className="w-4 h-4 mr-2" />
                            Send Invitations
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </form>
              </CardContent>
            </Card>
          </motion.div>
        ) : (
          <motion.div
            key="success"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="border-green-200 dark:border-green-800 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20">
              <CardHeader className="text-center pb-4">
                {/* <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mb-4">
                  <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
                </div> */}
                <CardTitle className="flex items-center justify-center gap-2 text-green-600 dark:text-green-400 text-2xl">
                  Invitations Sent Successfully!
                </CardTitle>
                <CardDescription className="text-md">
                  {sentInvitations.length} invitation(s) have been sent to join {organizationName || 'your organization'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-white dark:bg-gray-800 rounded-lg border border-green-200 dark:border-green-800">
                    <div className="text-2xl font-bold text-brand-600 dark:text-brand-400">
                      {sentInvitations.filter(i => !i.is_team_leader && !i.is_admin).length}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Individual Members</div>
                  </div>
                  <div className="text-center p-4 bg-white dark:bg-gray-800 rounded-lg border border-yellow-200 dark:border-yellow-800">
                    <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                      {sentInvitations.filter(i => i.is_team_leader).length}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Team Leaders</div>
                  </div>
                  <div className="text-center p-4 bg-white dark:bg-gray-800 rounded-lg border border-rose-200 dark:border-rose-800">
                    <div className="text-2xl font-bold text-rose-600 dark:text-rose-400">
                      {sentInvitations.filter(i => i.is_admin).length}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Org Admins</div>
                  </div>
                  <div className="text-center p-4 bg-white dark:bg-gray-800 rounded-lg border border-blue-200 dark:border-blue-800">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                      {sentInvitations.reduce((sum, i) => sum + i.credits, 0).toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Total Credits</div>
                  </div>
                </div>

                {/* Invitation List */}
                <div className="space-y-3">
                  <h3 className="font-semibold text-brand-500 dark:text-brand-400 text-lg">
                    Sent Invitations
                  </h3>
                  <div className="max-h-[400px] overflow-y-auto space-y-2">
                    {sentInvitations.map((invite, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-sm transition-shadow"
                      >
                        <div className="flex items-center gap-3">
                          {invite.is_admin ? (
                            <ShieldCheck className="w-5 h-5 text-rose-500" />
                          ) : invite.is_team_leader ? (
                            <Crown className="w-5 h-5 text-yellow-500" />
                          ) : (
                            <Users className="w-5 h-5 text-brand-500" />
                          )}
                          <div>
                            <p className="font-medium text-gray-900 dark:text-white">{invite.email}</p>
                            <p className="text-sm text-muted-foreground">
                              {invite.is_admin ? 'Organization Admin' : (invite.is_team_leader ? 'Team Leader' : 'Individual Member')}
                            </p>
                          </div>
                        </div>
                        <Badge variant={invite.is_admin ? "outline" : (invite.is_team_leader ? "default" : "secondary")} className={`text-sm ${invite.is_admin ? 'text-rose-600 border-rose-200' : ''}`}>
                          {invite.credits} credits
                        </Badge>
                      </motion.div>
                    ))}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row justify-center gap-3 pt-4">
                  <Button
                    variant="outline"
                    onClick={() => {
                      // Navigate to organization dashboard instead of reloading
                      if (typeof window !== 'undefined') {
                        window.location.href = '/organization';
                      }
                    }}
                    className="flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4" />
                    View Organization Dashboard
                  </Button>
                  <Button
                    onClick={handleClearInputs}
                    className="flex items-center gap-2"
                  >
                    <Send className="w-4 h-4" />
                    Send More Invites
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Insufficient Credits Modal */}
      <Dialog open={isInsufficientCreditsModalOpen} onOpenChange={setIsInsufficientCreditsModalOpen}>
        <DialogContent className="sm:max-w-md border-red-100 dark:border-red-900/30">
          <DialogHeader className="bg-red-50 dark:bg-red-950/30 px-6 py-4 border-b border-red-100 dark:border-red-900/50 -mx-6 -mt-6 mb-4 rounded-t-lg">
            <DialogTitle className="text-lg font-semibold text-red-600 dark:text-red-400">
              Insufficient Credits
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-600 dark:text-gray-400">
              {insufficientCreditsError?.message || "Your organization doesn't have enough credits to complete this action."}
            </DialogDescription>
          </DialogHeader>

          <div className="bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/20 dark:to-orange-950/20 border border-amber-200 dark:border-amber-800/50 rounded-xl p-5 mt-2">
            <div className="flex gap-4">
              <div className="w-10 h-10 bg-amber-100 dark:bg-amber-900/50 rounded-lg flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div className="text-sm">
                <p className="font-semibold text-amber-900 dark:text-amber-200 mb-2">Recommended Actions:</p>
                <ul className="space-y-2 text-amber-800/80 dark:text-amber-300/80">
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                    <span>Reduce the number of members or team leaders being invited.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                    <span>Decrease the credit allocation for individual invites.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                    <span>Contact your organization owner to top up available credits.</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <DialogFooter className="sm:justify-center gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsInsufficientCreditsModalOpen(false)}
              className="w-full sm:w-auto h-9 px-8 rounded-lg border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Close
            </Button>
            <Button
              type="button"
              onClick={() => {
                setIsInsufficientCreditsModalOpen(false);
                router.push('/organization/credits');
              }}
              className="w-full sm:w-auto h-9 px-8 rounded-lg bg-brand-500 hover:bg-brand-600 text-white font-medium shadow-sm hover:shadow-md transition-all"
            >
              Adjust Allocations
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Cohort Selection Modal */}
      <Dialog open={isCohortModalOpen} onOpenChange={setIsCohortModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader className="bg-brand-25 dark:bg-brand-950/30 px-6 py-4 border-b border-brand-100 dark:border-brand-900/50 -mx-6 -mt-6 mb-4 rounded-t-lg">
            <DialogTitle className="text-lg font-semibold text-brand-500 dark:text-white">
              Select a Cohort
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-600 dark:text-gray-400">
              Choose a cohort to assign all invitees to
            </DialogDescription>
          </DialogHeader>

          <div className="max-h-[320px] overflow-y-auto">
            {isLoadingCohorts ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-brand-500 animate-spin mb-3" />
                <p className="text-sm text-gray-500 dark:text-gray-400">Loading cohorts...</p>
              </div>
            ) : cohorts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-full mb-3">
                  <FolderOpen className="w-6 h-6 text-gray-400" />
                </div>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">No cohorts found</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Create cohorts in the Cohorts section first
                </p>

                <Button
                  type="button"
                  variant="outline"
                  className="w-full h-9 mt-4 text-brand-500 border-brand-200 hover:bg-brand-50"
                  onClick={() => setIsCreateCohortModalOpen(true)}
                >
                  <Plus className="w-4 h-4 mr-1.5" />
                  Create Cohort
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {cohorts.map((cohort) => (
                  <button
                    key={cohort.id}
                    type="button"
                    onClick={() => handleSelectCohort(cohort)}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all duration-200 text-left ${selectedCohort?.id === cohort.id
                      ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-emerald-300 dark:hover:border-emerald-700 hover:bg-gray-50 dark:hover:bg-gray-800/50'
                      }`}
                  >
                    <div
                      className="w-4 h-4 rounded-full flex-shrink-0"
                      style={{ backgroundColor: cohort.color || '#10b981' }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {cohort.name}
                      </p>
                      {cohort.description && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                          {cohort.description}
                        </p>
                      )}
                    </div>
                    {selectedCohort?.id === cohort.id && (
                      <Check className="w-5 h-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          <DialogFooter className="sm:justify-between items-center gap-3 pt-4 border-t border-gray-100 dark:border-gray-800 mt-4">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setSelectedCohort(null);
                setIsCohortModalOpen(false);
              }}
              className="text-gray-500 hover:text-gray-700 h-9"
            >
              Clear Selection
            </Button>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsCohortModalOpen(false)}
                className="h-9 px-6"
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={() => setIsCreateCohortModalOpen(true)}
                className="h-9 bg-brand-500 hover:bg-brand-600 text-white"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                Create New
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Cohort Modal */}
      <CreateCohortModal
        isOpen={isCreateCohortModalOpen}
        onOpenChange={setIsCreateCohortModalOpen}
        tenantId={organizationId}
        token={authService.getCurrentToken() || ''}
        onSuccess={handleCohortCreated}
      />
    </div>
  );
};

export default MemberInviteForm;