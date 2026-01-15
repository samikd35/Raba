"use client"
import { useMemo } from 'react'

type Scene = { index: number; label: string; duration: number; start: number; text?: string; thumb?: string }

export function SegmentStitcher({ data, onRegenerate }: { data: unknown; onRegenerate?: (index: number) => void }) {
  const scenes = useMemo(() => parseScenes(data), [data])
  if (!scenes.length) return null
  const total = scenes.reduce((s, sc) => s + sc.duration, 0)
  const max = Math.max(...scenes.map(s => s.duration)) || 1
  return (
    <div className="card-surface p-3 rounded-xl">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-medium">Segment Stitcher</h4>
        <span className="text-xs opacity-70">Total: {total}s</span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {scenes.map((s) => (
          <div key={s.index} className="min-w-[160px] max-w-[200px] flex-1 rounded-md border border-[var(--border)] p-2">
            <div className="text-xs opacity-70">{s.label}</div>
            <div className="mt-1 font-medium text-sm">{s.duration}s</div>
            {s.thumb && (
              <div className="mt-2 aspect-video rounded border border-[var(--border)] overflow-hidden">
                <img src={s.thumb} alt={`${s.label} thumbnail`} className="w-full h-full object-cover" />
              </div>
            )}
            <div className="mt-2 h-2 bg-gray-200 dark:bg-gray-700 rounded">
              <div className="h-2 bg-indigo-500 rounded" style={{ width: `${(s.duration / max) * 100}%` }} />
            </div>
            {s.text && <p className="mt-2 text-xs line-clamp-3 opacity-80">{s.text}</p>}
            {onRegenerate && (
              <button className="mt-2 w-full px-2 py-1 text-xs rounded-md border focus-ring" onClick={() => onRegenerate(s.index)} aria-label={`Regenerate segment ${s.index+1}`}>
                Regenerate Segment
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export function parseScenes(data: unknown): Scene[] {
  try {
    const d: any = data
    const out = d?.output ?? d
    if (!out) return []
    const thumbs: string[] = Array.isArray(out.image_urls) ? out.image_urls : []
    const scenes: Scene[] = []
    let start = 0
    if (out.hook) {
      const dur = Number(out.hook.duration ?? 0) || 0
      scenes.push({ index: scenes.length, label: 'Hook', duration: dur, start, text: out.hook.script, thumb: thumbs[0] })
      start += dur
    }
    if (Array.isArray(out.body)) {
      for (let i = 0; i < out.body.length; i++) {
        const b = out.body[i]
        const dur = Number(b.duration ?? 0) || 0
        scenes.push({ index: scenes.length, label: `Scene ${i+1}`, duration: dur, start, text: b.script, thumb: thumbs[i+1] })
        start += dur
      }
    }
    if (out.cta) {
      const dur = Number(out.cta.duration ?? 0) || 0
      scenes.push({ index: scenes.length, label: 'CTA', duration: dur, start, text: out.cta.script, thumb: thumbs[thumbs.length - 1] })
    }
    return scenes
  } catch {
    return []
  }
}
