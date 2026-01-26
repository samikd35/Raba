'use client'

import React from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { StatusBadge } from '@/components/status-badge'
import { PlusCircle, Search, Clock, Film } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { WorkflowState } from '@/hooks/use-workflow'

const categoryDisplayNames: Record<string, string> = {
    realistic: 'Realistic',
    anime: 'Anime',
    animation: 'Animation',
    surreal_realism: 'Realistic',
    high_octane_anime: 'Anime',
    stylized_3d: 'Animation',
    auto: 'Auto',
}

const formatCategory = (category: string | undefined): string => {
    if (!category) return 'Auto'
    return categoryDisplayNames[category] || category.replace('_', ' ')
}

interface WorkflowsResponse {
    workflows: WorkflowState[]
    total: number
    has_more: boolean
}

export default function WorkflowsPage() {
    const { data, isLoading, isError } = useQuery({
        queryKey: ['workflows'],
        queryFn: () => api.get<WorkflowsResponse>('/workflows?limit=50'),
    })

    return (
        <div className="container py-8 dark:bg-zinc-950 min-h-[calc(100vh-3.5rem)] mx-auto">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div className="space-y-1">
                    <h1 className="text-3xl font-bold tracking-tight">Workflows</h1>
                    <p className="text-muted-foreground">Manage and monitor your video generation pipelines.</p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="relative w-full md:w-64">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input type="search" placeholder="Search topics..." className="pl-9 bg-background/50" />
                    </div>
                    <Button asChild className="gap-2">
                        <Link href="/">
                            <PlusCircle className="h-4 w-4" /> Create
                        </Link>
                    </Button>
                </div>
            </div>

            {isLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {Array.from({ length: 8 }).map((_, i) => (
                        <Card key={i} className="bg-card/50">
                            <CardHeader><Skeleton className="h-6 w-3/4" /></CardHeader>
                            <CardContent className="h-32"><Skeleton className="h-full w-full" /></CardContent>
                        </Card>
                    ))}
                </div>
            ) : isError ? (
                <div className="p-10 text-center border dashed rounded-lg bg-muted/10">
                    <p className="text-destructive mb-2">Failed to load workflows.</p>
                    <Button onClick={() => window.location.reload()}>Retry</Button>
                </div>
            ) : data?.workflows.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-20 border-2 border-dashed rounded-xl bg-muted/5 text-center">
                    <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mb-4">
                        <Film className="h-8 w-8 text-muted-foreground" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2">No videos yet</h3>
                    <p className="text-muted-foreground mb-6 max-w-sm">Start your first AI video generation to see it appear here.</p>
                    <Button asChild size="lg">
                        <Link href="/">Create Video</Link>
                    </Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {data?.workflows.map((workflow) => (
                        <Link key={workflow.workflow_id} href={`/workflows/${workflow.workflow_id}`}>
                            <Card className="h-full hover:border-primary/50 transition-all hover:shadow-[0_0_20px_rgba(99,102,241,0.1)] group">
                                <div className="aspect-video bg-muted relative overflow-hidden rounded-t-lg">
                                    {workflow.generated_images?.[0] ? (
                                        <img src={workflow.generated_images[0]} alt="Preview" className="w-full h-full object-cover transition-transform group-hover:scale-105" />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center bg-zinc-900 text-zinc-700">
                                            <Film className="h-10 w-10" />
                                        </div>
                                    )}
                                    <div className="absolute top-2 right-2">
                                        <StatusBadge status={workflow.status} className="shadow-sm backdrop-blur-md bg-background/80" />
                                    </div>
                                </div>
                                <CardHeader className="pb-3 pt-4">
                                    <h3 className="font-semibold line-clamp-2 leading-tight group-hover:text-primary transition-colors">
                                        {workflow.topic}
                                    </h3>
                                </CardHeader>
                                <CardContent className="pb-3">
                                    <div className="flex items-center text-xs text-muted-foreground gap-3">
                                        <span className="flex items-center gap-1">
                                            <Clock className="h-3 w-3" />
                                            {new Date(workflow.created_at).toLocaleDateString()}
                                        </span>
                                        <span className="px-1.5 py-0.5 bg-muted rounded">
                                            {formatCategory(workflow.category)}
                                        </span>
                                    </div>
                                </CardContent>
                            </Card>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    )
}
