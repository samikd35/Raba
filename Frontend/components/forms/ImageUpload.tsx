"use client"
import { useCallback, useRef, useState } from 'react'

const ACCEPT = ['image/jpeg', 'image/png', 'image/webp']
const MAX_MB = 10

export function ImageUpload({ onFile }: { onFile: (file: File | null) => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<string | null>(null)

  const handleFile = useCallback((file: File | null) => {
    setError(null)
    setPreview(null)
    if (!file) {
      onFile(null)
      return
    }
    if (!ACCEPT.includes(file.type)) {
      setError('Invalid file type. Use JPG/PNG/WEBP.')
      onFile(null)
      return
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`File too large. Max ${MAX_MB}MB`)
      onFile(null)
      return
    }
    const reader = new FileReader()
    reader.onload = () => setPreview(String(reader.result))
    reader.readAsDataURL(file)
    onFile(file)
  }, [onFile])

  return (
    <div className="card-surface p-4 rounded-xl">
      <label className="block text-sm font-medium mb-2">Reference Image (Optional)</label>
      <div
        className="rounded-md border border-dashed border-[var(--border)] p-6 text-center cursor-pointer hover:shadow-glow"
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
      >
        <p className="text-sm opacity-80">Drag & drop or click to upload</p>
        <p className="text-xs opacity-60">Max 10MB, JPG/PNG/WEBP</p>
      </div>
      <input ref={inputRef} type="file" accept={ACCEPT.join(',')} hidden onChange={(e) => handleFile(e.target.files?.[0] || null)} />
      {preview && (
        <div className="mt-3">
          <img src={preview} alt="Reference preview" className="w-40 h-40 object-cover rounded-md border border-[var(--border)]" />
        </div>
      )}
      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  )
}

