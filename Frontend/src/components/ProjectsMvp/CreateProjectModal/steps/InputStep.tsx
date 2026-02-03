'use client';

import React from 'react';
import { Upload, FileText, X as XIcon, HelpCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

interface InputStepProps {
  projectName: string;
  ideaText: string;
  pdfFiles: File[];
  isSubmitting: boolean;
  error: string | null;
  onProjectNameChange: (value: string) => void;
  onIdeaTextChange: (value: string) => void;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveFile: (index: number) => void;
}

export const InputStep: React.FC<InputStepProps> = ({
  projectName,
  ideaText,
  pdfFiles,
  isSubmitting,
  error,
  onProjectNameChange,
  onIdeaTextChange,
  onFileChange,
  onRemoveFile,
}) => {
  return (
    <div className="py-2 space-y-4">
      {/* Project Name */}
      <div className="space-y-2">
        <Label htmlFor="project-name" className="text-sm font-medium text-brand-500 dark:text-gray-300">
          Project Name <span className="text-red-500">*</span>
        </Label>
        <Input
          id="project-name"
          type="text"
          placeholder="Enter your project name"
          value={projectName}
          onChange={(e) => onProjectNameChange(e.target.value)}
          className="w-full"
          disabled={isSubmitting}
        />
      </div>

      {/* Idea Text */}
      <div className="space-y-2">
        <Label htmlFor="idea-text" className="text-sm font-medium text-brand-500 dark:text-gray-300">
          Idea Description
        </Label>
        <Textarea
          id="idea-text"
          placeholder="Describe your business idea, problem you're solving, target customers, etc."
          value={ideaText}
          onChange={(e) => onIdeaTextChange(e.target.value)}
          className="w-full min-h-[150px] resize-y"
          disabled={isSubmitting}
        />
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Provide as much detail as possible about your idea to get better questions.
        </p>
      </div>

      {/* PDF Upload */}
      <div className="space-y-2">
        <Label className="text-sm font-medium text-brand-500 dark:text-gray-300">
          Supporting Documents (PDF) <span className="text-red-500">*</span>
        </Label>
        <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center hover:border-brand-400 dark:hover:border-brand-500 transition-colors">
          <input
            type="file"
            accept=".pdf,application/pdf"
            multiple
            onChange={onFileChange}
            className="hidden"
            id="pdf-upload"
            disabled={isSubmitting}
          />
          <label htmlFor="pdf-upload" className="cursor-pointer">
            <Upload className="h-10 w-10 mx-auto text-gray-400 dark:text-gray-500 mb-3" />
            <p className="text-sm text-gray-600 dark:text-gray-400">
              <span className="text-brand-500 font-medium hover:underline">Click to upload</span> or drag and drop
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              PDF files only (business plans, research docs, pitch decks, etc.)
            </p>
          </label>
        </div>

        {/* File List */}
        {pdfFiles.length > 0 && (
          <div className="space-y-2 mt-3">
            {pdfFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-red-500" />
                  <div>
                    <p className="text-sm font-medium text-brand-500 dark:text-gray-300 truncate max-w-md">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRemoveFile(index)}
                  className="text-gray-500 hover:text-red-500"
                  disabled={isSubmitting}
                >
                  <XIcon className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Validation Note */}
      <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <HelpCircle className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
        <p className="text-sm text-blue-700 dark:text-blue-300">
          Please upload at least one PDF document (business plan, research doc, pitch deck, etc.) to generate relevant questions for your project.
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}
    </div>
  );
};
