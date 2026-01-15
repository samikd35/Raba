import { formatCurrency } from '@/lib/utils'

export function CostBreakdown({ costs }: { costs?: Record<string, number> }) {
  if (!costs) return null
  const entries = Object.entries(costs)
  const total = entries.reduce((s, [, v]) => s + (v || 0), 0)
  return (
    <div className="card-surface p-4 rounded-xl">
      <h3 className="font-semibold mb-2">Cost Breakdown</h3>
      <ul className="text-sm space-y-1">
        {entries.map(([k, v]) => (
          <li key={k} className="flex justify-between"><span className="capitalize">{k.replaceAll('_', ' ')}</span><span>{formatCurrency(v)}</span></li>
        ))}
        <li className="flex justify-between font-medium border-t border-[var(--border)] pt-1"><span>Total</span><span>{formatCurrency(total)}</span></li>
      </ul>
    </div>
  )
}

