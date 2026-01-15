import dynamic from 'next/dynamic'

export const Charts = dynamic(() => import('./ChartsClient').then(m => m.ChartsClient), {
  ssr: false,
  loading: () => <div className="text-sm opacity-70">Loading chart…</div>
})

