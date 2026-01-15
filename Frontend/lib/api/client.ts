const DEFAULT_BASE = ''

export function apiBase() {
  // Use relative paths to match backend reverse proxy in dev
  return process.env.NEXT_PUBLIC_API_BASE || DEFAULT_BASE
}

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    cache: 'no-store',
  })
  if (!res.ok) {
    let detail = 'Request failed'
    try {
      const data = await res.json()
      detail = (data && (data.detail || data.message)) || detail
    } catch {}
    throw new Error(`${res.status} ${res.statusText}: ${detail}`)
  }
  return res.json() as Promise<T>
}

export async function httpForm<T>(path: string, form: FormData, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: 'POST',
    body: form,
    ...init,
  })
  if (!res.ok) {
    let detail = 'Upload failed'
    try {
      const data = await res.json()
      detail = (data && (data.detail || data.message)) || detail
    } catch {}
    throw new Error(`${res.status} ${res.statusText}: ${detail}`)
  }
  return res.json() as Promise<T>
}

