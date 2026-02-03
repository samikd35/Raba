import {
  CheckCircle,
  XCircle,
  Clock,
  FileText,
} from 'lucide-react';
import type { ProfileStatus } from '@/types/cofounder';

export function getStatusConfig(status: ProfileStatus) {
  switch (status) {
    case 'approved':
      return {
        icon: CheckCircle,
        color: 'text-green-600 dark:text-green-400',
        bgColor: 'bg-green-50 dark:bg-green-900/20',
        borderColor: 'border-green-200 dark:border-green-800',
        label: 'Approved',
      };
    case 'submitted':
      return {
        icon: Clock,
        color: 'text-blue-600 dark:text-blue-400',
        bgColor: 'bg-blue-50 dark:bg-blue-900/20',
        borderColor: 'border-blue-200 dark:border-blue-800',
        label: 'Pending Review',
      };
    case 'rejected':
      return {
        icon: XCircle,
        color: 'text-red-600 dark:text-red-400',
        bgColor: 'bg-red-50 dark:bg-red-900/20',
        borderColor: 'border-red-200 dark:border-red-800',
        label: 'Rejected',
      };
    case 'draft':
    default:
      return {
        icon: FileText,
        color: 'text-gray-600 dark:text-gray-400',
        bgColor: 'bg-gray-50 dark:bg-gray-700/50',
        borderColor: 'border-gray-200 dark:border-gray-700',
        label: 'Draft',
      };
  }
}
