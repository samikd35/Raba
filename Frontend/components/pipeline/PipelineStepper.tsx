"use client"
import { motion } from 'framer-motion'
import { Check, CirclePause, Loader2 } from 'lucide-react'

type Stage = {
  key: 'tool_selection' | 'research' | 'script' | 'images' | 'video'
  label: string
  status: 'pending' | 'running' | 'completed' | 'awaiting' | 'failed'
  meta?: string
}

export function PipelineStepper({ stages, onSelect }: { stages: Stage[]; onSelect?: (key: Stage['key']) => void }) {
  return (
    <div className="card-surface p-4 rounded-xl">
      <ol className="space-y-3">
        {stages.map((s, idx) => (
          <li key={s.key} className="flex items-start gap-3">
            <StatusIcon status={s.status} />
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <button className="text-left font-medium focus-ring" onClick={() => onSelect?.(s.key)}>
                  {idx + 1}. {s.label}
                </button>
                {s.meta && <span className="text-xs opacity-70">{s.meta}</span>}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

function StatusIcon({ status }: { status: Stage['status'] }) {
  if (status === 'completed') return <Check className="text-emerald-500" size={18} />
  if (status === 'running') return <Loader2 className="animate-spin text-indigo-500" size={18} />
  if (status === 'awaiting') return <CirclePause className="text-yellow-500" size={18} />
  if (status === 'failed') return <span className="w-3 h-3 rounded-full bg-red-500" />
  return <span className="w-3 h-3 rounded-full bg-zinc-400" />
}

