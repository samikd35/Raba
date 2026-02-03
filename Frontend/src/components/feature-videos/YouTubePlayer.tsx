'use client';

import { useState, useCallback, useEffect } from 'react';
import { Volume2, VolumeX } from 'lucide-react';

interface YouTubePlayerProps {
  youtubeId: string;
  autoplay?: boolean;
  startTimeSeconds?: number;
  className?: string;
  playerKey?: string | number;
  showMuteControl?: boolean;
}

export default function YouTubePlayer({
  youtubeId,
  autoplay = false,
  startTimeSeconds,
  className = '',
  playerKey,
  showMuteControl = true,
}: YouTubePlayerProps) {
  const [isMuted, setIsMuted] = useState(true); // Start muted for autoplay
  const [muteKey, setMuteKey] = useState(0); // Force iframe reload on mute toggle

  // Reset muted state when playerKey changes (new video session)
  useEffect(() => {
    setIsMuted(true);
    setMuteKey(0);
  }, [playerKey]);

  const buildEmbedUrl = useCallback(() => {
    const params = new URLSearchParams({
      autoplay: autoplay ? '1' : '0', // Always autoplay when requested (muted autoplay is allowed)
      mute: isMuted ? '1' : '0',
      playsinline: '1',
      rel: '0',
      modestbranding: '1',
      enablejsapi: '1',
      iv_load_policy: '3',
      disablekb: '0',
      fs: '0',
    });

    // When unmuting, always restart from 00:00; otherwise use startTimeSeconds
    if (!isMuted) {
      params.append('start', '0');
    } else if (startTimeSeconds && startTimeSeconds > 0) {
      params.append('start', startTimeSeconds.toString());
    }

    return `https://www.youtube.com/embed/${youtubeId}?${params.toString()}`;
  }, [youtubeId, autoplay, startTimeSeconds, isMuted]);

  const handleToggleMute = useCallback(() => {
    if (isMuted) {
      // Unmuting: restart from beginning with audio
      setIsMuted(false);
      setMuteKey(prev => prev + 1); // Force iframe reload
    } else {
      // Muting: continue playback muted (reload to apply mute)
      setIsMuted(true);
      setMuteKey(prev => prev + 1);
    }
  }, [isMuted]);

  return (
    <div className={`relative w-full h-full bg-black ${className}`}>
      <iframe
        key={`${playerKey}-${muteKey}`}
        src={buildEmbedUrl()}
        title="Feature Help Video"
        className="absolute inset-0 w-full h-full"
        frameBorder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        referrerPolicy="strict-origin-when-cross-origin"
        allowFullScreen
      />

      {/* Mute/Unmute control - glassmorphic style */}
      {showMuteControl && (
        <button
          onClick={handleToggleMute}
          className="absolute bottom-3 right-3 z-20 p-2 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/20 transition-colors"
          aria-label={isMuted ? 'Unmute' : 'Mute'}
          title={isMuted ? 'Unmute (restarts video)' : 'Mute'}
        >
          {isMuted ? (
            <VolumeX className="w-5 h-5 text-white" />
          ) : (
            <Volume2 className="w-5 h-5 text-white" />
          )}
        </button>
      )}
    </div>
  );
}
