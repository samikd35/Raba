"use client";

import React from "react";
import { motion } from "framer-motion";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface ProcessingIndicatorProps {
  progress: number;
  progressDetails?: string | null;
}

export default function ProcessingIndicator({ progress, progressDetails }: ProcessingIndicatorProps) {
  return (
    <Dialog open={true}>
      <DialogContent className="sm:max-w-md border-0 bg-transparent shadow-none p-0">
        <motion.div 
          initial={{ opacity: 0, y: 20, scale: 0.95 }} 
          animate={{ opacity: 1, y: 0, scale: 1 }} 
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
          className="relative w-full mx-auto p-6 rounded-2xl border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-900"
        >
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <motion.div 
              className="relative"
              animate={{ rotate: 360 }}
              transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            >
              <div className="w-3 h-3 bg-gradient-to-r from-brand-400 to-brand-600 rounded-full" />
              <motion.div 
                className="absolute inset-0 w-3 h-3 bg-gradient-to-r from-brand-400 to-brand-600 rounded-full"
                animate={{ scale: [1, 1.5, 1], opacity: [1, 0, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </motion.div>
            <motion.span 
              className="text-sm font-semibold text-gray-800 dark:text-gray-200"
              animate={{ opacity: [0.7, 1, 0.7] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              {progressDetails || "Processing your request..."}
            </motion.span>
          </div>
          <motion.div
            className="flex items-center gap-2"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.3, type: "spring", stiffness: 200 }}
          >
            <motion.span 
              className="text-xs font-bold text-brand-600 dark:text-brand-400 bg-brand-100/50 dark:bg-brand-900/30 px-2 py-1 rounded-full"
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              {progress}%
            </motion.span>
          </motion.div>
        </div>

        {/* Enhanced progress bar with shimmer effect */}
        <div className="relative w-full h-3 bg-gray-200/80 dark:bg-gray-700/80 rounded-full overflow-hidden mb-6 shadow-inner">
          <motion.div 
            className="h-full bg-gradient-to-r from-brand-400 via-brand-500 to-brand-600 relative overflow-hidden" 
            initial={{ width: 0 }} 
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          >
            {/* Shimmer effect */}
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
              animate={{ x: ["-100%", "200%"] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
            />
          </motion.div>
          
          {/* Progress glow */}
          <motion.div
            className="absolute top-0 h-full bg-gradient-to-r from-brand-400/50 to-brand-600/50 blur-sm"
            initial={{ width: 0 }} 
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>

        <motion.div 
          className="space-y-3"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <motion.div 
            className="flex items-center justify-between text-xs font-bold text-gray-700 dark:text-gray-300"
            animate={{ opacity: [0.8, 1, 0.8] }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            <span className="flex items-center gap-2">
              <motion.div
                className="w-1.5 h-1.5 bg-brand-500 rounded-full"
                animate={{ scale: [1, 1.3, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              />
              What the assistant is working on for you:
            </span>
          </motion.div>

          <motion.div
            className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs"
            initial="hidden"
            animate="visible"
            variants={{
              hidden: {},
              visible: {
                transition: {
                  staggerChildren: 0.1,
                },
              },
            }}
          >
            {[
              { title: "Domain Specification", desc: "Understanding and framing the user's research domain and core objective.", color: "from-blue-400/60 via-blue-500 to-blue-400/60" },
              { title: "Keyword Expansion", desc: "Generating and expanding relevant keywords based on user input.", color: "from-purple-400/60 via-purple-500 to-purple-400/60" },
              { title: "Industry Analysis", desc: "Identifying the overall industry landscape and trends.", color: "from-green-400/60 via-green-500 to-green-400/60" },
              { title: "Challenges", desc: "Analyzing potential challenges and barriers to entry.", color: "from-orange-400/60 via-orange-500 to-orange-400/60" },
              { title: "Recommendation", desc: "Developing strategic recommendations based on findings.", color: "from-pink-400/60 via-pink-500 to-pink-400/60" },
              { title: "Final Report Generation", desc: "Synthesizing the findings into a comprehensive and structured report.", color: "from-indigo-400/60 via-indigo-500 to-indigo-400/60" }
            ].map((item, index) => (
              <motion.div
                key={index}
                className="relative p-3 rounded-xl bg-gradient-to-br from-gray-50/80 via-white/50 to-gray-50/80 dark:from-gray-900/60 dark:via-gray-800/40 dark:to-gray-900/60 border border-gray-200/50 dark:border-gray-700/50 backdrop-blur-sm overflow-hidden group"
                variants={{ 
                  hidden: { opacity: 0, y: 15, scale: 0.9 }, 
                  visible: { opacity: 1, y: 0, scale: 1 } 
                }}
              >
                {/* Animated border glow */}
                <motion.div
                  className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100"
                  style={{
                    background: `linear-gradient(45deg, ${item.color.replace('from-', '').replace('via-', '').replace('to-', '').replace('/60', '/20')})`,
                  }}
                  transition={{ duration: 0.3 }}
                />
                
                {/* Top progress line */}
                <motion.div
                  className={`h-0.5 w-full mb-2 rounded-full bg-gradient-to-r ${item.color} opacity-90`}
                  initial={{ x: "-100%" }}
                  animate={{ x: ["-100%", "100%"] }}
                  transition={{ 
                    duration: 2 + Math.random(), 
                    repeat: Infinity, 
                    ease: "easeInOut",
                    delay: index * 0.2
                  }}
                />
                
                <div className="relative z-10">
                  <motion.p 
                    className="font-bold text-gray-900 dark:text-gray-100 mb-1"
                    animate={{ opacity: [0.9, 1, 0.9] }}
                    transition={{ duration: 2, repeat: Infinity, delay: index * 0.1 }}
                  >
                    {item.title}
                  </motion.p>
                  <p className="text-[11px] text-gray-600 dark:text-gray-400 leading-relaxed">
                    {item.desc}
                  </p>
                </div>

                {/* Floating micro-particles */}
                <div className="absolute inset-0 overflow-hidden rounded-xl pointer-events-none">
                  {[...Array(3)].map((_, i) => (
                    <motion.div
                      key={i}
                      className="absolute w-0.5 h-0.5 bg-brand-400/60 rounded-full"
                      initial={{ 
                        x: Math.random() * 100, 
                        y: Math.random() * 60,
                        opacity: 0 
                      }}
                      animate={{ 
                        y: [null, -10, null],
                        opacity: [0, 0.6, 0],
                        scale: [0.5, 1, 0.5]
                      }}
                      transition={{ 
                        duration: 2 + Math.random(), 
                        repeat: Infinity, 
                        delay: Math.random() + index * 0.1,
                        ease: "easeInOut"
                      }}
                    />
                  ))}
                </div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </div>
        </motion.div>
      </DialogContent>
    </Dialog>
  );
}
