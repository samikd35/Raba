"use client"
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { z } from 'zod'
import { TopicInput } from '@/components/forms/TopicInput'
import { ParameterSelectors } from '@/components/forms/ParameterSelectors'
import { HITLModeToggle } from '@/components/forms/HITLModeToggle'
import { ImageUpload } from '@/components/forms/ImageUpload'
import { AspectRatio, Category, Resolution } from '@/lib/types'
import { createWorkflow, createWorkflowWithImage } from '@/lib/api/workflows'

const schema = z.object({ topic: z.string().min(3).max(500) })

export default function CreatePage() {
  const router = useRouter()
  const [topic, setTopic] = useState('')
  const [duration, setDuration] = useState(18)
  const [aspect, setAspect] = useState<AspectRatio>('9:16')
  const [resolution, setResolution] = useState<Resolution>('1080p')
  const [category, setCategory] = useState<Category>('auto')
  const [hitl, setHitl] = useState<'auto'|'manual'>('manual')
  const [enableAudio, setEnableAudio] = useState(true)
  const [enableSubs, setEnableSubs] = useState(false)
  const [file, setFile] = useState<File | null>(null)

  const mutation = useMutation({
    mutationFn: async () => {
      schema.parse({ topic })
      if (file) {
        return createWorkflowWithImage({ topic, duration_seconds: duration, aspect_ratio: aspect, resolution, category, hitl_mode: hitl, enable_audio: enableAudio, enable_subtitles: enableSubs, reference_image: file })
      }
      return createWorkflow({ topic, duration_seconds: duration, aspect_ratio: aspect, resolution, category, hitl_mode: hitl, enable_audio: enableAudio, enable_subtitles: enableSubs })
    },
    onSuccess: (res) => router.push(`/workflows/${res.workflow_id}`)
  })

  const disabled = topic.length < 3 || topic.length > 500 || mutation.isPending

  return (
    <div className="space-y-5 max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold">Create Your Video</h1>
      <TopicInput value={topic} onChange={setTopic} />
      <ParameterSelectors duration={duration} setDuration={setDuration} aspect={aspect} setAspect={setAspect} resolution={resolution} setResolution={setResolution} category={category} setCategory={setCategory} />
      <ImageUpload onFile={setFile} />
      <div className="card-surface p-4 rounded-xl flex items-center gap-4">
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={enableAudio} onChange={(e) => setEnableAudio(e.target.checked)} /> Enable Audio</label>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={enableSubs} onChange={(e) => setEnableSubs(e.target.checked)} /> Enable Subtitles</label>
      </div>
      <HITLModeToggle value={hitl} onChange={setHitl} />
      <div className="flex items-center gap-3">
        <button className="px-4 py-2 rounded-md bg-indigo-500 text-white focus-ring disabled:opacity-50" disabled={disabled} onClick={() => mutation.mutate()}>
          {mutation.isPending ? 'Generating…' : 'Generate Video →'}
        </button>
        {mutation.isError && <span className="text-sm text-red-500">{(mutation.error as Error).message}</span>}
      </div>
      <div className="card-surface p-3 rounded-xl text-sm opacity-80">Estimated Cost: ~$1.50 - $2.50 • Estimated Time: 4-5 minutes</div>
    </div>
  )
}

