"use client"
import { useEffect, useState } from 'react'
import { apiBase } from '@/lib/api/client'

export function ConnectionStatus() {
  const [status, setStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')
  useEffect(() => {
    let mounted = true
    const check = async () => {
      try {
        const res = await fetch(`${apiBase()}/health`)
        if (!mounted) return
        setStatus(res.ok ? 'connected' : 'disconnected')
      } catch {
        if (!mounted) return
        setStatus('disconnected')
      }
    }
    check()
    const iv = setInterval(check, 30_000)
    return () => { mounted = false; clearInterval(iv) }
  }, [])
  const color = status === 'connected' ? 'bg-emerald-500' : status === 'checking' ? 'bg-zinc-400' : 'bg-red-500'
  const label = status === 'connected' ? 'API' : status === 'checking' ? '...' : 'API'
  return (
    <div aria-live="polite" className="flex items-center gap-2 text-xs opacity-80" title={status === 'connected' ? 'API Connected' : status === 'checking' ? 'Checking API...' : 'API Disconnected'}>
      <span className={`inline-block w-2 h-2 rounded-full ${color}`} aria-hidden="true" />
      <span className="hidden sm:inline">{label}</span>
    </div>
  )
}

