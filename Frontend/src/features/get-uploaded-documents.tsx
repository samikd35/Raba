"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import toast from "react-hot-toast";
import { 
  FileText, 
  Table, 
  Loader2,
  RefreshCw,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Users,
  File
} from "lucide-react";
import { useAuthStore } from "@/stores/authStore";

interface DocumentMetadata {
  filename: string;
  file_size: number;
  parsed_at: string;
  persona_id: string;
  total_pages?: number;
  total_words?: number;
  content_type: string;
  failed_pages?: number[];
  extracted_pages?: number;
}

interface ProcessingStatus {
  status: 'completed' | 'processing' | 'failed';
  chunks: number;
  error_message: string | null;
  updated_at: string;
}

interface Document {
  document_type: 'pdf' | 'csv';
  filename: string;
  file_size: number;
  chunks_count: number;
  processing_status: ProcessingStatus;
  persona_id: string;
  metadata: DocumentMetadata;
}

interface DocumentsResponse {
  project_id: string;
  documents: Document[];
  total_documents: number;
  total_chunks: number;
}

interface GetUploadedDocumentsProps {
  projectId: string;
  setViewAnalysis?: (value: boolean) => void;
  refreshTrigger?: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const GetUploadedDocuments: React.FC<GetUploadedDocumentsProps> = ({ projectId, setViewAnalysis, refreshTrigger }) => {
  const router = useRouter();
  const { isAuthenticated, token } = useAuthStore();

  const [documents, setDocuments] = useState<Document[]>([]);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [totalChunks, setTotalChunks] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchDocuments = useCallback(async () => {
    if (!isAuthenticated || !token || !projectId) return;

    try {
      setIsLoading(true);
      setError(null);

      if (process.env.NODE_ENV === 'development') {
        console.log('📥 Fetching uploaded documents, refreshTrigger:', refreshTrigger);
      }

      const response = await fetch(
        `${API_URL}/api/v1/market-research/analysis/projects/${projectId}/documents`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        setViewAnalysis?.(false);
        throw new Error(`Failed to fetch documents: ${response.status}`);
      }
      const data: DocumentsResponse = await response.json();
      setDocuments(data.documents || []);
      setTotalDocuments(data.total_documents || 0);
      setTotalChunks(data.total_chunks || 0);

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Documents fetched:', data.total_documents);
      }

    } catch (err: any) {
      setError(err.message || 'Failed to load documents');
      toast.error('Failed to load uploaded documents');
      setViewAnalysis?.(false);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, token, isAuthenticated, setViewAnalysis, refreshTrigger]);

  useEffect(() => {
    fetchDocuments();
    if (documents.length === 0) {
      setViewAnalysis?.(false);
    }
  }, [fetchDocuments]);

  useEffect(() => {
    if (typeof setViewAnalysis === 'function') {
      if (documents.length === 0) {
        setViewAnalysis(false);
      }
      if (documents.length > 0) {
        setViewAnalysis(true);
      }
    }
  }, [documents.length, setViewAnalysis]);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const groupDocumentsByPersona = () => {
    const grouped: { [personaId: string]: Document[] } = {};
    documents.forEach(doc => {
      if (!grouped[doc.persona_id]) {
        grouped[doc.persona_id] = [];
      }
      grouped[doc.persona_id].push(doc);
    });
    return grouped;
  };

  const handleDeleteClick = useCallback((doc: Document) => {
    setDocumentToDelete(doc);
    setIsDeleteModalOpen(true);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!documentToDelete || !token || !projectId) return;

    try {
      setIsDeleting(true);
      
      // Build URL with optional persona_id query parameter
      const url = new URL(
        `${API_URL}/api/v1/market-research/analysis/projects/${projectId}/documents/${encodeURIComponent(documentToDelete.filename)}`
      );
      
      if (documentToDelete.persona_id) {
        url.searchParams.append('persona_id', documentToDelete.persona_id);
      }

      const response = await fetch(url.toString(), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Failed to delete document: ${response.status}`);
      }

      const data = await response.json();
      
      toast.success(data.message || 'Document deleted successfully');
      
      // Close modal and reset state
      setIsDeleteModalOpen(false);
      setDocumentToDelete(null);
      
      // Refresh documents list
      await fetchDocuments();
      
    } catch (err: any) {
      console.error('Delete error:', err);
      toast.error(err.message || 'Failed to delete document');
    } finally {
      setIsDeleting(false);
    }
  }, [documentToDelete, token, projectId, fetchDocuments]);

  const handleDeleteCancel = useCallback(() => {
    setIsDeleteModalOpen(false);
    setDocumentToDelete(null);
  }, []);

  if (!isAuthenticated) {
    router.push('/signin');
    return null;
  }

  if (isLoading) {
    return (
      <Card className="p-6 mt-6">
        <div className="flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-brand-500" />
          <span>Loading uploaded documents...</span>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6 mt-6 border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-red-900 dark:text-red-100 mb-1">
              Error Loading Documents
            </h3>
            <p className="text-red-700 dark:text-red-300 text-sm mb-4">{error}</p>
            <Button onClick={fetchDocuments} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  if (documents.length === 0) {
    return (
      <Card className="p-6 mt-6 border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50">
        <div className="flex items-start gap-3">
          <File className="h-5 w-5 text-gray-500 mt-0.5" />
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
              No Documents Uploaded
            </h3>
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              Upload PDF interviews or CSV survey data to get started with analysis.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const groupedDocuments = groupDocumentsByPersona();

  return (
    <div className="mt-6">
      <Card className="p-6">
        <div className="flex items-center justify-between ">
          <div>
            <h2 className="text-xl font-bold text-brand-500 dark:text-white">
              Uploaded Documents
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {totalDocuments} document{totalDocuments !== 1 ? 's' : ''}
            </p>
          </div>
          <Button onClick={fetchDocuments} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {Object.entries(groupedDocuments).map(([personaId, docs]) => (
          <div key={personaId} className="mb-6 last:mb-0">
           

            <div className="space-y-3">
              {docs.map((doc, index) => (
                <div
                  key={`${doc.filename}-${index}`}
                  className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      {doc.document_type === 'pdf' ? (
                        <FileText className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
                      ) : (
                        <Table className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
                      )}
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="text-sm font-medium truncate">{doc.filename}</p>
                          {doc.processing_status.status === 'completed' && (
                            <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                          )}
                          {doc.processing_status.status === 'processing' && (
                            <Loader2 className="h-4 w-4 text-blue-500 animate-spin flex-shrink-0" />
                          )}
                          {doc.processing_status.status === 'failed' && (
                            <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                          )}
                        </div>

                        <div className="flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400">
                          <span>{formatFileSize(doc.file_size)}</span>
                          <span>•</span>
                          <span>{doc.chunks_count} chunks</span>
                          {doc.metadata.total_pages && (
                            <>
                              <span>•</span>
                              <span>{doc.metadata.total_pages} pages</span>
                            </>
                          )}
                          {doc.metadata.total_words && (
                            <>
                              <span>•</span>
                              <span>{doc.metadata.total_words.toLocaleString()} words</span>
                            </>
                          )}
                          <span>•</span>
                          <span>{formatDate(doc.processing_status.updated_at)}</span>
                        </div>

                        {doc.processing_status.status === 'completed' && (
                          <Badge variant="default" className="mt-2 bg-green-500 hover:bg-green-600">
                            Processed
                          </Badge>
                        )}
                        {doc.processing_status.status === 'processing' && (
                          <Badge variant="default" className="mt-2 bg-blue-500 hover:bg-blue-600">
                            Processing...
                          </Badge>
                        )}
                        {doc.processing_status.status === 'failed' && (
                          <div className="mt-2">
                            <Badge variant="destructive">Failed</Badge>
                            {doc.processing_status.error_message && (
                              <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                                {doc.processing_status.error_message}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    <Button
                      onClick={() => handleDeleteClick(doc)}
                      variant="ghost"
                      size="sm"
                      className="ml-2 text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:text-red-300 dark:hover:bg-red-900/20"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </Card>

      {/* Delete Confirmation Modal */}
      <Dialog open={isDeleteModalOpen} onOpenChange={setIsDeleteModalOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600 dark:text-red-400">
              <AlertCircle className="h-5 w-5" />
              Delete Document
            </DialogTitle>
            <DialogDescription className="pt-3">
              Are you sure you want to delete this document? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          
          {documentToDelete && (
            <div className="py-4">
              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-start gap-3">
                  {documentToDelete.document_type === 'pdf' ? (
                    <FileText className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
                  ) : (
                    <Table className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{documentToDelete.filename}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {formatFileSize(documentToDelete.file_size)} • {documentToDelete.chunks_count} chunks
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              onClick={handleDeleteCancel}
              variant="outline"
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleDeleteConfirm}
              variant="destructive"
              disabled={isDeleting}
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default GetUploadedDocuments;