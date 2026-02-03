'use client';

import { useState } from 'react';
import { Calendar, ExternalLink, Save, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';

interface CalendarBookingUrlCardProps {
  currentUrl?: string;
  onUpdate?: (newUrl: string) => void;
}

export default function CalendarBookingUrlCard({
  currentUrl = '',
  onUpdate
}: CalendarBookingUrlCardProps) {
  const [url, setUrl] = useState(currentUrl);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  const handleUrlChange = (newUrl: string) => {
    setUrl(newUrl);
    setHasChanges(newUrl !== currentUrl);
  };

  const handleSave = async () => {
    // Validate URL
    if (url && !isValidUrl(url)) {
      toast.error('Please enter a valid URL');
      return;
    }

    try {
      setIsSaving(true);
      await ventureBuilderAPI.profile.update({
        calendar_booking_url: url || undefined,
      });

      toast.success('Calendar booking URL updated successfully!');
      setHasChanges(false);
      onUpdate?.(url);
    } catch (error: any) {
      console.error('Failed to update calendar URL:', error);
      toast.error(error.message || 'Failed to update calendar URL');
    } finally {
      setIsSaving(false);
    }
  };

  const isValidUrl = (urlString: string): boolean => {
    try {
      const url = new URL(urlString);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
      return false;
    }
  };

  const hasUrl = Boolean(url && url.trim());

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg border p-6 ${
      hasUrl
        ? 'border-green-200 dark:border-green-800'
        : 'border-gray-200 dark:border-gray-700'
    }`}>
      <div className="flex items-start gap-4">
        <div className={`p-3 rounded-lg ${
          hasUrl
            ? 'bg-green-100 dark:bg-green-900/20'
            : 'bg-gray-100 dark:bg-gray-700'
        }`}>
          {hasUrl ? (
            <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
          ) : (
            <Calendar className="w-6 h-6 text-gray-600 dark:text-gray-400" />
          )}
        </div>

        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Calendar Booking URL
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Provide a link to your calendar booking page (e.g., Calendly, Cal.com, Google Calendar appointment page).
            Founders will use this to schedule sessions with you.
          </p>

          {!hasUrl && (
            <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                    Calendar URL Not Set
                  </p>
                  <p className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">
                    You need to add your calendar booking URL before founders can book sessions with you.
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Booking Page URL
              </label>
              <div className="flex gap-2">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => handleUrlChange(e.target.value)}
                  placeholder="https://calendly.com/yourname or https://cal.com/yourname"
                  className="flex-1 px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                />
                <button
                  onClick={handleSave}
                  disabled={!hasChanges || isSaving}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      Save
                    </>
                  )}
                </button>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                Popular services: Calendly, Cal.com, Google Calendar Appointment Schedules, Acuity Scheduling
              </p>
            </div>

            {hasUrl && (
              <div className="p-4 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Current Booking Link
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 break-all">
                      {url}
                    </p>
                  </div>
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 ml-4 inline-flex items-center gap-1 text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300"
                  >
                    Preview
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
