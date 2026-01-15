"use client"
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMonitoringPricing, getMonitoringSummary } from '@/lib/api/monitoring'
import { queryKeys } from '@/lib/queryKeys'
import { formatCurrency, secondsToHms } from '@/lib/utils'
import { RechartsCharts } from '@/components/monitoring/RechartsCharts'

export default function MonitoringPage() {
  const [days, setDays] = useState(7)
  const summary = useQuery({ queryKey: queryKeys.monitoring.summary(days), queryFn: () => getMonitoringSummary(days), refetchInterval: 60_000 })
  const pricing = useQuery({ queryKey: queryKeys.monitoring.pricing(), queryFn: () => getMonitoringPricing(), staleTime: 60 * 60 * 1000 })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Monitoring</h1>
        <select value={days} onChange={(e)=>setDays(Number(e.target.value))} className="rounded-md border border-[var(--border)] bg-transparent p-2 text-sm focus-ring">
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {summary.isLoading ? <p>Loading…</p> : summary.isError ? <p className="text-red-500">Failed to load summary.</p> : summary.data && summary.data.totals && summary.data.metrics ? (
        <section className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <SummaryCard label="Total Cost" value={formatCurrency(summary.data.totals.total_cost_usd || 0)} />
          <SummaryCard label="Videos Generated" value={String(summary.data.totals.total_videos || 0)} />
          <SummaryCard label="Success Rate" value={`${Math.round((summary.data.metrics.success_rate || 0) * 100)}%`} />
        </section>
      ) : summary.data ? (
        <p className="text-yellow-500">Summary data incomplete. Please try again.</p>
      ) : null}

      {summary.data && summary.data.totals && summary.data.metrics && (
        <section className="space-y-4">
          <RechartsCharts byType={summary.data.by_generation_type as any} byModel={summary.data.by_model as any} />
          <div className="card-surface p-4 rounded-xl">
            <h3 className="font-semibold mb-2">Performance</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
              <Perf label="Cache Hit Rate" value={`${Math.round((summary.data.metrics.cache_hit_rate || 0) * 100)}%`} />
              <Perf label="Avg Gen Time" value={secondsToHms(summary.data.metrics.avg_generation_time_seconds || 0)} />
              <Perf label="Avg Cost/Video" value={formatCurrency(summary.data.metrics.avg_cost_per_video_usd || 0)} />
              <Perf label="Completed" value={String(summary.data.totals.completed_videos || 0)} />
            </div>
          </div>
        </section>
      )}

      {pricing.data && (
        <section className="card-surface p-4 rounded-xl">
          <h3 className="font-semibold mb-2">Pricing</h3>
          <ul className="text-sm grid grid-cols-1 sm:grid-cols-2 gap-2">
            {Object.entries(pricing.data).map(([k,v]) => (
              <li key={k} className="flex items-center justify-between rounded-md border border-[var(--border)] p-2">
                <span>{k}</span>
                <span>{v.unit} • {formatCurrency(v.price)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card-surface p-4 rounded-xl">
      <div className="text-xs opacity-70">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  )
}

function Perf({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[var(--border)] p-3">
      <div className="text-xs opacity-70">{label}</div>
      <div className="font-medium">{value}</div>
    </div>
  )
}
