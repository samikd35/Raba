import React, { useCallback, useState } from 'react';
import { motion } from 'framer-motion';
import { X, Star, Award, Briefcase, Linkedin, Mail, Calendar } from 'lucide-react';
import { VBProfile } from '@/types/ventureBuilder';
import BookingWizard from '../book-a-consultation/BookingWizard';

interface VentureBuilderProfileModalProps {
  isOpen: boolean;
  profile: VBProfile | null;
  onClose: () => void;
}

const VentureBuilderProfileModal: React.FC<VentureBuilderProfileModalProps> = ({
  isOpen,
  profile,
  onClose
}) => {
  if (!isOpen || !profile) return null;

  console.log('VentureBuilderProfileModal - Profile:', profile);
  console.log('VentureBuilderProfileModal - full_name:', profile.full_name);
  console.log('VentureBuilderProfileModal - name:', (profile as any).name);

  const [isBookingWizardOpen, setIsBookingWizardOpen] = useState(false);

  const handleOverlayClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  }, [onClose]);

  const handleBookSession = useCallback(() => {
    setIsBookingWizardOpen(true);
  }, []);

  const handleCloseBookingWizard = useCallback(() => {
    setIsBookingWizardOpen(false);
  }, []);

  // Get the display name (handle both 'name' and 'full_name' fields)
  const displayName = profile.full_name || (profile as any).name || 'Venture Builder';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={handleOverlayClick}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="bg-white dark:bg-gray-900/80 border border-brand-200 dark:border-brand-700/50 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden backdrop-blur-sm"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-brand-200 dark:border-brand-700/50 bg-brand-50 dark:bg-brand-800/40 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-brand-500 dark:bg-brand-400 rounded-full" />
              <h2 className="text-xl font-semibold text-brand-700 dark:text-brand-200">
                Venture Builder Profile
              </h2>
            </div>
            <button
              className="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-700/60 text-brand-600 dark:text-brand-300 flex items-center justify-center transition-all duration-200 hover:bg-brand-200 dark:hover:bg-brand-600/80 hover:rotate-90 hover:scale-105"
              onClick={onClose}
              aria-label="Close profile modal"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex flex-col max-h-[calc(90vh-80px)] overflow-y-auto">
          {/* Profile Header Section */}
          <div className="p-6 bg-brand-25 dark:bg-brand-800/30 border-b border-brand-200 dark:border-brand-700/50">
            <div className="flex flex-col md:flex-row items-start gap-6">
              {/* Profile Image and Action */}
              <div className="flex flex-col items-center gap-4 flex-shrink-0">
                <div className="relative">
                  <div className="w-32 h-32 rounded-2xl overflow-hidden border-4 border-brand-200 dark:border-brand-600/50 shadow-lg ring-2 ring-brand-100 dark:ring-brand-700/30">
                    <img
                      src={profile.profile_picture_url}
                      alt={displayName}
                      className="w-full h-full object-cover"
                    />
                  </div>
                </div>

                {/* Book Session Button */}
                <button
                  onClick={handleBookSession}
                  className="w-full px-6 py-3 bg-primary hover:bg-primary/90 text-white rounded-lg font-semibold transition-all duration-200 shadow-md hover:shadow-lg flex items-center justify-center gap-2"
                >
                  <Calendar className="w-5 h-5" />
                  Book a Session
                </button>
              </div>

              {/* Profile Info */}
              <div className="flex-1 min-w-0">
                <div className="flex flex-col md:flex-row md:items-start gap-4">
                  <div className="flex-1 ">
                    <h3 className="text-3xl font-bold text-brand-700 dark:text-brand-200 mb-2">
                      {displayName}
                    </h3>
                    <div className="flex items-center gap-2">
                      <span className="px-4 py-2 text-sm font-semibold bg-brand-50 dark:bg-brand-800/60 text-brand-500 dark:text-brand-300 rounded-full border dark:border-brand-700/30">
                        {profile.main_expertise ||
                         (profile.expertise_areas && profile.expertise_areas.length > 0
                          ? profile.expertise_areas[0].name
                          : 'Venture Builder')}
                      </span>
                    </div>
                  </div>

                  {/* Status Indicators */}
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-2 px-3 py-1 bg-green-50 dark:bg-green-800/30 text-green-700 dark:text-green-300 rounded-full border dark:border-green-700/30">
                      <Star className="w-3 h-3 text-green-600 dark:text-green-400" />
                      <span>Expert</span>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-800/30 text-blue-700 dark:text-blue-300 rounded-full border dark:border-blue-700/30">
                      <Award className="w-3 h-3 text-blue-600 dark:text-blue-400" />
                      <span>Verified</span>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1 bg-purple-50 dark:bg-purple-800/30 text-purple-700 dark:text-purple-300 rounded-full border dark:border-purple-700/30">
                      <Briefcase className="w-3 h-3 text-purple-600 dark:text-purple-400" />
                      <span>Active</span>
                    </div>
                  </div>
                </div>

                {/* Bio */}
                <p className="text-brand-600 dark:text-brand-400 mt-2 text-[0.9rem] leading-relaxed">
                  {profile.biography}
                </p>

                {/* Contact Info */}
                <div className="flex flex-wrap gap-3 mt-4">
                  {profile.linkedin_url && (
                    <a
                      href={profile.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-lg text-sm hover:bg-blue-100 dark:hover:bg-blue-800/30 transition-colors"
                    >
                      <Linkedin className="w-4 h-4" />
                      LinkedIn Profile
                    </a>
                  )}
                  {profile.contact_email && (
                    <a
                      href={`mailto:${profile.contact_email}`}
                      className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <Mail className="w-4 h-4" />
                      {profile.contact_email}
                    </a>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Pricing & Expertise Section */}
          <div className="py-8 px-12 bg-white dark:bg-gray-900/50">
            <div className="grid grid-cols-1 gap-8">
              {/* Pricing Info */}
              {profile.credit_price_per_hour && (
                <div className="p-6 bg-gradient-to-br from-brand-50 to-brand-100 dark:from-brand-900/20 dark:to-brand-800/20 rounded-xl border border-brand-200 dark:border-brand-700">
                  <h4 className="text-lg font-semibold text-brand-700 dark:text-brand-200 mb-3 flex items-center gap-2">
                    <Award className="w-5 h-5 text-brand-500 dark:text-brand-400" />
                    Session Pricing
                  </h4>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-brand-600 dark:text-brand-400">
                      {profile.credit_price_per_hour}
                    </span>
                    <span className="text-sm text-brand-600 dark:text-brand-400">credits per hour</span>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                    One-on-one consultation sessions are 60 minutes long
                  </p>
                </div>
              )}

              {/* Work Experience */}
              {profile.work_experience && profile.work_experience.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-brand-700 dark:text-brand-200 mb-4 flex items-center gap-2">
                    <Briefcase className="w-5 h-5 text-brand-500 dark:text-brand-400" />
                    Work Experience
                  </h4>
                  <div className="space-y-4">
                    {profile.work_experience.map((exp, index) => (
                      <div key={index} className="p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-700">
                        <h5 className="font-semibold text-brand-700 dark:text-brand-200">{exp.position}</h5>
                        <p className="text-sm text-brand-600 dark:text-brand-400">{exp.organization}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">{exp.years}</p>
                        {exp.description && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">{exp.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Expertise Areas */}
              {profile.expertise_areas && profile.expertise_areas.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-brand-700 dark:text-brand-200 mb-4 flex items-center gap-2">
                    <Star className="w-5 h-5 text-brand-500 dark:text-brand-400" />
                    Areas of Expertise
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {profile.expertise_areas.map((area) => (
                      <span
                        key={area.id}
                        className="px-3 py-1 text-xs font-medium bg-blue-50 dark:bg-blue-800/30 text-blue-600 dark:text-blue-300 border border-blue-200 dark:border-blue-700/50 rounded-lg transition-all duration-200 hover:bg-blue-100 dark:hover:bg-blue-700/40 hover:scale-105"
                        title={area.description}
                      >
                        {area.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>


          </div>
        </div>
      </motion.div>

      {/* Booking Wizard */}
      <BookingWizard
        isOpen={isBookingWizardOpen}
        onClose={handleCloseBookingWizard}
        ventureBuilder={profile}
      />
    </motion.div>
  );
};

export default VentureBuilderProfileModal;
