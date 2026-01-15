export const queryKeys = {
  workflows: {
    all: ['workflows'] as const,
    lists: () => [...queryKeys.workflows.all, 'list'] as const,
    list: (filters: Record<string, unknown>) => [...queryKeys.workflows.lists(), filters] as const,
    details: () => [...queryKeys.workflows.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.workflows.details(), id] as const,
    gate: (id: string) => [...queryKeys.workflows.detail(id), 'gate'] as const,
    gateOutput: (id: string, gate: string) => [...queryKeys.workflows.gate(id), gate] as const,
  },
  tools: {
    all: ['tools'] as const,
    lists: () => [...queryKeys.tools.all, 'list'] as const,
    list: (filters: Record<string, unknown>) => [...queryKeys.tools.lists(), filters] as const,
    details: () => [...queryKeys.tools.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.tools.details(), id] as const,
  },
  monitoring: {
    summary: (days: number) => ['monitoring', 'summary', days] as const,
    video: (id: string) => ['monitoring', 'video', id] as const,
    pricing: () => ['monitoring', 'pricing'] as const,
  },
}

