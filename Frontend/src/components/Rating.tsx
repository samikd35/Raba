import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Star, MessageSquare, X, ExternalLink, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

interface RatingProps {
  className?: string
  variant?: "default" | "dropdown"
}

export default function Rating({ className = "", variant = "default" }: RatingProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isHovered, setIsHovered] = useState(false)

  // For dropdown variant, use simple button styling that matches shadcn
  if (variant === "dropdown") {
    return (
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          <button
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors font-medium",
              "hover:bg-brand-50 hover:text-brand-900 dark:hover:bg-brand-900/20 dark:hover:text-brand-100",
              "focus:outline-none focus:bg-brand-50 focus:text-brand-900 dark:focus:bg-brand-900/20 dark:focus:text-brand-100",
              "text-brand-700 dark:text-brand-300",
              className
            )}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
          >
            <span className="font-medium text-brand-600 dark:text-brand-300">Give us feedback</span>
          </button>
        </DialogTrigger>

        <DialogContent
          className="p-0 max-w-2xl overflow-hidden"
          onPointerDownOutside={(e) => {
            // Prevent dropdown or parent handlers from treating this as an outside click
            e.preventDefault();
          }}
          onInteractOutside={(e) => {
            // Avoid accidental closes caused by nested menus/dialogs
            e.preventDefault();
          }}
          onOpenAutoFocus={(e) => {
            // Prevent focus shifts from closing parent menus
            e.preventDefault();
          }}
        >
          <DialogHeader
            className="px-6 py-4 border-b bg-brand-25 dark:bg-brand-900/30 border-brand-200 dark:border-brand-700"
            onClick={(e) => {
              // Ensure clicks in header don't bubble and close the modal
              e.stopPropagation();
            }}
          >
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-500/10 dark:bg-brand-500/20">
                <Star className="w-4 h-4 text-brand-500 dark:text-brand-400" />
              </div>
              <div>
                <DialogTitle className="text-lg font-semibold text-brand-700 dark:text-brand-200">
                  Help us improve Yuba
                </DialogTitle>
                <p className="text-sm text-brand-600 dark:text-brand-400 mt-1">
                  Your feedback helps us build better features
                </p>
              </div>
            </div>
          </DialogHeader>

          <div className="p-6">
            <div className="rounded-lg border overflow-hidden bg-background dark:bg-gray-900 border-brand-200 dark:border-brand-700">
              <iframe
                src="https://forms.gle/MKdjcSNcM3bBfVLK9"
                className="w-full h-[500px] border-0"
                title="Yuba Feedback Form"
                loading="lazy"
                sandbox="allow-scripts allow-forms allow-same-origin"
              >
                <div className="flex items-center justify-center h-full">
                  <div className="text-center p-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500 dark:border-brand-400 mx-auto mb-4"></div>
                    <p className="text-brand-600 dark:text-brand-400">Loading feedback form...</p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-4"
                      onClick={() => window.open("https://forms.gle/MKdjcSNcM3bBfVLK9", "_blank")}
                    >
                      <ExternalLink className="w-4 h-4 mr-2" />
                      Open in new tab
                    </Button>
                  </div>
                </div>
              </iframe>
            </div>

            <div className="mt-4 flex items-center justify-between text-xs text-brand-500 dark:text-brand-400">
              <span className="text-brand-600 dark:text-brand-400">Powered by Google Forms</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-1 text-xs hover:text-brand-700 dark:hover:text-brand-200 hover:bg-brand-50 dark:hover:bg-brand-800/50"
                onClick={() => window.open("https://forms.gle/MKdjcSNcM3bBfVLK9", "_blank")}
              >
                <ExternalLink className="w-3 h-3 mr-1" />
                Open externally
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  // Original floating/default variants remain the same
  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <motion.div
          className={cn(
            "flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all duration-300 group",
            "bg-white dark:bg-gray-900 border border-brand-200 dark:border-brand-700",
            "text-brand-700 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-800/50",
            "hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-lg dark:hover:shadow-brand-500/10",
            className
          )}
          onHoverStart={() => setIsHovered(true)}
          onHoverEnd={() => setIsHovered(false)}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          role="button"
          tabIndex={0}
          aria-label="Open feedback form"
        >
          <motion.div
            animate={{
              rotate: isHovered ? 360 : 0,
              scale: isHovered ? 1.1 : 1,
            }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
          >
            <Star
              className="w-4 h-4 text-brand-500 transition-colors duration-300 group-hover:text-brand-600 dark:text-brand-400 dark:group-hover:text-brand-300"
              fill={isHovered ? "currentColor" : "none"}
            />
          </motion.div>

          <span className="text-brand-600 dark:text-brand-300 group-hover:text-brand-700 dark:group-hover:text-brand-200 transition-colors duration-300">
            Give us feedback
          </span>

          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: isHovered ? 1 : 0, x: isHovered ? 0 : -10 }}
            transition={{ duration: 0.2 }}
          >
            <Sparkles className="w-4 h-4 text-brand-400 dark:text-brand-500" />
          </motion.div>
        </motion.div>
      </DialogTrigger>

      <AnimatePresence>
        {isOpen && (
          <DialogContent
            className="flex flex-col gap-0 p-0 max-w-2xl w-full max-h-[80vh] overflow-hidden bg-white dark:bg-gray-900 border border-brand-200 dark:border-brand-700"
            onPointerDownOutside={(e) => {
              setIsOpen(false);
            }}
            onInteractOutside={(e) => {
              setIsOpen(false);
            }}
          >
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              onClick={(e) => {
                e.stopPropagation();
              }}
            >
              <DialogHeader className="relative bg-gradient-to-r from-brand-50 to-brand-100 dark:from-brand-900/50 dark:to-brand-800/50 border-b border-brand-200 dark:border-brand-700">
                <div className="flex items-center justify-between px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div>
                      <DialogTitle className="text-lg font-semibold text-brand-700 dark:text-brand-200">
                        Help us improve Yuba
                      </DialogTitle>
                      <p className="text-sm text-brand-600 dark:text-brand-400 mt-1">
                        Your feedback helps us build better features
                      </p>
                    </div>
                  </div>
                </div>
              </DialogHeader>

              <div className="relative bg-white dark:bg-gray-900">
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2, duration: 0.3 }}
                  className="p-6"
                >
                  <div className="relative rounded-lg border border-brand-200 dark:border-brand-700 overflow-hidden bg-white dark:bg-gray-900 shadow-sm dark:shadow-brand-500/5">
                    <iframe
                      src="https://forms.gle/MKdjcSNcM3bBfVLK9"
                      className="w-full h-[500px] border-0"
                      title="Yuba Feedback Form"
                      loading="lazy"
                      sandbox="allow-scripts allow-forms allow-same-origin"
                    >
                      <div className="flex items-center justify-center h-full">
                        <div className="text-center p-8">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500 dark:border-brand-400 mx-auto mb-4"></div>
                          <p className="text-brand-600 dark:text-brand-400">Loading feedback form...</p>
                          <Button
                            variant="outline"
                            size="sm"
                            className="mt-4"
                            onClick={() => window.open("https://forms.gle/MKdjcSNcM3bBfVLK9", "_blank")}
                          >
                            <ExternalLink className="w-4 h-4 mr-2" />
                            Open in new tab
                          </Button>
                        </div>
                      </div>
                    </iframe>
                  </div>

                  <div className="mt-4 flex items-center justify-between text-xs text-brand-500 dark:text-brand-400">
                    <span className="text-brand-600 dark:text-brand-400">Powered by Google Forms</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-auto p-1 text-xs hover:text-brand-700 dark:hover:text-brand-200 hover:bg-brand-50 dark:hover:bg-brand-800/50"
                      onClick={() => window.open("https://forms.gle/MKdjcSNcM3bBfVLK9", "_blank")}
                    >
                      <ExternalLink className="w-3 h-3 mr-1" />
                      Open externally
                    </Button>
                  </div>
                </motion.div>
              </div>
            </motion.div>
          </DialogContent>
        )}
      </AnimatePresence>
    </Dialog>
  )
}