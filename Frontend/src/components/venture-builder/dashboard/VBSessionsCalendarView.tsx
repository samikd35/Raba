'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Calendar,
  Filter,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { getVBSessions } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import SessionDetailModal from './SessionDetailModal';
import type { VBSession, SessionStatus } from '@/types/ventureBuilder';

const DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const STATUS_COLORS: Record<SessionStatus, { bg: string; text: string; border: string }> = {
  confirmed: {
    bg: 'bg-blue-100 dark:bg-blue-900/40',
    text: 'text-blue-700 dark:text-blue-300',
    border: 'border-blue-300 dark:border-blue-700',
  },
  completed: {
    bg: 'bg-green-100 dark:bg-green-900/40',
    text: 'text-green-700 dark:text-green-300',
    border: 'border-green-300 dark:border-green-700',
  },
  settled: {
    bg: 'bg-purple-100 dark:bg-purple-900/40',
    text: 'text-purple-700 dark:text-purple-300',
    border: 'border-purple-300 dark:border-purple-700',
  },
  canceled: {
    bg: 'bg-gray-100 dark:bg-gray-800',
    text: 'text-gray-500 dark:text-gray-400',
    border: 'border-gray-300 dark:border-gray-600',
  },
  pending: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/40',
    text: 'text-yellow-700 dark:text-yellow-300',
    border: 'border-yellow-300 dark:border-yellow-700',
  },
};

interface VBSessionsCalendarViewProps {
  startHour?: number;
  endHour?: number;
  hourHeight?: number;
}

export default function VBSessionsCalendarView({
  startHour = 6,
  endHour = 22,
  hourHeight = 48,
}: VBSessionsCalendarViewProps) {
  const [sessions, setSessions] = useState<VBSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<SessionStatus | 'all'>('all');
  const [currentWeekStart, setCurrentWeekStart] = useState<Date>(() => {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek; // Monday as start
    const monday = new Date(today);
    monday.setDate(today.getDate() + diff);
    monday.setHours(0, 0, 0, 0);
    return monday;
  });
  const [selectedSession, setSelectedSession] = useState<VBSession | null>(null);

  const totalHours = endHour - startHour;

  // Calculate week dates
  const weekDates = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const date = new Date(currentWeekStart);
      date.setDate(currentWeekStart.getDate() + i);
      return date;
    });
  }, [currentWeekStart]);

  // Load sessions
  const loadSessions = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const data = await getVBSessions(token, {
        status_filter: statusFilter !== 'all' ? statusFilter : undefined,
      });
      setSessions(data);
    } catch (error: any) {
      console.error('Error fetching sessions:', error);
      setError(error.message || 'Failed to load sessions');
      toast.error(error.message || 'Failed to load sessions');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [statusFilter]);

  // Filter sessions for current week
  const weekSessions = useMemo(() => {
    const weekEnd = new Date(currentWeekStart);
    weekEnd.setDate(weekEnd.getDate() + 7);

    return sessions.filter((session) => {
      const sessionDate = new Date(session.session_datetime);
      return sessionDate >= currentWeekStart && sessionDate < weekEnd;
    });
  }, [sessions, currentWeekStart]);

  // Group sessions by day
  const sessionsByDay = useMemo(() => {
    const grouped: Record<number, VBSession[]> = {};
    for (let i = 0; i < 7; i++) {
      grouped[i] = [];
    }

    weekSessions.forEach((session) => {
      const sessionDate = new Date(session.session_datetime);
      const dayIndex = weekDates.findIndex(
        (d) => d.toDateString() === sessionDate.toDateString()
      );
      if (dayIndex !== -1) {
        grouped[dayIndex].push(session);
      }
    });

    return grouped;
  }, [weekSessions, weekDates]);

  // Navigation
  const goToPrevWeek = () => {
    const newStart = new Date(currentWeekStart);
    newStart.setDate(newStart.getDate() - 7);
    setCurrentWeekStart(newStart);
  };

  const goToNextWeek = () => {
    const newStart = new Date(currentWeekStart);
    newStart.setDate(newStart.getDate() + 7);
    setCurrentWeekStart(newStart);
  };

  const goToToday = () => {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
    const monday = new Date(today);
    monday.setDate(today.getDate() + diff);
    monday.setHours(0, 0, 0, 0);
    setCurrentWeekStart(monday);
  };

  // Format hour for display
  const formatHour = (hour: number): string => {
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour} ${period}`;
  };

  // Get session position on grid
  const getSessionPosition = (session: VBSession) => {
    const sessionDate = new Date(session.session_datetime);
    const hour = sessionDate.getHours();
    const minutes = sessionDate.getMinutes();
    const startOffset = hour - startHour + minutes / 60;
    const duration = session.session_duration_minutes / 60;

    return {
      top: Math.max(0, startOffset * hourHeight),
      height: Math.min(duration * hourHeight, (endHour - hour) * hourHeight),
    };
  };

  // Format week range
  const formatWeekRange = () => {
    const weekEnd = new Date(currentWeekStart);
    weekEnd.setDate(weekEnd.getDate() + 6);

    const startMonth = currentWeekStart.toLocaleDateString('en-US', { month: 'short' });
    const endMonth = weekEnd.toLocaleDateString('en-US', { month: 'short' });
    const startDay = currentWeekStart.getDate();
    const endDay = weekEnd.getDate();
    const year = currentWeekStart.getFullYear();

    if (startMonth === endMonth) {
      return `${startMonth} ${startDay} - ${endDay}, ${year}`;
    }
    return `${startMonth} ${startDay} - ${endMonth} ${endDay}, ${year}`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading sessions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-lg font-semibold text-red-900 dark:text-red-200 mb-2">
              Error Loading Sessions
            </h3>
            <p className="text-red-700 dark:text-red-300">{error}</p>
            <button
              onClick={loadSessions}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header Controls */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        {/* Week Navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={goToPrevWeek}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
          <button
            onClick={goToToday}
            className="px-3 py-1.5 text-sm font-medium text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded-lg transition-colors"
          >
            Today
          </button>
          <button
            onClick={goToNextWeek}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
          <span className="ml-2 text-lg font-semibold text-gray-900 dark:text-white">
            {formatWeekRange()}
          </span>
        </div>

        {/* Filter & Stats */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as SessionStatus | 'all')}
              className="px-3 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="all">All Status</option>
              <option value="confirmed">Confirmed</option>
              <option value="completed">Completed</option>
              <option value="settled">Settled</option>
              <option value="canceled">Canceled</option>
            </select>
          </div>
          <div className="px-3 py-1.5 bg-brand-100 dark:bg-brand-900/30 border border-brand-200 dark:border-brand-700 rounded-lg">
            <span className="text-sm font-semibold text-brand-700 dark:text-brand-300">
              {weekSessions.length} this week
            </span>
          </div>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-900">
        <div className="flex">
          {/* Time axis */}
          <div className="w-16 flex-shrink-0 border-r border-gray-200 dark:border-gray-700">
            {/* Empty header cell */}
            <div className="h-16 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50" />

            {/* Hour labels */}
            <div className="relative" style={{ height: `${totalHours * hourHeight}px` }}>
              {Array.from({ length: totalHours }, (_, i) => (
                <div
                  key={i}
                  className="absolute left-0 right-0 flex items-start justify-end pr-2 -translate-y-2"
                  style={{ top: `${i * hourHeight}px` }}
                >
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {formatHour(startHour + i)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Day columns */}
          <div className="flex-1 grid grid-cols-7">
            {weekDates.map((date, dayIndex) => {
              const isToday = date.toDateString() === new Date().toDateString();
              const daySessions = sessionsByDay[dayIndex] || [];

              return (
                <div
                  key={dayIndex}
                  className="border-r border-gray-200 dark:border-gray-700 last:border-r-0"
                >
                  {/* Day header */}
                  <div
                    className={`h-16 border-b border-gray-200 dark:border-gray-700 p-2 text-center ${
                      isToday ? 'bg-brand-50 dark:bg-brand-900/20' : 'bg-gray-50 dark:bg-gray-800/50'
                    }`}
                  >
                    <div className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                      {DAYS_OF_WEEK[dayIndex]}
                    </div>
                    <div
                      className={`text-lg font-semibold mt-1 ${
                        isToday
                          ? 'text-brand-600 dark:text-brand-400'
                          : 'text-gray-900 dark:text-white'
                      }`}
                    >
                      {date.getDate()}
                    </div>
                  </div>

                  {/* Time slots with sessions */}
                  <div
                    className="relative"
                    style={{ height: `${totalHours * hourHeight}px` }}
                  >
                    {/* Hour grid lines */}
                    {Array.from({ length: totalHours }, (_, i) => (
                      <div
                        key={i}
                        className="absolute left-0 right-0 border-b border-gray-100 dark:border-gray-800"
                        style={{ top: `${i * hourHeight}px`, height: `${hourHeight}px` }}
                      />
                    ))}

                    {/* Session blocks */}
                    {daySessions.map((session) => {
                      const { top, height } = getSessionPosition(session);
                      const colors = STATUS_COLORS[session.status] || STATUS_COLORS.pending;
                      const sessionTime = new Date(session.session_datetime);

                      return (
                        <button
                          key={session.id}
                          onClick={() => setSelectedSession(session)}
                          className={`absolute left-1 right-1 rounded-md border overflow-hidden cursor-pointer hover:shadow-md transition-shadow ${colors.bg} ${colors.border}`}
                          style={{ top: `${top}px`, height: `${Math.max(height, 24)}px` }}
                        >
                          <div className={`p-1.5 h-full ${colors.text}`}>
                            <div className="text-xs font-semibold truncate">
                              {sessionTime.toLocaleTimeString('en-US', {
                                hour: 'numeric',
                                minute: '2-digit',
                              })}
                            </div>
                            {height > 36 && (
                              <div className="text-xs truncate opacity-80">
                                {session.user_name ||
                                  session.vb_email ||
                                  session.booked_by_user_id.substring(0, 8)}
                              </div>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Empty state */}
      {sessions.length === 0 && (
        <div className="text-center py-8">
          <Calendar className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-gray-600 dark:text-gray-400">No sessions found</p>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 text-xs">
        {Object.entries(STATUS_COLORS).map(([status, colors]) => (
          <div key={status} className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded ${colors.bg} ${colors.border} border`} />
            <span className="text-gray-600 dark:text-gray-400 capitalize">{status}</span>
          </div>
        ))}
      </div>

      {/* Session Detail Modal */}
      {selectedSession && (
        <SessionDetailModal
          session={selectedSession}
          onClose={() => setSelectedSession(null)}
          onSessionUpdated={loadSessions}
        />
      )}
    </div>
  );
}
