import dynamic from 'next/dynamic'

export const ScriptEditor = dynamic(() => import('./ScriptEditorClient').then(m => m.ScriptEditorClient), {
  ssr: false,
  loading: () => <div className="rounded-md border border-[var(--border)] p-3 text-sm opacity-70">Loading editor…</div>
})
