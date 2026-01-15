"use client"
import { useParams } from 'next/navigation'
import { useMutation, useQuery } from '@tanstack/react-query'
import { getGateStatus, getWorkflow, submitHITLFeedback } from '@/lib/api/workflows'
import { queryKeys } from '@/lib/queryKeys'
import { PipelineStepper } from '@/components/pipeline/PipelineStepper'
import { HITLGate } from '@/components/workflow/HITLGate'
import { ImageGallery } from '@/components/workflow/ImageGallery'
import { VideoPlayer } from '@/components/workflow/VideoPlayer'
import { CostBreakdown } from '@/components/workflow/CostBreakdown'

export default function WorkflowDetailPage() {
  const params = useParams<{ id: string }>()
  const id = params.id
  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.workflows.detail(id),
    queryFn: () => getWorkflow(id),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 3000
      if (data.status === 'completed' || data.status === 'failed') return false
      if (String(data.status).startsWith('awaiting_')) return 5000
      return 3000
    },
    refetchIntervalInBackground: true,
  })

  const gate = useQuery({ queryKey: queryKeys.workflows.gate(id), queryFn: () => getGateStatus(id), enabled: !!data && data.hitl_mode === 'manual', refetchInterval: 5000 })

  const continueFromFailure = useMutation({
    mutationFn: () => submitHITLFeedback(id, { action: 'approve' }),
  })

  if (isLoading) return <div>Loading workflow…</div>
  if (isError || !data) return <div className="text-red-500">Workflow not found.</div>

  const stages = [
    { key: 'tool_selection', label: '1. Intent/Tool Selector', status: derive('tool_selection', data.status, gate.data?.current_gate, gate.data?.approved_gates), meta: data.tool_selection?.tool_name },
    { key: 'research', label: '2. Deep Research', status: derive('research', data.status, gate.data?.current_gate, gate.data?.approved_gates) },
    { key: 'script', label: '3. Script Writer', status: derive('script', data.status, gate.data?.current_gate, gate.data?.approved_gates) },
    { key: 'images', label: '4. Image Generator', status: derive('images', data.status, gate.data?.current_gate, gate.data?.approved_gates) },
    { key: 'video', label: '5. Video Generator', status: derive('video', data.status, gate.data?.current_gate, gate.data?.approved_gates) },
  ] as const

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <a href="/workflows" className="text-sm opacity-80 hover:opacity-100">← Back to Workflows</a>
        <h1 className="text-xl font-semibold">Workflow: {id}</h1>
      </div>

      <PipelineStepper stages={stages as any} />

      {gate.data?.current_gate && (
        <HITLGate workflowId={id} gate={gate.data.current_gate} />
      )}

      {data.research_output && (
        <div className="card-surface p-4 rounded-xl">
          <h3 className="font-semibold mb-2">Research Findings</h3>
          <ul className="list-disc list-inside text-sm opacity-90 space-y-1">
            {data.research_output.facts?.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}

      {data.images_output?.image_urls?.length ? (
        <div className="space-y-2">
          <h3 className="font-semibold">Generated Images</h3>
          <ImageGallery images={data.images_output.image_urls} />
        </div>
      ) : null}

      {data.video_output?.video_url && (
        <div className="space-y-2">
          <h3 className="font-semibold">Final Video</h3>
          <VideoPlayer src={data.video_output.video_url} poster={data.video_output.thumbnail_url} />
        </div>
      )}

      <CostBreakdown costs={data.cost_breakdown} />

      {data.status === 'failed' && (
        <div className="card-surface p-4 rounded-xl">
          <p className="text-red-500">Workflow failed. You can try to resume.</p>
          <button className="mt-2 px-3 py-2 rounded-md border focus-ring" onClick={() => continueFromFailure.mutate()} disabled={continueFromFailure.isPending}>Resume from this step</button>
        </div>
      )}
    </div>
  )
}

function derive(
  stage: 'tool_selection'|'research'|'script'|'images'|'video',
  status: string,
  currentGate: string | null | undefined,
  approved: string[] | undefined
): 'pending'|'running'|'completed'|'awaiting'|'failed' {
  const order: Array<'tool_selection'|'research'|'script'|'images'|'video'> = ['tool_selection','research','script','images','video']
  if (status === 'failed') return 'failed'
  if (status === 'completed') return 'completed'
  if (approved?.includes(stage)) return 'completed'
  if (String(status).startsWith('awaiting_')) {
    if (currentGate === stage) return 'awaiting'
    // earlier stages should be completed
    if (approved && order.indexOf(stage) < (currentGate ? order.indexOf(currentGate as any) : 99)) return 'completed'
    return 'pending'
  }
  if (status === 'running') {
    // find first stage not approved; that's running
    const firstNotApproved = order.find(s => !approved?.includes(s))
    if (firstNotApproved === stage) return 'running'
    if (approved?.includes(stage)) return 'completed'
    return 'pending'
  }
  return 'pending'
}
