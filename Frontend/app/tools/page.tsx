"use client"
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listTools, createTool } from '@/lib/api/tools'
import { queryKeys } from '@/lib/queryKeys'
import { useState } from 'react'
import { Modal } from '@/components/common/Modal'

export default function ToolsPage() {
  const [open, setOpen] = useState(false)
  const [category, setCategory] = useState('')
  const { data, isLoading, isError } = useQuery({ queryKey: queryKeys.tools.list({ category }), queryFn: () => listTools({ category: category || undefined, is_active: true, limit: 60 }) })
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Tools</h1>
        <button className="px-3 py-2 rounded-md bg-indigo-500 text-white focus-ring" onClick={() => setOpen(true)}>+ Create Tool</button>
      </div>
      <div className="flex gap-2 items-center">
        <label className="text-sm">Category</label>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="rounded-md border border-[var(--border)] bg-transparent p-2 text-sm focus-ring">
          <option value="">All</option>
          <option value="surreal_realism">Surreal Realism</option>
          <option value="high_octane_anime">High Octane Anime</option>
          <option value="stylized_3d">Stylized 3D</option>
        </select>
      </div>
      {isLoading && <p>Loading tools…</p>}
      {isError && <p className="text-red-500">Failed to load tools.</p>}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.tools.map(t => (
            <div key={t.tool_id} className="card-surface p-4 rounded-xl border-beam">
              <div className="text-sm font-semibold">{t.tool_name}</div>
              <div className="mt-1 text-xs opacity-70 capitalize">{t.category.replaceAll('_',' ')}</div>
              <p className="mt-2 text-sm opacity-80 line-clamp-3">{t.description}</p>
              <div className="mt-3 text-xs opacity-70 flex items-center justify-between">
                <span>Usage: {t.usage_count ?? 0}x</span>
                <span>Success: {Math.round((t.success_rate ?? 0) * 100)}%</span>
              </div>
            </div>
          ))}
        </div>
      )}
      <CreateToolModal open={open} onClose={() => setOpen(false)} />
    </div>
  )
}

function CreateToolModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const [tool_name, setName] = useState('')
  const [idea, setIdea] = useState('')
  const [category, setCategory] = useState('')
  const create = useMutation({
    mutationFn: () => createTool({ tool_name, idea, category: (category || undefined) as any }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.tools.lists() })
      onClose()
      setName(''); setIdea(''); setCategory('')
    }
  })
  return (
    <Modal open={open} onClose={onClose} title="Create Tool">
      <div className="space-y-3">
        <div>
          <label className="block text-sm mb-1">Tool Name</label>
          <input value={tool_name} onChange={(e)=>setName(e.target.value)} className="w-full rounded-md border border-[var(--border)] bg-transparent p-2 focus-ring" />
        </div>
        <div>
          <label className="block text-sm mb-1">Idea</label>
          <textarea value={idea} onChange={(e)=>setIdea(e.target.value)} className="w-full rounded-md border border-[var(--border)] bg-transparent p-2 focus-ring min-h-[100px]" />
        </div>
        <div>
          <label className="block text-sm mb-1">Category</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full rounded-md border border-[var(--border)] bg-transparent p-2 focus-ring">
            <option value="">Auto</option>
            <option value="surreal_realism">Surreal Realism</option>
            <option value="high_octane_anime">High Octane Anime</option>
            <option value="stylized_3d">Stylized 3D</option>
          </select>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button className="px-3 py-2 rounded-md border focus-ring" onClick={onClose}>Cancel</button>
          <button className="px-3 py-2 rounded-md bg-indigo-500 text-white focus-ring disabled:opacity-50" disabled={!tool_name || idea.length < 10 || create.isPending} onClick={() => create.mutate()}>Create Tool</button>
        </div>
        {create.isError && <p className="text-sm text-red-500">Failed to create tool.</p>}
      </div>
    </Modal>
  )
}

