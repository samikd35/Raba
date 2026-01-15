"use client"

export function HITLModeToggle({ value, onChange }: { value: 'auto' | 'manual'; onChange: (v: 'auto' | 'manual') => void }) {
  return (
    <fieldset className="card-surface p-4 rounded-xl">
      <legend className="text-sm font-medium">HITL Mode</legend>
      <div className="mt-2 grid sm:grid-cols-2 gap-3">
        <label className="flex items-start gap-3 p-3 rounded-md border border-[var(--border)] cursor-pointer">
          <input type="radio" name="hitl" value="auto" checked={value === 'auto'} onChange={() => onChange('auto')} />
          <div>
            <div className="font-medium">Auto</div>
            <div className="text-xs opacity-70">End-to-end, no approval gates.</div>
          </div>
        </label>
        <label className="flex items-start gap-3 p-3 rounded-md border border-[var(--border)] cursor-pointer">
          <input type="radio" name="hitl" value="manual" checked={value === 'manual'} onChange={() => onChange('manual')} />
          <div>
            <div className="font-medium">Manual</div>
            <div className="text-xs opacity-70">5 approval gates for review.</div>
          </div>
        </label>
      </div>
    </fieldset>
  )
}

