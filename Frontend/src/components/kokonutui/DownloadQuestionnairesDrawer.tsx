'use client'

import { useState } from 'react'
import { Download, FileText, FileSpreadsheet, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { authService } from '@/services/authService'

interface DownloadQuestionnairesDrawerProps {
  projectId: string
}

type DownloadFormat = 'pdf' | 'docx'

export default function DownloadQuestionnairesDrawer({ projectId }: DownloadQuestionnairesDrawerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadingFormat, setDownloadingFormat] = useState<DownloadFormat | null>(null)
  const [formatToConfirm, setFormatToConfirm] = useState<DownloadFormat | null>(null)
  const token = authService.getCurrentToken()

  const handleDownload = async (format: DownloadFormat) => {
    if (!token) {
      toast.error('Authentication required', {
        description: 'Please sign in to download questionnaires',
      })
      return
    }

    setIsDownloading(true)
    setDownloadingFormat(format)

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL
      const response = await fetch(
        `${API_URL}/api/v2/vmp/projects/${projectId}/field-prep/questionnaires/download?format=${format}`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication failed. Please sign in again.')
        } else if (response.status === 404) {
          throw new Error('Questionnaires not found for this project.')
        } else {
          throw new Error(`Download failed: ${response.statusText}`)
        }
      }

      // Get the blob from response
      const blob = await response.blob()
      
      // Create a download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // Set filename based on format
      const extension = format === 'pdf' ? 'pdf' : 'docx'
      link.download = `questionnaires-${projectId}.${extension}`
      
      // Trigger download
      document.body.appendChild(link)
      link.click()
      
      // Cleanup
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      toast.success('Download successful!', {
        description: `Questionnaires downloaded as ${format.toUpperCase()}`,
      })

      // Close dialog after successful download
      setTimeout(() => {
        setIsOpen(false)
        setFormatToConfirm(null)
      }, 1000)

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to download questionnaires'
      
      if (process.env.NODE_ENV === 'development') {
        console.error('Download error:', error)
      }

      toast.error('Download failed', {
        description: errorMessage,
      })
    } finally {
      setIsDownloading(false)
      setDownloadingFormat(null)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => {
      setIsOpen(open)
      if (!open) {
        setFormatToConfirm(null)
      }
    }}>
      <DialogTrigger asChild>
        <Button variant="default" className="gap-2">
          <Download className="h-4 w-4" />
          Download Questionnaires
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-brand-500 dark:text-brand-400">
            <Download className="h-5 w-5 text-brand-500 dark:text-brand-400" />
            Download Questionnaires
          </DialogTitle>
          <DialogDescription>
            Choose your preferred format to download the customer interview questionnaires.
          </DialogDescription>
        </DialogHeader>

        <AnimatePresence mode="wait">
          {isDownloading ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="py-8 px-4"
            >
              <div className="flex flex-col items-center justify-center gap-2">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                >
                  <Loader2 className="h-12 w-12 text-brand-600 dark:text-brand-400" />
                </motion.div>
                
                <div className="text-center space-y-4">
                  <motion.p
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="text-sm font-medium text-brand-500 dark:text-brand-400"
                  >
                    Downloading your file...
                  </motion.p>
                  
                  
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key={formatToConfirm ? "confirm" : "buttons"}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="grid gap-2"
            >
              {formatToConfirm ? (
                <div className="space-y-2">
                  {/* Header */}
                  <div className="flex items-center justify-center gap-2 bg-brand-25 dark:bg-brand-900/10 p-3 rounded-lg">
                    <div className="shrink-0 rounded-lg p-2 bg-brand-50 dark:bg-brand-900/30 border border-brand-200/70 dark:border-brand-800/70">
                      {formatToConfirm === 'pdf' ? (
                        <FileText className="h-5 w-5 text-brand-600 dark:text-brand-400" />
                      ) : (
                        <FileSpreadsheet className="h-5 w-5 text-brand-600 dark:text-brand-400" />
                      )}
                    </div>
                    <div>
                      
                      <p className="text-xs text-brand-700 dark:text-brand-300">
                        You are about to download the customer interview questionnaires as
                        <span className="font-semibold"> {formatToConfirm.toUpperCase()}</span>.
                      </p>
                    </div>
                  </div>

                 

                  {/* Advisory */}
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className="p-4 rounded-xl bg-brand-25 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800"
                  >
                    <p className="text-sm font-semibold text-brand-600 dark:text-brand-400 mb-3">
                      Recommended sample size
                    </p>
                    <div className="grid grid-cols-1 gap-2 text-sm text-brand-700 dark:text-brand-300">
                      <div className="rounded-lg border border-brand-100/70 dark:border-brand-800/70 bg-white/60 dark:bg-brand-900/10 p-3">
                        <p className="font-semibold italic mb-1">If your persona is a Business:</p>
                        <p>10 – 15 full customer interviews</p>
                      </div>
                      <div className="rounded-lg border border-brand-100/70 dark:border-brand-800/70 bg-white/60 dark:bg-brand-900/10 p-3">
                        <p className="font-semibold italic mb-1">If your persona is an Individual:</p>
                        <p>25 – 30 full customer interviews</p>
                      </div>
                    </div>
                  </motion.div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-2 mt-4">
                    <div className="flex items-end gap-2">
                      <Button
                        variant="ghost"
                        onClick={() => setFormatToConfirm(null)}
                        className="text-gray-600 dark:text-gray-300"
                        disabled={isDownloading}
                      >
                        Cancel
                      </Button>
                      <Button
                        onClick={() => {
                          if (formatToConfirm) {
                            handleDownload(formatToConfirm)
                          }
                        }}
                        className="gap-2"
                        disabled={isDownloading}
                      >
                        {isDownloading ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Download className="h-4 w-4" />
                        )}
                        {isDownloading ? 'Preparing...' : 'Proceed to download'}
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Button
                      onClick={() => setFormatToConfirm('pdf')}
                      className="w-full h-auto py-4 px-6 flex items-center justify-between group"
                      variant="outline"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-red-50 dark:bg-red-900/20 group-hover:bg-red-100 dark:group-hover:bg-red-900/30 transition-colors">
                          <FileText className="h-5 w-5 text-red-600 dark:text-red-400" />
                        </div>
                        <div className="text-left">
                          <p className="font-semibold text-gray-900 dark:text-gray-100">PDF Format</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            Best for printing and sharing
                          </p>
                        </div>
                      </div>
                      <Download className="h-4 w-4 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-200 transition-colors" />
                    </Button>
                  </motion.div>

                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Button
                      onClick={() => setFormatToConfirm('docx')}
                      className="w-full h-auto py-4 px-6 flex items-center justify-between group"
                      variant="outline"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30 transition-colors">
                          <FileSpreadsheet className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div className="text-left">
                          <p className="font-semibold text-gray-900 dark:text-gray-100">Word Format</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            Easy to edit and customize
                          </p>
                        </div>
                      </div>
                      <Download className="h-4 w-4 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-200 transition-colors" />
                    </Button>
                  </motion.div>

                  <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-lg">
                    <p className="text-xs text-gray-600 dark:text-gray-400 text-center">
                      Tip: Use these questionnaires to conduct customer interviews and validate your value proposition
                    </p>
                  </div>
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </DialogContent>
    </Dialog>
  )
}
