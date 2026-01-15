import dynamic from 'next/dynamic'

export const RechartsCharts = dynamic(() => import('./RechartsChartsClient').then(m => m.RechartsChartsClient), {
  ssr: false,
  loading: () => <div className="text-sm opacity-70">Loading charts…</div>
})

