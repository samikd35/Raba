"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import toast from "react-hot-toast";
import { 
  Upload, 
  FileText, 
  Table, 
  X, 
  CheckCircle2, 
  AlertCircle,
  Loader2,
  Users,
  Info
} from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { MarketAnalysisLoader } from "@/components/ui/market-analysis-loader";

interface Persona {
  id: string;
  name: string;
}

interface FileWithMetadata {
  file: File;
  id: string;
  type: 'pdf' | 'csv';
  personaId?: string;
}

interface PersonaFilesMap {
  [personaId: string]: FileWithMetadata[];
}

interface MarketResearchAnalysisUploadProps {
  projectId: string;
  viewAnalysis?: boolean;
  onDocumentChange?: () => void;
  path?: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const MAX_PDF_FILES = 25;
const MAX_CSV_FILES = 5;
const MAX_FILE_SIZE = 25 * 1024 * 1024;

const MarketResearchAnalysisUpload: React.FC<MarketResearchAnalysisUploadProps> = ({ path = 'workspace', projectId, viewAnalysis, onDocumentChange }) => {
  const router = useRouter();
  const { isAuthenticated, token } = useAuthStore();

  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selectedPersona, setSelectedPersona] = useState<string>("");
  const [personaFiles, setPersonaFiles] = useState<PersonaFilesMap>({});
  const [isLoadingPersonas, setIsLoadingPersonas] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [showFilesDialog, setShowFilesDialog] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const pdfInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Market analysis loading states
  const marketAnalysisSteps = [
    {
      text: "Parsing raw market research to capture the overall gist",
    },
    {
      text: "Extracting customer pain points related to Assumption 1",
    },
    {
      text: "Identifying customer gains related to Assumption 2",
      },
    {
      text: "Mapping Jobs-to-be-Done related to Assumption 3",
    },
    {
      text: "Surfacing key insights and running validation rate checks",
    },
    {
      text: "Consolidating everything into a structured market findings report",
    }
  ];

  useEffect(() => {
    if (!isAuthenticated || !token || !projectId) return;
    fetchPersonas();
  }, [isAuthenticated, token, projectId]);

  const fetchPersonas = useCallback(async () => {
    try {
      setIsLoadingPersonas(true);
      const response = await fetch(
        `${API_URL}/api/v2/vmp/projects/${projectId}/personas`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      if (!response.ok) throw new Error('Failed to fetch personas');
      const data = await response.json();
      const personasList = data.data?.personas || [];
      setPersonas(personasList);
      if (personasList.length === 1) setSelectedPersona(personasList[0].id);
    } catch (error) {
      toast.error('Failed to load personas');
    } finally {
      setIsLoadingPersonas(false);
    }
  }, [projectId, token]);

  const validateFile = useCallback((file: File, type: 'pdf' | 'csv'): string | null => {
    if (file.size > MAX_FILE_SIZE) {
      return `File too large: ${(file.size / 1024 / 1024).toFixed(2)}MB (max: 25MB)`;
    }
    if (type === 'pdf' && file.type !== 'application/pdf') {
      return `Invalid PDF file type`;
    }
    if (type === 'csv') {
      const validTypes = ['text/csv', 'application/csv', 'text/plain'];
      if (!validTypes.includes(file.type) && !file.name.endsWith('.csv')) {
        return `Invalid CSV file type`;
      }
    }
    return null;
  }, []);

  const handleFileSelect = useCallback((files: FileList | null, type: 'pdf' | 'csv') => {
    if (!files || files.length === 0) return;
    
    // For multi-persona projects, require persona selection
    if (personas.length > 1 && !selectedPersona) {
      toast.error('Please select a persona first');
      return;
    }

    const fileArray = Array.from(files);
    const currentPersonaId = personas.length === 1 ? personas[0].id : selectedPersona;
    const currentFiles = personaFiles[currentPersonaId] || [];
    
    // Count files by type for this persona
    const currentPdfCount = currentFiles.filter(f => f.type === 'pdf').length;
    const currentCsvCount = currentFiles.filter(f => f.type === 'csv').length;
    const newFilesOfType = fileArray.length;
    
    const maxFiles = type === 'pdf' ? MAX_PDF_FILES : MAX_CSV_FILES;
    const currentCount = type === 'pdf' ? currentPdfCount : currentCsvCount;

    if (currentCount + newFilesOfType > maxFiles) {
      toast.error(`Maximum ${maxFiles} ${type.toUpperCase()} files allowed per persona`);
      return;
    }

    const newFiles: FileWithMetadata[] = [];
    const errors: string[] = [];

    fileArray.forEach(file => {
      const error = validateFile(file, type);
      if (error) {
        errors.push(`${file.name}: ${error}`);
      } else {
        newFiles.push({
          file,
          id: `${type}_${Date.now()}_${Math.random()}`,
          type,
          personaId: currentPersonaId
        });
      }
    });

    if (errors.length > 0) toast.error(`Validation errors: ${errors[0]}`);
    if (newFiles.length > 0) {
      setPersonaFiles(prev => ({
        ...prev,
        [currentPersonaId]: [...(prev[currentPersonaId] || []), ...newFiles]
      }));
      const personaName = personas.find(p => p.id === currentPersonaId)?.name || 'Selected persona';
      toast.success(`Added ${newFiles.length} ${type.toUpperCase()} file(s) for ${personaName}`);
      onDocumentChange?.();
    }
  }, [personas, selectedPersona, personaFiles, validateFile, onDocumentChange]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;

    const pdfList: File[] = [];
    const csvList: File[] = [];
    Array.from(files).forEach(file => {
      if (file.type === 'application/pdf') pdfList.push(file);
      else if (file.type.includes('csv') || file.name.endsWith('.csv')) csvList.push(file);
    });

    if (pdfList.length > 0) {
      const dt = new DataTransfer();
      pdfList.forEach(f => dt.items.add(f));
      handleFileSelect(dt.files, 'pdf');
    }
    if (csvList.length > 0) {
      const dt = new DataTransfer();
      csvList.forEach(f => dt.items.add(f));
      handleFileSelect(dt.files, 'csv');
    }
  }, [handleFileSelect]);

  const removeFile = useCallback((fileId: string, personaId: string) => {
    setPersonaFiles(prev => ({
      ...prev,
      [personaId]: (prev[personaId] || []).filter(f => f.id !== fileId)
    }));
    onDocumentChange?.();
  }, [onDocumentChange]);

  const handleUpload = useCallback(async () => {
    // Check if all personas have files
    const personasWithoutFiles = personas.filter(p => {
      const files = personaFiles[p.id] || [];
      return files.length === 0;
    });

    if (personasWithoutFiles.length > 0) {
      const missingNames = personasWithoutFiles.map(p => p.name).join(', ');
      toast.error(`Please upload files for all personas. Missing: ${missingNames}`);
      return;
    }

    if (personas.length === 0) {
      toast.error('Please complete persona identification first');
      return;
    }

    try {
      setIsUploading(true);
      setUploadProgress(0);

      const totalPersonas = personas.length;
      let completedPersonas = 0;

      // Upload files for each persona sequentially
      for (const persona of personas) {
        const files = personaFiles[persona.id] || [];
        if (files.length === 0) continue;

        abortControllerRef.current = new AbortController();

        const formData = new FormData();
        files.forEach(f => {
          if (f.type === 'pdf') formData.append('pdf_files', f.file);
          else formData.append('csv_files', f.file);
        });
        formData.append('persona_id', persona.id);
        formData.append('enable_enhanced_processing', 'true');
        formData.append('extract_statistics', 'true');
        formData.append('enable_fact_validation', 'true');

        const uploadPromise = new Promise<any>((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
              // Calculate progress: (completed personas + current upload progress) / total personas
              const currentPersonaProgress = (e.loaded / e.total);
              const overallProgress = ((completedPersonas + currentPersonaProgress) / totalPersonas) * 100;
              setUploadProgress(Math.round(overallProgress));
            }
          });
          xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve(JSON.parse(xhr.responseText));
            } else {
              try {
                reject(JSON.parse(xhr.responseText));
              } catch {
                reject(new Error(`Upload failed: ${xhr.status}`));
              }
            }
          });
          xhr.addEventListener('error', () => reject(new Error('Network error')));
          xhr.addEventListener('abort', () => reject(new Error('Upload cancelled')));
          xhr.open('POST', `${API_URL}/api/v1/market-research/analysis/projects/${projectId}/upload-documents`);
          xhr.setRequestHeader('Authorization', `Bearer ${token}`);
          xhr.send(formData);
          if (abortControllerRef.current) {
            abortControllerRef.current.signal.addEventListener('abort', () => xhr.abort());
          }
        });

        const response = await uploadPromise;
        if (response.success) {
          completedPersonas++;
          // Update progress to reflect completed persona
          setUploadProgress(Math.round((completedPersonas / totalPersonas) * 100));
          toast.success(`Files uploaded successfully for ${persona.name}!`);
        }
      }

      // Clear all files after successful upload
      setPersonaFiles({});
      setUploadProgress(100);
      toast.success('All files uploaded successfully!');
      
      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 Upload complete! Calling onDocumentChange callback...');
      }
      onDocumentChange?.();
      
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ onDocumentChange callback executed');
      }
    } catch (error: any) {
      if (error.error === 'persona_id_required') {
        toast.error(error.message);
      } else if (error.message === 'Upload cancelled') {
        toast('Upload cancelled');
      } else {
        toast.error(error.message || 'Upload failed');
      }
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
      abortControllerRef.current = null;
    }
  }, [personas, personaFiles, projectId, token, onDocumentChange]);

  // Calculate total files and personas with files
  const totalFiles = Object.values(personaFiles).reduce((sum, files) => sum + files.length, 0);
  const personasWithFiles = personas.filter(p => (personaFiles[p.id] || []).length > 0);
  const allPersonasHaveFiles = personas.length > 0 && personasWithFiles.length === personas.length;

  const analyzeMarketResearch = useCallback(async () => {
    // Validation: Check if all personas have files


    if (!token || !projectId) {
      toast.error('Authentication required');
      router.push('/signin');
      return;
    }

    try {
      setIsAnalyzing(true);

      if (process.env.NODE_ENV === 'development') {
        console.log('🔍 Starting Market Research Analyzer for project:', projectId);
      }

      const response = await fetch(
        `${API_URL}/api/v1/market-research/analysis/projects/${projectId}/execute`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Analysis failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Analysis result:', result);
      }

      if (result.success) {
        const { data } = result;
        const successCount = data.successful_personas?.length || 0;
        const totalCount = data.total_personas || 0;
        const failedCount = data.failed_personas?.length || 0;

        if (data.status === 'completed' && failedCount === 0) {
          // Navigate to results or next step
          // Adjust the route based on your application flow
          const targetPath = `/${path}/market-research-analysis/${projectId}`;
          if (process.env.NODE_ENV === 'development') {
            console.log('➡️ Navigating to analysis page:', targetPath);
          }
          safeNavigate(targetPath);
        } else if (failedCount > 0) {
          toast.error(
            `Analysis completed with errors: ${successCount} succeeded, ${failedCount} failed`,
            { duration: 6000 }
          );
        } else {
          toast.success(result.message || 'Analysis completed successfully');
        }
      } else {
        throw new Error(result.message || 'Analysis failed');
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Analysis error:', error);
      }
      
      const errorMessage = error instanceof Error ? error.message : 'Failed to analyze market research';
      toast.error(errorMessage, { duration: 5000 });
    } finally {
      setIsAnalyzing(false);
    }
  }, [allPersonasHaveFiles, token, projectId, router]);

  // Safe navigation that falls back to full-page navigation if client router is blocked
  const safeNavigate = useCallback((to: string) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('➡️ Attempting navigation to:', to);
    }
    try {
      const before = typeof window !== 'undefined' ? window.location.pathname : '';
      router.push(to);
      // Fallback: if still on the same path after a short delay, force navigate
      if (typeof window !== 'undefined') {
        setTimeout(() => {
          const now = window.location.pathname;
          if (process.env.NODE_ENV === 'development') {
            console.log('🧭 Navigation check — before:', before, 'now:', now);
          }
          if (now !== to) {
            if (process.env.NODE_ENV === 'development') {
              console.warn('⚠️ router.push did not change route, forcing navigation');
            }
            window.location.href = to;
          }
        }, 1000);
      }
    } catch (e) {
      if (process.env.NODE_ENV === 'development') {
        console.error('router.push failed, forcing navigation:', e);
      }
      if (typeof window !== 'undefined') window.location.href = to;
    }
  }, [router]);

  if (!isAuthenticated) {
    router.push('/signin');
    return null;
  }

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="flex items-center justify-between gap-2 mb-4">
        <div>
          <h1 className="text-xl font-bold text-brand-500 dark:text-white">Upload Your Market Research Findings</h1>
          <p className="text-gray-600 dark:text-gray-400 text-sm">Supported Document: PDF or CSV Files.</p>
        </div>

        <div className="flex items-center gap-2 justify-end">
          {personas.length > 1 && (
            <div className="px-4 py-2 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-lg">
              <div className="flex items-start gap-3">
                <Info className="h-5 w-5 text-brand-600 dark:text-brand-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm text-brand-700 dark:text-brand-300">
                    You must upload files for all {personas.length} personas before proceeding.
                  </p>
                </div>
              </div>
            </div>
          )}

            <Button onClick={analyzeMarketResearch} variant="default" disabled={!viewAnalysis || isAnalyzing} >
              Analyze Market Findings
            </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Persona Selection */}
        {isLoadingPersonas ? (
          <Card className="p-6">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-brand-500" />
              <span className="text-sm text-muted-foreground">Loading personas...</span>
            </div>
          </Card>
        ) : personas.length === 0 ? (
          <Card className="p-6 border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="font-semibold text-amber-900 dark:text-amber-100 mb-1">
                  No Personas Found
                </h3>
                <p className="text-amber-700 dark:text-amber-300 text-sm mb-4">
                  Complete persona identification first
                </p>
                <Button 
                  onClick={() => router.push(`/${path}/personas/${projectId}`)} 
                  variant="outline"
                  size="sm"
                  className="border-amber-300 hover:bg-amber-100 dark:border-amber-700 dark:hover:bg-amber-900/40"
                >
                  Go to Personas
                </Button>
              </div>
            </div>
          </Card>
        ) : (
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <Users className="h-5 w-5 text-brand-500" />
              <h3 className="font-semibold text-brand-500 text-xl">Select Persona</h3>
            </div>
            <div className="space-y-3">
              {personas.map(persona => {
                const hasFiles = (personaFiles[persona.id] || []).length > 0;
                const fileCount = (personaFiles[persona.id] || []).length;
                const isSelected = selectedPersona === persona.id;
                
                return (
                  <button
                    key={persona.id}
                    onClick={() => setSelectedPersona(persona.id)}
                    className={`w-full p-4 rounded-lg border-2 transition-all text-left group hover:shadow-sm ${
                      isSelected
                        ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20 shadow-sm'
                        : 'border-border hover:border-brand-300 dark:hover:border-brand-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`font-medium truncate ${isSelected ? 'text-brand-700 dark:text-brand-300' : 'text-brand-500'}`}>
                            {persona.name}
                          </span>
                          {isSelected && <CheckCircle2 className="h-4 w-4 text-brand-500 flex-shrink-0" />}
                        </div>
                        {hasFiles ? (
                          <Badge variant="default" className="bg-green-500 hover:bg-green-600 text-white">
                            {fileCount} file{fileCount !== 1 ? 's' : ''} added
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="text-muted-foreground">
                            No files yet
                          </Badge>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </Card>
        )}

        {/* Right Column - File Upload */}
        <Card className="p-6">
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
              dragActive 
                ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20 shadow-inner' 
                : 'border-muted-foreground/25 hover:border-muted-foreground/50'
            }`}
          >
            <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 transition-colors ${
              dragActive 
                ? 'bg-brand-100 dark:bg-brand-900/40' 
                : 'bg-muted'
            }`}>
              <Upload className={`h-8 w-8 transition-colors ${
                dragActive ? 'text-brand-500' : 'text-muted-foreground'
              }`} />
            </div>
            
            <h3 className="text-base font-semibold mb-1 text-brand-500">
              {dragActive ? 'Drop files here' : 'Upload research documents'}
            </h3>
            <p className="text-sm text-muted-foreground mb-6">
              Drag and drop or click to browse
            </p>
            
            <div className="flex flex-col sm:flex-row justify-center gap-3 mb-6">
              <Button 
                onClick={() => pdfInputRef.current?.click()} 
                variant="outline" 
                size="sm"
                disabled={isUploading || personas.length === 0}
                className="min-w-[120px]"
              >
                <FileText className="h-4 w-4 mr-2" />
                PDF Files
              </Button>
              <Button 
                onClick={() => csvInputRef.current?.click()} 
                variant="outline" 
                size="sm"
                disabled={isUploading || personas.length === 0}
                className="min-w-[120px]"
              >
                <Table className="h-4 w-4 mr-2" />
                CSV Files
              </Button>
            </div>
            
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">
                <span className="font-medium">PDF:</span> Max 25 files, 25MB each
              </p>
              <p className="text-xs text-muted-foreground">
                <span className="font-medium">CSV:</span> Max 5 files, 25MB each
              </p>
            </div>
          </div>
          <input 
            ref={pdfInputRef} 
            type="file" 
            accept=".pdf" 
            multiple 
            onChange={(e) => handleFileSelect(e.target.files, 'pdf')} 
            className="hidden" 
          />
          <input 
            ref={csvInputRef} 
            type="file" 
            accept=".csv" 
            multiple 
            onChange={(e) => handleFileSelect(e.target.files, 'csv')} 
            className="hidden" 
          />
        </Card>
      </div>

      {totalFiles > 0 && (
        <>
          <div className="mt-6 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-base px-3 py-1">
                {totalFiles} file{totalFiles !== 1 ? 's' : ''} selected
              </Badge>
              {!allPersonasHaveFiles && (
                <Badge variant="destructive" className="text-xs">
                  {personasWithFiles.length}/{personas.length} personas
                </Badge>
              )}
            </div>
            {totalFiles > 0 && !isUploading && (
        <div className="flex justify-end gap-3">
          <Button onClick={() => setShowFilesDialog(true)} variant="default">
            View Selected Files
          </Button>
        </div>
      )}
          </div>

          <Dialog open={showFilesDialog} onOpenChange={setShowFilesDialog}>
            <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Selected Files ({totalFiles})</DialogTitle>
                <DialogDescription>
                  Review and manage files for each persona before uploading
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6 py-4">
                {personas.map(persona => {
                  const files = personaFiles[persona.id] || [];
                  if (files.length === 0) return null;
                  
                  const pdfFiles = files.filter(f => f.type === 'pdf');
                  const csvFiles = files.filter(f => f.type === 'csv');

                  return (
                    <div key={persona.id} className="space-y-4">
                      <div className="flex items-center gap-2 pb-2 border-b">
                        <Users className="h-4 w-4 text-brand-500" />
                        <span className="font-semibold text-brand-600 dark:text-brand-400">{persona.name}</span>
                        <Badge variant="secondary" className="ml-auto">{files.length} file{files.length !== 1 ? 's' : ''}</Badge>
                      </div>

                      {pdfFiles.length > 0 && (
                        <div>
                          <div className="flex items-center gap-2 mb-3">
                            <FileText className="h-4 w-4 text-red-500" />
                            <span className="text-sm font-medium">PDF Files ({pdfFiles.length}/{MAX_PDF_FILES})</span>
                          </div>
                          <div className="space-y-2">
                            {pdfFiles.map(f => (
                              <div key={f.id} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                                <div className="flex-1 min-w-0">
                                  <FileText className="h-5 w-5 text-red-500 flex-shrink-0" />
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium truncate">{f.file.name}</p>
                                    <p className="text-xs text-muted-foreground">{(f.file.size / 1024 / 1024).toFixed(2)} MB</p>
                                  </div>
                                </div>
                                <Button 
                                  onClick={() => removeFile(f.id, persona.id)} 
                                  variant="ghost" 
                                  size="sm" 
                                  disabled={isUploading}
                                  className="flex-shrink-0"
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {csvFiles.length > 0 && (
                        <div>
                          <div className="flex items-center gap-2 mb-3">
                            <Table className="h-4 w-4 text-green-500" />
                            <span className="text-sm font-medium">CSV Files ({csvFiles.length}/{MAX_CSV_FILES})</span>
                          </div>
                          <div className="space-y-2">
                            {csvFiles.map(f => (
                              <div key={f.id} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                  <Table className="h-5 w-5 text-green-500 flex-shrink-0" />
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium truncate">{f.file.name}</p>
                                    <p className="text-xs text-muted-foreground">{(f.file.size / 1024 / 1024).toFixed(2)} MB</p>
                                  </div>
                                </div>
                                <Button 
                                  onClick={() => removeFile(f.id, persona.id)} 
                                  variant="ghost" 
                                  size="sm" 
                                  disabled={isUploading}
                                  className="flex-shrink-0"
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              <DialogFooter>
                <Button onClick={() => setPersonaFiles({})} variant="outline" disabled={isUploading}>
                  Clear All
                </Button>
                <Button 
                  onClick={() => {
                    setShowFilesDialog(false);
                    handleUpload();
                  }} 
                  disabled={!allPersonasHaveFiles || isUploading}
                  className={!allPersonasHaveFiles ? 'opacity-50 cursor-not-allowed' : ''}
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Files for All Personas
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </>
      )}

      {isUploading && (
        <Card className="p-6 my-4 border-brand-200 bg-brand-50/50 dark:border-brand-800 dark:bg-brand-900/10">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Loader2 className="h-6 w-6 text-brand-500 animate-spin" />
                <div className="absolute inset-0 h-6 w-6 rounded-full bg-brand-500/20 animate-ping" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-brand-700 dark:text-brand-300">
                    Uploading files...
                  </span>
                  <span className="text-sm font-medium text-brand-600 dark:text-brand-400">
                    {uploadProgress}%
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Please wait while we process your documents
                </p>
              </div>
            </div>
            
            <div className="space-y-2">
              <Progress value={uploadProgress} className="h-2.5 bg-brand-100 dark:bg-brand-900/30" />
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Processing {totalFiles} file{totalFiles !== 1 ? 's' : ''}</span>
                <span className="font-medium">{Math.round((uploadProgress / 100) * totalFiles)} of {totalFiles}</span>
              </div>
            </div>

            <Button 
              onClick={() => abortControllerRef.current?.abort()} 
              variant="outline" 
              size="sm" 
              className="w-full border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
            >
              <X className="h-4 w-4 mr-2" />
              Cancel Upload
            </Button>
          </div>
        </Card>
      )}

      <MarketAnalysisLoader
        loadingStates={marketAnalysisSteps}
        loading={isAnalyzing}
        onCancel={() => {
          abortControllerRef.current?.abort();
          setIsAnalyzing(false);
        }}
        totalDuration={1 * 30 * 1000} // 1 minutes
      />

      
    </div>
  );
};

export default MarketResearchAnalysisUpload;