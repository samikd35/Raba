"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { useAuthStore } from "@/stores/authStore";
import { organizationService } from "@/lib/api/organizationService";
import Image from "next/image";
import { 
  Building2, 
  Mail, 
  CheckCircle,
  Calendar,
  Shield,
  Coins,
  Loader2,
  AlertTriangle,
  ArrowLeft,
  Users,
  Sparkles
} from "lucide-react";

export default function OrganizationMembershipConfirmation() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuthStore();

  const orgId = searchParams.get('org_id');
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [membershipData, setMembershipData] = useState<any>(null);

  useEffect(() => {
    const fetchMembershipDetails = async () => {
      if (!orgId) {
        setError('Organization ID not found');
        setLoading(false);
        return;
      }
      
      try {
        const data = await organizationService.getUserMembershipDetails(orgId);
        setMembershipData(data);
      } catch (err: any) {
        if (process.env.NODE_ENV === 'development') {
          console.error('Failed to fetch membership details:', err);
        }
        setError(err?.message || 'Failed to load membership details');
      } finally {
        setLoading(false);
      }
    };
    
    fetchMembershipDetails();
  }, [orgId]);

  // Extract data with fallbacks
  const orgName = membershipData?.organization?.name || searchParams.get('org_name') || 'the Organization';
  const creditsAllocated = membershipData?.invitation?.credits_allocated || 0;
  const joinedAt = membershipData?.invitation?.accepted_at || membershipData?.membership?.joined_at;
  const role = membershipData?.membership?.role || 'member';
  const invitedBy = membershipData?.invitation?.invited_by_email;

  const formatJoinedDate = (dateStr?: string | null) => {
    if (!dateStr) return 'Just joined today!';
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return 'Just joined today!';
    return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  };

  if (loading) {
    return (
      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-[#101828] xl:px-10 flex items-center justify-center">
        <motion.div 
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="p-4 rounded-full bg-brand-50 dark:bg-brand-800/50 mb-6 inline-flex">
            <Loader2 className="w-8 h-8 text-brand-600 dark:text-brand-400 animate-spin" />
          </div>
          <h2 className="text-xl font-semibold text-brand-700 dark:text-white mb-2">Loading Membership Details</h2>
          <p className="text-brand-600 dark:text-brand-200">Please wait while we verify your organization access...</p>
        </motion.div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-[#101828] xl:px-10">
        <div className="max-w-2xl mx-auto py-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            {/* Back Navigation */}
            <div className="mb-8 flex items-center gap-2 text-sm text-brand-600 dark:text-brand-400">
              <ArrowLeft className="w-4 h-4" />
              <button
                onClick={() => router.back()}
                className="hover:underline hover:text-brand-700 dark:hover:text-brand-300 transition-colors"
              >
                Back
              </button>
            </div>

            {/* Error Card */}
            <div className="p-6 bg-white dark:bg-[#101828] border border-red-200 dark:border-red-700 rounded-xl shadow-sm">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-full bg-red-50 dark:bg-red-800/50 text-red-600 dark:text-red-400">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <h1 className="text-2xl font-bold text-brand-700 dark:text-white mb-2">Unable to Load Membership</h1>
                  <p className="text-brand-600 dark:text-brand-200 mb-6">{error}</p>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <button
                      onClick={() => router.refresh()}
                      className="px-6 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600 text-white font-medium transition-colors"
                    >
                      Try Again
                    </button>
                    <Link
                      href="/signin"
                      className="px-6 py-2.5 rounded-lg border border-brand-300 dark:border-brand-600 text-brand-700 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-800/50 font-medium transition-colors text-center"
                    >
                      Go to Sign In
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-[#101828] xl:px-10">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
        

          {/* Success Confirmation */}
          <motion.div 
            className="p-4 bg-brand-25 dark:bg-brand-800/30 border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm mb-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.3 }}
          >
            <div className="text-center flex flex-col items-center justify-center gap-1">
              <Image
                className="dark:hidden mb-2"
                src="/images/logo/logo.svg"
                alt="Logo"
                width={110}
                height={20}
              />
              <h2 className="text-2xl font-bold text-brand-500 dark:text-white">
                Membership Confirmed!
              </h2>
              <p className="text-brand-600 dark:text-brand-200">
                You're now an active member of {orgName} with full access to organization resources
              </p>
            </div>
          </motion.div>

          {/* Membership Details Grid */}
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            {/* Organization Info */}
            <motion.div 
              className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 dark:hover:bg-brand-700/50 transition-all duration-200"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.4 }}
            >
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-lg bg-brand-100 dark:bg-brand-800/50">
                  <Building2 className="w-6 h-6 text-brand-600 dark:text-brand-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-brand-700 dark:text-white mb-1">Organization</h3>
                  <p className="text-xl font-bold text-brand-600 dark:text-brand-200">{orgName}</p>
                  <p className="text-sm text-brand-500 dark:text-brand-400 mt-1">Active Member</p>
                </div>
              </div>
            </motion.div>

            {/* Member Since */}
            <motion.div 
              className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 dark:hover:bg-brand-700/50 transition-all duration-200"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.5 }}
            >
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-lg bg-brand-100 dark:bg-brand-800/50">
                  <Calendar className="w-6 h-6 text-brand-600 dark:text-brand-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-brand-700 dark:text-white mb-1">Member Since</h3>
                  <p className="text-brand-600 dark:text-brand-200 font-medium">
                    {formatJoinedDate(joinedAt)}
                  </p>
                </div>
              </div>
            </motion.div>

            {/* Role */}
            <motion.div 
              className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 dark:hover:bg-brand-700/50 transition-all duration-200"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.6 }}
            >
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-lg bg-brand-100 dark:bg-brand-800/50">
                  <Shield className="w-6 h-6 text-brand-600 dark:text-brand-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-brand-700 dark:text-white mb-1">Your Role</h3>
                  <span className="px-3 py-1 text-sm font-semibold bg-brand-100 dark:bg-brand-800 text-brand-700 dark:text-brand-200 rounded-full capitalize">
                    {role}
                  </span>
                </div>
              </div>
            </motion.div>

            {/* Credits */}
            {creditsAllocated > 0 && (
              <motion.div 
                className="p-6 bg-white dark:bg-[#101828] border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm hover:shadow-lg hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 dark:hover:bg-brand-700/50 transition-all duration-200"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.7 }}
              >
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-lg bg-brand-100 dark:bg-brand-800/50">
                    <Coins className="w-6 h-6 text-brand-600 dark:text-brand-400" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-brand-700 dark:text-white mb-1">Credits Allocated</h3>
                    <p className="text-2xl font-bold text-brand-600 dark:text-brand-200">{creditsAllocated}</p>
                    <p className="text-sm text-brand-500 dark:text-brand-400">Available for platform usage</p>
                  </div>
                </div>
              </motion.div>
            )}
          </div>

          {/* Additional Information */}
          {invitedBy && (
            <motion.div 
              className="p-6 bg-brand-50 dark:bg-brand-800/30 border border-brand-200 dark:border-brand-700 rounded-xl shadow-sm mb-8"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.8 }}
            >
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-lg bg-brand-100 dark:bg-brand-800/50">
                  <Mail className="w-6 h-6 text-brand-600 dark:text-brand-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-brand-700 dark:text-white mb-2">Invitation Details</h3>
                  <p className="text-brand-600 dark:text-brand-200">
                    You were invited by <span className="font-medium">{invitedBy}</span>
                  </p>
                </div>
              </div>
            </motion.div>
          )}



          {/* Action Buttons */}
          <motion.div 
            className="flex flex-col sm:flex-row gap-4 justify-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 1.0 }}
          >
            <button
              onClick={() => router.push('/choose-workspace')}
              className="px-6 py-2 bg-brand-500 hover:bg-brand-600 dark:bg-brand-500 dark:hover:bg-brand-600 text-white rounded-lg font-medium shadow-lg hover:shadow-xl transition-all duration-200"
            >
              Go to Workspace
            </button>
           
          </motion.div>

 
        </motion.div>
      </div>
    </div>
  );
}
