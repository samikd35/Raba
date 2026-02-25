
'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { ReactNode } from 'react'

export type WorkflowStatus =
    | 'pending'
    | 'running'
    | 'awaiting_tool_approval'
    | 'awaiting_research_approval'
    | 'awaiting_script_approval'
    | 'awaiting_image_approval'
    | 'awaiting_images_approval'
    | 'awaiting_video_approval'
    | 'research_complete'
    | 'script_complete'
    | 'image_complete'
    | 'completed'
    | 'failed'

export interface WorkflowState {
    workflow_id: string
    status: WorkflowStatus
    topic: string
    duration_seconds: number
    aspect_ratio: string
    resolution: string
    category: string

    // Method results
    tool_selection?: {
        selected_tool: any
        intent_metadata: any
        selection_reasoning: any
        validated_params: any
        tool_name: string
        confidence: number
    }
    research_output?: {
        total_sources: number
        executive_summary: ReactNode
        visual_elements: any
        interesting_angles: any
        research_findings: any[]
        sources: any[]
        strategy_used?: string
    }
    script_output?: {
        total_duration_seconds: number | null
        viral_metrics: any
        call_to_action: any
        hook: string | {
            visual_direction?: ReactNode
            duration_seconds?: number | null
            script: string
        }
        scenes: { description: string }[]
        viral_score: number
    }
    audio_output?: any
    audio_url?: string
    character_reference_sheet?: {
        character_description: ReactNode
        character_name: string
        reference_images: Array<{ view: string; url: string }>
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
