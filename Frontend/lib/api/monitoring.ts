import { http } from './client'
import type { MonitoringSummaryResponse } from '@/lib/types'

export function getMonitoringSummary(days = 7) {
  const q = new URLSearchParams({ days: String(days) })
  return http<MonitoringSummaryResponse>(`/api/v1/monitoring/summary?${q.toString()}`)
}

export function getMonitoringPricing() {
  return http<Record<string, { unit: string; price: number }>>('/api/v1/monitoring/pricing')
}

export function getMonitoringVideo(id: string) {
  return http<unknown>(`/api/v1/monitoring/video/${id}`)
}
