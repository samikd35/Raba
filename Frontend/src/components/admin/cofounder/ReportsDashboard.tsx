'use client';

import { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Filter,
  Search,
  Loader2,
} from 'lucide-react';
import { reportAPI } from '@/lib/api/reportService';
import type {
  Report,
  ReportStatus,
  ReportType,
  ReportStatistics,
} from '@/types/reports';
import { REPORT_REASON_LABELS } from '@/types/reports';
import ReportDetailModal from '@/components/cofounder/reports/ReportDetailModal';
import { useRouter } from 'next/navigation';


export default function ReportsDashboard() {
  const router = useRouter();
  const [reports, setReports] = useState<Report[]>([]);
  const [statistics, setStatistics] = useState<ReportStatistics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  // Filters
  const [statusFilter, setStatusFilter] = useState<ReportStatus | 'ALL'>('ALL');
  const [typeFilter, setTypeFilter] = useState<ReportType | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 20;

  // Load statistics
  useEffect(() => {
    loadStatistics();
  }, []);

  // Load reports when filters change
  useEffect(() => {
    loadReports();
  }, [statusFilter, typeFilter, currentPage]);

  const loadStatistics = async () => {
    try {
      const stats = await reportAPI.admin.getStatistics();
      setStatistics(stats);
    } catch (error: any) {
      console.error('Failed to load statistics:', error);
      toast.error('Failed to load report statistics');
    }
  };

  const loadReports = async () => {
    try {
      setIsLoading(true);
      const response = await reportAPI.admin.listReports({
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        report_type: typeFilter === 'ALL' ? undefined : typeFilter,
        page: currentPage,
        page_size: pageSize,
      });

      setReports(response.data);
      setTotalPages(Math.ceil(response.total / pageSize));
    } catch (error: any) {
      console.error('Failed to load reports:', error);
      toast.error('Failed to load reports');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReportClick = (report: Report) => {
    setSelectedReport(report);
    setShowDetailModal(true);
  };

  const handleReportResolved = () => {
    // Reload reports and statistics after resolution
    loadReports();
    loadStatistics();
    setShowDetailModal(false);
  };

  const getStatusBadge = (status: ReportStatus) => {
    const styles = {
      PENDING: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
      REVIEWED: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
      ACTIONED: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
      NO_ACTION: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    };

    const icons = {
      PENDING: <Clock className="w-3 h-3" />,
      REVIEWED: <AlertTriangle className="w-3 h-3" />,
      ACTIONED: <CheckCircle className="w-3 h-3" />,
      NO_ACTION: <XCircle className="w-3 h-3" />,
    };

    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${styles[status]}`}
      >
        {icons[status]}
        {status.replace('_', ' ')}
      </span>
    );
  };

  const getTypeBadge = (type: ReportType) => {
    const styles = {
      PROFILE: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
      MESSAGE: 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300',
    };

    return (
      <span
        className={`px-2.5 py-1 rounded-full text-xs font-medium ${styles[type]}`}
      >
        {type}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Reports Dashboard
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage and review user reports
            </p>
          </div>

          {/* Toggle Switch */}
            <div className="flex items-center gap-2 bg-white dark:bg-gray-800 p-1 rounded-lg border border-gray-200 dark:border-gray-700">
              <button
                onClick={() => router.push('/admin/cofounder-moderation')}
                className="px-4 py-2 rounded border border-brand-400 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Moderation
              </button>
              <button
                onClick={() => router.push('/admin/enums')}
                className="px-4 py-2 rounded border border-brand-400 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Enums
              </button>

              <button
                className="px-4 py-2 rounded border border-blue-light-200 text-sm font-medium bg-brand-500 text-white"
              >
                Report Managment
              </button>
            </div>
        </div>

        {/* Statistics Cards */}
        {statistics && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Reports</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {statistics.total_reports}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-yellow-200 dark:border-yellow-800 p-4">
              <p className="text-sm text-yellow-700 dark:text-yellow-300">Pending</p>
              <p className="text-2xl font-bold text-yellow-900 dark:text-yellow-200 mt-1">
                {statistics.pending_reports}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-blue-200 dark:border-blue-800 p-4">
              <p className="text-sm text-blue-700 dark:text-blue-300">Reviewed</p>
              <p className="text-2xl font-bold text-blue-900 dark:text-blue-200 mt-1">
                {statistics.reviewed_reports}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-green-200 dark:border-green-800 p-4">
              <p className="text-sm text-green-700 dark:text-green-300">Actioned</p>
              <p className="text-2xl font-bold text-green-900 dark:text-green-200 mt-1">
                {statistics.actioned_reports}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">No Action</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {statistics.no_action_reports}
              </p>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-500" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Filters:
              </span>
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as ReportStatus | 'ALL');
                setCurrentPage(1);
              }}
              className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500"
            >
              <option value="ALL">All Status</option>
              <option value="PENDING">Pending</option>
              <option value="REVIEWED">Reviewed</option>
              <option value="ACTIONED">Actioned</option>
              <option value="NO_ACTION">No Action</option>
            </select>

            {/* Type Filter */}
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value as ReportType | 'ALL');
                setCurrentPage(1);
              }}
              className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500"
            >
              <option value="ALL">All Types</option>
              <option value="PROFILE">Profile Reports</option>
              <option value="MESSAGE">Message Reports</option>
            </select>
          </div>
        </div>

        {/* Reports Table */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
            </div>
          ) : reports.length === 0 ? (
            <div className="text-center p-12">
              <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400">No reports found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Reason
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Reported At
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {reports.map((report) => (
                    <tr
                      key={report.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getTypeBadge(report.report_type)}
                      </td>
                      <td className="px-6 py-4">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {REPORT_REASON_LABELS[report.reason]}
                        </p>
                        {report.description && (
                          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 truncate max-w-xs">
                            {report.description}
                          </p>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(report.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {new Date(report.created_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <button
                          onClick={() => handleReportClick(report)}
                          className="text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 text-sm font-medium"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {!isLoading && reports.length > 0 && totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Report Detail Modal */}
      {selectedReport && (
        <ReportDetailModal
          isOpen={showDetailModal}
          onClose={() => setShowDetailModal(false)}
          report={selectedReport}
          onResolved={handleReportResolved}
        />
      )}
    </div>
  );
}
