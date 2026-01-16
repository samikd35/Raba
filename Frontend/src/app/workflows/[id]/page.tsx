'use client'

import { useParams, useRouter } from 'next/navigation'
import { useWorkflow } from '@/hooks/use-workflow'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { PipelineStepper } from '@/components/pipeline-stepper'
import { StatusBadge } from '@/components/status-badge'
import { ChevronLeft, RefreshCw, Trash2, Download, ExternalLink } from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import { toast } from 'sonner'
import { BorderBeam } from '@/components/ui/border-beam'

export default function WorkflowDetailPage() {
    const params = useParams()
    const router = useRouter()
    const workflowId = params.id as string
    const { data: workflow, isLoading, error, refetch } = useWorkflow(workflowId)

    const handleDelete = async () => {
        if (!confirm('Are you sure you want to delete this workflow?')) return
        try {
            await api.delete(`/workflows/${workflowId}`)
            toast.success('Workflow deleted')
            router.push('/workflows')
        } catch (e) {
            toast.error('Failed to delete workflow')
        }
    }

    if (isLoading) {
        return (
            <div className="container py-10 space-y-8">
                <div className="flex items-center gap-4">
                    <Skeleton className="h-10 w-10 rounded-md" />
                    <div className="space-y-2">
                        <Skeleton className="h-8 w-64" />
                        <Skeleton className="h-4 w-32" />
                    </div>
                </div>
                <Skeleton className="h-24 w-full" />
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Skeleton className="h-96 md:col-span-2" />
                    <Skeleton className="h-96" />
                </div>
            </div>
        )
    }

    if (error || !workflow) {
        return (
            <div className="container py-20 text-center">
                <h2 className="text-2xl font-bold text-destructive mb-4">Workflow Not Found</h2>
                <p className="text-muted-foreground mb-8">Could not load workflow {workflowId}</p>
                <Button variant="outline" asChild>
                    <Link href="/workflows">Back to Workflows</Link>
                </Button>
            </div>
        )
    }

    // Calculate pipeline steps
    const steps = [
        {
            id: 'tool',
            label: 'Strategy',
            status: workflow.tool_selection ? 'completed' : workflow.current_hitl_gate === 'tool_selection' ? 'waiting' : workflow.status === 'running' ? 'running' : 'pending',
            meta: workflow.tool_selection?.tool_name
        },
        {
            id: 'research',
            label: 'Research',
            status: workflow.research_output ? 'completed' : (workflow.tool_selection && workflow.current_hitl_gate === 'research') ? 'waiting' : (workflow.tool_selection && workflow.status === 'running') ? 'running' : 'pending',
            meta: workflow.research_output ? `${workflow.research_output.sources?.length || 0} sources` : undefined
        },
        {
            id: 'script',
            label: 'Script',
            status: workflow.script_output ? 'completed' : (workflow.research_output && workflow.current_hitl_gate === 'script') ? 'waiting' : (workflow.research_output && workflow.status === 'running') ? 'running' : 'pending',
            meta: workflow.script_output ? `Viral Score: ${workflow.script_output.viral_score}` : undefined
        },
        {
            id: 'image',
            label: 'Images',
            status: (workflow.generated_images?.length || 0) > 0 ? 'completed' : (workflow.script_output && workflow.current_hitl_gate === 'images') ? 'waiting' : (workflow.script_output && workflow.status === 'running') ? 'running' : 'pending',
            meta: workflow.generated_images ? `${workflow.generated_images.length} generated` : undefined
        },
        {
            id: 'video',
            label: 'Video',
            status: workflow.video_url ? 'completed' : (workflow.generated_images && workflow.current_hitl_gate === 'video') ? 'waiting' : (workflow.generated_images && workflow.status === 'running') ? 'running' : 'pending'
        }
    ] as const

    return (
        <div className="container py-8 max-w-6xl space-y-8 mx-auto">
            {/* Header */}
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="flex items-start gap-4">
                    <Button variant="ghost" size="icon" asChild className="mt-1">
                        <Link href="/workflows"><ChevronLeft className="h-5 w-5" /></Link>
                    </Button>
                    <div className="space-y-1">
                        <div className="flex items-center gap-3">
                            <h1 className="text-2xl font-bold tracking-tight line-clamp-1">{workflow.topic}</h1>
                            <StatusBadge status={workflow.status} />
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>{new Date(workflow.created_at).toLocaleDateString()}</span>
                            <span>•</span>
                            <span className="capitalize">{workflow.category.replace('_', ' ')}</span>
                            <span>•</span>
                            <span>{workflow.resolution}</span>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => refetch()}>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Refresh
                    </Button>
                    <Button variant="destructive" size="sm" onClick={handleDelete}>
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete
                    </Button>
                </div>
            </div>

            {/* Pipeline Stepper */}
            <Card>
                <CardContent className="pt-6">
                    <PipelineStepper steps={steps as any} />
                </CardContent>
            </Card>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                {/* Left Column: Artifacts */}
                <div className="lg:col-span-2 space-y-6">

                    {/* Script Card */}
                    {workflow.script_output && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2">
                                    Script
                                    <span className="text-xs font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                                        Viral Score: {workflow.script_output.viral_score}
                                    </span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4 max-h-[400px] overflow-y-auto font-mono text-sm leading-relaxed">
                                <div className="p-4 bg-muted/30 rounded-lg border-l-4 border-primary">
                                    <p className="font-semibold text-primary mb-1">Hook</p>
                                    {workflow.script_output.hook.script}
                                </div>
                                <div className="space-y-4">
                                    {workflow.script_output.scenes.map((scene, i) => (
                                        <div key={i} className="pl-4 border-l-2 border-border">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider block mb-1">Scene {i + 1}</span>
                                            <p>{scene.description}</p>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Images Grid */}
                    {workflow.generated_images && workflow.generated_images.length > 0 && (
                        <Card>
                            <CardHeader><CardTitle className="text-lg">Generated Images</CardTitle></CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                                    {workflow.generated_images.map((url, i) => (
                                        <div key={i} className="aspect-square relative rounded-lg overflow-hidden border bg-muted group">
                                            <img src={url} alt={`Scene ${i + 1}`} className="object-cover w-full h-full transition-transform group-hover:scale-105" />
                                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                                <a href={url} target="_blank" rel="noopener noreferrer" className="p-2 bg-background/80 rounded-full hover:bg-background">
                                                    <ExternalLink className="h-4 w-4" />
                                                </a>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>

                {/* Right Column: Video Preview & Actions */}
                <div className="space-y-6">

                    {/* Video Player */}
                    <Card className="overflow-hidden relative bg-black/5 border-muted-foreground/10">
                        {workflow.video_url ? (
                            <div className="relative aspect-[9/16] bg-black">
                                <BorderBeam size={200} duration={8} borderWidth={2} colorFrom="#BEF264" colorTo="#6366F1" />
                                <video
                                    src={workflow.video_url}
                                    controls
                                    className="w-full h-full object-contain"
                                    poster={workflow.generated_images?.[0]}
                                />
                            </div>
                        ) : (
                            <div className="aspect-[9/16] flex flex-col items-center justify-center text-center p-6 bg-muted/10 border-2 border-dashed border-muted-foreground/20 m-4 rounded-xl">
                                {workflow.status === 'failed' ? (
                                    <div className="text-destructive space-y-2">
                                        <Trash2 className="h-8 w-8 mx-auto" />
                                        <p className="font-semibold">Generation Failed</p>
                                    </div>
                                ) : (
                                    <div className="text-muted-foreground space-y-4 animate-pulse">
                                        <div className="h-12 w-12 rounded-full bg-muted mx-auto" />
                                        <p className="text-sm">Video generating...</p>
                                    </div>
                                )}
                            </div>
                        )}

                        {workflow.video_url && (
                            <div className="p-4 flex gap-2">
                                <Button className="w-full" asChild>
                                    <a href={workflow.video_url} download>
                                        <Download className="h-4 w-4 mr-2" /> Download
                                    </a>
                                </Button>
                            </div>
                        )}
                    </Card>

                    {/* Research Summary */}
                    {workflow.research_output && (
                        <Card>
                            <CardHeader><CardTitle className="text-base">Research</CardTitle></CardHeader>
                            <CardContent className="text-sm space-y-3">
                                <div>
                                    <span className="font-semibold">{workflow.research_output.sources?.length || 0} Sources Used</span>
                                    <ul className="list-disc pl-4 mt-1 text-muted-foreground text-xs line-clamp-3">
                                        {(workflow.research_output.sources || []).slice(0, 3).map((s: any, i: number) => (
                                            <li key={i}>{typeof s === 'string' ? s : s.title || s.url}</li>
                                        ))}
                                    </ul>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                </div>
            </div>
        </div>
    )
}
