"use client"
import { AspectRatio, Category, Resolution } from '@/lib/types'

export function ParameterSelectors(props: {
  duration: number
  setDuration: (v: number) => void
  aspect: AspectRatio
  setAspect: (v: AspectRatio) => void
  resolution: Resolution
  setResolution: (v: Resolution) => void
  category: Category
  setCategory: (v: Category) => void
}) {
  const { duration, setDuration, aspect, setAspect, resolution, setResolution, category, setCategory } = props
  return (
    <div className="card-surface p-4 rounded-xl grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div>
        <label className="block text-sm font-medium mb-1">Duration</label>
        <select value={duration} onChange={(e) => setDuration(Number(e.target.value))} className="w-full rounded-md border border-[var(--border)] bg-transparent p-2 focus-ring">
          {[...Array(18)].map((_, i) => 8 + i).map((s) => (
            <option key={s} value={s}>{s}s</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Aspect Ratio</label>
        <select value={aspect} onChange={(e) => setAspect(e.target.value as AspectRatio)} className="w-full rounded-md border border-[var(--border)] bg-transparent p-2 focus-ring">
          <option value="9:16">9:16</option>
          <option value="16:9">16:9</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Resolution</label>
        <select value={resolution} onChange={(e) => setResolution(e.target.value as Resolution)} className="w-full rounded-md border border-[var(--border)] bg-transparent p-2 focus-ring">
          <option value="720p">720p</option>
          <option value="1080p">1080p</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Category</label>
        <select value={category} onChange={(e) => setCategory(e.target.value as Category)} className="w-full rounded-md border border-[var(--border)] bg-transparent p-2 focus-ring">
          <option value="auto">Auto</option>
          <option value="surreal_realism">Surreal Realism</option>
          <option value="high_octane_anime">High Octane Anime</option>
          <option value="stylized_3d">Stylized 3D</option>
        </select>
      </div>
    </div>
  )
}

