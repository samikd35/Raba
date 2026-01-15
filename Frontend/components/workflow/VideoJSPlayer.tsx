"use client"
import { useEffect, useRef } from 'react'
import videojs from 'video.js'
import type Player from 'video.js/dist/types/player'
import 'video.js/dist/video-js.css'

export default function VideoJSPlayer({ src, poster }: { src: string; poster?: string }) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const playerRef = useRef<Player | null>(null)

  useEffect(() => {
    if (!videoRef.current) return
    playerRef.current = videojs(videoRef.current, {
      controls: true,
      preload: 'auto',
      fluid: true,
      sources: [{ src, type: 'video/mp4' }],
      poster,
    })
    return () => {
      playerRef.current?.dispose()
      playerRef.current = null
    }
  }, [src, poster])

  return (
    <div className="relative w-full max-w-[420px] aspect-[9/16] mx-auto overflow-hidden rounded-xl border border-[var(--border)]">
      <video ref={videoRef} className="video-js vjs-default-skin vjs-16-9" />
    </div>
  )
}

