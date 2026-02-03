"use client"

import { useState, useCallback, useRef, useEffect } from 'react'
import Image from 'next/image'

interface LiteYouTubeProps {
  videoId: string
  title?: string
  className?: string
  thumbnailQuality?: 'default' | 'hqdefault' | 'mqdefault' | 'sddefault' | 'maxresdefault'
}

interface YTPlayer {
  playVideo: () => void
  pauseVideo: () => void
  stopVideo: () => void
  seekTo: (seconds: number, allowSeekAhead: boolean) => void
  isMuted: () => boolean
  mute: () => void
  unMute: () => void
  destroy: () => void
}

declare global {
  interface Window {
    onYouTubeIframeAPIReady: (() => void) | undefined
    YT: {
      Player: new (
        elementId: string | HTMLElement,
        configuration: {
          height: string
          width: string
          videoId: string
          host: string
          playerVars?: {
            autoplay?: 0 | 1
            mute?: 0 | 1
            playsinline?: 0 | 1
            modestbranding?: 0 | 1
            rel?: 0 | 1
            controls?: 0 | 1
            enablejsapi?: 0 | 1
          }
          events?: {
            onReady?: (event: { target: YTPlayer }) => void
            onStateChange?: (event: { target: YTPlayer; data: number }) => void
            onError?: (event: { target: YTPlayer; data: number }) => void
          }
        }
      ) => YTPlayer
      PlayerState: {
        UNSTARTED: number
        ENDED: number
        PLAYING: number
        PAUSED: number
        BUFFERING: number
        CUED: number
      }
    }
  }
}

export default function LiteYouTube({
  videoId,
  title = 'YouTube video',
  className = '',
  thumbnailQuality = 'maxresdefault',
}: LiteYouTubeProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [playerError, setPlayerError] = useState(false)
  const [thumbnailError, setThumbnailError] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [isMuted, setIsMuted] = useState(true)
  const playerRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const playerInstanceRef = useRef<YTPlayer | null>(null)
  const hasUnmutedRef = useRef(false)

  const thumbnailUrl = thumbnailError 
    ? `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`
    : `https://i.ytimg.com/vi/${videoId}/${thumbnailQuality}.jpg`

  const handleTogglePlay = useCallback(() => {
    if (!playerInstanceRef.current) return
    
    if (isPaused) {
      playerInstanceRef.current.playVideo()
      setIsPaused(false)
    } else {
      playerInstanceRef.current.pauseVideo()
      setIsPaused(true)
    }
  }, [isPaused])

  const handleToggleMute = useCallback(() => {
    if (!playerInstanceRef.current) return
    
    if (isMuted) {
      // Unmute and restart from beginning
      playerInstanceRef.current.seekTo(0, true)
      playerInstanceRef.current.unMute()
      playerInstanceRef.current.playVideo()
      setIsMuted(false)
      setIsPaused(false)
      hasUnmutedRef.current = true
    } else {
      playerInstanceRef.current.mute()
      setIsMuted(true)
    }
  }, [isMuted])

  const handlePlayerReady = useCallback((event: { target: YTPlayer }) => {
    setIsLoading(false)
    playerInstanceRef.current = event.target
    // Always start muted and autoplay
    event.target.mute()
    event.target.playVideo()
    setIsMuted(true)
    setIsPaused(false)
  }, [])

  const handleStateChange = useCallback((event: { target: YTPlayer; data: number }) => {
    if (!window.YT) return
    
    // Update paused state based on player state
    if (event.data === window.YT.PlayerState.PAUSED) {
      setIsPaused(true)
    } else if (event.data === window.YT.PlayerState.PLAYING) {
      setIsPaused(false)
    }
  }, [])

  const handlePlayerError = useCallback((event: { target: YTPlayer; data: number }) => {
    console.error('YouTube Player Error:', event.data)
    setPlayerError(true)
    setIsLoading(false)
  }, [])

  useEffect(() => {
    if (!playerRef.current) return

    const initializePlayer = () => {
      if (!playerRef.current || !window.YT?.Player) return

      try {
        new window.YT.Player(playerRef.current, {
          height: '100%',
          width: '100%',
          videoId,
          host: 'https://www.youtube-nocookie.com',
          playerVars: {
            autoplay: 1,
            mute: 1,
            playsinline: 1,
            modestbranding: 1,
            rel: 0,
            controls: 1,
            enablejsapi: 1,
          },
          events: {
            onReady: handlePlayerReady,
            onStateChange: handleStateChange,
            onError: handlePlayerError,
          },
        })
      } catch (error) {
        console.error('Failed to initialize YouTube player:', error)
        setPlayerError(true)
        setIsLoading(false)
      }
    }

    // Check if YT API is already loaded
    if (window.YT?.Player) {
      initializePlayer()
      return
    }

    // Set up callback for when API loads
    const existingCallback = window.onYouTubeIframeAPIReady
    window.onYouTubeIframeAPIReady = () => {
      existingCallback?.()
      initializePlayer()
    }

    // Load YouTube API if not present
    if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
      const tag = document.createElement('script')
      tag.src = 'https://www.youtube.com/iframe_api'
      tag.async = true
      tag.onerror = () => {
        console.error('Failed to load YouTube IFrame API')
        setPlayerError(true)
        setIsLoading(false)
      }
      document.head.appendChild(tag)
    }

    return () => {
      if (playerInstanceRef.current) {
        try {
          playerInstanceRef.current.destroy()
        } catch (e) {
          console.warn('Error destroying player:', e)
        }
        playerInstanceRef.current = null
      }
    }
  }, [videoId, handlePlayerReady, handleStateChange, handlePlayerError])

  if (playerError) {
    return (
      <div className={`relative w-full h-full flex flex-col items-center justify-center bg-gray-100 text-gray-500 p-4 ${className}`}>
        <p className="text-lg font-medium mb-2">Video unavailable</p>
        <p className="text-sm text-center">Please check your connection or try again later.</p>
        <button
          onClick={() => {
            setPlayerError(false)
            setIsLoading(true)
            window.location.reload()
          }}
          className="mt-4 px-4 py-2 text-sm font-medium text-brand-600 border border-brand-600 rounded-md hover:bg-brand-50 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div ref={containerRef} className={`relative w-full h-full ${className}`}>
      {/* Loading state with thumbnail */}
      {isLoading && (
        <div className="absolute inset-0 z-20">
          <Image
            src={thumbnailUrl}
            alt={title}
            fill
            sizes="(max-width: 768px) 100vw, 700px"
            className="object-cover"
            priority
            onError={() => setThumbnailError(true)}
          />
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50">
            <div className="w-12 h-12 border-4 border-white/30 border-t-white rounded-full animate-spin" />
          </div>
        </div>
      )}

      {/* YouTube Player */}
      <div 
        ref={playerRef} 
        className="w-full h-full"
        onClick={handleTogglePlay}
        style={{ cursor: isPaused ? 'pointer' : 'default' }}
      />

      {/* Play button overlay - only shown when paused */}
      {isPaused && !isLoading && (
        <div 
          className="absolute inset-0 flex items-center justify-center z-10 cursor-pointer"
          onClick={handleTogglePlay}
        >
          <div className="w-20 h-20 md:w-24 md:h-24 rounded-full bg-gradient-to-r from-brand-500 to-[#128AA3] flex items-center justify-center shadow-[0_8px_32px_0_rgba(36,70,148,0.4)] hover:shadow-[0_12px_40px_0_rgba(36,70,148,0.5)] transform hover:scale-110 transition-all duration-200">
            <svg
              className="w-10 h-10 md:w-12 md:h-12 text-white ml-1"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
        </div>
      )}

      {/* Mute/Unmute button - bottom right corner */}
      {!isLoading && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleToggleMute()
          }}
          className="absolute bottom-4 right-4 z-20 w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 flex items-center justify-center transition-all duration-200 backdrop-blur-sm border border-white/20"
          aria-label={isMuted ? "Unmute (restarts video)" : "Mute"}
        >
          {isMuted ? (
            <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
            </svg>
          ) : (
            <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
            </svg>
          )}
        </button>
      )}
    </div>
  )
}
