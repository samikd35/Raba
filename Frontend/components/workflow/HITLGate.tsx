"use client"
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getGateOutput, submitHITLFeedback } from '@/lib/api/workflows'
import { queryKeys } from '@/lib/queryKeys'
import { useState } from 'react'
import { ScriptEditor } from './ScriptEditor'
import { SegmentStitcher } from './SegmentStitcher'

export function HITLGate({ workflowId, gate }: { workflowId: string; gate: 'tool_selection'|'research'|'script'|'images'|'video' }) {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: queryKeys.workflows.gateOutput(workflowId, gate), queryFn: () => getGateOutput(workflowId, gate), refetchInterval: 5000 })
  const [feedback, setFeedback] = useState('')
  const [edited, setEdited] = useState<string>('')
  const [tab, setTab] = useState<'edit'|'preview'>('edit')
  const [regenCountOverride, setRegenCountOverride] = useState<number | null>(null)
  const [editCount, setEditCount] = useState(0)
  const approve = useMutation({
    mutationFn: () => submitHITLFeedback(workflowId, { action: 'approve' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.workflows.detail(workflowId) })
  })
  const regenerate = useMutation({
    mutationFn: () => submitHITLFeedback(workflowId, { action: 'regenerate', feedback }),
    onMutate: async () => {
      const current = (data as any)?.regeneration_count ?? 0
      setRegenCountOverride(current + 1)
    },
    onError: () => setRegenCountOverride(null),
    onSettled: () => qc.invalidateQueries({ queryKey: queryKeys.workflows.gateOutput(workflowId, gate) })
  })
  const edit = useMutation({
    mutationFn: () => submitHITLFeedback(workflowId, { action: 'edit', edited_content: { html: edited } }),
    onMutate: async () => setEditCount((c) => c + 1),
    onError: () => setEditCount((c) => Math.max(0, c - 1)),
    onSettled: () => qc.invalidateQueries({ queryKey: queryKeys.workflows.detail(workflowId) })
  })
  const regenerateSegment = useMutation({
    mutationFn: (index: number) => submitHITLFeedback(workflowId, { action: 'regenerate', feedback: `segment:${index}` }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.workflows.detail(workflowId) })
  })

  if (isLoading) return <div className="card-surface p-4 rounded-xl">Loading gate output...</div>
  if (data === undefined) return null

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <div className="card-surface p-4 rounded-xl space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Current Output</h3>
          {gate === 'script' && (
            <div className="flex gap-1 text-sm border border-[var(--border)] rounded-md overflow-hidden">
              <button className={`px-3 py-1 ${tab==='edit' ? 'bg-indigo-500 text-white' : ''}`} onClick={()=>setTab('edit')} aria-pressed={tab==='edit'}>Edit</button>
              <button className={`px-3 py-1 ${tab==='preview' ? 'bg-indigo-500 text-white' : ''}`} onClick={()=>setTab('preview')} aria-pressed={tab==='preview'}>Preview</button>
            </div>
          )}
        </div>
        {gate === 'script' ? (
          tab === 'edit' ? (
            <ScriptEditor value={edited || toInitialHtml(data)} onChange={setEdited} />
          ) : (
            <ScriptEditor value={edited || toInitialHtml(data)} onChange={() => {}} readOnly />
          )
        ) : (
          <pre className="text-sm whitespace-pre-wrap opacity-90">{JSON.stringify(data, null, 2)}</pre>
        )}
        {(gate === 'script' || gate === 'images') && (
          <SegmentStitcher data={data} onRegenerate={(i)=>regenerateSegment.mutate(i)} />
        )}
      </div>
      <div className="card-surface p-4 rounded-xl">
        <h3 className="font-semibold mb-2">HITL Actions</h3>
        <div className="space-y-3">
          <textarea className="w-full min-h-[120px] rounded-md border border-[var(--border)] bg-transparent p-2 focus-ring" placeholder="Optional feedback for regeneration" value={feedback} onChange={(e) => setFeedback(e.target.value)} />
          <div className="flex gap-2 flex-wrap items-center">
            <button className="px-3 py-2 rounded-md bg-indigo-500 text-white focus-ring disabled:opacity-50" disabled={approve.isPending || regenerate.isPending} onClick={() => approve.mutate()}>Approve</button>
            <button className="px-3 py-2 rounded-md border focus-ring disabled:opacity-50" disabled={regenerate.isPending} onClick={() => regenerate.mutate()}>Regenerate</button>
            {gate === 'script' && (
              <button className="px-3 py-2 rounded-md border focus-ring disabled:opacity-50" disabled={edit.isPending || !edited} onClick={() => edit.mutate()}>Save Edit</button>
            )}
            {(data as any)?.regeneration_count !== undefined && (
              <span className="text-xs opacity-70">Regenerations: {(regenCountOverride ?? (data as any).regeneration_count)}/3</span>
            )}
            {gate === 'script' && (
              <span className="text-xs opacity-70">Edits: {editCount}</span>
            )}
          </div>
          {(approve.isError || regenerate.isError || edit.isError || regenerateSegment.isError) && <p className="text-sm text-red-500">Action failed. Try again.</p>}
        </div>
      </div>
    </div>
  )
}

function toInitialHtml(data: unknown): string {
  try {
    const d: any = data || {}
    if (d?.output) {
      const o = d.output
      const lines: string[] = []
      if (o.hook?.script) lines.push(`<p><strong>Hook:</strong> ${o.hook.script}</p>`) 
      if (Array.isArray(o.body)) {
        o.body.forEach((b: any, i: number) => lines.push(`<p><strong>Scene ${i+1}:</strong> ${b.script ?? ''}</p>`))
      }
      if (o.cta?.script) lines.push(`<p><strong>CTA:</strong> ${o.cta.script}</p>`) 
      return lines.join('') || '<p></p>'
    }
  } catch {}
  return '<p></p>'
}
