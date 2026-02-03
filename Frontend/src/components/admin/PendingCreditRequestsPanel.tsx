"use client";

import React, { useState, useEffect } from 'react';
import { creditRequestService } from '@/lib/api/creditRequestService';
import { CreditRequest } from '@/types/team';
import { toast } from "react-hot-toast";
import { Clock, AlertCircle, Eye } from 'lucide-react';
import CreditRequestReviewModal from './CreditRequestReviewModal';

interface PendingCreditRequestsPanelProps {
  organizationId: string;
}

export default function PendingCreditRequestsPanel({ organizationId }: PendingCreditRequestsPanelProps) {
  const [requests, setRequests] = useState<CreditRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState<CreditRequest | null>(null);
  const [showReviewModal, setShowReviewModal] = useState(false);

  useEffect(() => {
    fetchRequests();
  }, [organizationId]);

  const fetchRequests = async () => {
    setIsLoading(true);
    try {
      const data = await creditRequestService.getOrganizationCreditRequests(organizationId);
      setRequests(data);
    } catch (error: any) {
      console.error('Failed to fetch credit requests:', error);
      toast.error('Failed to load credit requests');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReview = (request: CreditRequest) => {
    setSelectedRequest(request);
    setShowReviewModal(true);
  };

  const handleReviewComplete = () => {
    fetchRequests(); // Refresh the list
  };

  const pendingRequests = requests.filter(r => r.status === 'pending');

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
              <Clock className="w-5 h-5" />
              <span>Pending Credit Requests</span>
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Review and approve credit requests from team leaders
            </p>
          </div>
          {pendingRequests.length > 0 && (
            <span className="px-3 py-1 bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded-full text-sm font-medium">
              {pendingRequests.length} Pending
            </span>
          )}
        </div>

        {pendingRequests.length === 0 ? (
          <div className="text-center py-12">
            <Clock className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">No pending credit requests</p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
              Requests from team leaders will appear here
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {pendingRequests.map((request) => (
              <div
                key={request.request_id}
                className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="font-medium text-gray-900 dark:text-white">
                        {request.team_name || 'Unknown Team'}
                      </h3>
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full text-xs font-medium">
                        {request.requested_credits.toLocaleString()} credits
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                      <p>
                        <span className="font-medium">Requester:</span> {request.requester_name} ({request.requester_email})
                      </p>
                      {request.reason && (
                        <p>
                          <span className="font-medium">Reason:</span> {request.reason}
                        </p>
                      )}
                      <p className="text-xs text-gray-500 dark:text-gray-500">
                        Submitted: {new Date(request.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleReview(request)}
                    className="ml-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm flex items-center space-x-2 transition-colors"
                  >
                    <Eye className="w-4 h-4" />
                    <span>Review</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Show all requests count */}
        {requests.length > pendingRequests.length && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
              {requests.length - pendingRequests.length} completed request(s) in history
            </p>
          </div>
        )}
      </div>

      {/* Review Modal */}
      <CreditRequestReviewModal
        isOpen={showReviewModal}
        onClose={() => {
          setShowReviewModal(false);
          setSelectedRequest(null);
        }}
        request={selectedRequest}
        organizationId={organizationId}
        onReviewComplete={handleReviewComplete}
      />
    </>
  );
}
