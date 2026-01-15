import { http, httpForm } from './client'
import type {
  CreateWorkflowBody,
  CreateWorkflowResponse,
  WorkflowsListResponse,
  WorkflowDetail,
  HITLFeedbackBody,
  GateStatusResponse,
} from '@/lib/types'

export function createWorkflow(body: CreateWorkflowBody) {
  return http<CreateWorkflowResponse>('/api/v1/generate', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function createWorkflowWithImage(fields: CreateWorkflowBody & { reference_image?: File }) {
  const form = new FormData()
  Object.entries(fields).forEach(([k, v]) => {
    if (v === undefined || v === null) return
    if (k === 'reference_image' && v instanceof File) form.append('reference_image', v)
    else form.append(k, String(v))
  })
  return httpForm<CreateWorkflowResponse>('/api/v1/generate/with-image', form)
}

export function getWorkflow(id: string) {
  return http<WorkflowDetail>(`/api/v1/workflows/${id}`)
}

export function listWorkflows(params: { status?: string; q?: string; limit?: number; offset?: number } = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.set(k, String(v))
  })
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return http<WorkflowsListResponse>(`/api/v1/workflows${suffix}`)
}

export function deleteWorkflow(id: string) {
  return http<{ message: string }>(`/api/v1/workflows/${id}`, { method: 'DELETE' })
}

export function getGateStatus(id: string) {
  return http<GateStatusResponse>(`/api/v1/workflows/${id}/gate`)
}

export function getGateOutput(id: string, gate: string) {
  return http<unknown>(`/api/v1/workflows/${id}/gate/${gate}/output`)
}

export function submitHITLFeedback(id: string, body: HITLFeedbackBody) {
  return http<{ message: string }>(`/api/v1/workflows/${id}/feedback`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
