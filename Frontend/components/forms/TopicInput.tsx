"use client"
import { useState } from 'react'

export function TopicInput({ value, onChange, max = 500 }: { value: string; onChange: (v: string) => void; max?: number }) {
  const [focused, setFocused] = useState(false)
  const length = value.length
  const invalid = length > max || length > 0 && length < 3
  return (
    <div className={`card-surface p-4 ${focused ? 'shadow-glow' : ''} rounded-xl`}>
      <label htmlFor="topic" className="block text-sm font-medium mb-2">Topic</label>
      <textarea
        id="topic"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        aria-invalid={invalid}
        aria-describedby="topic-help"
        placeholder="What video do you want to create? Describe your topic..."
        className="w-full min-h-[120px] resize-y rounded-md border border-[var(--border)] bg-transparent p-3 focus-ring"
        maxLength={max}
      />
      <div className="mt-2 flex items-center justify-between text-xs">
        <span id="topic-help" className={`opacity-80 ${invalid ? 'text-red-500' : ''}`}>
          {invalid ? '3-500 characters' : 'Describe your topic clearly'}
        </span>
        <span className="opacity-60">{length}/{max}</span>
      </div>
    </div>
  )
}

