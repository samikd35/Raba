'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { fetchMyVBProfile, updateMyVBProfile, deleteMyVBProfile } from '@/lib/api/venture-builder';
import { VBProfile } from '@/types/ventureBuilder';
import { Loader2, Edit, Trash2, Save, X, Mail, Linkedin, Briefcase, Star, Award, ArrowLeft } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function MyProfileView() {
  const router = useRouter();
  const { token } = useAuthStore();
  const [profile, setProfile] = useState<VBProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [editedProfile, setEditedProfile] = useState<Partial<VBProfile>>({});

  useEffect(() => {
    const loadProfile = async () => {
      if (!token) {
        router.push('/auth/login');
        return;
      }

      try {
        setIsLoading(true);
        const data = await fetchMyVBProfile(token);
        setProfile(data);
        setEditedProfile(data);
      } catch (error: any) {
        console.error('Error loading profile:', error);
        toast.error(error.message || 'Failed to load profile');
      } finally {
        setIsLoading(false);
      }
    };

    loadProfile();
  }, [token, router]);

  const handleEdit = () => {
    setIsEditing(true);
    setEditedProfile(profile || {});
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedProfile(profile || {});
  };

  const handleSave = async () => {
    if (!token) return;

    try {
      setIsSaving(true);
      const updated = await updateMyVBProfile(editedProfile, token);
      setProfile(updated);
      setIsEditing(false);
      toast.success('Profile updated successfully!');
    } catch (error: any) {
      console.error('Error updating profile:', error);
      toast.error(error.message || 'Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!token) return;

    const confirmed = window.confirm(
      'Are you sure you want to delete your Venture Builder profile? This action cannot be undone.'
    );

    if (!confirmed) return;

    try {
      setIsDeleting(true);
      await deleteMyVBProfile(token);
      toast.success('Profile deleted successfully');
      router.push('/');
    } catch (error: any) {
      console.error('Error deleting profile:', error);
      toast.error(error.message || 'Failed to delete profile');
    } finally {
      setIsDeleting(false);
    }
  };

  const updateField = <K extends keyof VBProfile>(field: K, value: VBProfile[K]) => {
    setEditedProfile(prev => ({ ...prev, [field]: value }));
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading your profile...</p>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 text-center">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Profile Not Found</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            You don't have a Venture Builder profile yet.
          </p>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-3 bg-primary hover:bg-primary/90 text-white rounded-lg font-semibold transition-colors"
          >
            Go to Home
          </button>
        </div>
      </div>
    );
  }

  const displayName = profile.full_name || profile.name || 'Venture Builder';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        {/* Back Button */}
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="font-medium">Back</span>
        </button>

        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                My Venture Builder Profile
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Manage your professional profile and settings
              </p>
            </div>
            <div className="flex gap-2">
              {!isEditing ? (
                <>
                  <button
                    onClick={handleEdit}
                    className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg font-medium transition-colors"
                  >
                    <Edit className="w-4 h-4" />
                    Edit Profile
                  </button>
                  <button
                    onClick={handleDelete}
                    disabled={isDeleting}
                    className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    {isDeleting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                    Delete
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    {isSaving ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    Save Changes
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    disabled={isSaving}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    <X className="w-4 h-4" />
                    Cancel
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Profile Content */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          {/* Profile Header */}
          <div className="p-6 bg-brand-50 dark:bg-brand-900/20 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-start gap-6">
              {/* Profile Picture */}
              <div className="flex-shrink-0">
                <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-white dark:border-gray-700 shadow-lg">
                  <img
                    src={profile.profile_picture_url}
                    alt={displayName}
                    className="w-full h-full object-cover"
                  />
                </div>
              </div>

              {/* Basic Info */}
              <div className="flex-1">
                {!isEditing ? (
                  <>
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                      {displayName}
                    </h2>
                    <p className="text-brand-600 dark:text-brand-400 font-medium mb-2">
                      {profile.main_expertise}
                    </p>
                    <p className="text-gray-600 dark:text-gray-400 mb-4">
                      {profile.short_intro}
                    </p>
                  </>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Full Name
                      </label>
                      <input
                        type="text"
                        value={(editedProfile.name || editedProfile.full_name) || ''}
                        onChange={(e) => updateField('name' as any, e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Main Expertise
                      </label>
                      <input
                        type="text"
                        value={editedProfile.main_expertise || ''}
                        onChange={(e) => updateField('main_expertise', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Short Introduction
                      </label>
                      <input
                        type="text"
                        value={editedProfile.short_intro || ''}
                        onChange={(e) => updateField('short_intro', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      />
                    </div>
                  </div>
                )}

                {/* Status Badges */}
                <div className="flex items-center gap-3 mt-4">
                  <span className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full text-sm font-medium flex items-center gap-1">
                    <Star className="w-3 h-3" />
                    Expert
                  </span>
                  <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium flex items-center gap-1">
                    <Award className="w-3 h-3" />
                    {profile.status || 'Active'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Contact & Links */}
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Contact Information
            </h3>
            {!isEditing ? (
              <div className="space-y-3">
                {profile.contact_email && (
                  <div className="flex items-center gap-3 text-gray-700 dark:text-gray-300">
                    <Mail className="w-5 h-5 text-gray-400" />
                    <a href={`mailto:${profile.contact_email}`} className="hover:text-brand-600">
                      {profile.contact_email}
                    </a>
                  </div>
                )}
                {profile.linkedin_url && (
                  <div className="flex items-center gap-3 text-gray-700 dark:text-gray-300">
                    <Linkedin className="w-5 h-5 text-gray-400" />
                    <a
                      href={profile.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-brand-600"
                    >
                      LinkedIn Profile
                    </a>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Contact Email
                  </label>
                  <input
                    type="email"
                    value={editedProfile.contact_email || ''}
                    onChange={(e) => updateField('contact_email', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    LinkedIn URL
                  </label>
                  <input
                    type="url"
                    value={editedProfile.linkedin_url || ''}
                    onChange={(e) => updateField('linkedin_url', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Biography */}
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Biography
            </h3>
            {!isEditing ? (
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                {profile.biography}
              </p>
            ) : (
              <textarea
                value={editedProfile.biography || ''}
                onChange={(e) => updateField('biography', e.target.value)}
                rows={6}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                placeholder="Write a detailed biography..."
              />
            )}
          </div>

          {/* Work Experience */}
          {profile.work_experience && profile.work_experience.length > 0 && (
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Briefcase className="w-5 h-5" />
                Work Experience
              </h3>
              <div className="space-y-4">
                {profile.work_experience.map((exp, index) => (
                  <div
                    key={index}
                    className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600"
                  >
                    <h4 className="font-semibold text-gray-900 dark:text-white">{exp.position}</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{exp.organization}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">{exp.years}</p>
                    {exp.description && (
                      <p className="text-sm text-gray-700 dark:text-gray-300 mt-2">{exp.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Expertise Areas */}
          {profile.expertise_areas && profile.expertise_areas.length > 0 && (
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Star className="w-5 h-5" />
                Areas of Expertise
              </h3>
              <div className="flex flex-wrap gap-2">
                {profile.expertise_areas.map((area) => (
                  <span
                    key={area.id}
                    className="px-3 py-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-lg text-sm font-medium"
                  >
                    {area.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Pricing */}
          {profile.credit_price_per_hour && (
            <div className="p-6 bg-brand-50 dark:bg-brand-900/20">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Session Pricing
              </h3>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-brand-600 dark:text-brand-400">
                  {profile.credit_price_per_hour}
                </span>
                <span className="text-gray-600 dark:text-gray-400">credits per hour</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
