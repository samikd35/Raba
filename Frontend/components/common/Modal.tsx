"use client"
import { ReactNode, useEffect, useLayoutEffect, useRef } from 'react'

export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title?: string; children: ReactNode }) {
  const dialogRef = useRef<HTMLDivElement | null>(null)
  const lastFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    if (open) document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  useLayoutEffect(() => {
    if (open) {
      lastFocusRef.current = (document.activeElement as HTMLElement) || null
      // Focus first focusable element or dialog container
      const first = getFocusable(dialogRef.current)[0] || dialogRef.current
      ;(first as HTMLElement | null)?.focus?.()
    } else {
      lastFocusRef.current?.focus?.()
    }
  }, [open])

  if (!open) return null

  const handleTab = (e: React.KeyboardEvent) => {
    if (e.key !== 'Tab') return
    const focusables = getFocusable(dialogRef.current)
    if (!focusables.length) return
    const currentIndex = focusables.indexOf(document.activeElement as HTMLElement)
    let nextIndex = currentIndex
    if (e.shiftKey) nextIndex = currentIndex <= 0 ? focusables.length - 1 : currentIndex - 1
    else nextIndex = currentIndex === focusables.length - 1 ? 0 : currentIndex + 1
    if (nextIndex !== currentIndex) {
      e.preventDefault()
      focusables[nextIndex]?.focus()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" onKeyDown={handleTab}>
      <button className="absolute inset-0 bg-black/50" aria-label="Close" onClick={onClose} />
      <div ref={dialogRef} className="relative card-surface w-full max-w-lg p-4 rounded-xl" tabIndex={-1}>
        {title && <h2 className="text-lg font-semibold mb-2">{title}</h2>}
        {children}
      </div>
    </div>
  )
}

function getFocusable(root: HTMLElement | null) {
  if (!root) return [] as HTMLElement[]
  const selectors = [
    'a[href]', 'button:not([disabled])', 'textarea:not([disabled])', 'input:not([disabled])', 'select:not([disabled])', '[tabindex]:not([tabindex="-1"])'
  ]
  return Array.from(root.querySelectorAll<HTMLElement>(selectors.join(','))).filter(el => el.offsetParent !== null)
}
