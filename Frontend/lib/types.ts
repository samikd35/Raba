// Shared API types approximated from Backend/Documentations/API_Docs

export type AspectRatio = '9:16' | '16:9'
export type Resolution = '720p' | '1080p'
export type Category = 'auto' | 'surreal_realism' | 'high_octane_anime' | 'stylized_3d'
export type WorkflowStatus = 'pending' | 'running' | 'completed' | 'failed' | `awaiting_${string}`

export interface CreateWorkflowBody {
  topic: string
  duration_seconds?: number
  aspect_ratio?: AspectRatio
  resolution?: Resolution
  category?: Category
  hitl_mode?: 'auto' | 'manual'
  enable_audio?: boolean
  enable_subtitles?: boolean
}

export interface CreateWorkflowResponse {
  workflow_id: string
  status: WorkflowStatus | 'pending'
  message: string
}

export interface WorkflowDetail {
  workflow_id: string
  status: WorkflowStatus
  topic: string
  duration_seconds: number
  aspect_ratio: AspectRatio
  resolution: Resolution
  category: Category
  hitl_mode: 'auto' | 'manual'
  current_hitl_gate: null | 'tool_selection' | 'research' | 'script' | 'images' | 'video'
  tool_selection?: { tool_id: string; tool_name: string; confidence: number } | null
  research_output?: { facts: string[]; sources: string[] } | null
  script_output?: unknown
  images_output?: { image_urls: string[]; prompts_used?: string[] } | null
  video_output?: { video_url: string; duration_seconds: number; resolution: Resolution; thumbnail_url?: string } | null
  cost_breakdown?: Record<string, number>
}

export interface WorkflowListItem {
  workflow_id: string
  topic: string
  status: WorkflowStatus
  created_at?: string
  category?: Category
  duration_seconds?: number
  thumbnail_url?: string | null
}

export interface WorkflowsListResponse {
  workflows: WorkflowListItem[]
  total: number
  limit: number
  offset: number
}

export interface GateStatusResponse {
  workflow_id: string
  current_gate: null | 'tool_selection' | 'research' | 'script' | 'images' | 'video'
  hitl_mode: 'auto' | 'manual'
  workflow_status: WorkflowStatus
  approved_gates: string[]
  gate_info?: unknown
}

export interface HITLFeedbackBody {
  action: 'approve' | 'regenerate' | 'edit' | 'add_image'
  feedback?: string
  edited_content?: unknown
  additional_images?: string[]
}

export interface ToolItem {
  id: string
  tool_id: string
  tool_name: string
  category: Category
  description: string
  capabilities?: Record<string, unknown>
  is_active: boolean
  priority?: number
  version?: number
  usage_count?: number
  success_rate?: number
  created_at?: string
  updated_at?: string
}

export interface ToolsListResponse {
  tools: ToolItem[]
  total: number
  limit: number
  offset: number
}

export interface CreateToolBody {
  tool_name: string
  idea: string
  category?: Category
}

export interface MonitoringSummaryResponse {
  period: { start: string; end: string; days: number }
  totals: { total_tokens: number; total_cost_usd: number; total_videos: number; completed_videos: number; failed_videos: number }
  by_generation_type: Record<string, { tokens: number; cost_usd: number; count: number }>
  by_model: Record<string, { tokens: number; cost_usd: number; calls: number }>
  metrics: { success_rate: number; cache_hit_rate: number; avg_generation_time_seconds: number; avg_cost_per_video_usd: number }
}
