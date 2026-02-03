'use client';
import React, { useEffect, useState, useCallback, useMemo } from "react";
import { motion } from "framer-motion";
import { Calendar, User, Lock, ExternalLink, Star, Award, Briefcase } from "lucide-react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import { useRouter } from 'next/navigation';
import VentureBuilderProfileModal from './VentureBuilderProfileModal';
import { ventureBuilders } from './data/ventureBuilders';
import { VentureBuilder } from '@/types/venture';

export default function BookConsultationPage() {
  const router = useRouter();
  const [selectedBuilder, setSelectedBuilder] = useState<VentureBuilder | null>(null);
  const [isCalendarModalOpen, setIsCalendarModalOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<VentureBuilder | null>(null);

  // Memoized data with validation
  const validatedBuilders = useMemo(() => {
    return ventureBuilders.filter(builder => 
      builder?.id && 
      builder?.name && 
      builder?.fullName && 
      builder?.profileImage &&
      builder?.domain &&
      builder?.bio
    );
  }, []);

  // Optimized handlers
  const handleSelectBuilder = useCallback((builder: VentureBuilder) => {
    setSelectedBuilder(current => 
      current?.id === builder.id ? null : builder
    );
  }, []);

  const openCalendarModal = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setIsCalendarModalOpen(true);
  }, []);

  const closeCalendarModal = useCallback(() => {
    setIsCalendarModalOpen(false);
  }, []);

  const createProfileModalHandler = useCallback((builder: VentureBuilder) => {
    return (e: React.MouseEvent) => {
      e.stopPropagation();
      setSelectedProfile(builder);
      setIsProfileModalOpen(true);
    };
  }, []);

  const closeProfileModal = useCallback(() => {
    setIsProfileModalOpen(false);
    setSelectedProfile(null);
  }, []);

  const handleGoBack = useCallback(() => {
    router.push('/team-workspace');
  }, [router]);

  // Safe image URL getter
  const getSafeImageUrl = useCallback((image: any): string => {
    if (!image) return '';
    return image.src || image || '';
  }, []);

  // Handle escape key to close modals
  useEffect(() => {
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (isCalendarModalOpen) {
          closeCalendarModal();
        } else if (isProfileModalOpen) {
          closeProfileModal();
        }
      }
    };
    
    if (isCalendarModalOpen || isProfileModalOpen) {
      document.addEventListener('keydown', handleEscapeKey);
      document.body.style.overflow = 'hidden';
    }
    
    return () => {
      document.removeEventListener('keydown', handleEscapeKey);
      document.body.style.overflow = 'unset';
    };
  }, [isCalendarModalOpen, isProfileModalOpen, closeCalendarModal, closeProfileModal]);

  return (
    <div>
      <PageBreadcrumb pageTitle="Book a Consultation" />
      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-4 py-4 dark:border-gray-800 dark:bg-gray-900/50 xl:px-10">
        <div className="max-w-7xl mx-auto">
          {/* Header Section */}
          

          {/* Venture Builders Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {validatedBuilders.map((builder, index) => (
              <motion.div
                key={builder.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                className={`group relative p-6 bg-white dark:bg-gray-900/80 border border-brand-200 dark:border-brand-700/50 rounded-xl shadow-sm transition-all duration-200 cursor-pointer backdrop-blur-sm ${
                  selectedBuilder?.id === builder.id 
                    ? 'border-brand-500 dark:border-brand-400 shadow-lg shadow-brand-500/20 dark:shadow-brand-400/20 bg-brand-25 dark:bg-brand-800/30 ring-2 ring-brand-200 dark:ring-brand-400/30' 
                    : 'hover:shadow-lg hover:shadow-brand-500/10 dark:hover:shadow-brand-400/10 hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 dark:hover:bg-brand-700/30 hover:scale-[1.02]'
                }`}
                onClick={() => handleSelectBuilder(builder)}
              >
                {/* Lock Badge */}
                <div className="absolute top-4 right-4 w-8 h-8 bg-gradient-to-br from-red-500 to-red-600 dark:from-red-400 dark:to-red-500 rounded-full flex items-center justify-center shadow-lg">
                  <Lock className="w-4 h-4 text-white" />
                </div>

                {/* Profile Image and Basic Info */}
                <div className="flex items-start gap-4 mb-4">
                  <div className="w-16 h-16 rounded-full overflow-hidden border-3 border-brand-200 dark:border-brand-600/50 flex-shrink-0 ring-2 ring-brand-100 dark:ring-brand-700/30">
                    <img
                      src={getSafeImageUrl(builder.profileImage)}
                      alt={builder.name}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-brand-700 dark:text-brand-200 mb-1 truncate">
                      {builder.fullName}
                    </h3>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-3 py-1 text-xs font-semibold bg-brand-100 dark:bg-brand-800/60 text-brand-700 dark:text-brand-300 rounded-full border dark:border-brand-700/30">
                        {builder.domain}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Bio */}
                <p className="text-sm text-brand-600 dark:text-brand-400 mb-4 line-clamp-3 leading-relaxed">
                  {builder.bio}
                </p>

                {/* Stats/Highlights */}
                <div className="flex items-center justify-between mb-4 text-xs text-brand-500 dark:text-brand-400">
                  <div className="flex items-center gap-1 px-2 py-1 bg-brand-50 dark:bg-brand-800/30 rounded-md">
                    <Star className="w-3 h-3 text-yellow-500 dark:text-yellow-400" />
                    <span>Expert</span>
                  </div>
                  <div className="flex items-center gap-1 px-2 py-1 bg-green-50 dark:bg-green-800/30 rounded-md">
                    <Award className="w-3 h-3 text-green-500 dark:text-green-400" />
                    <span>Verified</span>
                  </div>
                  <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 dark:bg-blue-800/30 rounded-md">
                    <Briefcase className="w-3 h-3 text-blue-500 dark:text-blue-400" />
                    <span>Active</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <button 
                    className="flex-1 py-2 px-4 bg-brand-50 dark:bg-brand-800/50 text-brand-600 dark:text-brand-300 border border-brand-200 dark:border-brand-600/50 rounded-lg text-sm font-medium transition-all duration-200 hover:bg-brand-100 dark:hover:bg-brand-700/60 hover:border-brand-300 dark:hover:border-brand-500 hover:shadow-sm dark:hover:shadow-brand-500/20"
                    onClick={createProfileModalHandler(builder)}
                    aria-label={`View ${builder.name}'s profile`}
                  >
                    <User className="w-4 h-4 inline mr-2" />
                    View Profile
                  </button>
                  <button 
                    className="flex-1 py-2 px-4 bg-gray-100 dark:bg-gray-800/60 text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700/50 rounded-lg text-sm font-medium cursor-not-allowed opacity-60"
                    disabled
                    aria-label="Calendar booking coming soon"
                  >
                    <Calendar className="w-4 h-4 inline mr-2" />
                    Coming Soon
                  </button>
                </div>

                {/* Hover Overlay for Profile */}
                <div className="absolute inset-0 bg-gradient-to-br from-brand-500/5 to-brand-600/10 dark:from-brand-400/5 dark:to-brand-500/10 rounded-xl opacity-0 group-hover:opacity-100 transition-all duration-300 pointer-events-none" />
              </motion.div>
            ))}
          </div>

          {/* Empty State */}
          {validatedBuilders.length === 0 && (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-brand-100 dark:bg-brand-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                <User className="w-8 h-8 text-brand-500 dark:text-brand-400" />
              </div>
              <h3 className="text-lg font-semibold text-brand-700 dark:text-brand-300 mb-2">
                No Venture Builders Available
              </h3>
              <p className="text-brand-600 dark:text-brand-400">
                Our expert venture builders will be available soon. Check back later!
              </p>
            </div>
          )}
        </div>
      </div>
      
      {/* Calendar Modal */}
      {isCalendarModalOpen && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={closeCalendarModal}
        >
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="bg-white dark:bg-gray-900/80 border border-brand-200 dark:border-brand-700/50 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden backdrop-blur-sm"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-brand-200 dark:border-brand-700/50 bg-brand-50 dark:bg-brand-800/40 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-brand-700 dark:text-brand-200 flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-brand-500 dark:text-brand-400" />
                  Schedule Your Session
                </h2>
                <button 
                  className="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-700/60 text-brand-600 dark:text-brand-300 flex items-center justify-center transition-all duration-200 hover:bg-brand-200 dark:hover:bg-brand-600/80 hover:scale-105"
                  onClick={closeCalendarModal}
                  aria-label="Close calendar modal"
                >
                  <ExternalLink className="w-4 h-4 rotate-45" />
                </button>
              </div>
            </div>
            <div className="p-6 h-[600px] bg-gray-50 dark:bg-gray-900/50">
              <div className="bg-white dark:bg-gray-800/80 rounded-xl h-full overflow-hidden border border-gray-200 dark:border-gray-700/50 shadow-inner">
                <iframe
                  src="https://calendar.google.com/calendar/appointments/schedules/AcZssZ0Xw4LEXmR8GKhFy_4iD6Y6QG186I89CaTesIQu2deOPi0jyZ45SDKe055mnlo1uEK0lTgnL8BZ?gv=true&bgcolor=%23ffffff&color=%23000000&showTitle=0&showNav=1&showTabs=1&mode=week&theme=light"
                  width="100%"
                  height="100%"
                  frameBorder="0"
                  scrolling="yes"
                  title="Google Calendar Scheduling"
                  className="rounded-lg"
                  loading="lazy"
                />
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}

      {/* Profile Modal */}
      <VentureBuilderProfileModal
        isOpen={isProfileModalOpen}
        profile={selectedProfile}
        onClose={closeProfileModal}
      />
    </div>
  );
}