import { http } from './client'
import type { ToolsListResponse, CreateToolBody, ToolItem } from '@/lib/types'

export function listTools(params: { category?: string; is_active?: boolean; limit?: number; offset?: number } = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) q.set(k, String(v))
  })
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return http<ToolsListResponse>(`/api/v1/tools${suffix}`)
}

export function createTool(body: CreateToolBody) {
  return http<ToolItem>('/api/v1/tools', { method: 'POST', body: JSON.stringify(body) })
}

export function getTool(toolId: string) {
  return http<ToolItem>(`/api/v1/tools/${toolId}`)
}

export function updateTool(toolId: string, body: Partial<ToolItem>) {
  return http<ToolItem>(`/api/v1/tools/${toolId}`, { method: 'PUT', body: JSON.stringify(body) })
}

export function deleteTool(toolId: string) {
  return http<{ message: string }>(`/api/v1/tools/${toolId}`, { method: 'DELETE' })
}

