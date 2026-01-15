import dynamic from 'next/dynamic'

export const VideoPlayer = dynamic(() => import('./VideoJSPlayer'), {
  ssr: false,
  loading: () => (
    <div className="relative w-full max-w-[420px] aspect-[9/16] mx-auto border border-[var(--border)] rounded-xl overflow-hidden">
      <div className="absolute inset-0 animate-pulse bg-gray-200 dark:bg-gray-700" />
    </div>
  )
})
