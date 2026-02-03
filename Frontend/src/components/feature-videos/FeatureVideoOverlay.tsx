'use client';

import { useState, useEffect, useCallback } from 'react';
import { X, Maximize2, Minimize2, BookOpen } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import YouTubePlayer from './YouTubePlayer';
import FeatureVideoButton from './FeatureVideoButton';
import { useSeenFeatureVideosStore, useIsSeenLoaded } from '@/lib/featureVideos/seenStore';
import type { FeatureId } from '@/lib/featureVideos/featureIds';

type OverlayState = 'closed' | 'openSmall' | 'openFullscreen';

interface FeatureVideoOverlayProps {
  featureId: FeatureId;
  youtubeId: string;
  resourcesHref: string;
  title?: string;
  startTimeSeconds?: number;
  className?: string;
  buttonClassName?: string;
}

export default function FeatureVideoOverlay({
  featureId,
  youtubeId,
  resourcesHref,
  title,
  startTimeSeconds,
  className = '',
  buttonClassName,
}: FeatureVideoOverlayProps) {
  const router = useRouter();
  const [overlayState, setOverlayState] = useState<OverlayState>('closed');
  const [hasAutoOpened, setHasAutoOpened] = useState(false);
  const [openCount, setOpenCount] = useState(0);
  
  const { isSeen, markSeenAndPost, isLoaded } = useSeenFeatureVideosStore();
  const isSeenLoaded = useIsSeenLoaded();

  const featureIsSeen = isSeen(featureId);

  useEffect(() => {
    if (!isSeenLoaded || !isLoaded || hasAutoOpened) {
      return;
    }

    if (!featureIsSeen) {
      // First-time users get fullscreen video overlay
      setOverlayState('openFullscreen');
      setOpenCount(c => c + 1);
      setHasAutoOpened(true);
      markSeenAndPost(featureId, 'autoplay');
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[FeatureVideoOverlay] Auto-opening fullscreen for first-time feature:', featureId);
      }
    }
  }, [featureId, featureIsSeen, isSeenLoaded, isLoaded, hasAutoOpened, markSeenAndPost]);

  const handleOpen = useCallback(() => {
    setOverlayState('openSmall');
    setOpenCount(c => c + 1);
    // Mark as seen with icon_click source (idempotent - won't POST if already seen)
    markSeenAndPost(featureId, 'icon_click');
  }, [featureId, markSeenAndPost]);

  const handleClose = useCallback(() => {
    setOverlayState('closed');
  }, []);

  const handleToggleSize = useCallback(() => {
    setOverlayState((prev) => 
      prev === 'openSmall' ? 'openFullscreen' : 'openSmall'
    );
  }, []);

  const handleLearnMore = useCallback(() => {
    router.push(resourcesHref);
  }, [router, resourcesHref]);

  const isOpen = overlayState !== 'closed';
  const isFullscreen = overlayState === 'openFullscreen';

  return (
    <div className={className}>
      <AnimatePresence>
        {!isOpen && (
          <FeatureVideoButton onClick={handleOpen} className={buttonClassName} />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isOpen && (
          <>
            {isFullscreen && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/70 z-50"
                onClick={handleClose}
              />
            )}

            <motion.div
              initial={isFullscreen ? { opacity: 0, scale: 0.9 } : { opacity: 0, y: 20, scale: 0.95 }}
              animate={isFullscreen ? { opacity: 1, scale: 1 } : { opacity: 1, y: 0, scale: 1 }}
              exit={isFullscreen ? { opacity: 0, scale: 0.9 } : { opacity: 0, y: 20, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={`
                fixed z-50 bg-black rounded-xl shadow-2xl overflow-hidden dark:border-gray-200 dark:border-2
                ${isFullscreen 
                  ? 'inset-[7%] md:inset-[10%] lg:inset-[15%]' 
                  : 'bottom-6 right-6 w-[360px] h-[220px]'
                }
              `}
            >
              {/* Top controls overlay */}
              <div className="absolute top-0 left-0 right-0 h-10 bg-gradient-to-b from-black/80 to-transparent z-20 flex items-start justify-between px-3 pt-2">
                <span className="text-white text-sm font-medium truncate pr-2">
                  {title || 'Feature Help'}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleToggleSize}
                    className="p-1.5 rounded-lg bg-black/40 hover:bg-black/60  transition-colors backdrop-blur-sm"
                    aria-label={isFullscreen ? 'Minimize' : 'Maximize'}
                  >
                    {isFullscreen ? (
                      <Minimize2 className="w-6 h-6 text-white" />
                    ) : (
                      <Maximize2 className="w-6 h-6 text-white" />
                    )}
                  </button>
                  <button
                    onClick={handleClose}
                    className="p-1.5 rounded-lg bg-black/40 hover:bg-black/60 transition-colors backdrop-blur-sm"
                    aria-label="Close"
                  >
                    <X className="w-6 h-6 text-white" />
                  </button>
                </div>
              </div>

              {/* Video container - takes full height */}
              <div className="w-full h-full">
                <YouTubePlayer
                  youtubeId={youtubeId}
                  autoplay={true}
                  startTimeSeconds={startTimeSeconds}
                  playerKey={openCount}
                />
              </div>

              {/* Learn more button - glassmorphic overlay at bottom center */}
              {/* <button
                onClick={handleLearnMore}
                className="absolute bottom-3 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/20 transition-colors text-white text-sm font-medium"
              >
                <BookOpen className="w-4 h-4" />
                Learn more
              </button> */}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
