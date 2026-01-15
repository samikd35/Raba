"use client"
import Link from 'next/link'
import { useInfiniteQuery } from '@tanstack/react-query'
import { listWorkflows } from '@/lib/api/workflows'
import { queryKeys } from '@/lib/queryKeys'
import { useEffect, useRef, useState } from 'react'
import { Skeleton } from '@/components/common/Skeleton'

export default function WorkflowsListPage() {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState<string>('')
  const limit = 30
  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch,
  } = useInfiniteQuery({
    queryKey: queryKeys.workflows.list({ q, status }),
    queryFn: ({ pageParam }) => listWorkflows({ q, status: status || undefined, limit, offset: pageParam ?? 0 }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((s, p) => s + p.workflows.length, 0)
      return loaded < lastPage.total ? loaded : undefined
    },
    staleTime: 30_000,
  })
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (!sentinelRef.current) return
    const el = sentinelRef.current
    const io = new IntersectionObserver((entries) => {
      const [entry] = entries
      if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) {
        fetchNextPage()
      }
    }, { rootMargin: '200px' })
    io.observe(el)
    return () => io.disconnect()
  }, [fetchNextPage, hasNextPage, isFetchingNextPage])

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        <h1 className="text-2xl font-semibold">Workflows</h1>
        <div className="flex gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search topic" className="rounded-md border border-[var(--border)] bg-transparent p-2 text-sm focus-ring" />
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-md border border-[var(--border)] bg-transparent p-2 text-sm focus-ring">
            <option value="">All</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
          <button className="px-3 py-2 rounded-md border focus-ring" onClick={() => refetch()}>Filter</button>
        </div>
      </div>
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card-surface p-4 rounded-xl">
              <Skeleton className="h-40" />
              <Skeleton className="h-4 mt-3 w-2/3" />
            </div>
          ))}
        </div>
      )}
      {isError && <div className="text-red-500">Failed to load workflows.</div>}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.pages.flatMap(p => p.workflows).map(w => (
            <Link key={w.workflow_id} href={`/workflows/${w.workflow_id}`} className="card-surface p-4 rounded-xl hover:shadow-glow transition">
              <div className="aspect-video rounded-md border border-[var(--border)] bg-black/5 dark:bg-white/5" />
              <div className="mt-3 text-sm font-medium line-clamp-2">{w.topic}</div>
              <div className="mt-1 text-xs opacity-70 flex items-center justify-between">
                <span className="capitalize">{w.status.replace('awaiting_', 'awaiting ')}</span>
                {w.duration_seconds ? <span>{w.duration_seconds}s</span> : null}
              </div>
            </Link>
          ))}
        </div>
      )}
      <div ref={sentinelRef} />
      {isFetchingNextPage && <div className="text-sm opacity-70">Loading more…</div>}
      {data && data.pages[0]?.total === 0 && (
        <div className="card-surface p-6 rounded-xl text-center">
          <p className="opacity-80">No workflows yet. Create your first video.</p>
        </div>
      )}
    </div>
  )
}
