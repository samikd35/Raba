"use client"
import { useMemo } from 'react'

type ByType = Record<string, { cost_usd: number; tokens?: number; count?: number }>

export function ChartsClient({ byType }: { byType: ByType }) {
  const items = useMemo(() => {
    const entries = Object.entries(byType || {})
    const max = Math.max(...entries.map(([, v]) => v.cost_usd || 0), 1)
    return entries.map(([k, v]) => ({ key: k, label: k, value: v.cost_usd, pct: (v.cost_usd / max) * 100 }))
  }, [byType])

  if (!items.length) return null

  return (
    <div className="space-y-2" role="figure" aria-label="Cost by type bar chart">
      {items.map((it) => (
        <div key={it.key} className="grid grid-cols-[120px_1fr_auto] items-center gap-2 text-sm">
          <div className="capitalize opacity-80">{it.label}</div>
          <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded">
            <div className="h-2 bg-indigo-500 rounded" style={{ width: `${it.pct}%` }} />
          </div>
          <div className="tabular-nums opacity-80">${it.value.toFixed(2)}</div>
        </div>
      ))}
    </div>
  )
}

