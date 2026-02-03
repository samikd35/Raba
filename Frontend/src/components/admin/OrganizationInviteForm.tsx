'use client';

import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { z } from 'zod';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import { organizationService } from '@/lib/api/organizationService';
import { OrganizationInviteRequest, OrganizationInviteResponse } from '@/types/organization';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
  Loader2,
  CheckCircle,
  AlertCircle,
  Mail,
  CreditCard,
  Building2,
  Send,
  RefreshCw,
  Copy,
  Check,
  Sparkles,
  Gift,
  Wallet,
  Calendar,
  ShieldCheck,
  Layers,
  History
} from 'lucide-react';
import Badge from '@/components/ui/badge/Badge';

// Zod validation schema
const organizationInviteSchema = z.object({
  email: z.string().email('Invalid email address'),
  organization_type: z.enum(['prepay_org', 'grant_org', 'postpay_org']),
  monthly_credit_limit: z.number()
    .int('Must be a whole number')
    .positive('Must be greater than 0')
    .optional(),
}).refine(
  (data) => {
    if (data.organization_type === 'grant_org') {
      return data.monthly_credit_limit !== undefined && data.monthly_credit_limit > 0;
    }
    return true;
  },
  {
    message: 'Monthly credit limit is required for grant organizations',
    path: ['monthly_credit_limit'],
  }
);

type FormData = z.infer<typeof organizationInviteSchema>;

interface FormErrors {
  email?: string;
  organization_type?: string;
  monthly_credit_limit?: string;
}

interface ValidationState {
  email: 'idle' | 'valid' | 'invalid';
  monthly_credit_limit: 'idle' | 'valid' | 'invalid';
}

// Debounce hook for performance
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}

export const OrganizationInviteForm: React.FC = () => {
  // Refs
  const emailInputRef = useRef<HTMLInputElement>(null);

  // Form state
  const [formData, setFormData] = useState<FormData>({
    email: '',
    organization_type: 'prepay_org',
    monthly_credit_limit: undefined,
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [validation, setValidation] = useState<ValidationState>({
    email: 'idle',
    monthly_credit_limit: 'idle',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [inviteResponse, setInviteResponse] = useState<OrganizationInviteResponse | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [copied, setCopied] = useState(false);

  // Debounced email for validation
  const debouncedEmail = useDebounce(formData.email, 300);

  // Auto-focus email input on mount
  useEffect(() => {
    emailInputRef.current?.focus();
  }, []);

  // Debounced email validation
  useEffect(() => {
    if (!debouncedEmail) {
      setValidation(prev => ({ ...prev, email: 'idle' }));
      setErrors(prev => ({ ...prev, email: undefined }));
      return;
    }

    try {
      z.string().email().parse(debouncedEmail);
      setValidation(prev => ({ ...prev, email: 'valid' }));
      setErrors(prev => ({ ...prev, email: undefined }));
    } catch {
      setValidation(prev => ({ ...prev, email: 'invalid' }));
      setErrors(prev => ({ ...prev, email: 'Please enter a valid email address' }));
    }
  }, [debouncedEmail]);

  // Validate credit limit when it changes
  useEffect(() => {
    if (formData.organization_type !== 'grant_org') {
      setValidation(prev => ({ ...prev, monthly_credit_limit: 'idle' }));
      return;
    }

    if (!formData.monthly_credit_limit) {
      setValidation(prev => ({ ...prev, monthly_credit_limit: 'idle' }));
      return;
    }

    if (formData.monthly_credit_limit > 0) {
      setValidation(prev => ({ ...prev, monthly_credit_limit: 'valid' }));
      setErrors(prev => ({ ...prev, monthly_credit_limit: undefined }));
    } else {
      setValidation(prev => ({ ...prev, monthly_credit_limit: 'invalid' }));
      setErrors(prev => ({ ...prev, monthly_credit_limit: 'Must be greater than 0' }));
    }
  }, [formData.monthly_credit_limit, formData.organization_type]);

  // Memoized form validity check
  const isFormValid = useMemo(() => {
    if (!formData.email || validation.email !== 'valid') return false;
    if (formData.organization_type === 'grant_org') {
      return validation.monthly_credit_limit === 'valid';
    }
    return true;
  }, [formData.email, formData.organization_type, validation]);

  // Memoized handlers
  const handleEmailChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setFormData(prev => ({ ...prev, email: value }));
  }, []);

  const handleOrganizationTypeChange = useCallback((value: 'prepay_org' | 'grant_org' | 'postpay_org') => {
    setFormData(prev => ({
      ...prev,
      organization_type: value,
      monthly_credit_limit: value === 'grant_org' ? prev.monthly_credit_limit : undefined,
    }));
    setErrors(prev => ({ ...prev, organization_type: undefined, monthly_credit_limit: undefined }));
  }, []);

  const handleCreditLimitChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    const numValue = value === '' ? undefined : parseInt(value, 10);
    setFormData(prev => ({ ...prev, monthly_credit_limit: numValue }));
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isFormValid) {
      toast.error('Please fix the validation errors before submitting');
      return;
    }

    setIsLoading(true);

    try {
      const request: OrganizationInviteRequest = {
        email: formData.email,
        organization_type: formData.organization_type,
        monthly_credit_limit: formData.monthly_credit_limit,
      };

      const response = await organizationService.inviteOrganization(request);

      setInviteResponse(response);
      setShowSuccess(true);
      toast.success('Organization invitation sent successfully!');
    } catch (error) {
      console.error('Error inviting organization:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to send invitation';
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [formData, isFormValid]);

  const handleSendAnother = useCallback(() => {
    setFormData({
      email: '',
      organization_type: 'prepay_org',
      monthly_credit_limit: undefined,
    });
    setErrors({});
    setValidation({ email: 'idle', monthly_credit_limit: 'idle' });
    setInviteResponse(null);
    setShowSuccess(false);
    setCopied(false);
    // Focus email input after reset
    setTimeout(() => emailInputRef.current?.focus(), 100);
  }, []);

  const handleCopyLink = useCallback(async () => {
    if (inviteResponse?.invite_url) {
      await navigator.clipboard.writeText(inviteResponse.invite_url);
      setCopied(true);
      toast.success('Link copied to clipboard!');
      setTimeout(() => setCopied(false), 2000);
    }
  }, [inviteResponse?.invite_url]);

  // Handle keyboard submit
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && isFormValid && !isLoading) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  }, [handleSubmit, isFormValid, isLoading]);

  // Validation indicator component
  const ValidationIndicator = ({ state }: { state: 'idle' | 'valid' | 'invalid' }) => {
    if (state === 'idle') return null;

    return (
      <motion.div
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="absolute right-3 top-1/2 -translate-y-1/2"
      >
        {state === 'valid' ? (
          <CheckCircle className="w-4 h-4 text-green-500" />
        ) : (
          <AlertCircle className="w-4 h-4 text-red-500" />
        )}
      </motion.div>
    );
  };

  return (
    <div className="mx-auto" onKeyDown={handleKeyDown}>
      <AnimatePresence mode="wait">
        {!showSuccess ? (
          <motion.div
            key="form"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            <Card className="relative overflow-hidden border border-gray-200 dark:border-gray-700">
              {/* Subtle gradient accent */}
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-brand-400 via-brand-500 to-brand-600" />

              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-3 text-xl">
                  <div className="p-2 rounded-lg bg-brand-50 dark:bg-brand-500/10">
                    <Building2 className="w-5 h-5 text-brand-500" />
                  </div>
                  Invite Organization Admin
                </CardTitle>
                <CardDescription className="text-gray-600 dark:text-gray-400">
                  Send an invitation to an organization admin to join the platform
                </CardDescription>
              </CardHeader>

              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* Email Input */}
                  <div className="space-y-2">
                    <Label htmlFor="email" className="flex items-center gap-2 text-sm font-medium">
                      <Mail className="w-4 h-4 text-gray-500" />
                      Email Address
                      <span className="text-red-500">*</span>
                    </Label>
                    <div className="relative">
                      <Input
                        ref={emailInputRef}
                        id="email"
                        type="email"
                        placeholder="admin@organization.com"
                        value={formData.email}
                        onChange={handleEmailChange}
                        aria-invalid={validation.email === 'invalid'}
                        disabled={isLoading}
                        className={`w-full pr-10 transition-all duration-200 ${validation.email === 'valid'
                          ? 'border-green-300 focus:border-green-500 focus:ring-green-500/20'
                          : validation.email === 'invalid'
                            ? 'border-red-300 focus:border-red-500 focus:ring-red-500/20'
                            : ''
                          }`}
                      />
                      <ValidationIndicator state={validation.email} />
                    </div>
                    <AnimatePresence>
                      {errors.email && (
                        <motion.p
                          initial={{ opacity: 0, y: -10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -10 }}
                          className="text-sm text-red-500 flex items-center gap-1.5"
                        >
                          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                          {errors.email}
                        </motion.p>
                      )}
                    </AnimatePresence>
                  </div>

                  {/* Organization Type Selector */}
                  <div className="space-y-3">
                    <Label className="flex items-center gap-2 text-sm font-medium">
                      <Building2 className="w-4 h-4 text-gray-500" />
                      Organization Type
                      <span className="text-red-500">*</span>
                    </Label>
                    <RadioGroup
                      value={formData.organization_type}
                      onValueChange={handleOrganizationTypeChange}
                      disabled={isLoading}
                      className="grid grid-cols-1 gap-3"
                    >
                      {/* Prepay Organization Option */}
                      <label htmlFor="prepay_org" className="cursor-pointer">
                        <motion.div
                          whileHover={{ scale: 1.01 }}
                          whileTap={{ scale: 0.99 }}
                          className={`relative flex items-start space-x-3 p-4 rounded-xl border-2 transition-all ${formData.organization_type === 'prepay_org'
                            ? 'border-brand-500 bg-gradient-to-br from-brand-50 to-brand-100/50 dark:from-brand-500/10 dark:to-brand-500/5 shadow-md shadow-brand-500/10'
                            : 'border-gray-200 dark:border-gray-700 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-sm'
                            }`}
                        >
                          {formData.organization_type === 'prepay_org' && (
                            <motion.div
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              className="absolute top-2 right-2"
                            >
                              <CheckCircle className="w-5 h-5 text-brand-500" />
                            </motion.div>
                          )}
                          <RadioGroupItem value="prepay_org" id="prepay_org" className="mt-0.5" />
                          <div className="flex-1 space-y-1.5">
                            <span className="font-semibold flex items-center gap-2">
                              <CreditCard className="w-4 h-4 text-brand-500" />
                              Prepay Organization
                            </span>
                            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                              Organization purchases credits via payment. No monthly limit required.
                            </p>
                          </div>
                        </motion.div>
                      </label>

                      {/* Grant Organization Option */}
                      <label htmlFor="grant_org" className="cursor-pointer">
                        <motion.div
                          whileHover={{ scale: 1.01 }}
                          whileTap={{ scale: 0.99 }}
                          className={`relative flex items-start space-x-3 p-4 rounded-xl border-2 transition-all ${formData.organization_type === 'grant_org'
                            ? 'border-brand-500 bg-gradient-to-br from-brand-50 to-brand-100/50 dark:from-brand-500/10 dark:to-brand-500/5 shadow-md shadow-brand-500/10'
                            : 'border-gray-200 dark:border-gray-700 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-sm'
                            }`}
                        >
                          {formData.organization_type === 'grant_org' && (
                            <motion.div
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              className="absolute top-2 right-2"
                            >
                              <CheckCircle className="w-5 h-5 text-brand-500" />
                            </motion.div>
                          )}
                          <RadioGroupItem value="grant_org" id="grant_org" className="mt-0.5" />
                          <div className="flex-1 space-y-1.5">
                            <span className="font-semibold flex items-center gap-2">
                              <Gift className="w-4 h-4 text-purple-500" />
                              Grant Organization
                            </span>
                            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                              Organization receives monthly credit allocation. Requires monthly limit.
                            </p>
                          </div>
                        </motion.div>
                      </label>

                      {/* Postpay Organization Option */}
                      <label htmlFor="postpay_org" className="cursor-pointer">
                        <motion.div
                          whileHover={{ scale: 1.01 }}
                          whileTap={{ scale: 0.99 }}
                          className={`relative flex items-start space-x-3 p-4 rounded-xl border-2 transition-all ${formData.organization_type === 'postpay_org'
                            ? 'border-brand-500 bg-gradient-to-br from-brand-50 to-brand-100/50 dark:from-brand-500/10 dark:to-brand-500/5 shadow-md shadow-brand-500/10'
                            : 'border-gray-200 dark:border-gray-700 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-sm'
                            }`}
                        >
                          {formData.organization_type === 'postpay_org' && (
                            <motion.div
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              className="absolute top-2 right-2"
                            >
                              <CheckCircle className="w-5 h-5 text-brand-500" />
                            </motion.div>
                          )}
                          <RadioGroupItem value="postpay_org" id="postpay_org" className="mt-0.5" />
                          <div className="flex-1 space-y-1.5">
                            <span className="font-semibold flex items-center gap-2">
                              <Wallet className="w-4 h-4 text-blue-500" />
                              Postpay Organization
                            </span>
                            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                              Organization pays for usage at the end of the billing cycle.
                            </p>
                          </div>
                        </motion.div>
                      </label>
                    </RadioGroup>
                  </div>

                  {/* Conditional Monthly Credit Limit Input */}
                  <AnimatePresence>
                    {formData.organization_type === 'grant_org' && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.25, ease: 'easeOut' }}
                        className="space-y-2 overflow-hidden"
                      >
                        <Label htmlFor="monthly_credit_limit" className="flex items-center gap-2 text-sm font-medium">
                          <Sparkles className="w-4 h-4 text-gray-500" />
                          Monthly Credit Limit
                          <span className="text-red-500">*</span>
                        </Label>
                        <div className="relative">
                          <Input
                            id="monthly_credit_limit"
                            type="number"
                            placeholder="e.g., 1000"
                            value={formData.monthly_credit_limit ?? ''}
                            onChange={handleCreditLimitChange}
                            aria-invalid={validation.monthly_credit_limit === 'invalid'}
                            disabled={isLoading}
                            min="1"
                            step="1"
                            className={`w-full pr-10 transition-all duration-200 ${validation.monthly_credit_limit === 'valid'
                              ? 'border-green-300 focus:border-green-500 focus:ring-green-500/20'
                              : validation.monthly_credit_limit === 'invalid'
                                ? 'border-red-300 focus:border-red-500 focus:ring-red-500/20'
                                : ''
                              }`}
                          />
                          <ValidationIndicator state={validation.monthly_credit_limit} />
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          Maximum credits this organization can allocate per month
                        </p>
                        <AnimatePresence>
                          {errors.monthly_credit_limit && (
                            <motion.p
                              initial={{ opacity: 0, y: -10 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -10 }}
                              className="text-sm text-red-500 flex items-center gap-1.5"
                            >
                              <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                              {errors.monthly_credit_limit}
                            </motion.p>
                          )}
                        </AnimatePresence>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Submit Button */}
                  <div className="flex justify-end pt-2">
                    <Button
                      type="submit"
                      disabled={isLoading || !isFormValid}
                      className={`min-w-[160px] gap-2 transition-all duration-200 ${isFormValid && !isLoading
                        ? 'bg-brand-500 hover:bg-brand-600 shadow-md hover:shadow-lg hover:shadow-brand-500/25'
                        : ''
                        }`}
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          Send Invitation
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </motion.div>
        ) : (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          >
            <Card className="relative overflow-hidden border-2 border-green-200 dark:border-green-800 shadow-lg">
              {/* Success gradient accent */}
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-green-400 via-emerald-500 to-teal-500" />

              {/* Celebration background */}
              <div className="absolute inset-0 bg-gradient-to-br from-green-50/50 via-transparent to-emerald-50/30 dark:from-green-900/10 dark:to-emerald-900/10 pointer-events-none" />

              <CardHeader className="relative">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                  className="flex items-center gap-3"
                >
                  <div className="p-3 rounded-full bg-green-100 dark:bg-green-900/30">
                    <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <CardTitle className="text-xl text-green-700 dark:text-green-400">
                      Invitation Sent Successfully!
                    </CardTitle>
                    <CardDescription className="text-green-600/80 dark:text-green-400/70">
                      The organization admin will receive an email shortly
                    </CardDescription>
                  </div>
                </motion.div>
              </CardHeader>

              <CardContent className="relative space-y-6">
                {/* Invitation Details */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="overflow-hidden rounded-xl border border-gray-100 dark:border-gray-800 bg-white/50 dark:bg-gray-900/40 backdrop-blur-sm shadow-sm"
                >
                  <div className="bg-gray-50/50 dark:bg-white/5 px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
                    <h3 className="font-semibold text-sm text-brand-500 dark:text-gray-300 flex items-center gap-2">
                      <History className="w-4 h-4 text-brand-500" />
                      Invitation Summary
                    </h3>
                    <Badge
                      variant="light"
                      color={inviteResponse?.status === 'pending' ? 'warning' : 'success'}
                      size="sm"
                      startIcon={<div className={`w-1.5 h-1.5 rounded-full ${inviteResponse?.status === 'pending' ? 'bg-amber-500 animate-pulse' : 'bg-green-500'}`} />}
                    >
                      {inviteResponse?.status || 'Pending'}
                    </Badge>
                  </div>

                  <div className="p-4 space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Email Row */}
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 p-1.5 rounded-lg bg-blue-50 dark:bg-blue-500/10">
                          <Mail className="w-3.5 h-3.5 text-blue-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold mb-0.5">Admin Email</p>
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{inviteResponse?.email}</p>
                        </div>
                      </div>

                      {/* Organization Type Row */}
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 p-1.5 rounded-lg bg-purple-50 dark:bg-purple-500/10">
                          <Building2 className="w-3.5 h-3.5 text-purple-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold mb-0.5">Account Type</p>
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {inviteResponse?.organization_type === 'prepay_org'
                              ? 'Prepay'
                              : inviteResponse?.organization_type === 'grant_org'
                                ? 'Grant'
                                : 'Postpay'}
                          </p>
                        </div>
                      </div>

                      {/* Monthly Limit (Conditional) */}
                      {inviteResponse?.monthly_credit_limit && (
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 p-1.5 rounded-lg bg-amber-50 dark:bg-amber-500/10">
                            <Layers className="w-3.5 h-3.5 text-amber-500" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold mb-0.5">Monthly Credits</p>
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{inviteResponse.monthly_credit_limit.toLocaleString()} / mo</p>
                          </div>
                        </div>
                      )}

                      {/* Expiration Row */}
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 p-1.5 rounded-lg bg-rose-50 dark:bg-rose-500/10">
                          <Calendar className="w-3.5 h-3.5 text-rose-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold mb-0.5">Invitation Expires</p>
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {inviteResponse?.expires_at
                              ? new Date(inviteResponse.expires_at).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric'
                              })
                              : 'N/A'}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Security Note */}
                    <div className="flex items-center gap-2 px-3 py-2 bg-brand-50/50 dark:bg-brand-500/5 rounded-lg border border-brand-100/50 dark:border-brand-500/10">
                      <ShieldCheck className="w-4 h-4 text-brand-500" />
                      <p className="text-[11px] text-brand-600 dark:text-brand-400 font-medium">This is a secure one-time use invitation link.</p>
                    </div>
                  </div>
                </motion.div>

                {/* Invitation URL */}
                {inviteResponse?.invite_url && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="space-y-2"
                  >
                    <Label className="text-sm font-semibold flex items-center gap-2 text-brand-500">
                      <Mail className="w-4 h-4" />
                      Invitation Link
                    </Label>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Input
                          value={inviteResponse.invite_url}
                          readOnly
                          className="pr-4 text-xs font-mono bg-gray-50 dark:bg-gray-800"
                        />
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleCopyLink}
                        className={`min-w-[100px] gap-2 transition-all duration-200 ${copied ? 'bg-green-50 border-green-300 text-green-700' : ''
                          }`}
                      >
                        <AnimatePresence mode="wait">
                          {copied ? (
                            <motion.div
                              key="check"
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              exit={{ scale: 0 }}
                              className="flex items-center gap-1.5"
                            >
                              <Check className="w-4 h-4" />
                              Copied!
                            </motion.div>
                          ) : (
                            <motion.div
                              key="copy"
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              exit={{ scale: 0 }}
                              className="flex items-center gap-1.5 text-brand-500"
                            >
                              <Copy className="w-4 h-4" />
                              Copy
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </Button>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Share this link with the organization admin to complete registration
                    </p>
                  </motion.div>
                )}

                {/* Action Buttons */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                  className="flex flex-col sm:flex-row justify-end gap-3 pt-2"
                >
                  <Button
                    variant="outline"
                    onClick={() => window.location.href = '/admin/organizations'}
                    className="gap-2"
                  >
                    <Building2 className="w-4 h-4" />
                    View All Organizations
                  </Button>
                  <Button
                    onClick={handleSendAnother}
                    className="gap-2 bg-brand-500 hover:bg-brand-600"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Send Another Invite
                  </Button>
                </motion.div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default OrganizationInviteForm;
