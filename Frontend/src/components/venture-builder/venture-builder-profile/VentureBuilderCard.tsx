'use client';

import { useCallback, useState } from 'react';
import { motion } from 'framer-motion';
import { User, Calendar, Star, Award, Briefcase, Loader2, CreditCard, Linkedin, ExternalLink } from 'lucide-react';
import { VBProfile } from '@/types/ventureBuilder';
import BookingWizard from '../book-a-consultation/BookingWizard';

interface VentureBuilderCardProps {
  builder: VBProfile;
  isSelected: boolean;
  onSelect: (builder: VBProfile) => void;
  onViewProfile: (builder: VBProfile) => void;
  index: number;
}

export default function VentureBuilderCard({
  builder,
  isSelected,
  onSelect,
  onViewProfile,
  index,
}: VentureBuilderCardProps) {
  const [isBookingWizardOpen, setIsBookingWizardOpen] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);


  const handleViewProfile = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();

    try {
      setIsLoadingProfile(true);
      const { fetchVentureBuilderById } = await import('@/lib/api/venture-builder');
      const fullProfile = await fetchVentureBuilderById(builder.id);
      onViewProfile(fullProfile);
    } catch (error) {
      console.error('Error fetching VB details:', error);
      onViewProfile(builder);
    } finally {
      setIsLoadingProfile(false);
    }
  }, [builder, onViewProfile]);

  const handleBookSession = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setIsBookingWizardOpen(true);
  }, []);

  const handleCloseBookingWizard = useCallback(() => {
    setIsBookingWizardOpen(false);
  }, []);

  const domain = builder.main_expertise ||
    (builder.expertise_areas && builder.expertise_areas.length > 0
      ? builder.expertise_areas[0].name
      : 'Venture Builder');

  // Always allow booking - the booking wizard will handle availability checking
  const canBookSession = true;

  // Expertise pills display logic
  const maxVisibleExpertise = 2;
  const visibleExpertise = builder.expertise_areas?.slice(0, maxVisibleExpertise) || [];
  const remainingExpertise = (builder.expertise_areas?.length || 0) - maxVisibleExpertise;

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: index * 0.1 }}
        className={`group relative p-6 bg-white dark:bg-gray-900/80 border border-brand-200 dark:border-brand-700/50 rounded-xl shadow-sm transition-all duration-200 cursor-pointer backdrop-blur-sm ${
          isSelected
            ? 'border-brand-500 dark:border-brand-400 shadow-lg shadow-brand-500/20 dark:shadow-brand-400/20 bg-brand-25 dark:bg-brand-800/30 ring-2 ring-brand-200 dark:ring-brand-400/30'
            : 'hover:shadow-lg hover:shadow-brand-500/10 dark:hover:shadow-brand-400/10 hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-25 dark:hover:bg-brand-700/30 hover:scale-[1.02]'
        }`}
        onClick={() => onSelect(builder)}
      >
        {/* Profile Image and Basic Info */}
        <div className="flex items-start gap-4 mb-4">
          <div className="w-16 h-16 rounded-full overflow-hidden border-3 border-brand-200 dark:border-brand-600/50 flex-shrink-0 ring-2 ring-brand-100 dark:ring-brand-700/30">
            <img
              src={builder.profile_picture_url}
              alt={builder.full_name || 'Venture Builder'}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-brand-700 dark:text-brand-200 mb-1 truncate">
              {builder.full_name || (builder as any).name || 'Venture Builder'}
            </h3>
            {/* Expertise Pills */}
            <div className="flex flex-wrap items-center gap-1.5 mb-2">
              {visibleExpertise.map((area, index) => (
                <span
                  key={area.id || index}
                  className="px-2.5 py-0.5 text-xs font-medium bg-brand-100 dark:bg-brand-800/60 text-brand-700 dark:text-brand-300 rounded-full border dark:border-brand-700/30"
                >
                  {area.name}
                </span>
              ))}
              {remainingExpertise > 0 && (
                <span className="px-2.5 py-0.5 text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-full">
                  +{remainingExpertise} more
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Bio */}
        <p className="text-sm text-brand-600 dark:text-brand-400 mb-4 line-clamp-3 leading-relaxed">
          {builder.biography}
        </p>

        {/* Price Display */}
        {builder.credit_price_per_hour && builder.credit_price_per_hour > 0 && (
          <div className="mb-4 p-3 bg-gradient-to-r from-brand-50 to-brand-100 dark:from-brand-900/20 dark:to-brand-800/20 border border-brand-200 dark:border-brand-700 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <span className="text-sm font-medium text-brand-700 dark:text-brand-300">
                  {builder.credit_price_per_hour} credits
                </span>
              </div>
              <span className="text-xs text-brand-600 dark:text-brand-400">
                / 1-hour session
              </span>
            </div>
          </div>
        )}

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
          {builder.linkedin_url && (
            <a
              href={builder.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1 px-2 py-1 bg-blue-50 dark:bg-blue-800/30 rounded-md hover:bg-blue-100 dark:hover:bg-blue-700/40 transition-colors"
            >
              <Linkedin className="w-3 h-3 text-blue-600 dark:text-blue-400" />
              <ExternalLink className="w-2 h-2 text-blue-600 dark:text-blue-400" />
            </a>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            className="flex-1 py-2 px-4 bg-brand-50 dark:bg-brand-800/50 text-brand-600 dark:text-brand-300 border border-brand-200 dark:border-brand-600/50 rounded-lg text-sm font-medium transition-all duration-200 hover:bg-brand-100 dark:hover:bg-brand-700/60 hover:border-brand-300 dark:hover:border-brand-500 hover:shadow-sm dark:hover:shadow-brand-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={handleViewProfile}
            disabled={isLoadingProfile}
            aria-label={`View ${builder.full_name}'s profile`}
          >
            {isLoadingProfile ? (
              <>
                <Loader2 className="w-4 h-4 inline mr-2 animate-spin" />
                Loading...
              </>
            ) : (
              <>
                <User className="w-4 h-4 inline mr-2" />
                View Profile
              </>
            )}
          </button>
          <button
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
              canBookSession
                ? 'bg-primary hover:bg-primary/90 text-white shadow-sm hover:shadow-md'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 cursor-not-allowed opacity-60'
            }`}
            onClick={canBookSession ? handleBookSession : undefined}
            disabled={!canBookSession}
            aria-label={canBookSession ? 'Book a session' : 'Calendar not connected'}
            title={!canBookSession ? 'Calendar not connected' : undefined}
          >
            <Calendar className="w-4 h-4 inline mr-2" />
            {canBookSession ? 'Book Session' : 'Calendar Not Connected'}
          </button>
        </div>

        {/* Hover Overlay for Profile */}
        <div className="absolute inset-0 bg-gradient-to-br from-brand-500/5 to-brand-600/10 dark:from-brand-400/5 dark:to-brand-500/10 rounded-xl opacity-0 group-hover:opacity-100 transition-all duration-300 pointer-events-none" />
      </motion.div>

      {/* Booking Wizard */}
      <BookingWizard
        isOpen={isBookingWizardOpen}
        onClose={handleCloseBookingWizard}
        ventureBuilder={builder}
      />
    </>
  );
}
