// components/cofounder/hooks/useReportModal.ts
import { useState } from 'react';

interface UseReportModalReturn {
  isOpen: boolean;
  targetId: string | null;
  targetName: string | null;
  reportType: 'profile' | 'message' | null;
  openReportModal: (params: {
    type: 'profile' | 'message';
    id: string;
    name?: string;
  }) => void;
  closeReportModal: () => void;
}

/**
 * Hook for managing cofounder report modal state
 * Makes it easy to integrate reporting functionality into cofounder components
 */
export function useReportModal(): UseReportModalReturn {
  const [isOpen, setIsOpen] = useState(false);
  const [targetId, setTargetId] = useState<string | null>(null);
  const [targetName, setTargetName] = useState<string | null>(null);
  const [reportType, setReportType] = useState<'profile' | 'message' | null>(null);

  const openReportModal = ({
    type,
    id,
    name,
  }: {
    type: 'profile' | 'message';
    id: string;
    name?: string;
  }) => {
    setReportType(type);
    setTargetId(id);
    setTargetName(name || null);
    setIsOpen(true);
  };

  const closeReportModal = () => {
    setIsOpen(false);
    // Small delay before clearing to allow modal close animation
    setTimeout(() => {
      setTargetId(null);
      setTargetName(null);
      setReportType(null);
    }, 300);
  };

  return {
    isOpen,
    targetId,
    targetName,
    reportType,
    openReportModal,
    closeReportModal,
  };
}
