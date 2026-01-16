'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export interface WorkflowState {
    workflow_id: string
    status: 'pending' | 'running' | 'completed' | 'failed'
    topic: string
    duration_seconds: number
    aspect_ratio: string
    resolution: string
    category: string

    // Method results
    tool_selection?: {
        tool_name: string
        confidence: number
    }
    research_output?: {
        research_findings: any[]
        sources: any[]
    }
    script_output?: {
        hook: { script: string }
        scenes: { description: string }[]
        viral_score: number
    }
    generated_images?: string[]
    video_url?: string

    // HITL
    hitl_mode: 'auto' | 'manual'
    current_hitl_gate?: string | null

    error?: string
    created_at: string
}

export function useWorkflow(workflowId: string) {
    return useQuery({
        queryKey: ['workflow', workflowId],
        queryFn: () => api.get<WorkflowState>(`/workflows/${workflowId}`),
        refetchInterval: (query) => {
            const status = query.state.data?.status
            if (status === 'completed' || status === 'failed') {
                return false // Stop polling
            }
            return 3000 // Poll every 3s
        },
    })
}
